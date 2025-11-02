"""
Test the actual implementation by importing app components.
This tests the real CoinGeckoAPI class integration.
"""
import asyncio
import sys
import os
import json

os.chdir(os.path.dirname(os.path.abspath(__file__)))


async def test_real_implementation():
    """Test with real implementation."""
    print("\n" + "=" * 80)
    print("Testing Real CoinGecko Implementation")
    print("=" * 80)
    
    # Import after chdir
    from src.utils.loader import config
    from src.logger.logger import Logger
    
    logger = Logger(logger_name="Test", logger_debug=True)
    
    print("\n[1] Importing CoinGeckoAPI...")
    from src.platforms.coingecko import CoinGeckoAPI
    
    print("[2] Creating and initializing API...")
    api = CoinGeckoAPI(logger=logger)
    await api.initialize()
    
    print("[3] Fetching global market data (force refresh)...")
    market_data = await api.get_global_market_data(force_refresh=True)
    
    print("\n[4] Checking data structure:")
    print(f"  - market_cap: {'✅' if market_data.get('market_cap') else '❌'}")
    print(f"  - volume: {'✅' if market_data.get('volume') else '❌'}")
    print(f"  - dominance: {'✅' if market_data.get('dominance') else '❌'}")
    print(f"  - stats: {'✅' if market_data.get('stats') else '❌'}")
    print(f"  - top_coins: {'✅' if market_data.get('top_coins') else '❌'}")
    print(f"  - defi: {'✅' if market_data.get('defi') else '❌'}")
    
    # Check top coins
    if market_data.get('top_coins'):
        print(f"\n[5] Top Coins: {len(market_data['top_coins'])} retrieved")
        for i, coin in enumerate(market_data['top_coins'][:3], 1):
            symbol = coin.get('symbol', '?').upper()
            price = coin.get('current_price', 0)
            change = coin.get('price_change_percentage_24h', 0)
            ath_pct = coin.get('ath_change_percentage', 0)
            print(f"  {i}. {symbol}: ${price:,.2f} (24h: {change:+.2f}%, ATH: {ath_pct:+.1f}%)")
    else:
        print("\n[5] ❌ No top_coins")
    
    # Check DeFi
    if market_data.get('defi'):
        defi = market_data['defi']
        print(f"\n[6] DeFi Data:")
        print(f"  - Market Cap: ${float(defi.get('defi_market_cap', 0)):,.0f}")
        print(f"  - Dominance: {float(defi.get('defi_dominance', 0)):.2f}%")
        print(f"  - Top Asset: {defi.get('top_coin_name', 'N/A')}")
    else:
        print("\n[6] ❌ No DeFi data")
    
    # Test MarketFormatter
    print("\n[7] Testing MarketFormatter...")
    from src.analyzer.formatting.market_formatter import MarketFormatter
    from src.utils.format_utils import FormatUtils
    
    formatter = MarketFormatter(logger=logger, format_utils=FormatUtils())
    formatted = formatter.format_market_overview(market_data)
    
    if formatted:
        print("\n[8] Formatted Output (first 1000 chars):")
        print("-" * 80)
        print(formatted[:1000])
        print("-" * 80)
        print(f"\nTotal length: {len(formatted)} chars")
    else:
        print("\n[8] ❌ No formatted output")
    
    # Check cache file
    print("\n[9] Verifying cache file...")
    cache_file = 'data/market_data/coingecko_global.json'
    if os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as f:
            cached = json.load(f)
        print(f"  - Timestamp: {cached.get('timestamp', 'N/A')}")
        data = cached.get('data', {})
        print(f"  - Has top_coins: {'✅' if data.get('top_coins') else '❌'}")
        print(f"  - Has defi: {'✅' if data.get('defi') else '❌'}")
    else:
        print("  ❌ Cache file not found")
    
    await api.close()
    
    print("\n" + "=" * 80)
    success = (
        market_data.get('top_coins') and 
        market_data.get('defi') and 
        formatted
    )
    if success:
        print("✅ ALL TESTS PASSED!")
    else:
        print("⚠ SOME TESTS FAILED")
    print("=" * 80 + "\n")
    
    return success


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        result = asyncio.run(test_real_implementation())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
