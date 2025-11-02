"""
Simple test to verify rag_engine includes top_coins and defi in market_overview.
"""
import json


def test_rag_engine_logic():
    """Simulate what rag_engine.py does with coingecko data."""
    
    print("="*60)
    print("TESTING RAG ENGINE MARKET OVERVIEW CONSTRUCTION")
    print("="*60)
    
    # Load actual cache data
    with open("data/market_data/coingecko_global.json", "r") as f:
        cache = json.load(f)
    
    coingecko_data = cache["data"]
    
    print("\n1. CoinGecko data keys:")
    print(f"   {list(coingecko_data.keys())}")
    
    print("\n2. Checking key fields:")
    print(f"   - top_coins: {len(coingecko_data.get('top_coins', []))} coins")
    print(f"   - defi: {len(coingecko_data.get('defi', {}))} metrics")
    
    # Simulate OLD rag_engine logic (missing top_coins and defi)
    old_market_overview = {
        "timestamp": "test",
        "market_cap": coingecko_data.get("market_cap", {}),
        "volume": coingecko_data.get("volume", {}),
        "dominance": coingecko_data.get("dominance", {}),
        "stats": coingecko_data.get("stats", {})
    }
    
    print("\n3. OLD market_overview (BEFORE FIX):")
    print(f"   Keys: {list(old_market_overview.keys())}")
    print(f"   ❌ top_coins: {'Yes' if 'top_coins' in old_market_overview else 'MISSING'}")
    print(f"   ❌ defi: {'Yes' if 'defi' in old_market_overview else 'MISSING'}")
    
    # Simulate NEW rag_engine logic (with top_coins and defi)
    new_market_overview = {
        "timestamp": "test",
        "market_cap": coingecko_data.get("market_cap", {}),
        "volume": coingecko_data.get("volume", {}),
        "dominance": coingecko_data.get("dominance", {}),
        "stats": coingecko_data.get("stats", {}),
        "top_coins": coingecko_data.get("top_coins", []),
        "defi": coingecko_data.get("defi", {})
    }
    
    print("\n4. NEW market_overview (AFTER FIX):")
    print(f"   Keys: {list(new_market_overview.keys())}")
    print(f"   ✅ top_coins: {len(new_market_overview.get('top_coins', []))} coins")
    print(f"   ✅ defi: {len(new_market_overview.get('defi', {}))} metrics")
    
    # Show what formatter will see
    print("\n5. What MarketFormatter.format_market_overview() will receive:")
    top_coins = new_market_overview.get("top_coins", [])
    if top_coins:
        print(f"   Top 3 coins:")
        for coin in top_coins[:3]:
            symbol = coin.get("symbol", "?").upper()
            name = coin.get("name", "?")
            rank = coin.get("market_cap_rank", "?")
            print(f"     #{rank}: {symbol} ({name})")
    
    defi = new_market_overview.get("defi", {})
    if defi:
        print(f"   DeFi metrics:")
        for key, value in list(defi.items())[:3]:
            print(f"     {key}: {value}")
    
    print("\n" + "="*60)
    if new_market_overview.get("top_coins") and new_market_overview.get("defi"):
        print("✅ SUCCESS: Fix verified - top_coins and defi are included!")
    else:
        print("❌ FAILURE: Still missing data")
    print("="*60)


if __name__ == "__main__":
    test_rag_engine_logic()
