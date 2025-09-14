"""
Basic formatting utilities for analyzers.
"""
import numpy as np
from datetime import datetime


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
    """Public helper to format technical-analysis indicator values.

    This centralizes the logic used across many formatter classes so there
    is only one canonical implementation.
    """
    try:
        val = indicator_calculator.get_indicator_value(td, key)
    except Exception:
        return default

    if isinstance(val, (int, float)) and not np.isnan(val):
        return fmt(val, precision)
    return default


class BasicFormatter:
    """Basic formatting utilities for timestamps and common data types."""
    
    def format_timestamp(self, timestamp_ms) -> str:
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
