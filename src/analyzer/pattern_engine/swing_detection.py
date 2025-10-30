import numpy as np
from numba import njit
from src.indicators.indicators.statistical.utils.dsp_filters import f_ess


@njit(cache=True)
def detect_swing_highs_numba(high: np.ndarray, lookback: int = 5, lookahead: int = 5) -> np.ndarray:
    n = len(high)
    swings = np.zeros(n, dtype=np.bool_)
    
    for i in range(lookback, n - lookahead):
        is_swing = True
        current_high = high[i]
        
        for j in range(i - lookback, i):
            if high[j] >= current_high:
                is_swing = False
                break
        
        if is_swing:
            for j in range(i + 1, i + lookahead + 1):
                if high[j] >= current_high:
                    is_swing = False
                    break
        
        swings[i] = is_swing
    
    return swings


@njit(cache=True)
def detect_swing_lows_numba(low: np.ndarray, lookback: int = 5, lookahead: int = 5) -> np.ndarray:
    n = len(low)
    swings = np.zeros(n, dtype=np.bool_)
    
    for i in range(lookback, n - lookahead):
        is_swing = True
        current_low = low[i]
        
        for j in range(i - lookback, i):
            if low[j] <= current_low:
                is_swing = False
                break
        
        if is_swing:
            for j in range(i + 1, i + lookahead + 1):
                if low[j] <= current_low:
                    is_swing = False
                    break
        
        swings[i] = is_swing
    
    return swings


@njit(cache=True)
def classify_swings_numba(high: np.ndarray, low: np.ndarray, 
                         swing_highs: np.ndarray, swing_lows: np.ndarray) -> np.ndarray:
    n = len(high)
    classifications = np.zeros(n, dtype=np.int32)
    
    last_swing_high = -1.0
    last_swing_low = -1.0
    
    for i in range(n):
        if swing_highs[i]:
            if last_swing_high > 0:
                if high[i] > last_swing_high:
                    classifications[i] = 1
                else:
                    classifications[i] = 2
            last_swing_high = high[i]
            
        if swing_lows[i]:
            if last_swing_low > 0:
                if low[i] < last_swing_low:
                    classifications[i] = 4
                else:
                    classifications[i] = 3
            last_swing_low = low[i]
    
    return classifications


def detect_swings_smoothed(high: np.ndarray, low: np.ndarray, 
                          smooth_length: int = 10,
                          lookback: int = 5, 
                          lookahead: int = 5) -> tuple:
    smoothed_high = f_ess(high, smooth_length)
    smoothed_low = f_ess(low, smooth_length)
    
    swing_highs = detect_swing_highs_numba(smoothed_high, lookback, lookahead)
    swing_lows = detect_swing_lows_numba(smoothed_low, lookback, lookahead)
    
    return swing_highs, swing_lows
