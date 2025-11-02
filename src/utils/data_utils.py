"""
Data utilities for hashing and processing numpy arrays.
Shared utilities to avoid code duplication.
"""
import numpy as np


def hash_data(data: np.ndarray) -> str:
    """Create a simple hash of the data for caching
    
    Args:
        data: Numpy array to hash
        
    Returns:
        str: Hash string representing the data
    """
    if data is None or len(data) == 0:
        return "empty"
        
    # Use last few candles and length for hashing
    # This is faster than hashing the entire array
    try:
        last_candle = data[-1].tobytes()
        data_len = len(data)
        return f"{hash(last_candle)}_{data_len}"
    except (AttributeError, IndexError):
        # Fallback if tobytes() is not available
        return str(hash(str(data[-1])) + len(data))
