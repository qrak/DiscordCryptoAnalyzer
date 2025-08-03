from typing import List

from src.indicators.base.pattern_detector import BasePatternDetector, MarketData, Pattern, MACDSettings


class MACDPatternDetector(BasePatternDetector):
    """Detector for MACD patterns like crossovers and zero-line crosses"""
    
    def __init__(self, settings: MACDSettings, logger=None):
        super().__init__(settings, logger)
        self.signal_lookback = settings.signal_lookback
    
    def detect(self, data: MarketData) -> List[Pattern]:
        if not self._validate_input(data):
            return []
        
        macd_line = data.get_indicator_history("macd_line")
        macd_signal = data.get_indicator_history("macd_signal")
        macd_hist = data.get_indicator_history("macd_hist")
        
        if len(macd_line) < 14 or len(macd_signal) < 14 or len(macd_hist) < 14:
            return []
        
        patterns = []
        
        # Get recent values for analysis
        recent_line = macd_line[-30:] if len(macd_line) > 30 else macd_line
        recent_signal = macd_signal[-30:] if len(macd_signal) > 30 else macd_signal
        
        # Calculate original data starting index
        original_start_index = max(0, len(data.ohlcv) - len(recent_line))
        
        # Detect crossovers
        crossover_patterns = self._detect_crossovers(recent_line, recent_signal, data, original_start_index)
        patterns.extend(crossover_patterns)
        
        # Detect zero line crossovers
        zero_line_patterns = self._detect_zero_line_crosses(recent_line, data, original_start_index)
        patterns.extend(zero_line_patterns)
        
        return patterns
    
    def _detect_crossovers(self, 
                           recent_line: List[float], 
                           recent_signal: List[float],
                           market_data: MarketData,
                           original_start_index: int) -> List[Pattern]:
        """Detect MACD line crossing signal line"""
        patterns = []
        
        # Look for crossovers within the lookback period
        lookback = min(self.signal_lookback, len(recent_line))
        
        for i in range(2, lookback):
            # Bullish crossover (MACD line crosses above signal line)
            if recent_line[-i] <= recent_signal[-i] and recent_line[-i+1] > recent_signal[-i+1]:
                # Get timestamp for this pattern
                timestamp = market_data.get_timestamp_at_index(original_start_index + len(recent_line) - i + 1)
                
                pattern = Pattern(
                    "bullish_crossover",
                    f"Bullish MACD crossover {i-1} periods ago with MACD at {recent_line[-i+1]:.4f}.",
                    timestamp=timestamp,  # Add timestamp
                    periods_ago=i-1,
                    macd_value=recent_line[-i+1],
                    signal_value=recent_signal[-i+1]
                )
                self._log_detection(pattern)
                patterns.append(pattern)
                
            # Bearish crossover (MACD line crosses below signal line)
            if recent_line[-i] >= recent_signal[-i] and recent_line[-i+1] < recent_signal[-i+1]:
                # Get timestamp for this pattern
                timestamp = market_data.get_timestamp_at_index(original_start_index + len(recent_line) - i + 1)
                
                pattern = Pattern(
                    "bearish_crossover",
                    f"Bearish MACD crossover {i-1} periods ago with MACD at {recent_line[-i+1]:.4f}.",
                    timestamp=timestamp,  # Add timestamp
                    periods_ago=i-1,
                    macd_value=recent_line[-i+1],
                    signal_value=recent_signal[-i+1]
                )
                self._log_detection(pattern)
                patterns.append(pattern)
        
        return patterns
    
    def _detect_zero_line_crosses(self, 
                                 recent_line: List[float],
                                 market_data: MarketData,
                                 original_start_index: int) -> List[Pattern]:
        """Detect MACD line crossing zero line"""
        patterns = []
        
        # Look for zero line crossovers within the lookback period
        lookback = min(self.signal_lookback, len(recent_line))
        
        for i in range(2, lookback):
            # Bullish zero line crossover
            if recent_line[-i] <= 0 and recent_line[-i+1] > 0:
                # Get timestamp for this pattern
                timestamp = market_data.get_timestamp_at_index(original_start_index + len(recent_line) - i + 1)
                
                pattern = Pattern(
                    "zero_line_bullish",
                    f"MACD crossed above zero line {i-1} periods ago.",
                    timestamp=timestamp,  # Add timestamp
                    periods_ago=i-1,
                    value=recent_line[-i+1]
                )
                self._log_detection(pattern)
                patterns.append(pattern)
                
            # Bearish zero line crossover
            if recent_line[-i] >= 0 and recent_line[-i+1] < 0:
                # Get timestamp for this pattern
                timestamp = market_data.get_timestamp_at_index(original_start_index + len(recent_line) - i + 1)
                
                pattern = Pattern(
                    "zero_line_bearish",
                    f"MACD crossed below zero line {i-1} periods ago.",
                    timestamp=timestamp,  # Add timestamp
                    periods_ago=i-1,
                    value=recent_line[-i+1]
                )
                self._log_detection(pattern)
                patterns.append(pattern)
        
        return patterns