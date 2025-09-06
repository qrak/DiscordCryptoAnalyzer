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
        lookback = min(self.signal_lookback, len(recent_line))
        
        additional_data = {
            'macd_value': None,  # Will be set per pattern
            'signal_value': None  # Will be set per pattern
        }
        
        patterns = self._detect_line_crossovers(
            recent_line, recent_signal, market_data, original_start_index,
            lookback, "macd", ":.4f", additional_data
        )
        
        # Update pattern data with MACD-specific values and fix pattern types
        for pattern in patterns:
            periods_ago = pattern.periods_ago + 1  # Adjust for indexing
            if periods_ago < len(recent_line):
                pattern.macd_value = recent_line[-periods_ago]
                pattern.signal_value = recent_signal[-periods_ago]
                
                # Update pattern types to be MACD-specific
                if "bullish" in pattern.type:
                    pattern.type = "bullish_crossover"
                    pattern.description = f"Bullish MACD crossover {pattern.periods_ago} periods ago with MACD at {pattern.macd_value:.4f}."
                else:
                    pattern.type = "bearish_crossover"
                    pattern.description = f"Bearish MACD crossover {pattern.periods_ago} periods ago with MACD at {pattern.macd_value:.4f}."
        
        return patterns
    
    def _detect_zero_line_crosses(self, 
                                 recent_line: List[float],
                                 market_data: MarketData,
                                 original_start_index: int) -> List[Pattern]:
        """Detect MACD line crossing zero line"""
        lookback = min(self.signal_lookback, len(recent_line))
        
        patterns = self._detect_zero_line_crossovers(
            recent_line, market_data, original_start_index, lookback, "macd"
        )
        
        # Update pattern types to be MACD-specific
        for pattern in patterns:
            if "bullish" in pattern.type:
                pattern.type = "zero_line_bullish"
            else:
                pattern.type = "zero_line_bearish"
        
        return patterns