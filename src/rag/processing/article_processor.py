"""
Shared article processing utilities for RAG components.
Eliminates code duplication between news_manager and context_builder.
"""
from datetime import datetime
from typing import Dict, Any
import logging


class ArticleProcessor:
    """Utility class for common article processing operations."""
    
    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)
    
    def get_article_timestamp(self, article: Dict[str, Any]) -> float:
        """Extract timestamp from article in a consistent format."""
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
    
    def format_article_date(self, article: Dict[str, Any]) -> str:
        """Format article date in a consistent way."""
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
    
    def extract_base_coin(self, symbol: str) -> str:
        """Extract base coin from trading pair symbol."""
        if not symbol:
            return ""
        
        # Handle symbols with explicit separators first (like SOL/USDT)
        if '/' in symbol:
            return symbol.split('/')[0].upper()
        
        # Handle symbols with hyphen separator (like SOL-USDT)
        if '-' in symbol:
            return symbol.split('-')[0].upper()
        
        # Common trading pair separators for concatenated symbols (like SOLUSDT)
        separators = ['USDT', 'USD', 'BTC', 'ETH', 'BNB', 'BUSD']
        
        for sep in separators:
            if symbol.endswith(sep):
                return symbol[:-len(sep)].upper()
        
        # If no separator found, return the symbol as is
        return symbol.upper()
    
    def calculate_time_decay(self, article: Dict[str, Any], current_time: float) -> float:
        """Calculate time-based decay factor for article relevance."""
        pub_time = self.get_article_timestamp(article)
        if pub_time <= 0:
            return 0.0
        
        time_diff = current_time - pub_time
        return max(0.0, 1.0 - (time_diff / (24 * 3600)))
