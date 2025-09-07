from typing import Dict, Any, Optional, List

import numpy as np

from .technical_calculator import TechnicalCalculator
from .pattern_analyzer import PatternAnalyzer
from ..formatting.indicator_formatter import IndicatorFormatter
from ..data.data_processor import DataProcessor
from src.logger.logger import Logger


class IndicatorCalculator:
    """Centralized calculator for technical indicators with caching capability"""
    
    def __init__(self, logger: Optional[Logger] = None):
        """Initialize the indicator calculator with component instances"""
        self.logger = logger
        
        # Initialize component instances
        self.technical_calculator = TechnicalCalculator(logger=logger)
        self.pattern_analyzer = PatternAnalyzer(logger=logger)
        self.formatter = IndicatorFormatter(logger=logger)
        self.data_processor = DataProcessor()
        
        # Maintain backward compatibility by exposing component properties
        self.ti = self.technical_calculator.ti
        self.pattern_recognizer = self.pattern_analyzer.pattern_recognizer
        
        # Cache storage - delegates to technical calculator for main cache
        self._cache = {}
        
        # Define indicator thresholds as instance variable so it's available to all methods
        self.INDICATOR_THRESHOLDS = self.technical_calculator.INDICATOR_THRESHOLDS
        
    def get_indicators(self, ohlcv_data: np.ndarray) -> Dict[str, np.ndarray]:
        """Calculate all technical indicators with caching based on data hash"""
        return self.technical_calculator.get_indicators(ohlcv_data)
        
    def get_long_term_indicators(self, ohlcv_data: np.ndarray) -> Dict[str, Any]:
        """Calculate long-term indicators for historical data."""
        return self.technical_calculator.get_long_term_indicators(ohlcv_data)
    
    def detect_patterns(self, ohlcv_data: np.ndarray, technical_history: Dict[str, np.ndarray]) -> Dict[str, Any]:
        """Detect technical patterns using the pattern recognizer"""
        return self.pattern_analyzer.detect_patterns(ohlcv_data, technical_history)
        
    def get_all_patterns(self, ohlcv_data: np.ndarray, technical_history: Dict[str, np.ndarray]) -> List[Dict]:
        """Centralized pattern detection using PatternRecognizer"""
        return self.pattern_analyzer.get_all_patterns(ohlcv_data, technical_history)

    def format_market_period_metrics(self, market_metrics: dict) -> str:
        """Format market metrics for different time periods"""
        return self.formatter.format_market_period_metrics(market_metrics)

    def format_long_term_analysis(self, long_term_data: dict, current_price: float = None) -> str:
        """Format long-term analysis from historical data"""
        return self.formatter.format_long_term_analysis(long_term_data, current_price)

    def get_indicator_value(self, td: dict, key: str):
        """Get indicator value with proper type checking and error handling
        
        Args:
            td: Technical data dictionary
            key: Indicator key to retrieve
            
        Returns:
            float or str: Indicator value or 'N/A' if invalid
        """
        return self.data_processor.get_indicator_value(td, key)
    
    def get_indicator_values(self, td: dict, key: str, expected_count: int = 2):
        """Get multiple indicator values with proper type checking
        
        Args:
            td: Technical data dictionary
            key: Indicator key to retrieve
            expected_count: Number of values expected
            
        Returns:
            list[float]: List of indicator values or empty list if invalid
        """
        return self.data_processor.get_indicator_values(td, key, expected_count)
