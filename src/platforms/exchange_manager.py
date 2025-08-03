import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

import ccxt.async_support as ccxt
import aiohttp

from src.logger.logger import Logger
from src.utils.decorators import retry_async


class ExchangeManager:
    def __init__(self, logger: Logger):
        self.logger = logger
        self.exchanges: Dict[str, ccxt.Exchange] = {}
        self.symbols_by_exchange: Dict[str, Set[str]] = {}
        self.last_update: Optional[datetime] = None
        self._update_task: Optional[asyncio.Task] = None
        self._shutdown_in_progress = False
        self.exchange_config = {
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        }
        self.exchange_names = ["binance", "kucoin", "gateio"]
        self.session = None
    
    async def initialize(self) -> None:
        """Initialize exchanges and load markets"""
        self.logger.info("Initializing SymbolManager and loading markets")
        # Create a single session for all exchanges to share
        self.session = aiohttp.ClientSession()
        self.exchange_config['session'] = self.session
        
        await self._load_all_exchanges()
        self._update_task = asyncio.create_task(self._periodic_update())
        self._update_task.add_done_callback(self._handle_update_task_done)
    
    def _handle_update_task_done(self, task):
        if task.exception() and not self._shutdown_in_progress:
            self.logger.error(f"Periodic update task failed: {task.exception()}")
    
    async def shutdown(self) -> None:
        """Close all exchanges and stop periodic updates"""
        self._shutdown_in_progress = True
        
        if self._update_task:
            self.logger.info("Cancelling periodic update task")
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                self.logger.exception(f"Error during update task cancellation: {e}")
            finally:
                self._update_task = None
        
        self.logger.info("Closing exchange connections")
        for exchange_id, exchange in list(self.exchanges.items()):
            try:
                await exchange.close()
                self.logger.debug(f"Closed {exchange_id} connection")
            except Exception as e:
                self.logger.error(f"Error closing {exchange_id} connection: {e}")
        
        # Close the shared session last, after all exchanges have been closed
        if self.session:
            try:
                self.logger.debug("Closing shared aiohttp session")
                await self.session.close()
            except Exception as e:
                self.logger.error(f"Error closing shared aiohttp session: {e}")
            finally:
                self.session = None
        
        self.exchanges.clear()
        self.symbols_by_exchange.clear()
        self.logger.info("SymbolManager shutdown complete")
    
    @retry_async()
    async def _load_exchange(self, exchange_id: str) -> Optional[ccxt.Exchange]:
        """Load a single exchange and its markets"""
        self.logger.info(f"Loading {exchange_id} markets")
        try:
            # Create exchange instance with the shared session
            exchange_class = getattr(ccxt, exchange_id)
            exchange_config = self.exchange_config.copy()
            
            # Add the session to the config
            if self.session:
                exchange_config['session'] = self.session
                
            exchange = exchange_class(exchange_config)
            
            # Load markets
            await exchange.load_markets()
            return exchange
        except Exception as e:
            self.logger.error(f"Failed to load {exchange_id} markets: {e}")
            return None

    async def _load_all_exchanges(self) -> None:
        """Load all supported exchanges and their markets"""
        for exchange_id in self.exchange_names:
            exchange = await self._load_exchange(exchange_id)
            if exchange:
                self.exchanges[exchange_id] = exchange
                self.symbols_by_exchange[exchange_id] = set(exchange.symbols)
                self.logger.info(f"Loaded {exchange_id} with {len(exchange.symbols)} symbols")
        
        self.last_update = datetime.now()
        self.logger.info(f"Finished loading all exchanges at {self.last_update}")
    
    async def refresh_markets(self) -> None:
        """Refresh markets for all exchanges"""
        self.logger.info("Refreshing markets for all exchanges")
        
        for exchange_id, exchange in list(self.exchanges.items()):
            try:
                self.logger.debug(f"Refreshing {exchange_id} markets")
                await exchange.load_markets(reload=True)
                self.symbols_by_exchange[exchange_id] = set(exchange.symbols)
                self.logger.info(f"Refreshed {exchange_id} with {len(exchange.symbols)} symbols")
            except Exception as e:
                self.logger.error(f"Failed to refresh {exchange_id} markets: {e}")
                # Try to reconnect if refresh fails
                try:
                    # Close old exchange connection first
                    try:
                        await exchange.close()
                    except Exception as e_close:
                        self.logger.warning(f"Error closing old {exchange_id} connection: {e_close}")
                    
                    # Create new exchange instance with shared session
                    new_exchange = await self._load_exchange(exchange_id)
                    if new_exchange:
                        self.exchanges[exchange_id] = new_exchange
                        self.symbols_by_exchange[exchange_id] = set(new_exchange.symbols)
                except Exception as reconnect_err:
                    self.logger.error(f"Failed to reconnect to {exchange_id}: {reconnect_err}")
                    # Remove failed exchange from dicts to avoid using a dead instance
                    self.exchanges.pop(exchange_id, None)
                    self.symbols_by_exchange.pop(exchange_id, None)
        
        self.last_update = datetime.now()
        self.logger.info(f"Markets refresh completed at {self.last_update}")
    
    async def _periodic_update(self) -> None:
        """Periodically refresh markets every 24 hours"""
        while not self._shutdown_in_progress:
            try:
                # Calculate time until next update (24 hours from last update)
                now = datetime.now()
                next_update = self.last_update + timedelta(hours=24)
                
                # If we're past the next update time, update immediately
                if now >= next_update:
                    await self.refresh_markets()
                    continue
                
                # Calculate delay until next update
                delay = (next_update - now).total_seconds()
                self.logger.info(f"Next market update scheduled in {delay/3600:.2f} hours")
                
                # Wait until next update time
                await asyncio.sleep(delay)
                await self.refresh_markets()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in periodic update: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying on error
    
    async def find_symbol_exchange(self, symbol: str) -> Tuple[Optional[ccxt.Exchange], Optional[str]]:
        """Find the first exchange that supports the given symbol"""
        for exchange_id in self.exchange_names:
            if exchange_id in self.symbols_by_exchange and symbol in self.symbols_by_exchange[exchange_id]:
                return self.exchanges.get(exchange_id), exchange_id
        
        # If symbol not found, try refreshing markets once
        if self.last_update and (datetime.now() - self.last_update).total_seconds() > 3600:
            self.logger.info(f"Symbol {symbol} not found, refreshing markets")
            await self.refresh_markets()
            
            # Try again after refresh
            for exchange_id in self.exchange_names:
                if exchange_id in self.symbols_by_exchange and symbol in self.symbols_by_exchange[exchange_id]:
                    return self.exchanges.get(exchange_id), exchange_id
        
        return None, None
    
    def get_all_symbols(self) -> Set[str]:
        """Get all unique symbols across all exchanges"""
        all_symbols = set()
        for symbols in self.symbols_by_exchange.values():
            all_symbols.update(symbols)
        return all_symbols
    
    def get_all_base_symbols(self) -> Set[str]:
        """Extract and return all base symbols from trading pairs across all exchanges"""
        all_base_symbols = set()
        for exchange_symbols in self.symbols_by_exchange.values():
            for symbol in exchange_symbols:
                if '/' in symbol:
                    base = symbol.split('/')[0]
                    all_base_symbols.add(base)
        return all_base_symbols
    
    def get_exchange_info(self) -> List[Dict]:
        """Get information about loaded exchanges"""
        info = []
        for exchange_id in self.exchange_names:
            if exchange_id in self.exchanges:
                info.append({
                    'id': exchange_id,
                    'loaded': True,
                    'symbol_count': len(self.symbols_by_exchange.get(exchange_id, set()))
                })
            else:
                info.append({
                    'id': exchange_id,
                    'loaded': False,
                    'symbol_count': 0
                })
        return info