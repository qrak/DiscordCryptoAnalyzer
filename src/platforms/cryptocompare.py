import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set

import aiohttp

from src.logger.logger import Logger
from src.utils.decorators import retry_api_call
from .utils.cryptocompare_news_api import CryptoCompareNewsAPI
from .utils.cryptocompare_categories_api import CryptoCompareCategoriesAPI
from .utils.cryptocompare_market_api import CryptoCompareMarketAPI
from .utils.cryptocompare_data_processor import CryptoCompareDataProcessor


class CryptoCompareAPI:
    """
    API client for CryptoCompare services.
    Handles news fetching, price data, and categories with proper caching.
    
    This class acts as an orchestrator for specialized API components while maintaining
    full backward compatibility with the existing interface.
    """
    
    def __init__(
        self,
        logger: Logger,
        data_dir: str = 'data',
        cache_dir: str = 'data/news_cache',
        update_interval_hours: int = 1,
        categories_update_interval_hours: int = 24
    ) -> None:
        # Initialize specialized components
        self.logger = logger
        self.data_dir = data_dir
        self.cache_dir = cache_dir
        
        # Initialize specialized API components
        self.news_api = CryptoCompareNewsAPI(logger, cache_dir, update_interval_hours)
        self.categories_api = CryptoCompareCategoriesAPI(logger, data_dir, categories_update_interval_hours)
        self.market_api = CryptoCompareMarketAPI(logger)
        self.data_processor = CryptoCompareDataProcessor(logger)
        
        # Maintain backward compatibility properties
        self.update_interval = timedelta(hours=update_interval_hours)
        self.categories_update_interval = timedelta(hours=categories_update_interval_hours)
        
        # Ensure directories exist
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(cache_dir, exist_ok=True)
        
        self.session = None
    
    # Backward compatibility properties that delegate to specialized components
    @property
    def last_news_update(self) -> Optional[datetime]:
        """Get last news update timestamp"""
        return self.news_api.last_news_update
    
    @property
    def categories_last_update(self) -> Optional[datetime]:
        """Get last categories update timestamp"""
        return self.categories_api.categories_last_update
    
    @property
    def api_categories(self) -> List[Dict[str, Any]]:
        """Get current API categories"""
        return self.categories_api.get_api_categories()
    
    @property
    def category_word_map(self) -> Dict[str, str]:
        """Get current category word mapping"""
        return self.categories_api.get_category_word_map()
    
    @property
    def categories_file(self) -> str:
        """Get categories file path"""
        return self.categories_api.categories_file
    
    @property
    def news_cache_file(self) -> str:
        """Get news cache file path"""
        return self.news_api.news_cache_file
    
    @property
    def OHLCV_API_URL_TEMPLATE(self) -> str:
        """Get OHLCV API URL template"""
        return self.market_api.get_ohlcv_url_template()
    
    async def initialize(self) -> None:
        """Initialize the API client and load cached data"""
        # Create a shared session
        self.session = aiohttp.ClientSession()
        
        # Initialize specialized components
        await self.news_api.initialize()
        await self.categories_api.initialize()
    
    async def close(self) -> None:
        """Close resources"""
        if hasattr(self, 'session') and self.session:
            try:
                self.logger.debug("Closing CryptoCompare API session")
                await self.session.close()
                self.session = None
            except Exception as e:
                self.logger.error(f"Error closing CryptoCompare API session: {e}")
    
    # Delegate news operations to news API component
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
        return await self.news_api.get_latest_news(
            limit=limit,
            max_age_hours=max_age_hours,
            session=self.session,
            api_categories=self.categories_api.get_api_categories()
        )
    
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
        return await self.news_api.get_news_by_category(
            category=category,
            limit=limit,
            category_word_map=self.categories_api.get_category_word_map(),
            session=self.session,
            api_categories=self.categories_api.get_api_categories()
        )
    
    # Delegate categories operations to categories API component
    @retry_api_call(max_retries=3)
    async def get_categories(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Get cryptocurrency categories data
        
        Args:
            force_refresh: Force refresh from API instead of using cache
            
        Returns:
            List of category objects
        """
        return await self.categories_api.get_categories(force_refresh=force_refresh)
    
    # Delegate market operations to market API component
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
        return await self.market_api.get_multi_price_data(coins=coins, vs_currencies=vs_currencies)
    
    # Delegate static methods to appropriate components
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
        return await CryptoCompareNewsAPI.detect_coins_in_article(article, known_tickers)
    
    # Backward compatibility methods that delegate to specialized components
    async def _load_cached_categories(self) -> None:
        """Load cached categories data - maintained for backward compatibility"""
        await self.categories_api._load_cached_categories()
    
    async def _get_cached_news(self, limit: int, cutoff_time: datetime) -> List[Dict[str, Any]]:
        """Get news from cache - maintained for backward compatibility"""
        return await self.news_api._get_cached_news(limit, cutoff_time)
    
    def _cache_news_data(self, articles: List[Dict[str, Any]]) -> None:
        """Save news data to cache - maintained for backward compatibility"""
        self.news_api._cache_news_data(articles)
    
    async def _fetch_crypto_news(self) -> List[Dict[str, Any]]:
        """Fetch crypto news from API - maintained for backward compatibility"""
        return await self.news_api._fetch_crypto_news(
            session=self.session,
            api_categories=self.categories_api.get_api_categories()
        )
    
    def _filter_news_by_category(self, articles: List[Dict[str, Any]], category: str, limit: int) -> List[Dict[str, Any]]:
        """Filter news by category - maintained for backward compatibility"""
        return self.news_api._filter_news_by_category(
            articles, category, limit, self.categories_api.get_category_word_map()
        )
    
    def _article_matches_category_directly(self, article: Dict[str, Any], category_lower: str) -> bool:
        """Check direct category match - maintained for backward compatibility"""
        return self.news_api._article_matches_category_directly(article, category_lower)
    
    def _article_matches_category_words(self, article: Dict[str, Any], category_lower: str) -> bool:
        """Check category word match - maintained for backward compatibility"""
        return self.news_api._article_matches_category_words(
            article, category_lower, self.categories_api.get_category_word_map()
        )
    
    def _get_article_timestamp(self, article: Dict[str, Any]) -> float:
        """Get article timestamp - maintained for backward compatibility"""
        return self.news_api._get_article_timestamp(article)
    
    def _process_api_categories(self, api_categories: Any) -> None:
        """Process API categories - maintained for backward compatibility"""
        self.categories_api._process_api_categories(api_categories)
    
    def _normalize_categories_data(self, api_categories: Any) -> Optional[List]:
        """Normalize categories data - maintained for backward compatibility"""
        return self.data_processor.normalize_categories_data(api_categories)
    
    def _extract_data_from_dict(self, data_dict: Dict) -> Optional[List]:
        """Extract data from dict - maintained for backward compatibility"""
        return self.data_processor._extract_data_from_dict(data_dict)
    
    def _extract_category_mappings(self, categories_list: List) -> None:
        """Extract category mappings - maintained for backward compatibility"""
        self.categories_api._extract_category_mappings(categories_list)
    
    def _process_category_dict(self, cat: Dict) -> None:
        """Process category dict - maintained for backward compatibility"""
        self.categories_api._process_category_dict(cat)
    
    def _add_words_to_mapping(self, words: List, category_name: str) -> None:
        """Add words to mapping - maintained for backward compatibility"""
        self.categories_api._add_words_to_mapping(words, category_name)
    
    @staticmethod
    def _get_important_categories() -> List[str]:
        """Get important categories - maintained for backward compatibility"""
        return CryptoCompareDataProcessor.get_important_categories()