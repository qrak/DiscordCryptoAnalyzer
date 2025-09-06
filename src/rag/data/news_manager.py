"""
News Management Module for RAG Engine

Handles fetching, caching, and processing of cryptocurrency news articles.
"""

import asyncio
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
from src.logger.logger import Logger
from .file_handler import RagFileHandler
from ..processing.article_processor import ArticleProcessor


class NewsManager:
    """Manages cryptocurrency news articles and related operations."""
    
    def __init__(self, logger: Logger, file_handler: RagFileHandler, cryptocompare_api=None):
        self.logger = logger
        self.file_handler = file_handler
        self.cryptocompare_api = cryptocompare_api
        self.article_processor = ArticleProcessor(logger)
        
        # News database
        self.news_database: List[Dict[str, Any]] = []
        self.latest_article_urls: Dict[str, str] = {}
        
    async def load_cached_news(self) -> None:
        """Load cached news articles from disk."""
        try:
            self.news_database = self.file_handler.load_news_articles()
            if self.news_database:
                self.logger.debug(f"Loaded {len(self.news_database)} cached news articles")
        except Exception as e:
            self.logger.exception(f"Error loading cached news: {e}")
            self.news_database = []
    
    async def fetch_fresh_news(self, known_crypto_tickers: Set[str]) -> List[Dict[str, Any]]:
        """Fetch fresh news articles from external API."""
        if self.cryptocompare_api is None:
            self.logger.error("CryptoCompare API client not initialized")
            return []
            
        try:
            # Use the CryptoCompare API client to fetch news
            articles = await self.cryptocompare_api.get_latest_news(limit=50, max_age_hours=24)
            
            if articles:
                # Detect coins in articles using local method instead of API method
                for article in articles:
                    coins_mentioned = self.detect_coins_in_article(article, known_crypto_tickers)
                    if coins_mentioned:
                        article['detected_coins'] = '|'.join(coins_mentioned)
                        
                self.logger.debug(f"Fetched {len(articles)} recent news articles from CryptoCompare")
                return articles
            else:
                self.logger.warning("No articles returned from CryptoCompare API")
                return self._get_fallback_articles()
                
        except Exception as e:
            self.logger.error(f"Error fetching CryptoCompare news: {e}")
            return self._get_fallback_articles()
    
    def _get_fallback_articles(self) -> List[Dict[str, Any]]:
        """Get fallback articles when fresh fetch fails."""
        fallback_articles = self.file_handler.load_fallback_articles(max_age_hours=72)
        if fallback_articles:
            self.logger.info(f"Using {len(fallback_articles)} cached articles as fallback")
            return fallback_articles
        return []
    
    def update_news_database(self, new_articles: List[Dict[str, Any]]) -> bool:
        """Update news database with new articles."""
        if not new_articles:
            self.logger.debug("No new articles to process")
            return False
            
        recent_articles = self.file_handler.filter_recent_articles(new_articles)
        
        existing_ids = {article.get('id') for article in self.news_database if article.get('id')}
        unique_articles = [art for art in recent_articles if art.get('id') and art.get('id') not in existing_ids]
        
        if unique_articles:
            self.logger.debug(f"Found {len(unique_articles)} new articles")
            combined_articles = self.news_database + unique_articles
            
            # Sort by timestamp, newest first
            combined_articles.sort(key=lambda x: self._get_article_timestamp(x), reverse=True)
            
            # Filter to keep only recent articles
            self.news_database = self.file_handler.filter_recent_articles(combined_articles)
            
            # Save updated database
            self.file_handler.save_news_articles(self.news_database)
            
            self.logger.debug(f"Updated news database with {len(self.news_database)} recent articles")
            return True
        else:
            self.logger.debug("No new articles to add or only duplicates found")
            return False
    
    def detect_coins_in_article(self, article: Dict[str, Any], known_crypto_tickers: Set[str]) -> Set[str]:
        """Detect cryptocurrency mentions in article content."""
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
    
    def get_articles_by_indices(self, indices: List[int]) -> List[Dict[str, Any]]:
        """Get articles by their indices in the database."""
        articles = []
        for idx in indices:
            if 0 <= idx < len(self.news_database):
                articles.append(self.news_database[idx])
        return articles
    
    def search_articles_by_coin(self, coin: str) -> List[int]:
        """Search for article indices mentioning a specific coin."""
        coin_lower = coin.lower()
        results = []
        
        for i, article in enumerate(self.news_database):
            # Check detected coins
            detected_coins = article.get('detected_coins', '').lower()
            if coin_lower in detected_coins:
                results.append(i)
                continue
                
            # Check categories
            categories = article.get('categories', '').lower()
            if coin_lower in categories:
                results.append(i)
                continue
                
            # Check title and body
            title = article.get('title', '').lower()
            body = article.get('body', '').lower()
            
            if coin_lower in title or f" {coin_lower} " in f" {body} ":
                results.append(i)

        return results
    
    def format_article_date(self, article: Dict[str, Any]) -> str:
        """Format article date in a consistent way."""
        return self.article_processor.format_article_date(article)
    
    def _get_article_timestamp(self, article: Dict[str, Any]) -> float:
        """Extract timestamp from article in a consistent format."""
        return self.article_processor.get_article_timestamp(article)
    
    def get_database_size(self) -> int:
        """Get the number of articles in the database."""
        return len(self.news_database)
    
    def clear_database(self) -> None:
        """Clear the news database."""
        self.news_database.clear()
        self.latest_article_urls.clear()
