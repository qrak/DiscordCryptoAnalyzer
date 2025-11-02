"""
Test script to verify indicator calculations against real OHLCV data from CCXT.

This script fetches BTC/USDT 1h data and validates:
1. Stochastic bullish crossover detection
2. MACD histogram decreasing (momentum shift)
3. TTM Squeeze detection (Bollinger Bands inside Keltner Channels)
4. Volume dry-up detection

Based on the reported patterns:
- MACD histogram decreasing at 2025-11-02 20:00:00
- TTM Squeeze detected at 2025-11-02 20:00:00
- Stochastic bullish crossover 2 periods ago at 2025-11-02 18:00:00 in oversold territory
- Volume dry-up: 0.41x average at 2025-11-02 20:00:00
"""

import asyncio
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


def format_timestamp(ts_ms):
    """Convert timestamp to readable format"""
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')


def fetch_ohlcv_data(symbol='BTC/USDT', timeframe='1h', limit=200):
    """
    Fetch OHLCV data using CCXT from Binance.
    
    Args:
        symbol: Trading pair
        timeframe: Candle timeframe
        limit: Number of candles to fetch
        
    Returns:
        pandas DataFrame with OHLCV data
    """
    print(f"\n{'='*80}")
    print(f"FETCHING DATA: {symbol} @ {timeframe}")
    print(f"{'='*80}")
    
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'spot'}
    })
    
    # Fetch OHLCV
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    
    # Convert to DataFrame
    df = pd.DataFrame(
        ohlcv,
        columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
    )
    
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    
    print(f"\nFetched {len(df)} candles")
    print(f"Date range: {df['datetime'].iloc[0]} to {df['datetime'].iloc[-1]}")
    print(f"\nLast 5 candles:")
    print(df[['datetime', 'open', 'high', 'low', 'close', 'volume']].tail())
    
    return df


def calculate_stochastic(df, period_k=14, smooth_k=3, period_d=3):
    """Calculate Stochastic oscillator"""
    print(f"\n{'='*80}")
    print("STOCHASTIC OSCILLATOR CALCULATION")
    print(f"{'='*80}")
    print(f"Parameters: period_k={period_k}, smooth_k={smooth_k}, period_d={period_d}")
    
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    
    stoch_k, stoch_d = stochastic_numba(high, low, close, period_k, smooth_k, period_d)
    
    df['stoch_k'] = stoch_k
    df['stoch_d'] = stoch_d
    
    # Display last 10 values
    print("\nLast 10 Stochastic values:")
    print(df[['datetime', 'close', 'stoch_k', 'stoch_d']].tail(10).to_string(index=False))
    
    return stoch_k, stoch_d


def detect_stochastic_crossover(df, stoch_k, stoch_d):
    """Detect Stochastic bullish crossover"""
    print(f"\n{'='*80}")
    print("STOCHASTIC CROSSOVER DETECTION")
    print(f"{'='*80}")
    
    found, periods_ago, k_val, d_val, in_oversold = detect_stoch_bullish_crossover_numba(
        stoch_k, stoch_d, oversold_threshold=30.0
    )
    
    if found:
        crossover_idx = len(df) - periods_ago - 1
        crossover_time = df.iloc[crossover_idx]['datetime']
        
        print(f"\n✓ BULLISH CROSSOVER DETECTED!")
        print(f"  Periods ago: {periods_ago}")
        print(f"  Timestamp: {crossover_time}")
        print(f"  Stoch K: {k_val:.2f}")
        print(f"  Stoch D: {d_val:.2f}")
        print(f"  In Oversold (<30): {'YES' if in_oversold else 'NO'}")
        
        # Show context around crossover
        print(f"\n  Context (3 candles before and after crossover):")
        start_idx = max(0, crossover_idx - 3)
        end_idx = min(len(df), crossover_idx + 4)
        context = df.iloc[start_idx:end_idx][['datetime', 'stoch_k', 'stoch_d']].copy()
        context['is_crossover'] = ''
        context.loc[context.index == crossover_idx, 'is_crossover'] = '<<<'
        print(context.to_string(index=False))
    else:
        print("\n✗ No bullish crossover detected in last 5 periods")
    
    return found, periods_ago if found else 0


def calculate_macd(df, fast=12, slow=26, signal=9):
    """Calculate MACD"""
    print(f"\n{'='*80}")
    print("MACD CALCULATION")
    print(f"{'='*80}")
    print(f"Parameters: fast={fast}, slow={slow}, signal={signal}")
    
    close = df['close'].values
    macd_line, signal_line, histogram = macd_numba(close, fast, slow, signal)
    
    df['macd_line'] = macd_line
    df['macd_signal'] = signal_line
    df['macd_hist'] = histogram
    
    # Display last 10 values
    print("\nLast 10 MACD values:")
    print(df[['datetime', 'close', 'macd_line', 'macd_signal', 'macd_hist']].tail(10).to_string(index=False))
    
    return macd_line, signal_line, histogram


def detect_macd_momentum_shift(df, histogram):
    """Detect MACD histogram decreasing (momentum shift)"""
    print(f"\n{'='*80}")
    print("MACD MOMENTUM SHIFT DETECTION")
    print(f"{'='*80}")
    
    # Check if histogram is decreasing
    if len(histogram) < 3:
        print("\n✗ Insufficient data")
        return False
    
    # Get last 3 histogram values
    last_vals = histogram[-3:]
    if np.any(np.isnan(last_vals)):
        print("\n✗ NaN values in histogram")
        return False
    
    # Check if decreasing: hist[-1] < hist[-2] < hist[-3]
    is_decreasing = last_vals[-1] < last_vals[-2] and last_vals[-2] < last_vals[-3]
    
    print(f"\nLast 3 histogram values:")
    for i, val in enumerate(last_vals):
        idx = len(df) - 3 + i
        timestamp = df.iloc[idx]['datetime']
        print(f"  [{i}] {timestamp}: {val:.6f}")
    
    if is_decreasing:
        print(f"\n✓ MACD HISTOGRAM DECREASING (momentum shift)")
        print(f"  Current: {last_vals[-1]:.6f}")
        print(f"  Previous: {last_vals[-2]:.6f}")
        print(f"  2 periods ago: {last_vals[-3]:.6f}")
    else:
        print(f"\n✗ MACD histogram NOT consistently decreasing")
    
    return is_decreasing


def calculate_ttm_squeeze(df, bb_length=20, bb_mult=2.0, kc_length=20, kc_mult=1.5):
    """Calculate TTM Squeeze indicator"""
    print(f"\n{'='*80}")
    print("TTM SQUEEZE DETECTION")
    print(f"{'='*80}")
    print(f"Bollinger Bands: length={bb_length}, mult={bb_mult}")
    print(f"Keltner Channels: length={kc_length}, mult={kc_mult}")
    
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    
    # Calculate Bollinger Bands
    bb_upper, bb_middle, bb_lower = bollinger_bands_numba(close, bb_length, bb_mult)
    
    # Calculate Keltner Channels
    kc_upper, kc_middle, kc_lower = keltner_channels_numba(high, low, close, kc_length, kc_mult, 'ema')
    
    df['bb_upper'] = bb_upper
    df['bb_lower'] = bb_lower
    df['kc_upper'] = kc_upper
    df['kc_lower'] = kc_lower
    
    # Display last 5 values
    print("\nLast 5 Band values:")
    print(df[['datetime', 'close', 'bb_upper', 'bb_lower', 'kc_upper', 'kc_lower']].tail(5).to_string(index=False))
    
    # Detect squeeze
    squeeze_detected = detect_keltner_squeeze_numba(kc_upper, kc_lower, bb_upper, bb_lower)
    
    if squeeze_detected:
        print(f"\n✓ TTM SQUEEZE DETECTED!")
        print(f"  Bollinger Bands are INSIDE Keltner Channels (extreme low volatility)")
        last_idx = len(df) - 1
        print(f"\n  Current values at {df.iloc[last_idx]['datetime']}:")
        print(f"    BB Upper: {bb_upper[last_idx]:.2f}")
        print(f"    KC Upper: {kc_upper[last_idx]:.2f}")
        print(f"    Close:    {close[last_idx]:.2f}")
        print(f"    KC Lower: {kc_lower[last_idx]:.2f}")
        print(f"    BB Lower: {bb_lower[last_idx]:.2f}")
        print(f"\n  Squeeze condition: BB_upper <= KC_upper AND BB_lower >= KC_lower")
        print(f"    {bb_upper[last_idx]:.2f} <= {kc_upper[last_idx]:.2f}: {bb_upper[last_idx] <= kc_upper[last_idx]}")
        print(f"    {bb_lower[last_idx]:.2f} >= {kc_lower[last_idx]:.2f}: {bb_lower[last_idx] >= kc_lower[last_idx]}")
    else:
        print(f"\n✗ NO TTM SQUEEZE detected")
        last_idx = len(df) - 1
        print(f"\n  Current values at {df.iloc[last_idx]['datetime']}:")
        print(f"    BB Upper: {bb_upper[last_idx]:.2f}")
        print(f"    KC Upper: {kc_upper[last_idx]:.2f}")
        print(f"    BB Lower: {bb_lower[last_idx]:.2f}")
        print(f"    KC Lower: {kc_lower[last_idx]:.2f}")
    
    return squeeze_detected


def analyze_volume(df, lookback=20):
    """Analyze volume dry-up"""
    print(f"\n{'='*80}")
    print("VOLUME ANALYSIS")
    print(f"{'='*80}")
    print(f"Lookback period: {lookback} candles")
    
    volume = df['volume'].values
    
    if len(volume) < lookback + 1:
        print("\n✗ Insufficient data")
        return False, 0.0
    
    # Calculate average volume (excluding current candle)
    avg_volume = np.mean(volume[-(lookback+1):-1])
    current_volume = volume[-1]
    volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
    
    print(f"\nCurrent volume: {current_volume:,.2f}")
    print(f"Average volume ({lookback} candles): {avg_volume:,.2f}")
    print(f"Ratio: {volume_ratio:.2f}x")
    
    # Volume dry-up = below 0.5x average
    is_dryup = volume_ratio < 0.5
    
    if is_dryup:
        print(f"\n✓ VOLUME DRY-UP DETECTED (potential breakout setup)")
    else:
        print(f"\n✗ NO volume dry-up (volume is normal/high)")
    
    # Show last 10 volume values
    print(f"\nLast 10 volume values:")
    last_10 = df[['datetime', 'volume']].tail(10).copy()
    last_10['vs_avg'] = last_10['volume'] / avg_volume
    print(last_10.to_string(index=False))
    
    return is_dryup, volume_ratio


def main():
    """Main test function"""
    print("\n" + "="*80)
    print("INDICATOR VERIFICATION TEST SCRIPT")
    print("Testing against real OHLCV data from CCXT (Binance)")
    print("="*80)
    
    # Fetch data
    df = fetch_ohlcv_data(symbol='BTC/USDT', timeframe='1h', limit=200)
    
    # Calculate and verify Stochastic
    stoch_k, stoch_d = calculate_stochastic(df, period_k=14, smooth_k=3, period_d=3)
    stoch_found, stoch_periods_ago = detect_stochastic_crossover(df, stoch_k, stoch_d)
    
    # Calculate and verify MACD
    macd_line, signal_line, histogram = calculate_macd(df, fast=12, slow=26, signal=9)
    macd_decreasing = detect_macd_momentum_shift(df, histogram)
    
    # Calculate and verify TTM Squeeze
    ttm_squeeze = calculate_ttm_squeeze(df, bb_length=20, bb_mult=2.0, kc_length=20, kc_mult=1.5)
    
    # Analyze volume
    volume_dryup, volume_ratio = analyze_volume(df, lookback=20)
    
    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY OF FINDINGS")
    print(f"{'='*80}")
    print(f"\n1. Stochastic Bullish Crossover:")
    print(f"   Status: {'✓ FOUND' if stoch_found else '✗ NOT FOUND'}")
    if stoch_found:
        print(f"   Periods ago: {stoch_periods_ago}")
    
    print(f"\n2. MACD Histogram Decreasing:")
    print(f"   Status: {'✓ CONFIRMED' if macd_decreasing else '✗ NOT CONFIRMED'}")
    
    print(f"\n3. TTM Squeeze:")
    print(f"   Status: {'✓ DETECTED' if ttm_squeeze else '✗ NOT DETECTED'}")
    
    print(f"\n4. Volume Dry-up:")
    print(f"   Status: {'✓ DETECTED' if volume_dryup else '✗ NOT DETECTED'}")
    print(f"   Ratio: {volume_ratio:.2f}x average")
    
    # Expected vs Actual comparison
    print(f"\n{'='*80}")
    print("COMPARISON WITH REPORTED VALUES")
    print(f"{'='*80}")
    print("\nReported patterns:")
    print("  - MACD histogram decreasing at 2025-11-02 20:00:00")
    print("  - TTM Squeeze detected at 2025-11-02 20:00:00")
    print("  - Stochastic bullish crossover 2 periods ago at 2025-11-02 18:00:00")
    print("  - Volume dry-up: 0.41x average at 2025-11-02 20:00:00")
    
    print("\nActual findings:")
    print(f"  - MACD histogram decreasing: {'YES' if macd_decreasing else 'NO'}")
    print(f"  - TTM Squeeze detected: {'YES' if ttm_squeeze else 'NO'}")
    print(f"  - Stochastic crossover: {'YES' if stoch_found else 'NO'}")
    if stoch_found:
        print(f"    → {stoch_periods_ago} periods ago")
    print(f"  - Volume dry-up: {'YES' if volume_dryup else 'NO'}")
    print(f"    → {volume_ratio:.2f}x average")
    
    print(f"\n{'='*80}")
    print("TEST COMPLETE")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    main()
