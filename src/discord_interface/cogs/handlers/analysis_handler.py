"""
Analysis handling utilities for Discord bot commands.
Handles the core analysis workflow and coordination.
"""
import asyncio
from datetime import datetime
from typing import Any, Dict, Optional, Set, Tuple, TYPE_CHECKING
import discord
from discord.ext import commands

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
            if self.logger:
                self.logger.warning(f"Symbol {symbol} not found on supported exchanges")
            return None, None
        return exchange, exchange_id
    
    async def execute_analysis(self, symbol: str, exchange: Any, language: Optional[str]) -> Tuple[bool, Any]:
        """Execute the market analysis."""
        self.market_analyzer.initialize_for_symbol(symbol, exchange, language)
        result = await self.market_analyzer.analyze_market()
        self.market_analyzer.last_analysis_result = result
        
        success = await self.market_analyzer.publish_analysis()
        return success, result
    
    async def _handle_analysis_result(self, symbol: str, success: bool, result: Any, 
                                    ctx: commands.Context, send_message_func) -> None:
        """Handle the analysis result and send appropriate messages."""
        if not success or (isinstance(result, dict) and "error" in result):
            error_msg = result.get("error", "Analysis failed") if isinstance(result, dict) else "Analysis failed"
            await send_message_func(ctx, f"⚠️ Analysis of {symbol} failed: {error_msg}")
        else:
            await send_message_func(ctx, f"✅ Analysis of {symbol} completed!")
    
    async def _cleanup_analysis(self, symbol: str, error_handler) -> None:
        """Clean up analysis state and resources."""
        request_info = self.remove_analysis_request(symbol)
        
        if request_info:
            initial_msg = request_info.get("message")
            if initial_msg:
                try:
                    await self._delete_message_with_retry(initial_msg)
                except Exception as e:
                    await error_handler.handle_cleanup_error(symbol, initial_msg, e)
    
    async def _delete_message_with_retry(self, message: discord.Message) -> bool:
        """Helper method to delete a Discord message with retry logic."""
        try:
            await message.delete()
            return True
        except Exception as e:
            # Let error handler manage the specific error types
            return False
    
    def set_shutdown_flag(self) -> None:
        """Set shutdown flag to prevent new analyses."""
        self._shutdown_in_progress = True
    
    def is_shutdown_in_progress(self) -> bool:
        """Check if shutdown is in progress."""
        return self._shutdown_in_progress
    
    async def cleanup_tasks(self, error_handler) -> None:
        """Clean up all pending analysis tasks."""
        await error_handler.cancel_pending_tasks(self._analysis_tasks)
