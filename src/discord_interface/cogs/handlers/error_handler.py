"""
Error handling utilities for Discord bot commands.
Handles exceptions, logging, and error recovery.
"""
import asyncio
from typing import Any, Optional
import discord
from discord.ext import commands


class ErrorHandler:
    """Handles errors and exceptions for Discord commands."""
    
    def __init__(self, logger):
        self.logger = logger
    
    async def handle_analysis_error(self, symbol: str, error: Exception, send_message_func, ctx: commands.Context) -> None:
        """Handle errors that occur during analysis."""
        if self.logger:
            self.logger.error(f"Error analyzing {symbol}: {str(error)}", exc_info=True)
        
        error_message = f"⚠️ Failed to analyze {symbol}: Error occurred."
        await send_message_func(ctx, error_message)
    
    async def handle_message_deletion_error(self, message: discord.Message, error: Exception) -> bool:
        """Handle errors during message deletion."""
        if isinstance(error, discord.NotFound):
            # Already deleted is fine
            return True
        elif isinstance(error, discord.HTTPException):
            if self.logger:
                self.logger.warning(f"Could not delete message {message.id}: {error}")
            raise  # Let retry decorator handle this
        else:
            if self.logger:
                self.logger.error(f"Unexpected error deleting message {message.id}: {error}")
            return False
    
    async def handle_cleanup_error(self, symbol: str, message: discord.Message, error: Exception) -> None:
        """Handle errors during cleanup operations."""
        if self.logger:
            self.logger.warning(f"Could not delete initial analysis msg for {symbol} after retries: {error}")
    
    async def handle_prerequisite_validation_error(self, component: str, ctx: commands.Context, send_message_func) -> None:
        """Handle prerequisite validation errors."""
        if self.logger:
            self.logger.error(f"{component} not found on bot instance")
        await send_message_func(ctx, f"⚠️ System error: {component} unavailable.")
    
    async def handle_symbol_not_found_error(self, symbol: str, ctx: commands.Context, send_message_func) -> None:
        """Handle symbol not found errors."""
        if self.logger:
            self.logger.warning(f"Symbol {symbol} not found on supported exchanges")
        await send_message_func(ctx, f"⚠️ Symbol {symbol} not available.")
    
    async def cancel_pending_tasks(self, tasks: set) -> None:
        """Cancel and clean up pending tasks."""
        if self.logger:
            self.logger.info(f"Cancelling {len(tasks)} ongoing analysis tasks.")
        
        tasks_to_cancel = list(tasks)
        for task in tasks_to_cancel:
            task.cancel()
        
        if tasks_to_cancel:
            await asyncio.gather(*tasks_to_cancel, return_exceptions=True)
        
        tasks.clear()
        
        if self.logger:
            self.logger.info("Task cleanup complete.")
