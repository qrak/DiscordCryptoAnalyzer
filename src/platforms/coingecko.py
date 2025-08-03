import asyncio
import json
import os
from datetime import datetime, timedelta
from os.path import exists, getsize
from typing import Dict, List, Any, Literal, Optional

from aiohttp_client_cache import CachedSession, SQLiteBackend

from src.logger.logger import Logger
from src.utils.decorators import retry_api_call


class CacheData(Dict[str, Any]):
    """Type for cached data with timestamp and data"""
    pass


class CoinGeckoAPI:
    GLOBAL_API_URL = "https://api.coingecko.com/api/v3/global"
    COINS_LIST_URL = "https://api.coingecko.com/api/v3/coins/list"
    COIN_DATA_URL_TEMPLATE = "https://api.coingecko.com/api/v3/coins/{coin_id}"
    
    def __init__(
        self,
        logger: Logger,
        cache_name: str = 'cache/coingecko_cache.db',
        cache_dir: str = 'data/market_data',
        expire_after: int = -1
    ) -> None:
        self.cache_backend = SQLiteBackend(cache_name=cache_name, expire_after=expire_after)
        self.session: Optional[CachedSession] = None
        self.symbol_to_id_map: Dict[str, List[Dict[str, str]]] = {}
        self.logger = logger
        self.cache_dir = cache_dir
        self.coingecko_cache_file = os.path.join(self.cache_dir, "coingecko_global.json")
        self.update_interval = timedelta(hours=4)  # Default update interval
        self.last_update: Optional[datetime] = None

        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)

    async def initialize(self) -> None:
        """Initialize the API client and load cached data"""
        await self.initialize_coin_mappings()
        
        # Check if we have cached global data
        if os.path.exists(self.coingecko_cache_file):
            try:
                with open(self.coingecko_cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    if "timestamp" in cached_data:
                        self.last_update = datetime.fromisoformat(cached_data["timestamp"])
                        self.logger.debug(f"Loaded CoinGecko cache from {self.last_update.isoformat()}")
            except Exception as e:
                self.logger.error(f"Error loading CoinGecko cache: {e}")

    async def initialize_coin_mappings(self) -> None:
        """
        Initialize coin mappings from CoinGecko API.
        This method is kept separate for backward compatibility with app.py.
        """
        try:
            if self.session:
                await self.session.close()

            self.session = CachedSession(cache=self.cache_backend)
            coins = await self._fetch_all_coins()
            if coins:
                self._update_symbol_map(coins)
                self.logger.info(f"Loaded {len(self.symbol_to_id_map)} unique symbols from coingecko.")
                self._log_cache_info()
        except Exception as e:
            self.logger.error(f"Error initializing coin mappings: {e}")
            self.symbol_to_id_map = {}

    async def get_coin_image(self,
                             base_symbol: str,
                             exchange_name: str,
                             size: Literal['thumb', 'small', 'large'] = 'small') -> str:
        try:
            base_symbol = base_symbol.upper()
            coin_data_list = self.symbol_to_id_map.get(base_symbol, [])
            if not coin_data_list:
                return ''

            if not self.session:
                self.session = CachedSession(cache=self.cache_backend)

            for coin_data in coin_data_list:
                coin_info = await self._fetch_coin_data(coin_data['id'])
                if self._coin_traded_on_exchange(coin_info, exchange_name):
                    image_url = coin_info.get('image', {}).get(size, '')
                    if image_url:
                        coin_data['image'] = image_url
                        return image_url

            if coin_data_list:
                first_coin_data = coin_data_list[0]
                if first_coin_data.get('image'):
                    return first_coin_data['image']

                coin_info = await self._fetch_coin_data(first_coin_data['id'])
                image_url = coin_info.get('image', {}).get(size, '')
                if image_url:
                    first_coin_data['image'] = image_url
                    return image_url

        except Exception as e:
            self.logger.error(f"Error fetching coin image for {base_symbol} on {exchange_name}: {e}")
        return ''

    @retry_api_call(max_retries=3)
    async def get_global_market_data(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get global market data from CoinGecko.
        
        Args:
            force_refresh: If True, bypass cache and fetch fresh data
        
        Returns:
            Dictionary containing processed market data
        """
        current_time = datetime.now()
        
        # Check if we should use cached data
        if not force_refresh and self.last_update and \
           current_time - self.last_update < self.update_interval:
            try:
                with open(self.coingecko_cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    if "data" in cached_data:
                        self.logger.debug(f"Using cached CoinGecko data from {self.last_update.isoformat()}")
                        return cached_data["data"]
            except Exception as e:
                self.logger.warning(f"Failed to read cached data: {e}")
        
        # Fetch fresh data
        self.logger.debug("Fetching fresh CoinGecko global data")
        if not self.session:
            self.session = CachedSession(cache=self.cache_backend)
            
        try:
            async with self.session.get(self.GLOBAL_API_URL) as response:
                if response.status == 200:
                    api_data = await response.json()
                    processed_data = self._process_global_data(api_data)
                    
                    # Save to cache
                    cache_data = {
                        "timestamp": current_time.isoformat(),
                        "data": processed_data
                    }
                    with open(self.coingecko_cache_file, 'w', encoding='utf-8') as f:
                        json.dump(cache_data, f, ensure_ascii=False, indent=2)
                    
                    self.last_update = current_time
                    self.logger.debug("Updated CoinGecko global data cache")
                    return processed_data
                else:
                    self.logger.error(f"Failed to fetch global data. Status: {response.status}")
                    # Try to return cached data as fallback
                    return await self._get_cached_global_data()
        except Exception as e:
            self.logger.error(f"Error fetching global market data: {e}")
            return await self._get_cached_global_data()
    
    async def _get_cached_global_data(self) -> Dict[str, Any]:
        """Retrieve cached global data as fallback"""
        try:
            if os.path.exists(self.coingecko_cache_file):
                with open(self.coingecko_cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    if "data" in cached_data:
                        self.logger.warning("Using cached CoinGecko global data as fallback")
                        return cached_data["data"]
        except Exception as e:
            self.logger.error(f"Error reading cached global data: {e}")
        
        # Return empty dict if cache read fails
        return {}
    
    def _process_global_data(self, api_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process raw API data into a standardized format"""
        if not api_data or "data" not in api_data:
            return {}
            
        data = api_data["data"]
        
        return {
            "market_cap": {
                "total_usd": data.get("total_market_cap", {}).get("usd", 0),
                "change_24h": data.get("market_cap_change_percentage_24h_usd", 0)
            },
            "volume": {
                "total_usd": data.get("total_volume", {}).get("usd", 0)
            },
            "dominance": data.get("market_cap_percentage", {}),
            "stats": {
                "active_coins": data.get("active_cryptocurrencies", 0),
                "active_markets": data.get("markets", 0)
            }
        }
    
    @retry_api_call(max_retries=2)
    async def get_market_cap_data(self) -> Dict[str, Any]:
        """Get market cap specific data"""
        market_data = await self.get_global_market_data()
        if not market_data:
            return {}
            
        return {
            "total_market_cap": market_data.get("market_cap", {}).get("total_usd", 0),
            "market_cap_change_24h": market_data.get("market_cap", {}).get("change_24h", 0),
            "total_volume_24h": market_data.get("volume", {}).get("total_usd", 0)
        }
    
    @retry_api_call(max_retries=2)
    async def get_coin_dominance(self, limit: int = 5) -> Dict[str, float]:
        """
        Get coin dominance percentages
        
        Args:
            limit: Number of top coins to include
            
        Returns:
            Dictionary mapping coin symbols to dominance percentages
        """
        market_data = await self.get_global_market_data()
        if not market_data or "dominance" not in market_data:
            return {}
            
        dominance = market_data["dominance"]
        # Sort by dominance percentage and take top 'limit' coins
        sorted_coins = sorted(dominance.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_coins[:limit])
        
    async def _fetch_all_coins(self) -> List[Dict[str, str]]:
        if not self.session:
            self.session = CachedSession(cache=self.cache_backend)
            
        async with self.session.get(self.COINS_LIST_URL) as response:
            if response.status == 200:
                return await response.json()
            else:
                self.logger.error(f"Failed to fetch coin list. Status: {response.status}")
                return []

    @retry_api_call(max_retries=2)
    async def _fetch_coin_data(self, coin_id: str) -> Dict[str, Any]:
        if not self.session:
            self.session = CachedSession(cache=self.cache_backend)
            
        url = self.COIN_DATA_URL_TEMPLATE.format(coin_id=coin_id)
        async with self.session.get(url) as response:
            if response.status == 200:
                return await response.json()
            return {}

    def _update_symbol_map(self, coins: List[Dict[str, str]]) -> None:
        for coin in coins:
            symbol = coin['symbol'].upper()
            if symbol not in self.symbol_to_id_map:
                self.symbol_to_id_map[symbol] = []
            self.symbol_to_id_map[symbol].append({
                'id': coin['id'],
                'name': coin['name'],
                'image': ''
            })

    @staticmethod
    def _coin_traded_on_exchange(coin_data: Dict[str, Any], exchange_name: str) -> bool:
        return any(
            ticker.get('market', {}).get('name') == exchange_name
            for ticker in coin_data.get('tickers', [])
        )

    def _log_cache_info(self) -> None:
        cache_file_path = self.cache_backend.name
        if exists(cache_file_path):
            cache_size = getsize(cache_file_path)
            cache_size_mb = cache_size / (1024 * 1024)
            self.logger.info(f"Cache file size: {cache_size_mb:.2f} MB")
        else:
            self.logger.info("Cache file does not exist yet.")

    async def close(self) -> None:
        if self.session:
            try:
                await asyncio.wait_for(self.session.close(), timeout=1.0)
            except asyncio.TimeoutError:
                self.logger.error("CoinGecko session close timed out")
            except Exception as e:
                self.logger.error(f"Error closing CoinGecko session: {e}")
            finally:
                self.session = None