"""
Shared article processing utilities for RAG components.
Eliminates code duplication between news_manager and context_builder.
"""
from datetime import datetime
from typing import Dict, Any, Set
import logging
import re


class ArticleProcessor:
    """Utility class for common article processing operations."""
    
    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)
    
    def detect_coins_in_article(self, article: Dict[str, Any], known_crypto_tickers: Set[str]) -> Set[str]:
        """Detect cryptocurrency mentions in article content (centralized implementation)."""
        coins_mentioned = set()
        title = article.get('title', '').upper()
        body = article.get('body', '').upper() if len(article.get('body', '')) < 10000 else article.get('body', '')[:10000].upper()
        categories = article.get('categories', '').split('|')

        # Check categories for tickers
        for category in categories:
            cat_upper = category.upper()
            if cat_upper in known_crypto_tickers:
                coins_mentioned.add(cat_upper)

        # Find potential tickers in title and body
        potential_tickers_regex = r'\b[A-Z]{2,6}\b'
        potential_tickers_in_title = set(re.findall(potential_tickers_regex, title))
        potential_tickers_in_body = set(re.findall(potential_tickers_regex, body))

        # Validate tickers against known set
        for ticker in potential_tickers_in_title:
            if ticker in known_crypto_tickers:
                coins_mentioned.add(ticker)

        for ticker in potential_tickers_in_body:
            if ticker in known_crypto_tickers:
                coins_mentioned.add(ticker)

        # Special handling for major cryptocurrencies
        title_lower = title.lower()
        body_lower = body.lower()
        if 'bitcoin' in title_lower or 'bitcoin' in body_lower or 'BTC' in coins_mentioned:
            coins_mentioned.add('BTC')
        if 'ethereum' in title_lower or 'ethereum' in body_lower or 'ETH' in coins_mentioned:
            coins_mentioned.add('ETH')

        return coins_mentioned
    
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
