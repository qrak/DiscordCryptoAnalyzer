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
            "vwap": self.ti.vol.rolling_vwap(length=20),
            "twap": self.ti.vol.twap(length=20),
            "mfi": self.ti.vol.mfi(length=14),
            "obv": self.ti.vol.obv(length=20),
            "cmf": self.ti.vol.chaikin_money_flow(length=20),
            "force_index": self.ti.vol.force_index(length=20),
            "cci": self.ti.vol.cci(length=14),
            "rsi": self.ti.momentum.rsi(length=14),
            "stoch_k": self.ti.momentum.stochastic(period_k=14, smooth_k=3, period_d=3)[0],
            "stoch_d": self.ti.momentum.stochastic(period_k=14, smooth_k=3, period_d=3)[1],
            "williams_r": self.ti.momentum.williams_r(length=14),
            "uo": self.ti.momentum.uo(),  # Ultimate Oscillator uses fixed periods (7,14,28)
            "adx": self.ti.trend.adx(length=14)[0],
            "plus_di": self.ti.trend.adx(length=14)[1],
            "minus_di": self.ti.trend.adx(length=14)[2],
            "atr": self.ti.volatility.atr(length=20),
            "kurtosis": self.ti.statistical.kurtosis(length=20),
            "zscore": self.ti.statistical.zscore(length=20),
            "hurst": self.ti.statistical.hurst(max_lag=20),
        }
        
        # Calculate MACD separately to handle the tuple return
        macd_line, macd_signal, macd_hist = self.ti.momentum.macd(fast_length=12, slow_length=26, signal_length=9)
        indicators["macd_line"] = macd_line
        indicators["macd_signal"] = macd_signal
        indicators["macd_hist"] = macd_hist
        
        # Calculate Bollinger Bands separately
        bb_upper, bb_middle, bb_lower = self.ti.volatility.bollinger_bands(length=20, num_std_dev=2)
        indicators["bb_upper"] = bb_upper
        indicators["bb_middle"] = bb_middle
        indicators["bb_lower"] = bb_lower
        
        # Calculate BB %B (position within bands)
        current_price = ohlcv_data[-1, 3]  # Close price
        if bb_upper[-1] != bb_lower[-1]:  # Avoid division by zero
            bb_percent_b = (current_price - bb_lower[-1]) / (bb_upper[-1] - bb_lower[-1])
            indicators["bb_percent_b"] = bb_percent_b
        else:
            indicators["bb_percent_b"] = np.nan
        
        # Calculate Keltner Channels separately
        kc_upper, kc_middle, kc_lower = self.ti.volatility.keltner_channels(length=20, multiplier=2)
        indicators["kc_upper"] = kc_upper
        indicators["kc_middle"] = kc_middle
        indicators["kc_lower"] = kc_lower
        
        # Calculate Supertrend separately
        supertrend, supertrend_direction = self.ti.trend.supertrend(length=20, multiplier=3.0)
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
        
        # Calculate Donchian Channels using proper @njit implementation
        donchian_upper, donchian_middle, donchian_lower = self.ti.volatility.donchian_channels(length=20)
        indicators["donchian_upper"] = donchian_upper
        indicators["donchian_middle"] = donchian_middle  
        indicators["donchian_lower"] = donchian_lower
        
        # Calculate ATR Percentage
        current_price = ohlcv_data[-1, 4] if len(ohlcv_data) > 0 else 1  # Close price
        atr_values = indicators["atr"]
        indicators["atr_percent"] = (atr_values / current_price) * 100 if current_price > 0 else np.full_like(atr_values, np.nan)
        
        # Add support and resistance indicators
        support, resistance = self.ti.support_resistance.support_resistance(length=20)
        indicators["basic_support"] = support
        indicators["basic_resistance"] = resistance
        
        # Add advanced support and resistance with volume analysis
        adv_support, adv_resistance = self.ti.support_resistance.advanced_support_resistance(
            length=20,
            strength_threshold=1,
            persistence=1,
            volume_factor=1.5,
            price_factor=0.004
        )
        # Store as arrays instead of single values
        indicators["advanced_support"] = adv_support
        indicators["advanced_resistance"] = adv_resistance
        
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
        pivot_point, r1, r2, r3, r4, s1, s2, s3, s4 = self.ti.support_resistance.pivot_points()
        indicators["pivot_point"] = pivot_point
        indicators["pivot_r1"] = r1
        indicators["pivot_r2"] = r2
        indicators["pivot_r3"] = r3
        indicators["pivot_r4"] = r4
        indicators["pivot_s1"] = s1
        indicators["pivot_s2"] = s2
        indicators["pivot_s3"] = s3
        indicators["pivot_s4"] = s4
        
        # Add Parabolic SAR
        sar_values = self.ti.trend.parabolic_sar(step=0.02, max_step=0.2)
        indicators["sar"] = sar_values
        
        # Add signal interpretations
        self._add_signal_interpretations(indicators, ohlcv_data)
        
        # Add advanced trend indicators
        vortex_plus, vortex_minus = self.ti.trend.vortex_indicator(length=20)
        indicators["vortex_plus"] = vortex_plus
        indicators["vortex_minus"] = vortex_minus
        
        # Add more momentum indicators
        indicators["tsi"] = self.ti.momentum.tsi(long_length=20, short_length=10)
        indicators["rmi"] = self.ti.momentum.rmi(length=20, momentum_length=5)
        indicators["ppo"] = self.ti.momentum.ppo(fast_length=12, slow_length=26)
        indicators["coppock"] = self.ti.momentum.coppock_curve(wl1=11, wl2=14, wma_length=10)
        indicators["kst"] = self.ti.momentum.kst()  # KST uses fixed periods
        
        # Add more trend indicators
        indicators["trix"] = self.ti.trend.trix(length=20)
        indicators["pfe"] = self.ti.trend.pfe(n=20, m=5)
        indicators["td_sequential"] = self.ti.trend.td_sequential(length=9)  # TD Sequential uses fixed 9 periods
        
        # Calculate Chandelier Exit for trend reversals
        long_exit, short_exit = self.ti.volatility.chandelier_exit(length=20, multiplier=3.0)
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
        available_days = len(ohlcv_data)

        sma_values, volume_sma_values = self._compute_sma_sets(ti_lt, available_days)
        price_change_pct, volume_change_pct = self._compute_change_metrics(ti_lt, available_days)
        volatility = self._compute_volatility(ti_lt, available_days)

        daily_indicators = self._compute_daily_indicators(ti_lt, available_days)
        
        # Add macro trend analysis based on SMA relationships
        macro_trend_analysis = self._compute_macro_trend_analysis(ti_lt, available_days, sma_values)

        result = {
            'sma_values': sma_values,
            'volume_sma_values': volume_sma_values,
            'price_change': price_change_pct,
            'volume_change': volume_change_pct,
            'volatility': volatility,
            'available_days': available_days,
            'macro_trend': macro_trend_analysis,
            **daily_indicators
        }

        # Ensure we're not returning numpy types that might not be recognized properly
        result = {k: float(v) if isinstance(v, (np.floating, float)) and not np.isnan(v) else v
                  for k, v in result.items() if k not in ('sma_values', 'volume_sma_values')}

        # Store in cache
        self._cache[cache_key] = result
        return result

    # ---------------- Helper Methods (extracted for clarity) ----------------
    def _compute_sma_sets(self, ti: TechnicalIndicators, available_days: int):
        sma_periods = [20, 50, 100, 200]
        sma_values: Dict[int, float] = {}
        volume_sma_values: Dict[int, float] = {}
        for period in sma_periods:
            if available_days >= period:
                # Use technical indicators directly instead of extracted arrays
                sma = ti.overlap.sma(ti.close, period)
                vol_sma = ti.overlap.sma(ti.volume, period)
                if not np.isnan(sma[-1]):
                    sma_values[period] = float(sma[-1])
                if not np.isnan(vol_sma[-1]):
                    volume_sma_values[period] = float(vol_sma[-1])
        return sma_values, volume_sma_values

    def _compute_change_metrics(self, ti: TechnicalIndicators, available_days: int):
        price_change_pct = volume_change_pct = None
        if available_days >= 2:
            # Use technical indicators data directly
            price_change_pct = float((ti.close[-1] / ti.close[0] - 1) * 100)
            volume_change_pct = float((ti.volume[-1] / max(ti.volume[0], 1) - 1) * 100)
        return price_change_pct, volume_change_pct

    def _compute_volatility(self, ti: TechnicalIndicators, available_days: int):
        if available_days >= 7:
            # Use technical indicators data directly
            daily_returns = np.diff(ti.close) / ti.close[:-1]
            return float(np.std(daily_returns) * 100)
        return None
    
    def _compute_macro_trend_analysis(self, ti: TechnicalIndicators, available_days: int, sma_values: Dict[int, float]) -> Dict[str, Any]:
        """Analyze macro trend using SMA relationships and 365-day context."""
        analysis = {
            'trend_direction': 'Neutral',
            'sma_alignment': 'Mixed',
            'golden_cross': False,
            'death_cross': False,
            'price_above_200sma': False,
            'sma_50_vs_200': 'Neutral'
        }
        
        if available_days < 200:
            return analysis
            
        current_price = float(ti.close[-1])
        
        # Check price position relative to key SMAs
        if 200 in sma_values:
            analysis['price_above_200sma'] = current_price > sma_values[200]
            
        # Analyze SMA 50 vs SMA 200 relationship (Golden/Death Cross context)
        if 50 in sma_values and 200 in sma_values:
            sma_50 = sma_values[50]
            sma_200 = sma_values[200]
            
            if sma_50 > sma_200:
                analysis['sma_50_vs_200'] = 'Bullish'
                # Check if this could be a golden cross scenario
                if available_days >= 250:  # Need enough data to check trend
                    sma_50_prev = ti.overlap.sma(ti.close, 50)[-10]  # 10 periods ago
                    sma_200_prev = ti.overlap.sma(ti.close, 200)[-10]
                    if sma_50_prev <= sma_200_prev and sma_50 > sma_200:
                        analysis['golden_cross'] = True
            elif sma_50 < sma_200:
                analysis['sma_50_vs_200'] = 'Bearish'
                # Check if this could be a death cross scenario
                if available_days >= 250:
                    sma_50_prev = ti.overlap.sma(ti.close, 50)[-10]
                    sma_200_prev = ti.overlap.sma(ti.close, 200)[-10]
                    if sma_50_prev >= sma_200_prev and sma_50 < sma_200:
                        analysis['death_cross'] = True
        
        # Determine overall SMA alignment
        if 20 in sma_values and 50 in sma_values and 100 in sma_values and 200 in sma_values:
            smas = [sma_values[20], sma_values[50], sma_values[100], sma_values[200]]
            if all(smas[i] >= smas[i+1] for i in range(len(smas)-1)):
                analysis['sma_alignment'] = 'Bullish (Ascending)'
            elif all(smas[i] <= smas[i+1] for i in range(len(smas)-1)):
                analysis['sma_alignment'] = 'Bearish (Descending)'
            else:
                analysis['sma_alignment'] = 'Mixed'
        
        # Determine overall trend direction
        bullish_signals = sum([
            analysis['price_above_200sma'],
            analysis['sma_50_vs_200'] == 'Bullish',
            analysis['golden_cross'],
            analysis['sma_alignment'] == 'Bullish (Ascending)'
        ])
        
        bearish_signals = sum([
            not analysis['price_above_200sma'],
            analysis['sma_50_vs_200'] == 'Bearish', 
            analysis['death_cross'],
            analysis['sma_alignment'] == 'Bearish (Descending)'
        ])
        
        if bullish_signals >= 3:
            analysis['trend_direction'] = 'Bullish'
        elif bearish_signals >= 3:
            analysis['trend_direction'] = 'Bearish'
        else:
            analysis['trend_direction'] = 'Neutral'
            
        return analysis

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
            
            # Handle numpy arrays by taking the last value
            if hasattr(span_a, '__iter__') and not isinstance(span_a, str):
                span_a = span_a[-1] if len(span_a) > 0 else None
            if hasattr(span_b, '__iter__') and not isinstance(span_b, str):
                span_b = span_b[-1] if len(span_b) > 0 else None
            
            if isinstance(span_a, (int, float)) and isinstance(span_b, (int, float)) and not (np.isnan(span_a) or np.isnan(span_b)):
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
            
            # Handle numpy arrays by taking the last value
            if hasattr(bb_upper, '__iter__') and not isinstance(bb_upper, str):
                bb_upper = bb_upper[-1] if len(bb_upper) > 0 else None
            if hasattr(bb_middle, '__iter__') and not isinstance(bb_middle, str):
                bb_middle = bb_middle[-1] if len(bb_middle) > 0 else None
            if hasattr(bb_lower, '__iter__') and not isinstance(bb_lower, str):
                bb_lower = bb_lower[-1] if len(bb_lower) > 0 else None
            
            if all(isinstance(val, (int, float)) and not np.isnan(val) for val in [bb_upper, bb_middle, bb_lower]):
                # Calculate distance to each band as percentage
                upper_dist = abs(current_price - bb_upper) / bb_upper
                _middle_dist = abs(current_price - bb_middle) / bb_middle
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
