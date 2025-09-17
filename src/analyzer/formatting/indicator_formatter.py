"""
Consolidated Indicator Formatter.
Simplified orchestrator using the new consolidated formatting components.
"""
from typing import Optional

from ..data.data_processor import DataProcessor
from src.logger.logger import Logger
from .format_utils import format_timestamp
from .market_formatter import MarketFormatter


class IndicatorFormatter:
    """
    Orchestrates formatting of technical indicators and market data for display.
    Simplified to use consolidated formatting components.
    """
    
    def __init__(self, logger: Optional[Logger] = None):
        """Initialize the indicator formatter with consolidated components."""
        self.logger = logger
        self.data_processor = DataProcessor()
        
        # Initialize consolidated formatter
        self.market_formatter = MarketFormatter(logger)
        # Default thresholds for backward compatibility
        self.INDICATOR_THRESHOLDS = {
            'rsi': {'oversold': 30, 'overbought': 70},
            'stoch_k': {'oversold': 20, 'overbought': 80},
            'stoch_d': {'oversold': 20, 'overbought': 80},
            'adx': {'weak': 25, 'strong': 50, 'very_strong': 75},
            'mfi': {'oversold': 20, 'overbought': 80},
            'williams_r': {'oversold': -80, 'overbought': -20}
        }
        
    def format_timestamp(self, timestamp_ms) -> str:
        """Format a timestamp from milliseconds since epoch to a human-readable string."""
        try:
            formatted = format_timestamp(timestamp_ms)
            return f"({formatted}) " if formatted != "N/A" else ""
        except (ValueError, TypeError):
            return ""
            
    def format_market_period_metrics(self, market_metrics: dict) -> str:
        """Format market metrics for different time periods."""
        if not market_metrics:
            return ""
        
        # Use the consolidated formatter
        formatted_metrics = self.market_formatter.format_market_period_metrics(market_metrics)
        
        if formatted_metrics:
            return f"MARKET PERIOD METRICS:{formatted_metrics}"
        
        return ""
    
    def format_long_term_analysis(self, long_term_data: dict, current_price: float = None) -> str:
        """Format comprehensive long-term analysis from historical data."""
        return self.market_formatter.format_long_term_analysis(long_term_data, current_price)
    
    def format_coin_details_section(self, coin_details: dict) -> str:
        """Format cryptocurrency details section."""
        return self.market_formatter.format_coin_details_section(coin_details)
