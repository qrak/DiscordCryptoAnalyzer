# Indicator Patterns Documentation

This document lists all available indicator patterns detected by the DiscordCryptoAnalyzer system.

## Overview

The indicator pattern detection system uses pure NumPy/Numba implementations for high-performance pattern recognition across various technical indicators. These patterns complement chart patterns by providing momentum, overbought/oversold, and divergence signals.

## Pattern Categories

### RSI Patterns

**detect_rsi_oversold_numba**
- **Purpose**: Detects oversold conditions in RSI
- **Signal**: RSI < threshold (default 30)
- **Use**: Potential bullish reversal signal

**detect_rsi_overbought_numba**
- **Purpose**: Detects overbought conditions in RSI
- **Signal**: RSI > threshold (default 70)
- **Use**: Potential bearish reversal signal

**detect_rsi_w_bottom_numba**
- **Purpose**: Detects W-Bottom pattern in RSI (bullish reversal confirmation)
- **Signal**: Double bottom in RSI where second bottom is higher than first, price makes equal or lower low
- **Use**: Strong bullish reversal confirmation

**detect_rsi_m_top_numba**
- **Purpose**: Detects M-Top pattern in RSI (bearish reversal confirmation)
- **Signal**: Double top in RSI where second top is lower than first, price makes equal or higher high
- **Use**: Strong bearish reversal confirmation

### MACD Patterns

**detect_macd_crossover_numba**
- **Purpose**: Detects MACD line crossing signal line
- **Signal**: MACD crosses above/below signal line
- **Use**: Momentum shift indication

**detect_macd_zero_cross_numba**
- **Purpose**: Detects MACD line crossing zero line
- **Signal**: MACD crosses above/below zero
- **Use**: Major momentum shift (bullish/bearish)

**get_macd_histogram_trend_numba**
- **Purpose**: Gets MACD histogram trend direction
- **Signal**: Increasing/decreasing histogram bars
- **Use**: Momentum acceleration/deceleration

### Divergence Patterns

**detect_bullish_divergence_numba**
- **Purpose**: Detects bullish divergence between price and indicator
- **Signal**: Price makes lower low, indicator makes higher low
- **Use**: Suggests weakening bearish momentum, potential reversal up

**detect_bearish_divergence_numba**
- **Purpose**: Detects bearish divergence between price and indicator
- **Signal**: Price makes higher high, indicator makes lower high
- **Use**: Suggests weakening bullish momentum, potential reversal down

### Volatility Patterns

**detect_atr_spike_numba**
- **Purpose**: Detects sudden ATR spikes (volatility explosion)
- **Signal**: Current ATR significantly higher than recent average
- **Use**: Risk warning, often at trend reversals or breakouts

**detect_bb_squeeze_numba**
- **Purpose**: Detects Bollinger Band squeeze (low volatility)
- **Signal**: Band width in lowest percentile over lookback period
- **Use**: Indicates consolidation, potential for big move (breakout/breakdown)

**detect_volatility_trend_numba**
- **Purpose**: Detects trend in volatility
- **Signal**: Increasing, decreasing, or stable volatility
- **Use**: Volatility regime identification

**detect_keltner_squeeze_numba**
- **Purpose**: Detects TTM Squeeze (Bollinger Bands inside Keltner Channels)
- **Signal**: BB completely inside KC (extreme low volatility)
- **Use**: Breakout imminent when squeeze releases

### Moving Average Crossover Patterns

**detect_golden_cross_numba**
- **Purpose**: Detects Golden Cross
- **Signal**: 50 SMA crosses above 200 SMA
- **Use**: Strong bullish signal indicating potential long-term uptrend

**detect_death_cross_numba**
- **Purpose**: Detects Death Cross
- **Signal**: 50 SMA crosses below 200 SMA
- **Use**: Strong bearish signal indicating potential long-term downtrend

**detect_short_term_crossover_numba**
- **Purpose**: Detects short-term MA crossover
- **Signal**: 20 SMA crosses 50 SMA
- **Use**: Medium-term trend signal for swing trading

**check_ma_alignment_numba**
- **Purpose**: Checks alignment of moving averages for trend confirmation
- **Signal**: Bullish (20 > 50 > 200) or Bearish (20 < 50 < 200) alignment
- **Use**: Trend confirmation and strength assessment

### Stochastic Patterns

**detect_stoch_oversold_numba**
- **Purpose**: Detects oversold Stochastic condition
- **Signal**: Stochastic %K < threshold (default 20)
- **Use**: Potential bullish reversal

**detect_stoch_overbought_numba**
- **Purpose**: Detects overbought Stochastic condition
- **Signal**: Stochastic %K > threshold (default 80)
- **Use**: Potential bearish reversal

**detect_stoch_bullish_crossover_numba**
- **Purpose**: Detects bullish Stochastic crossover
- **Signal**: %K crosses above %D while in oversold territory
- **Use**: Strong bullish signal when occurring below 30

**detect_stoch_bearish_crossover_numba**
- **Purpose**: Detects bearish Stochastic crossover
- **Signal**: %K crosses below %D while in overbought territory
- **Use**: Strong bearish signal when occurring above 70

**detect_stoch_divergence_numba**
- **Purpose**: Detects divergence between Stochastic and price
- **Signal**: Price lower low + Stochastic higher low (bullish) or Price higher high + Stochastic lower high (bearish)
- **Use**: Momentum divergence identification

### Volume Patterns

**detect_volume_spike_numba**
- **Purpose**: Detects volume spike
- **Signal**: Current volume > multiplier × average volume
- **Use**: Strong confirmation for breakouts

**detect_volume_dryup_numba**
- **Purpose**: Detects volume dry-up
- **Signal**: Current volume < threshold × average volume
- **Use**: Often precedes major moves, indicates consolidation

**detect_volume_price_divergence_numba**
- **Purpose**: Detects divergence between volume and price movement
- **Signal**: Price rising but volume declining (bearish) or Price falling but volume declining (bullish)
- **Use**: Identifies weak rallies or selloffs

**detect_accumulation_distribution_numba**
- **Purpose**: Detects accumulation (buying pressure) or distribution (selling pressure)
- **Signal**: Volume increases on up days (accumulation) or down days (distribution)
- **Use**: Institutional activity identification

**detect_climax_volume_numba**
- **Purpose**: Detects climax volume (extreme volume spike)
- **Signal**: Volume > multiplier × average (default 3.0×)
- **Use**: Indicates potential exhaustion, often marks reversals

## Technical Implementation

- **Performance**: All patterns use @njit compilation for maximum speed
- **Data Format**: Functions expect NumPy arrays with most recent data last
- **Return Values**: Tuples containing detection results, timing, and relevant values
- **Integration**: Patterns are orchestrated by `IndicatorPatternEngine` class

## Usage in Analysis

These patterns are automatically detected and incorporated into the comprehensive technical analysis reports generated by the DiscordCryptoAnalyzer system. They provide additional confirmation signals and help identify high-probability trading setups.