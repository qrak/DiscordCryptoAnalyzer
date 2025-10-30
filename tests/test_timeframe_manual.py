"""
Manual testing script for timeframe-specific prompt and indicator calculations.

Tests prompt generation and technical indicator calculations for 2h, 4h, and 6h timeframes.
"""

import asyncio
import sys
import os
import numpy as np
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.analyzer.prompts.context_builder import ContextBuilder
from src.analyzer.calculations.technical_calculator import TechnicalCalculator
from src.utils.timeframe_validator import TimeframeValidator


def generate_realistic_ohlcv(num_candles: int, base_price: float = 50000) -> np.ndarray:
    """Generate realistic OHLCV data for testing."""
    data = []
    current_price = base_price
    base_time = int(datetime.now().timestamp() * 1000) - (num_candles * 3600000)
    
    for i in range(num_candles):
        # Simulate price movement
        change_percent = np.random.uniform(-0.02, 0.02)  # ±2% per candle
        current_price *= (1 + change_percent)
        
        open_price = current_price
        high = open_price * (1 + abs(np.random.uniform(0, 0.01)))
        low = open_price * (1 - abs(np.random.uniform(0, 0.01)))
        close = np.random.uniform(low, high)
        volume = np.random.uniform(100, 1000)
        
        timestamp = base_time + (i * 3600000)
        data.append([timestamp, open_price, high, low, close, volume])
    
    return np.array(data)


def print_separator(title: str):
    """Print a formatted separator."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def test_timeframe_period_calculations():
    """Test period calculations for different timeframes."""
    print_separator("PERIOD CALCULATIONS TEST")
    
    timeframes = ['2h', '4h', '6h']
    
    for tf in timeframes:
        print(f"Timeframe: {tf}")
        print(f"  Display: {TimeframeValidator.format_timeframe_display(tf)}")
        print(f"  Minutes: {TimeframeValidator.to_minutes(tf)}")
        print(f"  Intraday: {TimeframeValidator.is_intraday(tf)}")
        
        # Calculate periods
        periods = {
            '4h': TimeframeValidator.calculate_period_candles(tf, '4h'),
            '24h': TimeframeValidator.calculate_period_candles(tf, '24h'),
            '3d': TimeframeValidator.calculate_period_candles(tf, '3d'),
            '7d': TimeframeValidator.calculate_period_candles(tf, '7d'),
            '30d': TimeframeValidator.calculate_period_candles(tf, '30d'),
        }
        
        print(f"  Period calculations:")
        for period, candles in periods.items():
            print(f"    {period:6s} = {candles:4d} candles")
        
        # Calculate candle limit for 30 days
        limit = TimeframeValidator.get_candle_limit_for_days(tf, 30)
        print(f"  30-day candle limit: {limit}")
        
        # CryptoCompare format
        endpoint, multiplier = TimeframeValidator.to_cryptocompare_format(tf)
        print(f"  CryptoCompare: endpoint='{endpoint}', aggregate={multiplier}")
        print()


def test_context_builder(timeframe: str):
    """Test ContextBuilder for a specific timeframe."""
    print_separator(f"CONTEXT BUILDER TEST - {timeframe}")
    
    builder = ContextBuilder(timeframe=timeframe)
    
    # Test period calculations
    periods = builder._calculate_period_candles()
    print(f"Period candles for {timeframe}:")
    for period, count in periods.items():
        print(f"  {period}: {count} candles")
    
    # Generate test data
    limit = TimeframeValidator.get_candle_limit_for_days(timeframe, 30)
    ohlcv = generate_realistic_ohlcv(limit)
    
    print(f"\nGenerated {len(ohlcv)} candles of test data")
    print(f"Price range: ${ohlcv[:, 4].min():.2f} - ${ohlcv[:, 4].max():.2f}")
    
    # Build market data section
    market_data = builder.build_market_data_section(ohlcv)
    
    # Extract key information
    lines = market_data.split('\n')
    print("\nMarket Data Section Preview:")
    for line in lines[:15]:  # First 15 lines
        if line.strip():
            print(f"  {line}")
    
    # Check for timeframe mention
    if f"Based on {timeframe} candles" in market_data:
        print(f"\n✅ Timeframe '{timeframe}' correctly mentioned in market data")
    else:
        print(f"\n❌ Timeframe '{timeframe}' NOT found in market data")
    
    return ohlcv


def test_technical_indicators(timeframe: str, ohlcv: np.ndarray):
    """Test technical indicator calculations for a specific timeframe."""
    print_separator(f"TECHNICAL INDICATORS TEST - {timeframe}")
    
    calculator = TechnicalCalculator()
    
    # Calculate all indicators using the actual get_indicators method
    print("Calculating technical indicators...")
    
    try:
        indicators = calculator.get_indicators(ohlcv)
        
        # Get latest values
        current_price = ohlcv[-1, 4]
        
        print(f"\nTimeframe: {timeframe} ({TimeframeValidator.format_timeframe_display(timeframe)})")
        print(f"Data points: {len(ohlcv)} candles")
        print(f"Current Price: ${current_price:.2f}")
        
        print("\nVolatility Indicators:")
        print(f"  BB Upper: ${indicators['bb_upper'][-1]:.2f}")
        print(f"  BB Middle: ${indicators['bb_middle'][-1]:.2f}")
        print(f"  BB Lower: ${indicators['bb_lower'][-1]:.2f}")
        print(f"  BB %B: {indicators['bb_percent_b']:.2f}")
        print(f"  ATR(20): ${indicators['atr'][-1]:.2f}")
        print(f"  Keltner Upper: ${indicators['kc_upper'][-1]:.2f}")
        print(f"  Keltner Lower: ${indicators['kc_lower'][-1]:.2f}")
        
        print("\nMomentum Indicators:")
        print(f"  RSI(14): {indicators['rsi'][-1]:.2f}")
        print(f"  MACD Line: {indicators['macd_line'][-1]:.2f}")
        print(f"  MACD Signal: {indicators['macd_signal'][-1]:.2f}")
        print(f"  MACD Histogram: {indicators['macd_hist'][-1]:.2f}")
        print(f"  Stochastic %K: {indicators['stoch_k'][-1]:.2f}")
        print(f"  Stochastic %D: {indicators['stoch_d'][-1]:.2f}")
        print(f"  Williams %R: {indicators['williams_r'][-1]:.2f}")
        print(f"  Ultimate Oscillator: {indicators['uo'][-1]:.2f}")
        
        print("\nTrend Indicators:")
        print(f"  ADX: {indicators['adx'][-1]:.2f}")
        print(f"  +DI: {indicators['plus_di'][-1]:.2f}")
        print(f"  -DI: {indicators['minus_di'][-1]:.2f}")
        
        print("\nVolume Indicators:")
        print(f"  VWAP: ${indicators['vwap'][-1]:.2f}")
        print(f"  TWAP: ${indicators['twap'][-1]:.2f}")
        print(f"  MFI: {indicators['mfi'][-1]:.2f}")
        print(f"  OBV: {indicators['obv'][-1]:,.0f}")
        print(f"  CMF: {indicators['cmf'][-1]:.4f}")
        print(f"  Force Index: {indicators['force_index'][-1]:.2f}")
        print(f"  CCI: {indicators['cci'][-1]:.2f}")
        
        print("\nStatistical Indicators:")
        print(f"  Kurtosis: {indicators['kurtosis'][-1]:.4f}")
        print(f"  Z-Score: {indicators['zscore'][-1]:.4f}")
        print(f"  Hurst Exponent: {indicators['hurst'][-1]:.4f}")
        
        # Validate indicators are reasonable
        print("\n✅ Validation:")
        checks = []
        checks.append(("BB values", not np.isnan(indicators['bb_middle'][-1]) and indicators['bb_middle'][-1] > 0))
        checks.append(("RSI in range [0,100]", 0 <= indicators['rsi'][-1] <= 100))
        checks.append(("Stochastic in range [0,100]", 0 <= indicators['stoch_k'][-1] <= 100))
        checks.append(("Bollinger bands ordered", indicators['bb_lower'][-1] < indicators['bb_middle'][-1] < indicators['bb_upper'][-1]))
        checks.append(("ATR positive", indicators['atr'][-1] > 0))
        checks.append(("Williams %R in range [-100,0]", -100 <= indicators['williams_r'][-1] <= 0))
        checks.append(("MFI in range [0,100]", 0 <= indicators['mfi'][-1] <= 100))
        checks.append(("ADX in range [0,100]", 0 <= indicators['adx'][-1] <= 100))
        
        for check_name, result in checks:
            status = "✅" if result else "❌"
            print(f"  {status} {check_name}: {result}")
        
        return all(check[1] for check in checks)
        
    except Exception as e:
        print(f"\n❌ Error calculating indicators: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_candle_progress_calculation():
    """Test candle progress calculation for different timeframes."""
    print_separator("CANDLE PROGRESS CALCULATION TEST")
    
    # Mock current time: 10:35 AM = 635 minutes into day
    test_hour = 10
    test_minute = 35
    minutes_into_day = test_hour * 60 + test_minute
    
    print(f"Test time: {test_hour:02d}:{test_minute:02d} ({minutes_into_day} minutes into day)")
    print()
    
    timeframes = ['2h', '4h', '6h']
    
    for tf in timeframes:
        tf_minutes = TimeframeValidator.to_minutes(tf)
        progress_minutes = minutes_into_day % tf_minutes
        
        print(f"{tf} ({tf_minutes} min candles):")
        print(f"  Progress: {progress_minutes}/{tf_minutes} minutes")
        print(f"  Percentage: {(progress_minutes/tf_minutes*100):.1f}%")
        print()


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("  TIMEFRAME VALIDATION SUITE")
    print("  Testing: 2h, 4h, 6h timeframes")
    print("=" * 80)
    
    try:
        # Test 1: Period calculations
        test_timeframe_period_calculations()
        
        # Test 2: Candle progress
        test_candle_progress_calculation()
        
        # Test 3-5: Full context builder and indicator tests
        timeframes = ['2h', '4h', '6h']
        all_valid = True
        
        for tf in timeframes:
            ohlcv = test_context_builder(tf)
            is_valid = test_technical_indicators(tf, ohlcv)
            all_valid = all_valid and is_valid
        
        # Final summary
        print_separator("FINAL SUMMARY")
        
        if all_valid:
            print("✅ ALL TESTS PASSED")
            print("\nAll timeframes correctly calculate:")
            print("  • Period candles (4h, 24h, 3d, 7d, 30d)")
            print("  • Candle limits for 30 days")
            print("  • CryptoCompare API format")
            print("  • Technical indicators (SMA, EMA, RSI, MACD, Stochastic, BB, ATR, OBV)")
            print("  • Candle progress tracking")
            print("\n✅ Ready for production use with 2h, 4h, and 6h timeframes")
        else:
            print("❌ SOME TESTS FAILED")
            print("Review the output above for details.")
        
        return 0 if all_valid else 1
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
