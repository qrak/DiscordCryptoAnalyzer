from typing import Optional, Tuple, Dict, Any, List
import time

import numpy as np
from numpy.typing import NDArray

from src.logger.logger import Logger
from src.utils.decorators import retry_async
from src.utils.timeframe_validator import TimeframeValidator


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
        
        # Validate timeframe is supported by exchange
        if hasattr(self.exchange, 'timeframes') and self.exchange.timeframes:
            if timeframe not in self.exchange.timeframes:
                self.logger.error(
                    f"Timeframe {timeframe} not supported by {self.exchange.id}. "
                    f"Supported: {', '.join(self.exchange.timeframes.keys())}"
                )
                return None
        elif not TimeframeValidator.is_ccxt_compatible(timeframe):
            self.logger.warning(
                f"Timeframe {timeframe} may not be supported by {self.exchange.id}. "
                f"Attempting fetch anyway..."
            )
        
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
        cache_key = self._get_cache_key(symbols)
        
        # Try cache first
        cached_data = self._get_cached_tickers(cache_key)
        if cached_data is not None:
            return cached_data
        
        self.logger.debug(f"Fetching multiple tickers: {symbols if symbols else 'all'}")
        
        try:
            # Validate exchange capabilities
            if not self._validate_exchange_support():
                return {}
            
            # Fetch and process ticker data
            tickers = await self.exchange.fetch_tickers(symbols)
            if not tickers:
                self.logger.warning("No ticker data returned from exchange")
                return {}
            
            result = self._process_ticker_data(tickers)
            self._cache_ticker_data(cache_key, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error fetching multiple tickers: {e}")
            return {}

    def _get_cache_key(self, symbols: List[str] = None) -> str:
        """Generate cache key for ticker data."""
        return 'all' if symbols is None else ','.join(sorted(symbols))

    def _get_cached_tickers(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached ticker data if available and valid."""
        current_time = time.time()
        
        if cache_key not in self.ticker_cache:
            return None
            
        cache_entry = self.ticker_cache[cache_key]
        if current_time - cache_entry['timestamp'] >= self.cache_ttl:
            return None
            
        self.logger.debug(
            f"Using cached ticker data for {cache_key} "
            f"(age: {int(current_time - cache_entry['timestamp'])}s)"
        )
        return cache_entry['data']

    def _validate_exchange_support(self) -> bool:
        """Validate that the exchange supports the required operations."""
        if not self.exchange.has.get('fetchTickers', False):
            self.logger.warning(f"Exchange {self.exchange.id} does not support fetchTickers")
            return False
        return True

    def _process_ticker_data(self, tickers: Dict[str, Any]) -> Dict[str, Any]:
        """Process ticker data into CryptoCompare-like format."""
        result = {"RAW": {}, "DISPLAY": {}}
        
        for symbol, ticker in tickers.items():
            base_currency, quote_currency = self._extract_currencies(symbol)
            if not base_currency or not quote_currency:
                continue
                
            if not self._has_required_ticker_data(ticker):
                continue
                
            self._add_ticker_to_result(result, base_currency, quote_currency, ticker)
        
        return result

    def _extract_currencies(self, symbol: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract base and quote currencies from symbol."""
        if '/' not in symbol:
            return None, None
        parts = symbol.split('/', 1)
        return parts[0], parts[1]

    def _has_required_ticker_data(self, ticker: Dict[str, Any]) -> bool:
        """Check if ticker has required data fields."""
        return 'last' in ticker and ticker['last'] is not None

    def _add_ticker_to_result(self, result: Dict[str, Any], base_currency: str, 
                            quote_currency: str, ticker: Dict[str, Any]) -> None:
        """Add processed ticker data to result structure."""
        # Initialize structure if needed
        if base_currency not in result["RAW"]:
            result["RAW"][base_currency] = {}
        if base_currency not in result["DISPLAY"]:
            result["DISPLAY"][base_currency] = {}
        
        # Add RAW data
        result["RAW"][base_currency][quote_currency] = self._create_raw_ticker_data(ticker)
        
        # Add DISPLAY data
        result["DISPLAY"][base_currency][quote_currency] = self._create_display_ticker_data(
            ticker, quote_currency
        )

    def _create_raw_ticker_data(self, ticker: Dict[str, Any]) -> Dict[str, Any]:
        """Create raw ticker data structure."""
        return {
            "PRICE": ticker.get('last', 0),
            "CHANGEPCT24HOUR": ticker.get('percentage', 0),
            "CHANGE24HOUR": ticker.get('change', 0),
            "VOLUME24HOUR": ticker.get('baseVolume', 0),
            "MKTCAP": None,  # Market cap not typically available in CCXT ticker
            "LASTUPDATE": ticker.get('timestamp', 0),
            "HIGH24HOUR": ticker.get('high', 0),
            "LOW24HOUR": ticker.get('low', 0),
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

    def _create_display_ticker_data(self, ticker: Dict[str, Any], quote_currency: str) -> Dict[str, Any]:
        """Create display ticker data structure with formatted values."""
        is_usd_quote = quote_currency in ("USD", "USDT")
        
        def format_price(value: float) -> str:
            if is_usd_quote:
                return f"$ {value:,.2f}"
            return f"{value:,.8f}"
        
        return {
            "PRICE": format_price(ticker.get('last', 0)),
            "CHANGEPCT24HOUR": f"{ticker.get('percentage', 0):,.2f}",
            "VOLUME24HOUR": f"{ticker.get('baseVolume', 0):,.2f}",
            "HIGH24HOUR": format_price(ticker.get('high', 0)),
            "LOW24HOUR": format_price(ticker.get('low', 0)),
            "VWAP": format_price(ticker.get('vwap', 0)),
            "BID": format_price(ticker.get('bid', 0)),
            "ASK": format_price(ticker.get('ask', 0)),
        }

    def _cache_ticker_data(self, cache_key: str, data: Dict[str, Any]) -> None:
        """Store ticker data in cache."""
        self.ticker_cache[cache_key] = {
            'timestamp': time.time(),
            'data': data
        }

