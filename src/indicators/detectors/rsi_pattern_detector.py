from typing import List, Tuple, NamedTuple, Callable
import numpy as np

from src.indicators.base.pattern_detector import BasePatternDetector, MarketData, Pattern, RSISettings
from src.analyzer.formatting.format_utils import FormatUtils


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


class RSIPatternDetector(BasePatternDetector):
    """Detector for RSI patterns like oversold/overbought conditions, W-bottoms, and M-tops"""
    
    def __init__(self, settings: RSISettings, logger=None):
        super().__init__(settings, logger)
        self.overbought = settings.overbought
        self.oversold = settings.oversold
        self.w_bottom_threshold = settings.w_bottom_threshold
        self.m_top_threshold = settings.m_top_threshold 
        self.bottom_similarity = settings.bottom_similarity
        self.peak_similarity = settings.peak_similarity 
        self.intermediate_peak_ratio = settings.intermediate_peak_ratio 
        self.intermediate_trough_ratio = settings.intermediate_trough_ratio
        self.format_utils = FormatUtils() 

    def detect(self, data: MarketData) -> List[Pattern]:
        if not self._validate_input(data):
            return []
        
        patterns = []
        rsi_values = data.get_indicator_history("rsi") # Returns np.ndarray now
        
        if len(rsi_values) < 14:
            return []
        
        # Determine the slice of RSI and corresponding indices in the original data
        num_recent = min(30, len(rsi_values))
        recent_rsi = rsi_values[-num_recent:]
        original_start_index = len(data.ohlcv) - num_recent # Map recent_rsi index back to original ohlcv index
        
        # Detect oversold patterns
        oversold_patterns = self._detect_oversold(recent_rsi, data, original_start_index)
        patterns.extend(oversold_patterns)
        
        # Detect overbought patterns
        overbought_patterns = self._detect_overbought(recent_rsi, data, original_start_index)
        patterns.extend(overbought_patterns)
        
        # Detect W-bottoms (double bottom in RSI)
        w_bottom_patterns = self._detect_w_bottoms(recent_rsi, data, original_start_index)
        patterns.extend(w_bottom_patterns)

        # Detect M-tops (double top in RSI)
        m_top_patterns = self._detect_m_tops(recent_rsi, data, original_start_index)
        patterns.extend(m_top_patterns)
        
        return patterns
    
    def _detect_threshold_condition(self, recent_rsi: np.ndarray, market_data: MarketData, 
                                   original_start_index: int, condition: ThresholdCondition) -> List[Pattern]:
        """Detect threshold-based conditions using configuration."""
        periods = self.find_threshold_periods(recent_rsi, condition)
        
        if periods:
            pattern = self.create_threshold_pattern(condition, periods, market_data, original_start_index)
            self._log_detection(pattern)
            return [pattern]
        
        return []
    
    def _detect_oversold(self, recent_rsi: np.ndarray, market_data: MarketData, original_start_index: int) -> List[Pattern]:
        """Detect oversold conditions using configuration."""
        condition = self.create_oversold_condition(self.oversold)
        return self._detect_threshold_condition(recent_rsi, market_data, original_start_index, condition)
    
    def _detect_overbought(self, recent_rsi: np.ndarray, market_data: MarketData, original_start_index: int) -> List[Pattern]:
        """Detect overbought conditions using configuration."""
        condition = self.create_overbought_condition(self.overbought)
        return self._detect_threshold_condition(recent_rsi, market_data, original_start_index, condition)
    
    def _detect_w_bottoms(self, recent_rsi: np.ndarray, market_data: MarketData, original_start_index: int) -> List[Pattern]:
        """Detect W-bottom patterns using configuration."""
        config = self.create_w_bottom_config(self.w_bottom_threshold, self.bottom_similarity, self.intermediate_peak_ratio)
        return self._detect_double_pattern(recent_rsi, market_data, original_start_index, config)
    
    def _detect_m_tops(self, recent_rsi: np.ndarray, market_data: MarketData, original_start_index: int) -> List[Pattern]:
        """Detect M-top patterns using configuration.""" 
        config = self.create_m_top_config(self.m_top_threshold, self.peak_similarity, self.intermediate_trough_ratio)
        return self._detect_double_pattern(recent_rsi, market_data, original_start_index, config)
    
    def _detect_double_pattern(self, recent_rsi: np.ndarray, market_data: MarketData, 
                              original_start_index: int, config: DoublePatternConfig) -> List[Pattern]:
        """Detect double patterns using configuration."""
        patterns = []
        min_separation = 5
        
        if len(recent_rsi) < 14:
            return patterns

        # Find potential first extremes
        potential_first_extremes = self.find_rsi_extremes(recent_rsi, config.threshold, config.is_bottom_pattern)
        
        # Look for matching second extremes
        for i in potential_first_extremes:
            pattern = self._find_matching_extreme(recent_rsi, i, config, market_data, original_start_index, min_separation)
            if pattern:
                # Check for overlaps and add pattern
                if self.should_replace_pattern(patterns, pattern, min_separation, config.is_bottom_pattern):
                    self._log_detection(pattern)
                    patterns.append(pattern)
                    break  # Don't need to check further j for this i
        
        return patterns
    
    def _find_matching_extreme(self, rsi_array: np.ndarray, first_idx: int, config: DoublePatternConfig,
                              market_data: MarketData, original_start_index: int, min_separation: int) -> Pattern | None:
        """Find a matching second extreme using configuration."""
        search_start = first_idx + min_separation
        search_end = min(first_idx + 15, len(rsi_array) - 3)

        for j in range(search_start, search_end):
            if self.validate_second_extreme(rsi_array, j, config.threshold, first_idx, 
                                     config.similarity_threshold, config.is_bottom_pattern):
                # Validate intermediate value
                intermediate_segment = rsi_array[first_idx+1:j]
                if len(intermediate_segment) > 0:
                    intermediate_val, _ = self.get_intermediate_extreme(
                        intermediate_segment, first_idx, config.is_bottom_pattern
                    )
                    
                    if self.validate_intermediate_value(
                        intermediate_val, float(rsi_array[first_idx]), float(rsi_array[j]), 
                        config.intermediate_ratio, config.is_bottom_pattern
                    ):
                        return self.create_double_pattern(
                            config, rsi_array, first_idx, j, intermediate_val,
                            market_data, original_start_index
                        )
        return None

    def create_oversold_condition(self, oversold_threshold: float) -> ThresholdCondition:
        """Create configuration for oversold condition detection."""
        return ThresholdCondition(
            threshold=oversold_threshold,
            condition_type="oversold",
            comparison_func=lambda val, thresh: val < thresh,
            comparison_symbol="<"
        )

    def create_overbought_condition(self, overbought_threshold: float) -> ThresholdCondition:
        """Create configuration for overbought condition detection."""
        return ThresholdCondition(
            threshold=overbought_threshold,
            condition_type="overbought",
            comparison_func=lambda val, thresh: val > thresh,
            comparison_symbol=">"
        )

    def create_w_bottom_config(self, w_bottom_threshold: float, bottom_similarity: float,
                              intermediate_peak_ratio: float) -> DoublePatternConfig:
        """Create configuration for W-bottom pattern detection."""
        return DoublePatternConfig(
            pattern_type="w_bottom",
            threshold=w_bottom_threshold,
            similarity_threshold=bottom_similarity,
            intermediate_ratio=intermediate_peak_ratio,
            is_bottom_pattern=True
        )

    def create_m_top_config(self, m_top_threshold: float, peak_similarity: float,
                           intermediate_trough_ratio: float) -> DoublePatternConfig:
        """Create configuration for M-top pattern detection."""
        return DoublePatternConfig(
            pattern_type="m_top",
            threshold=m_top_threshold,
            similarity_threshold=peak_similarity,
            intermediate_ratio=intermediate_trough_ratio,
            is_bottom_pattern=False
        )

    def find_threshold_periods(self, recent_rsi: np.ndarray, condition: ThresholdCondition) -> List[dict]:
        """Find periods where RSI meets threshold condition."""
        periods = []
        current_condition = False
        start_idx = None
        
        for i, value in enumerate(recent_rsi):
            if condition.comparison_func(value, condition.threshold) and not current_condition:
                current_condition = True
                start_idx = i
            elif not condition.comparison_func(value, condition.threshold) and current_condition:
                extreme_value = self.get_extreme_value_in_range(
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
            extreme_value = self.get_extreme_value_in_range(
                recent_rsi, start_idx, len(recent_rsi), condition.condition_type == "overbought"
            )
            periods.append({
                "start": start_idx,
                "end": len(recent_rsi) - 1,
                "duration": len(recent_rsi) - start_idx,
                f"{'max' if condition.condition_type == 'overbought' else 'min'}_value": extreme_value
            })
        
        return periods

    def get_extreme_value_in_range(self, rsi_values: np.ndarray, start: int, end: int, is_maximum: bool) -> float:
        """Get extreme value (max or min) in a range."""
        segment = rsi_values[start:end]
        return float(np.max(segment) if is_maximum else np.min(segment))

    def create_threshold_pattern(self, condition: ThresholdCondition, periods: List[dict], 
                               market_data: MarketData, original_start_index: int) -> Pattern:
        """Create a pattern from threshold condition detection with enhanced timing info."""
        last_period = periods[-1]
        timestamp = market_data.get_timestamp_at_index(original_start_index + last_period['end'])
        
        # Enhanced description with duration and active status
        total_occurrences = len(periods)
        duration = last_period.get('duration', 1)
        is_active = last_period.get('end') >= len(periods) - 1
        
        # Calculate periods ago for the most recent occurrence
        current_period_index = len(periods) - 1
        periods_ago = current_period_index - last_period['end']
        
        # Use instance formatting utilities
        if is_active and duration > 1:
            duration_text = self.format_utils.format_pattern_duration(duration, is_active=True)
            periods_ago_text = self.format_utils.format_periods_ago_with_context(periods_ago + duration - 1)
            description = (f"RSI {condition.condition_type} (>{condition.threshold}) for {duration_text} "
                          f"(started {periods_ago_text}). "
                          f"Total occurrences in recent period: {total_occurrences}")
        elif duration > 1:
            duration_text = self.format_utils.format_pattern_duration(duration, is_active=False)
            periods_ago_text = self.format_utils.format_periods_ago_with_context(periods_ago)
            description = (f"RSI {condition.condition_type} lasted {duration_text} "
                          f"(ended {periods_ago_text}). "
                          f"Total occurrences in recent period: {total_occurrences}")
        else:
            description = (f"RSI entered {condition.condition_type} territory "
                          f"({condition.comparison_symbol}{condition.threshold}) "
                          f"{len(periods)} times in the recent period.")
        
        return Pattern(
            condition.condition_type,
            description,
            timestamp=timestamp,
            periods=periods,
            duration=duration,
            periods_ago=periods_ago,
            is_active=is_active
        )

    def find_rsi_extremes(self, rsi_array: np.ndarray, threshold: float, is_bottom_pattern: bool) -> List[int]:
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

    def validate_second_extreme(self, rsi_array: np.ndarray, j: int, threshold: float,
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

    def get_intermediate_extreme(self, intermediate_segment: np.ndarray, first_idx: int, 
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
        
        return float(intermediate_val), intermediate_extreme_idx

    def validate_intermediate_value(self, intermediate_val: float, first_val: float, second_val: float,
                                  intermediate_ratio: float, is_bottom_pattern: bool) -> bool:
        """Validate if intermediate value meets ratio requirements."""
        avg_extreme_val = (first_val + second_val) / 2
        
        if is_bottom_pattern:
            # For W-bottoms, intermediate peak should be significantly higher
            return intermediate_val > avg_extreme_val * intermediate_ratio
        else:
            # For M-tops, intermediate trough should be significantly lower
            return intermediate_val < avg_extreme_val * intermediate_ratio

    def create_double_pattern(self, config: DoublePatternConfig, rsi_array: np.ndarray, 
                             first_idx: int, second_idx: int, intermediate_val: float,
                             market_data: MarketData, original_start_index: int) -> Pattern:
        """Create a Pattern object for double patterns with enhanced timing info."""
        timestamp = market_data.get_timestamp_at_index(original_start_index + second_idx)
        
        # Calculate timing information
        pattern_duration = second_idx - first_idx
        current_period = len(rsi_array) - 1
        first_periods_ago = current_period - first_idx
        second_periods_ago = current_period - second_idx
        
        # Use instance formatting utilities
        first_periods_text = self.format_utils.format_periods_ago_with_context(first_periods_ago)
        second_periods_text = self.format_utils.format_periods_ago_with_context(second_periods_ago)
        
        if config.is_bottom_pattern:
            description = (f"W-bottom pattern detected: First bottom {first_periods_text} ({rsi_array[first_idx]:.1f}), "
                          f"second bottom {second_periods_text} ({rsi_array[second_idx]:.1f}), "
                          f"intermediate peak at {intermediate_val:.1f}. "
                          f"Pattern formed over {pattern_duration} periods. Potentially bullish.")
            return Pattern(
                config.pattern_type, description, timestamp=timestamp,
                first_bottom_idx=original_start_index + first_idx,
                second_bottom_idx=original_start_index + second_idx,
                value1=float(rsi_array[first_idx]), value2=float(rsi_array[second_idx]),
                intermediate_peak=intermediate_val,
                pattern_duration=pattern_duration,
                first_periods_ago=first_periods_ago,
                second_periods_ago=second_periods_ago
            )
        else:
            description = (f"M-top pattern detected: First peak {first_periods_text} ({rsi_array[first_idx]:.1f}), "
                          f"second peak {second_periods_text} ({rsi_array[second_idx]:.1f}), "
                          f"intermediate trough at {intermediate_val:.1f}. "
                          f"Pattern formed over {pattern_duration} periods. Potentially bearish.")
            return Pattern(
                config.pattern_type, description, timestamp=timestamp,
                first_peak_idx=original_start_index + first_idx,
                second_peak_idx=original_start_index + second_idx,
                value1=float(rsi_array[first_idx]), value2=float(rsi_array[second_idx]),
                intermediate_trough=intermediate_val,
                pattern_duration=pattern_duration,
                first_periods_ago=first_periods_ago,
                second_periods_ago=second_periods_ago
            )

    def should_replace_pattern(self, patterns: List[Pattern], new_pattern: Pattern,
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

