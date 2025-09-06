from typing import Dict, List, Any

import aiohttp

from config.config import CRYPTOCOMPARE_API_KEY, RAG_PRICE_API_URL
from src.logger.logger import Logger
from src.utils.decorators import retry_api_call


class CryptoCompareMarketAPI:
    """
    Handles CryptoCompare market data API operations including price data and OHLCV data
    """
    
    OHLCV_API_URL_TEMPLATE = f"https://min-api.cryptocompare.com/data/v2/histo{{timeframe}}?fsym={{base}}&tsym={{quote}}&limit={{limit}}&api_key={CRYPTOCOMPARE_API_KEY}"
    
    def __init__(self, logger: Logger) -> None:
        self.logger = logger
    
    @retry_api_call(max_retries=3)
    async def get_multi_price_data(
        self, 
        coins: List[str] = None, 
        vs_currencies: List[str] = None
    ) -> Dict[str, Any]:
        """
        Get price data for multiple coins
        
        Args:
            coins: List of coin symbols (default: BTC,ETH,XRP,LTC,BCH,BNB,ADA,DOT,LINK)
            vs_currencies: List of fiat currencies (default: USD)
            
        Returns:
            Dictionary with price data
        """
        default_coins = ["BTC", "ETH", "XRP", "LTC", "BCH", "BNB", "ADA", "DOT", "LINK"]
        default_currencies = ["USD"]
        
        # Use defaults if not provided
        fsyms = coins if coins else default_coins
        tsyms = vs_currencies if vs_currencies else default_currencies
        
        # Build URL: use canonical config URL when caller doesn't provide coins or currencies
        if coins is None and vs_currencies is None:
            url = RAG_PRICE_API_URL
        else:
            url = f"https://min-api.cryptocompare.com/data/pricemultifull?fsyms={','.join(fsyms)}&tsyms={','.join(tsyms)}&api_key={CRYPTOCOMPARE_API_KEY}"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=30) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data and "RAW" in data:
                            return data
                        else:
                            self.logger.warning("Price data response missing RAW field")
                            return {}
                    else:
                        self.logger.error(f"Price API request failed with status {resp.status}")
                        return {}
            except Exception as e:
                self.logger.error(f"Error fetching price data: {e}")
                return {}
    
    def get_ohlcv_url_template(self) -> str:
        """Get the OHLCV API URL template"""
        return self.OHLCV_API_URL_TEMPLATE
