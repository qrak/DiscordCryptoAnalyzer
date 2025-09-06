"""
Market Data Cache Manager
Handles caching and storage of market overview data.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from src.logger.logger import Logger
from ..file_handler import RagFileHandler


class MarketDataCache:
    """Handles caching and storage operations for market data."""
    
    def __init__(self, logger: Logger, file_handler: RagFileHandler):
        self.logger = logger
        self.file_handler = file_handler
        self.current_market_overview: Optional[Dict[str, Any]] = None
        self.coingecko_last_update: Optional[datetime] = None
    
    async def load_cached_market_overview(self) -> Optional[Dict[str, Any]]:
        """Load cached market overview data from disk."""
        try:
            market_overview_file = self.file_handler.get_market_overview_path()
            self.current_market_overview = self.file_handler.load_json_file(market_overview_file)
            return self.current_market_overview
        except Exception as e:
            self.logger.error(f"Error loading cached market overview: {e}")
            return None
    
    async def save_market_overview(self, market_overview: Dict[str, Any]) -> None:
        """Save market overview data to disk."""
        try:
            market_overview_file = self.file_handler.get_market_overview_path()
            self.file_handler.save_json_file(market_overview_file, market_overview)
            self.current_market_overview = market_overview
            self.coingecko_last_update = datetime.now()
            self.logger.debug("Market overview updated and saved.")
        except Exception as e:
            self.logger.error(f"Error saving market overview: {e}")
    
    def get_current_overview(self) -> Optional[Dict[str, Any]]:
        """Get the current market overview data."""
        return self.current_market_overview
    
    def is_overview_stale(self, max_age_hours: int = 1, normalize_timestamp_func=None) -> bool:
        """Check if the current market overview is stale."""
        if self.current_market_overview is None:
            return True
            
        timestamp_field = self.current_market_overview.get('published_on',
                                                           self.current_market_overview.get('timestamp', 0))
        
        if normalize_timestamp_func:
            timestamp = normalize_timestamp_func(timestamp_field)
        else:
            # Fallback simple normalization
            timestamp = float(timestamp_field) if isinstance(timestamp_field, (int, float)) else 0
        
        if timestamp:
            data_time = datetime.fromtimestamp(timestamp)
            current_time = datetime.now()
            return current_time - data_time > timedelta(hours=max_age_hours)
        
        return True
    
    def should_update_market_data(self, max_age_hours: int = 24) -> bool:
        """Check if market data should be updated."""
        if not self.coingecko_last_update:
            return True
        
        time_since_update = datetime.now() - self.coingecko_last_update
        return time_since_update > timedelta(hours=max_age_hours)
