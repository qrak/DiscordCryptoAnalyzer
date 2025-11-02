"""
Test script that replicates the EXACT analysis scenario from the log.

Analysis Time: 2025-11-02 21:34:25
Current Candle: 20:00:00 (34/60 minutes = 56.7% complete)
Note: "Technical indicators calculated using only completed candles"

This means at 21:34:25:
- The 20:00:00 candle was INCOMPLETE (still forming)
- Last COMPLETE candle was 19:00:00
- Indicators should use data up to 19:00:00

The patterns reported:
- "MACD histogram decreasing (momentum shift) now at 2025-11-02 20:00:00"
- "TTM Squeeze detected (extreme low volatility) now at 2025-11-02 20:00:00"
- "Stochastic bullish crossover 2 periods ago at 2025-11-02 18:00:00"
- "Volume dry-up: 0.41x average at 2025-11-02 20:00:00"

HYPOTHESIS: The "now at 2025-11-02 20:00:00" timestamp refers to the REFERENCE POINT
for the pattern detection (current incomplete candle time), but calculations use
ONLY COMPLETED CANDLES (up to 19:00:00).
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import ccxt

# Import indicator implementations
from src.indicators.indicators.momentum.momentum_indicators import (
    macd_numba,
    stochastic_numba
)
from src.indicators.indicators.volatility.volatility_indicators import (
    bollinger_bands_numba,
    keltner_channels_numba
)
from src.analyzer.pattern_engine.indicator_patterns.stochastic_patterns import (
    detect_stoch_bullish_crossover_numba
)
from src.analyzer.pattern_engine.indicator_patterns.volatility_patterns import (
    detect_keltner_squeeze_numba
)
from src.analyzer.pattern_engine.indicator_patterns.macd_patterns import (
    get_macd_histogram_trend_numba
)


def fetch_data_until_time(symbol='BTC/USDT', timeframe='1h', until_timestamp='2025-11-02 19:00:00', limit=200):
    """
    Fetch OHLCV data up to a specific timestamp (simulating completed candles only).
    
    Args:
        symbol: Trading pair
        timeframe: Candle timeframe
        until_timestamp: Last completed candle timestamp (exclusive of incomplete candles)
        limit: Number of candles
        
    Returns:
        DataFrame with completed candles only
    """
    print(f"\n{'='*80}")
    print(f"FETCHING DATA: {symbol} @ {timeframe}")
    print(f"SIMULATING ANALYSIS AT: 2025-11-02 21:34:25")
    print(f"LAST COMPLETED CANDLE: {until_timestamp}")
    print(f"{'='*80}")
    
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'spot'}
    })
    
    # Fetch more data than needed to ensure we get enough
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit + 10)
    
    # Convert to DataFrame
    df = pd.DataFrame(
        ohlcv,
        columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
    )
    
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    
    # Filter to only include candles up to and including the "until" timestamp
    until_ts = pd.Timestamp(until_timestamp, tz='UTC')
    df = df[df['datetime'] <= until_ts].copy()
    
    # Trim to last 'limit' candles
    if len(df) > limit:
        df = df.tail(limit).reset_index(drop=True)
    
    print(f"\nUsing {len(df)} completed candles")
    print(f"Date range: {df['datetime'].iloc[0]} to {df['datetime'].iloc[-1]}")
    print(f"\nLast 5 completed candles:")
    print(df[['datetime', 'open', 'high', 'low', 'close', 'volume']].tail())
    
    return df


def test_stochastic_crossover(df):
    """Test Stochastic crossover detection"""
    print(f"\n{'='*80}")
    print("STOCHASTIC BULLISH CROSSOVER TEST")
    print(f"{'='*80}")
    print("Expected: '2 periods ago at 2025-11-02 18:00:00'")
    print("Reference point: 2025-11-02 20:00:00 (incomplete)")
    print("Calculation uses: completed candles up to 19:00:00")
    
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    
    stoch_k, stoch_d = stochastic_numba(high, low, close, 14, 3, 3)
    df['stoch_k'] = stoch_k
    df['stoch_d'] = stoch_d
    
    # Detect crossover
    found, periods_ago, k_val, d_val, in_oversold = detect_stoch_bullish_crossover_numba(
        stoch_k, stoch_d, oversold_threshold=30.0
    )
    
    print(f"\nLast 8 Stochastic values:")
    print(df[['datetime', 'stoch_k', 'stoch_d']].tail(8).to_string(index=False))
    
    if found:
        crossover_idx = len(df) - periods_ago - 1
        crossover_time = df.iloc[crossover_idx]['datetime']
        
        print(f"\n✓ CROSSOVER DETECTED")
        print(f"  Periods ago: {periods_ago}")
        print(f"  Timestamp: {crossover_time}")
        print(f"  Stoch K: {k_val:.2f}")
        print(f"  Stoch D: {d_val:.2f}")
        print(f"  In Oversold: {'YES' if in_oversold else 'NO'}")
        
        # Check if this matches expected
        expected_time = pd.Timestamp('2025-11-02 18:00:00', tz='UTC')
        if crossover_time == expected_time:
            print(f"\n  ✅ MATCHES EXPECTED: crossover at 18:00:00")
        else:
            print(f"\n  ⚠️  MISMATCH: Expected {expected_time}, got {crossover_time}")
    else:
        print(f"\n✗ NO CROSSOVER DETECTED")
    
    return found


def test_macd_histogram_trend(df):
    """Test MACD histogram trend detection"""
    print(f"\n{'='*80}")
    print("MACD HISTOGRAM DECREASING TEST")
    print(f"{'='*80}")
    print("Expected: 'MACD histogram decreasing (momentum shift)'")
    print("Uses last 3 completed histogram values")
    
    close = df['close'].values
    macd_line, signal_line, histogram = macd_numba(close, 12, 26, 9)
    df['macd_hist'] = histogram
    
    # Get trend
    trend = get_macd_histogram_trend_numba(histogram, lookback=3)
    
    print(f"\nLast 8 MACD histogram values:")
    print(df[['datetime', 'macd_hist']].tail(8).to_string(index=False))
    
    print(f"\nHistogram trend analysis (last 4 values):")
    last_4 = histogram[-4:]
    for i in range(1, 4):
        change = last_4[i] - last_4[i-1]
        direction = "📉 decreasing" if change < 0 else "📈 increasing"
        print(f"  Period {i}: {last_4[i-1]:.6f} → {last_4[i]:.6f} ({direction})")
    
    print(f"\nTrend result: {trend}")
    print(f"  -1 = decreasing (bearish)")
    print(f"   0 = neutral/mixed")
    print(f"   1 = increasing (bullish)")
    
    if trend == -1:
        print(f"\n✓ HISTOGRAM DECREASING DETECTED")
        print(f"  ✅ MATCHES EXPECTED")
    elif trend == 1:
        print(f"\n✗ HISTOGRAM INCREASING (opposite of expected)")
    else:
        print(f"\n✗ HISTOGRAM NEUTRAL/MIXED (not consistently decreasing)")
    
    return trend == -1


def test_ttm_squeeze(df):
    """Test TTM Squeeze detection"""
    print(f"\n{'='*80}")
    print("TTM SQUEEZE DETECTION TEST")
    print(f"{'='*80}")
    print("Expected: 'TTM Squeeze detected (extreme low volatility)'")
    print("Condition: Bollinger Bands INSIDE Keltner Channels")
    
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    
    # Calculate bands
    bb_upper, bb_mid, bb_lower = bollinger_bands_numba(close, 20, 2.0)
    kc_upper, kc_mid, kc_lower = keltner_channels_numba(high, low, close, 20, 1.5, 'ema')
    
    df['bb_upper'] = bb_upper
    df['bb_lower'] = bb_lower
    df['kc_upper'] = kc_upper
    df['kc_lower'] = kc_lower
    
    # Detect squeeze at last candle
    squeeze = detect_keltner_squeeze_numba(kc_upper, kc_lower, bb_upper, bb_lower)
    
    print(f"\nLast 5 band values:")
    print(df[['datetime', 'bb_upper', 'kc_upper', 'close', 'kc_lower', 'bb_lower']].tail(5).to_string(index=False))
    
    # Check last value
    last_idx = len(df) - 1
    bb_u = bb_upper[last_idx]
    bb_l = bb_lower[last_idx]
    kc_u = kc_upper[last_idx]
    kc_l = kc_lower[last_idx]
    
    print(f"\nLast candle ({df.iloc[last_idx]['datetime']}):")
    print(f"  BB Upper: {bb_u:.2f}  |  KC Upper: {kc_u:.2f}")
    print(f"  Close:    {close[last_idx]:.2f}")
    print(f"  BB Lower: {bb_l:.2f}  |  KC Lower: {kc_l:.2f}")
    
    print(f"\nSqueeze conditions:")
    print(f"  BB_upper <= KC_upper: {bb_u:.2f} <= {kc_u:.2f} = {bb_u <= kc_u}")
    print(f"  BB_lower >= KC_lower: {bb_l:.2f} >= {kc_l:.2f} = {bb_l >= kc_l}")
    
    if squeeze:
        print(f"\n✓ TTM SQUEEZE DETECTED")
        print(f"  ✅ MATCHES EXPECTED")
    else:
        print(f"\n✗ NO TTM SQUEEZE")
    
    return squeeze


def test_volume_dryup(df, lookback=20):
    """Test volume dry-up detection"""
    print(f"\n{'='*80}")
    print("VOLUME DRY-UP TEST")
    print(f"{'='*80}")
    print(f"Expected: 'Volume dry-up: 0.41x average'")
    print(f"Lookback: {lookback} periods")
    
    volume = df['volume'].values
    
    # Calculate average volume (excluding last candle)
    avg_volume = np.mean(volume[-(lookback+1):-1])
    current_volume = volume[-1]
    volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
    
    print(f"\nLast candle: {df.iloc[-1]['datetime']}")
    print(f"Current volume: {current_volume:.2f}")
    print(f"Average volume ({lookback} candles): {avg_volume:.2f}")
    print(f"Ratio: {volume_ratio:.4f}x ({volume_ratio:.2%} of average)")
    
    print(f"\nLast 8 volume values:")
    last_8 = df[['datetime', 'volume']].tail(8).copy()
    last_8['vs_avg'] = last_8['volume'] / avg_volume
    print(last_8.to_string(index=False))
    
    is_dryup = volume_ratio < 0.5
    
    if is_dryup:
        print(f"\n✓ VOLUME DRY-UP DETECTED")
        print(f"  Ratio: {volume_ratio:.2f}x")
        
        # Check if close to 0.41
        if 0.38 <= volume_ratio <= 0.44:
            print(f"  ✅ CLOSE TO EXPECTED 0.41x")
        else:
            print(f"  ⚠️  Different from expected 0.41x")
    else:
        print(f"\n✗ NO VOLUME DRY-UP")
    
    return is_dryup, volume_ratio


def main():
    print("\n" + "="*80)
    print("EXACT SCENARIO REPLICATION TEST")
    print("Simulating analysis at 2025-11-02 21:34:25")
    print("Using only completed candles (up to 19:00:00)")
    print("="*80)
    
    # Fetch data up to last completed candle
    df = fetch_data_until_time(
        symbol='BTC/USDT',
        timeframe='1h',
        until_timestamp='2025-11-02 19:00:00',
        limit=200
    )
    
    # Run all tests
    stoch_result = test_stochastic_crossover(df)
    macd_result = test_macd_histogram_trend(df)
    ttm_result = test_ttm_squeeze(df)
    volume_result, volume_ratio = test_volume_dryup(df, lookback=20)
    
    # Summary
    print(f"\n{'='*80}")
    print("TEST RESULTS SUMMARY")
    print(f"{'='*80}")
    print(f"\n1. Stochastic Bullish Crossover: {'✅ PASS' if stoch_result else '❌ FAIL'}")
    print(f"2. MACD Histogram Decreasing: {'✅ PASS' if macd_result else '❌ FAIL'}")
    print(f"3. TTM Squeeze Detected: {'✅ PASS' if ttm_result else '❌ FAIL'}")
    print(f"4. Volume Dry-up (0.41x): {'✅ PASS' if volume_result else '❌ FAIL'} (actual: {volume_ratio:.2f}x)")
    
    total = sum([stoch_result, macd_result, ttm_result, volume_result])
    print(f"\nTotal: {total}/4 tests passed")
    
    print(f"\n{'='*80}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    main()
