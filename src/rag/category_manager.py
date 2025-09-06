"""
Category Management Module for RAG Engine

Handles cryptocurrency categories, tickers, and related operations.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set, Tuple
from src.logger.logger import Logger
from src.rag.filehandler import RagFileHandler
from config.config import (
    RAG_CATEGORIES_UPDATE_INTERVAL_HOURS,
    RAG_INITIAL_KNOWN_TICKERS,
    RAG_IMPORTANT_CATEGORIES, 
    RAG_NON_TICKER_CATEGORIES
)


class CategoryManager:
    """Manages cryptocurrency categories and ticker information."""
    
    def __init__(self, logger: Logger, file_handler: RagFileHandler, 
                 cryptocompare_api=None, symbol_manager=None, index_manager=None):
        self.logger = logger
        self.file_handler = file_handler
        self.cryptocompare_api = cryptocompare_api
        self.symbol_manager = symbol_manager
        self.index_manager = index_manager
        
        # Category data
        self.category_word_map: Dict[str, str] = {}
        self.api_categories: List[Dict[str, Any]] = []
        self.categories_last_update: Optional[datetime] = None
        
        # Configuration data
        self.tickers_file = self.file_handler.get_tickers_file_path()
        self.categories_update_interval = timedelta(hours=RAG_CATEGORIES_UPDATE_INTERVAL_HOURS)
        
        # Use config for initial sets
        self.known_crypto_tickers: Set[str] = set(RAG_INITIAL_KNOWN_TICKERS)
        self.important_categories: Set[str] = set(RAG_IMPORTANT_CATEGORIES)
        self.non_ticker_categories: Set[str] = set(RAG_NON_TICKER_CATEGORIES)
    
    async def load_known_tickers(self) -> None:
        """Load known tickers from disk."""
        try:
            data = self.file_handler.load_json_file(self.tickers_file)
            if data:
                saved_tickers = set(data.get("tickers", []))
                new_count = len(saved_tickers - self.known_crypto_tickers)
                self.known_crypto_tickers.update(saved_tickers)
                self.logger.debug(f"Loaded {len(saved_tickers)} tickers from disk ({new_count} new)")
        except Exception as e:
            self.logger.error(f"Error loading known tickers: {e}")
    
    async def fetch_cryptocompare_categories(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Fetch cryptocurrency categories from CryptoCompare API."""
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
    
    def process_api_categories(self, api_categories: List[Dict[str, Any]]) -> None:
        """Process API categories and update internal indices."""
        if not api_categories:
            return
        
        self.logger.debug(f"Processing {len(api_categories) if isinstance(api_categories, list) else 'unknown number of'} categories")
        
        # Store the API categories and clear existing maps
        self.api_categories = api_categories
        self.category_word_map = {}
        
        # Process categories using helper methods
        general_categories, ticker_categories = self._categorize_api_data(api_categories)
        self._update_category_sets(general_categories, ticker_categories)
        
        self.logger.debug(f"Processed {len(general_categories)} general categories and {len(ticker_categories)} ticker categories")
        self.logger.debug(f"Updated category-word map with {len(self.category_word_map)} entries")

    def _categorize_api_data(self, api_categories: List[Dict[str, Any]]) -> Tuple[Set[str], Set[str]]:
        """Categorize API data into general and ticker categories."""
        general_categories = set()
        ticker_categories = set()

        if not isinstance(api_categories, list):
            return general_categories, ticker_categories

        for category in api_categories:
            if not isinstance(category, dict) or 'categoryName' not in category:
                continue
                
            category_name = category['categoryName'].upper()
            
            if self._is_ticker_category(category_name):
                ticker_categories.add(category_name)
            else:
                general_categories.add(category_name)
            
            self._process_category_words(category, category_name)
        
        return general_categories, ticker_categories

    def _is_ticker_category(self, category_name: str) -> bool:
        """Determine if a category name represents a ticker."""
        return (len(category_name) <= 5 and 
                category_name.isupper() and 
                ' ' not in category_name and
                category_name not in self.non_ticker_categories)

    def _process_category_words(self, category: Dict[str, Any], category_name: str) -> None:
        """Process words associated with a category."""
        word_sources = ['wordsAssociatedWithCategory', 'includedPhrases']
        
        for word_source in word_sources:
            if word_source not in category or not isinstance(category[word_source], list):
                continue
                
            for word in category[word_source]:
                if isinstance(word, str) and len(word) > 2:
                    self.category_word_map[word.lower()] = category_name

    def _update_category_sets(self, general_categories: Set[str], ticker_categories: Set[str]) -> None:
        """Update the internal category and ticker sets."""
        self.non_ticker_categories.update(general_categories)
        self.known_crypto_tickers.update(ticker_categories)
    
    async def ensure_categories_updated(self, force_refresh: bool = False) -> bool:
        """Ensure categories data is up-to-date."""
        current_time = datetime.now()
        needs_update = (force_refresh or
                        not self.categories_last_update or
                        (current_time - self.categories_last_update) > self.categories_update_interval)

        if needs_update:
            self.logger.debug("Categories data may be outdated, refreshing...")
            api_categories = await self.fetch_cryptocompare_categories(force_refresh)
            if api_categories:
                self.process_api_categories(api_categories)
                return True
        return False
    
    async def update_known_tickers(self, news_database: List[Dict[str, Any]]) -> None:
        """Update known cryptocurrency ticker symbols."""
        try:
            await self.ensure_categories_updated()

            # Collect coins from different sources
            detected_coins = self._extract_detected_coins(news_database)
            category_coins = self._extract_category_coins(news_database)
            
            # Combine and filter coins
            all_coins = detected_coins | category_coins
            filtered_coins = all_coins - self.non_ticker_categories

            # Validate and add new coins
            await self._validate_and_add_coins(filtered_coins)
            
        except Exception as e:
            self.logger.error(f"Error updating known tickers: {e}")

    def _extract_detected_coins(self, news_database: List[Dict[str, Any]]) -> set:
        """Extract coins from detected_coins field in articles."""
        detected_coins = set()
        
        for article in news_database:
            if 'detected_coins' in article:
                coin_list = article.get('detected_coins', '').split('|')
                for coin in coin_list:
                    if coin:
                        detected_coins.add(coin)
        
        return detected_coins

    def _extract_category_coins(self, news_database: List[Dict[str, Any]]) -> set:
        """Extract valid ticker symbols from article categories."""
        category_coins = set()
        
        for article in news_database:
            categories = article.get('categories', '').split('|')
            for category in categories:
                if self._is_valid_ticker_category(category, article):
                    category_coins.add(category)
        
        return category_coins

    def _is_valid_ticker_category(self, category: str, article: dict) -> bool:
        """Check if a category represents a valid ticker symbol."""
        if not category or len(category) > 5 or not category.isupper():
            return False
        
        if ' ' in category or category in self.non_ticker_categories:
            return False
            
        title = article.get('title', '')
        return (f"{category}/USD" in title or
                f"{category}/BTC" in title or
                f"{category} price" in title.upper())

    async def _validate_and_add_coins(self, filtered_coins: set) -> None:
        """Validate coins against exchange symbols and add new ones."""
        valid_exchange_symbols = set()
        if self.symbol_manager:
            valid_exchange_symbols = self.symbol_manager.get_all_base_symbols()
            self.logger.debug(f"Validating tickers against {len(valid_exchange_symbols)} exchange base symbols")

        new_coins = 0
        for coin in filtered_coins:
            if self._should_add_coin(coin, valid_exchange_symbols):
                self.known_crypto_tickers.add(coin)
                new_coins += 1

        if new_coins > 0:
            self.logger.debug(f"Added {new_coins} new cryptocurrencies to known tickers")

        # Save updated tickers
        await self.save_tickers()

    def _should_add_coin(self, coin: str, valid_exchange_symbols: set) -> bool:
        """Check if a coin should be added to known tickers."""
        return ((not self.symbol_manager or coin in valid_exchange_symbols) and 
                coin not in self.known_crypto_tickers)
    
    async def save_tickers(self) -> None:
        """Save known tickers to disk."""
        try:
            self.file_handler.save_json_file(
                self.tickers_file,
                {"tickers": list(self.known_crypto_tickers)}
            )
            self.logger.debug(f"Saved {len(self.known_crypto_tickers)} known tickers to disk")
        except Exception as e:
            self.logger.error(f"Error saving tickers: {e}")
    
    def get_coin_categories(self, symbol: str, news_database: Optional[List[Dict[str, Any]]] = None) -> List[str]:
        """Get categories associated with a coin symbol."""
        base_coin = self.extract_base_coin(symbol).upper()
        categories = set()

        # Get categories from API data
        categories.update(self._get_api_categories(base_coin))
        
        # Get categories from news articles if news database is provided
        if news_database:
            categories.update(self._get_news_categories(base_coin, news_database))
        
        return sorted(list(categories))
    
    def _get_news_categories(self, base_coin: str, news_database: List[Dict[str, Any]]) -> set:
        """Extract categories from news articles for a given coin."""
        categories = set()
        
        # Search for articles about this specific coin
        indices = self.index_manager.search_by_coin(base_coin) if self.index_manager else []
        
        for idx in indices:
            if idx >= len(news_database):
                continue
                
            article = news_database[idx]
            article_categories = article.get('categories', '').split('|')
            
            for category in article_categories:
                if (category and 
                    category != base_coin and 
                    category not in self.non_ticker_categories):
                    categories.add(category)
        
        return categories
    
    def _get_api_categories(self, base_coin: str) -> set:
        """Extract categories from API data for a given coin."""
        categories = set()
        
        if hasattr(self, 'api_categories'):
            for cat in self.api_categories:
                if cat.get('categoryName', '').upper() == base_coin:
                    if 'wordsAssociatedWithCategory' in cat:
                        categories.update(cat['wordsAssociatedWithCategory'])
        
        return categories
    
    def extract_base_coin(self, symbol: str) -> str:
        """Extract base coin from trading pair symbol."""
        if '/' in symbol:
            base = symbol.split('/')[0]
        else:
            base = symbol

        return base
    
    def get_known_tickers(self) -> Set[str]:
        """Get the set of known cryptocurrency tickers."""
        return self.known_crypto_tickers.copy()
    
    def get_category_word_map(self) -> Dict[str, str]:
        """Get the category word mapping."""
        return self.category_word_map.copy()
    
    def get_important_categories(self) -> Set[str]:
        """Get the set of important categories."""
        return self.important_categories.copy()
    
    def is_important_category(self, category: str) -> bool:
        """Check if a category is considered important."""
        return category.upper() in self.important_categories
    
    def add_known_ticker(self, ticker: str) -> None:
        """Add a ticker to the known tickers set."""
        self.known_crypto_tickers.add(ticker.upper())
    
    def is_known_ticker(self, ticker: str) -> bool:
        """Check if a ticker is in the known tickers set."""
        return ticker.upper() in self.known_crypto_tickers
