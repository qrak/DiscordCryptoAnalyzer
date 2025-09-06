from typing import List
import numpy as np

from src.indicators.base.pattern_detector import BasePatternDetector, MarketData, Pattern, RSISettings
from .rsi_pattern_utils import (
    create_oversold_condition, create_overbought_condition,
    create_w_bottom_config, create_m_top_config,
    find_threshold_periods, create_threshold_pattern,
    find_rsi_extremes, validate_second_extreme,
    get_intermediate_extreme, validate_intermediate_value,
    create_double_pattern, should_replace_pattern,
    ThresholdCondition, DoublePatternConfig
)


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
    
    def _detect_threshold_condition(self, recent_rsi: np.ndarray, market_data: MarketData, 
                                   original_start_index: int, condition: ThresholdCondition) -> List[Pattern]:
        """Detect threshold-based conditions using configuration."""
        periods = find_threshold_periods(recent_rsi, condition)
        
        if periods:
            pattern = create_threshold_pattern(condition, periods, market_data, original_start_index)
            self._log_detection(pattern)
            return [pattern]
        
        return []
    
    def _detect_oversold(self, recent_rsi: np.ndarray, market_data: MarketData, original_start_index: int) -> List[Pattern]:
        """Detect oversold conditions using configuration."""
        condition = create_oversold_condition(self.oversold)
        return self._detect_threshold_condition(recent_rsi, market_data, original_start_index, condition)
    
    def _detect_overbought(self, recent_rsi: np.ndarray, market_data: MarketData, original_start_index: int) -> List[Pattern]:
        """Detect overbought conditions using configuration."""
        condition = create_overbought_condition(self.overbought)
        return self._detect_threshold_condition(recent_rsi, market_data, original_start_index, condition)
    
    def _detect_w_bottoms(self, recent_rsi: np.ndarray, market_data: MarketData, original_start_index: int) -> List[Pattern]:
        """Detect W-bottom patterns using configuration."""
        config = create_w_bottom_config(self.w_bottom_threshold, self.bottom_similarity, self.intermediate_peak_ratio)
        return self._detect_double_pattern(recent_rsi, market_data, original_start_index, config)
    
    def _detect_m_tops(self, recent_rsi: np.ndarray, market_data: MarketData, original_start_index: int) -> List[Pattern]:
        """Detect M-top patterns using configuration.""" 
        config = create_m_top_config(self.m_top_threshold, self.peak_similarity, self.intermediate_trough_ratio)
        return self._detect_double_pattern(recent_rsi, market_data, original_start_index, config)
    
    def _detect_double_pattern(self, recent_rsi: np.ndarray, market_data: MarketData, 
                              original_start_index: int, config: DoublePatternConfig) -> List[Pattern]:
        """Detect double patterns using configuration."""
        patterns = []
        min_separation = 5
        
        if len(recent_rsi) < 14:
            return patterns

        # Find potential first extremes
        potential_first_extremes = find_rsi_extremes(recent_rsi, config.threshold, config.is_bottom_pattern)
        
        # Look for matching second extremes
        for i in potential_first_extremes:
            pattern = self._find_matching_extreme(recent_rsi, i, config, market_data, original_start_index, min_separation)
            if pattern:
                # Check for overlaps and add pattern
                if should_replace_pattern(patterns, pattern, min_separation, config.is_bottom_pattern):
                    self._log_detection(pattern)
                    patterns.append(pattern)
                    break  # Don't need to check further j for this i
        
        return patterns
    
    def _find_matching_extreme(self, rsi_array: np.ndarray, first_idx: int, config: DoublePatternConfig,
                              market_data: MarketData, original_start_index: int, min_separation: int) -> Pattern:
        """Find a matching second extreme using configuration."""
        search_start = first_idx + min_separation
        search_end = min(first_idx + 15, len(rsi_array) - 3)

        for j in range(search_start, search_end):
            if validate_second_extreme(rsi_array, j, config.threshold, first_idx, 
                                     config.similarity_threshold, config.is_bottom_pattern):
                # Validate intermediate value
                intermediate_segment = rsi_array[first_idx+1:j]
                if len(intermediate_segment) > 0:
                    intermediate_val, _ = get_intermediate_extreme(
                        intermediate_segment, first_idx, config.is_bottom_pattern
                    )
                    
                    if validate_intermediate_value(
                        intermediate_val, rsi_array[first_idx], rsi_array[j], 
                        config.intermediate_ratio, config.is_bottom_pattern
                    ):
                        return create_double_pattern(
                            config, rsi_array, first_idx, j, intermediate_val,
                            market_data, original_start_index
                        )
        return None

