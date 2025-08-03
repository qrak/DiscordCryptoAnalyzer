from typing import Dict, Any, Optional, List, Union

import numpy as np

from src.indicators.base.technical_indicators import TechnicalIndicators
from src.indicators.base.pattern_recognizer import PatternRecognizer
from src.logger.logger import Logger


def fmt(val, precision=8):
    """Format a value with appropriate precision based on its magnitude"""
    if isinstance(val, (int, float)) and not np.isnan(val):
        if abs(val) > 0 and abs(val) < 0.000001:
            return f"{val:.{precision}e}"  # Scientific notation for very small values
        elif abs(val) < 0.001:
            return f"{val:.{max(precision, 8)}f}"  # More decimal places for small values
        elif abs(val) < 0.01:
            return f"{val:.6f}"
        elif abs(val) < 0.1:
            return f"{val:.4f}"
        elif abs(val) < 10:
            return f"{val:.{precision}f}"
        else:
            return f"{val:.2f}"
    return "N/A"


class IndicatorCalculator:
    """Centralized calculator for technical indicators with caching capability"""
    
    def __init__(self, logger: Optional[Logger] = None):
        """Initialize the indicator calculator with technical indicators instance"""
        self.logger = logger
        self.ti = TechnicalIndicators()
        self.pattern_recognizer = PatternRecognizer(logger=logger)
        
        # Cache storage
        self._cache = {}
        self._ohlcv_hash = None
        
        # Define indicator thresholds as instance variable so it's available to all methods
        self.INDICATOR_THRESHOLDS = {
            'rsi': {'oversold': 30, 'overbought': 70},
            'stoch_k': {'oversold': 20, 'overbought': 80},
            'stoch_d': {'oversold': 20, 'overbought': 80},
            'williams_r': {'oversold': -80, 'overbought': -20},
            'adx': {'weak': 25, 'strong': 50, 'very_strong': 75},
            'mfi': {'oversold': 20, 'overbought': 80},
            'bb_width': {'tight': 2, 'wide': 10}
        }
        
    def get_indicators(self, ohlcv_data: np.ndarray) -> Dict[str, np.ndarray]:
        """Calculate all technical indicators with caching based on data hash"""
        data_hash = self._hash_data(ohlcv_data)
        
        # Return cached results if data hasn't changed
        if data_hash == self._ohlcv_hash and self._cache:
            if self.logger:
                self.logger.debug("Using cached technical indicators")
            # Ensure cache contains all expected keys before returning
            required_keys = {"ichimoku_conversion", "ichimoku_base", "ichimoku_span_a", "ichimoku_span_b"}
            if required_keys.issubset(self._cache.keys()):
                return self._cache
            else:
                if self.logger:
                    self.logger.debug("Cache miss due to missing keys, recalculating.")

        # Calculate new indicators if data changed or cache is empty
        self._ohlcv_hash = data_hash
        self.ti.get_data(ohlcv_data)
        
        # Calculate all indicators
        indicators = {
            "vwap": self.ti.vol.rolling_vwap(length=14),
            "twap": self.ti.vol.twap(length=14),
            "mfi": self.ti.vol.mfi(length=14),
            "obv": self.ti.vol.obv(length=14),
            "cmf": self.ti.vol.chaikin_money_flow(length=20),
            "force_index": self.ti.vol.force_index(length=13),
            "rsi": self.ti.momentum.rsi(length=14),
            "stoch_k": self.ti.momentum.stochastic()[0],
            "stoch_d": self.ti.momentum.stochastic()[1],
            "williams_r": self.ti.momentum.williams_r(length=14),
            "adx": self.ti.trend.adx()[0],
            "plus_di": self.ti.trend.adx()[1],
            "minus_di": self.ti.trend.adx()[2],
            "atr": self.ti.volatility.atr(length=14),
            "kurtosis": self.ti.statistical.kurtosis(length=30),
            "zscore": self.ti.statistical.zscore(length=20),
            "hurst": self.ti.statistical.hurst(max_lag=20),
        }
        
        # Calculate MACD separately to handle the tuple return
        macd_line, macd_signal, macd_hist = self.ti.momentum.macd()
        indicators["macd_line"] = macd_line
        indicators["macd_signal"] = macd_signal
        indicators["macd_hist"] = macd_hist
        
        # Calculate Bollinger Bands separately
        bb_upper, bb_middle, bb_lower = self.ti.volatility.bollinger_bands()
        indicators["bb_upper"] = bb_upper
        indicators["bb_middle"] = bb_middle
        indicators["bb_lower"] = bb_lower
        
        # Calculate Supertrend separately
        supertrend, supertrend_direction = self.ti.trend.supertrend()
        indicators["supertrend"] = supertrend
        indicators["supertrend_direction"] = supertrend_direction

        # Calculate Ichimoku Cloud separately
        conversion, base, span_a, span_b = self.ti.trend.ichimoku_cloud(
            conversion_length=9,
            base_length=26,
            lagging_span2_length=52,
            displacement=26
        )
        indicators["ichimoku_conversion"] = conversion  # Tenkan-sen
        indicators["ichimoku_base"] = base  # Kijun-sen
        indicators["ichimoku_span_a"] = span_a  # Senkou Span A
        indicators["ichimoku_span_b"] = span_b  # Senkou Span B
        
        # Add support and resistance indicators
        support, resistance = self.ti.support_resistance.support_resistance(length=30)
        indicators["basic_support"] = support
        indicators["basic_resistance"] = resistance
        
        # Add advanced support and resistance with volume analysis
        adv_support, adv_resistance = self.ti.support_resistance.advanced_support_resistance(
            length=25,
            strength_threshold=1,
            persistence=1,
            volume_factor=1.5,
            price_factor=0.004
        )
        indicators["support_resistance"] = [adv_support[-1], adv_resistance[-1]]
        
        # Add advanced trend indicators
        vortex_plus, vortex_minus = self.ti.trend.vortex_indicator(length=14)
        indicators["vortex_indicator"] = [vortex_plus, vortex_minus]
        
        # Add more momentum indicators
        indicators["tsi"] = self.ti.momentum.tsi(long_length=25, short_length=13)
        indicators["rmi"] = self.ti.momentum.rmi(length=14, momentum_length=5)
        indicators["ppo"] = self.ti.momentum.ppo(fast_length=12, slow_length=26)
        indicators["coppock"] = self.ti.momentum.coppock_curve()
        indicators["uo"] = self.ti.momentum.uo()
        indicators["kst"] = self.ti.momentum.kst()
        
        # Add more trend indicators
        indicators["trix"] = self.ti.trend.trix(length=18)
        indicators["pfe"] = self.ti.trend.pfe(n=10, m=10)
        
        # Calculate Chandelier Exit for trend reversals
        long_exit, short_exit = self.ti.volatility.chandelier_exit()
        indicators["chandelier_long"] = long_exit
        indicators["chandelier_short"] = short_exit
        
        # Store in cache
        self._cache = indicators
        
        if self.logger:
            self.logger.debug("Calculated new technical indicators")
            
        return indicators
        
    def get_long_term_indicators(self, ohlcv_data: np.ndarray) -> Dict[str, Any]:
        """Calculate long-term indicators for historical data"""
        data_hash = self._hash_data(ohlcv_data)
        cache_key = f"long_term_{data_hash}"
        
        if cache_key in self._cache:
            if self.logger:
                self.logger.debug("Using cached long-term indicators")
            return self._cache[cache_key]
            
        # Create new TI instance for long-term calculations
        # This avoids interfering with the regular timeframe indicators
        ti_lt = TechnicalIndicators()
        ti_lt.get_data(ohlcv_data)
        
        # Extract closing prices and volume
        close_prices = np.array([float(candle[4]) for candle in ohlcv_data])
        volumes = np.array([float(candle[5]) for candle in ohlcv_data])
        
        # Calculate SMAs for different periods
        sma_values = {}
        volume_sma_values = {}
        sma_periods = [20, 50, 100, 200]
        
        available_days = len(ohlcv_data)
        
        for period in sma_periods:
            if available_days >= period:
                sma = ti_lt.overlap.sma(close_prices, period)
                vol_sma = ti_lt.overlap.sma(volumes, period)
                
                # Store the latest value for each SMA period
                if not np.isnan(sma[-1]):
                    sma_values[period] = float(sma[-1])
                
                if not np.isnan(vol_sma[-1]):
                    volume_sma_values[period] = float(vol_sma[-1])
        
        # Calculate volatility (standard deviation of daily returns)
        volatility = None
        if available_days >= 7:  # At least a week of data
            daily_returns = np.diff(close_prices) / close_prices[:-1]
            volatility = float(np.std(daily_returns) * 100)  # Convert to percentage
            
        # Calculate overall price change
        price_change_pct = None
        volume_change_pct = None
        if available_days >= 2:
            price_change_pct = float((close_prices[-1] / close_prices[0] - 1) * 100)
            volume_change_pct = float((volumes[-1] / max(volumes[0], 1) - 1) * 100)
            

        daily_rsi = None
        daily_macd_line = None
        daily_macd_signal = None
        daily_macd_hist = None
        daily_atr = None
        daily_adx = None
        daily_plus_di = None
        daily_minus_di = None
        daily_obv = None
        daily_ichimoku_conversion = None
        daily_ichimoku_base = None
        daily_ichimoku_span_a = None
        daily_ichimoku_span_b = None

        if available_days >= 14:  # Need enough data for standard periods
            rsi_vals = ti_lt.momentum.rsi(length=14)
            if rsi_vals is not None and not np.isnan(rsi_vals[-1]):
                daily_rsi = float(rsi_vals[-1])

            atr_vals = ti_lt.volatility.atr(length=14)
            if atr_vals is not None and not np.isnan(atr_vals[-1]):
                daily_atr = float(atr_vals[-1])

            # --- ADD ADX/DI CALCULATION ---
            adx_vals, plus_di_vals, minus_di_vals = ti_lt.trend.adx(length=14)
            if adx_vals is not None and not np.isnan(adx_vals[-1]):
                daily_adx = float(adx_vals[-1])
            if plus_di_vals is not None and not np.isnan(plus_di_vals[-1]):
                daily_plus_di = float(plus_di_vals[-1])
            if minus_di_vals is not None and not np.isnan(minus_di_vals[-1]):
                daily_minus_di = float(minus_di_vals[-1])

            obv_vals = ti_lt.vol.obv() # Default length usually not needed or handled internally
            if obv_vals is not None and not np.isnan(obv_vals[-1]):
                daily_obv = float(obv_vals[-1])

        if available_days >= 26:  # Need enough data for MACD
            macd_line, macd_signal, macd_hist = ti_lt.momentum.macd()
            if macd_line is not None and not np.isnan(macd_line[-1]):
                daily_macd_line = float(macd_line[-1])
            if macd_signal is not None and not np.isnan(macd_signal[-1]):
                daily_macd_signal = float(macd_signal[-1])
            if macd_hist is not None and not np.isnan(macd_hist[-1]):
                daily_macd_hist = float(macd_hist[-1])

        # --- ADD ICHIMOKU CALCULATION ---
        if available_days >= 52: # Standard Ichimoku needs 52 periods
            conversion, base, span_a, span_b = ti_lt.trend.ichimoku_cloud()
            if conversion is not None and not np.isnan(conversion[-1]):
                daily_ichimoku_conversion = float(conversion[-1])
            if base is not None and not np.isnan(base[-1]):
                daily_ichimoku_base = float(base[-1])
            if span_a is not None and len(span_a) > 0:
                 last_valid_span_a_index = np.where(~np.isnan(span_a))[0]
                 if len(last_valid_span_a_index) > 0:
                     daily_ichimoku_span_a = float(span_a[last_valid_span_a_index[-1]])

            if span_b is not None and len(span_b) > 0:
                 last_valid_span_b_index = np.where(~np.isnan(span_b))[0]
                 if len(last_valid_span_b_index) > 0:
                     daily_ichimoku_span_b = float(span_b[last_valid_span_b_index[-1]])

        result = {
            'sma_values': sma_values,
            'volume_sma_values': volume_sma_values,
            'price_change': price_change_pct,
            'volume_change': volume_change_pct,
            'volatility': volatility,
            'available_days': available_days,
            # --- ADDED ---
            'daily_rsi': daily_rsi,
            'daily_macd_line': daily_macd_line,
            'daily_macd_signal': daily_macd_signal,
            'daily_macd_hist': daily_macd_hist,
            'daily_atr': daily_atr,
            'daily_adx': daily_adx,
            'daily_plus_di': daily_plus_di,
            'daily_minus_di': daily_minus_di,
            'daily_obv': daily_obv,
            'daily_ichimoku_conversion': daily_ichimoku_conversion,
            'daily_ichimoku_base': daily_ichimoku_base,
            'daily_ichimoku_span_a': daily_ichimoku_span_a,
            'daily_ichimoku_span_b': daily_ichimoku_span_b
            # --- END ADDED ---
        }
        
        # Ensure we're not returning numpy types that might not be recognized properly
        result = {k: float(v) if isinstance(v, (np.floating, float)) and not np.isnan(v) else v 
                  for k, v in result.items() if k not in ('sma_values', 'volume_sma_values')}
        
        # Store in cache
        self._cache[cache_key] = result
        return result
        
    def detect_patterns(self, ohlcv_data: np.ndarray, technical_history: Dict[str, np.ndarray]) -> Dict[str, Any]:
        """Detect technical patterns using the pattern recognizer"""
        data_hash = self._hash_data(ohlcv_data)
        cache_key = f"patterns_{data_hash}"
        
        if cache_key in self._cache:
            if self.logger:
                self.logger.debug("Using cached pattern detection results")
            return self._cache[cache_key]
            
        patterns = self.pattern_recognizer.detect_patterns(
            ohlcv=ohlcv_data,
            technical_history=technical_history
        )
          # Store in cache
        self._cache[cache_key] = patterns
        return patterns
        
    def get_all_patterns(self, ohlcv_data: np.ndarray, technical_history: Dict[str, np.ndarray]) -> List[Dict]:
        """Centralized pattern detection using PatternRecognizer
        
        Args:
            ohlcv_data: OHLCV data array
            technical_history: Dictionary of technical indicator histories
            
        Returns:
            List of all detected patterns as dictionaries
        """
        try:
            # Use the existing PatternRecognizer instead of duplicating logic
            patterns_dict = self.pattern_recognizer.detect_patterns(
                ohlcv=ohlcv_data, 
                technical_history=technical_history
            )
            
            # Flatten all pattern categories into a single list
            all_patterns = []
            for category, patterns_list in patterns_dict.items():
                all_patterns.extend(patterns_list)
            
            if self.logger:
                self.logger.debug(f"Detected {len(all_patterns)} patterns using PatternRecognizer")
                
            return all_patterns
                
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Error in pattern detection: {e}")
            return []

    def _hash_data(self, data: np.ndarray) -> str:
        """Create a simple hash of the data for caching"""
        if data is None or len(data) == 0:
            return "empty"
            
        # Use last few candles and length for hashing
        # This is faster than hashing the entire array
        try:
            last_candle = data[-1].tobytes()
            data_len = len(data)
            return f"{hash(last_candle)}_{data_len}"
        except (AttributeError, IndexError):
            # Fallback if tobytes() is not available
            return str(hash(str(data[-1])) + len(data))
        
    def get_indicator_value(self, td: dict, key: str) -> Union[float, str]:
        """Get indicator value with proper type checking and error handling
        
        Args:
            td: Technical data dictionary
            key: Indicator key to retrieve
            
        Returns:
            float or str: Indicator value or 'N/A' if invalid
        """
        try:
            value = td[key]
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, (list, tuple)) and len(value) == 1:
                return float(value[0])
            if isinstance(value, (list, tuple)) and len(value) > 1:
                return float(value[-1])
            return 'N/A'
        except (KeyError, TypeError, ValueError, IndexError):
            return 'N/A'
        
    def get_indicator_values(self, td: dict, key: str, expected_count: int = 2) -> List[float]:
        """Get multiple indicator values with proper type checking
        
        Args:
            td: Technical data dictionary
            key: Indicator key to retrieve
            expected_count: Number of values expected
            
        Returns:
            list[float]: List of indicator values or empty list if invalid
        """
        try:
            values = td[key]
            if not isinstance(values, (list, tuple)) or len(values) != expected_count:
                return []
            return [float(val) if not isinstance(val, str) else val for val in values]
        except (KeyError, TypeError, ValueError):
            return []
    
    def calculate_bb_width(self, td: dict) -> float:
         """Calculate Bollinger Band width percentage.
         
         Args:
             td: Technical data dictionary with bb_upper, bb_lower, bb_middle
             
         Returns:
             float: BB width as percentage or 0.0 if calculation fails
         """
         upper = self.get_indicator_value(td, "bb_upper")
         lower = self.get_indicator_value(td, "bb_lower")
         middle = self.get_indicator_value(td, "bb_middle")

         if upper != 'N/A' and lower != 'N/A' and middle != 'N/A' and middle != 0:
             try:
                 return ((upper - lower) / middle) * 100
             except (ZeroDivisionError, TypeError):
                 return 0.0
         return 0.0

    def format_timestamp(self, timestamp_ms) -> str:
        """Format a timestamp from milliseconds since epoch to a human-readable string
        
        Args:
            timestamp_ms: Timestamp in milliseconds
            
        Returns:
            str: Formatted timestamp string or empty string on error
        """
        try:
            from datetime import datetime
            dt = datetime.fromtimestamp(float(timestamp_ms) / 1000.0)
            return f"({dt.strftime('%Y-%m-%d %H:%M')}) "
        except (ValueError, TypeError):
            return ""
            
    def extract_key_patterns(self, context) -> str:
        """Extract key technical patterns from context data
        
        DEPRECATED: This method provides basic pattern extraction. 
        Use get_all_patterns() for more sophisticated pattern detection via PatternRecognizer.
        
        Args:
            context: Analysis context with technical data and market metrics
            
        Returns:
            str: Formatted key patterns section
        """
        if self.logger:
            self.logger.debug("extract_key_patterns is deprecated. Use get_all_patterns() for advanced pattern detection.")
        
        # Try to use PatternRecognizer first
        try:
            if hasattr(context, 'ohlcv_candles') and hasattr(context, 'technical_data'):
                ohlcv_data = context.ohlcv_candles
                technical_history = context.technical_data.get('history', {})
                patterns = self.get_all_patterns(ohlcv_data, technical_history)
                
                if patterns:
                    pattern_summaries = []
                    for pattern in patterns[-3:]:  # Show last 3 patterns
                        description = pattern.get('description', 'Unknown pattern')
                        pattern_summaries.append(f"- {description}")
                    
                    if pattern_summaries:
                        return "## Key Patterns (PatternRecognizer):\n" + "\n".join(pattern_summaries)
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Could not use PatternRecognizer, falling back to basic: {e}")
        
        
        # Fallback to basic pattern extraction
        patterns_summary = []
        
        # Check market metrics if available
        if context.market_metrics:
            # Daily price moves
            if '1D' in context.market_metrics:
                daily_change = context.market_metrics['1D']['metrics'].get('price_change_percent', 0)
                if abs(daily_change) > 5:
                    patterns_summary.append(f"Large daily move: {daily_change:.2f}% in the last 24 hours")
            
            # Weekly trend changes
            if '7D' in context.market_metrics and 'indicator_changes' in context.market_metrics['7D']:
                changes = context.market_metrics['7D']['indicator_changes']
                rsi_change = changes.get('rsi_change', 0)
                if abs(rsi_change) > 15:
                    direction = "strengthening" if rsi_change > 0 else "weakening"
                    patterns_summary.append(f"Significant momentum {direction}: RSI changed by {abs(rsi_change):.1f} points in 7 days")
                
                macd_start = changes.get('macd_line_start', 0)
                macd_end = changes.get('macd_line_end', 0)
                if macd_start * macd_end < 0:
                    direction = "bullish" if macd_end > 0 else "bearish" if macd_end < 0 else "neutral"
                    patterns_summary.append(f"MACD crossed zero line ({direction})")
        
        # Check technical data if available
        if context.technical_data and context.ohlcv_candles.size > 0:
            td = context.technical_data
            ts_str = self.format_timestamp(context.ohlcv_candles[-1, 0])
            
            # RSI conditions
            rsi = self.get_indicator_value(td, 'rsi')
            if rsi != 'N/A':
                if rsi < self.INDICATOR_THRESHOLDS['rsi']['oversold']:
                    patterns_summary.append(f"{ts_str}Currently Oversold: RSI below {self.INDICATOR_THRESHOLDS['rsi']['oversold']}")
                elif rsi > self.INDICATOR_THRESHOLDS['rsi']['overbought']:
                    patterns_summary.append(f"{ts_str}Currently Overbought: RSI above {self.INDICATOR_THRESHOLDS['rsi']['overbought']}")
            
            # Bollinger Bands
            bb_width = self.calculate_bb_width(td)
            if bb_width < self.INDICATOR_THRESHOLDS['bb_width']['tight']:
                tightness = (self.INDICATOR_THRESHOLDS['bb_width']['tight'] - bb_width) / self.INDICATOR_THRESHOLDS['bb_width']['tight'] * 100
                patterns_summary.append(f"{ts_str}Tight Bollinger Bands ({bb_width:.2f}% width) suggesting potential volatility expansion. {tightness:.1f}% tighter than threshold.")
            elif bb_width > self.INDICATOR_THRESHOLDS['bb_width']['wide']:
                patterns_summary.append(f"{ts_str}Wide Bollinger Bands ({bb_width:.2f}% width) indicating high volatility phase.")
            
            # SMA levels
            if context.long_term_data and context.long_term_data.get('sma_values') and context.current_price:
                for period, value in context.long_term_data['sma_values'].items():
                    if value and abs((context.current_price / value - 1) * 100) < 1:
                        patterns_summary.append(f"{ts_str}Price near critical SMA({period}): {value:.2f}")

        if patterns_summary:
            return "KEY PATTERNS DETECTED:\n- " + "\n- ".join(patterns_summary)
        else:
            return ""
                
    def format_market_period_metrics(self, market_metrics: dict) -> str:
        """Format market metrics for different time periods
        
        Args:
            market_metrics: Dictionary containing market metrics for different periods
            
        Returns:
            str: Formatted market period metrics text
        """
        if not market_metrics:
            return ""

        lines = ["MARKET PERIOD METRICS:"]
        period_order = ["1D", "2D", "3D", "7D", "30D"]

        for period_name in period_order:
            if period_name in market_metrics:
                market_period = market_metrics[period_name]
                metrics = market_period.get('metrics', {})

                lines.append(f"\n=== {period_name} Period Analysis ===")
                lines.append(f"Price Movement:")
                
                # Format lowest/highest price with appropriate precision for small values
                lowest_price = metrics.get('lowest_price', 'N/A')
                lowest_price_str = fmt(lowest_price, 8) if isinstance(lowest_price, (int, float)) else 'N/A'
                
                highest_price = metrics.get('highest_price', 'N/A')
                highest_price_str = fmt(highest_price, 8) if isinstance(highest_price, (int, float)) else 'N/A'
                
                lines.append(f"- Period Low: {lowest_price_str}")
                lines.append(f"- Period High: {highest_price_str}")
                
                price_change = metrics.get('price_change', 'N/A')
                price_change_str = fmt(price_change, 8) if isinstance(price_change, (int, float)) else 'N/A'
                
                price_change_pct = metrics.get('price_change_percent', 'N/A')
                price_change_pct_str = f"{price_change_pct:.2f}%" if isinstance(price_change_pct, (int, float)) else "N/A"
                
                lines.append(f"- Change: {price_change_str} ({price_change_pct_str})")
                volatility = metrics.get('volatility', 'N/A')
                volatility_str = f"{volatility:.2f}%" if isinstance(volatility, (int, float)) else "N/A"
                lines.append(f"- Volatility: {volatility_str}")

                lines.append(f"Volume Analysis:")
                lines.append(f"- Total Volume: {metrics.get('total_volume', 'N/A')}")
                lines.append(f"- Average Volume: {metrics.get('avg_volume', 'N/A')}")

                # Add Indicator Changes directly after the period if available (7D, 30D)
                if period_name in ["7D", "30D"] and 'indicator_changes' in market_period:
                    indicator_changes = market_period['indicator_changes']
                    if indicator_changes:
                        lines.append(f"\n--- {period_name} Indicator Changes ---")
                        if 'rsi_start' in indicator_changes and 'rsi_end' in indicator_changes:
                            rsi_start = indicator_changes['rsi_start']
                            rsi_end = indicator_changes['rsi_end']
                            rsi_change = indicator_changes.get('rsi_change', 0)
                            lines.append(f"RSI: {rsi_start:.1f} → {rsi_end:.1f} (Change: {rsi_change:.1f})")

                        if 'macd_line_start' in indicator_changes and 'macd_line_end' in indicator_changes:
                            macd_start = indicator_changes['macd_line_start']
                            macd_end = indicator_changes['macd_line_end']
                            macd_change = indicator_changes.get('macd_line_change', 0)
                            # Format MACD values consistently
                            macd_start_str = f"{macd_start:.6f}" if isinstance(macd_start, (int, float)) else "N/A"
                            macd_end_str = f"{macd_end:.6f}" if isinstance(macd_end, (int, float)) else "N/A"
                            macd_change_str = f"{macd_change:.6f}" if isinstance(macd_change, (int, float)) else "N/A"
                            lines.append(f"MACD Line: {macd_start_str} → {macd_end_str} (Change: {macd_change_str})")

                        if 'adx_start' in indicator_changes and 'adx_end' in indicator_changes:
                            adx_start = indicator_changes['adx_start']
                            adx_end = indicator_changes['adx_end']
                            adx_change = indicator_changes.get('adx_change', 0)
                            lines.append(f"ADX: {adx_start:.1f} → {adx_end:.1f} (Change: {adx_change:.1f})")

                        if 'mfi_start' in indicator_changes and 'mfi_end' in indicator_changes:
                            mfi_start = indicator_changes['mfi_start']
                            mfi_end = indicator_changes.get('mfi_end', 'N/A')
                            mfi_change = indicator_changes.get('mfi_change', 0)
                            mfi_end_str = f"{mfi_end:.1f}" if isinstance(mfi_end, (int, float)) else "N/A"
                            lines.append(f"MFI: {mfi_start:.1f} → {mfi_end_str} (Change: {mfi_change:.1f})")

        return "\n".join(lines)

    def format_long_term_analysis(self, long_term_data: dict, current_price: float = None) -> str:
        """Format long-term analysis from historical data
        
        Args:
            long_term_data: Dictionary containing long-term metrics and indicators
            current_price: Current market price for comparison with SMAs
            
        Returns:
            str: Formatted long-term analysis text
        """
        if not long_term_data:
            return ""
        
        # If the token is completely new with no historical data
        if long_term_data.get('available_days', 0) == 0:
            return """
            LONG-TERM ANALYSIS (365-Day Daily Timeframe):
            No long-term historical data available. This appears to be a relatively new token with limited price history.
            Analysis must be based entirely on short-term data, which increases risk and uncertainty.
            """
        
        # If it's a newer token with limited but some history
        if long_term_data.get('is_new_token', False):
            limited_days = long_term_data.get('available_days', 0)
            
            # Get price change and volatility values
            price_change = long_term_data.get('price_change')
            price_change_str = f"{price_change:.2f}" if isinstance(price_change, (int, float)) else "N/A"
            
            volatility = long_term_data.get('volatility')
            volatility_str = f"{volatility:.2f}" if isinstance(volatility, (int, float)) else "N/A"
            
            return f"""
            LONG-TERM ANALYSIS (Daily Timeframe):
            This appears to be a relatively new token with {limited_days} days of available price history (less than full 365-day history).
            Limited historical data should be considered when making long-term projections.
            
            Available Historical Data:
            - Days of Price History: {limited_days}
            - Price Change: {price_change_str}% since first available data
            - Volatility: {volatility_str}% (daily return standard deviation)
            """
        
        # For tokens with substantial history
        sma_lines = []
        if long_term_data.get('sma_values'):
            for period, value in long_term_data['sma_values'].items():
                sma_lines.append(f"- SMA({period}): {fmt(value, 8)}")
        
        sma_text = ""
        if sma_lines:
            sma_text = "Moving Averages (Daily):\n" + "\n".join(sma_lines)
        
        vol_sma_lines = []
        if long_term_data.get('volume_sma_values'):
            for period, value in long_term_data['volume_sma_values'].items():
                vol_sma_lines.append(f"- Volume SMA({period}): {value:.2f}")
        
        vol_sma_text = ""
        if vol_sma_lines:
            vol_sma_text = "\n\nVolume Moving Averages (Daily):\n" + "\n".join(vol_sma_lines)
        
        # Price position relative to SMAs - bullish/bearish signals
        price_position = ""
        if long_term_data.get('sma_values') and current_price:
            sma_values = long_term_data['sma_values']
            price = current_price
            
            above_count = sum(1 for sma_value in sma_values.values() if price > sma_value)
            below_count = sum(1 for sma_value in sma_values.values() if price < sma_value)
            
            if above_count > below_count:
                price_position = f"\n\nPrice Position: Price is above {above_count}/{len(sma_values)} major SMAs, suggesting overall bullish momentum."
            elif below_count > above_count:
                price_position = f"\n\nPrice Position: Price is below {below_count}/{len(sma_values)} major SMAs, suggesting overall bearish momentum."
            
            # Golden/Death Cross check
            if 50 in sma_values and 200 in sma_values:
                sma50 = sma_values[50]
                sma200 = sma_values[200]
                
                if sma50 > sma200:
                    # Golden Cross
                    cross_pct = ((sma50 / sma200) - 1) * 100
                    price_position += f"\nGolden Cross: SMA(50) is {cross_pct:.2f}% above SMA(200), indicating a potential long-term bullish trend."
                elif sma200 > sma50:
                    # Death Cross
                    cross_pct = ((sma200 / sma50) - 1) * 100
                    price_position += f"\nDeath Cross: SMA(50) is {cross_pct:.2f}% below SMA(200), indicating a potential long-term bearish trend."
        
        # --- ADD FORMATTING FOR DAILY INDICATORS ---
        daily_indicators_text = "\n\nCurrent Daily Indicators:\n"
        daily_rsi = long_term_data.get('daily_rsi')
        if daily_rsi is not None:
            rsi_cond = "Neutral"
            if daily_rsi < self.INDICATOR_THRESHOLDS['rsi']['oversold']: rsi_cond = "Oversold"
            elif daily_rsi > self.INDICATOR_THRESHOLDS['rsi']['overbought']: rsi_cond = "Overbought"
            daily_indicators_text += f"- Daily RSI(14): {daily_rsi:.1f} ({rsi_cond})\n"
        else:
            daily_indicators_text += "- Daily RSI(14): N/A\n"

        daily_macd_line = long_term_data.get('daily_macd_line')
        daily_macd_signal = long_term_data.get('daily_macd_signal')
        daily_macd_hist = long_term_data.get('daily_macd_hist')
        if daily_macd_line is not None and daily_macd_signal is not None and daily_macd_hist is not None:
            macd_cond = "Neutral"
            if daily_macd_line > daily_macd_signal and daily_macd_hist > 0: macd_cond = "Bullish Momentum"
            elif daily_macd_line < daily_macd_signal and daily_macd_hist < 0: macd_cond = "Bearish Momentum"
            daily_indicators_text += f"- Daily MACD(12,26,9): Line={fmt(daily_macd_line, 8)}, Signal={fmt(daily_macd_signal, 8)}, Hist={fmt(daily_macd_hist, 8)} ({macd_cond})\n"
        else:
            daily_indicators_text += "- Daily MACD(12,26,9): N/A\n"
        
        daily_atr = long_term_data.get('daily_atr')
        if daily_atr is not None:
             daily_indicators_text += f"- Daily ATR(14): {fmt(daily_atr, 8)} (Avg True Range)\n"
        else:
             daily_indicators_text += "- Daily ATR(14): N/A\n"
             
        # --- ADD ADX/DI FORMATTING ---
        daily_adx = long_term_data.get('daily_adx')
        daily_plus_di = long_term_data.get('daily_plus_di')
        daily_minus_di = long_term_data.get('daily_minus_di')
        if daily_adx is not None and daily_plus_di is not None and daily_minus_di is not None:
            adx_cond = "Weak/No Trend"
            if daily_adx > self.INDICATOR_THRESHOLDS['adx']['very_strong']: adx_cond = "Extremely Strong Trend"
            elif daily_adx > self.INDICATOR_THRESHOLDS['adx']['strong']: adx_cond = "Very Strong Trend"
            elif daily_adx > self.INDICATOR_THRESHOLDS['adx']['weak']: adx_cond = "Strong Trend"
            
            # Basic DI condition (advanced pattern detection handled by PatternRecognizer)
            di_cond = "Neutral"
            if daily_plus_di > daily_minus_di: di_cond = "Bullish Pressure (+DI > -DI)"
            elif daily_minus_di > daily_plus_di: di_cond = "Bearish Pressure (-DI > +DI)"
                    
            daily_indicators_text += f"- Daily ADX(14): {daily_adx:.1f} ({adx_cond}), +DI={daily_plus_di:.1f}, -DI={daily_minus_di:.1f} ({di_cond})\n"
        else:
            daily_indicators_text += "- Daily ADX/DI(14): N/A\n"
        # --- END ADX/DI FORMATTING ---

        # --- ADD OBV FORMATTING ---
        daily_obv = long_term_data.get('daily_obv')
        if daily_obv is not None:
            # OBV trend is more important than absolute value, but we show the value
            daily_indicators_text += f"- Daily OBV: {daily_obv:.0f} (Trend indicates volume flow)\n"
        else:
            daily_indicators_text += "- Daily OBV: N/A\n"
        # --- END OBV FORMATTING ---

        # --- ADD ICHIMOKU FORMATTING ---
        daily_conv = long_term_data.get('daily_ichimoku_conversion')
        daily_base = long_term_data.get('daily_ichimoku_base')
        daily_span_a = long_term_data.get('daily_ichimoku_span_a')
        daily_span_b = long_term_data.get('daily_ichimoku_span_b')
        if all(v is not None for v in [daily_conv, daily_base, daily_span_a, daily_span_b]):
            cloud_status = "Neutral"
            if daily_span_a > daily_span_b: cloud_status = "Bullish Cloud"
            elif daily_span_b > daily_span_a: cloud_status = "Bearish Cloud"
            price_cloud = "N/A"
            if current_price:
                if current_price > max(daily_span_a, daily_span_b): price_cloud = "Above Cloud (Bullish)"
                elif current_price < min(daily_span_a, daily_span_b): price_cloud = "Below Cloud (Bearish)"
                else: price_cloud = "Inside Cloud (Neutral/Uncertain)"

            tk_cross = "Neutral"
            if daily_conv > daily_base: tk_cross = "Bullish TK Cross"
            elif daily_base > daily_conv: tk_cross = "Bearish TK Cross"

            daily_indicators_text += (f"- Daily Ichimoku: Conv={daily_conv:.6f}, Base={daily_base:.6f}, "
                                      f"SpanA={daily_span_a:.6f}, SpanB={daily_span_b:.6f}\n"
                                      f"  * Cloud: {cloud_status}, Price: {price_cloud}, TK Cross: {tk_cross}\n")
        else:
            daily_indicators_text += "- Daily Ichimoku Cloud: N/A (Requires 52+ days)\n"
        # --- END ICHIMOKU FORMATTING ---

        if daily_indicators_text == "\n\nCurrent Daily Indicators:\n":  # If no daily indicators were added
             daily_indicators_text = ""
        # --- END FORMATTING ---

        # Process values that might be N/A
        price_change = long_term_data.get('price_change')
        price_change_str = f"{price_change:.2f}" if isinstance(price_change, (int, float)) else "N/A"
        
        volume_change = long_term_data.get('volume_change')
        volume_change_str = f"{volume_change:.2f}" if isinstance(volume_change, (int, float)) else "N/A"
        
        volatility = long_term_data.get('volatility')
        volatility_str = f"{volatility:.2f}" if isinstance(volatility, (int, float)) else "N/A"
        
        return f"""
        LONG-TERM ANALYSIS (365-Day Daily Timeframe):
        
        Historical Performance:
        - Available Days of Data: {long_term_data.get('available_days')}
        - Long-Term Price Change: {price_change_str}%
        - Long-Term Volume Change: {volume_change_str}%
        - Historical Volatility: {volatility_str}%
        
        {sma_text}        {vol_sma_text}
        {price_position}
        {daily_indicators_text}
        """
