from typing import List

from src.indicators.base.pattern_detector import BasePatternDetector, MarketData, Pattern, CrossoverSettings


class CrossoverPatternDetector(BasePatternDetector):
    """Detector for various indicator crossover patterns"""
    
    def __init__(self, settings: CrossoverSettings, logger=None):
        super().__init__(settings, logger)
        self.lookback_periods = settings.lookback_periods
    
    def detect(self, data: MarketData) -> List[Pattern]:
        if not self._validate_input(data):
            return []
        
        history = data.technical_history
        patterns = []
        
        # Detect ADX DI+ and DI- crossovers
        if all(k in history for k in ["adx", "plus_di", "minus_di"]):
            di_patterns = self._detect_di_crossovers(
                data,
                history["adx"], 
                history["plus_di"], 
                history["minus_di"]
            )
            patterns.extend(di_patterns)
            
        # Detect supertrend direction changes
        if "supertrend_direction" in history:
            supertrend_patterns = self._detect_supertrend_changes(
                data,
                history["supertrend_direction"]
            )
            patterns.extend(supertrend_patterns)
            
        return patterns
    
    def _detect_di_crossovers(self,
                             market_data: MarketData,  # Added market_data parameter
                             adx: List[float],
                             plus_di: List[float],
                             minus_di: List[float]) -> List[Pattern]:
        """Detect ADX DI+ and DI- crossovers"""
        patterns = []
        
        min_length = min(len(adx), len(plus_di), len(minus_di))
        if min_length < 5:
            return []
            
        lookback = min(self.lookback_periods, min_length)
        
        # Calculate the starting index in the original data
        if market_data.has_data:
            original_start_index = max(0, len(market_data.ohlcv) - min_length)
        else:
            original_start_index = 0
            
        # Look for DI+ crossing above DI- (bullish)
        for i in range(1, lookback):
            if plus_di[-i-1] <= minus_di[-i-1] and plus_di[-i] > minus_di[-i]:
                # Get timestamp for this pattern using the right index
                timestamp = market_data.get_timestamp_at_index(original_start_index + min_length - i)
                
                pattern = Pattern(
                    "di_bullish_cross",
                    f"Bullish DMI crossover {i} periods ago (DI+ crossed above DI-) with ADX at {adx[-i]:.1f}.",
                    timestamp=timestamp,  # Added timestamp
                    periods_ago=i,
                    adx_value=adx[-i]
                )
                self._log_detection(pattern)
                patterns.append(pattern)
                break
                
        # Look for DI- crossing above DI+ (bearish)
        for i in range(1, lookback):
            if minus_di[-i-1] <= plus_di[-i-1] and minus_di[-i] > plus_di[-i]:
                # Get timestamp for this pattern
                timestamp = market_data.get_timestamp_at_index(original_start_index + min_length - i)
                
                pattern = Pattern(
                    "di_bearish_cross",
                    f"Bearish DMI crossover {i} periods ago (DI- crossed above DI+) with ADX at {adx[-i]:.1f}.",
                    timestamp=timestamp,  # Added timestamp
                    periods_ago=i,
                    adx_value=adx[-i]
                )
                self._log_detection(pattern)
                patterns.append(pattern)
                break
                
        return patterns
    
    def _detect_supertrend_changes(self, market_data: MarketData, direction: List[float]) -> List[Pattern]:
        """Detect supertrend direction changes"""
        patterns = []
        
        if len(direction) < 5:
            return []
            
        lookback = min(self.lookback_periods, len(direction))
        
        # Calculate the starting index in the original data
        if market_data.has_data:
            original_start_index = max(0, len(market_data.ohlcv) - len(direction))
        else:
            original_start_index = 0
            
        for i in range(1, lookback):
            if i < len(direction) and direction[-i] != direction[-i-1]:
                # Get timestamp for this pattern
                timestamp = market_data.get_timestamp_at_index(original_start_index + len(direction) - i)
                
                trend_type = "bullish" if direction[-i] > 0 else "bearish"
                pattern = Pattern(
                    f"supertrend_{trend_type}",
                    f"Supertrend turned {trend_type} {i} periods ago.",
                    timestamp=timestamp,  # Added timestamp
                    periods_ago=i
                )
                self._log_detection(pattern)
                patterns.append(pattern)
                break
                
        return patterns