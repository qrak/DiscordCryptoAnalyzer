"""
Critical Test: Verify timestamp handling and incomplete candle exclusion

The issue might be that at analysis time 21:34:25, the CCXT fetch is returning
the 20:00:00 candle as the "last" candle in the array, and the code excludes it,
meaning the analysis actually runs on data up to 19:00:00.

But the pattern timestamps are being reported relative to the "current" time (20:00:00)
not the last completed candle time.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import ccxt


def test_timestamp_handling():
    """Test how CCXT returns timestamps and how we handle them"""
    print("\n" + "="*80)
    print("TIMESTAMP HANDLING INVESTIGATION")
    print("="*80)
    
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'spot'}
    })
    
    # Fetch with limit + 1 (as the code does)
    print("\nFetching BTC/USDT 1h data with limit=201 (200 + 1)...")
    ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1h', limit=201)
    
    print(f"Received {len(ohlcv)} candles from exchange")
    
    # Convert to array
    ohlcv_array = np.array(ohlcv)
    
    print(f"\n{'='*80}")
    print("RAW DATA FROM EXCHANGE (last 3 candles)")
    print(f"{'='*80}")
    
    for i in range(-3, 0):
        ts_ms = ohlcv_array[i, 0]
        dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        print(f"\nCandle {len(ohlcv) + i} (index {i}):")
        print(f"  Timestamp: {ts_ms} ms")
        print(f"  DateTime: {dt}")
        print(f"  Open: {ohlcv_array[i, 1]:.2f}")
        print(f"  Close: {ohlcv_array[i, 4]:.2f}")
        print(f"  Volume: {ohlcv_array[i, 5]:.2f}")
    
    # Now exclude last candle (as data_fetcher.py does)
    closed_candles = ohlcv_array[:-1]
    latest_close = float(ohlcv_array[-1, 4])
    
    print(f"\n{'='*80}")
    print("AFTER EXCLUDING LAST CANDLE (as data_fetcher.py does)")
    print(f"{'='*80}")
    
    print(f"\nClosed candles count: {len(closed_candles)}")
    print(f"Latest close price (from excluded candle): {latest_close:.2f}")
    
    print(f"\nLast 3 CLOSED (completed) candles:")
    for i in range(-3, 0):
        ts_ms = closed_candles[i, 0]
        dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        print(f"\nCandle {len(closed_candles) + i} (index {i}):")
        print(f"  DateTime: {dt}")
        print(f"  Close: {closed_candles[i, 4]:.2f}")
    
    # Check current time vs last candle time
    print(f"\n{'='*80}")
    print("TIME ANALYSIS")
    print(f"{'='*80}")
    
    current_time = datetime.now(timezone.utc)
    last_complete_time = datetime.fromtimestamp(closed_candles[-1, 0] / 1000, tz=timezone.utc)
    incomplete_time = datetime.fromtimestamp(ohlcv_array[-1, 0] / 1000, tz=timezone.utc)
    
    print(f"\nCurrent UTC time: {current_time}")
    print(f"Last completed candle: {last_complete_time}")
    print(f"Incomplete candle (excluded): {incomplete_time}")
    
    time_diff = (current_time - last_complete_time).total_seconds() / 60
    print(f"\nMinutes since last completed candle: {time_diff:.1f}")
    
    # Determine what percentage through the current hour we are
    current_minute = current_time.minute
    hour_progress = (current_minute / 60) * 100
    print(f"Current hour progress: {hour_progress:.1f}% ({current_minute}/60 minutes)")
    
    return closed_candles, incomplete_time


def test_pattern_timestamp_reporting(closed_candles, incomplete_time):
    """Test how patterns report timestamps"""
    print(f"\n{'='*80}")
    print("PATTERN TIMESTAMP REPORTING")
    print(f"{'='*80}")
    
    print("\nQuestion: When a pattern says 'now at 2025-11-02 20:00:00', does it mean:")
    print("  A) The pattern was detected on the last COMPLETED candle (19:00:00)")
    print("  B) The pattern timestamp refers to the CURRENT/INCOMPLETE candle time (20:00:00)")
    print("  C) Something else?")
    
    last_complete_time = datetime.fromtimestamp(closed_candles[-1, 0] / 1000, tz=timezone.utc)
    
    print(f"\nData used for indicators:")
    print(f"  Last completed candle: {last_complete_time}")
    print(f"  Number of candles: {len(closed_candles)}")
    
    print(f"\nPattern timestamp in log:")
    print(f"  'now at 2025-11-02 20:00:00'")
    
    print(f"\nHYPOTHESIS:")
    print(f"  The pattern detection runs on completed candles (up to {last_complete_time})")
    print(f"  But the timestamp formatter uses the 'current' reference time ({incomplete_time})")
    print(f"  So 'now' = current incomplete candle time, even though data is from previous hour")
    
    # Check the _format_pattern_time logic
    print(f"\n{'='*80}")
    print("TIMESTAMP FORMATTING LOGIC")
    print(f"{'='*80}")
    
    print("\nFrom indicator_pattern_engine.py:")
    print("  timestamp_str = self._format_pattern_time(0, pattern_index, timestamps)")
    print("\nWhere:")
    print("  - periods_ago = 0 means 'current' pattern")
    print("  - pattern_index = len(array) - 1 (last element)")
    print("  - timestamps = list of datetime objects from ohlcv_candles")
    
    print(f"\nIf timestamps come from closed_candles:")
    print(f"  timestamps[-1] would be: {last_complete_time}")
    print(f"\nBut log shows: 2025-11-02 20:00:00")
    print(f"Which is: {incomplete_time}")
    
    print(f"\n⚠️  DISCREPANCY: Log timestamp doesn't match last completed candle!")


def main():
    print("\n" + "="*80)
    print("CRITICAL INVESTIGATION: TIMESTAMP HANDLING")
    print("="*80)
    
    closed_candles, incomplete_time = test_timestamp_handling()
    test_pattern_timestamp_reporting(closed_candles, incomplete_time)
    
    print(f"\n{'='*80}")
    print("CONCLUSION")
    print(f"{'='*80}")
    
    print("\nThe TTM Squeeze discrepancy might be caused by:")
    print("  1. Pattern detection uses completed candles (correct)")
    print("  2. But timestamps in patterns refer to incomplete/current time (misleading)")
    print("  3. Historical squeeze existed at 01:00-06:00 but not at 19:00 or 20:00")
    print("  4. The pattern might have been detected HOURS earlier and cached/persisted")
    
    print("\nNext step: Check if patterns are cached between analysis runs")
    print("="*80 + "\n")


if __name__ == '__main__':
    main()
