"""
Quick test to verify market overview includes top_coins and defi data.
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from src.platforms.coingecko import CoinGeckoAPI
from src.logger.logger import Logger


async def test_market_overview():
    """Test that market overview contains all expected fields."""
    logger = Logger("Test")
    
    # Initialize CoinGecko API
    coingecko = CoinGeckoAPI(logger=logger)
    
    print("Fetching market overview data...")
    market_data = await coingecko.get_global_market_data()
    
    print("\n" + "="*60)
    print("MARKET DATA STRUCTURE CHECK")
    print("="*60)
    
    # Check for expected top-level keys
    expected_keys = ["market_cap", "volume", "dominance", "stats", "top_coins", "defi"]
    
    for key in expected_keys:
        if key in market_data:
            if key == "top_coins":
                coin_count = len(market_data[key]) if market_data[key] else 0
                print(f"✅ {key}: Present ({coin_count} coins)")
                if coin_count > 0:
                    first_coin = market_data[key][0]
                    print(f"   Example: {first_coin.get('symbol', '?').upper()} - {first_coin.get('name', '?')}")
            elif key == "defi":
                defi_keys = list(market_data[key].keys()) if market_data[key] else []
                print(f"✅ {key}: Present ({len(defi_keys)} metrics)")
                if defi_keys:
                    print(f"   Metrics: {', '.join(defi_keys[:3])}")
            else:
                print(f"✅ {key}: Present")
        else:
            print(f"❌ {key}: MISSING")
    
    print("\n" + "="*60)
    print("SIMULATING RAG ENGINE DATA FLOW")
    print("="*60)
    
    # Simulate what rag_engine.py does
    market_overview = {
        "timestamp": "test",
        "summary": "CRYPTO MARKET OVERVIEW",
        "published_on": 0,
        "data_sources": ["coingecko_global"],
        "market_cap": market_data.get("market_cap", {}),
        "volume": market_data.get("volume", {}),
        "dominance": market_data.get("dominance", {}),
        "stats": market_data.get("stats", {}),
        "top_coins": market_data.get("top_coins", []),
        "defi": market_data.get("defi", {})
    }
    
    print(f"Market overview has {len(market_overview.get('top_coins', []))} top coins")
    print(f"Market overview has {len(market_overview.get('defi', {}))} DeFi metrics")
    
    if market_overview.get("top_coins") and market_overview.get("defi"):
        print("\n✅ SUCCESS: Market overview includes top_coins and defi!")
    else:
        print("\n❌ FAILURE: Missing top_coins or defi in market overview")
    
    await coingecko.close()


if __name__ == "__main__":
    asyncio.run(test_market_overview())
