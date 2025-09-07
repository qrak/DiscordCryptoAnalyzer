"""
Base formatter class for technical analysis formatters.
Provides common formatting utilities to eliminate code duplication.
"""

import numpy as np
from ..basic_formatter import fmt


class BaseTechnicalFormatter:
    """Base class for technical analysis formatters with common utilities."""
    
    def __init__(self, indicator_calculator, logger=None):
        """Initialize base formatter with indicator calculator and logger.
        
        Args:
            indicator_calculator: IndicatorCalculator instance for value retrieval
            logger: Optional logger instance for debugging
        """
        self.indicator_calculator = indicator_calculator
        self.logger = logger
    
    def _fmt_ta(self, key: str, td: dict, precision: int = 8, default: str = 'N/A') -> str:
        """Format technical analysis value safely.
        
        Args:
            key: Indicator key to format
            td: Technical data dictionary
            precision: Number of decimal places
            default: Default value if indicator unavailable
            
        Returns:
            str: Formatted value or default
        """
        val = self.indicator_calculator.get_indicator_value(td, key)
        if isinstance(val, (int, float)) and not np.isnan(val):
            return fmt(val, precision)
        return default
    
    def _is_valid_value(self, value) -> bool:
        """Check if a value is valid for formatting.
        
        Args:
            value: Value to check
            
        Returns:
            bool: True if value is valid number, False otherwise
        """
        return isinstance(value, (int, float)) and not np.isnan(value)
    
    def _fmt_val(self, value, precision: int = 8) -> str:
        """Format a value with specified precision.
        
        Args:
            value: Value to format
            precision: Number of decimal places
            
        Returns:
            str: Formatted value or 'N/A' if invalid
        """
        if self._is_valid_value(value):
            return fmt(value, precision)
        return 'N/A'
