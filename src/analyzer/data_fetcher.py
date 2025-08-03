from typing import Optional, Tuple, Dict, Any, List
import time

import numpy as np
from numpy.typing import NDArray

from src.logger.logger import Logger
from src.utils.decorators import retry_async


class DataFetcher:
    def __init__(self, exchange, logger: Logger):
        self.exchange = exchange
        self.logger: Logger = logger
        self.ticker_cache = {}
        self.cache_ttl = 3600  # Cache data for 1 hour

    @retry_async()
    async def fetch_candlestick_data(self,
                                     pair: str,
                                     timeframe: str,
                                     limit: int,
                                     start_time: Optional[int] = None
                                     ) -> Optional[Tuple[NDArray, float]]:
        self.logger.debug(f"Fetching {pair} OHLCV data on {timeframe} timeframe with limit {limit}")
        
        if limit > 1000:
            self.logger.warning(f"Requested limit {limit} exceeds exchange standard limits, may be truncated")
            
        ohlcv = await self.exchange.fetch_ohlcv(pair, timeframe, since=start_time, limit=limit + 1)

        if ohlcv is None or len(ohlcv) == 0:
            self.logger.warning(f"No data returned for {pair} on {self.exchange.id}")
            return None
        
        self.logger.debug(f"Received {len(ohlcv)} raw candles from exchange for {pair}")
        
        ohlcv_array = np.array(ohlcv)
        closed_candles = ohlcv_array[:-1]
        latest_close = float(ohlcv_array[-1, 4])
        
        self.logger.debug(f"Processed {len(closed_candles)} closed candles, latest close: {latest_close}")
        
        # Verify we have enough data
        if len(closed_candles) < min(720, limit - 1):
            self.logger.warning(f"Received fewer candles ({len(closed_candles)}) than expected ({min(720, limit - 1)})")
            self.logger.debug(f"First candle timestamp: {closed_candles[0][0] if len(closed_candles) > 0 else 'N/A'}")
            self.logger.debug(f"Last candle timestamp: {closed_candles[-1][0] if len(closed_candles) > 0 else 'N/A'}")

        return closed_candles, latest_close

    @retry_async()
    async def fetch_daily_historical_data(self,
                                         pair: str,
                                         days: int = 365
                                         ) -> Dict[str, Any]:
        """
        Fetch historical daily data for a specified number of days.
        
        Args:
            pair: The trading pair to fetch data for
            days: Number of days of historical data to retrieve (default: 365)
            
        Returns:
            Dict containing:
                'data': NDArray of OHLCV data if available, or None
                'latest_close': Latest closing price
                'available_days': Number of days of data actually available
                'is_complete': Boolean indicating if we have full history for requested period
        """
        self.logger.debug(f"Fetching historical daily data for {pair}, {days} days")
        
        try:
            result = await self.fetch_candlestick_data(
                pair=pair,
                timeframe="1d",
                limit=days
            )
            
            if result is None:
                self.logger.warning(f"No daily historical data available for {pair}")
                return {
                    'data': None,
                    'latest_close': None,
                    'available_days': 0,
                    'is_complete': False,
                    'error': "No data returned from exchange"
                }
                
            ohlcv_data, latest_close = result
            available_days = len(ohlcv_data)
            is_complete = (available_days >= days - 1)  # Account for the +1 in fetch_candlestick_data
            
            if not is_complete:
                self.logger.info(f"Limited historical data for {pair}: requested {days} days, got {available_days} days")
            else:
                self.logger.debug(f"Successfully fetched {available_days} days of historical data for {pair}")
                
            return {
                'data': ohlcv_data,
                'latest_close': latest_close,
                'available_days': available_days,
                'is_complete': is_complete,
                'error': None
            }
            
        except Exception as e:
            self.logger.error(f"Error fetching daily historical data for {pair}: {str(e)}")
            return {
                'data': None,
                'latest_close': None,
                'available_days': 0,
                'is_complete': False,
                'error': str(e)
            }

    @retry_async()
    async def fetch_multiple_tickers(self, symbols: List[str] = None) -> Dict[str, Any]:
        """
        Fetch price data for multiple trading pairs at once using CCXT with caching
        
        Args:
            symbols: List of trading pair symbols (e.g., ["BTC/USDT", "ETH/USDT"])
                    If None, fetches all available tickers
                    
        Returns:
            Dictionary with processed ticker data in a format similar to CryptoCompare API
        """
        # Try to get from cache first
        cache_key = 'all' if symbols is None else ','.join(sorted(symbols))
        current_time = time.time()
        
        if cache_key in self.ticker_cache:
            cache_entry = self.ticker_cache[cache_key]
            if current_time - cache_entry['timestamp'] < self.cache_ttl:
                self.logger.debug(f"Using cached ticker data for {cache_key} (age: {int(current_time - cache_entry['timestamp'])}s)")
                return cache_entry['data']
                
        self.logger.debug(f"Fetching multiple tickers: {symbols if symbols else 'all'}")
        
        try:
            # Check if exchange supports fetch_tickers
            if not self.exchange.has.get('fetchTickers', False):
                self.logger.warning(f"Exchange {self.exchange.id} does not support fetchTickers")
                return {}
            
            # Fetch tickers from exchange
            tickers = await self.exchange.fetch_tickers(symbols)
            
            if not tickers:
                self.logger.warning("No ticker data returned from exchange")
                return {}
                
            # Process the ticker data into a similar format as CryptoCompare API
            result = {
                "RAW": {},
                "DISPLAY": {}
            }
            
            for symbol, ticker in tickers.items():
                # Extract base currency from symbol
                if '/' in symbol:
                    base_currency = symbol.split('/')[0]
                    quote_currency = symbol.split('/')[1]
                else:
                    # Skip if we can't determine base/quote
                    continue
                    
                # Only process if we have the necessary data
                if 'last' not in ticker or ticker['last'] is None:
                    continue
                    
                # Initialize structure if needed
                if base_currency not in result["RAW"]:
                    result["RAW"][base_currency] = {}
                if base_currency not in result["DISPLAY"]:
                    result["DISPLAY"][base_currency] = {}
                    
                # Populate RAW data with enhanced fields
                result["RAW"][base_currency][quote_currency] = {
                    "PRICE": ticker.get('last', 0),
                    "CHANGEPCT24HOUR": ticker.get('percentage', 0),
                    "CHANGE24HOUR": ticker.get('change', 0),
                    "VOLUME24HOUR": ticker.get('baseVolume', 0),
                    "MKTCAP": None,  # Market cap not typically available in CCXT ticker
                    "LASTUPDATE": ticker.get('timestamp', 0),
                    "HIGH24HOUR": ticker.get('high', 0),
                    "LOW24HOUR": ticker.get('low', 0),
                    # Additional fields added from CCXT data
                    "VWAP": ticker.get('vwap', 0),
                    "BID": ticker.get('bid', 0),
                    "ASK": ticker.get('ask', 0),
                    "BIDVOLUME": ticker.get('bidVolume', 0),
                    "ASKVOLUME": ticker.get('askVolume', 0),
                    "OPEN24HOUR": ticker.get('open', 0),
                    "PREVCLOSE": ticker.get('previousClose', 0),
                    "QUOTEVOLUME24HOUR": ticker.get('quoteVolume', 0),
                    "AVERAGE": ticker.get('average', 0)
                }
                
                # Populate DISPLAY data with formatted values
                result["DISPLAY"][base_currency][quote_currency] = {
                    "PRICE": f"$ {ticker.get('last', 0):,.2f}" if quote_currency in ("USD", "USDT") else f"{ticker.get('last', 0):,.8f}",
                    "CHANGEPCT24HOUR": f"{ticker.get('percentage', 0):,.2f}",
                    "VOLUME24HOUR": f"{ticker.get('baseVolume', 0):,.2f}",
                    "HIGH24HOUR": f"{ticker.get('high', 0):,.2f}" if quote_currency in ("USD", "USDT") else f"{ticker.get('high', 0):,.8f}",
                    "LOW24HOUR": f"{ticker.get('low', 0):,.2f}" if quote_currency in ("USD", "USDT") else f"{ticker.get('low', 0):,.8f}",
                    # Additional display fields
                    "VWAP": f"$ {ticker.get('vwap', 0):,.2f}" if quote_currency in ("USD", "USDT") else f"{ticker.get('vwap', 0):,.8f}",
                    "BID": f"$ {ticker.get('bid', 0):,.2f}" if quote_currency in ("USD", "USDT") else f"{ticker.get('bid', 0):,.8f}",
                    "ASK": f"$ {ticker.get('ask', 0):,.2f}" if quote_currency in ("USD", "USDT") else f"{ticker.get('ask', 0):,.8f}",
                }
            
            # Store result in cache before returning
            self.ticker_cache[cache_key] = {
                'timestamp': current_time,
                'data': result
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error fetching multiple tickers: {e}")
            return {}

