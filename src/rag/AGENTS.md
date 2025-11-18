# RAG (Retrieval-Augmented Generation) System Documentation

**Parent Instructions**: See `/AGENTS.md` for global project context and universal coding guidelines.

**This document** contains RAG-specific implementation details that extend/override root instructions.

---

## Overview

The RAG layer enhances AI analysis with real-time market context: news articles, global market data, sentiment metrics, and cryptocurrency category information. It indexes news articles for semantic search, detects coin mentions via NLP, and builds contextual prompts that combine technical indicators with market narrative.

## Architecture

### Core Design Principles

- **Real-time context**: News updated hourly, market data every 4 hours
- **Symbol-aware**: Automatic coin detection in news (NLP + regex)
- **Indexed search**: Fast article lookup by coin, category, keyword, tag
- **Token-aware**: Respects context limits (configurable per model)
- **Modular components**: Separate managers for news, market data, categories, indexing

### Directory Structure

```
src/rag/
├── AGENTS.md (this file)
├── core/
│   ├── rag_engine.py           # Main orchestrator
│   └── context_builder.py      # Builds contextual prompts
├── data/
│   ├── news_manager.py         # News fetching & caching
│   ├── market_data_manager.py  # Market overview data
│   ├── file_handler.py         # JSON file I/O
│   └── market_components.py    # Market data sub-components
├── management/
│   ├── category_manager.py     # Cryptocurrency categories
│   ├── ticker_manager.py       # Known ticker validation
│   └── category_fetcher.py     # Category API integration
├── processing/
│   ├── article_processor.py    # Article parsing utilities
│   └── news_category_analyzer.py  # Category classification
└── search/
    ├── index_manager.py        # Search indices
    └── search_utilities.py     # Search helpers
```

## Core Engine

### RagEngine

**Location**: `src/rag/core/rag_engine.py`

**Purpose**: Main orchestrator coordinating news, market data, categories, and search.

**Initialization**:
```python
rag_engine = RagEngine(
    logger=logger,
    token_counter=token_counter,
    coingecko_api=coingecko_api,
    cryptocompare_api=cryptocompare_api,
    symbol_manager=symbol_manager,
    format_utils=format_utils
)
await rag_engine.initialize()  # Load cached data, start periodic updates
```

**Key Methods**:

#### `initialize() -> None`
Bootstrap RAG engine:
1. Initialize API clients (CoinGecko, CryptoCompare)
2. Load known tickers from disk (`data/known_tickers.json`)
3. Ensure categories up-to-date (`data/categories.json`)
4. Load cached news (`data/crypto_news.json`)
5. Build search indices (category, tag, coin, keyword)
6. Update known tickers from news mentions

#### `refresh_market_data() -> None`
Update all market context:
```python
await rag_engine.refresh_market_data()
# 1. Ensure categories up-to-date (24-hour cache)
# 2. Fetch fresh news articles (50 articles, 24-hour max age)
# 3. Update market overview (global market cap, volume, dominance)
# 4. Process articles (detect coins, filter duplicates)
# 5. Update news database
# 6. Rebuild search indices
```

**Update Intervals** (configured in `config.ini`):
- News: 1 hour (`rag_update_interval_hours`)
- Categories: 24 hours
- Market overview: 4 hours

#### `retrieve_context(query: str, symbol: str, k: int, max_tokens: int) -> str`
Retrieve relevant news context for analysis:
```python
context = await rag_engine.retrieve_context(
    query="What's happening with Bitcoin?",
    symbol="BTC/USDT",
    k=3,  # Top 3 articles
    max_tokens=8096  # Token limit
)
# Returns: Formatted news articles with metadata
```

**Context Building Pipeline**:
1. **Keyword search**: Score articles by query relevance
2. **Symbol filtering**: Prioritize coin-specific articles
3. **Token limiting**: Truncate to fit model context window
4. **Formatting**: Structure with timestamps, sources, summaries

**Component Managers**:
```python
self.news_manager          # News fetching, caching, processing
self.market_data_manager   # Market overview data
self.category_manager      # Cryptocurrency categories
self.index_manager         # Search indices
self.context_builder       # Context prompt construction
```

**Periodic Updates**:
- Task: `_periodic_update_task` (background asyncio task)
- Checks: `update_if_needed()` every analysis
- Trigger: Time-based (last_update + update_interval)

### ContextBuilder

**Location**: `src/rag/core/context_builder.py`

**Purpose**: Build contextual prompts from news articles with token limiting.

**Key Methods**:

#### `keyword_search(query, news_database, symbol, coin_indices, category_word_map, important_categories) -> List[Tuple[int, float]]`
Score articles by relevance:
```python
scores = await context_builder.keyword_search(
    query="Bitcoin ETF approval",
    news_database=rag_engine.news_manager.news_database,
    symbol="BTC/USDT",
    coin_indices=index_manager.get_coin_indices(),
    category_word_map=category_manager.get_category_word_map(),
    important_categories=category_manager.get_important_categories()
)
# Returns: [(article_index, score), ...] sorted by score descending
```

**Scoring Algorithm**:
1. **Coin mention**: +10 points if symbol in article
2. **Query keywords**: +5 points per keyword match (title), +2 points (body)
3. **Category match**: +7 points for important categories (Bitcoin, Ethereum, etc.)
4. **Recency**: +3 points for articles < 12 hours old

#### `build_context_with_token_limit(articles, max_tokens) -> str`
Format articles within token budget:
```python
context = context_builder.build_context_with_token_limit(
    articles=[article1, article2, article3],
    max_tokens=8096
)
# Returns:
# """
# === NEWS CONTEXT ===
# 
# [1] Bitcoin ETF Approved by SEC (2025-11-02 14:30 UTC)
# Source: CoinDesk | Coins: BTC, ETH
# Summary: The SEC has approved the first spot Bitcoin ETF...
# 
# [2] Ethereum Network Upgrade Scheduled (2025-11-01 18:00 UTC)
# Source: CoinTelegraph | Coins: ETH
# Summary: The Ethereum network will undergo...
# """
```

**Token Management**:
- Uses `TokenCounter` to measure prompt size
- Truncates articles that exceed budget
- Prioritizes higher-scoring articles
- Ensures at least 1 article included (if available)

## Data Management

### NewsManager

**Location**: `src/rag/data/news_manager.py`

**Purpose**: Fetch, cache, and process cryptocurrency news articles.

**Key Methods**:

#### `fetch_fresh_news(known_crypto_tickers: Set[str]) -> List[Dict[str, Any]]`
Fetch recent news from CryptoCompare:
```python
articles = await news_manager.fetch_fresh_news(
    known_crypto_tickers={"BTC", "ETH", "SOL", ...}
)
# Returns: List of articles with detected coins
# [
#   {
#     "id": "123456",
#     "title": "Bitcoin Breaks $50k",
#     "body": "Bitcoin has surged...",
#     "source": "CoinDesk",
#     "published_on": 1730563200,
#     "tags": "bitcoin|market",
#     "categories": "BTC,Market",
#     "detected_coins": ["BTC"],
#     "detected_coins_str": "BTC"
#   }
# ]
```

**Coin Detection Pipeline**:
1. **Category extraction**: Check `categories` field for tickers
2. **Title/body NLP**: Use `ArticleProcessor.detect_coins_in_article()`
3. **Regex matching**: Find ticker patterns (e.g., `$BTC`, `BTC/USD`)
4. **Known ticker validation**: Filter against `known_tickers` set

#### `update_news_database(new_articles: List[Dict[str, Any]]) -> bool`
Update cached news with new articles:
```python
updated = news_manager.update_news_database(new_articles)
# 1. Filter articles by age (24 hours)
# 2. Deduplicate by article ID
# 3. Sort by timestamp (newest first)
# 4. Save to data/crypto_news.json
# Returns: True if database updated, False if no new articles
```

**Caching Strategy**:
- File: `data/crypto_news.json`
- Format: JSON array of article objects
- Retention: 24 hours (filtered on update)
- Fallback: Load cached articles on API failure

**Fallback Mechanism**:
- If API fails: Use cached articles up to 72 hours old
- Prevents analysis failures during API outages

### MarketDataManager

**Location**: `src/rag/data/market_data_manager.py`

**Purpose**: Fetch and process global cryptocurrency market overview data.

**Component Architecture**:
- **MarketDataFetcher**: Fetch from CoinGecko/CryptoCompare
- **MarketDataProcessor**: Extract and format market metrics
- **MarketDataCache**: File-based caching
- **MarketOverviewBuilder**: Construct final overview structure

**Key Methods**:

#### `fetch_market_overview() -> Optional[Dict[str, Any]]`
Fetch global market data:
```python
overview = await market_data_manager.fetch_market_overview()
# Returns:
# {
#   "total_market_cap": {"usd": 2500000000000},
#   "total_volume": {"usd": 150000000000},
#   "market_cap_percentage": {"btc": 45.2, "eth": 18.3},
#   "updated_at": 1730563200,
#   "top_coins": {
#     "BTC": {
#       "price": 50000,
#       "change24h": 5.2,
#       "volume24h": 30000000000,
#       "mcap": 1000000000000,
#       "vwap": 49800
#     }
#   }
# }
```

**Data Sources**:
1. **Primary**: CoinGecko (`/global`, `/coins/markets`)
2. **Fallback**: CryptoCompare (`/pricemultifull`)
3. **Supplemental**: CCXT exchange tickers (if available)

#### `update_market_overview_if_needed(max_age_hours: int) -> bool`
Conditional update based on age:
```python
updated = await market_data_manager.update_market_overview_if_needed(max_age_hours=4)
# Checks timestamp, updates if older than max_age_hours
# Returns: True if updated, False if cache still valid
```

**Caching**:
- File: `data/market_data/coingecko_global.json`
- Update interval: 4 hours (default)
- Format: JSON with timestamp metadata

**Top Coins Extraction**:
- Prioritizes coins by market cap dominance
- Excludes stablecoins (USDT, USDC, DAI)
- Default: Top 10 coins (BTC, ETH, BNB, SOL, etc.)

### CategoryManager

**Location**: `src/rag/management/category_manager.py`

**Purpose**: Manage cryptocurrency categories and category-to-coin mappings.

**Key Methods**:

#### `load_known_tickers() -> None`
Load cryptocurrency tickers from disk:
```python
await category_manager.load_known_tickers()
# Loads data/known_tickers.json
# Sets: self.known_tickers = {"BTC", "ETH", "SOL", ...}
```

**Known Tickers**:
- File: `data/known_tickers.json`
- Format: JSON array of ticker strings
- Auto-updated from news mentions

#### `ensure_categories_updated() -> bool`
Update categories if cache stale:
```python
updated = await category_manager.ensure_categories_updated()
# Checks data/categories.json timestamp
# Fetches from CryptoCompare if older than 24 hours
# Returns: True if updated (rebuild indices needed), False if cache valid
```

**Categories Structure**:
```json
[
  {
    "categoryId": "BTC",
    "categoryName": "Bitcoin",
    "avgCoinPrice": 50000,
    "totalMarketCap": 1000000000000
  },
  {
    "categoryId": "DEFI",
    "categoryName": "DeFi",
    "avgCoinPrice": 1500,
    "totalMarketCap": 50000000000
  }
]
```

#### `get_category_word_map() -> Dict[str, str]`
Get keyword-to-category mapping:
```python
word_map = category_manager.get_category_word_map()
# Returns: {
#   "bitcoin": "BTC",
#   "ethereum": "ETH",
#   "defi": "DEFI",
#   "nft": "NFT",
#   ...
# }
```

**Word Map Usage**:
- Powers keyword-based article categorization
- Used in `IndexManager._index_article_keywords()`
- Enables semantic search (e.g., "DeFi" → finds articles about Uniswap, Aave)

#### `get_important_categories() -> Set[str]`
Get high-priority categories:
```python
important = category_manager.get_important_categories()
# Returns: {"BTC", "ETH", "DEFI", "NFT", "REGULATION"}
```

**Important Categories**:
- Weighted higher in relevance scoring
- Configurable via hardcoded set (can be dynamic later)

## Search & Indexing

### IndexManager

**Location**: `src/rag/search/index_manager.py`

**Purpose**: Build and maintain inverted indices for fast article lookup.

**Index Types**:
1. **Category Index**: `category -> [article_indices]`
2. **Tag Index**: `tag -> [article_indices]`
3. **Coin Index**: `coin_ticker -> [article_indices]`
4. **Keyword Index**: `keyword -> [article_indices]`

**Key Methods**:

#### `build_indices(news_database, known_crypto_tickers, category_word_map) -> None`
Build all search indices:
```python
index_manager.build_indices(
    news_database=rag_engine.news_manager.news_database,
    known_crypto_tickers=category_manager.get_known_tickers(),
    category_word_map=category_manager.get_category_word_map()
)
# Clears existing indices, rebuilds from scratch
```

**Indexing Pipeline** (per article):
1. **Category indexing**: Split `categories` field, lowercase, add to index
2. **Tag indexing**: Split `tags` field, lowercase, add to index
3. **Coin indexing**: Detect coins via `ArticleProcessor`, add to index
4. **Keyword indexing**: Extract title/body keywords, associate with categories

#### `search_by_coin(coin: str) -> List[int]`
Find articles mentioning a specific coin:
```python
article_indices = index_manager.search_by_coin("BTC")
# Returns: [0, 5, 12, 23, ...] (indices in news_database)
```

#### `search_by_category(category: str) -> List[int]`
Find articles in a category:
```python
article_indices = index_manager.search_by_category("DeFi")
# Returns: [1, 8, 15, ...] (indices of DeFi-related articles)
```

#### `search_by_keyword(keyword: str) -> List[int]`
Find articles containing keyword:
```python
article_indices = index_manager.search_by_keyword("regulation")
# Returns: [3, 9, 17, ...] (indices of articles with "regulation")
```

**Index Statistics**:
```python
stats = index_manager.get_index_stats()
# Returns: {
#   "categories": 50,    # Number of unique categories
#   "tags": 200,         # Number of unique tags
#   "coins": 150,        # Number of unique coins
#   "keywords": 5000     # Number of unique keywords
# }
```

**Index Rebuilding**:
- Triggered on: News database update, category refresh
- Frequency: Every news update (hourly)
- Cost: O(n) where n = number of articles (~50 articles = <50ms)

### ArticleProcessor

**Location**: `src/rag/processing/article_processor.py`

**Purpose**: Shared utilities for article parsing and coin detection.

**Key Methods**:

#### `detect_coins_in_article(article: Dict[str, Any], known_crypto_tickers: Set[str]) -> Set[str]`
Detect coins mentioned in article:
```python
coins = article_processor.detect_coins_in_article(
    article={
        "title": "Bitcoin and Ethereum Surge on ETF News",
        "body": "Bitcoin (BTC) and Ethereum (ETH) both rallied...",
        "categories": "BTC,Market"
    },
    known_crypto_tickers={"BTC", "ETH", "SOL", ...}
)
# Returns: {"BTC", "ETH"}
```

**Detection Algorithm**:
1. **Category extraction**: Check `categories` field
2. **Title NLP**: Use `UnifiedParser.detect_coins_in_text()`
3. **Body NLP**: Scan first 10,000 chars of body
4. **Known ticker filtering**: Only return known tickers

**Regex Patterns** (in UnifiedParser):
- `$BTC`, `$ETH` (Twitter-style)
- `BTC/USD`, `ETH/USDT` (trading pairs)
- `Bitcoin (BTC)`, `Ethereum (ETH)` (parenthetical)
- Word boundaries: `\bBTC\b` (not "BTCUSD" or "BTC123")

#### `get_article_timestamp(article: Dict[str, Any]) -> float`
Extract Unix timestamp:
```python
timestamp = article_processor.get_article_timestamp(article)
# Returns: 1730563200.0 (float Unix timestamp)
```

#### `format_article_date(article: Dict[str, Any]) -> str`
Format human-readable date:
```python
date_str = article_processor.format_article_date(article)
# Returns: "2025-11-02 14:30 UTC"
```

## Integration with Analysis System

### Usage in AnalysisEngine

**Location**: `src/analyzer/core/analysis_engine.py`

```python
class AnalysisEngine:
    def __init__(self, ..., rag_engine):
        self.rag_engine = rag_engine
    
    async def analyze_market(self, symbol: str) -> Dict[str, Any]:
        # 1. Ensure RAG context up-to-date
        await self.rag_engine.update_if_needed()
        
        # 2. Calculate technical indicators
        indicators = self.technical_calculator.get_indicators(ohlcv_data)
        
        # 3. Detect patterns
        patterns = self.pattern_analyzer.detect_patterns(ohlcv_data, indicators)
        
        # 4. Retrieve news context
        news_context = await self.rag_engine.retrieve_context(
            query=f"Latest news about {symbol}",
            symbol=symbol,
            k=3,  # Top 3 articles
            max_tokens=8096
        )
        
        # 5. Build AI prompt with news context
        prompt = self.prompt_builder.build_prompt(
            symbol=symbol,
            indicators=indicators,
            patterns=patterns,
            news_context=news_context
        )
        
        # 6. Get AI analysis
        analysis = await self.model_manager.get_analysis(prompt)
        
        return analysis
```

### PromptBuilder Integration

**Location**: `src/analyzer/prompts/prompt_builder.py`

```python
class PromptBuilder:
    def build_prompt(self, symbol, indicators, patterns, news_context, ...):
        sections = [
            self._build_system_instructions(),
            self._build_market_overview_section(),  # Uses RAG market data
            self._build_technical_section(indicators),
            self._build_pattern_section(patterns),
            news_context,  # RAG news context
            self._build_query_section(symbol)
        ]
        
        return "\n\n".join(sections)
```

**Note**: Market overview data is fetched separately by PromptBuilder to avoid duplication. `retrieve_context()` only returns news articles.

## Configuration

### config.ini

```ini
[rag]
rag_update_interval_hours = 1         # News update interval
categories_update_hours = 24          # Category update interval
market_overview_update_hours = 4      # Market data update interval

[cryptocompare]
news_update_hours = 1                 # News cache expiry
news_max_age_hours = 24              # Article age filter
news_fetch_limit = 50                # Articles per fetch

[coingecko]
cache_expiry = -1                    # SQLite cache (never expire)
update_interval_hours = 4            # Manual update interval
```

### Data Files

- **News cache**: `data/crypto_news.json`
- **Known tickers**: `data/known_tickers.json`
- **Categories**: `data/categories.json`
- **Market overview**: `data/market_data/coingecko_global.json`
- **News fallback**: `data/news_cache/recent_news.json`

## Common Patterns

### Initialize RAG Engine

```python
# In app.py initialization
rag_engine = RagEngine(
    logger=logger,
    token_counter=token_counter,
    coingecko_api=coingecko_api,
    cryptocompare_api=cryptocompare_api,
    symbol_manager=symbol_manager,
    format_utils=format_utils
)
await rag_engine.initialize()
```

### Edge Cases & Configuration

- **Ticker collisions**: Coin detection trusts the `known_tickers` set managed by `CategoryManager`/`TickerManager`. When two assets share a symbol (e.g., SOL vs. SoLend), manually curate `data/known_tickers.json` or adjust `category_processor.category_word_map` to avoid false positives.
- **Article length**: Only the first 10,000 characters of an article body are scanned for tickers (`ArticleProcessor.detect_coins_in_article`). Long-form research pieces should surface key tickers near the top or via the `categories` metadata.
- **Category word map**: `CategoryManager` maps keywords to categories but does not attempt disambiguation. If a word spans multiple sectors, add project-specific keywords or tighten regex rules in `category_processor` to prevent broad matches.
- **Symbol extraction**: Base-coin extraction for context queries relies on `UnifiedParser.extract_base_coin`; provide trading pairs in standard `BASE/QUOTE` format to keep lookups accurate.

### Scalability Considerations

- **Index rebuild cost**: `IndexManager.build_indices` runs in O(n) over the current news database (default 50 articles). Even at 500 articles, rebuilds remain sub-100 ms, but keep `news_fetch_limit` aligned with available memory if you expect sustained growth.
- **Background updates**: `RagEngine.start_periodic_updates` spawns an async loop keyed off `config.RAG_UPDATE_INTERVAL_HOURS`. For high-throughput deployments ensure only a single instance runs periodic refreshes to avoid duplicated API calls.
- **Token budgeting**: `TokenCounter` defaults to the `cl100k_base` tokenizer. When switching to models with different tokenization, instantiate `TokenCounter(encoding_name=...)` and pass it into `RagEngine` so context trimming respects the new limits.

### Data Integrity & Recovery

- **Atomic file writes**: `RagFileHandler.save_json_file` writes via temporary files and `os.replace`, minimizing risk of half-written caches if the process terminates mid-write.
- **Corrupted cache files**: `RagFileHandler.load_json_file` logs the failure and returns `None`, allowing `NewsManager`/`CategoryManager` to rebuild fresh state from live API calls without crashing the update loop.
- **Fallback articles**: `RagFileHandler.load_fallback_articles` keeps up to 72 h of news for outages. After a failure the next successful fetch repopulates indices automatically through `RagEngine._build_indices()`.
- **Known ticker drift**: Run `await category_manager.update_known_tickers(news_database)` whenever integrating new exchanges so ticker validation stays in sync.
- **Manual resets**: Delete `data/crypto_news.json`, `data/categories.json`, or `data/known_tickers.json` to force clean rebuilds. The initial `RagEngine.initialize()` call recreates directories and downloads fresh content on startup.

### Update News Manually

```python
# Force refresh regardless of cache age
await rag_engine.refresh_market_data()
```

### Search for Coin-Specific News

```python
# Get articles mentioning Bitcoin
btc_indices = index_manager.search_by_coin("BTC")
btc_articles = [news_database[i] for i in btc_indices]

# Get top 5 by recency
btc_articles.sort(key=lambda x: x['published_on'], reverse=True)
top_5 = btc_articles[:5]
```

### Build Context for Specific Symbol

```python
context = await rag_engine.retrieve_context(
    query="Ethereum network upgrade",
    symbol="ETH/USDT",
    k=5,  # Top 5 articles
    max_tokens=16000
)
```

### Check News Database Status

```python
db_size = rag_engine.news_manager.get_database_size()
last_update = rag_engine.last_update

if db_size == 0:
    logger.warning("News database is empty, refreshing...")
    await rag_engine.refresh_market_data()
```

## Error Handling

### API Failures

**News API Failure**:
```python
# NewsManager._get_fallback_articles()
# Falls back to cached articles up to 72 hours old
fallback = news_manager._get_fallback_articles()
if fallback:
    logger.info(f"Using {len(fallback)} cached articles as fallback")
```

**Market Data API Failure**:
```python
# Returns None, analysis continues without market overview
overview = await market_data_manager.fetch_market_overview()
if overview is None:
    logger.warning("Market overview unavailable, continuing without it")
```

### Empty News Database

```python
# retrieve_context() returns empty string if no articles
context = await rag_engine.retrieve_context(...)
if not context:
    logger.warning("No news context available for analysis")
# Analysis proceeds with technical indicators only
```

### Coin Detection Failures

```python
# ArticleProcessor.detect_coins_in_article() returns empty set
coins = article_processor.detect_coins_in_article(article, known_tickers)
if not coins:
    # Article not indexed by coin (only by keyword/category)
    pass
```

## Performance Considerations

### Indexing Performance

- **Index build time**: ~50ms for 50 articles
- **Search time**: O(1) lookup via dict (instant)
- **Memory usage**: ~100KB for 50 articles with indices

### News Fetching

- **API call frequency**: 1 hour (configurable)
- **Rate limits**: CryptoCompare free tier = 100,000 calls/month
- **Caching**: Reduces API calls by ~95%

### Token Budgeting

- **Default limit**: 8096 tokens (Gemini 2.5 Flash)
- **Context truncation**: Oldest articles truncated first
- **Article overhead**: ~500 tokens per article (avg)
- **Typical context**: 3-5 articles = 1500-2500 tokens

### Update Intervals

**Recommended**:
- News: 1 hour (real-time enough for most use cases)
- Categories: 24 hours (rarely change)
- Market overview: 4 hours (global data stable)

**High-frequency trading**:
- News: 15 minutes (API rate limits permissive)
- Market overview: 1 hour (more up-to-date)

## Troubleshooting

**No articles in database**:
- Check `data/crypto_news.json` exists
- Verify CryptoCompare API key (if using paid tier)
- Check network connectivity
- Enable debug logging: `logger_debug = true` in config

**Coin detection missing obvious mentions**:
- Update `data/known_tickers.json` with missing tickers
- Check `ArticleProcessor.detect_coins_in_article()` logic
- Verify UnifiedParser regex patterns

**Search returns no results**:
- Rebuild indices: `index_manager.build_indices(...)`
- Check case sensitivity (all indices lowercase)
- Verify article has non-empty title/body

**High memory usage**:
- Reduce `news_fetch_limit` in config (default: 50)
- Reduce `news_max_age_hours` (filter older articles)
- Clear cache: Delete `data/crypto_news.json`

**Stale market data**:
- Check `last_update` timestamp
- Force refresh: `await rag_engine.refresh_market_data()`
- Verify API connectivity

## Files for Deeper Context

- **Core engine**: `src/rag/core/rag_engine.py`, `context_builder.py`
- **News management**: `src/rag/data/news_manager.py`, `file_handler.py`
- **Market data**: `src/rag/data/market_data_manager.py`, `market_components.py`
- **Categories**: `src/rag/management/category_manager.py`, `ticker_manager.py`
- **Search**: `src/rag/search/index_manager.py`, `search_utilities.py`
- **Processing**: `src/rag/processing/article_processor.py`, `news_category_analyzer.py`
- **Integration**: `src/analyzer/core/analysis_engine.py`, `prompts/prompt_builder.py`
- **Configuration**: `config/config.ini`, `data/*.json`
