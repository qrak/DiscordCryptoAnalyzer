# Platforms & External Integrations Documentation

This document describes external platform integrations (exchanges, market data APIs, AI providers) in DiscordCryptoAnalyzer.

## Overview

The platforms layer provides unified interfaces to external services: cryptocurrency exchanges (CCXT), market data APIs (CoinGecko, CryptoCompare, Alternative.me), and AI providers (Google AI, OpenRouter, LM Studio). All clients use async I/O, connection pooling, and implement retry/fallback logic for resilience.

## Architecture

### Core Design Principles

- **Async-first**: All API calls are `async` with proper session management
- **Connection pooling**: Single `aiohttp.ClientSession` shared across components
- **Lazy loading**: Resources initialized on-demand, not at startup
- **Caching**: SQLite/JSON caching reduces API rate limit pressure
- **Retry/fallback**: Automatic retry with exponential backoff, AI provider fallback chains
- **Resource cleanup**: Explicit shutdown handlers close all connections

### Directory Structure

```
src/platforms/
├── AGENTS.md (this file)
├── exchange_manager.py          # Multi-exchange integration via CCXT
├── coingecko.py                 # CoinGecko API (global data, coin images, DeFi)
├── cryptocompare.py             # CryptoCompare API (news, categories, market data)
├── alternative_me.py            # Alternative.me API (Fear & Greed Index)
├── ai_providers/
│   ├── base.py                  # BaseApiClient (shared HTTP logic)
│   ├── google.py                # Google AI Studio/Gemini API
│   ├── lmstudio.py              # LM Studio local inference
│   └── openrouter.py            # OpenRouter proxy API
└── utils/
    ├── cryptocompare_news_api.py         # News fetching & caching
    ├── cryptocompare_categories_api.py   # Category management
    ├── cryptocompare_market_api.py       # Market data endpoints
    └── cryptocompare_data_processor.py   # Data processing utilities
```

## Exchange Integrations

### ExchangeManager

**Location**: `src/platforms/exchange_manager.py`

**Purpose**: Manage connections to multiple cryptocurrency exchanges via CCXT with lazy loading and automatic refresh.

**Initialization**:
```python
exchange_manager = ExchangeManager(logger)
await exchange_manager.initialize()  # Creates shared aiohttp session, starts refresh task
```

**Lazy Loading Design**:
- No exchanges loaded at startup
- Exchanges loaded on first symbol validation
- Cached markets refreshed every `MARKET_REFRESH_HOURS` (configurable)

**Key Methods**:

#### `find_symbol_exchange(symbol: str) -> Tuple[Optional[ccxt.Exchange], Optional[str]]`
Find the first exchange supporting a trading pair:
```python
exchange, exchange_id = await exchange_manager.find_symbol_exchange("BTC/USDT")
if exchange:
    # Use exchange for OHLCV data fetching
    ohlcv = await exchange.fetch_ohlcv("BTC/USDT", "1h")
```

**Supported Exchanges** (configured in `config.ini`):
- Binance (default, highest liquidity)
- KuCoin
- Gate.io
- MEXC
- Hyperliquid

**Lifecycle**:
1. **Initialize**: Create shared session, start periodic refresh task
2. **Lazy Load**: Load exchange on first symbol lookup
3. **Periodic Refresh**: Update markets every N hours (background task)
4. **Shutdown**: Cancel refresh task, close exchanges, close shared session

**Error Handling**:
- Network errors: Retry with exponential backoff (`@retry_async` decorator)
- Failed refresh: Attempt reconnection, remove dead exchange from pool
- Rate limits: Enabled by default (`enableRateLimit: true` in config)

### CCXT Integration Details

**CCXT Configuration**:
```python
exchange_config = {
    'enableRateLimit': True,           # Respect exchange rate limits
    'options': {'defaultType': 'spot'},  # Use spot markets
    'session': aiohttp.ClientSession()  # Shared session
}
```

**Symbol Resolution**:
- Checks cached symbols first (fast)
- Loads exchange if not cached
- Iterates through exchanges in priority order (Binance first)

**Market Refresh**:
- Periodic task runs every `MARKET_REFRESH_HOURS`
- Only refreshes already-loaded exchanges (no unnecessary loading)
- Updates `symbols_by_exchange` cache

## Market Data APIs

### CoinGeckoAPI

**Location**: `src/platforms/coingecko.py`

**Purpose**: Fetch global crypto market data, coin metadata, and images.

**Key Features**:
- **SQLite cache** (`cache/coingecko_cache.db`) with `aiohttp-client-cache`
- **Automatic cache expiry** (configurable via `expire_after`)
- **Symbol-to-ID mapping** (e.g., "BTC" → "bitcoin")
- **Exchange-aware coin resolution** (prioritizes coins traded on user's exchange)

**Key Methods**:

#### `get_coin_image(base_symbol: str, exchange_name: str, size: Literal['thumb', 'small', 'large']) -> str`
Fetch coin logo URL:
```python
image_url = await coingecko.get_coin_image("BTC", "binance", "small")
# Returns: "https://assets.coingecko.com/coins/images/1/small/bitcoin.png"
```

#### `get_global_market_data(force_refresh: bool) -> Dict[str, Any]`
Fetch global market overview:
```python
global_data = await coingecko.get_global_market_data(force_refresh=False)
# Returns: {
#   "total_market_cap": {...},
#   "total_volume": {...},
#   "market_cap_percentage": {"btc": 45.2, "eth": 18.3},
#   "updated_at": 1234567890
# }
```

#### `get_top_coins_by_dominance(dominance_coins: List[str]) -> List[Dict[str, Any]]`
Fetch market data for top coins:
```python
coins = await coingecko.get_top_coins_by_dominance(["bitcoin", "ethereum", "tether"])
# Returns list of coin objects with price, market cap, volume, 24h change
```

#### `get_defi_market_data() -> Dict[str, Any]`
Fetch DeFi metrics (TVL, volume, market cap):
```python
defi_data = await coingecko.get_defi_market_data()
# Returns: {
#   "defi_market_cap": "100000000000",
#   "eth_market_cap": "300000000000",
#   "defi_to_eth_ratio": "33.33%",
#   "trading_volume_24h": "50000000000"
# }
```

**Caching Strategy**:
- SQLite backend caches HTTP responses
- Global data cached to `data/market_data/coingecko_global.json`
- Update interval: 4 hours (default, configurable)
- Manual refresh: Use `force_refresh=True`

**Symbol Resolution**:
1. Load all coins from `/coins/list` (cached)
2. Build `symbol_to_id_map` (symbol → list of coin IDs)
3. Prioritize coins traded on target exchange
4. Fallback to first match if exchange not found

### CryptoCompareAPI

**Location**: `src/platforms/cryptocompare.py`

**Purpose**: Fetch cryptocurrency news, categories, and supplemental market data.

**Component Architecture**:
- **CryptoCompareNewsAPI**: News fetching & caching
- **CryptoCompareCategoriesAPI**: Category management (Bitcoin, DeFi, NFT, etc.)
- **CryptoCompareMarketAPI**: Price data and coin details
- **CryptoCompareDataProcessor**: Utilities for data processing

**Key Methods**:

#### `get_latest_news(limit: int, max_age_hours: int) -> List[Dict[str, Any]]`
Fetch recent crypto news:
```python
articles = await cryptocompare.get_latest_news(limit=50, max_age_hours=24)
# Returns list of articles with title, body, source, published_on, tags, categories
```

**News Caching**:
- Cache file: `data/news_cache/recent_news.json`
- Update interval: 1 hour (default)
- Automatic staleness detection

#### `get_news_by_category(category: str, limit: int) -> List[Dict[str, Any]]`
Filter news by category (e.g., "Bitcoin", "DeFi"):
```python
articles = await cryptocompare.get_news_by_category("Bitcoin", limit=10)
```

**Category Mapping**:
- Uses word-based categorization (`category_word_map`)
- Categories: Bitcoin, Ethereum, Altcoin, DeFi, NFT, Regulation, etc.

#### `get_categories(force_refresh: bool) -> List[Dict[str, Any]]`
Fetch cryptocurrency categories:
```python
categories = await cryptocompare.get_categories(force_refresh=False)
# Returns: [{"name": "Bitcoin", "coins": ["BTC", "BCH", "BSV"]}, ...]
```

**Category Caching**:
- Cache file: `data/categories.json`
- Update interval: 24 hours (default)

#### `get_multi_price_data(coins: List[str], vs_currencies: List[str]) -> Dict[str, Any]`
Fetch prices for multiple coins:
```python
prices = await cryptocompare.get_multi_price_data(["BTC", "ETH"], ["USD"])
# Returns: {"BTC": {"USD": 50000}, "ETH": {"USD": 3000}}
```

#### `get_coin_details(symbol: str) -> Dict[str, Any]`
Fetch detailed coin information:
```python
details = await cryptocompare.get_coin_details("LINK")
# Returns: {
#   "description": "Chainlink is...",
#   "algorithm": "Ethash",
#   "proof_type": "PoS",
#   "taxonomy": {"asset": "Cryptocurrency", "sector": "Smart Contracts"},
#   "weiss_rating": {"rating": "A-", "tech_adoption": "A", "market_performance": "B+"}
# }
```

**Data Processing**:
- `detect_coins_in_article`: NLP-based ticker extraction from news text
- Filters duplicate articles by title/URL
- Enriches articles with category tags

### AlternativeMeAPI

**Location**: `src/platforms/alternative_me.py`

**Purpose**: Fetch Fear & Greed Index (market sentiment indicator).

**Key Methods**:

#### `get_fear_greed_index(force_refresh: bool) -> Dict[str, Any]`
Fetch current Fear & Greed Index:
```python
index = await alternative_me.get_fear_greed_index(force_refresh=False)
# Returns: {
#   "value": 45,
#   "value_classification": "Neutral",
#   "timestamp": 1234567890,
#   "time": "2025-11-02T12:00:00"
# }
```

**Sentiment Classifications**:
- 0-24: Extreme Fear
- 25-49: Fear
- 50-74: Greed
- 75-100: Extreme Greed

#### `get_historical_fear_greed(days: int) -> List[Dict[str, Any]]`
Fetch historical sentiment data:
```python
history = await alternative_me.get_historical_fear_greed(days=30)
# Returns: List of index values sorted by date (newest first)
```

**Caching**:
- Cache file: `data/market_data/fear_greed_index.json`
- Update interval: 12 hours (default)
- Fallback to cache on API failure

## AI Providers

### BaseApiClient

**Location**: `src/platforms/ai_providers/base.py`

**Purpose**: Shared HTTP logic for all AI provider clients.

**Features**:
- **Session management**: Ensures single session per client
- **Error handling**: Standardized HTTP error responses
- **Context manager support**: `async with GoogleAIClient(...) as client`
- **Timeout handling**: Configurable request timeouts
- **Rate limit detection**: Special handling for 429 errors

**Key Methods**:

#### `_make_post_request(url, headers, payload, model, timeout) -> Optional[Dict[str, Any]]`
Common POST request with retry and error handling:
```python
response = await self._make_post_request(
    url="https://api.example.com/chat",
    headers={"Authorization": f"Bearer {api_key}"},
    payload={"model": "gpt-4", "messages": [...]},
    model="gpt-4",
    timeout=300
)
```

#### `_handle_error_response(response, model) -> Dict[str, Any]`
Parse API error responses:
- 401: Authentication error
- 403: Permission denied
- 404: Model not found
- 429: Rate limit exceeded
- 408/timeout: Request timeout
- 5xx: Server error

**Exception Handling**:
- `asyncio.TimeoutError`: Returns `{"error": "timeout"}`
- `aiohttp.ClientPayloadError`: Returns `{"error": {"code": 502}}`
- `aiohttp.ClientError`: Returns `{"error": {"code": 503}}`

### GoogleAIClient

**Location**: `src/platforms/ai_providers/google.py`

**Purpose**: Google AI Studio/Gemini API client using official SDK (`google-genai`).

**Models Supported**:
- `gemini-2.5-flash` (default, fast)
- `gemini-2.5-pro` (advanced reasoning, paid tier)
- `gemini-1.5-flash` (legacy)

**Key Methods**:

#### `chat_completion(messages, model_config, model) -> Optional[ResponseDict]`
Text-only chat completion:
```python
async with GoogleAIClient(api_key, "gemini-2.5-flash", logger) as client:
    response = await client.chat_completion(
        messages=[
            {"role": "system", "content": "You are a crypto analyst"},
            {"role": "user", "content": "Analyze BTC"}
        ],
        model_config={"temperature": 0.7, "max_tokens": 32768}
    )
    # Returns: {"choices": [{"message": {"content": "...", "role": "assistant"}}]}
```

#### `chat_completion_with_chart_analysis(messages, chart_image, model_config, model) -> Optional[ResponseDict]`
Multimodal chat completion (text + image):
```python
async with GoogleAIClient(api_key, "gemini-2.5-flash", logger) as client:
    response = await client.chat_completion_with_chart_analysis(
        messages=[...],
        chart_image=io.BytesIO(chart_png),  # or file path or bytes
        model_config={"temperature": 0.5, "max_tokens": 16384}
    )
```

**SDK Features**:
- **Official SDK**: Uses `google.genai.Client` (no custom HTTP calls)
- **Async support**: `client.aio.models.generate_content(...)`
- **Multimodal**: Supports text + image input (PNG only)
- **Type safety**: Proper typing with `google.genai.types`

**Message Conversion**:
- Converts OpenAI-style messages to Gemini prompt format
- System messages prefixed with "System:"
- Images added via `types.Part.from_bytes(...)`

**Error Handling**:
- `_handle_exception`: Catches SDK exceptions, logs errors
- Auto-retry via `@retry_api_call` decorator (3 retries, exponential backoff)

### Provider configuration & fallback (top-level -> platforms)

- Respect `config.ini` `[ai_providers]` section:
    - `provider = "local"`: LM Studio only (streaming supported)
    - `provider = "googleai"`: Google AI Studio only (official SDK)
    - `provider = "openrouter"`: OpenRouter only
    - `provider = "all"`: Fallback chain (Google AI → LM Studio → OpenRouter)

- Google paid tier fallback: If `GOOGLE_STUDIO_PAID_API_KEY` is present in `keys.env`, `ModelManager` will prefer paid Google models and auto-fallback on 503 errors (see `ModelManager._invoke_provider()` for implementation reference).

Add any per-provider SDK notes (timeouts, streaming, multimodal) here so this file is authoritative for provider integration and fallback behavior.

### LMStudioClient

**Location**: `src/platforms/ai_providers/lmstudio.py`

**Purpose**: Local inference via LM Studio server (OpenAI-compatible API).

**Key Features**:
- **Local models**: No API key required, runs on localhost
- **Streaming support**: Real-time token streaming
- **OpenAI-compatible**: Uses `/v1/chat/completions` endpoint

**Key Methods**:

#### `chat_completion(model, messages, model_config) -> Optional[ResponseDict]`
Standard chat completion:
```python
async with LMStudioClient("http://localhost:1234", logger) as client:
    response = await client.chat_completion(
        model="local-model",
        messages=[...],
        model_config={"temperature": 0.7}
    )
```

#### `chat_completion_stream(model, messages, model_config) -> AsyncIterator[str]`
Streaming chat completion:
```python
async with LMStudioClient("http://localhost:1234", logger) as client:
    async for token in client.chat_completion_stream("local-model", messages, config):
        print(token, end="", flush=True)
```

**Configuration**:
- Base URL: Configured in `config.ini` (`[ai_providers] lm_studio_url`)
- No API key required
- Model name: Any model loaded in LM Studio

**Stream Handling**:
- Processes Server-Sent Events (SSE)
- Handles `[DONE]` termination signal
- Accumulates delta tokens from `choices[0].delta.content`

### OpenRouterClient

**Location**: `src/platforms/ai_providers/openrouter.py`

**Purpose**: OpenRouter proxy API client (access to 100+ models).

**Models Supported**:
- OpenAI: `openai/gpt-4-turbo`
- Anthropic: `anthropic/claude-3.5-sonnet`
- Meta: `meta-llama/llama-3.1-70b-instruct`
- Mistral: `mistralai/mistral-large`
- Google: `google/gemini-pro`

**Key Methods**:

#### `chat_completion(model, messages, model_config) -> Optional[ResponseDict]`
Standard chat completion:
```python
async with OpenRouterClient(api_key, "https://openrouter.ai/api", logger) as client:
    response = await client.chat_completion(
        model="openai/gpt-4-turbo",
        messages=[...],
        model_config={"temperature": 0.7}
    )
```

#### `chat_completion_with_chart_analysis(model, messages, chart_image, model_config) -> Optional[ResponseDict]`
Multimodal chat completion:
```python
response = await client.chat_completion_with_chart_analysis(
    model="anthropic/claude-3.5-sonnet",
    messages=[...],
    chart_image=chart_bytes,
    model_config={"temperature": 0.5}
)
```

**Image Handling**:
- Converts images to base64
- Uses `data:image/png;base64,<base64_data>` format
- Supports vision-capable models only

#### `chat_completion_with_images(model, messages, images, model_config) -> Optional[ResponseDict]`
Multi-image chat completion:
```python
response = await client.chat_completion_with_images(
    model="anthropic/claude-3.5-sonnet",
    messages=[...],
    images=[image1_bytes, image2_bytes, image3_bytes],
    model_config={"temperature": 0.5}
)
```

**Headers**:
- `Authorization: Bearer <api_key>`
- `HTTP-Referer`: Bot identifier
- `X-Title`: Application name

**Message Conversion**:
- System messages converted to user messages with "System instructions:" prefix
- Multimodal content: `[{"type": "text", "text": "..."}, {"type": "image_url", "image_url": {...}}]`

## Provider Fallback System & ModelManager

**Location**: `src/models/manager.py` (Note: AGENTS.md previously referenced `src/analyzer/prompts/manager.py` - this is outdated)

**Purpose**: Automatic fallback chain across AI providers to ensure analysis resilience.

**Architecture**:
- **Protocol-based**: ModelManager implements `ModelManagerProtocol` from `src/contracts/model_manager.py`
- **Config injection**: ModelManager receives `ConfigProtocol` instance for provider settings, API keys, model names
- **Dependency injection**: ModelManager is created in `app.py` and injected into AnalysisEngine
- **Factory pattern**: Uses `ProviderFactory` to centralize AI client creation logic
- **No Optional fallbacks**: ModelManager is a required parameter (follows project DI guidelines)

### ProviderFactory

**Location**: `src/factories/provider_factory.py`

**Purpose**: Centralized factory for creating AI provider client instances based on configuration.

**Design Benefits**:
- **Single responsibility**: Encapsulates all provider instantiation logic
- **Testable**: Can inject mock factory for testing
- **Maintainable**: Provider creation logic in one place, not scattered across ModelManager
- **Explicit dependencies**: Clear what each provider needs (API keys, URLs, models)

**Key Methods**:

#### `create_google_clients() -> Tuple[Optional[GoogleAIClient], Optional[GoogleAIClient]]`
Create Google AI clients (free tier and optional paid tier):
```python
factory = ProviderFactory(logger, config)
google_client, google_paid_client = factory.create_google_clients()
# Returns: (GoogleAIClient, GoogleAIClient) or (GoogleAIClient, None) or (None, None)
```

#### `create_openrouter_client() -> Optional[OpenRouterClient]`
Create OpenRouter client if API key configured:
```python
openrouter_client = factory.create_openrouter_client()
# Returns: OpenRouterClient or None
```

#### `create_lmstudio_client() -> Optional[LMStudioClient]`
Create LM Studio client for local inference:
```python
lmstudio_client = factory.create_lmstudio_client()
# Returns: LMStudioClient or None
```

#### `create_all_clients() -> dict`
Create all available clients in one call:
```python
clients = factory.create_all_clients()
# Returns: {
#     'google': GoogleAIClient or None,
#     'google_paid': GoogleAIClient or None,
#     'openrouter': OpenRouterClient or None,
#     'lmstudio': LMStudioClient or None
# }
```

**Usage in ModelManager**:
```python
from src.factories import ProviderFactory

class ModelManager(ModelManagerProtocol):
    def __init__(self, logger: Logger, config: "ConfigProtocol") -> None:
        self.logger = logger
        self.config = config
        
        # Use factory to create all clients
        factory = ProviderFactory(logger, config)
        clients = factory.create_all_clients()
        
        self.openrouter_client = clients['openrouter']
        self.google_client = clients['google']
        self.google_paid_client = clients['google_paid']
        self.lm_studio_client = clients['lmstudio']
```

**Constructor**:
```python
def __init__(self, logger: Logger, config: ConfigProtocol) -> None:
    """Initialize ModelManager with logger and config.
    
    Args:
        logger: Logger instance
        config: ConfigProtocol instance for accessing provider settings
    
    Raises:
        ValueError: If config is None
    """
```

**Initialization**:
```python
# In app.py (DiscordCryptoBot.initialize())
from src.utils.loader import config

self.model_manager = ModelManager(self.logger, config)
self.market_analyzer = AnalysisEngine(
    logger=self.logger,
    rag_engine=self.rag_engine,
    coingecko_api=self.coingecko_api,
    model_manager=self.model_manager,  # Required parameter
    config=config,                      # Required parameter
    # ... other dependencies
)
```

**Configuration Usage**:
- `config.PROVIDER`: Primary AI provider ('googleai', 'local', 'openrouter')
- `config.GOOGLE_STUDIO_API_KEY`, `config.GOOGLE_STUDIO_PAID_API_KEY`: Google AI credentials
- `config.OPENROUTER_API_KEY`, `config.OPENROUTER_BASE_URL`: OpenRouter settings
- `config.LM_STUDIO_BASE_URL`, `config.LM_STUDIO_MODEL`: Local LM Studio settings
- `config.get_model_config(model_name)`: Retrieve model-specific configuration (temperature, top_p, max_tokens)

**Protocol Contract** (`src/contracts/model_manager.py`):
```python
class ModelManagerProtocol(Protocol):
    token_counter: TokenCounter  # Regular attribute for token tracking
    
    async def send_prompt_streaming(...) -> str: ...
    async def send_prompt_with_chart_analysis(...) -> str: ...
    def supports_image_analysis(...) -> bool: ...
    def describe_provider_and_model(...) -> Tuple[str, str]: ...
    async def close() -> None: ...
```

**Benefits of Protocol-based Design**:
- Enables dependency injection and testing with mock implementations
- Type-safe without circular import issues (uses TYPE_CHECKING)
- Clear contract definition for what AnalysisEngine requires from AI providers

**Fallback Order** (configured in `config.ini`):
1. **Google AI** (primary, fast and cheap)
2. **LM Studio** (local fallback, no cost)
3. **OpenRouter** (final fallback, access to Claude/GPT-4)

**Configuration**:
```ini
[ai_providers]
provider = "all"  # Enable fallback chain
# OR
provider = "googleai"  # Single provider only
```

**Paid Tier Fallback**:
- If `GOOGLE_STUDIO_PAID_API_KEY` set in `keys.env`
- Auto-fallback to paid tier on 503 errors (rate limit/quota exceeded)
- Transparent to user (logged only)

**Error Handling**:
```python
# ModelManager._invoke_provider() logic:
try:
    return await google_client.chat_completion(...)
except RateLimitError:
    if paid_key_available:
        return await google_paid_client.chat_completion(...)
    else:
        # Fall through to LM Studio
        return await lmstudio_client.chat_completion(...)
```

## Integration with Analysis System

### Usage in AnalysisEngine

**Location**: `src/analyzer/core/analysis_engine.py`

**Constructor Signature** (updated with DI):
```python
class AnalysisEngine:
    def __init__(
        self,
        logger: Logger,
        rag_engine: RagEngine,
        coingecko_api: CoinGeckoAPI,
        model_manager: ModelManagerProtocol,  # Required parameter (Protocol type)
        alternative_me_api: AlternativeMeAPI = None,
        cryptocompare_api = None,
        discord_notifier = None,
        format_utils = None,
        data_processor = None
    ) -> None:
        # model_manager is required - raises ValueError if None
        if model_manager is None:
            raise ValueError("model_manager is a required parameter and cannot be None")
        self.model_manager = model_manager
        # ...
```

**Usage Example**:
```python
    async def analyze_market(self, symbol: str) -> Dict[str, Any]:
        # 1. Find exchange supporting symbol
        exchange, exchange_id = await self.exchange_manager.find_symbol_exchange(symbol)
        
        # 2. Fetch OHLCV data from exchange
        ohlcv = await exchange.fetch_ohlcv(symbol, "1h", limit=500)
        
        # 3. Get market context (global data, sentiment, news)
        global_data = await self.coingecko.get_global_market_data()
        fear_greed = await self.alternative_me.get_fear_greed_index()
        news = await self.cryptocompare.get_latest_news(limit=50)
        
        # 4. Calculate indicators
        indicators = self.technical_calculator.get_indicators(ohlcv)
        
        # 5. Detect patterns
        patterns = self.pattern_analyzer.detect_patterns(ohlcv, indicators)
        
        # 6. Build AI prompt with all context
        prompt = self.prompt_builder.build_prompt(
            symbol, indicators, patterns, global_data, fear_greed, news
        )
        
        # 7. Get AI analysis (with fallback)
        analysis = await self.model_manager.get_analysis(prompt)
        
        return analysis
```

### Initialization Order

**Location**: `src/app.py` (DiscordCryptoBot.initialize())

```python
async def initialize(self):
    # 1. Initialize market data APIs
    await self.coingecko.initialize()
    await self.cryptocompare.initialize()
    await self.alternative_me.initialize()
    
    # 2. Initialize exchange manager
    await self.exchange_manager.initialize()
    
    # 3. Initialize Discord bot (depends on market APIs)
    await self.discord_notifier.initialize()
    
    # 4. Initialize RAG engine (depends on news APIs)
    await self.rag_engine.initialize()
```

**Shutdown Order** (reverse):
```python
async def shutdown(self):
    await self.discord_notifier.shutdown()
    await self.rag_engine.shutdown()
    await self.exchange_manager.shutdown()
    await self.cryptocompare.close()
    # Note: CoinGecko/AlternativeMe use aiohttp-client-cache (auto-close)
```

## Configuration

### config.ini

```ini
[general]
timeframe = 4h

[exchanges]
supported_exchanges = binance,kucoin,gateio,mexc,hyperliquid
market_refresh_hours = 24

[coingecko]
cache_expiry = -1  # Never expire (manual control)
update_interval_hours = 4

[cryptocompare]
news_update_hours = 1
categories_update_hours = 24

[alternative_me]
fear_greed_update_hours = 12

[ai_providers]
provider = all  # "all", "googleai", "local", "openrouter"
lm_studio_url = http://localhost:1234
google_model = gemini-2.5-flash
openrouter_model = openai/gpt-4-turbo
```

### keys.env

```env
# Discord
DISCORD_BOT_TOKEN=your_bot_token_here

# AI Providers
GOOGLE_STUDIO_API_KEY=your_google_api_key_here
GOOGLE_STUDIO_PAID_API_KEY=your_paid_google_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Note: LM Studio requires no API key (local)
```

## Common Patterns

### Fetch Market Overview

```python
# Global market cap, volume, dominance
global_data = await coingecko.get_global_market_data()

# Top coins by market cap
top_coins = await coingecko.get_top_coins_by_dominance(["bitcoin", "ethereum", "tether"])

# DeFi metrics
defi_data = await coingecko.get_defi_market_data()

# Sentiment
fear_greed = await alternative_me.get_fear_greed_index()
```

### Validate Trading Pair

```python
exchange, exchange_id = await exchange_manager.find_symbol_exchange("BTC/USDT")
if not exchange:
    # Symbol not found on any supported exchange
    return error_message("Symbol BTC/USDT not found")
```

### Fetch News Context

```python
# All recent news
news = await cryptocompare.get_latest_news(limit=50, max_age_hours=24)

# Category-specific news
bitcoin_news = await cryptocompare.get_news_by_category("Bitcoin", limit=10)
```

### Get AI Analysis with Fallback

```python
# ModelManager handles fallback automatically
analysis = await model_manager.get_analysis(
    messages=[
        {"role": "system", "content": "You are a crypto analyst"},
        {"role": "user", "content": prompt}
    ],
    model_config={"temperature": 0.7, "max_tokens": 32768}
)
```

## Error Handling

### Logging Philosophy

**Layered Error Logging**:
The system uses a layered approach to error logging to avoid duplication and provide clear context:

1. **Low-level (base.py)**: Logs at DEBUG level - implementation details only
   - HTTP status codes, raw error responses
   - Network errors, timeouts, connection failures
   - These are diagnostic details, not user-facing errors

2. **Mid-level (provider clients)**: Logs provider-specific errors at ERROR level
   - Google AI, OpenRouter, LM Studio failures
   - Includes model name and operation context
   - Example: `"OpenRouter chart analysis failed: model=kimi-k2-thinking, error=404"`

3. **Top-level (analysis_engine.py)**: Logs user-facing warnings/errors
   - Clear context about what failed and what fallback is happening
   - Example: `"Chart analysis failed for BTC/USDT via OPENROUTER (kimi-k2-thinking): Model not found. Retrying with text-only analysis..."`
   - Success confirmation after fallback: `"Text-only analysis completed successfully for BTC/USDT"`

**Error Flow Example** (Chart Analysis Failure):
```
1. OpenRouter API returns 404 → base.py logs DEBUG: "API Error for model X: Status 404"
2. OpenRouterClient returns error dict → manager.py logs ERROR: "OpenRouter chart analysis failed: model=X, error=404"
3. ModelManager raises ValueError → analysis_result_processor.py re-raises (no log)
4. AnalysisEngine catches ValueError → logs WARNING with full context + retries text-only
5. If text-only succeeds → logs INFO: "Text-only analysis completed successfully"
```

### Network Errors

All API clients use `@retry_api_call` decorator:
```python
@retry_api_call(max_retries=3, initial_delay=1, backoff_factor=2, max_delay=30)
async def get_data(...):
    # Automatically retries on network errors
    # Exponential backoff: 1s, 2s, 4s
```

### Chart Analysis Fallback

**Chart Analysis → Text-only Fallback**:
When chart analysis fails (model doesn't support images, API error, etc.):
1. `ModelManager.send_prompt_with_chart_analysis()` raises `ValueError`
2. `AnalysisResultProcessor` re-raises without logging (avoids duplicate)
3. `AnalysisEngine` catches, logs WARNING with full context, rebuilds prompts without chart flag
4. Retries with `chart_image=None` (text-only analysis)
5. Logs INFO on success

**Why this approach?**:
- Single clear warning to user with all context (symbol, provider, model, error)
- No duplicate "Chart analysis failed" messages at multiple levels
- Success confirmation so user knows fallback worked

### Google AI SDK Warnings

**Non-text Response Parts**:
Some Google AI models (e.g., Gemini with thinking mode) return additional response parts like `thought_signature` that are not text content. The Google GenAI SDK logs a warning when accessing `response.text` if non-text parts exist.

**Our handling**:
- `GoogleAIClient._extract_text_from_response()` manually extracts text parts
- Logs DEBUG message about non-text parts (informational, not an error)
- Returns concatenated text content only
- User sees: `"Google AI response contains non-text parts: ['ThoughtSignature']. Extracting text content only."`

### Rate Limits

**CCXT**:
- Enabled by default (`enableRateLimit: true`)
- Automatic delay between requests

**CoinGecko**:
- Free tier: 10-50 calls/minute (varies by endpoint)
- SQLite cache reduces API calls
- Update interval: 4 hours (default)

**CryptoCompare**:
- Free tier: 100,000 calls/month
- News caching: 1 hour
- Categories caching: 24 hours

**AI Providers**:
- Google AI: 15 RPM (free), 1500 RPM (paid)
- OpenRouter: Varies by model (pay-as-you-go)
- LM Studio: No limits (local)

### Fallback Strategies

**Exchange Manager**:
- If exchange fails to load: Try next exchange in list
- If all exchanges fail: Return None (symbol not found)

**AI Providers**:
- Google AI → LM Studio → OpenRouter
- If all fail: Return error to user

**Market Data**:
- If API fails: Use cached data (if available)
- If cache stale: Return default/empty data with warning

## Troubleshooting

**Exchange connection errors**:
- Check CCXT version compatibility
- Verify exchange API status (e.g., maintenance)
- Check rate limits (enable debug logging)

**CoinGecko cache issues**:
- Delete `cache/coingecko_cache.db` to clear cache
- Check disk space (cache can grow large)

**CryptoCompare news not updating**:
- Delete `data/news_cache/recent_news.json`
- Check `news_update_hours` config (too high?)
- Verify API key (if using paid tier)

**AI provider fallback not working**:
- Check `provider = "all"` in config
- Verify all API keys in `keys.env`
- Enable debug logging to see fallback chain

**LM Studio connection refused**:
- Ensure LM Studio server running
- Check `lm_studio_url` in config (default: `http://localhost:1234`)
- Verify model loaded in LM Studio UI

## Files for Deeper Context

- **Exchange integration**: `src/platforms/exchange_manager.py`
- **Market data**: `src/platforms/coingecko.py`, `cryptocompare.py`, `alternative_me.py`
- **AI providers**: `src/platforms/ai_providers/base.py`, `google.py`, `lmstudio.py`, `openrouter.py`
- **Provider fallback**: `src/analyzer/prompts/manager.py` (ModelManager)
- **Integration usage**: `src/analyzer/core/analysis_engine.py`
- **Configuration**: `config/config.ini`, `keys.env.example`
