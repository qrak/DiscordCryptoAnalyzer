"""
Analysis handling utilities for Discord bot commands.
Handles the core analysis workflow and coordination.
"""
import asyncio
from datetime import datetime
from typing import Any, Dict, Optional, Set, Tuple, TYPE_CHECKING
import discord

if TYPE_CHECKING:
    from src.analyzer.core.analysis_engine import AnalysisEngine
    from src.platforms.exchange_manager import ExchangeManager


class AnalysisHandler:
    """Handles market analysis workflow and coordination."""
    
    def __init__(self, logger, symbol_manager: 'ExchangeManager', market_analyzer: 'AnalysisEngine'):
        self.logger = logger
        self.symbol_manager = symbol_manager
        self.market_analyzer = market_analyzer
        self.analysis_requests: Dict[str, Dict[str, Any]] = {}
        self._analysis_tasks: Set[asyncio.Task] = set()
        self._shutdown_in_progress: bool = False
        # Global lock to ensure the shared market_analyzer isn't accessed concurrently
        self._analysis_lock = asyncio.Lock()
        # Track users with an ongoing analysis to prevent multiple concurrent requests per user
        self._users_in_progress: Set[int] = set()
    
    def add_analysis_request(self, symbol: str, message: discord.Message, user: discord.Member, 
                           channel: discord.TextChannel, language: Optional[str] = None) -> None:
        """Add analysis request to tracking."""
        self.analysis_requests[symbol] = {
            "message": message,
            "user": user,
            "channel": channel,
            "requested_at": datetime.now(),
            "language": language
        }
    
    def remove_analysis_request(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Remove and return analysis request."""
        return self.analysis_requests.pop(symbol, None)
    
    async def validate_analysis_prerequisites(self, bot) -> Tuple[bool, Optional[str]]:
        """Validate that all required components are available."""
        if not hasattr(bot, 'discord_notifier'):
            return False, "Discord notifier not found on bot instance"
        
        if not self.symbol_manager:
            return False, "Symbol manager not available"
        
        if not self.market_analyzer:
            return False, "Market analyzer not available"
        
        return True, None
    
    async def find_symbol_exchange(self, symbol: str) -> Tuple[Optional[Any], Optional[str]]:
        """Find exchange for the given symbol."""
        exchange, exchange_id = await self.symbol_manager.find_symbol_exchange(symbol)
        if not exchange:
            return None, None
        return exchange, exchange_id
    
    async def execute_analysis(self, symbol: str, exchange: Any, language: Optional[str], 
                              timeframe: Optional[str] = None, provider: Optional[str] = None, 
                              model: Optional[str] = None) -> Tuple[bool, Any]:
        """
        Execute the market analysis with optional timeframe, provider, and model overrides.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            exchange: Exchange instance
            language: Optional language for analysis output
            timeframe: Optional timeframe override (uses config default if None)
            provider: Optional AI provider override (admin only)
            model: Optional AI model override (admin only)
            
        Returns:
            Tuple of (success, result)
        """
        # Serialize access to the shared analyzer to avoid state bleed between concurrent analyses
        async with self._analysis_lock:
            self.market_analyzer.initialize_for_symbol(symbol, exchange, language, timeframe)
            result = await self.market_analyzer.analyze_market(provider=provider, model=model)
            self.market_analyzer.last_analysis_result = result
            success = await self.market_analyzer.publish_analysis()
            return success, result
    
    def set_shutdown_flag(self) -> None:
        """Set shutdown flag to prevent new analyses."""
        self._shutdown_in_progress = True
    
    def is_shutdown_in_progress(self) -> bool:
        """Check if shutdown is in progress."""
        return self._shutdown_in_progress
    
    async def cleanup_tasks(self, error_handler) -> None:
        """Clean up all pending analysis tasks."""
        await error_handler.cancel_pending_tasks(self._analysis_tasks)

    # --- Per-user in-progress tracking ---
    def is_user_in_progress(self, user_id: int) -> bool:
        return user_id in self._users_in_progress

    def add_user_in_progress(self, user_id: int) -> None:
        self._users_in_progress.add(user_id)
        if self.logger:
            self.logger.debug(f"User {user_id} marked as in-progress. Users: {list(self._users_in_progress)}")

    def remove_user_in_progress(self, user_id: int) -> None:
        self._users_in_progress.discard(user_id)
        if self.logger:
            self.logger.debug(f"User {user_id} cleared from in-progress. Users: {list(self._users_in_progress)}")
