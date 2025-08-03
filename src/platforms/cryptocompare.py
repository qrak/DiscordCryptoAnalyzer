import asyncio
import json
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set

import aiohttp

from config.config import (
    RAG_NEWS_API_URL, RAG_CATEGORIES_API_URL, RAG_PRICE_API_URL,
    CRYPTOCOMPARE_API_KEY
)
from src.logger.logger import Logger
from src.utils.decorators import retry_api_call


class CryptoCompareAPI:
    """
    API client for CryptoCompare services.
    Handles news fetching, price data, and categories with proper caching.
    """
    OHLCV_API_URL_TEMPLATE = f"https://min-api.cryptocompare.com/data/v2/histo{{timeframe}}?fsym={{base}}&tsym={{quote}}&limit={{limit}}&api_key={CRYPTOCOMPARE_API_KEY}"
    
    def __init__(
        self,
        logger: Logger,
        data_dir: str = 'data',
        cache_dir: str = 'data/news_cache',
        update_interval_hours: int = 1,
        categories_update_interval_hours: int = 24
    ) -> None:
        # Logger and directories
        self.logger = logger
        self.data_dir = data_dir
        self.cache_dir = cache_dir
        
        # Update intervals
        self.update_interval = timedelta(hours=update_interval_hours)
        self.categories_update_interval = timedelta(hours=categories_update_interval_hours)
        
        # Timestamp tracking
        self.last_news_update: Optional[datetime] = None
        self.categories_last_update: Optional[datetime] = None
        
        # Data storage
        self.api_categories: List[Dict[str, Any]] = []
        self.category_word_map: Dict[str, str] = {}
        
        # File paths
        self.categories_file = os.path.join(data_dir, "categories.json")
        self.news_cache_file = os.path.join(cache_dir, "recent_news.json")
        
        # Ensure directories exist
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(cache_dir, exist_ok=True)
        
        self.session = None
    
    async def initialize(self) -> None:
        """Initialize the API client and load cached data"""
        # Create a shared session
        self.session = aiohttp.ClientSession()
        
        # Load categories
        await self._load_cached_categories()
        
        # Check if we have cached news
        if os.path.exists(self.news_cache_file):
            try:
                with open(self.news_cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    if "last_updated" in cached_data:
                        self.last_news_update = datetime.fromisoformat(cached_data["last_updated"])
                        self.logger.debug(f"Found cached news data from {self.last_news_update.isoformat()}")
            except Exception as e:
                self.logger.error(f"Error loading news cache: {e}")
    
    async def close(self) -> None:
        """Close resources"""
        if hasattr(self, 'session') and self.session:
            try:
                self.logger.debug("Closing CryptoCompare API session")
                await self.session.close()
                self.session = None
            except Exception as e:
                self.logger.error(f"Error closing CryptoCompare API session: {e}")
    
    async def _load_cached_categories(self) -> None:
        """Load cached categories data"""
        if os.path.exists(self.categories_file):
            try:
                with open(self.categories_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    if "timestamp" in cached_data:
                        self.categories_last_update = datetime.fromisoformat(cached_data["timestamp"])
                        if "categories" in cached_data:
                            self.api_categories = cached_data["categories"]
                            self._process_api_categories(self.api_categories)
                            self.logger.debug(f"Loaded {len(self.api_categories)} categories from cache")
            except Exception as e:
                self.logger.error(f"Error loading categories cache: {e}")
    
    @retry_api_call(max_retries=3)
    async def get_latest_news(self, limit: int = 50, max_age_hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get latest cryptocurrency news articles
        
        Args:
            limit: Maximum number of articles to return
            max_age_hours: Maximum age of articles in hours
            
        Returns:
            List of news articles
        """
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(hours=max_age_hours)
        
        # Check if we need to update
        if not self.last_news_update or current_time - self.last_news_update > self.update_interval:
            self.logger.debug("Fetching fresh news data from CryptoCompare")
            articles = await self._fetch_crypto_news()
            
            # Filter by age
            if articles:
                filtered_articles = []
                for article in articles:
                    pub_time = self._get_article_timestamp(article)
                    if pub_time > cutoff_time.timestamp():
                        filtered_articles.append(article)
                
                # Sort by publication date (newest first)
                filtered_articles.sort(key=lambda x: self._get_article_timestamp(x), reverse=True)
                
                # Trim to limit
                result = filtered_articles[:limit] if limit > 0 else filtered_articles
                
                # Cache the results
                self._cache_news_data(result)
                
                return result
            else:
                # If API fetch failed, try to use cached data
                return await self._get_cached_news(limit, cutoff_time)
        else:
            # Use cached data if it's recent enough
            return await self._get_cached_news(limit, cutoff_time)
    
    async def _get_cached_news(self, limit: int, cutoff_time: datetime) -> List[Dict[str, Any]]:
        """Get news from cache with filtering by age and limit"""
        try:
            if os.path.exists(self.news_cache_file):
                with open(self.news_cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    if "articles" in cached_data:
                        articles = cached_data["articles"]
                        # Filter by age
                        filtered_articles = [
                            art for art in articles 
                            if self._get_article_timestamp(art) > cutoff_time.timestamp()
                        ]
                        
                        # Return with limit
                        return filtered_articles[:limit] if limit > 0 else filtered_articles
        except Exception as e:
            self.logger.error(f"Error reading cached news: {e}")
        
        return []
    
    def _cache_news_data(self, articles: List[Dict[str, Any]]) -> None:
        """Save news data to cache file"""
        if not articles:
            return
            
        try:
            cache_data = {
                "last_updated": datetime.now().isoformat(),
                "count": len(articles),
                "articles": articles
            }
            
            with open(self.news_cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
                
            self.last_news_update = datetime.now()
            self.logger.debug(f"Saved {len(articles)} news articles to cache")
        except Exception as e:
            self.logger.error(f"Error saving news cache: {e}")
    
    @retry_api_call(max_retries=3)
    async def get_news_by_category(self, category: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get news articles filtered by category
        
        Args:
            category: Category name to filter by
            limit: Maximum number of articles to return
            
        Returns:
            List of news articles matching the category
        """
        # Get all recent news
        all_news = await self.get_latest_news(limit=0)  # No limit since we'll filter
        
        # Filter by category
        category_lower = category.lower()
        filtered_news = []
        
        for article in all_news:
            categories = article.get('categories', '').lower().split('|')
            if category_lower in categories:
                filtered_news.append(article)
                
            # Check category-associated words in title and body
            if len(filtered_news) < limit:
                title = article.get('title', '').lower()
                body = article.get('body', '').lower()
                
                for word, cat in self.category_word_map.items():
                    if cat.lower() == category_lower and (word in title or word in body):
                        if article not in filtered_news:
                            filtered_news.append(article)
                            break
        
        # Apply limit and return
        return filtered_news[:limit]
    
    async def _fetch_crypto_news(self) -> List[Dict[str, Any]]:
        """Fetch crypto news from CryptoCompare API"""
        articles = []
        
        # Add optional query parameters based on categories
        categories_param = ""
        if self.api_categories:
            important_cats = [cat['categoryName'] for cat in self.api_categories 
                              if cat.get('categoryName', '') in self._get_important_categories()]
            if important_cats:
                categories_param = f"&categories={','.join(important_cats[:5])}"
                
        url = f"{RAG_NEWS_API_URL}{categories_param}"
        
        # Use the shared session if available, otherwise create temporary one
        session_to_use = self.session or aiohttp.ClientSession()
        use_temp_session = self.session is None
        
        try:
            async with session_to_use.get(url, timeout=45) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data and "Data" in data:
                        articles = data["Data"]
                        self.logger.debug(f"Fetched {len(articles)} news articles from CryptoCompare")
                else:
                    self.logger.error(f"News API request failed with status {resp.status}")
        except asyncio.TimeoutError:
            self.logger.error("Timeout fetching news from CryptoCompare")
        except Exception as e:
            self.logger.error(f"Error fetching CryptoCompare news: {e}")
        finally:
            # Only close if we created a temporary session
            if use_temp_session:
                await session_to_use.close()
        
        return articles
    
    @staticmethod
    def _get_important_categories() -> List[str]:
        """Get list of important categories to prioritize in API requests"""
        # This would ideally be configurable
        return ["BTC", "ETH", "DeFi", "NFT", "Layer 2", "Stablecoin", "Altcoin"]
    
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
                self.logger.warning(f"Could not parse timestamp: {published_on}")
        
        return pub_time
    
    @retry_api_call(max_retries=3)
    async def get_categories(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Get cryptocurrency categories data
        
        Args:
            force_refresh: Force refresh from API instead of using cache
            
        Returns:
            List of category objects
        """
        current_time = datetime.now()
        
        # Check if we need to refresh
        if not force_refresh and self.categories_last_update and \
           current_time - self.categories_last_update < self.categories_update_interval:
            return self.api_categories
            
        self.logger.debug(f"Fetching categories from CryptoCompare API: {RAG_CATEGORIES_API_URL}")
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(RAG_CATEGORIES_API_URL, timeout=30) as resp:
                    self.logger.debug(f"Categories API response status: {resp.status}")
                    if resp.status == 200:
                        data = await resp.json()
                        self.logger.debug(f"Categories API raw response: {str(data)[:500]}...")
                        if data:
                            # Save to cache with proper structure
                            cache_data = {
                                "timestamp": current_time.isoformat(),
                                "categories": data
                            }
                            
                            with open(self.categories_file, 'w', encoding='utf-8') as f:
                                json.dump(cache_data, f, ensure_ascii=False, indent=2)
                                
                            # Update internal data
                            self.api_categories = data
                            self._process_api_categories(data)
                            self.categories_last_update = current_time
                            
                            return data
                    else:
                        self.logger.error(f"Categories API request failed with status {resp.status}")
                        self.logger.error(f"Response body: {await resp.text()}")
            except Exception as e:
                self.logger.error(f"Error fetching CryptoCompare categories: {e}")
        
        # Return cached data as fallback if API call fails
        return self.api_categories

    def _process_api_categories(self, api_categories: Any) -> None:
        """Process API categories and update internal data structures"""
        if not api_categories:
            return
            
        self.category_word_map = {}
        
        # Handle different data types that might be received
        try:
            # Debug logging for the received categories data
            self.logger.debug(f"Processing categories data of type: {type(api_categories)}")
            
            # Handle string data - possible serialized JSON
            if isinstance(api_categories, str):
                try:
                    api_categories = json.loads(api_categories)
                    self.logger.debug("Converted string to JSON object")
                except json.JSONDecodeError:
                    self.logger.warning("Received string data that is not valid JSON")
                    return
            
            # Handle the case when api_categories is a dictionary
            if isinstance(api_categories, dict):
                self.logger.debug(f"Processing dictionary with keys: {list(api_categories.keys())}")
                
                # Check CoinDesk format with Response, Message, Type, Data structure
                if "Response" in api_categories and "Data" in api_categories:
                    if api_categories["Response"] == "Success" or api_categories["Response"] == "success":
                        api_categories = api_categories["Data"]
                        self.logger.debug(f"Using data from 'Data' key: {type(api_categories)}")
                    else:
                        self.logger.warning(f"API response not successful: {api_categories.get('Message', 'Unknown error')}")
                        return
                # Simple Data key structure
                elif "Data" in api_categories:
                    api_categories = api_categories["Data"]
                    self.logger.debug(f"Using data from 'Data' key: {type(api_categories)}")
            
            # Process each category if we have a list
            if isinstance(api_categories, list):
                self.logger.debug(f"Processing list with {len(api_categories)} items")
                
                # Process items based on expected CryptoCompare category structure
                # Example: {"categoryName": "BTC", "wordsAssociatedWithCategory": ["BTC", "Bitcoin"], "includedPhrases": ["..."]}
                for cat in api_categories:
                    if isinstance(cat, dict) and 'categoryName' in cat:
                        category_name = cat.get('categoryName', '')
                        if category_name:
                            # Process wordsAssociatedWithCategory
                            if 'wordsAssociatedWithCategory' in cat and isinstance(cat['wordsAssociatedWithCategory'], list):
                                for word in cat['wordsAssociatedWithCategory']:
                                    if isinstance(word, str) and len(word) > 2:
                                        self.category_word_map[word.lower()] = category_name
                            
                            # Process includedPhrases
                            if 'includedPhrases' in cat and isinstance(cat['includedPhrases'], list):
                                for phrase in cat['includedPhrases']:
                                    if isinstance(phrase, str) and len(phrase) > 2:
                                        self.category_word_map[phrase.lower()] = category_name
                    elif isinstance(cat, str):
                        # For simple string categories, just log them
                        self.logger.debug(f"Adding string category: {cat}")
                    else:
                        self.logger.debug(f"Skipping category with unexpected structure: {type(cat)}")
                        
                self.logger.debug(f"Processed {len(self.category_word_map)} category-word associations")
            else:
                self.logger.warning(f"Unexpected data type for api_categories: {type(api_categories)}")
                
        except Exception as e:
            self.logger.error(f"Error processing API categories: {e}")

    @retry_api_call(max_retries=3)
    async def get_multi_price_data(self, coins: List[str] = None, vs_currencies: List[str] = None) -> Dict[str, Any]:
        """
        Get price data for multiple coins
        
        Args:
            coins: List of coin symbols (default: BTC,ETH,XRP,LTC,BCH,BNB,ADA,DOT,LINK)
            vs_currencies: List of fiat currencies (default: USD)
            
        Returns:
            Dictionary with price data
        """
        default_coins = ["BTC", "ETH", "XRP", "LTC", "BCH", "BNB", "ADA", "DOT", "LINK"]
        default_currencies = ["USD"]
        
        # Use defaults if not provided
        fsyms = coins if coins else default_coins
        tsyms = vs_currencies if vs_currencies else default_currencies
        
        # Build URL
        url = f"https://min-api.cryptocompare.com/data/pricemultifull?fsyms={','.join(fsyms)}&tsyms={','.join(tsyms)}"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=30) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data and "RAW" in data:
                            return data
                        else:
                            self.logger.warning("Price data response missing RAW field")
                            return {}
                    else:
                        self.logger.error(f"Price API request failed with status {resp.status}")
                        return {}
            except Exception as e:
                self.logger.error(f"Error fetching price data: {e}")
                return {}

    @staticmethod
    async def detect_coins_in_article(article: Dict[str, Any], known_tickers: Set[str]) -> Set[str]:
        """
        Detect cryptocurrency mentions in article content
        
        Args:
            article: Article data
            known_tickers: Set of known cryptocurrency tickers
            
        Returns:
            Set of detected coin tickers
        """
        coins_mentioned = set()
        title = article.get('title', '').upper()
        body = article.get('body', '').upper() if len(article.get('body', '')) < 10000 else article.get('body', '')[:10000].upper()
        categories = article.get('categories', '').split('|')
        
        # Check categories
        for category in categories:
            cat_upper = category.upper()
            if cat_upper in known_tickers:
                coins_mentioned.add(cat_upper)
        
        # Check for ticker patterns in title and body
        ticker_regex = r'\b[A-Z]{2,6}\b'
        potential_tickers_in_title = set(re.findall(ticker_regex, title))
        potential_tickers_in_body = set(re.findall(ticker_regex, body))
        
        # Add known tickers found in title
        for ticker in potential_tickers_in_title:
            if ticker in known_tickers:
                coins_mentioned.add(ticker)
        
        # Add known tickers found in body
        for ticker in potential_tickers_in_body:
            if ticker in known_tickers:
                coins_mentioned.add(ticker)
        
        # Special case for Bitcoin and Ethereum
        title_lower = title.lower()
        body_lower = body.lower()
        if 'bitcoin' in title_lower or 'bitcoin' in body_lower or 'BTC' in coins_mentioned:
            coins_mentioned.add('BTC')
        if 'ethereum' in title_lower or 'ethereum' in body_lower or 'ETH' in coins_mentioned:
            coins_mentioned.add('ETH')
        
        return coins_mentioned