from typing import List

from src.indicators.base.pattern_detector import BasePatternDetector, MarketData, Pattern, VolatilitySettings


class VolatilityPatternDetector(BasePatternDetector):
    """Detector for volatility patterns using ATR"""
    
    def __init__(self, settings: VolatilitySettings, logger=None):
        super().__init__(settings, logger)
        self.significant_change_threshold = settings.significant_change_threshold
        self.spike_threshold = settings.spike_threshold
        self.high_volatility_ratio = settings.high_volatility_ratio
        self.low_volatility_ratio = settings.low_volatility_ratio
    
    def detect(self, data: MarketData) -> List[Pattern]:
        if not self._validate_input(data):
            return []
        
        atr_values = data.get_indicator_history("atr")
        
        if len(atr_values) < 14:
            return []
        
        patterns = []
        
        # Get recent values for analysis
        recent_atr = atr_values[-30:] if len(atr_values) > 30 else atr_values
        
        # Calculate original data starting index
        original_start_index = max(0, len(data.ohlcv) - len(recent_atr))
        
        # Get current timestamp (most recent)
        current_timestamp = data.get_timestamp_at_index(len(data.ohlcv) - 1)
        
        # Detect volatility trend patterns
        trend_patterns = self._detect_volatility_trend(recent_atr, data, original_start_index)
        patterns.extend(trend_patterns)
        
        # Detect volatility spikes
        spike_patterns = self._detect_volatility_spikes(recent_atr, data, original_start_index)
        patterns.extend(spike_patterns)
        
        # Detect abnormal volatility levels compared to longer history
        if len(atr_values) >= 50:
            level_patterns = self._detect_volatility_levels(atr_values, data)
            patterns.extend(level_patterns)
        
        return patterns
    
    def _detect_volatility_trend(self, 
                                recent_atr: List[float],
                                market_data: MarketData,
                                original_start_index: int) -> List[Pattern]:
        """Detect overall trend in volatility"""
        patterns = []
        
        # Get start/end values for percentage change calculation
        start_atr = recent_atr[0]
        end_atr = recent_atr[-1]
        
        # Calculate percentage change in ATR over the period
        pct_change = 0
        if start_atr > 0:  # Avoid division by zero
            pct_change = ((end_atr / start_atr) - 1) * 100
            
        # Only report significant changes (configurable threshold)
        if abs(pct_change) >= self.significant_change_threshold:
            # Get timestamp for when this pattern occurred
            timestamp = market_data.get_timestamp_at_index(len(market_data.ohlcv) - 1)
            
            # Determine volatility state
            volatility_state = "increasing" if pct_change > 0 else "decreasing"
            
            # Calculate the analyzed period in days based on recent_atr length
            analyzed_period = len(recent_atr)
            timeframe_str = f"over the last {analyzed_period} periods"
            
            pattern = Pattern(
                "volatility_trend",
                f"Volatility has been {volatility_state} by {abs(pct_change):.1f}% {timeframe_str}.",
                timestamp=timestamp,  # Add timestamp
                start_value=start_atr,
                end_value=end_atr,
                percent_change=pct_change,
                trend=volatility_state,
                analyzed_periods=analyzed_period
            )
            self._log_detection(pattern)
            patterns.append(pattern)
        
        # Check for current volatility vs average
        avg_atr = sum(recent_atr) / len(recent_atr) if len(recent_atr) > 0 else 0
        if end_atr > avg_atr * 1.2:
            timestamp = market_data.get_timestamp_at_index(len(market_data.ohlcv) - 1)
            pattern = Pattern(
                "above_average_volatility",
                f"Current volatility is {(end_atr / avg_atr if avg_atr else 0):.1f}x higher than the period average.",
                timestamp=timestamp,  # Add timestamp
                current=end_atr,
                period_average=avg_atr,
                ratio=end_atr / avg_atr if avg_atr else 0
            )
            self._log_detection(pattern)
            patterns.append(pattern)
            
        return patterns
    
    def _detect_volatility_spikes(self, 
                                 recent_atr: List[float],
                                 market_data: MarketData,
                                 original_start_index: int) -> List[Pattern]:
        """Detect sudden spikes in volatility"""
        patterns = []
        
        for i in range(2, len(recent_atr)):
            # Detect volatility spike (ATR increases by spike threshold % or more in short period)
            spike_ratio = 1 + (self.spike_threshold / 100)
            if recent_atr[i] > recent_atr[i-2] * spike_ratio:
                # Get timestamp for this pattern
                timestamp = market_data.get_timestamp_at_index(original_start_index + i)
                
                pattern = Pattern(
                    "volatility_spike",
                    f"Volatility spike detected {len(recent_atr)-i} periods ago, ATR increased by {((recent_atr[i] / recent_atr[i-2]) - 1) * 100:.1f}%.",
                    timestamp=timestamp,  # Add timestamp
                    period=i,
                    before=recent_atr[i-2],
                    after=recent_atr[i],
                    percent_change=((recent_atr[i] / recent_atr[i-2]) - 1) * 100
                )
                self._log_detection(pattern)
                patterns.append(pattern)
        
        return patterns
    
    def _detect_volatility_levels(self, 
                                 atr_values: List[float],
                                 market_data: MarketData) -> List[Pattern]:
        """Compare current volatility to longer-term history"""
        patterns = []
        
        # Get the most recent value
        end_atr = atr_values[-1]
        
        # Calculate average over longer period (50)
        longer_atr = atr_values[-50:]
        avg_50_atr = sum(longer_atr) / len(longer_atr)
        
        # Get current timestamp
        timestamp = market_data.get_timestamp_at_index(len(market_data.ohlcv) - 1)
        
        if end_atr > avg_50_atr * self.high_volatility_ratio:
            pattern = Pattern(
                "high_volatility",
                f"Current volatility is {(end_atr / avg_50_atr):.1f}x higher than the 50-period average.",
                timestamp=timestamp,  # Add timestamp
                current=end_atr,
                average=avg_50_atr,
                ratio=end_atr / avg_50_atr
            )
            self._log_detection(pattern)
            patterns.append(pattern)
        elif end_atr < avg_50_atr * self.low_volatility_ratio:
            pattern = Pattern(
                "low_volatility",
                f"Current volatility is unusually low, {(end_atr / avg_50_atr):.1f}x below the 50-period average.",
                timestamp=timestamp,  # Add timestamp
                current=end_atr,
                average=avg_50_atr,
                ratio=end_atr / avg_50_atr
            )
            self._log_detection(pattern)
            patterns.append(pattern)
        
        return patterns