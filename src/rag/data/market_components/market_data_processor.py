"""
Market Data Processing Utilities
Handles data normalization and processing operations.
"""
from datetime import datetime
from typing import Dict, Any, Optional, Union, List

from src.logger.logger import Logger


class MarketDataProcessor:
    """Handles processing and normalization of market data."""
    
    def __init__(self, logger: Logger):
        self.logger = logger
    
    def normalize_timestamp(self, timestamp_field: Union[int, float, str, None]) -> float:
        """Convert various timestamp formats to a float timestamp."""
        if timestamp_field is None:
            return 0.0

        if isinstance(timestamp_field, (int, float)):
            return float(timestamp_field)
        
        if isinstance(timestamp_field, str):
            return self._parse_timestamp_string(timestamp_field)
        
        return 0.0
    
    def _parse_timestamp_string(self, timestamp_field: str) -> float:
        """Parse timestamp string to float."""
        try:
            if timestamp_field.endswith('Z'):
                timestamp_field = timestamp_field[:-1] + '+00:00'
            return datetime.fromisoformat(timestamp_field).timestamp()
        except ValueError:
            self.logger.warning(f"Could not normalize timestamp string: {timestamp_field}")
            return 0.0
        except Exception as e:
            self.logger.error(f"Error normalizing timestamp string '{timestamp_field}': {e}")
            return 0.0
    
    def extract_top_coins(self, coingecko_data: Optional[Dict]) -> List[str]:
        """Extract top cryptocurrency symbols from CoinGecko data."""
        try:
            if not coingecko_data or 'data' not in coingecko_data:
                return []
            
            data = coingecko_data['data']
            
            # Extract market cap dominance and percentages
            if 'market_cap_percentage' in data:
                return list(data['market_cap_percentage'].keys())[:10]
            
            return []
        except Exception as e:
            self.logger.error(f"Error extracting top coins: {e}")
            return []
    
    def process_coin_data(self, values: Dict) -> Optional[Dict]:
        """Process individual coin data from market sources."""
        try:
            processed_coin = {}
            
            # Process basic information
            if 'symbol' in values:
                processed_coin['symbol'] = values['symbol'].upper()
            
            # Process price information
            for price_key in ['close', 'last', 'price']:
                if price_key in values and values[price_key] is not None:
                    processed_coin['price'] = float(values[price_key])
                    break
            
            # Process volume information
            for volume_key in ['volume', 'baseVolume', 'quoteVolume']:
                if volume_key in values and values[volume_key] is not None:
                    processed_coin['volume'] = float(values[volume_key])
                    break
            
            # Process percentage change
            for change_key in ['percentage', 'change', 'percentage_change']:
                if change_key in values and values[change_key] is not None:
                    processed_coin['change_24h'] = float(values[change_key])
                    break
            
            return processed_coin if processed_coin else None
            
        except Exception as e:
            self.logger.error(f"Error processing coin data: {e}")
            return None
