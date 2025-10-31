"""
Test Stochastic crossover detection with real XRP/USDT 6h data
"""
import asyncio
import numpy as np
from datetime import datetime
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.indicators.base.technical_indicators import TechnicalIndicators
from src.logger.logger import Logger
from src.analyzer.pattern_engine.indicator_patterns.stochastic_patterns import (
    detect_stoch_bullish_crossover_numba,
    detect_stoch_bearish_crossover_numba
)

async def test_real_xrp_data():
    """Test with real XRP/USDT 6h data from exchange"""
    print("=" * 80)
    print("Testing Stochastic Crossover with Real XRP/USDT 6h Data")
    print("=" * 80)
    
    # Initialize CCXT
    import ccxt.async_support as ccxt
    
    exchange = ccxt.binance()
    
    try:
        # Fetch XRP/USDT 6h OHLCV data
        symbol = "XRP/USDT"
        timeframe = "6h"
        limit = 100  # Get enough data for Stochastic calculation
        
        print(f"\nFetching {symbol} {timeframe} data (last {limit} candles)...")
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        
        # Convert to numpy arrays
        ohlcv_array = np.array(ohlcv)
        timestamps = ohlcv_array[:, 0].astype(np.int64)
        opens = ohlcv_array[:, 1].astype(np.float64)
        highs = ohlcv_array[:, 2].astype(np.float64)
        lows = ohlcv_array[:, 3].astype(np.float64)
        closes = ohlcv_array[:, 4].astype(np.float64)
        volumes = ohlcv_array[:, 5].astype(np.float64)
        
        print(f"Fetched {len(closes)} candles")
        print(f"Latest candle timestamp: {datetime.fromtimestamp(timestamps[-1]/1000)}")
        print(f"Latest close: ${closes[-1]:.4f}")
        
        # Calculate Stochastic using the same method as production
        logger = Logger()
        ti = TechnicalIndicators()
        ti.get_data(ohlcv_array)
        
        print(f"\nCalculating Stochastic (period_k=14, smooth_k=3, period_d=3)...")
        stoch_k, stoch_d = ti.momentum.stochastic(period_k=14, smooth_k=3, period_d=3)
        
        # Show last 10 values
        print(f"\nLast 10 Stochastic values:")
        print(f"{'Index':<6} {'Timestamp':<20} {'K':<8} {'D':<8} {'Status'}")
        print("-" * 60)
        for i in range(max(0, len(stoch_k) - 10), len(stoch_k)):
            ts = datetime.fromtimestamp(timestamps[i]/1000).strftime('%Y-%m-%d %H:%M')
            k_val = stoch_k[i]
            d_val = stoch_d[i]
            
            # Check position
            status = ""
            if not np.isnan(k_val) and not np.isnan(d_val):
                if k_val < 30 or d_val < 30:
                    status += "OVERSOLD "
                if k_val > 70 or d_val > 70:
                    status += "OVERBOUGHT "
                if k_val > d_val:
                    status += "K>D"
                else:
                    status += "K≤D"
            
            print(f"{i:<6} {ts:<20} {k_val:>7.2f} {d_val:>7.2f} {status}")
        
        # Detect bullish crossover
        print(f"\n{'='*60}")
        print("BULLISH CROSSOVER DETECTION:")
        print(f"{'='*60}")
        found, periods_ago, k_val, d_val, in_oversold = detect_stoch_bullish_crossover_numba(stoch_k, stoch_d)
        
        if found:
            crossover_idx = len(stoch_k) - periods_ago
            crossover_ts = datetime.fromtimestamp(timestamps[crossover_idx]/1000)
            
            print(f"✓ BULLISH CROSSOVER DETECTED!")
            print(f"  Periods ago: {periods_ago}")
            print(f"  Crossover index: {crossover_idx}")
            print(f"  Timestamp: {crossover_ts}")
            print(f"  K value at crossover: {k_val:.2f}")
            print(f"  D value at crossover: {d_val:.2f}")
            print(f"  In oversold (<30): {in_oversold}")
            
            # Verify manually
            print(f"\nMANUAL VERIFICATION:")
            if crossover_idx > 0:
                prev_idx = crossover_idx - 1
                prev_ts = datetime.fromtimestamp(timestamps[prev_idx]/1000)
                
                prev_k = stoch_k[prev_idx]
                prev_d = stoch_d[prev_idx]
                curr_k = stoch_k[crossover_idx]
                curr_d = stoch_d[crossover_idx]
                
                print(f"  Previous candle ({prev_ts}):")
                print(f"    K={prev_k:.2f}, D={prev_d:.2f}, K≤D={prev_k <= prev_d}")
                print(f"  Crossover candle ({crossover_ts}):")
                print(f"    K={curr_k:.2f}, D={curr_d:.2f}, K>D={curr_k > curr_d}")
                
                if prev_k <= prev_d and curr_k > curr_d:
                    print(f"  ✓ Crossover confirmed: K crossed above D")
                else:
                    print(f"  ❌ ERROR: No crossover found in manual check!")
                
                # Check oversold at crossover point
                crossover_oversold = curr_k < 30 or curr_d < 30
                print(f"  Oversold at crossover: {crossover_oversold} (K<30={curr_k<30}, D<30={curr_d<30})")
                
                if in_oversold == crossover_oversold:
                    print(f"  ✓ Oversold detection correct")
                else:
                    print(f"  ❌ ERROR: Oversold mismatch! Function says {in_oversold}, actual {crossover_oversold}")
        else:
            print(f"No bullish crossover detected in last 5 periods")
        
        # Detect bearish crossover
        print(f"\n{'='*60}")
        print("BEARISH CROSSOVER DETECTION:")
        print(f"{'='*60}")
        found_bear, periods_ago_bear, k_val_bear, d_val_bear, in_overbought = detect_stoch_bearish_crossover_numba(stoch_k, stoch_d)
        
        if found_bear:
            crossover_idx = len(stoch_k) - periods_ago_bear
            crossover_ts = datetime.fromtimestamp(timestamps[crossover_idx]/1000)
            
            print(f"✓ BEARISH CROSSOVER DETECTED!")
            print(f"  Periods ago: {periods_ago_bear}")
            print(f"  Timestamp: {crossover_ts}")
            print(f"  K value at crossover: {k_val_bear:.2f}")
            print(f"  D value at crossover: {d_val_bear:.2f}")
            print(f"  In overbought (>70): {in_overbought}")
        else:
            print(f"No bearish crossover detected in last 5 periods")
        
        print(f"\n{'='*60}")
        print("SUMMARY:")
        print(f"{'='*60}")
        print(f"Latest K: {stoch_k[-1]:.2f}")
        print(f"Latest D: {stoch_d[-1]:.2f}")
        print(f"Current position: {'K>D (bullish)' if stoch_k[-1] > stoch_d[-1] else 'K≤D (bearish)'}")
        if stoch_k[-1] < 30 or stoch_d[-1] < 30:
            print(f"Current zone: OVERSOLD (<30)")
        elif stoch_k[-1] > 70 or stoch_d[-1] > 70:
            print(f"Current zone: OVERBOUGHT (>70)")
        else:
            print(f"Current zone: NEUTRAL (30-70)")
        
    finally:
        await exchange.close()

if __name__ == "__main__":
    # Set event loop policy for Windows
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(test_real_xrp_data())
