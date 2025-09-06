"""
Category processing and normalization operations.
"""
from typing import Dict, Any, List, Set, Tuple
from src.logger.logger import Logger


class CategoryProcessor:
    """Handles processing and normalization of cryptocurrency categories."""
    
    def __init__(self, logger: Logger):
        self.logger = logger
        
        # Category data storage
        self.category_word_map: Dict[str, str] = {}
        self.general_categories: Set[str] = set()
        self.ticker_categories: Set[str] = set()
        self.important_categories: Set[str] = {
            'decentralized-finance-defi', 'smart-contracts', 'ethereum-ecosystem',
            'binance-smart-chain', 'layer-1', 'layer-2', 'metaverse', 'gaming',
            'nft', 'web3', 'meme-tokens', 'stablecoins', 'privacy-coins'
        }
    
    def process_api_categories(self, api_categories: List[Dict[str, Any]]) -> None:
        """Process API categories and update internal indices."""
        if not api_categories:
            return
            
        # Clear existing mappings
        self.category_word_map.clear()
        
        # Categorize the data
        general_categories, ticker_categories = self._categorize_api_data(api_categories)
        
        # Process category words for mapping
        for category in api_categories:
            category_name = category.get('CategoryName', '').lower()
            if category_name:
                self._process_category_words(category, category_name)
        
        # Update internal category sets
        self._update_category_sets(general_categories, ticker_categories)
        
        self.logger.debug(f"Processed {len(api_categories)} categories")
        self.logger.debug(f"General categories: {len(self.general_categories)}")
        self.logger.debug(f"Ticker categories: {len(self.ticker_categories)}")
        self.logger.debug(f"Category word mappings: {len(self.category_word_map)}")
    
    def _categorize_api_data(self, api_categories: List[Dict[str, Any]]) -> Tuple[Set[str], Set[str]]:
        """Categorize API data into general and ticker categories."""
        general_categories = set()
        ticker_categories = set()
        
        for category in api_categories:
            category_name = category.get('CategoryName', '').lower()
            
            if category_name:
                if self._is_ticker_category(category_name):
                    ticker_categories.add(category_name)
                else:
                    general_categories.add(category_name)
        
        return general_categories, ticker_categories
    
    def _is_ticker_category(self, category_name: str) -> bool:
        """Determine if a category represents individual tickers."""
        ticker_indicators = ['symbol', 'coin', 'token', 'currency', '-usd', '-btc', '-eth']
        return any(indicator in category_name for indicator in ticker_indicators)
    
    def _process_category_words(self, category: Dict[str, Any], category_name: str) -> None:
        """Process category words and create mappings."""
        # Extract words from category for search mapping
        words = category_name.replace('-', ' ').split()
        for word in words:
            if len(word) > 2:  # Skip very short words
                word_lower = word.lower()
                if word_lower not in self.category_word_map:
                    self.category_word_map[word_lower] = category_name
    
    def _update_category_sets(self, general_categories: Set[str], ticker_categories: Set[str]) -> None:
        """Update internal category sets."""
        self.general_categories = general_categories
        self.ticker_categories = ticker_categories
    
    def get_api_categories(self, base_coin: str) -> set:
        """Get categories for a coin from the API category data."""
        matching_categories = set()
        
        # Check if the coin matches any ticker categories directly
        coin_lower = base_coin.lower()
        
        for category in self.ticker_categories:
            if coin_lower in category:
                matching_categories.add(category)
        
        # Check word-based mappings
        for word, category in self.category_word_map.items():
            if coin_lower == word or (len(coin_lower) > 3 and word in coin_lower):
                matching_categories.add(category)
        
        return matching_categories
    
    def extract_base_coin(self, symbol: str) -> str:
        """Extract base coin from trading pair symbol."""
        if not symbol:
            return ""
        
        # Handle different formats
        if '/' in symbol:
            return symbol.split('/')[0].upper()
        elif '-' in symbol:
            return symbol.split('-')[0].upper()
        else:
            # Try to extract base from common pairs
            common_quotes = ['USDT', 'USD', 'BTC', 'ETH', 'BNB', 'BUSD']
            symbol_upper = symbol.upper()
            
            for quote in common_quotes:
                if symbol_upper.endswith(quote):
                    return symbol_upper[:-len(quote)]
            
            return symbol_upper
