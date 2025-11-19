# Technical Indicators System Documentation

**Parent Instructions**: See `/AGENTS.md` for global project context and universal coding guidelines.

**This document** contains indicator-specific implementation details that extend/override root instructions.

---

## Overview

The indicators layer provides 50+ technical indicators organized by category (momentum, trend, volatility, volume, overlap, statistical, support/resistance). All indicators are implemented using high-performance numba-compiled functions for vectorized numpy operations, ensuring fast calculation across large datasets.

## Architecture

### Core Design Principles

- **Performance-first**: All indicators use `@njit(cache=True)` for numba compilation
- **Vectorized operations**: Leverage numpy for array operations
- **Zero caching**: Always calculate fresh to avoid stale data
- **Modular categories**: Indicators grouped by function (momentum, trend, etc.)
- **Type safety**: Strict numpy array handling

### Directory Structure

```
src/indicators/
├── AGENTS.md (this file)
├── constants.py                   # Shared constants
├── base/
│   ├── indicator_base.py          # Base class for all indicators
│   ├── indicator_categories.py    # Category wrapper classes
│   └── technical_indicators.py    # Main orchestrator class
└── indicators/
    ├── momentum/                   # RSI, MACD, Stochastic, Williams %R, etc.
    ├── trend/                      # ADX, Supertrend, Ichimoku, SAR
    ├── volatility/                 # ATR, Bollinger Bands, Keltner, Donchian
    ├── volume/                     # VWAP, OBV, MFI, CMF, Force Index
    ├── overlap/                    # SMA, EMA, VWAP, TWAP
    ├── statistical/                # Z-Score, Kurtosis, Skew, Entropy, Hurst
    ├── support_resistance/         # S/R levels, Fibonacci, Pivots
    ├── price/                      # Price transformations
    └── sentiment/                  # Sentiment-related indicators
```

## Base System

### TechnicalIndicators

**Location**: `src/indicators/base/technical_indicators.py`

**Purpose**: Main orchestrator class providing unified API for all indicator categories.

**Category Properties**:
```python
self.overlap             # SMA, EMA, WMA, HMA, VWAP, TWAP
self.momentum            # RSI, MACD, Stochastic, Williams %R, TSI, RMI, UO
self.price               # Price transforms (Heikin Ashi, etc.)
self.sentiment           # Sentiment indicators
self.statistical         # Z-Score, Kurtosis, Skew, Entropy, Hurst, Variance
self.support_resistance  # S/R levels, Fibonacci, Pivots
self.trend               # ADX, Supertrend, Ichimoku, SAR, Vortex, PFE
self.volatility          # ATR, Bollinger Bands, Keltner, Donchian, VHF
self.vol                 # VWAP, OBV, MFI, CMF, Force Index, CCI
```

**Usage Pattern**:
```python
ti = TechnicalIndicators()
ti.get_data(ohlcv_array)  # Set OHLCV data

# Calculate indicators
rsi = ti.momentum.rsi(length=14)
macd, signal, hist = ti.momentum.macd()
bb_upper, bb_mid, bb_lower = ti.volatility.bollinger_bands(length=20)
```

**Data Format**:
- Accepts: `pd.DataFrame`, `np.ndarray`, or `List[List[float]]`
- Expected columns: `[timestamp, open, high, low, close, volume]`
- Automatically extracts OHLCV arrays from input

### IndicatorBase

**Location**: `src/indicators/base/indicator_base.py`

**Purpose**: Base class handling data ingestion, validation, and common utilities.

**Responsibilities**:
- Parse input data formats (DataFrame, array, list)
- Extract OHLCV arrays
- Provide data properties (`open`, `high`, `low`, `close`, `volume`)
- Optional timing and CSV export for debugging

**Properties**:
```python
@property
def open(self) -> np.ndarray
def high(self) -> np.ndarray
def low(self) -> np.ndarray
def close(self) -> np.ndarray
def volume(self) -> np.ndarray
```

## Indicator Categories

### Momentum Indicators

**Location**: `src/indicators/indicators/momentum/momentum_indicators.py`

**Purpose**: Measure speed and magnitude of price movements.

#### RSI (Relative Strength Index)

**Function**: `rsi_numba(close, length=14)`

**Purpose**: Identifies overbought (>70) and oversold (<30) conditions.

**Algorithm**:
1. Calculate price changes (gains and losses)
2. Smooth with exponential average
3. Compute RS (Average Gain / Average Loss)
4. RSI = 100 - (100 / (1 + RS))

**Output**: Array of RSI values (0-100)

**Interpretation**:
- RSI > 70: Overbought (potential reversal down)
- RSI < 30: Oversold (potential reversal up)
- 50: Neutral momentum

#### MACD (Moving Average Convergence Divergence)

**Function**: `macd_numba(close, fast_length=12, slow_length=26, signal_length=9)`

**Purpose**: Trend-following momentum indicator showing relationship between two moving averages.

**Algorithm**:
1. Fast EMA (12-period default)
2. Slow EMA (26-period default)
3. MACD Line = Fast EMA - Slow EMA
4. Signal Line = EMA of MACD Line (9-period default)
5. Histogram = MACD Line - Signal Line

**Output**: Tuple of (macd_line, signal_line, histogram)

**Interpretation**:
- MACD > Signal: Bullish momentum
- MACD < Signal: Bearish momentum
- Histogram crossing zero: Trend change
- Divergence from price: Potential reversal

#### Stochastic Oscillator

**Function**: `stochastic_numba(high, low, close, period_k=14, smooth_k=3, period_d=3)`

**Purpose**: Compares closing price to price range over a period.

**Algorithm**:
1. %K = 100 * (Close - Lowest Low) / (Highest High - Lowest Low)
2. Smooth %K over smooth_k periods
3. %D = SMA of %K over period_d periods

**Output**: Tuple of (%K, %D)

**Interpretation**:
- %K > 80: Overbought
- %K < 20: Oversold
- %K crosses above %D: Bullish signal
- %K crosses below %D: Bearish signal

#### Williams %R

**Function**: `williams_r_numba(high, low, close, length=14)`

**Purpose**: Momentum oscillator measuring overbought/oversold levels (inverted scale).

**Algorithm**:
- %R = ((Highest High - Close) / (Highest High - Lowest Low)) * -100

**Output**: Array of Williams %R values (-100 to 0)

**Interpretation**:
- %R > -20: Overbought
- %R < -80: Oversold
- -50: Neutral

#### Ultimate Oscillator (UO)

**Function**: `uo_numba(high, low, close, fast=7, medium=14, slow=28, fast_w=4.0, medium_w=2.0, slow_w=1.0)`

**Purpose**: Multi-timeframe momentum oscillator reducing false signals.

**Algorithm**:
1. Calculate buying pressure (BP) and true range (TR)
2. Compute averages for 3 timeframes (7, 14, 28)
3. Weight and combine: UO = 100 * (weighted sum of BP/TR ratios)

**Output**: Array of UO values (0-100)

**Interpretation**:
- UO > 70: Overbought
- UO < 30: Oversold
- Divergence from price: Strong reversal signal

#### TSI (True Strength Index)

**Function**: `tsi_numba(close, long_length=25, short_length=13)`

**Purpose**: Double-smoothed momentum indicator showing trend strength and direction.

**Algorithm**:
1. Calculate price momentum (close[i] - close[i-1])
2. Double smooth momentum with EMAs (long, then short)
3. Double smooth absolute momentum
4. TSI = (Double Smoothed Momentum / Double Smoothed Abs Momentum) * 100

**Output**: Array of TSI values (-100 to +100)

#### RMI (Relative Momentum Index)

**Function**: `rmi_numba(close, length=20, momentum_length=5)`

**Purpose**: RSI variant using momentum instead of price changes.

**Algorithm**:
1. Calculate momentum over momentum_length periods
2. Apply RSI logic to momentum values

**Output**: Array of RMI values (0-100)

**Interpretation**: Similar to RSI but more sensitive to momentum shifts

### Trend Indicators

**Location**: `src/indicators/indicators/trend/trend_indicators.py`

**Purpose**: Identify and measure market trends.

#### ADX (Average Directional Index)

**Function**: `adx_numba(high, low, close, length=14)`

**Purpose**: Measures trend strength (not direction).

**Algorithm**:
1. Calculate True Range (TR)
2. Calculate Directional Movement (DM+ and DM-)
3. Smooth TR and DM with RMA
4. Calculate DI+ and DI- (directional indicators)
5. Calculate DX = 100 * |DI+ - DI-| / (DI+ + DI-)
6. ADX = RMA of DX

**Output**: Tuple of (ADX, DI+, DI-)

**Interpretation**:
- ADX > 25: Strong trend
- ADX > 50: Very strong trend
- ADX < 20: Weak/no trend
- DI+ > DI-: Uptrend
- DI- > DI+: Downtrend

#### Supertrend

**Function**: `supertrend_numba(high, low, close, length=10, multiplier=3.0)`

**Purpose**: Trend-following indicator using ATR-based bands.

**Algorithm**:
1. Calculate ATR
2. Basic Band = HL2 (High+Low)/2
3. Upper Band = HL2 + (multiplier * ATR)
4. Lower Band = HL2 - (multiplier * ATR)
5. Trend switches when price crosses bands

**Output**: Tuple of (supertrend, direction)
- direction = 1: Bullish (use lower band)
- direction = -1: Bearish (use upper band)

**Interpretation**:
- Price > Supertrend: Buy signal
- Price < Supertrend: Sell signal
- Fewer false signals than MA crossovers

#### Ichimoku Cloud

**Function**: `ichimoku_cloud_numba(high, low, conversion_length=9, base_length=26, lagging_span2_length=52, displacement=26)`

**Purpose**: Comprehensive trend system showing support, resistance, momentum, and trend direction.

**Components**:
1. **Tenkan-sen** (Conversion Line): (9-period high + low) / 2
2. **Kijun-sen** (Base Line): (26-period high + low) / 2
3. **Senkou Span A** (Leading Span A): (Conversion + Base) / 2, projected 26 periods ahead
4. **Senkou Span B** (Leading Span B): (52-period high + low) / 2, projected 26 periods ahead

**Output**: Tuple of (conversion, base, span_a, span_b)

**Interpretation**:
- Price above cloud: Bullish
- Price below cloud: Bearish
- Cloud thickness: Support/resistance strength
- Span A > Span B: Bullish cloud (green)
- Span B > Span A: Bearish cloud (red)

#### Parabolic SAR

**Function**: `parabolic_sar_numba(high, low, acceleration=0.02, max_acceleration=0.2)`

**Purpose**: Trailing stop and trend indicator.

**Algorithm**:
1. Initial trend from first price movement
2. SAR updates with acceleration factor
3. Switches trend when price crosses SAR

**Output**: Tuple of (sar, sar_long, sar_short, direction)

**Interpretation**:
- SAR below price: Bullish (use as stop-loss)
- SAR above price: Bearish (use as stop-loss)
- SAR switches: Trend reversal

#### Vortex Indicator

**Function**: `vortex_numba(high, low, close, length=14)`

**Purpose**: Identifies trend start and measures trend strength.

**Output**: Tuple of (vi_plus, vi_minus)

**Interpretation**:
- VI+ > VI-: Bullish trend
- VI- > VI+: Bearish trend
- Crossovers: Trend changes

### Volatility Indicators

**Location**: `src/indicators/indicators/volatility/volatility_indicators.py`

**Purpose**: Measure price variability and risk.

#### ATR (Average True Range)

**Function**: `atr_numba(high, low, close, length=14, mamode='rma', percent=False)`

**Purpose**: Measures market volatility (not direction).

**Algorithm**:
1. True Range = max(high - low, |high - prev_close|, |low - prev_close|)
2. ATR = Moving average of TR (RMA, EMA, SMA, or WMA)
3. Optional: Convert to percentage of price

**Output**: Array of ATR values

**Interpretation**:
- High ATR: High volatility (larger stops needed)
- Low ATR: Low volatility (tighter stops possible)
- ATR% > 2%: High volatility
- ATR% < 0.5%: Low volatility

#### Bollinger Bands

**Function**: `bollinger_bands_numba(close, length=20, num_std_dev=2)`

**Purpose**: Volatility bands based on standard deviation.

**Algorithm**:
1. Middle Band = SMA(close, length)
2. Standard Deviation = StdDev(close, length)
3. Upper Band = Middle + (num_std_dev * StdDev)
4. Lower Band = Middle - (num_std_dev * StdDev)

**Output**: Tuple of (upper, middle, lower)

**Interpretation**:
- Price near upper: Overbought
- Price near lower: Oversold
- Band squeeze: Low volatility (breakout coming)
- Band expansion: High volatility
- Price outside bands: Strong move (potential reversal)

**%B Indicator** (calculated separately):
- %B = (Price - Lower Band) / (Upper Band - Lower Band)
- %B > 1: Above upper band
- %B < 0: Below lower band
- %B = 0.5: At middle band

#### Keltner Channels

**Function**: `keltner_channels_numba(high, low, close, length=20, multiplier=2, mamode='ema')`

**Purpose**: Volatility bands based on ATR (trend-following).

**Algorithm**:
1. Middle = EMA(close, length)
2. ATR = ATR(high, low, close, length)
3. Upper = Middle + (multiplier * ATR)
4. Lower = Middle - (multiplier * ATR)

**Output**: Tuple of (upper, middle, lower)

**Interpretation**:
- Similar to Bollinger Bands
- More trend-focused (uses ATR not StdDev)
- Smoother than Bollinger Bands

#### Donchian Channels

**Function**: `donchian_channels_numba(high, low, length=20)`

**Purpose**: Shows highest high and lowest low over period.

**Algorithm**:
1. Upper = Highest High over length periods
2. Lower = Lowest Low over length periods
3. Middle = (Upper + Lower) / 2

**Output**: Tuple of (upper, middle, lower)

**Interpretation**:
- Breakout above upper: Strong bullish signal
- Breakout below lower: Strong bearish signal
- Used for trend following and breakout systems

#### VHF (Vertical Horizontal Filter)

**Function**: `vhf_numba(close, length=28, drift=1)`

**Purpose**: Determines if market is trending or ranging.

**Algorithm**:
- VHF = |Highest Close - Lowest Close| / Sum of |Close[i] - Close[i-1]|

**Output**: Array of VHF values

**Interpretation**:
- VHF > 0.4: Trending market (use trend indicators)
- VHF < 0.25: Ranging market (use oscillators)

### Volume Indicators

**Location**: `src/indicators/indicators/volume/volume_indicators.py`

**Purpose**: Analyze volume patterns and money flow.

#### VWAP (Volume Weighted Average Price)

**Function**: `rolling_vwap_numba(high, low, close, volume, length=20)`

**Purpose**: Average price weighted by volume.

**Algorithm**:
- VWAP = Sum(Price * Volume) / Sum(Volume)

**Output**: Array of VWAP values

**Interpretation**:
- Price > VWAP: Bullish (institutions buying)
- Price < VWAP: Bearish (institutions selling)
- Used by institutions for execution quality

#### OBV (On Balance Volume)

**Function**: `obv_numba(close, volume, length, initial=1)`

**Purpose**: Cumulative volume indicator showing buying/selling pressure.

**Algorithm**:
1. If close > prev_close: OBV += volume
2. If close < prev_close: OBV -= volume
3. If close = prev_close: OBV unchanged

**Output**: Array of OBV values

**Interpretation**:
- Rising OBV: Buying pressure
- Falling OBV: Selling pressure
- OBV divergence from price: Reversal warning

#### MFI (Money Flow Index)

**Function**: `mfi_numba(high, low, close, volume, length=14)`

**Purpose**: Volume-weighted RSI showing buying/selling pressure.

**Algorithm**:
1. Typical Price = (High + Low + Close) / 3
2. Raw Money Flow = Typical Price * Volume
3. Separate positive and negative money flows
4. Money Ratio = Positive MF / Negative MF
5. MFI = 100 - (100 / (1 + Money Ratio))

**Output**: Array of MFI values (0-100)

**Interpretation**:
- MFI > 80: Overbought
- MFI < 20: Oversold
- Divergence from price: Reversal signal

#### CMF (Chaikin Money Flow)

**Function**: `chaikin_money_flow_numba(high, low, close, volume, length=20)`

**Purpose**: Measures buying/selling pressure over a period.

**Algorithm**:
1. Money Flow Multiplier = ((Close - Low) - (High - Close)) / (High - Low)
2. Money Flow Volume = MF Multiplier * Volume
3. CMF = Sum(MF Volume) / Sum(Volume)

**Output**: Array of CMF values (-1 to +1)

**Interpretation**:
- CMF > 0: Buying pressure
- CMF < 0: Selling pressure
- CMF > 0.25: Strong buying
- CMF < -0.25: Strong selling

#### Force Index

**Function**: `force_index_numba(close, volume, length=20)`

**Purpose**: Measures force behind price movements using volume.

**Algorithm**:
- Force = (Close - Previous Close) * Volume
- Force Index = EMA(Force, length)

**Output**: Array of Force Index values

**Interpretation**:
- Positive Force: Bullish power
- Negative Force: Bearish power
- Magnitude shows strength

#### CCI (Commodity Channel Index)

**Function**: `cci_numba(high, low, close, length=14, c=0.015)`

**Purpose**: Measures deviation from statistical mean.

**Algorithm**:
1. Typical Price = (High + Low + Close) / 3
2. Mean Deviation = Average of |TP - SMA(TP)|
3. CCI = (TP - SMA(TP)) / (c * Mean Deviation)

**Output**: Array of CCI values

**Interpretation**:
- CCI > +100: Overbought
- CCI < -100: Oversold
- Used for divergence and trend detection

### Overlap Indicators

**Location**: `src/indicators/indicators/overlap/overlap_indicators.py`

**Purpose**: Moving averages and smoothing functions.

#### SMA (Simple Moving Average)

**Function**: `sma_numba(close, length=20)`

**Algorithm**: Average of last N periods

**Output**: Array of SMA values

#### EMA (Exponential Moving Average)

**Function**: `ema_numba(close, length=12)`

**Algorithm**: 
- EMA = (Close - Previous EMA) * Multiplier + Previous EMA
- Multiplier = 2 / (length + 1)

**Output**: Array of EMA values

**Note**: More responsive to recent prices than SMA

#### WMA (Weighted Moving Average)

**Function**: `wma_numba(close, length=20)`

**Algorithm**: Recent prices weighted more heavily

**Output**: Array of WMA values

#### HMA (Hull Moving Average)

**Function**: `hma_numba(close, length=20)`

**Algorithm**: 
- HMA = WMA(2*WMA(n/2) - WMA(n)), sqrt(n))

**Output**: Array of HMA values

**Note**: Faster and smoother than traditional MAs

#### TWAP (Time Weighted Average Price)

**Function**: `twap_numba(close, length=20)`

**Algorithm**: Simple average of closing prices over time

**Output**: Array of TWAP values

### Statistical Indicators

**Location**: `src/indicators/indicators/statistical/statistical_indicators.py`

**Purpose**: Statistical measures of price behavior.

#### Z-Score

**Function**: `zscore_numba(close, length=30, std=1.0)`

**Purpose**: Measures how many standard deviations price is from mean.

**Algorithm**:
- Z-Score = (Price - Mean) / Standard Deviation

**Output**: Array of Z-Score values

**Interpretation**:
- Z-Score > 2: Overbought (2 std devs above mean)
- Z-Score < -2: Oversold (2 std devs below mean)
- Mean reversion signal

#### Kurtosis

**Function**: `kurtosis_numba(arr, length=20)`

**Purpose**: Measures "tailedness" of price distribution.

**Algorithm**: Fourth standardized moment

**Output**: Array of kurtosis values

**Interpretation**:
- Kurtosis > 3: Fat tails (more extreme moves)
- Kurtosis < 3: Thin tails (normal distribution)
- High kurtosis: Expect volatility

#### Skewness

**Function**: `skew_numba(close, length=30)`

**Purpose**: Measures asymmetry of price distribution.

**Algorithm**: Third standardized moment

**Output**: Array of skew values

**Interpretation**:
- Skew > 0: Right tail (more upside moves)
- Skew < 0: Left tail (more downside moves)
- Skew = 0: Symmetric distribution

#### Hurst Exponent

**Function**: `hurst_numba(close, max_lag=20)`

**Purpose**: Measures long-term memory and trend persistence.

**Algorithm**: Rescaled range analysis

**Output**: Array of Hurst values

**Interpretation**:
- H > 0.5: Trending market (persistent)
- H < 0.5: Mean-reverting market (anti-persistent)
- H = 0.5: Random walk (efficient market)

#### Entropy

**Function**: `entropy_numba(close, length=10, base=2.0)`

**Purpose**: Measures randomness/predictability.

**Output**: Array of entropy values

**Interpretation**:
- High entropy: High randomness (unpredictable)
- Low entropy: Low randomness (more predictable)

#### Variance & Standard Deviation

**Function**: `variance_numba(close, length=30, ddof=1)` and `stdev_numba(close, length=30, ddof=1)`

**Purpose**: Measures price variability.

**Output**: Array of variance/stdev values

**Interpretation**: Higher values = higher volatility

### Support & Resistance Indicators

**Location**: `src/indicators/indicators/support_resistance/support_resistance_indicators.py`

**Purpose**: Identify key price levels.

#### Basic Support/Resistance

**Function**: `support_resistance_numba(low, high, length=20)`

**Algorithm**:
- Support = Lowest Low over period
- Resistance = Highest High over period

**Output**: Tuple of (support, resistance)

#### Advanced Support/Resistance

**Function**: `advanced_support_resistance_numba(high, low, close, volume, length=20, strength_threshold=1, persistence=1, volume_factor=1.5, price_factor=0.004)`

**Purpose**: Volume-confirmed support/resistance levels.

**Algorithm**:
1. Identify local extremes in price
2. Confirm with volume spikes (volume > avg * volume_factor)
3. Validate level persistence (hit multiple times)
4. Filter by strength threshold

**Output**: Tuple of (support_levels, resistance_levels) as arrays

**Note**: More sophisticated than basic S/R, filters noise

#### Fibonacci Retracement

**Function**: `fibonacci_retracement_numba(high, low, length=20)`

**Purpose**: Calculate Fibonacci retracement levels.

**Levels**: 
- 0% (swing low)
- 23.6%
- 38.2%
- 50%
- 61.8%
- 100% (swing high)

**Output**: 2D array (n_periods, n_levels)

**Interpretation**: Key retracement levels for pullbacks

#### Pivot Points

**Function**: `pivot_points_numba(high, low, close)`

**Purpose**: Calculate daily pivot levels.

**Levels**:
- Pivot Point (PP) = (High + Low + Close) / 3
- R1 = 2*PP - Low
- R2 = PP + (High - Low)
- R3 = High + 2*(PP - Low)
- R4 = R3 + (High - Low)
- S1 = 2*PP - High
- S2 = PP - (High - Low)
- S3 = Low - 2*(High - PP)
- S4 = S3 - (High - Low)

**Output**: Tuple of (PP, R1, R2, R3, R4, S1, S2, S3, S4)

**Interpretation**: Intraday support/resistance levels

## Integration with Analysis System

### TechnicalCalculator Usage

**Location**: `src/analyzer/calculations/technical_calculator.py`

```python
class TechnicalCalculator:
    def __init__(self, logger, format_utils):
        self.ti = TechnicalIndicators()
        
    def get_indicators(self, ohlcv_data):
        """Calculate all indicators - no caching"""
        self.ti.get_data(ohlcv_data)
        
        indicators = {
            "rsi": self.ti.momentum.rsi(length=14),
            "macd_line": self.ti.momentum.macd()[0],
            "macd_signal": self.ti.momentum.macd()[1],
            "macd_hist": self.ti.momentum.macd()[2],
            "stoch_k": self.ti.momentum.stochastic()[0],
            "stoch_d": self.ti.momentum.stochastic()[1],
            "adx": self.ti.trend.adx()[0],
            "plus_di": self.ti.trend.adx()[1],
            "minus_di": self.ti.trend.adx()[2],
            "bb_upper": self.ti.volatility.bollinger_bands()[0],
            "bb_middle": self.ti.volatility.bollinger_bands()[1],
            "bb_lower": self.ti.volatility.bollinger_bands()[2],
            "atr": self.ti.volatility.atr(length=20),
            "vwap": self.ti.vol.rolling_vwap(length=20),
            "mfi": self.ti.vol.mfi(length=14),
            # ... 40+ more indicators
        }
        
        return indicators
```

### Timeframe Adaptation

Indicators automatically adapt to timeframe through period scaling:

```python
# For 1h timeframe: RSI(14) = 14 hours
# For 4h timeframe: RSI(14) = 56 hours (same relative period)
# For 1d timeframe: RSI(14) = 14 days
```

This ensures indicators remain comparable across timeframes.

## Performance Considerations

### Numba Compilation

- First call to an indicator: Slower (compilation)
- Subsequent calls: Fast (compiled code cached)
- Use `@njit(cache=True)` to persist compilation

### Memory Efficiency

- Indicators work directly on numpy arrays
- No intermediate Python objects created
- Minimal memory allocations

### Calculation Speed

- Typical indicator: <1ms for 1000 data points
- Full suite of 50+ indicators: <50ms for 1000 data points
- Parallelization possible (indicators independent)

## Common Patterns

### Calculate Single Indicator

```python
ti = TechnicalIndicators()
ti.get_data(ohlcv_array)
rsi = ti.momentum.rsi(length=14)
latest_rsi = rsi[-1]
```

### Calculate Multiple Indicators

```python
ti = TechnicalIndicators()
ti.get_data(ohlcv_array)

# Momentum
rsi = ti.momentum.rsi()
macd, signal, hist = ti.momentum.macd()

# Trend
adx, di_plus, di_minus = ti.trend.adx()
supertrend, direction = ti.trend.supertrend()

# Volatility
bb_u, bb_m, bb_l = ti.volatility.bollinger_bands()
atr = ti.volatility.atr()
```

### Access Latest Values

```python
# All indicators return arrays
# Use indexing for latest values
latest_rsi = rsi[-1]
latest_macd = macd[-1]

# Check for NaN (insufficient data)
if not np.isnan(latest_rsi):
    # Use indicator value
    pass
```

### Handle Insufficient Data

```python
# Indicators need warm-up period
# RSI needs 14+ candles, MACD needs 26+
indicators = ti.momentum.rsi(length=14)

# Check if enough data
valid_indicators = indicators[~np.isnan(indicators)]
if len(valid_indicators) > 0:
    latest_value = valid_indicators[-1]
```

## Indicator Thresholds

**Defined in TechnicalCalculator**:

```python
INDICATOR_THRESHOLDS = {
    'rsi': {'oversold': 30, 'overbought': 70},
    'stoch_k': {'oversold': 20, 'overbought': 80},
    'stoch_d': {'oversold': 20, 'overbought': 80},
    'williams_r': {'oversold': -80, 'overbought': -20},
    'adx': {'weak': 25, 'strong': 50, 'very_strong': 75},
    'mfi': {'oversold': 20, 'overbought': 80},
    'bb_width': {'tight': 2, 'wide': 10}
}
```

These thresholds are used for:
- Pattern detection
- Signal generation
- Alert triggers
- Prompt formatting

## Error Handling

### NaN Handling

Indicators return `np.nan` for periods without sufficient data:

```python
rsi = ti.momentum.rsi(length=14)
# First 14 values will be NaN
# Only use rsi[14:] for valid values
```

### Division by Zero

All indicators handle division by zero:

```python
# Example from RSI
if avg_loss == 0:
    rsi[i] = 100  # Max value when no losses
else:
    rs = avg_gain / avg_loss
    rsi[i] = 100 - (100 / (1 + rs))
```

### Data Validation

```python
# Check for invalid input
if np.any(np.isnan(close)) or np.any(np.isinf(close)):
    # Return array of NaN
    return np.full(len(close), np.nan)
```

## Troubleshooting

**All indicators return NaN**:
- Insufficient data length
- Check OHLCV array has enough rows
- Verify data quality (no NaN in input)

**Indicators seem wrong**:
- Verify OHLCV column order: [timestamp, open, high, low, close, volume]
- Check timeframe matches data frequency
- Ensure data is sorted chronologically

**Performance issues**:
- First run slower (numba compilation)
- Subsequent runs fast (compiled code)
- Cache misses if indicator parameters change frequently

**Memory errors**:
- Large datasets (>100k candles) may need chunking
- Consider calculating only needed indicators
- Use data slicing for recent periods only

---

## Summary Documents Policy

**Do not create summary documents** in `.md` format or any format. All documentation should be maintained in the appropriate `AGENTS.md` file.
