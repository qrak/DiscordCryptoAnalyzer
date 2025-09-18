from typing import List

from src.indicators.base.pattern_detector import BasePatternDetector, MarketData, Pattern, DivergenceSettings


class DivergencePatternDetector(BasePatternDetector):
    """Detector for divergence patterns between price and indicators"""
    
    def __init__(self, settings: DivergenceSettings, logger=None):
        super().__init__(settings, logger)
        self.price_lookback = settings.price_lookback
        self.short_term_lookback = settings.short_term_lookback
    
    def detect(self, data: MarketData) -> List[Pattern]:
        if not self._validate_input(data):
            return []
        
        prices = data.prices
        rsi_values = data.get_indicator_history("rsi")
        macd_values = data.get_indicator_history("macd_line")
        stoch_values = data.get_indicator_history("stoch_k")
        
        # Ensure we have enough data
        min_length = min(len(prices), len(rsi_values), len(macd_values), len(stoch_values))
        if min_length < 14:
            return []
        
        patterns = []
        
        # Use recent data for analysis (last 30 periods)
        period_length = min(30, min_length)
        recent_prices = prices[-period_length:]
        recent_rsi = rsi_values[-period_length:]
        recent_macd = macd_values[-period_length:]
        recent_stoch = stoch_values[-period_length:]
        
        # Calculate the starting index in original data
        original_start_index = len(data.ohlcv) - period_length
        
        # Detect RSI divergences
        rsi_patterns = self._detect_rsi_divergences(recent_prices, recent_rsi.tolist(), data, original_start_index)
        patterns.extend(rsi_patterns)
        
        # Detect Stochastic divergences
        stoch_patterns = self._detect_stochastic_divergences(recent_prices, recent_stoch.tolist(), data, original_start_index)
        patterns.extend(stoch_patterns)
        
        # Detect MACD divergences
        macd_patterns = self._detect_macd_divergences(recent_prices, recent_macd.tolist(), data, original_start_index)
        patterns.extend(macd_patterns)
        
        return patterns
    
    def _detect_rsi_divergences(self, 
                               recent_prices: List[float], 
                               recent_rsi: List[float],
                               market_data: MarketData,
                               original_start_index: int) -> List[Pattern]:
        """Detect divergences between price and RSI"""
        patterns = []
        
        # Define common price conditions using price_lookback parameter
        price_making_lower_low = recent_prices[-1] < min(recent_prices[-self.price_lookback:-1])
        price_making_higher_high = recent_prices[-1] > max(recent_prices[-self.price_lookback:-1])
        
        # Define indicator conditions
        rsi_making_lower_low = recent_rsi[-1] < min(recent_rsi[-self.price_lookback:-1])
        rsi_making_higher_high = recent_rsi[-1] > max(recent_rsi[-self.price_lookback:-1])
        
        # Get current timestamp
        timestamp = market_data.get_timestamp_at_index(len(market_data.ohlcv) - 1)
        
        # Find the indices where the extreme values occur for better timing
        price_low_idx = len(recent_prices) - 1 - recent_prices[::-1].index(min(recent_prices[-self.price_lookback:]))
        rsi_low_idx = len(recent_rsi) - 1 - recent_rsi[::-1].index(min(recent_rsi[-self.price_lookback:]))
        price_high_idx = len(recent_prices) - 1 - recent_prices[::-1].index(max(recent_prices[-self.price_lookback:]))
        rsi_high_idx = len(recent_rsi) - 1 - recent_rsi[::-1].index(max(recent_rsi[-self.price_lookback:]))
        
        current_period = len(recent_prices) - 1
        
        # RSI divergences with enhanced timing
        if price_making_lower_low and not rsi_making_lower_low:
            price_periods_ago = current_period - price_low_idx
            rsi_periods_ago = current_period - rsi_low_idx
            
            description = (f"Bullish RSI divergence: Price low {price_periods_ago} periods ago "
                          f"({recent_prices[price_low_idx]:.2f}), RSI higher low {rsi_periods_ago} periods ago "
                          f"({recent_rsi[rsi_low_idx]:.1f}). Suggests potential upward reversal.")
            
            pattern = Pattern(
                "bullish_divergence",
                description,
                timestamp=timestamp,
                indicator="RSI",
                price_periods_ago=price_periods_ago,
                indicator_periods_ago=rsi_periods_ago,
                price_value=recent_prices[price_low_idx],
                indicator_value=recent_rsi[rsi_low_idx]
            )
            self._log_detection(pattern)
            patterns.append(pattern)

        if price_making_higher_high and not rsi_making_higher_high:
            price_periods_ago = current_period - price_high_idx
            rsi_periods_ago = current_period - rsi_high_idx
            
            description = (f"Bearish RSI divergence: Price high {price_periods_ago} periods ago "
                          f"({recent_prices[price_high_idx]:.2f}), RSI lower high {rsi_periods_ago} periods ago "
                          f"({recent_rsi[rsi_high_idx]:.1f}). Suggests potential downward reversal.")
            
            pattern = Pattern(
                "bearish_divergence",
                description,
                timestamp=timestamp,
                indicator="RSI",
                price_periods_ago=price_periods_ago,
                indicator_periods_ago=rsi_periods_ago,
                price_value=recent_prices[price_high_idx],
                indicator_value=recent_rsi[rsi_high_idx]
            )
            self._log_detection(pattern)
            patterns.append(pattern)
        
        return patterns
    
    def _detect_short_term_divergences(self,
                                      recent_prices: List[float],
                                      recent_indicator: List[float],
                                      market_data: MarketData,
                                      indicator_name: str,
                                      bullish_message: str,
                                      bearish_message: str) -> List[Pattern]:
        """Generic method to detect short-term divergences between price and an indicator"""
        patterns = []
        
        # Recent price movement (for short-term divergences)
        price_short_term_lower = recent_prices[-1] < recent_prices[-self.short_term_lookback]
        price_short_term_higher = recent_prices[-1] > recent_prices[-self.short_term_lookback]
        
        # Recent indicator movements (for short-term divergences)
        indicator_short_term_lower = recent_indicator[-1] < recent_indicator[-self.short_term_lookback]
        indicator_short_term_higher = recent_indicator[-1] > recent_indicator[-self.short_term_lookback]
        
        # Get current timestamp
        timestamp = market_data.get_timestamp_at_index(len(market_data.ohlcv) - 1)
        
        # Enhanced timing information
        price_change_periods = self.short_term_lookback - 1
        indicator_change_periods = self.short_term_lookback - 1
        
        # Check for divergence patterns with timing
        if price_short_term_lower and indicator_short_term_higher:
            enhanced_message = (f"Bullish {indicator_name} divergence: Price declined over {price_change_periods} periods "
                              f"({recent_prices[-self.short_term_lookback]:.2f} to {recent_prices[-1]:.2f}) while "
                              f"{indicator_name} increased ({recent_indicator[-self.short_term_lookback]:.2f} to {recent_indicator[-1]:.2f})")
            
            pattern = Pattern(
                "bullish_divergence",
                enhanced_message,
                timestamp=timestamp,
                indicator=indicator_name,
                lookback_periods=price_change_periods,
                price_start=recent_prices[-self.short_term_lookback],
                price_end=recent_prices[-1],
                indicator_start=recent_indicator[-self.short_term_lookback],
                indicator_end=recent_indicator[-1]
            )
            self._log_detection(pattern)
            patterns.append(pattern)

        if price_short_term_higher and indicator_short_term_lower:
            enhanced_message = (f"Bearish {indicator_name} divergence: Price increased over {price_change_periods} periods "
                              f"({recent_prices[-self.short_term_lookback]:.2f} to {recent_prices[-1]:.2f}) while "
                              f"{indicator_name} decreased ({recent_indicator[-self.short_term_lookback]:.2f} to {recent_indicator[-1]:.2f})")
            
            pattern = Pattern(
                "bearish_divergence",
                enhanced_message,
                timestamp=timestamp,
                indicator=indicator_name,
                lookback_periods=price_change_periods,
                price_start=recent_prices[-self.short_term_lookback],
                price_end=recent_prices[-1],
                indicator_start=recent_indicator[-self.short_term_lookback],
                indicator_end=recent_indicator[-1]
            )
            self._log_detection(pattern)
            patterns.append(pattern)
        
        return patterns
    
    def _detect_stochastic_divergences(self, 
                                      recent_prices: List[float], 
                                      recent_stoch: List[float],
                                      market_data: MarketData,
                                      original_start_index: int) -> List[Pattern]:
        """Detect divergences between price and Stochastic"""
        return self._detect_short_term_divergences(
            recent_prices, recent_stoch, market_data, "Stochastic",
            "Bullish stochastic divergence: price making lower lows while stochastic making higher lows.",
            "Bearish stochastic divergence: price making higher highs while stochastic making lower highs."
        )
    
    def _detect_macd_divergences(self, 
                                recent_prices: List[float], 
                                recent_macd: List[float],
                                market_data: MarketData,
                                original_start_index: int) -> List[Pattern]:
        """Detect divergences between price and MACD"""
        return self._detect_short_term_divergences(
            recent_prices, recent_macd, market_data, "MACD",
            "Bullish MACD divergence: price moving down while MACD trending up.",
            "Bearish MACD divergence: price moving up while MACD trending down."
        )