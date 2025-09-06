from typing import Dict, Any, Optional
import numpy as np

from src.indicators.base.technical_indicators import TechnicalIndicators
from src.logger.logger import Logger


class TechnicalCalculator:
    """Core calculator for technical indicators with caching capability"""
    
    def __init__(self, logger: Optional[Logger] = None):
        """Initialize the technical indicator calculator"""
        self.logger = logger
        self.ti = TechnicalIndicators()
        
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
        
        # Add Fibonacci retracement levels
        fib_levels = self.ti.support_resistance.fibonacci_retracement(length=20)
        if fib_levels is not None and len(fib_levels) > 0:
            # fib_levels is a 2D array (n_periods, n_levels)
            # Extract each fibonacci level as a separate array
            indicators["fib_236"] = fib_levels[:, 1]  # 23.6% level for all periods
            indicators["fib_382"] = fib_levels[:, 2]  # 38.2% level for all periods
            indicators["fib_500"] = fib_levels[:, 3]  # 50% level for all periods
            indicators["fib_618"] = fib_levels[:, 4]  # 61.8% level for all periods
        
        # Add Pivot Points using the proper numba implementation
        pivot_point, r1, r2, s1, s2 = self.ti.support_resistance.pivot_points()
        indicators["pivot_point"] = pivot_point
        indicators["pivot_r1"] = r1
        indicators["pivot_r2"] = r2
        indicators["pivot_s1"] = s1
        indicators["pivot_s2"] = s2
        
        # Add Parabolic SAR
        sar_values = self.ti.trend.parabolic_sar()
        indicators["sar"] = sar_values
        
        # Add signal interpretations - temporarily disabled to fix scalar issue
        # self._add_signal_interpretations(indicators, ohlcv_data)
        
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

    def _add_signal_interpretations(self, indicators: dict, ohlcv_data: np.ndarray) -> None:
        """Add signal interpretations for various indicators.
        
        Args:
            indicators: Dictionary to add signal interpretations to
            ohlcv_data: OHLCV data array for current price
        """
        if ohlcv_data is None or len(ohlcv_data) == 0:
            return
            
        current_price = float(ohlcv_data[-1, 4])  # Close price
        
        # Ichimoku Signal
        if all(key in indicators for key in ['ichimoku_span_a', 'ichimoku_span_b']):
            span_a = indicators.get('ichimoku_span_a')
            span_b = indicators.get('ichimoku_span_b')
            
            if isinstance(span_a, (int, float)) and isinstance(span_b, (int, float)):
                cloud_top = max(span_a, span_b)
                cloud_bottom = min(span_a, span_b)
                
                if current_price > cloud_top:
                    indicators["ichimoku_signal"] = 1  # Bullish
                elif current_price < cloud_bottom:
                    indicators["ichimoku_signal"] = -1  # Bearish
                else:
                    indicators["ichimoku_signal"] = 0  # In cloud
            else:
                indicators["ichimoku_signal"] = 0
        else:
            indicators["ichimoku_signal"] = 0
            
        # Bollinger Bands Signal
        if all(key in indicators for key in ['bb_upper', 'bb_middle', 'bb_lower']):
            bb_upper = indicators.get('bb_upper')
            bb_middle = indicators.get('bb_middle')
            bb_lower = indicators.get('bb_lower')
            
            if all(isinstance(val, (int, float)) for val in [bb_upper, bb_middle, bb_lower]):
                # Calculate distance to each band as percentage
                upper_dist = abs(current_price - bb_upper) / bb_upper
                middle_dist = abs(current_price - bb_middle) / bb_middle
                lower_dist = abs(current_price - bb_lower) / bb_lower
                
                # Find closest band (threshold of 2% to determine "near")
                threshold = 0.02
                if upper_dist < threshold:
                    indicators["bb_signal"] = 1  # Near upper band
                elif lower_dist < threshold:
                    indicators["bb_signal"] = -1  # Near lower band
                else:
                    indicators["bb_signal"] = 0  # Near middle or between bands
            else:
                indicators["bb_signal"] = 0
        else:
            indicators["bb_signal"] = 0

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
