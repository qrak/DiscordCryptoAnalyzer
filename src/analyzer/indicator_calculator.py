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
        """Calculate long-term indicators for historical data.

        Refactor note: Logic split into helper methods for clarity & reduced cyclomatic complexity.
        """
        data_hash = self._hash_data(ohlcv_data)
        cache_key = f"long_term_{data_hash}"

        if cache_key in self._cache:
            if self.logger:
                self.logger.debug("Using cached long-term indicators")
            return self._cache[cache_key]

        # Create new TI instance for long-term calculations (avoid interference with regular timeframe indicators)
        ti_lt = TechnicalIndicators()
        ti_lt.get_data(ohlcv_data)

        # Extract price & volume arrays
        close_prices, volumes = self._extract_price_volume_arrays(ohlcv_data)
        available_days = len(ohlcv_data)

        sma_values, volume_sma_values = self._compute_sma_sets(ti_lt, close_prices, volumes, available_days)
        price_change_pct, volume_change_pct = self._compute_change_metrics(close_prices, volumes, available_days)
        volatility = self._compute_volatility(close_prices, available_days)

        daily_indicators = self._compute_daily_indicators(ti_lt, available_days)

        result = {
            'sma_values': sma_values,
            'volume_sma_values': volume_sma_values,
            'price_change': price_change_pct,
            'volume_change': volume_change_pct,
            'volatility': volatility,
            'available_days': available_days,
            **daily_indicators
        }

        # Ensure we're not returning numpy types that might not be recognized properly
        result = {k: float(v) if isinstance(v, (np.floating, float)) and not np.isnan(v) else v
                  for k, v in result.items() if k not in ('sma_values', 'volume_sma_values')}

        # Store in cache
        self._cache[cache_key] = result
        return result

    # ---------------- Helper Methods (extracted for clarity) ----------------
    def _extract_price_volume_arrays(self, ohlcv_data: np.ndarray):
        close_prices = np.array([float(c[4]) for c in ohlcv_data])
        volumes = np.array([float(c[5]) for c in ohlcv_data])
        return close_prices, volumes

    def _compute_sma_sets(self, ti: TechnicalIndicators, close_prices: np.ndarray, volumes: np.ndarray, available_days: int):
        sma_periods = [20, 50, 100, 200]
        sma_values: Dict[int, float] = {}
        volume_sma_values: Dict[int, float] = {}
        for period in sma_periods:
            if available_days >= period:
                sma = ti.overlap.sma(close_prices, period)
                vol_sma = ti.overlap.sma(volumes, period)
                if not np.isnan(sma[-1]):
                    sma_values[period] = float(sma[-1])
                if not np.isnan(vol_sma[-1]):
                    volume_sma_values[period] = float(vol_sma[-1])
        return sma_values, volume_sma_values

    def _compute_change_metrics(self, close_prices: np.ndarray, volumes: np.ndarray, available_days: int):
        price_change_pct = volume_change_pct = None
        if available_days >= 2:
            price_change_pct = float((close_prices[-1] / close_prices[0] - 1) * 100)
            volume_change_pct = float((volumes[-1] / max(volumes[0], 1) - 1) * 100)
        return price_change_pct, volume_change_pct

    def _compute_volatility(self, close_prices: np.ndarray, available_days: int):
        if available_days >= 7:
            daily_returns = np.diff(close_prices) / close_prices[:-1]
            return float(np.std(daily_returns) * 100)
        return None

    def _compute_daily_indicators(self, ti: TechnicalIndicators, available_days: int) -> Dict[str, Any]:
        """Compute daily indicators based on available data."""
        out: Dict[str, Any] = self._initialize_daily_indicators()
        
        if available_days >= 14:
            self._compute_14_day_indicators(ti, out)
        
        if available_days >= 26:
            self._compute_26_day_indicators(ti, out)
            
        if available_days >= 52:
            self._compute_52_day_indicators(ti, out)
            
        return out
    
    def _initialize_daily_indicators(self) -> Dict[str, Any]:
        """Initialize dictionary with daily indicator keys."""
        return {
            'daily_rsi': None,
            'daily_macd_line': None,
            'daily_macd_signal': None,
            'daily_macd_hist': None,
            'daily_atr': None,
            'daily_adx': None,
            'daily_plus_di': None,
            'daily_minus_di': None,
            'daily_obv': None,
            'daily_ichimoku_conversion': None,
            'daily_ichimoku_base': None,
            'daily_ichimoku_span_a': None,
            'daily_ichimoku_span_b': None
        }
    
    def _compute_14_day_indicators(self, ti: TechnicalIndicators, out: Dict[str, Any]) -> None:
        """Compute indicators that require 14 days of data."""
        # RSI
        rsi_vals = ti.momentum.rsi(length=14)
        if rsi_vals is not None and not np.isnan(rsi_vals[-1]):
            out['daily_rsi'] = float(rsi_vals[-1])
        
        # ATR
        atr_vals = ti.volatility.atr(length=14)
        if atr_vals is not None and not np.isnan(atr_vals[-1]):
            out['daily_atr'] = float(atr_vals[-1])
        
        # ADX and DI
        adx_vals, plus_di_vals, minus_di_vals = ti.trend.adx(length=14)
        if adx_vals is not None and not np.isnan(adx_vals[-1]):
            out['daily_adx'] = float(adx_vals[-1])
        if plus_di_vals is not None and not np.isnan(plus_di_vals[-1]):
            out['daily_plus_di'] = float(plus_di_vals[-1])
        if minus_di_vals is not None and not np.isnan(minus_di_vals[-1]):
            out['daily_minus_di'] = float(minus_di_vals[-1])
        
        # OBV
        obv_vals = ti.vol.obv()
        if obv_vals is not None and not np.isnan(obv_vals[-1]):
            out['daily_obv'] = float(obv_vals[-1])
    
    def _compute_26_day_indicators(self, ti: TechnicalIndicators, out: Dict[str, Any]) -> None:
        """Compute indicators that require 26 days of data."""
        macd_line, macd_signal, macd_hist = ti.momentum.macd()
        
        if macd_line is not None and not np.isnan(macd_line[-1]):
            out['daily_macd_line'] = float(macd_line[-1])
        if macd_signal is not None and not np.isnan(macd_signal[-1]):
            out['daily_macd_signal'] = float(macd_signal[-1])
        if macd_hist is not None and not np.isnan(macd_hist[-1]):
            out['daily_macd_hist'] = float(macd_hist[-1])
    
    def _compute_52_day_indicators(self, ti: TechnicalIndicators, out: Dict[str, Any]) -> None:
        """Compute indicators that require 52 days of data."""
        conversion, base, span_a, span_b = ti.trend.ichimoku_cloud()
        
        if conversion is not None and not np.isnan(conversion[-1]):
            out['daily_ichimoku_conversion'] = float(conversion[-1])
        if base is not None and not np.isnan(base[-1]):
            out['daily_ichimoku_base'] = float(base[-1])
        
        # Handle span A
        self._process_ichimoku_span(span_a, out, 'daily_ichimoku_span_a')
        
        # Handle span B
        self._process_ichimoku_span(span_b, out, 'daily_ichimoku_span_b')
    
    def _process_ichimoku_span(self, span_data, out: Dict[str, Any], key: str) -> None:
        """Process Ichimoku span data safely."""
        if span_data is not None and len(span_data) > 0:
            span_valid = np.where(~np.isnan(span_data))[0]
            if len(span_valid) > 0:
                out[key] = float(span_data[span_valid[-1]])
        
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
        
        # Try PatternRecognizer first
        pattern_recognizer_result = self._try_pattern_recognizer(context)
        if pattern_recognizer_result:
            return pattern_recognizer_result
        
        # Fallback to basic pattern extraction
        patterns_summary = []
        patterns_summary.extend(self._extract_market_move_patterns(context))
        patterns_summary.extend(self._extract_technical_patterns(context))
        patterns_summary.extend(self._extract_sma_proximity_patterns(context))
        
        return "KEY PATTERNS DETECTED:\n- " + "\n- ".join(patterns_summary) if patterns_summary else ""
    
    # ---------- Pattern extraction helper methods ----------
    def _try_pattern_recognizer(self, context) -> str:
        """Try to use PatternRecognizer for advanced pattern detection"""
        try:
            if hasattr(context, 'ohlcv_candles') and hasattr(context, 'technical_data'):
                ohlcv_data = context.ohlcv_candles
                technical_history = context.technical_data.get('history', {})
                patterns = self.get_all_patterns(ohlcv_data, technical_history)
                
                if patterns:
                    pattern_summaries = [f"- {p.get('description', 'Unknown pattern')}" for p in patterns[-3:]]
                    return "## Key Patterns (PatternRecognizer):\n" + "\n".join(pattern_summaries)
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Could not use PatternRecognizer, falling back to basic: {e}")
        return ""
    
    def _extract_market_move_patterns(self, context) -> list:
        """Extract patterns from market metrics (large moves, momentum changes)"""
        patterns = []
        if not context.market_metrics:
            return patterns
        
        # Daily price moves
        if '1D' in context.market_metrics:
            daily_change = context.market_metrics['1D']['metrics'].get('price_change_percent', 0)
            if abs(daily_change) > 5:
                patterns.append(f"Large daily move: {daily_change:.2f}% in the last 24 hours")
        
        # Weekly trend changes
        if '7D' in context.market_metrics and 'indicator_changes' in context.market_metrics['7D']:
            changes = context.market_metrics['7D']['indicator_changes']
            
            # RSI momentum change
            rsi_change = changes.get('rsi_change', 0)
            if abs(rsi_change) > 15:
                direction = "strengthening" if rsi_change > 0 else "weakening"
                patterns.append(f"Significant momentum {direction}: RSI changed by {abs(rsi_change):.1f} points in 7 days")
            
            # MACD zero line cross
            macd_start = changes.get('macd_line_start', 0)
            macd_end = changes.get('macd_line_end', 0)
            if macd_start * macd_end < 0:
                direction = "bullish" if macd_end > 0 else "bearish" if macd_end < 0 else "neutral"
                patterns.append(f"MACD crossed zero line ({direction})")
        
        return patterns
    
    def _extract_technical_patterns(self, context) -> list:
        """Extract patterns from technical indicators (RSI, Bollinger Bands)"""
        patterns = []
        if not (context.technical_data and context.ohlcv_candles.size > 0):
            return patterns
        
        td = context.technical_data
        ts_str = self.format_timestamp(context.ohlcv_candles[-1, 0])
        
        # RSI conditions
        rsi = self.get_indicator_value(td, 'rsi')
        if rsi != 'N/A':
            if rsi < self.INDICATOR_THRESHOLDS['rsi']['oversold']:
                patterns.append(f"{ts_str}Currently Oversold: RSI below {self.INDICATOR_THRESHOLDS['rsi']['oversold']}")
            elif rsi > self.INDICATOR_THRESHOLDS['rsi']['overbought']:
                patterns.append(f"{ts_str}Currently Overbought: RSI above {self.INDICATOR_THRESHOLDS['rsi']['overbought']}")
        
        # Bollinger Bands volatility
        bb_width = self.calculate_bb_width(td)
        if bb_width < self.INDICATOR_THRESHOLDS['bb_width']['tight']:
            tightness = (self.INDICATOR_THRESHOLDS['bb_width']['tight'] - bb_width) / self.INDICATOR_THRESHOLDS['bb_width']['tight'] * 100
            patterns.append(f"{ts_str}Tight Bollinger Bands ({bb_width:.2f}% width) suggesting potential volatility expansion. {tightness:.1f}% tighter than threshold.")
        elif bb_width > self.INDICATOR_THRESHOLDS['bb_width']['wide']:
            patterns.append(f"{ts_str}Wide Bollinger Bands ({bb_width:.2f}% width) indicating high volatility phase.")
        
        return patterns
    
    def _extract_sma_proximity_patterns(self, context) -> list:
        """Extract patterns related to price proximity to key SMAs"""
        patterns = []
        if not (context.long_term_data and context.long_term_data.get('sma_values') and context.current_price):
            return patterns
        
        ts_str = self.format_timestamp(context.ohlcv_candles[-1, 0]) if context.ohlcv_candles.size > 0 else ""
        
        for period, value in context.long_term_data['sma_values'].items():
            if value and abs((context.current_price / value - 1) * 100) < 1:
                patterns.append(f"{ts_str}Price near critical SMA({period}): {value:.2f}")
        
        return patterns
                
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
                lines.extend(self._format_period_price_section(metrics))
                lines.extend(self._format_period_volume_section(metrics))
                
                # Add indicator changes for relevant periods
                if period_name in ["7D", "30D"] and 'indicator_changes' in market_period:
                    lines.extend(self._format_indicator_changes_section(market_period['indicator_changes'], period_name))

        return "\n".join(lines)
    
    # ---------- Market period metrics helper methods ----------
    def _format_period_price_section(self, metrics: dict) -> list:
        """Format price movement section for a period"""
        lines = ["Price Movement:"]
        
        # Low/High with proper precision
        lowest_price_str = fmt(metrics.get('lowest_price', 'N/A'), 8) if isinstance(metrics.get('lowest_price'), (int, float)) else 'N/A'
        highest_price_str = fmt(metrics.get('highest_price', 'N/A'), 8) if isinstance(metrics.get('highest_price'), (int, float)) else 'N/A'
        
        lines.append(f"- Period Low: {lowest_price_str}")
        lines.append(f"- Period High: {highest_price_str}")
        
        # Price change (absolute and percentage)
        price_change_str = fmt(metrics.get('price_change', 'N/A'), 8) if isinstance(metrics.get('price_change'), (int, float)) else 'N/A'
        price_change_pct = metrics.get('price_change_percent', 'N/A')
        price_change_pct_str = f"{price_change_pct:.2f}%" if isinstance(price_change_pct, (int, float)) else "N/A"
        
        lines.append(f"- Change: {price_change_str} ({price_change_pct_str})")
        
        # Volatility
        volatility = metrics.get('volatility', 'N/A')
        volatility_str = f"{volatility:.2f}%" if isinstance(volatility, (int, float)) else "N/A"
        lines.append(f"- Volatility: {volatility_str}")
        
        return lines
    
    def _format_period_volume_section(self, metrics: dict) -> list:
        """Format volume analysis section for a period"""
        return [
            "Volume Analysis:",
            f"- Total Volume: {metrics.get('total_volume', 'N/A')}",
            f"- Average Volume: {metrics.get('avg_volume', 'N/A')}"
        ]
    
    def _format_indicator_changes_section(self, indicator_changes: dict, period_name: str) -> list:
        """Format indicator changes section for periods that support it"""
        if not indicator_changes:
            return []
        
        lines = [f"\n--- {period_name} Indicator Changes ---"]
        
        # RSI changes
        if 'rsi_start' in indicator_changes and 'rsi_end' in indicator_changes:
            rsi_start = indicator_changes['rsi_start']
            rsi_end = indicator_changes['rsi_end']
            rsi_change = indicator_changes.get('rsi_change', 0)
            lines.append(f"RSI: {rsi_start:.1f} → {rsi_end:.1f} (Change: {rsi_change:.1f})")
        
        # MACD changes
        if 'macd_line_start' in indicator_changes and 'macd_line_end' in indicator_changes:
            macd_start = indicator_changes['macd_line_start']
            macd_end = indicator_changes['macd_line_end']
            macd_change = indicator_changes.get('macd_line_change', 0)
            
            macd_start_str = f"{macd_start:.6f}" if isinstance(macd_start, (int, float)) else "N/A"
            macd_end_str = f"{macd_end:.6f}" if isinstance(macd_end, (int, float)) else "N/A"
            macd_change_str = f"{macd_change:.6f}" if isinstance(macd_change, (int, float)) else "N/A"
            lines.append(f"MACD Line: {macd_start_str} → {macd_end_str} (Change: {macd_change_str})")
        
        # ADX changes
        if 'adx_start' in indicator_changes and 'adx_end' in indicator_changes:
            adx_start = indicator_changes['adx_start']
            adx_end = indicator_changes['adx_end']
            adx_change = indicator_changes.get('adx_change', 0)
            lines.append(f"ADX: {adx_start:.1f} → {adx_end:.1f} (Change: {adx_change:.1f})")
        
        # MFI changes
        if 'mfi_start' in indicator_changes and 'mfi_end' in indicator_changes:
            mfi_start = indicator_changes['mfi_start']
            mfi_end = indicator_changes.get('mfi_end', 'N/A')
            mfi_change = indicator_changes.get('mfi_change', 0)
            mfi_end_str = f"{mfi_end:.1f}" if isinstance(mfi_end, (int, float)) else "N/A"
            lines.append(f"MFI: {mfi_start:.1f} → {mfi_end_str} (Change: {mfi_change:.1f})")
        
        return lines

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
        
        # Handle edge cases
        if long_term_data.get('available_days', 0) == 0:
            return self._format_no_data_analysis()
        
        if long_term_data.get('is_new_token', False):
            return self._format_new_token_analysis(long_term_data)
        
        # Format standard analysis sections
        sma_text = self._format_sma_section(long_term_data)
        vol_sma_text = self._format_volume_sma_section(long_term_data)
        price_position = self._format_price_position_section(long_term_data, current_price)
        daily_indicators_text = self._format_daily_indicators_section(long_term_data, current_price)
        
        # Process main metrics
        price_change_str = self._format_numeric_value(long_term_data.get('price_change'), 2)
        volume_change_str = self._format_numeric_value(long_term_data.get('volume_change'), 2)
        volatility_str = self._format_numeric_value(long_term_data.get('volatility'), 2)
        
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
    
    # ---------- Long-term analysis helper methods ----------
    def _format_no_data_analysis(self) -> str:
        return """
        LONG-TERM ANALYSIS (365-Day Daily Timeframe):
        No long-term historical data available. This appears to be a relatively new token with limited price history.
        Analysis must be based entirely on short-term data, which increases risk and uncertainty.
        """
    
    def _format_new_token_analysis(self, long_term_data: dict) -> str:
        limited_days = long_term_data.get('available_days', 0)
        price_change_str = self._format_numeric_value(long_term_data.get('price_change'), 2)
        volatility_str = self._format_numeric_value(long_term_data.get('volatility'), 2)
        
        return f"""
        LONG-TERM ANALYSIS (Daily Timeframe):
        This appears to be a relatively new token with {limited_days} days of available price history (less than full 365-day history).
        Limited historical data should be considered when making long-term projections.
        
        Available Historical Data:
        - Days of Price History: {limited_days}
        - Price Change: {price_change_str}% since first available data
        - Volatility: {volatility_str}% (daily return standard deviation)
        """
    
    def _format_sma_section(self, long_term_data: dict) -> str:
        sma_lines = []
        if long_term_data.get('sma_values'):
            for period, value in long_term_data['sma_values'].items():
                sma_lines.append(f"- SMA({period}): {fmt(value, 8)}")
        return "Moving Averages (Daily):\n" + "\n".join(sma_lines) if sma_lines else ""
    
    def _format_volume_sma_section(self, long_term_data: dict) -> str:
        vol_sma_lines = []
        if long_term_data.get('volume_sma_values'):
            for period, value in long_term_data['volume_sma_values'].items():
                vol_sma_lines.append(f"- Volume SMA({period}): {value:.2f}")
        return "\n\nVolume Moving Averages (Daily):\n" + "\n".join(vol_sma_lines) if vol_sma_lines else ""
    
    def _format_price_position_section(self, long_term_data: dict, current_price: float) -> str:
        if not (long_term_data.get('sma_values') and current_price):
            return ""
        
        sma_values = long_term_data['sma_values']
        above_count = sum(1 for sma_value in sma_values.values() if current_price > sma_value)
        below_count = sum(1 for sma_value in sma_values.values() if current_price < sma_value)
        
        price_position = ""
        if above_count > below_count:
            price_position = f"\n\nPrice Position: Price is above {above_count}/{len(sma_values)} major SMAs, suggesting overall bullish momentum."
        elif below_count > above_count:
            price_position = f"\n\nPrice Position: Price is below {below_count}/{len(sma_values)} major SMAs, suggesting overall bearish momentum."
        
        # Add Golden/Death Cross analysis
        if 50 in sma_values and 200 in sma_values:
            sma50, sma200 = sma_values[50], sma_values[200]
            if sma50 > sma200:
                cross_pct = ((sma50 / sma200) - 1) * 100
                price_position += f"\nGolden Cross: SMA(50) is {cross_pct:.2f}% above SMA(200), indicating a potential long-term bullish trend."
            elif sma200 > sma50:
                cross_pct = ((sma200 / sma50) - 1) * 100
                price_position += f"\nDeath Cross: SMA(50) is {cross_pct:.2f}% below SMA(200), indicating a potential long-term bearish trend."
        
        return price_position
    
    def _format_daily_indicators_section(self, long_term_data: dict, current_price: float) -> str:
        daily_indicators_text = "\n\nCurrent Daily Indicators:\n"
        
        # RSI
        daily_rsi = long_term_data.get('daily_rsi')
        if daily_rsi is not None:
            rsi_cond = ("Oversold" if daily_rsi < self.INDICATOR_THRESHOLDS['rsi']['oversold'] else
                       "Overbought" if daily_rsi > self.INDICATOR_THRESHOLDS['rsi']['overbought'] else "Neutral")
            daily_indicators_text += f"- Daily RSI(14): {daily_rsi:.1f} ({rsi_cond})\n"
        else:
            daily_indicators_text += "- Daily RSI(14): N/A\n"
        
        # MACD
        macd_line = long_term_data.get('daily_macd_line')
        macd_signal = long_term_data.get('daily_macd_signal')
        macd_hist = long_term_data.get('daily_macd_hist')
        if all(v is not None for v in [macd_line, macd_signal, macd_hist]):
            macd_cond = ("Bullish Momentum" if macd_line > macd_signal and macd_hist > 0 else
                        "Bearish Momentum" if macd_line < macd_signal and macd_hist < 0 else "Neutral")
            daily_indicators_text += f"- Daily MACD(12,26,9): Line={fmt(macd_line, 8)}, Signal={fmt(macd_signal, 8)}, Hist={fmt(macd_hist, 8)} ({macd_cond})\n"
        else:
            daily_indicators_text += "- Daily MACD(12,26,9): N/A\n"
        
        # ATR
        daily_atr = long_term_data.get('daily_atr')
        if daily_atr is not None:
            daily_indicators_text += f"- Daily ATR(14): {fmt(daily_atr, 8)} (Avg True Range)\n"
        else:
            daily_indicators_text += "- Daily ATR(14): N/A\n"
        
        # ADX/DI
        daily_indicators_text += self._format_adx_section(long_term_data)
        
        # OBV
        daily_obv = long_term_data.get('daily_obv')
        if daily_obv is not None:
            daily_indicators_text += f"- Daily OBV: {daily_obv:.0f} (Trend indicates volume flow)\n"
        else:
            daily_indicators_text += "- Daily OBV: N/A\n"
        
        # Ichimoku
        daily_indicators_text += self._format_ichimoku_section(long_term_data, current_price)
        
        return daily_indicators_text if daily_indicators_text != "\n\nCurrent Daily Indicators:\n" else ""
    
    def _format_adx_section(self, long_term_data: dict) -> str:
        daily_adx = long_term_data.get('daily_adx')
        daily_plus_di = long_term_data.get('daily_plus_di')
        daily_minus_di = long_term_data.get('daily_minus_di')
        
        if all(v is not None for v in [daily_adx, daily_plus_di, daily_minus_di]):
            adx_cond = ("Extremely Strong Trend" if daily_adx > self.INDICATOR_THRESHOLDS['adx']['very_strong'] else
                       "Very Strong Trend" if daily_adx > self.INDICATOR_THRESHOLDS['adx']['strong'] else
                       "Strong Trend" if daily_adx > self.INDICATOR_THRESHOLDS['adx']['weak'] else "Weak/No Trend")
            
            di_cond = ("Bullish Pressure (+DI > -DI)" if daily_plus_di > daily_minus_di else
                      "Bearish Pressure (-DI > +DI)" if daily_minus_di > daily_plus_di else "Neutral")
            
            return f"- Daily ADX(14): {daily_adx:.1f} ({adx_cond}), +DI={daily_plus_di:.1f}, -DI={daily_minus_di:.1f} ({di_cond})\n"
        else:
            return "- Daily ADX/DI(14): N/A\n"
    
    def _format_ichimoku_section(self, long_term_data: dict, current_price: float) -> str:
        daily_conv = long_term_data.get('daily_ichimoku_conversion')
        daily_base = long_term_data.get('daily_ichimoku_base')
        daily_span_a = long_term_data.get('daily_ichimoku_span_a')
        daily_span_b = long_term_data.get('daily_ichimoku_span_b')
        
        if not all(v is not None for v in [daily_conv, daily_base, daily_span_a, daily_span_b]):
            return "- Daily Ichimoku Cloud: N/A (Requires 52+ days)\n"
        
        cloud_status = ("Bullish Cloud" if daily_span_a > daily_span_b else
                       "Bearish Cloud" if daily_span_b > daily_span_a else "Neutral")
        
        price_cloud = "N/A"
        if current_price:
            if current_price > max(daily_span_a, daily_span_b):
                price_cloud = "Above Cloud (Bullish)"
            elif current_price < min(daily_span_a, daily_span_b):
                price_cloud = "Below Cloud (Bearish)"
            else:
                price_cloud = "Inside Cloud (Neutral/Uncertain)"
        
        tk_cross = ("Bullish TK Cross" if daily_conv > daily_base else
                   "Bearish TK Cross" if daily_base > daily_conv else "Neutral")
        
        return (f"- Daily Ichimoku: Conv={daily_conv:.6f}, Base={daily_base:.6f}, "
                f"SpanA={daily_span_a:.6f}, SpanB={daily_span_b:.6f}\n"
                f"  * Cloud: {cloud_status}, Price: {price_cloud}, TK Cross: {tk_cross}\n")
    
    def _format_numeric_value(self, value, precision: int = 2) -> str:
        """Helper to safely format numeric values with fallback to 'N/A'"""
        if isinstance(value, (int, float)):
            return f"{value:.{precision}f}"
        return "N/A"
