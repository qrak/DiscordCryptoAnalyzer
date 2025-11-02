"""
Minimal test for CoinGecko API enhancements.
This only initializes the CoinGeckoAPI component.
"""
import asyncio
import sys
import os

# Change to project root
os.chdir(os.path.dirname(os.path.abspath(__file__)))


async def main():
    """Test CoinGecko API directly."""
    print("\n" + "=" * 80)
    print("Minimal CoinGecko API Test")
    print("=" * 80)
    
    print("\n[1] Creating CoinGeckoAPI instance...")
    
    # Import and create directly
    from aiohttp_client_cache import CachedSession, SQLiteBackend
    import json
    from datetime import datetime
    
    # Create a minimal version inline to avoid imports
    class TestCoinGeckoAPI:
        GLOBAL_API_URL = "https://api.coingecko.com/api/v3/global"
        COINS_MARKETS_URL = "https://api.coingecko.com/api/v3/coins/markets"
        GLOBAL_DEFI_URL = "https://api.coingecko.com/api/v3/global/decentralized_finance_defi"
        
        def __init__(self):
            self.session = None
            self.cache_backend = SQLiteBackend(
                cache_name='cache/coingecko_cache.db',
                expire_after=-1
            )
        
        async def initialize(self):
            self.session = CachedSession(cache=self.cache_backend)
        
        def _get_dominance_coin_ids(self):
            symbol_to_id = {
                "btc": "bitcoin",
                "eth": "ethereum",
                "usdt": "tether",
                "xrp": "ripple",
                "bnb": "binancecoin",
                "sol": "solana",
                "usdc": "usd-coin",
                "steth": "staked-ether",
                "doge": "dogecoin",
                "trx": "tron"
            }
            return list(symbol_to_id.values())
        
        async def fetch_global(self):
            async with self.session.get(self.GLOBAL_API_URL) as response:
                if response.status == 200:
                    return await response.json()
                print(f"Failed to fetch global: {response.status}")
                return {}
        
        async def fetch_top_coins(self, coin_ids):
            if not coin_ids:
                return []
            
            ids_str = ",".join(coin_ids)
            params = {
                "vs_currency": "usd",
                "ids": ids_str,
                "order": "market_cap_desc",
                "per_page": 100,
                "page": 1,
                "sparkline": "false",
                "price_change_percentage": "1h,24h,7d",
                "precision": "2"
            }
            
            async with self.session.get(self.COINS_MARKETS_URL, params=params) as response:
                if response.status == 200:
                    return await response.json()
                print(f"Failed to fetch top coins: {response.status}")
                return []
        
        async def fetch_defi(self):
            async with self.session.get(self.GLOBAL_DEFI_URL) as response:
                if response.status == 200:
                    return await response.json()
                print(f"Failed to fetch DeFi: {response.status}")
                return {}
        
        async def close(self):
            if self.session:
                await self.session.close()
    
    api = TestCoinGeckoAPI()
    await api.initialize()
    
    print("[2] Fetching data from all three endpoints...")
    
    coin_ids = api._get_dominance_coin_ids()
    global_data, top_coins, defi_data = await asyncio.gather(
        api.fetch_global(),
        api.fetch_top_coins(coin_ids),
        api.fetch_defi(),
        return_exceptions=True
    )
    
    print("\n[3] Results:")
    print(f"  - Global data: {'✅' if global_data and not isinstance(global_data, Exception) else '❌'}")
    print(f"  - Top coins: {'✅' if top_coins and not isinstance(top_coins, Exception) else '❌'}")
    if top_coins and not isinstance(top_coins, Exception):
        print(f"    Number of coins: {len(top_coins)}")
    print(f"  - DeFi data: {'✅' if defi_data and not isinstance(defi_data, Exception) else '❌'}")
    
    # Show samples
    if top_coins and not isinstance(top_coins, Exception) and len(top_coins) > 0:
        print("\n[4] Top Coins Sample:")
        for i, coin in enumerate(top_coins[:3], 1):
            print(f"  {i}. {coin.get('symbol', '?').upper()}: ${coin.get('current_price', 0):,.2f}")
    
    if defi_data and not isinstance(defi_data, Exception) and 'data' in defi_data:
        print("\n[5] DeFi Data Sample:")
        data = defi_data['data']
        print(f"  - DeFi Market Cap: {data.get('defi_market_cap', 'N/A')}")
        print(f"  - Top DeFi: {data.get('top_coin_name', 'N/A')}")
    
    await api.close()
    
    print("\n" + "=" * 80)
    print("✅ Test Complete!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())
