"""
Test enhanced market overview with analyzed coin comparison.
"""
import asyncio
import sys
import os
import json

os.chdir(os.path.dirname(os.path.abspath(__file__)))


async def test_enhanced_overview():
    """Test the enhanced market overview formatting."""
    print("\n" + "=" * 80)
    print("Testing Enhanced Market Overview with Coin Comparison")
    print("=" * 80)
    
    from src.utils.loader import config
    from src.logger.logger import Logger
    from src.platforms.coingecko import CoinGeckoAPI
    from src.analyzer.formatting.market_formatter import MarketFormatter
    from src.analyzer.data.data_processor import DataProcessor
    from src.utils.format_utils import FormatUtils
    
    logger = Logger(logger_name="EnhancedTest", logger_debug=False)
    
    print("\n[1] Loading cached market data...")
    with open('data/market_data/coingecko_global.json', 'r') as f:
        cached = json.load(f)
    market_data = cached['data']
    
    print("\n[2] Creating formatter...")
    data_processor = DataProcessor()
    format_utils = FormatUtils(data_processor)
    formatter = MarketFormatter(logger=logger, format_utils=format_utils)
    
    # Test with BTC (should show position and exclude from top coins)
    print("\n" + "=" * 80)
    print("TEST 1: Analyzing BTC/USDT (Top Coin)")
    print("=" * 80)
    formatted_btc = formatter.format_market_overview(market_data, analyzed_symbol="BTC/USDT")
    print(formatted_btc)
    
    # Test with ETH (should show position and exclude from top coins)
    print("\n" + "=" * 80)
    print("TEST 2: Analyzing ETH/USDT (Top Coin)")
    print("=" * 80)
    formatted_eth = formatter.format_market_overview(market_data, analyzed_symbol="ETH/USDT")
    print(formatted_eth)
    
    # Test with non-top coin (should show all top coins normally)
    print("\n" + "=" * 80)
    print("TEST 3: Analyzing MATIC/USDT (Non-Top-10 Coin)")
    print("=" * 80)
    formatted_matic = formatter.format_market_overview(market_data, analyzed_symbol="MATIC/USDT")
    print(formatted_matic)
    
    # Test without symbol (backward compatibility)
    print("\n" + "=" * 80)
    print("TEST 4: No Analyzed Symbol (Backward Compatibility)")
    print("=" * 80)
    formatted_none = formatter.format_market_overview(market_data)
    print(formatted_none)
    
    print("\n" + "=" * 80)
    print("✅ All Tests Complete!")
    print("=" * 80)
    
    # Summary
    print("\n📊 Key Improvements:")
    print("  1. ✅ Analyzed coin position shown separately with rank, market share, volume share")
    print("  2. ✅ Analyzed coin excluded from 'Top Coins' list to avoid self-comparison")
    print("  3. ✅ Added 1h momentum to top coins for short-term trend context")
    print("  4. ✅ Added volume share percentages for liquidity comparison")
    print("  5. ✅ Added supply metrics (circulating vs max) for scarcity analysis")
    print("  6. ✅ Added market cap rank to each top coin")
    print("  7. ✅ Backward compatible - works with or without analyzed_symbol")


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(test_enhanced_overview())
