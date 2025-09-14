import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Union

from config.config import DATA_DIR
from src.logger.logger import Logger


class RagFileHandler:
    NEWS_FILE = "crypto_news.json"
    MARKET_DATA_DIR = "market_data"
    COINGECKO_CACHE_FILE = "coingecko_global.json"
    
    def __init__(self, logger: Logger):
        self.logger = logger
        self.base_dir = self._resolve_base_dir()
        self.data_dir = os.path.join(self.base_dir, DATA_DIR)
        self.market_data_dir = os.path.join(self.data_dir, self.MARKET_DATA_DIR)
        self.news_file_path = os.path.join(self.data_dir, self.NEWS_FILE)
        self.tickers_file = os.path.join(self.data_dir, "known_tickers.json")
        self._last_news_save_time = 0
        
        self.setup_directories()
    
    def _normalize_timestamp(self, timestamp_field: Union[int, float, str, None]) -> float:
        """Convert various timestamp formats to a float timestamp."""
        if timestamp_field is None:
            return 0.0

        # Handle numeric timestamps
        if isinstance(timestamp_field, (int, float)):
            return float(timestamp_field)
        
        # Handle string timestamps
        if isinstance(timestamp_field, str):
            try:
                # Try to parse as numeric string first
                return float(timestamp_field)
            except ValueError:
                try:
                    # Normalize Z timezone indicator
                    normalized_str = timestamp_field.replace('Z', '+00:00')
                    return datetime.fromisoformat(normalized_str).timestamp()
                except (ValueError, Exception) as e:
                    self.logger.warning(f"Could not normalize timestamp '{timestamp_field}': {e}")
        
        return 0.0
    
    def setup_directories(self):
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.market_data_dir, exist_ok=True)
        self.logger.debug("Initialized RAG file directories")
    
    def _resolve_base_dir(self) -> str:
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        else:
            # __file__ is inside src/rag/data; go up four levels to reach project root
            return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        
    def load_json_file(self, file_path: str) -> Optional[Dict]:
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        except Exception as e:
            self.logger.error(f"Error loading JSON file {file_path}: {e}")
            return None

    def save_json_file(self, file_path: str, data: Dict):
        try:
            # Atomic write: write to temporary file first, then rename
            temp_path = f"{file_path}.tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # Atomic operation: rename temp file to target
            os.replace(temp_path, file_path)
        except Exception as e:
            # Clean up temp file if it exists
            temp_path = f"{file_path}.tmp"
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            self.logger.error(f"Error saving JSON file {file_path}: {e}")
        
    def save_news_articles(self, articles: List[Dict]):
        if not articles:
            return
        
        # Prevent saving more than once per second to avoid duplicate writes during shutdown
        current_time = time.time()
        if current_time - self._last_news_save_time < 1:
            self.logger.debug("Skipping news save, too soon after previous save")
            return
            
        self._last_news_save_time = current_time
            
        current_timestamp = datetime.now().timestamp()
        one_day_ago = current_timestamp - 86400
        
        recent_articles = []
        for art in articles:
            article_timestamp = self._normalize_timestamp(art.get('published_on', 0))
            if article_timestamp > one_day_ago:
                recent_articles.append(art)
        
        if not recent_articles:
            self.logger.debug("No recent articles to save")
            return

        try:
            recent_articles.sort(key=lambda x: self._normalize_timestamp(x.get('published_on', 0)), reverse=True)
            
            news_data = {
                'last_updated': datetime.now().isoformat(),
                'count': len(recent_articles),
                'articles': recent_articles
            }
            
            self.save_json_file(self.news_file_path, news_data)
            self.logger.debug(f"Saved {len(recent_articles)} recent news articles")
            
        except Exception as e:
            self.logger.error(f"Error saving news articles: {e}")

    def load_news_articles(self) -> List[Dict]:
        try:
            data = self.load_json_file(self.news_file_path)
            
            if not data or 'articles' not in data:
                self.logger.debug("No news articles found in file or empty file")
                return []
                
            articles = data.get('articles', [])
            
            current_timestamp = datetime.now().timestamp()
            one_day_ago = current_timestamp - 86400
            
            recent_articles = []
            for art in articles:
                article_timestamp = self._normalize_timestamp(art.get('published_on', 0))
                if article_timestamp > one_day_ago:
                    recent_articles.append(art)
            
            if len(recent_articles) < len(articles):
                self.logger.debug(f"Filtered out {len(articles) - len(recent_articles)} articles older than 24 hours")
            
            return recent_articles
                
        except Exception as e:
            self.logger.error(f"Error loading news articles: {e}")
            return []
    
    def load_fallback_articles(self, max_age_hours: int = 72) -> List[Dict]:
        """Load articles from file with extended age for fallback when API fails"""
        try:
            data = self.load_json_file(self.news_file_path)
            
            if not data or 'articles' not in data:
                return []
                
            articles = data.get('articles', [])
            
            current_timestamp = datetime.now().timestamp()
            cutoff_time = current_timestamp - (max_age_hours * 3600)  # Convert hours to seconds
            
            fallback_articles = []
            for art in articles:
                article_timestamp = self._normalize_timestamp(art.get('published_on', 0))
                if article_timestamp > cutoff_time:
                    fallback_articles.append(art)
            
            if fallback_articles:
                self.logger.debug(f"Using {len(fallback_articles)} cached articles as fallback")
                
            return fallback_articles
                
        except Exception as e:
            self.logger.error(f"Error loading fallback news articles: {e}")
            return []
            
    def filter_recent_articles(self, articles: List[Dict]) -> List[Dict]:
        current_timestamp = datetime.now().timestamp()
        one_day_ago = current_timestamp - 86400
        
        recent_articles = []
        for art in articles:
            article_timestamp = self._normalize_timestamp(art.get('published_on', 0))
            if article_timestamp > one_day_ago:
                recent_articles.append(art)
        
        return recent_articles
    
    def load_known_tickers(self) -> Optional[List[str]]:
        """Load known tickers from disk."""
        try:
            data = self.load_json_file(self.tickers_file)
            if data and 'tickers' in data:
                return data['tickers']
            return None
        except Exception as e:
            self.logger.error(f"Error loading known tickers: {e}")
            return None
    
    def save_known_tickers(self, tickers: List[str]) -> None:
        """Save known tickers to disk."""
        try:
            data = {"tickers": tickers}
            self.save_json_file(self.tickers_file, data)
        except Exception as e:
            self.logger.error(f"Error saving known tickers: {e}")