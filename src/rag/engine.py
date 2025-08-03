import asyncio
import json
import re
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set, Tuple, TypedDict, Union

from config.config import (
    RAG_UPDATE_INTERVAL_HOURS, RAG_CATEGORIES_UPDATE_INTERVAL_HOURS,
    RAG_COINGECKO_UPDATE_INTERVAL_HOURS, RAG_INITIAL_KNOWN_TICKERS,
    RAG_IMPORTANT_CATEGORIES, RAG_NON_TICKER_CATEGORIES
)
from src.platforms.coingecko import CoinGeckoAPI
from src.platforms.cryptocompare import CryptoCompareAPI
from src.logger.logger import Logger
from src.rag.filehandler import RagFileHandler
from src.utils.token_counter import TokenCounter


class CacheData(TypedDict):
    timestamp: str
    data: Any


class NewsArticle(TypedDict, total=False):
    id: str
    title: str
    body: str
    published_on: Union[int, float, str]
    categories: str
    tags: str
    source: str
    detected_coins: str
    url: str


class RagEngine:
    def __init__(
        self,
        logger: Logger,
        token_counter: TokenCounter,
        coingecko_api: Optional[CoinGeckoAPI] = None,
        cryptocompare_api: Optional[CryptoCompareAPI] = None,
        symbol_manager=None
    ):
        self.logger = logger
        self.symbol_manager = symbol_manager
        self.token_counter = token_counter
        self.file_handler = RagFileHandler(logger=self.logger)
        
        # API clients with dependency injection
        self.coingecko_api = coingecko_api
        self.cryptocompare_api = cryptocompare_api

        # Update timestamps
        self.last_update: Optional[datetime] = None
        self.categories_last_update: Optional[datetime] = None
        self.coingecko_last_update: Optional[datetime] = None

        # Update intervals from config
        self.update_interval = timedelta(hours=RAG_UPDATE_INTERVAL_HOURS)
        self.categories_update_interval = timedelta(hours=RAG_CATEGORIES_UPDATE_INTERVAL_HOURS)
        self.coingecko_update_interval = timedelta(hours=RAG_COINGECKO_UPDATE_INTERVAL_HOURS)

        # Task management
        self._periodic_update_task = None

        # Data storage
        self.news_database: List[NewsArticle] = []
        self.category_index: Dict[str, List[int]] = defaultdict(list)
        self.tag_index: Dict[str, List[int]] = defaultdict(list)
        self.coin_index: Dict[str, List[int]] = defaultdict(list)
        self.keyword_index: Dict[str, List[int]] = defaultdict(list)
        self.category_word_map: Dict[str, str] = {}
        self.api_categories: List[Dict[str, Any]] = []
        self.latest_article_urls: Dict[str, str] = {}
        self.current_market_overview: Optional[Dict[str, Any]] = None

        # Configuration data
        self.tickers_file = self.file_handler.get_tickers_file_path()

        # Use config for initial sets
        self.known_crypto_tickers: Set[str] = set(RAG_INITIAL_KNOWN_TICKERS)
        self.important_categories: Set[str] = set(RAG_IMPORTANT_CATEGORIES)
        self.non_ticker_categories: Set[str] = set(RAG_NON_TICKER_CATEGORIES)

        # Closure flag
        self._is_closed = False

    async def initialize(self) -> None:
        """Initialize RAG engine and load cached data"""
        try:
            # Initialize API clients if they weren't provided
            if self.coingecko_api is None:
                self.coingecko_api = CoinGeckoAPI(logger=self.logger)
                await self.coingecko_api.initialize()
                
            if self.cryptocompare_api is None:
                self.cryptocompare_api = CryptoCompareAPI(logger=self.logger)
                await self.cryptocompare_api.initialize()
                
            # Load market overview data
            market_overview_file = self.file_handler.get_market_overview_path()
            self.current_market_overview = self.file_handler.load_json_file(market_overview_file)
            await self._load_known_tickers()

            # Ensure categories are up to date
            await self._ensure_categories_updated()

            # Load news database
            self.news_database = self.file_handler.load_news_articles()

            if self.news_database:
                self.last_update = datetime.now()
                self._build_indices()
                self.logger.debug(f"Loaded {len(self.news_database)} recent news articles")

            await self.update_known_tickers()

            if len(self.news_database) < 10:
                await self.refresh_market_data()
                self.last_update = datetime.now()
        except Exception as e:
            self.logger.exception(f"Error initializing RAG engine: {e}")
            self.news_database = []

    async def fetch_cryptocompare_categories(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Fetch cryptocurrency categories from CryptoCompare API"""
        if self.cryptocompare_api is None:
            self.logger.error("CryptoCompare API client not initialized")
            return []
            
        response = await self.cryptocompare_api.get_categories(force_refresh=force_refresh)
        
        # Debug logging to inspect the returned data
        self.logger.debug(f"Categories response type: {type(response)}")
        
        # Extract categories from the response structure
        categories = []
        
        if response:
            # Handle direct list of categories
            if isinstance(response, list):
                categories = response
                self.logger.debug(f"Found {len(categories)} categories in list format")
            # Handle dictionary with nested structure
            elif isinstance(response, dict):
                if "Response" in response and "Data" in response and response["Response"] == "Success":
                    categories = response["Data"]
                    self.logger.debug(f"Found categories in Response/Data structure: {len(categories) if isinstance(categories, list) else 'dict'}")
                elif "Data" in response:
                    categories = response["Data"]
                    self.logger.debug(f"Found categories in Data key: {len(categories) if isinstance(categories, list) else 'dict'}")
                else:
                    categories = response
                    self.logger.debug("Using response directly as categories")
            
        if categories:
            self.categories_last_update = datetime.now()
            
        return categories

    def _process_api_categories(self, api_categories: List[Dict[str, Any]]) -> None:
        """Process API categories and update internal indices"""
        if not api_categories:
            return
        
        self.logger.debug(f"Processing {len(api_categories) if isinstance(api_categories, list) else 'unknown number of'} categories")
        
        # Store the API categories
        self.api_categories = api_categories
        
        # Clear existing maps before processing
        self.category_word_map = {}
        
        general_categories = set()
        ticker_categories = set()

        # Handle list of category objects from API
        if isinstance(api_categories, list):
            for cat in api_categories:
                if isinstance(cat, dict) and 'categoryName' in cat:
                    category_name = cat['categoryName'].upper()
                    
                    # Decide if it's a ticker category or general category
                    if len(category_name) <= 5 and category_name.isupper() and ' ' not in category_name:
                        if category_name not in self.non_ticker_categories:
                            ticker_categories.add(category_name)
                    else:
                        general_categories.add(category_name)
                    
                    # Process associated words
                    word_sources = ['wordsAssociatedWithCategory', 'includedPhrases']
                    for word_source in word_sources:
                        if word_source in cat and isinstance(cat[word_source], list):
                            for word in cat[word_source]:
                                if isinstance(word, str) and len(word) > 2:
                                    self.category_word_map[word.lower()] = category_name
        
        self.non_ticker_categories.update(general_categories)
        self.known_crypto_tickers.update(ticker_categories)

        self.logger.debug(f"Processed {len(general_categories)} general categories and {len(ticker_categories)} ticker categories")
        self.logger.debug(f"Updated category-word map with {len(self.category_word_map)} entries")

    async def _load_known_tickers(self) -> None:
        """Load known tickers from disk"""
        data = self.file_handler.load_json_file(self.tickers_file)
        if data:
            saved_tickers = set(data.get("tickers", []))
            new_count = len(saved_tickers - self.known_crypto_tickers)
            self.known_crypto_tickers.update(saved_tickers)
            self.logger.debug(f"Loaded {len(saved_tickers)} tickers from disk ({new_count} new)")

    def _build_indices(self) -> None:
        """Build search indices from news database"""
        self.category_index.clear()
        self.tag_index.clear()
        self.coin_index.clear()
        self.keyword_index.clear()

        for i, article in enumerate(self.news_database):
            # Index categories
            categories = article.get('categories', '').split('|')
            for category in categories:
                if category:
                    self.category_index[category.lower()].append(i)

                    if category in self.known_crypto_tickers:
                        self.coin_index[category.lower()].append(i)

            # Index tags
            tags = article.get('tags', '').split('|')
            for tag in tags:
                if tag:
                    self.tag_index[tag.lower()].append(i)

            # Detect and index coins
            coins_mentioned = self._detect_coins_in_article(article)
            if coins_mentioned:
                article['detected_coins'] = '|'.join(coins_mentioned)
                for coin in coins_mentioned:
                    self.coin_index[coin.lower()].append(i)

            # Index title/body keywords
            title = article.get('title', '').lower()
            body = article.get('body', '').lower()

            # Index category-associated words
            for word, category in self.category_word_map.items():
                if re.search(rf'\b{re.escape(word)}\b', title) or re.search(rf'\b{re.escape(word)}\b', body):
                    self.keyword_index[word].append(i)
                    if category.upper() in self.known_crypto_tickers:
                        self.coin_index[category.lower()].append(i)

            # Index important title words
            title_words = set(re.findall(r'\b[a-z0-9]{3,15}\b', title))
            for word in title_words:
                if len(word) > 2 and word not in ['the', 'and', 'for', 'with']:
                    self.keyword_index[word].append(i)

    async def update_if_needed(self) -> bool:
        """Update market data if needed based on time intervals"""
        if not self.last_update:
            self.logger.debug("No previous update, refreshing market knowledge base")
            try:
                await self.refresh_market_data()
                self.last_update = datetime.now()
                return True
            except Exception as e:
                self.logger.error(f"Failed to update market knowledge: {e}")
                return False

        time_since_update = datetime.now() - self.last_update
        if time_since_update > self.update_interval:
            self.logger.debug(f"Last update was {time_since_update.total_seconds()/60:.1f} minutes ago, refreshing market knowledge")
            try:
                await self.refresh_market_data()
                self.last_update = datetime.now()
                return True
            except Exception as e:
                self.logger.error(f"Failed to update market knowledge: {e}")
                return False

        try:
            categories_updated = await self._ensure_categories_updated()
            if categories_updated:
                self._build_indices()
        except Exception as e:
            self.logger.error(f"Failed to update categories: {e}")

        return False

    async def refresh_market_data(self) -> None:
        """Refresh all market data from external sources"""
        await self._ensure_categories_updated()

        self.logger.debug("Starting fetch of news data")
        
        # Always fetch news
        try:
            articles = await self._fetch_crypto_news()
        except Exception as e:
            self.logger.error(f"Error fetching crypto news: {e}")
            articles = self.file_handler.load_fallback_articles(max_age_hours=72)
            if articles:
                self.logger.info(f"Using {len(articles)} cached articles as fallback after fetch error")
            else:
                self.logger.warning("No fallback articles available after fetch error.")
    
        # Only fetch market overview if needed
        market_overview = None
        should_update_market = False
        
        if self.current_market_overview is None:
            should_update_market = True
        else:
            # Check if market overview is older than 24 hours
            timestamp_field = self.current_market_overview.get('published_on', 
                                                             self.current_market_overview.get('timestamp', 0))
            timestamp = self._normalize_timestamp(timestamp_field)
            
            if timestamp:
                data_time = datetime.fromtimestamp(timestamp)
                current_time = datetime.now()
                
                if current_time - data_time > timedelta(hours=24):
                    self.logger.debug(f"Market overview data is older than 24 hours, refreshing")
                    should_update_market = True
    
        if should_update_market:
            try:
                self.logger.debug("Fetching market overview data")
                market_overview = await self._fetch_market_overview()
                if market_overview is None:
                    # Handle None return value specifically
                    self.logger.warning("No market overview data was available from data sources")
                    # Keep using current overview if available
                    market_overview = self.current_market_overview
            except Exception as e:
                self.logger.error(f"Error fetching market overview: {e}")
                market_overview = self.current_market_overview
                self.logger.warning("Market overview fetch failed, retaining previous overview if available.")
    
        # Process articles as before
        if articles:
            recent_articles = self.file_handler.filter_recent_articles(articles)
            
            existing_ids = {article.get('id') for article in self.news_database if article.get('id')}
            unique_articles = [art for art in recent_articles if art.get('id') and art.get('id') not in existing_ids]
            
            if unique_articles:
                self.logger.debug(f"Found {len(unique_articles)} new articles")
                combined_articles = self.news_database + unique_articles
                
                combined_articles.sort(key=lambda x: self._get_article_timestamp(x), reverse=True)
                
                self.news_database = self.file_handler.filter_recent_articles(combined_articles)
                
                self.file_handler.save_news_articles(self.news_database)
                
                self._build_indices()
                
                self.logger.debug(f"Updated news database with {len(self.news_database)} recent articles")
            else:
                self.logger.debug("No new articles to add or only duplicates found")
    
        # Update market overview if we have new data
        if market_overview and market_overview != self.current_market_overview:
            market_overview_file = self.file_handler.get_market_overview_path()
            self.file_handler.save_json_file(market_overview_file, market_overview)
            self.current_market_overview = market_overview
            self.logger.debug("Market overview updated and saved.")

    async def _fetch_crypto_news(self) -> List[Dict[str, Any]]:
        """Fetch crypto news from external API"""
        if self.cryptocompare_api is None:
            self.logger.error("CryptoCompare API client not initialized")
            return []
            
        try:
            # Use the CryptoCompare API client to fetch news
            articles = await self.cryptocompare_api.get_latest_news(limit=50, max_age_hours=24)
            
            if articles:
                # Detect coins in articles
                for article in articles:
                    coins_mentioned = await self.cryptocompare_api.detect_coins_in_article(
                        article, self.known_crypto_tickers)
                    if coins_mentioned:
                        article['detected_coins'] = '|'.join(coins_mentioned)
                        
                self.logger.debug(f"Fetched {len(articles)} recent news articles from CryptoCompare")
                return articles
            else:
                self.logger.warning("No articles returned from CryptoCompare API")
                fallback_articles = self.file_handler.load_fallback_articles(max_age_hours=72)
                if fallback_articles:
                    self.logger.info(f"Using {len(fallback_articles)} cached articles as fallback")
                    return fallback_articles
                return []
                
        except Exception as e:
            self.logger.error(f"Error fetching CryptoCompare news: {e}")
            fallback_articles = self.file_handler.load_fallback_articles(max_age_hours=72)
            if fallback_articles:
                self.logger.info(f"Using {len(fallback_articles)} cached articles as fallback after exception")
                return fallback_articles
            return []

    def _detect_coins_in_article(self, article: Dict[str, Any]) -> Set[str]:
        """Detect cryptocurrency mentions in article content (Optimized)"""
        coins_mentioned = set()
        title = article.get('title', '').upper()
        body = article.get('body', '').upper() if len(article.get('body', '')) < 10000 else article.get('body', '')[:10000].upper()
        categories = article.get('categories', '').split('|')

        for category in categories:
            cat_upper = category.upper()
            if cat_upper in self.known_crypto_tickers:
                coins_mentioned.add(cat_upper)

        potential_tickers_regex = r'\b[A-Z]{2,6}\b'
        potential_tickers_in_title = set(re.findall(potential_tickers_regex, title))
        potential_tickers_in_body = set(re.findall(potential_tickers_regex, body))

        for ticker in potential_tickers_in_title:
            if ticker in self.known_crypto_tickers:
                coins_mentioned.add(ticker)

        for ticker in potential_tickers_in_body:
            if ticker in self.known_crypto_tickers:
                coins_mentioned.add(ticker)

        title_lower = title.lower()
        body_lower = body.lower()
        if 'bitcoin' in title_lower or 'bitcoin' in body_lower or 'BTC' in coins_mentioned:
            coins_mentioned.add('BTC')
        if 'ethereum' in title_lower or 'ethereum' in body_lower or 'ETH' in coins_mentioned:
            coins_mentioned.add('ETH')

        return coins_mentioned

    async def _fetch_market_overview(self) -> Optional[Dict[str, Any]]:
        """Fetch overall market data from various sources concurrently"""
        overview = {"timestamp": datetime.now().isoformat(), "summary": "CRYPTO MARKET OVERVIEW"}
        
        if not self.coingecko_api:
            self.logger.error("CoinGecko API client not initialized for market overview fetch")
            return None
            
        try:
            # Get global market data from CoinGecko first to access dominance data
            coingecko_data = await self.coingecko_api.get_global_market_data()
            
            # Extract top coins by dominance, excluding stablecoins
            top_coins = []
            stablecoins = ["USDT", "USDC", "BUSD", "DAI", "TUSD", "UST", "USDP", "GUSD"]
            
            if coingecko_data and "dominance" in coingecko_data:
                # Sort coins by dominance percentage
                sorted_dominance = sorted(
                    coingecko_data["dominance"].items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )
                
                # Get top non-stablecoin coins
                for coin, _ in sorted_dominance:
                    if coin.upper() not in stablecoins:
                        top_coins.append(coin.upper())
                        if len(top_coins) >= 5:  # Get top 5 non-stablecoin coins
                            break
            
            # Fallback to default list if we couldn't get top coins
            if not top_coins:
                self.logger.warning("Could not determine top coins by dominance, using defaults")
                top_coins = ["BTC", "ETH", "BNB", "XRP", "ADA"]
            
            # Try to get price data using CCXT first
            price_data = None
            
            # If we have a symbol_manager, use it to get an exchange and create a DataFetcher
            if self.symbol_manager and self.symbol_manager.exchanges:
                from src.analyzer.data_fetcher import DataFetcher
                
                # Try to use Binance first if available, otherwise use any available exchange
                exchange = None
                if 'binance' in self.symbol_manager.exchanges:
                    exchange = self.symbol_manager.exchanges['binance']
                    self.logger.debug("Using Binance exchange for market data")
                else:
                    # Use first available exchange that supports fetch_tickers
                    for exchange_id, exch in self.symbol_manager.exchanges.items():
                        if exch.has.get('fetchTickers', False):
                            exchange = exch
                            self.logger.debug(f"Using {exchange_id} exchange for market data")
                            break
                
                if exchange:
                    # Create a DataFetcher with the selected exchange
                    data_fetcher = DataFetcher(exchange=exchange, logger=self.logger)
                    
                    # Use top coins from dominance data with USDT as quote currency
                    symbols = [f"{coin}/USDT" for coin in top_coins]
                    self.logger.debug(f"Fetching data for top coins: {symbols}")
                    
                    try:
                        price_data = await data_fetcher.fetch_multiple_tickers(symbols)
                        self.logger.debug(f"Fetched price data for {len(symbols)} symbols using CCXT")
                    except Exception as e:
                        self.logger.warning(f"Failed to fetch ticker data via CCXT: {e}")
            
            # Fallback to CryptoCompare if we couldn't get data from CCXT
            if (not price_data or not price_data.get("RAW")) and self.cryptocompare_api:
                self.logger.debug("Falling back to CryptoCompare API for price data")
                price_data = await self.cryptocompare_api.get_multi_price_data(coins=top_coins)
            
            # Process price data
            if price_data and "RAW" in price_data:
                overview["top_coins"] = {}
                for coin, values in price_data["RAW"].items():
                    quote_data = None
                    
                    # Try to get USD data first, then USDT if USD not available
                    if "USD" in values:
                        quote_data = values["USD"]
                        quote_currency = "USD"
                    elif "USDT" in values:
                        quote_data = values["USDT"]
                        quote_currency = "USDT"
                    
                    if quote_data:
                        coin_overview = {
                            "price": quote_data.get("PRICE", 0),
                            "change24h": quote_data.get("CHANGEPCT24HOUR", 0),
                            "volume24h": quote_data.get("VOLUME24HOUR", 0),
                            "mcap": quote_data.get("MKTCAP")
                        }
                        
                        # Add additional data if available
                        if "VWAP" in quote_data and quote_data["VWAP"]:
                            coin_overview["vwap"] = quote_data["VWAP"]
                            
                        if "BID" in quote_data and "ASK" in quote_data:
                            coin_overview["bid"] = quote_data["BID"]
                            coin_overview["ask"] = quote_data["ASK"]
                            
                        overview["top_coins"][coin] = coin_overview
            
            # Add CoinGecko global market data
            if coingecko_data:
                overview.update(coingecko_data)
                self.coingecko_last_update = datetime.now()
            
            if overview.get("top_coins") or overview.get("market_cap"):
                overview["id"] = "market_overview"
                overview["title"] = "Crypto Market Overview"
                
                # Add descriptive comments to help models understand the data structure
                overview["_description"] = {
                    "top_coins": "Price and metrics for leading cryptocurrencies",
                    "market_cap": "Total cryptocurrency market capitalization and changes",
                    "volume": "Total trading volume across all markets",
                    "dominance": "Percentage share of total market cap by leading assets",
                    "stats": "General statistics about cryptocurrency markets"
                }
                
                self.logger.debug("Market overview data fetched/processed.")
                return overview
            else:
                self.logger.error("Failed to fetch any market overview data.")
                return None
                
        except Exception as e:
            self.logger.error(f"Error fetching market overview: {e}")
            return None

    def extract_base_coin(self, symbol: str) -> str:
        """Extract base coin from trading pair symbol"""
        if '/' in symbol:
            base = symbol.split('/')[0]
        else:
            base = symbol

        return base

    def _search_by_coin(self, coin: str) -> List[int]:
        """Search for articles mentioning a specific coin"""
        coin_lower = coin.lower()

        if coin_lower in self.coin_index:
            return self.coin_index[coin_lower]

        if coin_lower in self.category_index:
            return self.category_index[coin_lower]

        results = []
        for i, article in enumerate(self.news_database):
            title = article.get('title', '').lower()
            body = article.get('body', '').lower()

            if coin_lower in title or f" {coin_lower} " in f" {body} ":
                results.append(i)

        return results

    async def _keyword_search(self, query: str, symbol: Optional[str] = None) -> List[Tuple[int, float]]:
        """Search for articles matching keywords with relevance scores"""
        query = query.lower()
        keywords = set(re.findall(r'\b\w{3,15}\b', query))

        coin = None
        if symbol:
            coin = self.extract_base_coin(symbol).upper()

        scores: List[Tuple[int, float]] = []
        current_time = datetime.now().timestamp()

        for i, article in enumerate(self.news_database):
            score = self._calculate_article_relevance(article, keywords, query, coin, current_time)
            if score > 0:
                scores.append((i, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores

    def _calculate_article_relevance(self, article: Dict[str, Any], keywords: Set[str],
                                     query: str, coin: Optional[str],
                                     current_time: float) -> float:
        """Calculate article relevance score based on various factors"""
        score = 0.0

        title = article.get('title', '').lower()
        body = article.get('body', '').lower()
        categories = article.get('categories', '').lower()
        tags = article.get('tags', '').lower()
        detected_coins = article.get('detected_coins', '').lower()

        pub_time = self._get_article_timestamp(article)
        time_diff = current_time - pub_time
        recency = max(0.0, 1.0 - (time_diff / (24 * 3600)))

        for keyword in keywords:
            if keyword in title:
                score += 10
            if keyword in body:
                score += 3
            if keyword in categories:
                score += 5
            if keyword in tags:
                score += 4

        for word, category in self.category_word_map.items():
            if word in query and category.lower() in categories:
                score += 5

        if coin:
            coin_lower = coin.lower()
            if coin_lower in categories:
                score += 15
            if re.search(rf'\b{re.escape(coin_lower)}\b', title):
                score += 15
            if re.search(rf'\b{re.escape(coin_lower)}\b', body):
                score += 5
            if coin_lower in detected_coins:
                score += 8

            if title.startswith(coin_lower) or f"{coin_lower} price" in title:
                score += 20

        for category in self.important_categories:
            if category.lower() in categories:
                score += 3

        final_score = score * (0.3 + 0.7 * recency)

        if article.get('id') == 'market_overview':
            final_score += 10

        return final_score

    def _get_article_timestamp(self, article: Dict[str, Any]) -> float:
        """Extract timestamp from article in a consistent format"""
        pub_time = 0.0
        published_on = article.get('published_on', 0)

        if isinstance(published_on, (int, float)):
            pub_time = float(published_on)
        elif isinstance(published_on, str):
            try:
                if published_on.endswith('Z'):
                    published_on = published_on[:-1] + '+00:00'
                pub_time = datetime.fromisoformat(published_on).timestamp()
            except ValueError:
                try:
                    self.logger.warning(f"Could not parse timestamp string: {published_on}")
                    pub_time = 0.0
                except Exception as e:
                    self.logger.error(f"Error parsing timestamp string '{published_on}': {e}")
                    pub_time = 0.0
        elif published_on is None:
            pub_time = 0.0
        else:
            self.logger.warning(f"Unexpected type for published_on: {type(published_on)}, value: {published_on}")
            pub_time = 0.0
        return pub_time

    def _category_search(self, category: str) -> List[int]:
        """Search for articles in a specific category"""
        return self.category_index.get(category.lower(), [])

    def _tag_search(self, tag: str) -> List[int]:
        """Search for articles with a specific tag"""
        return self.tag_index.get(tag.lower(), [])
    
    async def retrieve_context(self, query: str, symbol: str, k: int = 3, max_tokens: int = 8096) -> str:
        """Retrieve relevant context for a query with token limiting
        
        Note: Market overview data is handled separately by PromptBuilder._build_market_overview_section()
        This method only returns news articles and market context to avoid redundancy.
        """
        if not self.news_database:
            self.logger.warning("News database is empty")
            return ""

        try:
            rebuild_indices = await self._ensure_categories_updated()
            if rebuild_indices:
                self._build_indices()

            if not self.last_update or datetime.now() - self.last_update > timedelta(minutes=30):
                await self.update_if_needed()

            context_parts = []
            total_tokens = 0
            self.latest_article_urls = {}

            scores = await self._keyword_search(query, symbol)
            relevant_indices = [idx for idx, _ in scores[:k*2]]

            if symbol and len(relevant_indices) < k:
                coin = self.extract_base_coin(symbol)
                coin_indices = self._search_by_coin(coin)
                for idx in coin_indices:
                    if idx not in relevant_indices:
                        relevant_indices.append(idx)
                        if len(relevant_indices) >= k*2:
                            break

            articles_added = self._add_articles_to_context(
                relevant_indices, context_parts, self.latest_article_urls,
                self.token_counter, total_tokens, max_tokens, k
            )

            self.logger.debug(f"Added {articles_added} news articles to context (market overview handled separately)")
            self.logger.debug(f"Context tokens: {total_tokens}/{max_tokens}")

            return "".join(context_parts)
        except Exception as e:
            self.logger.error(f"Error retrieving context: {e}")
            return "Error retrieving market context."

    def _add_articles_to_context(self, indices: List[int], context_parts: List[str],
                                 url_dict: Dict[str, str], token_counter: TokenCounter,
                                 total_tokens: int, max_tokens: int, k: int) -> int:
        """Add articles to context with token limiting"""
        articles_added = 0
        for idx in indices:
            if idx >= len(self.news_database):
                continue

            article = self.news_database[idx]

            published_date = self._format_article_date(article)

            title = article.get('title', 'No Title')
            source = article.get('source', 'Unknown Source')

            article_text = f"## {title}\n"
            article_text += f"**Source:** {source} | **Date:** {published_date}\n\n"

            body = article.get('body', '')
            if body:
                paragraphs = body.split('\n\n')[:5]
                summary = '\n\n'.join(paragraphs)
                if len(summary) > 2500:
                    summary = summary[:2500] + "..."
                article_text += f"{summary}\n\n"

            categories = article.get('categories', '')
            tags = article.get('tags', '')
            if categories or tags:
                article_text += f"**Topics:** {categories} | {tags}\n\n"

            article_tokens = token_counter.count_tokens(article_text)
            if total_tokens + article_tokens <= max_tokens:
                context_parts.append(article_text)
                total_tokens += article_tokens
                articles_added += 1

                if 'url' in article:
                    url_dict[title] = article['url']
            else:
                break

            if articles_added >= k:
                break

        return articles_added

    def _format_article_date(self, article: Dict[str, Any]) -> str:
        """Format article date in a consistent way"""
        published_date = "Unknown Date"
        published_on = article.get('published_on', 0)

        try:
            if isinstance(published_on, (int, float)) and published_on > 0:
                dt_object = datetime.fromtimestamp(published_on)
                published_date = dt_object.strftime('%Y-%m-%d')
            elif isinstance(published_on, str):
                if published_on.endswith('Z'):
                    published_on = published_on[:-1] + '+00:00'
                dt_object = datetime.fromisoformat(published_on)
                published_date = dt_object.strftime('%Y-%m-%d')
        except (ValueError, TypeError, OSError) as e:
            self.logger.warning(f"Could not format date for article: {article.get('id', 'N/A')}, value: {published_on}, error: {e}")

        return published_date

    async def get_market_overview(self) -> Optional[Dict[str, Any]]:
        """Get current market overview data"""
        market_overview_file = self.file_handler.get_market_overview_path()

        if self.current_market_overview is None:
            self.current_market_overview = self.file_handler.load_json_file(market_overview_file)

        if self.current_market_overview is not None:
            timestamp_field = self.current_market_overview.get('published_on',
                                                               self.current_market_overview.get('timestamp', 0))
            timestamp = self._normalize_timestamp(timestamp_field)

            if timestamp:
                data_time = datetime.fromtimestamp(timestamp)
                current_time = datetime.now()

                if current_time - data_time > timedelta(hours=1):
                    self.logger.debug(f"Market overview data from {data_time.isoformat()} needs refresh")
                    await self._update_market_overview(market_overview_file)
        else:
            self.logger.debug("No market overview data, fetching fresh data")
            await self._update_market_overview(market_overview_file)

        return self.current_market_overview

    async def _update_market_overview(self, file_path: str) -> None:
        """Update market overview data and save to file"""
        market_overview = await self._fetch_market_overview()
        if market_overview:
            market_overview["id"] = "market_overview"
            market_overview["title"] = "Crypto Market Overview"

            self.file_handler.save_json_file(file_path, market_overview)
            self.current_market_overview = market_overview
            self.logger.debug(f"Updated market overview data at {datetime.now().isoformat()}")

    def _normalize_timestamp(self, timestamp_field: Union[int, float, str, None]) -> float:
        """Convert various timestamp formats to a float timestamp"""
        if timestamp_field is None:
            return 0.0

        if isinstance(timestamp_field, (int, float)):
            return float(timestamp_field)
        elif isinstance(timestamp_field, str):
            try:
                if timestamp_field.endswith('Z'):
                    timestamp_field = timestamp_field[:-1] + '+00:00'
                return datetime.fromisoformat(timestamp_field).timestamp()
            except ValueError:
                self.logger.warning(f"Could not normalize timestamp string: {timestamp_field}")
                return 0.0
            except Exception as e:
                self.logger.error(f"Error normalizing timestamp string '{timestamp_field}': {e}")
                return 0.0
        return 0.0

    async def get_coin_categories(self, symbol: str) -> List[str]:
        """Get categories associated with a coin symbol"""
        base_coin = self.extract_base_coin(symbol).upper()
        categories = set()

        if hasattr(self, 'api_categories'):
            for cat in self.api_categories:
                if cat.get('categoryName', '').upper() == base_coin:
                    if 'wordsAssociatedWithCategory' in cat:
                        for word in cat['wordsAssociatedWithCategory']:
                            categories.add(word)

        indices = self._search_by_coin(base_coin)

        for idx in indices:
            if idx >= len(self.news_database):
                continue

            article = self.news_database[idx]
            article_categories = article.get('categories', '').split('|')

            for category in article_categories:
                if category and category != base_coin and category not in self.non_ticker_categories:
                    categories.add(category)

        return sorted(list(categories))

    async def update_known_tickers(self) -> None:
        """Update known cryptocurrency ticker symbols"""
        try:
            await self._ensure_categories_updated()

            detected_coins = set()

            for article in self.news_database:
                if 'detected_coins' in article:
                    coin_list = article.get('detected_coins', '').split('|')
                    for coin in coin_list:
                        if coin:
                            detected_coins.add(coin)

                categories = article.get('categories', '').split('|')
                for category in categories:
                    if (category and
                        len(category) <= 5 and
                        category.isupper() and ' ' not in category and
                        category not in self.non_ticker_categories and
                        (f"{category}/USD" in article.get('title', '') or
                         f"{category}/BTC" in article.get('title', '') or
                         f"{category} price" in article.get('title', '').upper())):
                        detected_coins.add(category)

            filtered_coins = detected_coins - self.non_ticker_categories

            valid_exchange_symbols = set()
            if self.symbol_manager:
                valid_exchange_symbols = self.symbol_manager.get_all_base_symbols()
                self.logger.debug(f"Validating tickers against {len(valid_exchange_symbols)} exchange base symbols")

            new_coins = 0
            for coin in filtered_coins:
                if (not self.symbol_manager or coin in valid_exchange_symbols) and coin not in self.known_crypto_tickers:
                    self.known_crypto_tickers.add(coin)
                    new_coins += 1

            if new_coins > 0:
                self.logger.debug(f"Added {new_coins} new cryptocurrencies to known tickers")

            self.file_handler.save_json_file(
                self.tickers_file,
                {"tickers": list(self.known_crypto_tickers)}
            )
            self.logger.debug(f"Saved {len(self.known_crypto_tickers)} known tickers to disk")

        except Exception as e:
            self.logger.error(f"Error updating known tickers: {e}")

    async def start_periodic_updates(self) -> None:
        """Start periodic data update task"""
        async def update_loop():
            while True:
                try:
                    await asyncio.sleep(self.update_interval.total_seconds())
                    await self.update_if_needed()
                except asyncio.CancelledError:
                    self.logger.debug("Periodic updates cancelled")
                    break
                except Exception as e:
                    self.logger.error(f"Error in periodic update: {e}")
                    await asyncio.sleep(60)

        if self._periodic_update_task is None:
            self._periodic_update_task = asyncio.create_task(update_loop())
            self.logger.debug(f"Started periodic news updates every {self.update_interval.total_seconds()/60:.1f} minutes")

    async def stop_periodic_updates(self) -> None:
        """Stop periodic data update task"""
        if self._periodic_update_task:
            self._periodic_update_task.cancel()
            try:
                await self._periodic_update_task
            except asyncio.CancelledError:
                pass
            self._periodic_update_task = None
            self.logger.debug("Stopped periodic news updates")

    async def close(self) -> None:
        """Close resources and mark as closed"""
        if self._is_closed:
            return
            
        self._is_closed = True
        
        # Cancel periodic update task if running
        if self._periodic_update_task and not self._periodic_update_task.done():
            self.logger.debug("Cancelling periodic update task")
            self._periodic_update_task.cancel()
            try:
                await self._periodic_update_task
            except asyncio.CancelledError:
                pass
            
        # Close API clients if they have close methods
        for client in [self.coingecko_api, self.cryptocompare_api]:
            if client and hasattr(client, 'close') and callable(client.close):
                try:
                    await client.close()
                except Exception as e:
                    self.logger.error(f"Error closing API client: {e}")
                    
        self.logger.info("RAG Engine resources released")

    def set_symbol_manager(self, symbol_manager) -> None:
        """Set the symbol manager reference"""
        self.symbol_manager = symbol_manager
        self.logger.debug("SymbolManager set in RagEngine")

    async def _ensure_categories_updated(self, force_refresh: bool = False) -> bool:
        """Ensure categories data is up-to-date"""
        current_time = datetime.now()
        needs_update = (force_refresh or
                        not self.categories_last_update or
                        (current_time - self.categories_last_update) > self.categories_update_interval)

        if needs_update:
            self.logger.debug("Categories data may be outdated, refreshing...")
            api_categories = await self.fetch_cryptocompare_categories(force_refresh)
            if api_categories:
                self._process_api_categories(api_categories)
                return True
        return False