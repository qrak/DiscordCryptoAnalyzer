"""
Test formatting output with new improvements.
"""
import asyncio
import sys
import os
import json

os.chdir(os.path.dirname(os.path.abspath(__file__)))


async def test_formatting():
    """Test formatting with real data."""
    print("\n" + "=" * 80)
    print("Testing Improved Formatting")
    print("=" * 80)
    
    from src.utils.loader import config
    from src.logger.logger import Logger
    from src.platforms.coingecko import CoinGeckoAPI
    from src.analyzer.formatting.market_formatter import MarketFormatter
    from src.analyzer.data.data_processor import DataProcessor
    from src.utils.format_utils import FormatUtils
    
    logger = Logger(logger_name="FormatTest", logger_debug=False)
    
    print("\n[1] Fetching fresh data...")
    api = CoinGeckoAPI(logger=logger)
    await api.initialize()
    market_data = await api.get_global_market_data(force_refresh=True)
    
    print("\n[2] Creating formatter...")
    data_processor = DataProcessor()
    format_utils = FormatUtils(data_processor)
    formatter = MarketFormatter(logger=logger, format_utils=format_utils)
    
    print("\n[3] Formatting market overview...")
    formatted = formatter.format_market_overview(market_data)
    
    print("\n" + "=" * 80)
    print("FORMATTED OUTPUT:")
    print("=" * 80)
    print(formatted)
    print("=" * 80)
    
    # Check cache file
    print("\n[4] Cache file check:")
    with open('data/market_data/coingecko_global.json', 'r') as f:
        cached = json.load(f)
    
    defi = cached.get('data', {}).get('defi', {})
    if defi:
        print(f"  DeFi market cap type: {type(defi.get('defi_market_cap'))}")
        print(f"  DeFi market cap value: {defi.get('defi_market_cap')}")
        print(f"  DeFi dominance type: {type(defi.get('defi_dominance'))}")
        print(f"  DeFi dominance value: {defi.get('defi_dominance')}")
    
    top_coins = cached.get('data', {}).get('top_coins', [])
    if top_coins:
        print(f"\n  Top coins count: {len(top_coins)}")
        sample = top_coins[0]
        print(f"  Sample coin (BTC):")
        print(f"    - Symbol: {sample.get('symbol')}")
        print(f"    - Current price: {sample.get('current_price')}")
        print(f"    - ATH: {sample.get('ath')}")
        print(f"    - ATH date: {sample.get('ath_date')}")
        print(f"    - ATH change %: {sample.get('ath_change_percentage')}")
    
    await api.close()
    
    print("\n" + "=" * 80)
    print("✅ Test Complete!")
    print("=" * 80)


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(test_formatting())
