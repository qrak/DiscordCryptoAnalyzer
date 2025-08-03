import asyncio
import sys

from src.logger.logger import Logger
from src.platforms.alternative_me import AlternativeMeAPI
from src.platforms.coingecko import CoinGeckoAPI
from src.platforms.cryptocompare import CryptoCompareAPI
from src.platforms.exchange_manager import ExchangeManager
from src.analyzer.market_analyzer import MarketAnalyzer
from src.discord_interface.notifier import DiscordNotifier
from src.rag.engine import RagEngine
from src.utils.token_counter import TokenCounter
from src.utils.keyboard_handler import KeyboardHandler


class DiscordCryptoBot:
    def __init__(self, logger: Logger):
        self.market_analyzer = None
        self.coingecko_api = None
        self.cryptocompare_api = None
        self.alternative_me_api = None
        self.rag_engine = None
        self.logger = logger
        self.discord_notifier = None
        self.symbol_manager = None
        self.token_counter = None
        self.keyboard_handler = None
        self.tasks = []
        self.running = False
        self._active_tasks = set()

    async def initialize(self):
        self.logger.info("Initializing Discord Crypto Bot...")

        # Initialize TokenCounter early
        self.token_counter = TokenCounter()
        self.logger.debug("TokenCounter initialized")

        self.symbol_manager = ExchangeManager(self.logger)
        await self.symbol_manager.initialize()
        self.logger.debug("SymbolManager initialized")

        # Initialize API clients
        self.coingecko_api = CoinGeckoAPI(logger=self.logger)
        await self.coingecko_api.initialize()
        self.logger.debug("CoinGeckoAPI initialized")
        
        self.cryptocompare_api = CryptoCompareAPI(logger=self.logger)
        await self.cryptocompare_api.initialize()
        self.logger.debug("CryptoCompareAPI initialized")
        
        self.alternative_me_api = AlternativeMeAPI(logger=self.logger)
        await self.alternative_me_api.initialize()
        self.logger.debug("AlternativeMeAPI initialized")

        # Pass token_counter and initialized API clients to RagEngine to avoid double initialization
        self.rag_engine = RagEngine(
            self.logger, 
            self.token_counter,
            coingecko_api=self.coingecko_api,
            cryptocompare_api=self.cryptocompare_api
        )
        await self.rag_engine.initialize()
        self.logger.debug("RagEngine initialized")
        
        self.rag_engine.set_symbol_manager(self.symbol_manager)
        self.logger.debug("Passed SymbolManager to RagEngine")

        self.market_analyzer = MarketAnalyzer(
            logger=self.logger,
            rag_engine=self.rag_engine,
            coingecko_api=self.coingecko_api,
            alternative_me_api=self.alternative_me_api
        )

        self.logger.debug("MarketAnalyzer initialized")

        self.discord_notifier = DiscordNotifier(
            logger=self.logger,
            symbol_manager=self.symbol_manager,
            market_analyzer=self.market_analyzer,
        )
        discord_task = asyncio.create_task(
            self.discord_notifier.start(),
            name="Discord-Bot"
        )
        self._active_tasks.add(discord_task)
        discord_task.add_done_callback(self._active_tasks.discard)
        self.tasks.append(discord_task)

        # Wait for Discord notifier to be fully ready
        self.logger.debug("Waiting for Discord notifier to fully initialize...")
        await self.discord_notifier.wait_until_ready()
        self.logger.debug("DiscordNotifier initialized")

        self.market_analyzer.set_discord_notifier(self.discord_notifier)
        self.logger.debug("MarketAnalyzer set DiscordNotifier")

        await self.rag_engine.start_periodic_updates()
        
        # Initialize keyboard handler
        self.keyboard_handler = KeyboardHandler(logger=self.logger)
        self.keyboard_handler.register_command('r', self.refresh_crypto_news, "Refresh crypto news")
        self.keyboard_handler.register_command('o', self.refresh_market_overview, "Refresh market overview data")
        self.keyboard_handler.register_command('h', self.show_help, "Show this help message")
        self.keyboard_handler.register_command('q', self.request_shutdown, "Quit the application")
        
        # Start keyboard handler
        keyboard_task = asyncio.create_task(
            self.keyboard_handler.start_listening(),
            name="Keyboard-Handler"
        )
        self._active_tasks.add(keyboard_task)
        keyboard_task.add_done_callback(self._active_tasks.discard)
        self.tasks.append(keyboard_task)
        
        self.logger.info("Discord Crypto Bot initialized successfully")
        self.logger.info("Keyboard commands available: Press 'h' for help")

    async def start(self):
        """Start the bot and its components"""
        self.logger.info("Bot components running...")
        self.running = True
    
        try:
            await asyncio.gather(*self.tasks)
        except asyncio.CancelledError:
            self.logger.info("Discord bot received cancellation request...")
        except Exception as e:
            self.logger.error(f"Error in bot: {e}")

    async def refresh_crypto_news(self):
        """Refresh crypto news data"""
        self.logger.info("Manually refreshing crypto news...")
        try:
            await self.rag_engine.refresh_market_data()
            self.logger.info("Crypto news refreshed successfully")
        except Exception as e:
            self.logger.error(f"Error refreshing crypto news: {e}")

    async def refresh_market_overview(self):
        """Refresh market overview data"""
        self.logger.info("Manually refreshing market overview data...")
        try:
            market_overview = await self.rag_engine._fetch_market_overview()
            if market_overview:
                market_overview_file = self.rag_engine.file_handler.get_market_overview_path()
                self.rag_engine.file_handler.save_json_file(market_overview_file, market_overview)
                self.rag_engine.current_market_overview = market_overview
                self.logger.info("Market overview data refreshed successfully")
            else:
                self.logger.warning("Failed to fetch market overview data")
        except Exception as e:
            self.logger.error(f"Error refreshing market overview: {e}")

    async def show_help(self):
        """Show help information about available commands"""
        self.logger.info("\n=== Available Keyboard Commands ===")
        self.keyboard_handler.display_help()
        self.logger.info("=================================")

    async def request_shutdown(self):
        """Request application shutdown"""
        self.logger.info("Shutdown requested via keyboard command")
        self.running = False
        # Cancel all tasks to trigger shutdown
        for task in self.tasks:
            if not task.done():
                task.cancel()

    async def shutdown(self):
        self.logger.info("Shutting down gracefully...")
        self.running = False

        # Cancel active tasks first
        pending_tasks = list(self._active_tasks)
        if pending_tasks:
            self.logger.info(f"Cancelling {len(pending_tasks)} active tasks...")
            for task in pending_tasks:
                if not task.done():
                    task.cancel()
    
            try:
                await asyncio.wait(pending_tasks, timeout=3.0)
            except asyncio.TimeoutError:
                self.logger.warning("Some tasks didn't complete in time")

        # Close keyboard handler if it exists
        if self.keyboard_handler:
            try:
                self.logger.info("Closing keyboard handler...")
                await self.keyboard_handler.stop_listening()
                self.keyboard_handler = None
            except Exception as e:
                self.logger.warning(f"Error closing keyboard handler: {e}")

        # Close components in reverse initialization order
    
        # Discord notifier (contains the bot)
        if self.discord_notifier:
            try:
                self.logger.info("Closing Discord notifier...")
                await asyncio.wait_for(self.discord_notifier.__aexit__(None, None, None), timeout=5.0)
                self.discord_notifier = None
            except asyncio.TimeoutError:
                self.logger.warning("Discord notifier shutdown timed out")
            except Exception as e:
                self.logger.warning(f"Error closing Discord notifier: {e}")
    
        # Market analyzer
        if self.market_analyzer:
            try:
                self.logger.info("Closing market analyzer...")
                await asyncio.wait_for(self.market_analyzer.close(), timeout=3.0)
                self.market_analyzer = None
            except asyncio.TimeoutError:
                self.logger.warning("Market analyzer shutdown timed out")
            except Exception as e:
                self.logger.warning(f"Error closing market analyzer: {e}")

        # RAG engine
        if hasattr(self, 'rag_engine') and self.rag_engine:
            try:
                self.logger.info("Closing RAG engine...")
                await asyncio.wait_for(self.rag_engine.close(), timeout=3.0)
                self.rag_engine = None
            except asyncio.TimeoutError:
                self.logger.warning("RAG engine shutdown timed out")
            except Exception as e:
                self.logger.warning(f"Error closing RAG engine: {e}")
    
        # API clients
        for client_name, client in [
            ("AlternativeMeAPI", self.alternative_me_api),
            ("CryptoCompareAPI", self.cryptocompare_api),
            ("CoinGeckoAPI", self.coingecko_api)
        ]:
            if client and hasattr(client, 'close') and callable(client.close):
                try:
                    self.logger.info(f"Closing {client_name}...")
                    await asyncio.wait_for(client.close(), timeout=3.0)
                except asyncio.TimeoutError:
                    self.logger.warning(f"{client_name} shutdown timed out")
                except Exception as e:
                    self.logger.warning(f"Error closing {client_name}: {e}")
    
        # Symbol manager (should be closed last as other components might depend on it)
        if self.symbol_manager:
            try:
                self.logger.info("Closing SymbolManager...")
                await asyncio.wait_for(self.symbol_manager.shutdown(), timeout=3.0)
                self.symbol_manager = None
            except asyncio.TimeoutError:
                self.logger.warning("SymbolManager shutdown timed out")
            except Exception as e:
                self.logger.warning(f"Error closing SymbolManager: {e}")

        # Set all component references to None to help garbage collection
        self.alternative_me_api = None
        self.cryptocompare_api = None
        self.coingecko_api = None

        self.logger.info("Shutdown complete")