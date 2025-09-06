import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

from config.config import DATA_DIR
from src.logger.logger import Logger


class RagFileHandler:
    NEWS_FILE = "crypto_news.json"
    MARKET_OVERVIEW_FILE = "market_overview.json"
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
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving JSON file {file_path}: {e}")

    def file_exists(self, file_path: str) -> bool:
        return os.path.exists(file_path)

    def get_market_overview_path(self) -> str:
        return os.path.join(self.market_data_dir, self.MARKET_OVERVIEW_FILE)
    
    def get_news_file_path(self) -> str:
        return self.news_file_path

    def get_tickers_file_path(self) -> str:
        return self.tickers_file
        
    def get_categories_file_path(self) -> str:
        return os.path.join(self.data_dir, "categories.json")
        
    def get_coingecko_cache_path(self) -> str:
        return os.path.join(self.market_data_dir, self.COINGECKO_CACHE_FILE)
        
    def save_news_articles(self, articles: List[Dict]):
        if not articles:
            return
        
        # Prevent saving more than once per second to avoid duplicate writes during shutdown
        current_time = time.time()
        if current_time - self._last_news_save_time < 1:
            self.logger.debug("Skipping news save, too soon after previous save")
            return
            
        self._last_news_save_time = current_time
            
        current_time = datetime.now().timestamp()
        one_day_ago = current_time - 86400
        recent_articles = [art for art in articles if art.get('published_on', 0) > one_day_ago]
        
        if not recent_articles:
            self.logger.debug("No recent articles to save")
            return

        try:
            recent_articles.sort(key=lambda x: x.get('published_on', 0), reverse=True)
            
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
            
            current_time = datetime.now().timestamp()
            one_day_ago = current_time - 86400
            recent_articles = [art for art in articles if art.get('published_on', 0) > one_day_ago]
            
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
            
            current_time = datetime.now().timestamp()
            cutoff_time = current_time - (max_age_hours * 3600)  # Convert hours to seconds
            fallback_articles = [art for art in articles if art.get('published_on', 0) > cutoff_time]
            
            if fallback_articles:
                self.logger.debug(f"Using {len(fallback_articles)} cached articles as fallback")
                
            return fallback_articles
                
        except Exception as e:
            self.logger.error(f"Error loading fallback news articles: {e}")
            return []
            
    def filter_recent_articles(self, articles: List[Dict]) -> List[Dict]:
        current_time = datetime.now().timestamp()
        one_day_ago = current_time - 86400
        recent_articles = [art for art in articles if art.get('published_on', 0) > one_day_ago]
        
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