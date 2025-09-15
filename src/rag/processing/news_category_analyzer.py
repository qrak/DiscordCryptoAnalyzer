"""
News-based category operations for analyzing article content.
"""
from typing import List, Dict, Any, Set, Optional
from src.logger.logger import Logger
from src.parsing.unified_parser import UnifiedParser


class NewsCategoryAnalyzer:
    """Handles category analysis from news articles and content."""
    
    def __init__(self, logger: Logger, category_processor=None):
        self.logger = logger
        self.category_processor = category_processor
        self.parser = UnifiedParser(logger)
    
    def get_coin_categories(self, symbol: str, news_database: Optional[List[Dict[str, Any]]] = None) -> List[str]:
        """Get categories for a given coin symbol from multiple sources."""
        if not symbol:
            return []
        
        # Extract base coin from the symbol
        base_coin = self._extract_base_coin(symbol)
        all_categories = set()
        
        # Get categories from news database if provided
        if news_database:
            news_categories = self._get_news_categories(base_coin, news_database)
            all_categories.update(news_categories)
        
        # Get categories from API data if available
        if self.category_processor:
            api_categories = self.category_processor.get_api_categories(base_coin)
            all_categories.update(api_categories)
        
        return sorted(list(all_categories))
    
    def _get_news_categories(self, base_coin: str, news_database: List[Dict[str, Any]]) -> set:
        """Extract categories for a coin from news database."""
        coin_categories = set()
        coin_lower = base_coin.lower()
        
        for article in news_database:
            # Check if this coin is mentioned in the article
            coins_mentioned = article.get('coins_mentioned', [])
            article_categories = article.get('categories', '')
            
            # Check if coin is mentioned or in title/body
            coin_mentioned = False
            
            if isinstance(coins_mentioned, list) and base_coin in coins_mentioned:
                coin_mentioned = True
            else:
                # Check title and body for coin mention
                title = article.get('title', '').lower()
                body = article.get('body', '').lower()
                
                if coin_lower in title or coin_lower in body:
                    coin_mentioned = True
            
            # If coin is mentioned, extract categories
            if coin_mentioned and article_categories:
                categories = self.parser.parse_article_categories(article_categories)
                coin_categories.update(categories)
        
        return coin_categories
    
    def _extract_base_coin(self, symbol: str) -> str:
        """Extract base coin from trading pair symbol."""
        return self.parser.extract_base_coin(symbol)
