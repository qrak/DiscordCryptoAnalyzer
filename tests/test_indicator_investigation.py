"""
Enhanced test script to investigate specific timestamp discrepancies.

This script focuses on the reported timestamp (2025-11-02 20:00:00) and:
1. Checks if the crossover detection uses the correct reference point
2. Verifies MACD histogram momentum shift logic
3. Examines TTM Squeeze parameters that may differ
4. Investigates volume calculation methodology
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


def fetch_data(symbol='BTC/USDT', timeframe='1h', limit=200):
    """Fetch OHLCV data"""
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'spot'}
    })
    
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(
        ohlcv,
        columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
    )
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    
    return df


def investigate_stochastic_at_timestamp(df, target_time_str='2025-11-02 20:00:00'):
    """
    Investigate Stochastic crossover from the perspective of a specific timestamp.
    
    The reported pattern says: "Stochastic bullish crossover 2 periods ago at 2025-11-02 18:00:00"
    This was reported AT 2025-11-02 20:00:00, meaning:
    - Current time: 2025-11-02 20:00:00
    - 2 periods ago: 2025-11-02 18:00:00 (crossover happened here)
    """
    print(f"\n{'='*80}")
    print("STOCHASTIC CROSSOVER - TIMESTAMP PERSPECTIVE")
    print(f"{'='*80}")
    
    # Calculate Stochastic
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    stoch_k, stoch_d = stochastic_numba(high, low, close, 14, 3, 3)
    
    df['stoch_k'] = stoch_k
    df['stoch_d'] = stoch_d
    
    # Find the target timestamp (2025-11-02 20:00:00)
    target_time = pd.Timestamp(target_time_str, tz='UTC')
    target_idx = df[df['datetime'] == target_time].index
    
    if len(target_idx) == 0:
        print(f"\n✗ Timestamp {target_time_str} not found in dataset")
        return
    
    target_idx = target_idx[0]
    print(f"\nAnalyzing from perspective of: {target_time}")
    print(f"Index in dataset: {target_idx}")
    
    # Show context: current and 5 periods back
    context_start = max(0, target_idx - 5)
    context_end = min(len(df), target_idx + 2)
    
    print(f"\nStochastic values around target timestamp:")
    context = df.iloc[context_start:context_end][['datetime', 'stoch_k', 'stoch_d']].copy()
    context['periods_from_target'] = context.index - target_idx
    context['k_vs_d'] = context['stoch_k'] - context['stoch_d']
    context['k>d'] = context['stoch_k'] > context['stoch_d']
    print(context.to_string(index=False))
    
    # Check for crossover at "2 periods ago" (index = target_idx - 2)
    if target_idx >= 2:
        crossover_idx = target_idx - 2
        crossover_time = df.iloc[crossover_idx]['datetime']
        
        print(f"\n2 periods ago from target: {crossover_time}")
        
        # Check if crossover happened here (K crossed above D)
        if crossover_idx > 0:
            k_before = df.iloc[crossover_idx - 1]['stoch_k']
            d_before = df.iloc[crossover_idx - 1]['stoch_d']
            k_at = df.iloc[crossover_idx]['stoch_k']
            d_at = df.iloc[crossover_idx]['stoch_d']
            
            was_below = k_before <= d_before
            now_above = k_at > d_at
            is_crossover = was_below and now_above
            
            print(f"\nCrossover check at {crossover_time}:")
            print(f"  Before: K={k_before:.2f}, D={d_before:.2f} → K {'<=' if was_below else '>'} D")
            print(f"  At:     K={k_at:.2f}, D={d_at:.2f} → K {'>' if now_above else '<='} D")
            print(f"  Crossover: {'YES ✓' if is_crossover else 'NO ✗'}")
            
            if is_crossover:
                in_oversold = k_at < 30 or d_at < 30
                print(f"  In Oversold (<30): {'YES ✓' if in_oversold else 'NO ✗'}")
    
    # Run the detection function as of target timestamp
    print(f"\nRunning detection function with data up to {target_time}:")
    stoch_k_subset = stoch_k[:target_idx+1]
    stoch_d_subset = stoch_d[:target_idx+1]
    
    found, periods_ago, k_val, d_val, in_oversold = detect_stoch_bullish_crossover_numba(
        stoch_k_subset, stoch_d_subset, oversold_threshold=30.0
    )
    
    if found:
        detected_idx = len(stoch_k_subset) - periods_ago - 1
        detected_time = df.iloc[detected_idx]['datetime']
        print(f"  Detected: YES ✓")
        print(f"  Periods ago: {periods_ago}")
        print(f"  Timestamp: {detected_time}")
        print(f"  K={k_val:.2f}, D={d_val:.2f}")
        print(f"  In Oversold: {'YES' if in_oversold else 'NO'}")
    else:
        print(f"  Detected: NO ✗")


def investigate_macd_momentum(df, target_time_str='2025-11-02 20:00:00'):
    """
    Investigate MACD histogram momentum shift.
    
    The pattern description says "MACD histogram decreasing (momentum shift)".
    This could mean:
    1. Histogram is becoming less positive (moving toward zero from positive)
    2. Histogram is becoming more negative (moving away from zero into negative)
    3. Simply: histogram[now] < histogram[previous]
    """
    print(f"\n{'='*80}")
    print("MACD HISTOGRAM MOMENTUM SHIFT - INVESTIGATION")
    print(f"{'='*80}")
    
    # Calculate MACD
    close = df['close'].values
    macd_line, signal_line, histogram = macd_numba(close, 12, 26, 9)
    df['macd_hist'] = histogram
    
    # Find target timestamp
    target_time = pd.Timestamp(target_time_str, tz='UTC')
    target_idx = df[df['datetime'] == target_time].index
    
    if len(target_idx) == 0:
        print(f"\n✗ Timestamp {target_time_str} not found")
        return
    
    target_idx = target_idx[0]
    print(f"\nAnalyzing at: {target_time}")
    
    # Show histogram values
    context_start = max(0, target_idx - 5)
    context_end = min(len(df), target_idx + 2)
    
    print(f"\nMACD Histogram values:")
    context = df.iloc[context_start:context_end][['datetime', 'macd_hist']].copy()
    context['change'] = context['macd_hist'].diff()
    context['is_decreasing'] = context['change'] < 0
    print(context.to_string(index=False))
    
    # Check various momentum shift interpretations
    print(f"\nMomentum shift interpretations at target timestamp:")
    
    if target_idx >= 1:
        hist_now = histogram[target_idx]
        hist_prev = histogram[target_idx - 1]
        
        print(f"\n1. Simple decrease (hist[now] < hist[prev]):")
        print(f"   Now:  {hist_now:.6f}")
        print(f"   Prev: {hist_prev:.6f}")
        print(f"   Decreasing: {'YES ✓' if hist_now < hist_prev else 'NO ✗'}")
        
        if target_idx >= 2:
            hist_prev2 = histogram[target_idx - 2]
            
            print(f"\n2. Consistent decrease (3 periods):")
            print(f"   -2: {hist_prev2:.6f}")
            print(f"   -1: {hist_prev:.6f}")
            print(f"    0: {hist_now:.6f}")
            is_consistently_decreasing = hist_now < hist_prev < hist_prev2
            print(f"   Consistently decreasing: {'YES ✓' if is_consistently_decreasing else 'NO ✗'}")
            
        # Check if momentum is weakening (absolute value decreasing)
        abs_now = abs(hist_now)
        abs_prev = abs(hist_prev)
        print(f"\n3. Momentum weakening (|hist| decreasing):")
        print(f"   |Now|:  {abs_now:.6f}")
        print(f"   |Prev|: {abs_prev:.6f}")
        print(f"   Weakening: {'YES ✓' if abs_now < abs_prev else 'NO ✗'}")
        
        # Check if becoming more negative
        print(f"\n4. Becoming more negative:")
        is_more_negative = hist_now < hist_prev and hist_now < 0
        print(f"   More negative: {'YES ✓' if is_more_negative else 'NO ✗'}")


def investigate_ttm_squeeze_params(df, target_time_str='2025-11-02 20:00:00'):
    """
    Investigate TTM Squeeze with different parameter combinations.
    
    Standard TTM Squeeze uses:
    - Bollinger Bands: 20 period, 2.0 std dev
    - Keltner Channels: 20 period, 1.5 ATR multiplier
    
    But some implementations vary.
    """
    print(f"\n{'='*80}")
    print("TTM SQUEEZE - PARAMETER INVESTIGATION")
    print(f"{'='*80}")
    
    # Find target timestamp
    target_time = pd.Timestamp(target_time_str, tz='UTC')
    target_idx = df[df['datetime'] == target_time].index
    
    if len(target_idx) == 0:
        print(f"\n✗ Timestamp {target_time_str} not found")
        return
    
    target_idx = target_idx[0]
    print(f"\nAnalyzing at: {target_time}")
    
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    
    # Test different parameter combinations
    param_sets = [
        {'name': 'Standard TTM', 'bb_len': 20, 'bb_mult': 2.0, 'kc_len': 20, 'kc_mult': 1.5},
        {'name': 'Wide KC', 'bb_len': 20, 'bb_mult': 2.0, 'kc_len': 20, 'kc_mult': 2.0},
        {'name': 'Narrow KC', 'bb_len': 20, 'bb_mult': 2.0, 'kc_len': 20, 'kc_mult': 1.0},
        {'name': 'Wide BB', 'bb_len': 20, 'bb_mult': 2.5, 'kc_len': 20, 'kc_mult': 1.5},
        {'name': 'Narrow BB', 'bb_len': 20, 'bb_mult': 1.5, 'kc_len': 20, 'kc_mult': 1.5},
    ]
    
    print(f"\nTesting different parameter combinations:\n")
    
    results = []
    for params in param_sets:
        bb_upper, bb_mid, bb_lower = bollinger_bands_numba(close, params['bb_len'], params['bb_mult'])
        kc_upper, kc_mid, kc_lower = keltner_channels_numba(
            high, low, close, params['kc_len'], params['kc_mult'], 'ema'
        )
        
        # Check at target timestamp
        bb_u = bb_upper[target_idx]
        bb_l = bb_lower[target_idx]
        kc_u = kc_upper[target_idx]
        kc_l = kc_lower[target_idx]
        
        # Squeeze condition: BB inside KC
        squeeze = bb_u <= kc_u and bb_l >= kc_l
        
        # Calculate band widths
        bb_width = bb_u - bb_l
        kc_width = kc_u - kc_l
        ratio = bb_width / kc_width if kc_width > 0 else 0
        
        results.append({
            'name': params['name'],
            'bb_params': f"{params['bb_len']}/{params['bb_mult']}",
            'kc_params': f"{params['kc_len']}/{params['kc_mult']}",
            'squeeze': '✓' if squeeze else '✗',
            'bb_width': bb_width,
            'kc_width': kc_width,
            'ratio': ratio,
            'bb_upper': bb_u,
            'kc_upper': kc_u,
            'bb_lower': bb_l,
            'kc_lower': kc_l,
        })
    
    results_df = pd.DataFrame(results)
    print(results_df[['name', 'bb_params', 'kc_params', 'squeeze', 'ratio']].to_string(index=False))
    
    print(f"\n\nDetailed values for each configuration:")
    for r in results:
        print(f"\n{r['name']} (BB:{r['bb_params']}, KC:{r['kc_params']}):")
        print(f"  Squeeze: {r['squeeze']}")
        print(f"  BB Upper: {r['bb_upper']:.2f}  |  KC Upper: {r['kc_upper']:.2f}")
        print(f"  BB Lower: {r['bb_lower']:.2f}  |  KC Lower: {r['kc_lower']:.2f}")
        print(f"  BB Width: {r['bb_width']:.2f}  |  KC Width: {r['kc_width']:.2f}")
        print(f"  Ratio (BB/KC): {r['ratio']:.4f}")


def main():
    print("\n" + "="*80)
    print("ENHANCED INDICATOR INVESTIGATION")
    print("Focus: Discrepancies at 2025-11-02 20:00:00")
    print("="*80)
    
    # Fetch data
    df = fetch_data(symbol='BTC/USDT', timeframe='1h', limit=200)
    
    print(f"\nDataset info:")
    print(f"  Total candles: {len(df)}")
    print(f"  Date range: {df['datetime'].iloc[0]} to {df['datetime'].iloc[-1]}")
    
    # Investigate each indicator at the specific timestamp
    investigate_stochastic_at_timestamp(df, '2025-11-02 20:00:00')
    investigate_macd_momentum(df, '2025-11-02 20:00:00')
    investigate_ttm_squeeze_params(df, '2025-11-02 20:00:00')
    
    print(f"\n{'='*80}")
    print("INVESTIGATION COMPLETE")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    main()
