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
    
    def _detect_oversold(self, recent_rsi: np.ndarray, market_data: MarketData, original_start_index: int) -> List[Pattern]:
        """Detect oversold conditions (RSI < oversold threshold)"""
        patterns = []
        oversold_periods = []
        current_oversold = False
        start_idx = None
        
        for i, value in enumerate(recent_rsi):
            if value < self.oversold and not current_oversold:
                current_oversold = True
                start_idx = i
            elif value >= self.oversold and current_oversold:
                oversold_periods.append({
                    "start": start_idx,
                    "end": i-1,
                    "duration": i - start_idx,
                    "min_value": min(recent_rsi[start_idx:i])
                })
                current_oversold = False
        
        # If still in oversold period at the end
        if current_oversold:
            oversold_periods.append({
                "start": start_idx,
                "end": len(recent_rsi) - 1,
                "duration": len(recent_rsi) - start_idx,
                "min_value": min(recent_rsi[start_idx:])
            })
        
        if oversold_periods:
            # Use timestamp of the end of the last detected period
            last_period = oversold_periods[-1]
            timestamp = market_data.get_timestamp_at_index(original_start_index + last_period['end'])
            
            pattern = Pattern(
                "oversold",
                f"RSI entered oversold territory (<{self.oversold}) {len(oversold_periods)} times in the recent period.",
                timestamp=timestamp, # Pass timestamp
                periods=oversold_periods
            )
            self._log_detection(pattern)
            patterns.append(pattern)
        
        return patterns
    
    def _detect_overbought(self, recent_rsi: np.ndarray, market_data: MarketData, original_start_index: int) -> List[Pattern]:
        """Detect overbought conditions (RSI > overbought threshold)"""
        patterns = []
        overbought_periods = []
        current_overbought = False
        start_idx = None
        
        for i, value in enumerate(recent_rsi):
            if value > self.overbought and not current_overbought:
                current_overbought = True
                start_idx = i
            elif value <= self.overbought and current_overbought:
                overbought_periods.append({
                    "start": start_idx,
                    "end": i-1,
                    "duration": i - start_idx,
                    "max_value": max(recent_rsi[start_idx:i])
                })
                current_overbought = False
        
        # If still in overbought period at the end
        if current_overbought:
            overbought_periods.append({
                "start": start_idx,
                "end": len(recent_rsi) - 1,
                "duration": len(recent_rsi) - start_idx,
                "max_value": max(recent_rsi[start_idx:])
            })
        
        if overbought_periods:
            # Use timestamp of the end of the last detected period
            last_period = overbought_periods[-1]
            timestamp = market_data.get_timestamp_at_index(original_start_index + last_period['end'])

            pattern = Pattern(
                "overbought",
                f"RSI entered overbought territory (>{self.overbought}) {len(overbought_periods)} times in the recent period.",
                timestamp=timestamp, # Pass timestamp
                periods=overbought_periods
            )
            self._log_detection(pattern)
            patterns.append(pattern)
        
        return patterns
    
    def _detect_w_bottoms(self, recent_rsi: np.ndarray, market_data: MarketData, original_start_index: int) -> List[Pattern]:
        """Detect W-bottom patterns in RSI with intermediate peak check"""
        patterns = []
        min_separation = 5  # Minimum periods between bottoms
        
        if len(recent_rsi) < 14: # Need enough data for pattern
            return patterns

        # Use numpy array directly
        rsi_array = recent_rsi 

        # Find potential first bottoms (local minima below threshold)
        potential_first_bottoms = []
        for i in range(3, len(rsi_array) - 3):
             if (rsi_array[i] < rsi_array[i-2] and 
                 rsi_array[i] < rsi_array[i+2] and 
                 rsi_array[i] < self.w_bottom_threshold):
                 potential_first_bottoms.append(i)

        # Look for second bottoms and validate intermediate peak
        for i in potential_first_bottoms:
            # Search range for the second bottom
            search_start = i + min_separation
            search_end = min(i + 15, len(rsi_array) - 3) # Limit search window

            for j in range(search_start, search_end):
                 # Check for second bottom conditions
                 if (rsi_array[j] < rsi_array[j-2] and 
                     rsi_array[j] < rsi_array[j+2] and 
                     rsi_array[j] < self.w_bottom_threshold and
                     abs(rsi_array[i] - rsi_array[j]) < self.bottom_similarity):

                    # Find the peak between the two bottoms
                    intermediate_segment = rsi_array[i+1:j]
                    if len(intermediate_segment) > 0:
                        intermediate_peak_idx = np.argmax(intermediate_segment) + i + 1
                        intermediate_peak_val = rsi_array[intermediate_peak_idx]
                        avg_bottom_val = (rsi_array[i] + rsi_array[j]) / 2

                        # Check if intermediate peak is significantly higher
                        if intermediate_peak_val > avg_bottom_val * self.intermediate_peak_ratio:
                            timestamp = market_data.get_timestamp_at_index(original_start_index + j) # Timestamp of second bottom

                            pattern = Pattern(
                                "w_bottom",
                                f"W-bottom pattern detected in RSI with bottoms at {rsi_array[i]:.1f} and {rsi_array[j]:.1f}, intermediate peak at {intermediate_peak_val:.1f}. Potentially bullish.",
                                timestamp=timestamp, # Pass timestamp
                                first_bottom_idx=original_start_index + i, # Store original index
                                second_bottom_idx=original_start_index + j, # Store original index
                                value1=rsi_array[i],
                                value2=rsi_array[j],
                                intermediate_peak=intermediate_peak_val
                            )
                            # Simple check to avoid adding overlapping/less significant patterns
                            is_new = True
                            if patterns:
                                last_pattern = patterns[-1]
                                # Avoid adding if it overlaps significantly with the last one
                                if j < last_pattern.second_bottom_idx + min_separation // 2:
                                    is_new = False
                                    # Replace if this one is 'stronger' (lower bottoms)
                                    if avg_bottom_val < (last_pattern.value1 + last_pattern.value2) / 2:
                                        patterns.pop()
                                        is_new = True
                            if is_new:
                                self._log_detection(pattern)
                                patterns.append(pattern)
                            # Don't need to check further j for this i once a valid pattern is found
                            break 
        return patterns

    def _detect_m_tops(self, recent_rsi: np.ndarray, market_data: MarketData, original_start_index: int) -> List[Pattern]:
        """Detect M-top patterns in RSI with intermediate trough check"""
        patterns = []
        min_separation = 5  # Minimum periods between peaks
        
        if len(recent_rsi) < 14:
            return patterns

        # Use numpy array directly
        rsi_array = recent_rsi

        # Find potential first peaks (local maxima above threshold)
        potential_first_peaks = []
        for i in range(3, len(rsi_array) - 3):
             if (rsi_array[i] > rsi_array[i-2] and 
                 rsi_array[i] > rsi_array[i+2] and 
                 rsi_array[i] > self.m_top_threshold): # Use m_top_threshold
                 potential_first_peaks.append(i)

        # Look for second peaks and validate intermediate trough
        for i in potential_first_peaks:
            search_start = i + min_separation
            search_end = min(i + 15, len(rsi_array) - 3)

            for j in range(search_start, search_end):
                 # Check for second peak conditions
                 if (rsi_array[j] > rsi_array[j-2] and 
                     rsi_array[j] > rsi_array[j+2] and 
                     rsi_array[j] > self.m_top_threshold and # Use m_top_threshold
                     abs(rsi_array[i] - rsi_array[j]) < self.peak_similarity): # Use peak_similarity

                    # Find the trough between the two peaks
                    intermediate_segment = rsi_array[i+1:j]
                    if len(intermediate_segment) > 0:
                        intermediate_trough_idx = np.argmin(intermediate_segment) + i + 1
                        intermediate_trough_val = rsi_array[intermediate_trough_idx]
                        avg_peak_val = (rsi_array[i] + rsi_array[j]) / 2

                        # Check if intermediate trough is significantly lower
                        if intermediate_trough_val < avg_peak_val * self.intermediate_trough_ratio: 
                            timestamp = market_data.get_timestamp_at_index(original_start_index + j) # Timestamp of second peak

                            pattern = Pattern(
                                "m_top", 
                                f"M-top pattern detected in RSI with peaks at {rsi_array[i]:.1f} and {rsi_array[j]:.1f}, intermediate trough at {intermediate_trough_val:.1f}. Potentially bearish.",
                                timestamp=timestamp, # Pass timestamp
                                first_peak_idx=original_start_index + i, # Store original index
                                second_peak_idx=original_start_index + j, # Store original index
                                value1=rsi_array[i],
                                value2=rsi_array[j],
                                intermediate_trough=intermediate_trough_val 
                            )
                            # Simple check to avoid adding overlapping/less significant patterns
                            is_new = True
                            if patterns:
                                last_pattern = patterns[-1]
                                if j < last_pattern.second_peak_idx + min_separation // 2:
                                    is_new = False
                                    # Replace if this one is 'stronger' (higher peaks)
                                    if avg_peak_val > (last_pattern.value1 + last_pattern.value2) / 2:
                                        patterns.pop()
                                        is_new = True
                            if is_new:
                                self._log_detection(pattern)
                                patterns.append(pattern)
                            break 
        return patterns