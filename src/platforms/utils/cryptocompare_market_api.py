from typing import Dict, List, Any

import aiohttp

from config import CRYPTOCOMPARE_API_KEY, RAG_PRICE_API_URL
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
    
    @retry_api_call(max_retries=3)
    async def get_coin_details(self, symbol: str) -> Dict[str, Any]:
        """
        Get detailed coin information including description, taxonomy, and Weiss ratings
        
        Args:
            symbol: Cryptocurrency symbol (e.g., 'LINK', 'BTC')
            
        Returns:
            Dictionary with coin details including:
            - Description: Project description text
            - Algorithm: Consensus algorithm (e.g., "Proof of Work", "N/A")
            - ProofType: Proof mechanism type
            - Sponsored: Whether coin is sponsored on CryptoCompare
            - Taxonomy: Regulatory classifications (Access, FCA, FINMA, Industry, etc.)
            - Rating: Weiss ratings including overall, technology adoption, and market performance
        """
        url = f"https://min-api.cryptocompare.com/data/all/coinlist?fsym={symbol}&api_key={CRYPTOCOMPARE_API_KEY}"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=30) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data and data.get("Response") == "Success" and "Data" in data:
                            coin_data = data["Data"].get(symbol)
                            if coin_data:
                                # Extract the fields we need
                                return {
                                    "description": coin_data.get("Description", ""),
                                    "algorithm": coin_data.get("Algorithm", "N/A"),
                                    "proof_type": coin_data.get("ProofType", "N/A"),
                                    "sponsored": coin_data.get("Sponsored", False),
                                    "taxonomy": coin_data.get("Taxonomy", {}),
                                    "rating": coin_data.get("Rating", {}),
                                    "full_name": coin_data.get("FullName", ""),
                                    "coin_name": coin_data.get("CoinName", ""),
                                    "symbol": coin_data.get("Symbol", symbol),
                                    "is_trading": coin_data.get("IsTrading", True)
                                }
                            else:
                                self.logger.warning(f"No data found for symbol {symbol}")
                                return {}
                        else:
                            self.logger.warning(f"Coin details API response unsuccessful: {data.get('Message', 'Unknown error')}")
                            return {}
                    else:
                        self.logger.error(f"Coin details API request failed with status {resp.status}")
                        return {}
            except Exception as e:
                self.logger.error(f"Error fetching coin details for {symbol}: {e}")
                return {}
    
    def get_ohlcv_url_template(self) -> str:
        """Get the OHLCV API URL template"""
        return self.OHLCV_API_URL_TEMPLATE
