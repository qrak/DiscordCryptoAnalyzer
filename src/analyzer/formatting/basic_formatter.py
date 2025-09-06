"""
Basic formatting utilities for analyzers.
"""
import numpy as np
from datetime import datetime


def fmt(val, precision=8):
    """Format a value with appropriate precision based on its magnitude"""
    if isinstance(val, (int, float)) and not np.isnan(val):
        if abs(val) > 0 and abs(val) < 0.000001:
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
    
    def format_percentage(self, value: float, precision: int = 2) -> str:
        """Format a value as a percentage string."""
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return "N/A"
        try:
            return f"{value:.{precision}f}%"
        except (ValueError, TypeError):
            return "N/A"
    
    def format_currency(self, value: float, precision: int = 2) -> str:
        """Format a value as a currency string."""
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return "N/A"
        try:
            if abs(value) >= 1_000_000:
                return f"${value/1_000_000:.{precision}f}M"
            elif abs(value) >= 1_000:
                return f"${value/1_000:.{precision}f}K"
            else:
                return f"${value:.{precision}f}"
        except (ValueError, TypeError):
            return "N/A"
