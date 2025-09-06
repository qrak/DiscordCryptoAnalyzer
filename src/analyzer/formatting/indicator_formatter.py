"""
Refactored Indicator Formatter with reduced complexity.
Orchestrates specialized formatting components for maintainability.
"""
from typing import Dict, Any, Optional

from ..data.data_processor import DataProcessor
from src.logger.logger import Logger
from .basic_formatter import BasicFormatter
from .market_analysis.market_metrics_formatter import MarketMetricsFormatter
from .market_analysis.long_term_formatter import LongTermFormatter
from .technical_analysis.technical_formatter import TechnicalAnalysisFormatter


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
        # Note: TechnicalAnalysisFormatter requires indicator_calculator, will be set later if needed
        
        # Maintain backward compatibility with threshold definitions
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
    
    # Delegate specific section formatting to the indicator section formatter
    def _format_sma_section(self, long_term_data: dict) -> str:
        """Format Simple Moving Average analysis section."""
        return self.indicator_section_formatter.format_sma_section(long_term_data)
    
    def _format_volume_sma_section(self, long_term_data: dict) -> str:
        """Format Volume Simple Moving Average analysis section."""
        return self.indicator_section_formatter.format_volume_sma_section(long_term_data)
    
    def _format_price_position_section(self, long_term_data: dict, current_price: float) -> str:
        """Format price position relative to moving averages."""
        return self.indicator_section_formatter.format_price_position_section(long_term_data, current_price)
    
    def _format_daily_indicators_section(self, long_term_data: dict, current_price: float) -> str:
        """Format current daily indicators section with detailed analysis."""
        return self.indicator_section_formatter.format_daily_indicators_section(long_term_data, current_price)
    
    def _format_adx_section(self, long_term_data: dict) -> str:
        """Format ADX (Average Directional Index) analysis section."""
        return self.indicator_section_formatter.format_adx_section(long_term_data)
    
    def _format_ichimoku_section(self, long_term_data: dict, current_price: float) -> str:
        """Format Ichimoku Cloud analysis section."""
        return self.indicator_section_formatter.format_ichimoku_section(long_term_data, current_price)
    
    # Legacy method support for backward compatibility
    def _format_no_data_analysis(self) -> str:
        """Format message when no long-term data is available."""
        return self.long_term_formatter._format_no_data_analysis()
    
    def _format_new_token_analysis(self, long_term_data: dict) -> str:
        """Format analysis for tokens with limited historical data."""
        return self.long_term_formatter._format_new_token_analysis(long_term_data)
    
    # Legacy methods for backward compatibility (delegated to new formatters)
    def _format_period_price_section(self, metrics: dict) -> list:
        """Legacy method: Format price-related metrics for a period."""
        return self.market_metrics_formatter._format_period_price_section(metrics)
    
    def _format_period_volume_section(self, metrics: dict) -> list:
        """Legacy method: Format volume-related metrics for a period."""
        return self.market_metrics_formatter._format_period_volume_section(metrics)
    
    def _format_indicator_changes_section(self, indicator_changes: dict, period_name: str) -> list:
        """Legacy method: Format indicator changes for a period."""
        return self.market_metrics_formatter._format_indicator_changes_section(indicator_changes, period_name)
