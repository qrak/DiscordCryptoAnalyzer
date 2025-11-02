"""
Simple direct test of the CoinGecko enhancements.
This script will be called from start.py to test the implementation.
"""
import asyncio
import json
import os


async def test_enhancements():
    """Test the CoinGecko enhancements after bot initialization."""
    print("\n" + "=" * 80)
    print("Testing CoinGecko API Enhancements")
    print("=" * 80)
    
    # Check if cache file exists and has the new fields
    cache_file = 'data/market_data/coingecko_global.json'
    
    if not os.path.exists(cache_file):
        print("\n⚠ Cache file doesn't exist yet. Run the bot to generate it.")
        return False
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            cached = json.load(f)
        
        data = cached.get('data', {})
        
        print("\n✅ Cache Structure Check:")
        print(f"  - market_cap: {'✅' if data.get('market_cap') else '❌'}")
        print(f"  - volume: {'✅' if data.get('volume') else '❌'}")
        print(f"  - dominance: {'✅' if data.get('dominance') else '❌'}")
        print(f"  - stats: {'✅' if data.get('stats') else '❌'}")
        print(f"  - top_coins: {'✅' if data.get('top_coins') else '❌'}")
        print(f"  - defi: {'✅' if data.get('defi') else '❌'}")
        
        # Show top coins sample
        if data.get('top_coins'):
            print(f"\n✅ Top Coins: {len(data['top_coins'])} retrieved")
            for i, coin in enumerate(data['top_coins'][:3], 1):
                symbol = coin.get('symbol', '?').upper()
                price = coin.get('current_price', 0)
                change = coin.get('price_change_percentage_24h', 0)
                ath_pct = coin.get('ath_change_percentage', 0)
                print(f"  {i}. {symbol}: ${price:,.2f} (24h: {change:+.2f}%, ATH: {ath_pct:+.1f}%)")
        else:
            print("\n❌ No top_coins data in cache")
        
        # Show DeFi data
        if data.get('defi'):
            defi = data['defi']
            print(f"\n✅ DeFi Data:")
            mcap = float(defi.get('defi_market_cap', 0))
            dom = float(defi.get('defi_dominance', 0))
            print(f"  - DeFi Market Cap: ${mcap:,.0f}")
            print(f"  - DeFi Dominance: {dom:.2f}%")
            print(f"  - Top DeFi Asset: {defi.get('top_coin_name', 'N/A')}")
        else:
            print("\n❌ No DeFi data in cache")
        
        print("\n" + "=" * 80)
        
        # Return success if both new fields exist
        has_top_coins = bool(data.get('top_coins'))
        has_defi = bool(data.get('defi'))
        
        if has_top_coins and has_defi:
            print("✅ SUCCESS: All enhancements working correctly!")
        elif has_top_coins or has_defi:
            print("⚠ PARTIAL: Some enhancements working")
        else:
            print("❌ FAILED: Enhancements not present in cache")
        
        print("=" * 80 + "\n")
        
        return has_top_coins and has_defi
        
    except Exception as e:
        print(f"\n❌ Error testing enhancements: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if os.name == 'nt':  # Windows
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    result = asyncio.run(test_enhancements())
    exit(0 if result else 1)
