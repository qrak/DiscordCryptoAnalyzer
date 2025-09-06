"""
Market Data Management Module for RAG Engine

Handles fetching and processing of cryptocurrency market overview data.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from src.logger.logger import Logger
from src.rag.filehandler import RagFileHandler


class MarketDataManager:
    """Manages cryptocurrency market overview data and operations."""
    
    def __init__(self, logger: Logger, file_handler: RagFileHandler, 
                 coingecko_api=None, cryptocompare_api=None, symbol_manager=None):
        self.logger = logger
        self.file_handler = file_handler
        self.coingecko_api = coingecko_api
        self.cryptocompare_api = cryptocompare_api
        self.symbol_manager = symbol_manager
        
        # Market data storage
        self.current_market_overview: Optional[Dict[str, Any]] = None
        self.coingecko_last_update: Optional[datetime] = None
        
    async def load_cached_market_overview(self) -> Optional[Dict[str, Any]]:
        """Load cached market overview data from disk."""
        try:
            market_overview_file = self.file_handler.get_market_overview_path()
            self.current_market_overview = self.file_handler.load_json_file(market_overview_file)
            return self.current_market_overview
        except Exception as e:
            self.logger.error(f"Error loading cached market overview: {e}")
            return None
    
    async def fetch_market_overview(self) -> Optional[Dict[str, Any]]:
        """Fetch overall market data from various sources concurrently."""
        overview = {"timestamp": datetime.now().isoformat(), "summary": "CRYPTO MARKET OVERVIEW"}
        
        if not self.coingecko_api:
            self.logger.error("CoinGecko API client not initialized for market overview fetch")
            return None
            
        try:
            # Get global market data from CoinGecko
            coingecko_data = await self.coingecko_api.get_global_market_data()
            top_coins = self._extract_top_coins(coingecko_data)
            
            # Fetch price data for top coins
            price_data = await self._fetch_price_data(top_coins)
            
            # Build overview structure
            self._build_overview_structure(overview, price_data, coingecko_data)
            
            return self._finalize_overview(overview)
                
        except Exception as e:
            self.logger.error(f"Error fetching market overview: {e}")
            return None
    
    def _extract_top_coins(self, coingecko_data: Optional[Dict]) -> List[str]:
        """Extract top coins by dominance, excluding stablecoins."""
        top_coins = []
        stablecoins = ["USDT", "USDC", "BUSD", "DAI", "TUSD", "UST", "USDP", "GUSD"]
        
        if coingecko_data and "dominance" in coingecko_data:
            sorted_dominance = sorted(
                coingecko_data["dominance"].items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            
            for coin, _ in sorted_dominance:
                if coin.upper() not in stablecoins:
                    top_coins.append(coin.upper())
                    if len(top_coins) >= 5:
                        break
        
        if not top_coins:
            self.logger.warning("Could not determine top coins by dominance, using defaults")
            top_coins = ["BTC", "ETH", "BNB", "XRP", "ADA"]
        
        return top_coins
    
    async def _fetch_price_data(self, top_coins: List[str]) -> Optional[Dict]:
        """Fetch price data using CCXT or fallback to CryptoCompare."""
        # Try CCXT first if available
        price_data = await self._try_ccxt_price_data(top_coins)
        
        # Fallback to CryptoCompare
        if not price_data or not price_data.get("RAW"):
            if self.cryptocompare_api:
                self.logger.debug("Falling back to CryptoCompare API for price data")
                price_data = await self.cryptocompare_api.get_multi_price_data(coins=top_coins)
        
        return price_data
    
    async def _try_ccxt_price_data(self, top_coins: List[str]) -> Optional[Dict]:
        """Try to fetch price data using CCXT exchange."""
        if not (self.symbol_manager and self.symbol_manager.exchanges):
            return None
        
        from src.analyzer.data_fetcher import DataFetcher
        
        # Select best available exchange
        exchange = self._select_exchange()
        if not exchange:
            return None
        
        try:
            data_fetcher = DataFetcher(exchange=exchange, logger=self.logger)
            symbols = [f"{coin}/USDT" for coin in top_coins]
            self.logger.debug(f"Fetching data for top coins: {symbols}")
            
            price_data = await data_fetcher.fetch_multiple_tickers(symbols)
            self.logger.debug(f"Fetched price data for {len(symbols)} symbols using CCXT")
            return price_data
        except Exception as e:
            self.logger.warning(f"Failed to fetch ticker data via CCXT: {e}")
            return None
    
    def _select_exchange(self):
        """Select the best available exchange for market data."""
        # Prefer Binance if available
        if 'binance' in self.symbol_manager.exchanges:
            self.logger.debug("Using Binance exchange for market data")
            return self.symbol_manager.exchanges['binance']
        
        # Use first available exchange that supports fetch_tickers
        for exchange_id, exch in self.symbol_manager.exchanges.items():
            if exch.has.get('fetchTickers', False):
                self.logger.debug(f"Using {exchange_id} exchange for market data")
                return exch
        
        return None
    
    def _build_overview_structure(self, overview: Dict, price_data: Optional[Dict], coingecko_data: Optional[Dict]):
        """Build the overview data structure from fetched data."""
        # Process price data
        if price_data and "RAW" in price_data:
            overview["top_coins"] = {}
            for coin, values in price_data["RAW"].items():
                coin_overview = self._process_coin_data(values)
                if coin_overview:
                    overview["top_coins"][coin] = coin_overview
        
        # Add CoinGecko global market data
        if coingecko_data:
            overview.update(coingecko_data)
            self.coingecko_last_update = datetime.now()
    
    def _process_coin_data(self, values: Dict) -> Optional[Dict]:
        """Process individual coin data from price API response."""
        quote_data = None
        
        # Try to get USD data first, then USDT if USD not available
        if "USD" in values:
            quote_data = values["USD"]
        elif "USDT" in values:
            quote_data = values["USDT"]
        
        if not quote_data:
            return None
        
        coin_overview = {
            "price": quote_data.get("PRICE", 0),
            "change24h": quote_data.get("CHANGEPCT24HOUR", 0),
            "volume24h": quote_data.get("VOLUME24HOUR", 0),
            "mcap": quote_data.get("MKTCAP")
        }
        
        # Add optional data if available
        if "VWAP" in quote_data and quote_data["VWAP"]:
            coin_overview["vwap"] = quote_data["VWAP"]
        
        if "BID" in quote_data and "ASK" in quote_data:
            coin_overview["bid"] = quote_data["BID"]
            coin_overview["ask"] = quote_data["ASK"]
        
        return coin_overview
    
    def _finalize_overview(self, overview: Dict) -> Optional[Dict]:
        """Finalize and validate the market overview."""
        if overview.get("top_coins") or overview.get("market_cap"):
            overview["id"] = "market_overview"
            overview["title"] = "Crypto Market Overview"
            
            # Add descriptive comments to help models understand the data structure
            overview["_description"] = {
                "top_coins": "Price and metrics for leading cryptocurrencies",
                "market_cap": "Total cryptocurrency market capitalization and changes",
                "volume": "Total trading volume across all markets",
                "dominance": "Percentage share of total market cap by leading assets",
                "stats": "General statistics about cryptocurrency markets"
            }
            
            self.logger.debug("Market overview data fetched/processed.")
            return overview
        else:
            self.logger.error("Failed to fetch any market overview data.")
            return None
    
    async def update_market_overview_if_needed(self, max_age_hours: int = 24) -> bool:
        """Update market overview if needed based on age."""
        should_update = False
        
        if self.current_market_overview is None:
            should_update = True
        else:
            # Check if market overview is older than max_age_hours
            timestamp_field = self.current_market_overview.get('published_on', 
                                                             self.current_market_overview.get('timestamp', 0))
            timestamp = self._normalize_timestamp(timestamp_field)
            
            if timestamp:
                data_time = datetime.fromtimestamp(timestamp)
                current_time = datetime.now()
                
                if current_time - data_time > timedelta(hours=max_age_hours):
                    self.logger.debug(f"Market overview data is older than {max_age_hours} hours, refreshing")
                    should_update = True
        
        if should_update:
            try:
                self.logger.debug("Fetching market overview data")
                market_overview = await self.fetch_market_overview()
                if market_overview:
                    await self.save_market_overview(market_overview)
                    return True
                else:
                    self.logger.warning("No market overview data was available from data sources")
                    return False
            except Exception as e:
                self.logger.error(f"Error fetching market overview: {e}")
                return False
        
        return False
    
    async def save_market_overview(self, market_overview: Dict[str, Any]) -> None:
        """Save market overview data to file and update current cache."""
        try:
            market_overview["id"] = "market_overview"
            market_overview["title"] = "Crypto Market Overview"
            
            market_overview_file = self.file_handler.get_market_overview_path()
            self.file_handler.save_json_file(market_overview_file, market_overview)
            self.current_market_overview = market_overview
            self.logger.debug("Market overview updated and saved.")
        except Exception as e:
            self.logger.error(f"Error saving market overview: {e}")
    
    def _normalize_timestamp(self, timestamp_field: Union[int, float, str, None]) -> float:
        """Convert various timestamp formats to a float timestamp."""
        if timestamp_field is None:
            return 0.0

        if isinstance(timestamp_field, (int, float)):
            return float(timestamp_field)
        elif isinstance(timestamp_field, str):
            try:
                if timestamp_field.endswith('Z'):
                    timestamp_field = timestamp_field[:-1] + '+00:00'
                return datetime.fromisoformat(timestamp_field).timestamp()
            except ValueError:
                self.logger.warning(f"Could not normalize timestamp string: {timestamp_field}")
                return 0.0
            except Exception as e:
                self.logger.error(f"Error normalizing timestamp string '{timestamp_field}': {e}")
                return 0.0
        return 0.0
    
    def get_current_overview(self) -> Optional[Dict[str, Any]]:
        """Get the current market overview data."""
        return self.current_market_overview
    
    def is_overview_stale(self, max_age_hours: int = 1) -> bool:
        """Check if the current market overview is stale."""
        if self.current_market_overview is None:
            return True
            
        timestamp_field = self.current_market_overview.get('published_on',
                                                           self.current_market_overview.get('timestamp', 0))
        timestamp = self._normalize_timestamp(timestamp_field)

        if timestamp:
            data_time = datetime.fromtimestamp(timestamp)
            current_time = datetime.now()
            return current_time - data_time > timedelta(hours=max_age_hours)
        
        return True
