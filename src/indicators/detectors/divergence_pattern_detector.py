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
        rsi_patterns = self._detect_rsi_divergences(recent_prices, recent_rsi, data, original_start_index)
        patterns.extend(rsi_patterns)
        
        # Detect Stochastic divergences
        stoch_patterns = self._detect_stochastic_divergences(recent_prices, recent_stoch, data, original_start_index)
        patterns.extend(stoch_patterns)
        
        # Detect MACD divergences
        macd_patterns = self._detect_macd_divergences(recent_prices, recent_macd, data, original_start_index)
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
        
        # RSI divergences
        if price_making_lower_low and not rsi_making_lower_low:
            pattern = Pattern(
                "bullish_divergence",
                "Bullish divergence detected: price making lower lows while RSI is not. This suggests potential upward reversal.",
                timestamp=timestamp,  # Add timestamp
                indicator="RSI"
            )
            self._log_detection(pattern)
            patterns.append(pattern)

        if price_making_higher_high and not rsi_making_higher_high:
            pattern = Pattern(
                "bearish_divergence",
                "Bearish divergence detected: price making higher highs while RSI is not. This suggests potential downward reversal.",
                timestamp=timestamp,  # Add timestamp
                indicator="RSI"
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
        patterns = []
        
        # Recent price movement (for short-term divergences)
        price_short_term_lower = recent_prices[-1] < recent_prices[-self.short_term_lookback]
        price_short_term_higher = recent_prices[-1] > recent_prices[-self.short_term_lookback]
        
        # Recent indicator movements (for short-term divergences)
        stoch_short_term_lower = recent_stoch[-1] < recent_stoch[-self.short_term_lookback]
        stoch_short_term_higher = recent_stoch[-1] > recent_stoch[-self.short_term_lookback]
        
        # Get current timestamp
        timestamp = market_data.get_timestamp_at_index(len(market_data.ohlcv) - 1)
        
        # Stochastic divergences
        if price_short_term_lower and stoch_short_term_higher:
            pattern = Pattern(
                "bullish_divergence",
                "Bullish stochastic divergence: price making lower lows while stochastic making higher lows.",
                timestamp=timestamp,  # Add timestamp
                indicator="Stochastic"
            )
            self._log_detection(pattern)
            patterns.append(pattern)

        if price_short_term_higher and stoch_short_term_lower:
            pattern = Pattern(
                "bearish_divergence",
                "Bearish stochastic divergence: price making higher highs while stochastic making lower highs.",
                timestamp=timestamp,  # Add timestamp
                indicator="Stochastic"
            )
            self._log_detection(pattern)
            patterns.append(pattern)
        
        return patterns
    
    def _detect_macd_divergences(self, 
                                recent_prices: List[float], 
                                recent_macd: List[float],
                                market_data: MarketData,
                                original_start_index: int) -> List[Pattern]:
        """Detect divergences between price and MACD"""
        patterns = []
        
        # Recent price movement (for short-term divergences)
        price_short_term_lower = recent_prices[-1] < recent_prices[-self.short_term_lookback]
        price_short_term_higher = recent_prices[-1] > recent_prices[-self.short_term_lookback]
        
        # Recent indicator movements (for short-term divergences)
        macd_short_term_lower = recent_macd[-1] < recent_macd[-self.short_term_lookback]
        macd_short_term_higher = recent_macd[-1] > recent_macd[-self.short_term_lookback]
        
        # Get current timestamp
        timestamp = market_data.get_timestamp_at_index(len(market_data.ohlcv) - 1)
        
        # MACD divergences
        if price_short_term_higher and macd_short_term_lower:
            pattern = Pattern(
                "bearish_divergence",
                "Bearish MACD divergence: price moving up while MACD trending down.",
                timestamp=timestamp,  # Add timestamp
                indicator="MACD"
            )
            self._log_detection(pattern)
            patterns.append(pattern)

        if price_short_term_lower and macd_short_term_higher:
            pattern = Pattern(
                "bullish_divergence",
                "Bullish MACD divergence: price moving down while MACD trending up.",
                timestamp=timestamp,  # Add timestamp
                indicator="MACD"
            )
            self._log_detection(pattern)
            patterns.append(pattern)
        
        return patterns