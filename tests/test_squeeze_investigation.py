"""
Deep Investigation: TTM Squeeze Detection Logic

This test will:
1. Fetch the exact same data that would be used at analysis time
2. Calculate BB and KC bands step-by-step
3. Check the squeeze condition at every candle
4. Add detailed logging to understand the discrepancy
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import ccxt

from src.indicators.indicators.momentum.momentum_indicators import stochastic_numba
from src.indicators.indicators.volatility.volatility_indicators import (
    bollinger_bands_numba,
    keltner_channels_numba
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
    
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit + 1)
    
    # Mimic what data_fetcher.py does - exclude last candle
    ohlcv_array = np.array(ohlcv)
    closed_candles = ohlcv_array[:-1]  # Exclude incomplete candle
    latest_close = float(ohlcv_array[-1, 4])
    
    df = pd.DataFrame(
        closed_candles,
        columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
    )
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    
    return df, latest_close


def detailed_squeeze_analysis(df):
    """
    Perform detailed analysis of TTM Squeeze detection
    """
    print(f"\n{'='*80}")
    print("TTM SQUEEZE DEEP INVESTIGATION")
    print(f"{'='*80}")
    
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    
    # Calculate bands with default parameters
    bb_upper, bb_mid, bb_lower = bollinger_bands_numba(close, 20, 2.0)
    kc_upper, kc_mid, kc_lower = keltner_channels_numba(high, low, close, 20, 1.5, 'ema')
    
    df['bb_upper'] = bb_upper
    df['bb_mid'] = bb_mid
    df['bb_lower'] = bb_lower
    df['kc_upper'] = kc_upper
    df['kc_mid'] = kc_mid
    df['kc_lower'] = kc_lower
    
    # Calculate squeeze status for each candle
    df['bb_width'] = df['bb_upper'] - df['bb_lower']
    df['kc_width'] = df['kc_upper'] - df['kc_lower']
    df['bb_inside_kc_upper'] = df['bb_upper'] <= df['kc_upper']
    df['bb_inside_kc_lower'] = df['bb_lower'] >= df['kc_lower']
    df['squeeze'] = df['bb_inside_kc_upper'] & df['bb_inside_kc_lower']
    
    print(f"\nDataset info:")
    print(f"  Total candles: {len(df)}")
    print(f"  Date range: {df['datetime'].iloc[0]} to {df['datetime'].iloc[-1]}")
    
    # Check last 10 candles for squeeze
    print(f"\n{'='*80}")
    print("LAST 10 CANDLES - SQUEEZE STATUS")
    print(f"{'='*80}")
    
    last_10 = df.tail(10)[['datetime', 'close', 'bb_upper', 'kc_upper', 'bb_lower', 'kc_lower', 'squeeze']].copy()
    last_10['bb_upper_<=_kc_upper'] = last_10['bb_upper'] <= last_10['kc_upper']
    last_10['bb_lower_>=_kc_lower'] = last_10['bb_lower'] >= last_10['kc_lower']
    
    print(last_10.to_string(index=False))
    
    # Count squeezes in last 10 candles
    squeeze_count = df.tail(10)['squeeze'].sum()
    print(f"\nSqueeze count in last 10 candles: {squeeze_count}")
    
    # Test the detection function
    print(f"\n{'='*80}")
    print("TESTING DETECTION FUNCTION")
    print(f"{'='*80}")
    
    squeeze_detected = detect_keltner_squeeze_numba(kc_upper, kc_lower, bb_upper, bb_lower)
    
    print(f"\nFunction: detect_keltner_squeeze_numba()")
    print(f"Result: {squeeze_detected}")
    print(f"\nFunction checks LAST candle only:")
    
    last_idx = len(df) - 1
    print(f"  Index: {last_idx}")
    print(f"  Timestamp: {df.iloc[last_idx]['datetime']}")
    print(f"  BB Upper: {bb_upper[last_idx]:.2f}")
    print(f"  KC Upper: {kc_upper[last_idx]:.2f}")
    print(f"  BB Lower: {bb_lower[last_idx]:.2f}")
    print(f"  KC Lower: {kc_lower[last_idx]:.2f}")
    print(f"\n  Condition 1 (BB upper <= KC upper): {bb_upper[last_idx]:.2f} <= {kc_upper[last_idx]:.2f} = {bb_upper[last_idx] <= kc_upper[last_idx]}")
    print(f"  Condition 2 (BB lower >= KC lower): {bb_lower[last_idx]:.2f} >= {kc_lower[last_idx]:.2f} = {bb_lower[last_idx] >= kc_lower[last_idx]}")
    print(f"  Both conditions: {squeeze_detected}")
    
    # Check if there are NaN values
    print(f"\n{'='*80}")
    print("DATA QUALITY CHECK")
    print(f"{'='*80}")
    
    print(f"\nNaN counts in last 10 candles:")
    print(f"  BB Upper: {np.isnan(bb_upper[-10:]).sum()}")
    print(f"  BB Lower: {np.isnan(bb_lower[-10:]).sum()}")
    print(f"  KC Upper: {np.isnan(kc_upper[-10:]).sum()}")
    print(f"  KC Lower: {np.isnan(kc_lower[-10:]).sum()}")
    
    # Check different parameter combinations
    print(f"\n{'='*80}")
    print("PARAMETER SENSITIVITY ANALYSIS")
    print(f"{'='*80}")
    
    param_tests = [
        {'name': 'Standard (BB:20/2.0, KC:20/1.5)', 'bb_mult': 2.0, 'kc_mult': 1.5},
        {'name': 'Wider KC (BB:20/2.0, KC:20/2.0)', 'bb_mult': 2.0, 'kc_mult': 2.0},
        {'name': 'Narrower KC (BB:20/2.0, KC:20/1.0)', 'bb_mult': 2.0, 'kc_mult': 1.0},
        {'name': 'Wider BB (BB:20/2.5, KC:20/1.5)', 'bb_mult': 2.5, 'kc_mult': 1.5},
        {'name': 'Narrower BB (BB:20/1.5, KC:20/1.5)', 'bb_mult': 1.5, 'kc_mult': 1.5},
        {'name': 'Very Narrow BB (BB:20/1.0, KC:20/1.5)', 'bb_mult': 1.0, 'kc_mult': 1.5},
    ]
    
    print(f"\nTesting at last candle ({df.iloc[-1]['datetime']}):\n")
    
    for params in param_tests:
        bb_u, _, bb_l = bollinger_bands_numba(close, 20, params['bb_mult'])
        kc_u, _, kc_l = keltner_channels_numba(high, low, close, 20, params['kc_mult'], 'ema')
        
        squeeze = detect_keltner_squeeze_numba(kc_u, kc_l, bb_u, bb_l)
        
        print(f"{params['name']}")
        print(f"  Squeeze: {'YES ✓' if squeeze else 'NO ✗'}")
        if not np.isnan(bb_u[-1]) and not np.isnan(kc_u[-1]):
            print(f"  BB: {bb_l[-1]:.2f} - {bb_u[-1]:.2f} (width: {bb_u[-1] - bb_l[-1]:.2f})")
            print(f"  KC: {kc_l[-1]:.2f} - {kc_u[-1]:.2f} (width: {kc_u[-1] - kc_l[-1]:.2f})")
            print(f"  BB/KC ratio: {(bb_u[-1] - bb_l[-1]) / (kc_u[-1] - kc_l[-1]):.4f}")
        print()
    
    # Historical squeeze analysis
    print(f"\n{'='*80}")
    print("HISTORICAL SQUEEZE ANALYSIS")
    print(f"{'='*80}")
    
    # Find all squeeze periods in last 20 candles
    squeeze_periods = []
    for i in range(len(df) - 20, len(df)):
        if df.iloc[i]['squeeze']:
            squeeze_periods.append({
                'index': i,
                'datetime': df.iloc[i]['datetime'],
                'close': df.iloc[i]['close'],
                'bb_width': df.iloc[i]['bb_width'],
                'kc_width': df.iloc[i]['kc_width']
            })
    
    if squeeze_periods:
        print(f"\nFound {len(squeeze_periods)} squeeze candles in last 20:")
        for sp in squeeze_periods:
            print(f"  {sp['datetime']}: close={sp['close']:.2f}, BB width={sp['bb_width']:.2f}, KC width={sp['kc_width']:.2f}")
    else:
        print(f"\nNo squeeze detected in last 20 candles")
    
    return squeeze_detected


def main():
    print("\n" + "="*80)
    print("TTM SQUEEZE DISCREPANCY INVESTIGATION")
    print("="*80)
    
    # Fetch data (excluding incomplete candle)
    df, latest_close = fetch_data(symbol='BTC/USDT', timeframe='1h', limit=200)
    
    print(f"\nLatest data point (incomplete candle, not used):")
    print(f"  Close price: {latest_close:.2f}")
    
    # Run detailed analysis
    squeeze_detected = detailed_squeeze_analysis(df)
    
    print(f"\n{'='*80}")
    print("FINAL RESULT")
    print(f"{'='*80}")
    
    print(f"\nTTM Squeeze at last completed candle: {'YES ✓' if squeeze_detected else 'NO ✗'}")
    print(f"Expected from log: YES")
    print(f"Match: {'✅' if squeeze_detected else '❌'}")
    
    print(f"\n{'='*80}")
    print("INVESTIGATION COMPLETE")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    main()
