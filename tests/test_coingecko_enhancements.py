"""
Test script to verify CoinGecko API enhancements.
Tests the new endpoints and formatting methods without running the full bot.
"""
import asyncio
import json
import os
import sys

# Change to script directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))


async def test_coingecko_api():
    """Test the CoinGecko API enhancements."""
    print("=" * 80)
    print("Testing CoinGecko API Enhancements")
    print("=" * 80)
    
    # Import after changing directory to avoid circular imports
    from src.logger.logger import Logger
    from src.platforms.coingecko import CoinGeckoAPI
    from src.analyzer.formatting.market_formatter import MarketFormatter
    from src.utils.format_utils import FormatUtils
    
    # Initialize logger
    print("\n[1] Initializing Logger...")
    logger = Logger(
        log_dir="logs",
        log_name="test",
        logger_debug=True,
        logger_errors_to_file=False
    )
    
    # Initialize CoinGecko API
    print("\n[2] Initializing CoinGecko API...")
    api = CoinGeckoAPI(logger=logger)
    await api.initialize()
    
    # Test fetching global data with new endpoints
    print("\n[3] Fetching global market data (includes top coins and DeFi)...")
    market_data = await api.get_global_market_data(force_refresh=True)
    
    print("\n[4] Market Data Structure:")
    print(f"  - market_cap: {bool(market_data.get('market_cap'))}")
    print(f"  - volume: {bool(market_data.get('volume'))}")
    print(f"  - dominance: {bool(market_data.get('dominance'))}")
    print(f"  - stats: {bool(market_data.get('stats'))}")
    print(f"  - top_coins: {bool(market_data.get('top_coins'))}")
    print(f"  - defi: {bool(market_data.get('defi'))}")
    
    # Check top coins
    if market_data.get('top_coins'):
        print(f"\n[5] Top Coins Retrieved: {len(market_data['top_coins'])} coins")
        for i, coin in enumerate(market_data['top_coins'][:3], 1):
            print(f"  {i}. {coin.get('symbol', '?').upper()}: "
                  f"${coin.get('current_price', 0):,.2f} "
                  f"(24h: {coin.get('price_change_percentage_24h', 0):+.2f}%, "
                  f"ATH: {coin.get('ath_change_percentage', 0):+.1f}%)")
    else:
        print("\n[5] ⚠ No top_coins data retrieved")
    
    # Check DeFi data
    if market_data.get('defi'):
        defi = market_data['defi']
        print(f"\n[6] DeFi Data Retrieved:")
        print(f"  - DeFi Market Cap: ${float(defi.get('defi_market_cap', 0)):,.0f}")
        print(f"  - DeFi Dominance: {float(defi.get('defi_dominance', 0)):.2f}%")
        print(f"  - Top DeFi Coin: {defi.get('top_coin_name', 'N/A')}")
    else:
        print("\n[6] ⚠ No DeFi data retrieved")
    
    # Test formatting
    print("\n[7] Testing MarketFormatter...")
    format_utils = FormatUtils()
    formatter = MarketFormatter(logger=logger, format_utils=format_utils)
    formatted_output = formatter.format_market_overview(market_data)
    
    if formatted_output:
        print("\n[8] Formatted Output Preview:")
        print("-" * 80)
        # Print first 1500 chars
        print(formatted_output[:1500])
        if len(formatted_output) > 1500:
            print(f"\n... (truncated, total length: {len(formatted_output)} chars)")
        print("-" * 80)
    else:
        print("\n[8] ⚠ No formatted output generated")
    
    # Check cache file
    print("\n[9] Checking cached data file...")
    try:
        with open('data/market_data/coingecko_global.json', 'r', encoding='utf-8') as f:
            cached = json.load(f)
            print(f"  - Cache timestamp: {cached.get('timestamp', 'N/A')}")
            print(f"  - Has top_coins: {bool(cached.get('data', {}).get('top_coins'))}")
            print(f"  - Has defi: {bool(cached.get('data', {}).get('defi'))}")
            
            # Count coins
            if cached.get('data', {}).get('top_coins'):
                num_coins = len(cached['data']['top_coins'])
                print(f"  - Number of top coins: {num_coins}")
    except FileNotFoundError:
        print("  ⚠ Cache file not found")
    except Exception as e:
        print(f"  ⚠ Error reading cache: {e}")
    
    # Cleanup
    await api.close()
    
    print("\n" + "=" * 80)
    print("✅ Test Complete!")
    print("=" * 80)


if __name__ == "__main__":
    # Set Windows event loop policy if on Windows
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(test_coingecko_api())
