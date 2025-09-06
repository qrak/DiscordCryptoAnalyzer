"""
RSI Pattern Detection Utilities
Extracted to reduce complexity in rsi_pattern_detector.py
"""
from typing import List, Tuple, NamedTuple, Callable, Optional
import numpy as np
from datetime import datetime

from src.indicators.base.pattern_detector import MarketData, Pattern


class ThresholdCondition(NamedTuple):
    """Configuration for threshold-based conditions."""
    threshold: float
    condition_type: str
    comparison_func: Callable[[float, float], bool]
    comparison_symbol: str


class DoublePatternConfig(NamedTuple):
    """Configuration for double pattern detection."""
    pattern_type: str
    threshold: float
    similarity_threshold: float
    intermediate_ratio: float
    is_bottom_pattern: bool


class RSIExtremeResult(NamedTuple):
    """Result of finding extreme values in RSI."""
    extremes: List[int]
    intermediate_val: float
    intermediate_idx: int


def create_oversold_condition(oversold_threshold: float) -> ThresholdCondition:
    """Create configuration for oversold condition detection."""
    return ThresholdCondition(
        threshold=oversold_threshold,
        condition_type="oversold",
        comparison_func=lambda val, thresh: val < thresh,
        comparison_symbol="<"
    )


def create_overbought_condition(overbought_threshold: float) -> ThresholdCondition:
    """Create configuration for overbought condition detection."""
    return ThresholdCondition(
        threshold=overbought_threshold,
        condition_type="overbought",
        comparison_func=lambda val, thresh: val > thresh,
        comparison_symbol=">"
    )


def create_w_bottom_config(w_bottom_threshold: float, bottom_similarity: float,
                          intermediate_peak_ratio: float) -> DoublePatternConfig:
    """Create configuration for W-bottom pattern detection."""
    return DoublePatternConfig(
        pattern_type="w_bottom",
        threshold=w_bottom_threshold,
        similarity_threshold=bottom_similarity,
        intermediate_ratio=intermediate_peak_ratio,
        is_bottom_pattern=True
    )


def create_m_top_config(m_top_threshold: float, peak_similarity: float,
                       intermediate_trough_ratio: float) -> DoublePatternConfig:
    """Create configuration for M-top pattern detection."""
    return DoublePatternConfig(
        pattern_type="m_top",
        threshold=m_top_threshold,
        similarity_threshold=peak_similarity,
        intermediate_ratio=intermediate_trough_ratio,
        is_bottom_pattern=False
    )


def find_threshold_periods(recent_rsi: np.ndarray, condition: ThresholdCondition) -> List[dict]:
    """Find periods where RSI meets threshold condition."""
    periods = []
    current_condition = False
    start_idx = None
    
    for i, value in enumerate(recent_rsi):
        if condition.comparison_func(value, condition.threshold) and not current_condition:
            current_condition = True
            start_idx = i
        elif not condition.comparison_func(value, condition.threshold) and current_condition:
            extreme_value = get_extreme_value_in_range(
                recent_rsi, start_idx, i, condition.condition_type == "overbought"
            )
            periods.append({
                "start": start_idx,
                "end": i - 1,
                "duration": i - start_idx,
                f"{'max' if condition.condition_type == 'overbought' else 'min'}_value": extreme_value
            })
            current_condition = False
    
    # Handle end condition
    if current_condition:
        extreme_value = get_extreme_value_in_range(
            recent_rsi, start_idx, len(recent_rsi), condition.condition_type == "overbought"
        )
        periods.append({
            "start": start_idx,
            "end": len(recent_rsi) - 1,
            "duration": len(recent_rsi) - start_idx,
            f"{'max' if condition.condition_type == 'overbought' else 'min'}_value": extreme_value
        })
    
    return periods


def get_extreme_value_in_range(rsi_values: np.ndarray, start: int, end: int, is_maximum: bool) -> float:
    """Get extreme value (max or min) in a range."""
    segment = rsi_values[start:end]
    return np.max(segment) if is_maximum else np.min(segment)


def create_threshold_pattern(condition: ThresholdCondition, periods: List[dict], 
                           market_data: MarketData, original_start_index: int) -> Pattern:
    """Create a pattern from threshold condition detection."""
    last_period = periods[-1]
    timestamp = market_data.get_timestamp_at_index(original_start_index + last_period['end'])
    
    description = (f"RSI entered {condition.condition_type} territory "
                  f"({condition.comparison_symbol}{condition.threshold}) "
                  f"{len(periods)} times in the recent period.")
    
    return Pattern(
        condition.condition_type,
        description,
        timestamp=timestamp,
        periods=periods
    )


def find_rsi_extremes(rsi_array: np.ndarray, threshold: float, is_bottom_pattern: bool) -> List[int]:
    """Find potential extreme points in RSI array."""
    extremes = []
    for i in range(3, len(rsi_array) - 3):
        if is_bottom_pattern:
            # Looking for local minima below threshold
            if (rsi_array[i] < rsi_array[i-2] and 
                rsi_array[i] < rsi_array[i+2] and 
                rsi_array[i] < threshold):
                extremes.append(i)
        else:
            # Looking for local maxima above threshold
            if (rsi_array[i] > rsi_array[i-2] and 
                rsi_array[i] > rsi_array[i+2] and 
                rsi_array[i] > threshold):
                extremes.append(i)
    return extremes


def validate_second_extreme(rsi_array: np.ndarray, j: int, threshold: float,
                          first_idx: int, similarity_threshold: float, 
                          is_bottom_pattern: bool) -> bool:
    """Validate if a point forms a valid second extreme."""
    if is_bottom_pattern:
        return (rsi_array[j] < rsi_array[j-2] and 
                rsi_array[j] < rsi_array[j+2] and 
                rsi_array[j] < threshold and
                abs(rsi_array[first_idx] - rsi_array[j]) < similarity_threshold)
    else:
        return (rsi_array[j] > rsi_array[j-2] and 
                rsi_array[j] > rsi_array[j+2] and 
                rsi_array[j] > threshold and
                abs(rsi_array[first_idx] - rsi_array[j]) < similarity_threshold)


def get_intermediate_extreme(intermediate_segment: np.ndarray, first_idx: int, 
                           is_bottom_pattern: bool) -> Tuple[float, int]:
    """Get the intermediate extreme value and its index."""
    if is_bottom_pattern:
        # For W-bottoms, look for intermediate peak
        local_idx = np.argmax(intermediate_segment)
        intermediate_extreme_idx = local_idx + first_idx + 1
        intermediate_val = intermediate_segment[local_idx]
    else:
        # For M-tops, look for intermediate trough
        local_idx = np.argmin(intermediate_segment)
        intermediate_extreme_idx = local_idx + first_idx + 1
        intermediate_val = intermediate_segment[local_idx]
    
    return intermediate_val, intermediate_extreme_idx


def validate_intermediate_value(intermediate_val: float, first_val: float, second_val: float,
                              intermediate_ratio: float, is_bottom_pattern: bool) -> bool:
    """Validate if intermediate value meets ratio requirements."""
    avg_extreme_val = (first_val + second_val) / 2
    
    if is_bottom_pattern:
        # For W-bottoms, intermediate peak should be significantly higher
        return intermediate_val > avg_extreme_val * intermediate_ratio
    else:
        # For M-tops, intermediate trough should be significantly lower
        return intermediate_val < avg_extreme_val * intermediate_ratio


def create_double_pattern(config: DoublePatternConfig, rsi_array: np.ndarray, 
                         first_idx: int, second_idx: int, intermediate_val: float,
                         market_data: MarketData, original_start_index: int) -> Pattern:
    """Create a Pattern object for double patterns."""
    timestamp = market_data.get_timestamp_at_index(original_start_index + second_idx)
    
    if config.is_bottom_pattern:
        description = (f"W-bottom pattern detected in RSI with bottoms at {rsi_array[first_idx]:.1f} "
                      f"and {rsi_array[second_idx]:.1f}, intermediate peak at {intermediate_val:.1f}. "
                      f"Potentially bullish.")
        return Pattern(
            config.pattern_type, description, timestamp=timestamp,
            first_bottom_idx=original_start_index + first_idx,
            second_bottom_idx=original_start_index + second_idx,
            value1=rsi_array[first_idx], value2=rsi_array[second_idx],
            intermediate_peak=intermediate_val
        )
    else:
        description = (f"M-top pattern detected in RSI with peaks at {rsi_array[first_idx]:.1f} "
                      f"and {rsi_array[second_idx]:.1f}, intermediate trough at {intermediate_val:.1f}. "
                      f"Potentially bearish.")
        return Pattern(
            config.pattern_type, description, timestamp=timestamp,
            first_peak_idx=original_start_index + first_idx,
            second_peak_idx=original_start_index + second_idx,
            value1=rsi_array[first_idx], value2=rsi_array[second_idx],
            intermediate_trough=intermediate_val
        )


def should_replace_pattern(patterns: List[Pattern], new_pattern: Pattern,
                         min_separation: int, is_bottom_pattern: bool) -> bool:
    """Determine if new pattern should replace existing patterns."""
    if not patterns:
        return True
    
    last_pattern = patterns[-1]
    second_idx_attr = "second_bottom_idx" if is_bottom_pattern else "second_peak_idx"
    
    if getattr(new_pattern, second_idx_attr) < getattr(last_pattern, second_idx_attr) + min_separation // 2:
        # Check if this pattern is stronger
        avg_new = (new_pattern.value1 + new_pattern.value2) / 2
        avg_last = (last_pattern.value1 + last_pattern.value2) / 2
        
        if is_bottom_pattern:
            # For bottoms, lower is stronger
            is_stronger = avg_new < avg_last
        else:
            # For tops, higher is stronger
            is_stronger = avg_new > avg_last
        
        if is_stronger:
            patterns.pop()
            return True
        return False
    
    return True
