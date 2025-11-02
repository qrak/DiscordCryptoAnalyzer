"""
Final Investigation: Check the EXACT data that would have been used
at analysis time 21:34:25 on November 2, 2025

At 21:34:25:
- Current hour candle: 21:00:00 (34 minutes in = incomplete)
- Last COMPLETED candle: 20:00:00
- Analysis should use data up to 20:00:00

Let me check if squeeze was detected at 20:00:00 or if there's
caching/persistence causing old pattern to show up.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import ccxt

from src.indicators.indicators.volatility.volatility_indicators import (
    bollinger_bands_numba,
    keltner_channels_numba
)
from src.analyzer.pattern_engine.indicator_patterns.volatility_patterns import (
    detect_keltner_squeeze_numba
)


def main():
    print("\n" + "="*80)
    print("FINAL TTM SQUEEZE INVESTIGATION")
    print("Checking data at original analysis time: 2025-11-02 21:34:25")
    print("="*80)
    
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'spot'}
    })
    
    # Fetch data as it would have been at 21:34:25
    # At that time, 21:00 candle was incomplete (34 minutes in)
    # So we fetch limit+1, then exclude the last candle
    
    print("\nFetching 201 candles...")
    ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1h', limit=201)
    ohlcv_array = np.array(ohlcv)
    
    # Exclude incomplete candle (as data_fetcher.py does)
    closed_candles = ohlcv_array[:-1]
    
    df = pd.DataFrame(
        closed_candles,
        columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
    )
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms', utc=timezone.utc)
    
    print(f"Completed candles: {len(df)}")
    print(f"Last completed candle: {df.iloc[-1]['datetime']}")
    
    # Calculate indicators
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    
    bb_upper, bb_mid, bb_lower = bollinger_bands_numba(close, 20, 2.0)
    kc_upper, kc_mid, kc_lower = keltner_channels_numba(high, low, close, 20, 1.5, 'ema')
    
    # Check squeeze at last candle
    squeeze = detect_keltner_squeeze_numba(kc_upper, kc_lower, bb_upper, bb_lower)
    
    last_idx = len(df) - 1
    
    print(f"\n{'='*80}")
    print(f"SQUEEZE CHECK AT LAST COMPLETED CANDLE")
    print(f"{'='*80}")
    
    print(f"\nCandle: {df.iloc[last_idx]['datetime']}")
    print(f"Close: {close[last_idx]:.2f}")
    print(f"\nBollinger Bands:")
    print(f"  Upper: {bb_upper[last_idx]:.2f}")
    print(f"  Middle: {bb_mid[last_idx]:.2f}")
    print(f"  Lower: {bb_lower[last_idx]:.2f}")
    print(f"  Width: {bb_upper[last_idx] - bb_lower[last_idx]:.2f}")
    
    print(f"\nKeltner Channels:")
    print(f"  Upper: {kc_upper[last_idx]:.2f}")
    print(f"  Middle: {kc_mid[last_idx]:.2f}")
    print(f"  Lower: {kc_lower[last_idx]:.2f}")
    print(f"  Width: {kc_upper[last_idx] - kc_lower[last_idx]:.2f}")
    
    print(f"\nSqueeze Conditions:")
    print(f"  BB upper <= KC upper: {bb_upper[last_idx]:.2f} <= {kc_upper[last_idx]:.2f} = {bb_upper[last_idx] <= kc_upper[last_idx]}")
    print(f"  BB lower >= KC lower: {bb_lower[last_idx]:.2f} >= {kc_lower[last_idx]:.2f} = {bb_lower[last_idx] >= kc_lower[last_idx]}")
    print(f"\n  Squeeze Detected: {squeeze}")
    
    # Check historical squeezes
    print(f"\n{'='*80}")
    print("HISTORICAL SQUEEZE SCAN (last 24 hours)")
    print(f"{'='*80}")
    
    df['bb_upper'] = bb_upper
    df['bb_lower'] = bb_lower
    df['kc_upper'] = kc_upper
    df['kc_lower'] = kc_lower
    df['squeeze'] = (df['bb_upper'] <= df['kc_upper']) & (df['bb_lower'] >= df['kc_lower'])
    
    # Look at last 24 candles
    recent = df.tail(24)[['datetime', 'close', 'bb_upper', 'kc_upper', 'bb_lower', 'kc_lower', 'squeeze']]
    
    squeeze_candles = recent[recent['squeeze'] == True]
    
    if len(squeeze_candles) > 0:
        print(f"\nFound {len(squeeze_candles)} squeeze candles in last 24 hours:")
        for idx, row in squeeze_candles.iterrows():
            print(f"  {row['datetime']}: close={row['close']:.2f}")
    else:
        print("\nNo squeeze detected in last 24 hours")
    
    # Final verdict
    print(f"\n{'='*80}")
    print("INVESTIGATION RESULT")
    print(f"{'='*80}")
    
    print(f"\nAt last completed candle ({df.iloc[last_idx]['datetime']}):")
    print(f"  TTM Squeeze: {'YES ✓' if squeeze else 'NO ✗'}")
    
    print(f"\nReported in log:")
    print(f"  'TTM Squeeze detected (extreme low volatility) now at 2025-11-02 20:00:00'")
    
    if not squeeze:
        print(f"\n❌ CONTRADICTION FOUND!")
        print(f"\nPossible explanations:")
        print(f"  1. Pattern was detected earlier (check historical squeezes above)")
        print(f"  2. Pattern cache not being cleared between analyses")
        print(f"  3. Different parameters being used in production")
        print(f"  4. Bug in pattern persistence/reporting")
        
        if len(squeeze_candles) > 0:
            last_squeeze = squeeze_candles.iloc[-1]
            print(f"\n  Last actual squeeze was at: {last_squeeze['datetime']}")
            print(f"  Hours ago: {(df.iloc[last_idx]['datetime'] - last_squeeze['datetime']).total_seconds() / 3600:.1f}")
    else:
        print(f"\n✅ SQUEEZE CONFIRMED at last completed candle")
    
    print(f"\n{'='*80}\n")


if __name__ == '__main__':
    main()
