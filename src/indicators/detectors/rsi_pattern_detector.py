from typing import List
import numpy as np 
from datetime import datetime # Import datetime

from src.indicators.base.pattern_detector import BasePatternDetector, MarketData, Pattern, RSISettings


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
    
    def _detect_threshold_condition(self, 
                                   recent_rsi: np.ndarray, 
                                   market_data: MarketData, 
                                   original_start_index: int,
                                   threshold: float, 
                                   condition_type: str, 
                                   comparison_func) -> List[Pattern]:
        """Generic method to detect threshold-based conditions (oversold/overbought)"""
        patterns = []
        periods = []
        current_condition = False
        start_idx = None
        
        for i, value in enumerate(recent_rsi):
            if comparison_func(value, threshold) and not current_condition:
                current_condition = True
                start_idx = i
            elif not comparison_func(value, threshold) and current_condition:
                extreme_value = (max if condition_type == "overbought" else min)(recent_rsi[start_idx:i])
                periods.append({
                    "start": start_idx,
                    "end": i-1,
                    "duration": i - start_idx,
                    f"{'max' if condition_type == 'overbought' else 'min'}_value": extreme_value
                })
                current_condition = False
        
        # If still in condition at the end
        if current_condition:
            extreme_value = (max if condition_type == "overbought" else min)(recent_rsi[start_idx:])
            periods.append({
                "start": start_idx,
                "end": len(recent_rsi) - 1,
                "duration": len(recent_rsi) - start_idx,
                f"{'max' if condition_type == 'overbought' else 'min'}_value": extreme_value
            })
        
        if periods:
            # Use timestamp of the end of the last detected period
            last_period = periods[-1]
            timestamp = market_data.get_timestamp_at_index(original_start_index + last_period['end'])
            
            comparison_symbol = ">" if condition_type == "overbought" else "<"
            pattern = Pattern(
                condition_type,
                f"RSI entered {condition_type} territory ({comparison_symbol}{threshold}) {len(periods)} times in the recent period.",
                timestamp=timestamp,
                periods=periods
            )
            self._log_detection(pattern)
            patterns.append(pattern)
        
        return patterns
    
    def _detect_oversold(self, recent_rsi: np.ndarray, market_data: MarketData, original_start_index: int) -> List[Pattern]:
        """Detect oversold conditions (RSI < oversold threshold)"""
        return self._detect_threshold_condition(
            recent_rsi, market_data, original_start_index, 
            self.oversold, "oversold", lambda val, thresh: val < thresh
        )
    
    def _detect_overbought(self, recent_rsi: np.ndarray, market_data: MarketData, original_start_index: int) -> List[Pattern]:
        """Detect overbought conditions (RSI > overbought threshold)"""
        return self._detect_threshold_condition(
            recent_rsi, market_data, original_start_index, 
            self.overbought, "overbought", lambda val, thresh: val > thresh
        )
    
    def _detect_w_bottoms(self, recent_rsi: np.ndarray, market_data: MarketData, original_start_index: int) -> List[Pattern]:
        """Detect W-bottom patterns in RSI with intermediate peak check"""
        return self._detect_double_pattern(
            recent_rsi, market_data, original_start_index,
            pattern_type="w_bottom",
            threshold=self.w_bottom_threshold,
            similarity_threshold=self.bottom_similarity,
            intermediate_ratio=self.intermediate_peak_ratio,
            is_bottom_pattern=True
        )
    
    def _detect_m_tops(self, recent_rsi: np.ndarray, market_data: MarketData, original_start_index: int) -> List[Pattern]:
        """Detect M-top patterns in RSI with intermediate trough check"""
        return self._detect_double_pattern(
            recent_rsi, market_data, original_start_index,
            pattern_type="m_top",
            threshold=self.m_top_threshold,
            similarity_threshold=self.peak_similarity,
            intermediate_ratio=self.intermediate_trough_ratio,
            is_bottom_pattern=False
        )
    
    def _detect_double_pattern(self, recent_rsi: np.ndarray, market_data: MarketData, original_start_index: int,
                               pattern_type: str, threshold: float, similarity_threshold: float, 
                               intermediate_ratio: float, is_bottom_pattern: bool) -> List[Pattern]:
        """Generic detection for double patterns (W-bottoms and M-tops)"""
        patterns = []
        min_separation = 5
        
        if len(recent_rsi) < 14:
            return patterns

        rsi_array = recent_rsi
        
        # Find potential first extremes (peaks or bottoms)
        potential_first_extremes = self._find_extremes(rsi_array, threshold, is_bottom_pattern)
        
        # Look for second extremes and validate intermediate values
        for i in potential_first_extremes:
            pattern = self._find_matching_extreme(
                rsi_array, i, threshold, similarity_threshold, 
                intermediate_ratio, is_bottom_pattern, pattern_type,
                market_data, original_start_index, min_separation
            )
            if pattern:
                # Check for overlaps and add pattern
                if self._should_add_pattern(patterns, pattern, min_separation, is_bottom_pattern):
                    self._log_detection(pattern)
                    patterns.append(pattern)
                    break  # Don't need to check further j for this i
        
        return patterns
    
    def _find_extremes(self, rsi_array: np.ndarray, threshold: float, is_bottom_pattern: bool) -> List[int]:
        """Find potential extreme points (local minima for bottoms, local maxima for tops)"""
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
    
    def _find_matching_extreme(self, rsi_array: np.ndarray, first_idx: int, threshold: float,
                               similarity_threshold: float, intermediate_ratio: float,
                               is_bottom_pattern: bool, pattern_type: str, market_data: MarketData,
                               original_start_index: int, min_separation: int) -> Pattern:
        """Find a matching second extreme that forms a valid double pattern"""
        search_start = first_idx + min_separation
        search_end = min(first_idx + 15, len(rsi_array) - 3)

        for j in range(search_start, search_end):
            if self._is_valid_second_extreme(rsi_array, j, threshold, first_idx, similarity_threshold, is_bottom_pattern):
                # Validate intermediate value
                intermediate_segment = rsi_array[first_idx+1:j]
                if len(intermediate_segment) > 0:
                    intermediate_val, intermediate_idx = self._get_intermediate_extreme(
                        intermediate_segment, first_idx, is_bottom_pattern
                    )
                    
                    if self._is_valid_intermediate(
                        intermediate_val, rsi_array[first_idx], rsi_array[j], 
                        intermediate_ratio, is_bottom_pattern
                    ):
                        return self._create_double_pattern(
                            pattern_type, rsi_array, first_idx, j, intermediate_val,
                            market_data, original_start_index, is_bottom_pattern
                        )
        return None
    
    def _is_valid_second_extreme(self, rsi_array: np.ndarray, j: int, threshold: float,
                                 first_idx: int, similarity_threshold: float, is_bottom_pattern: bool) -> bool:
        """Check if the second point forms a valid extreme"""
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
    
    def _get_intermediate_extreme(self, intermediate_segment: np.ndarray, first_idx: int, is_bottom_pattern: bool):
        """Get the intermediate extreme value and its index"""
        if is_bottom_pattern:
            # For W-bottoms, look for intermediate peak
            intermediate_extreme_idx = np.argmax(intermediate_segment) + first_idx + 1
        else:
            # For M-tops, look for intermediate trough
            intermediate_extreme_idx = np.argmin(intermediate_segment) + first_idx + 1
        
        return intermediate_segment[np.argmax(intermediate_segment) if is_bottom_pattern else np.argmin(intermediate_segment)], intermediate_extreme_idx
    
    def _is_valid_intermediate(self, intermediate_val: float, first_val: float, second_val: float,
                               intermediate_ratio: float, is_bottom_pattern: bool) -> bool:
        """Check if the intermediate value meets the ratio requirement"""
        avg_extreme_val = (first_val + second_val) / 2
        
        if is_bottom_pattern:
            # For W-bottoms, intermediate peak should be significantly higher
            return intermediate_val > avg_extreme_val * intermediate_ratio
        else:
            # For M-tops, intermediate trough should be significantly lower
            return intermediate_val < avg_extreme_val * intermediate_ratio
    
    def _create_double_pattern(self, pattern_type: str, rsi_array: np.ndarray, first_idx: int, 
                               second_idx: int, intermediate_val: float, market_data: MarketData,
                               original_start_index: int, is_bottom_pattern: bool) -> Pattern:
        """Create a Pattern object for the double pattern"""
        timestamp = market_data.get_timestamp_at_index(original_start_index + second_idx)
        
        if is_bottom_pattern:
            description = (f"W-bottom pattern detected in RSI with bottoms at {rsi_array[first_idx]:.1f} "
                          f"and {rsi_array[second_idx]:.1f}, intermediate peak at {intermediate_val:.1f}. "
                          f"Potentially bullish.")
            return Pattern(
                pattern_type, description, timestamp=timestamp,
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
                pattern_type, description, timestamp=timestamp,
                first_peak_idx=original_start_index + first_idx,
                second_peak_idx=original_start_index + second_idx,
                value1=rsi_array[first_idx], value2=rsi_array[second_idx],
                intermediate_trough=intermediate_val
            )
    
    def _should_add_pattern(self, patterns: List[Pattern], new_pattern: Pattern, 
                            min_separation: int, is_bottom_pattern: bool) -> bool:
        """Check if the new pattern should be added or if it replaces an existing one"""
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