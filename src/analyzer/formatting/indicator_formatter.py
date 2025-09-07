"""
Refactored Indicator Formatter with reduced complexity.
Orchestrates specialized formatting components for maintainability.
"""
from typing import Optional

from ..data.data_processor import DataProcessor
from src.logger.logger import Logger
from .basic_formatter import BasicFormatter
from .market_analysis.market_metrics_formatter import MarketMetricsFormatter
from .market_analysis.long_term_formatter import LongTermFormatter


class IndicatorFormatter:
    """
    Orchestrates formatting of technical indicators and market data for display.
    Refactored to use specialized formatting components for better maintainability.
    """
    
    def __init__(self, logger: Optional[Logger] = None):
        """Initialize the indicator formatter with specialized components."""
        self.logger = logger
        self.data_processor = DataProcessor()
        
        # Initialize specialized formatters
        self.basic_formatter = BasicFormatter()
        self.market_metrics_formatter = MarketMetricsFormatter()
        self.long_term_formatter = LongTermFormatter()
        self.INDICATOR_THRESHOLDS = self.long_term_formatter.INDICATOR_THRESHOLDS
        
    def format_timestamp(self, timestamp_ms) -> str:
        """Format a timestamp from milliseconds since epoch to a human-readable string."""
        try:
            formatted = self.basic_formatter.format_timestamp(timestamp_ms)
            return f"({formatted}) " if formatted != "N/A" else ""
        except (ValueError, TypeError):
            return ""
            
    def format_market_period_metrics(self, market_metrics: dict) -> str:
        """Format market metrics for different time periods."""
        if not market_metrics:
            return ""
        
        # Use the specialized formatter
        formatted_metrics = self.market_metrics_formatter.format_market_period_metrics(market_metrics)
        
        if formatted_metrics:
            return f"MARKET PERIOD METRICS:{formatted_metrics}"
        
        return ""
    
    def format_long_term_analysis(self, long_term_data: dict, current_price: float = None) -> str:
        """Format comprehensive long-term analysis from historical data."""
        return self.long_term_formatter.format_long_term_analysis(long_term_data, current_price)
