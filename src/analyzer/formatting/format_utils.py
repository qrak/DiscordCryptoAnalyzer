"""
Consolidated formatting utilities for the analyzer.
Contains all shared formatting functions and utilities.
"""
import numpy as np
from datetime import datetime
from typing import Any, Optional


def fmt(val, precision=8):
    """Format a value with appropriate precision based on its magnitude"""
    if isinstance(val, (int, float)) and not np.isnan(val):
        if 0 < abs(val) < 0.000001:
            return f"{val:.{precision}e}"  # Scientific notation for very small values
        elif abs(val) < 0.001:
            return f"{val:.{max(precision, 8)}f}"  # More decimal places for small values
        elif abs(val) < 0.01:
            return f"{val:.6f}"
        elif abs(val) < 0.1:
            return f"{val:.4f}"
        elif abs(val) < 10:
            return f"{val:.{precision}f}"
        else:
            return f"{val:.2f}"
    return "N/A"


def fmt_ta(indicator_calculator, td: dict, key: str, precision: int = 8, default: str = 'N/A') -> str:
    """Format technical-analysis indicator values.
    
    Centralizes the logic used across all formatter classes.
    
    Args:
        indicator_calculator: IndicatorCalculator instance
        td: Technical data dictionary
        key: Indicator key to retrieve
        precision: Number of decimal places
        default: Default value if indicator not found
        
    Returns:
        Formatted indicator value string
    """
    try:
        val = indicator_calculator.get_indicator_value(td, key)
    except Exception:
        return default

    if isinstance(val, (int, float)) and not np.isnan(val):
        return fmt(val, precision)
    return default


def format_timestamp(timestamp_ms) -> str:
    """Format a timestamp from milliseconds since epoch to a human-readable string
    
    Args:
        timestamp_ms: Timestamp in milliseconds
        
    Returns:
        Human-readable datetime string
    """
    try:
        dt = datetime.fromtimestamp(timestamp_ms / 1000)
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError, OSError):
        return "N/A"


def is_valid_value(value) -> bool:
    """Check if a value is valid for formatting.
    
    Args:
        value: Value to check
        
    Returns:
        bool: True if value is valid number, False otherwise
    """
    return isinstance(value, (int, float)) and not np.isnan(value)


def format_value(value, precision: int = 8) -> str:
    """Format a value with specified precision.
    
    Args:
        value: Value to format
        precision: Number of decimal places
        
    Returns:
        str: Formatted value or 'N/A' if invalid
    """
    if is_valid_value(value):
        return fmt(value, precision)
    return 'N/A'


def get_supertrend_direction_string(direction) -> str:
    """Get supertrend direction as string."""
    if direction > 0:
        return 'Bullish'
    elif direction < 0:
        return 'Bearish'
    else:
        return 'Neutral'


def format_bollinger_interpretation(indicator_calculator, td: dict) -> str:
    """Format Bollinger Bands interpretation."""
    try:
        bb_position = indicator_calculator.get_indicator_value(td, 'bb_position')
        if bb_position is not None:
            if bb_position > 0.8:
                return " [Near upper band - possible overbought]"
            elif bb_position < 0.2:
                return " [Near lower band - possible oversold]"
            else:
                return " [Within normal range]"
    except Exception:
        pass
    return ""


def format_cmf_interpretation(indicator_calculator, td: dict) -> str:
    """Format Chaikin Money Flow interpretation."""
    try:
        cmf_val = indicator_calculator.get_indicator_value(td, 'cmf')
        if cmf_val is not None:
            if cmf_val > 0.1:
                return " [Accumulation phase]"
            elif cmf_val < -0.1:
                return " [Distribution phase]"
            else:
                return " [Neutral]"
    except Exception:
        pass
    return ""