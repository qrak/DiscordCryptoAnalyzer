import asyncio
from typing import Optional, Any, TYPE_CHECKING

import discord
from discord.ext import commands

from src.utils.loader import config
from src.utils.decorators import retry_async
from src.discord_interface.cogs.handlers.command_validator import CommandValidator, ValidationResult
from src.discord_interface.cogs.handlers.response_builder import ResponseBuilder
from src.discord_interface.cogs.handlers.error_handler import ErrorHandler
from src.discord_interface.cogs.handlers.analysis_handler import AnalysisHandler

if TYPE_CHECKING:
    from logging import Logger
    from src.analyzer.core.analysis_engine import AnalysisEngine
    from src.platforms.exchange_manager import ExchangeManager


class CommandHandler(commands.Cog):
    """Handles bot commands like market analysis using specialized components."""
    
    def __init__(self, bot: commands.Bot, logger: 'Logger', symbol_manager: 'ExchangeManager', market_analyzer: 'AnalysisEngine') -> None:
        """Initialize the CommandHandler with specialized components."""
        self.bot = bot
        self.logger = logger
        self._command_lock = asyncio.Lock()
        
        # Initialize specialized components
        self.validator = CommandValidator(logger)
        self.response_builder = ResponseBuilder(logger)
        self.error_handler = ErrorHandler(logger)
        self.analysis_handler = AnalysisHandler(logger, symbol_manager, market_analyzer)

    @retry_async(max_retries=3, initial_delay=1, backoff_factor=2)
    async def _delete_message_with_retry(self, message: discord.Message) -> bool:
        """Helper method to delete a Discord message with retry logic."""
        try:
            await message.delete()
            return True
        except Exception as e:
            return await self.error_handler.handle_message_deletion_error(message, e)

    async def track_user_command(self, ctx: commands.Context, expire_after: Optional[int] = config.FILE_MESSAGE_EXPIRY) -> None:
        """Track user command message for deletion via notifier."""
        if hasattr(self.bot, 'discord_notifier') and hasattr(self.bot.discord_notifier, 'file_handler'):
            notifier = self.bot.discord_notifier
            await notifier.file_handler.track_message(
                message_id=ctx.message.id,
                channel_id=ctx.channel.id,
                user_id=ctx.author.id,
                message_type="user_command",
                expire_after=expire_after
            )
            if self.logger:
                self.logger.debug(f"Tracking user command message for deletion: {ctx.message.id}")

    async def send_tracked_message(self, ctx: commands.Context, content: str, **kwargs: Any) -> Optional[discord.Message]:
        """Send tracked messages via the bot's discord notifier."""
        if hasattr(self.bot, 'discord_notifier'):
            notifier = self.bot.discord_notifier
            return await notifier.send_context_message(ctx, content, **kwargs)
        else:
            if self.logger:
                self.logger.warning("Discord notifier not found, sending untracked message.")
            return await ctx.send(content, **kwargs)

    @commands.command(name='analyze')
    async def analyze_command(self, ctx: commands.Context, *, args: Optional[str] = None) -> None:
        """Initiates market analysis for a given trading pair."""
        await self.track_user_command(ctx)

        async with self._command_lock:
            if self.logger:
                self.logger.debug(f"Processing analysis command for {ctx.message.content} from user {ctx.author.id}")

            # Disallow multiple concurrent analyses from the same user
            if self.analysis_handler.is_user_in_progress(ctx.author.id):
                # Short-lived notice (2 minutes) so it gets auto-deleted quickly
                await self.send_tracked_message(
                    ctx,
                    f"⏳ {ctx.author.mention}, you already have an analysis running. Please wait for it to finish.",
                    expire_after=120
                )
                return

            validation_result = await self._validate_analysis_request(ctx)
            if not validation_result.is_valid:
                # Validation messages should also be short-lived (5 minutes)
                await self.send_tracked_message(ctx, validation_result.error_message, expire_after=300)
                return

            symbol = validation_result.symbol
            timeframe = validation_result.timeframe  # NEW: Extract timeframe
            language = validation_result.language

            self.validator.add_ongoing_analysis(symbol)
            self.analysis_handler.add_user_in_progress(ctx.author.id)

            if self.logger:
                timeframe_info = f", Timeframe: {timeframe}" if timeframe else ""
                self.logger.info(f"Analysis initiated: {symbol}, User: {ctx.author.id}, Language: {language or 'English'}{timeframe_info}")

            embed = self.response_builder.build_analysis_embed(symbol, ctx.author, language)
            confirmation_message = await self.send_tracked_message(ctx, "", embed=embed)

            self.analysis_handler.add_analysis_request(symbol, confirmation_message, ctx.author, ctx.channel, language)

            # Create and track the analysis task
            analysis_task = self.bot.loop.create_task(
                self._perform_analysis_workflow(symbol, ctx, language, timeframe),  # NEW: Pass timeframe
                name=f"Analysis-{symbol}"
            )
            self.analysis_handler._analysis_tasks.add(analysis_task)

    async def _validate_analysis_request(self, ctx: commands.Context):
        """Validate analysis request and return ValidationResult."""
        # Check if shutdown is in progress
        if self.analysis_handler.is_shutdown_in_progress():
            return ValidationResult(is_valid=False, error_message=self.response_builder.build_shutdown_message())

        # Validate channel
        if not self.validator.validate_channel(ctx.channel.id):
            return ValidationResult(is_valid=False, error_message=self.response_builder.build_wrong_channel_message(config.MAIN_CHANNEL_ID))

        # Parse arguments and perform comprehensive validation
        args = ctx.message.content.split()[1:]
        return self.validator.validate_full_analysis_request(ctx, args, config.ANALYSIS_COOLDOWN_COIN, config.ANALYSIS_COOLDOWN_USER)

    async def _perform_analysis_workflow(self, symbol: str, ctx: commands.Context, language: Optional[str], timeframe: Optional[str] = None) -> None:
        """Perform the complete analysis workflow using the specialized components."""
        timeframe_info = f", Timeframe: {timeframe}" if timeframe else ""
        if self.logger:
            self.logger.info(f"Starting analysis: {symbol}, Lang: {language or 'English'}{timeframe_info}, User: {ctx.author}")
        
        try:
            # Validate prerequisites
            is_valid, error_msg = await self.analysis_handler.validate_analysis_prerequisites(self.bot)
            if not is_valid:
                await self.error_handler.handle_prerequisite_validation_error(error_msg, ctx, self.send_tracked_message)
                return
            
            # Find exchange for symbol
            exchange, exchange_id = await self.analysis_handler.find_symbol_exchange(symbol)
            if not exchange:
                await self.error_handler.handle_symbol_not_found_error(symbol, ctx, self.send_tracked_message)
                return
            
            if self.logger:
                self.logger.info(f"Using {exchange_id} for {symbol} analysis")
            
            # Perform analysis with optional timeframe override
            success, result = await self.analysis_handler.execute_analysis(symbol, exchange, language, timeframe)
            
            # Update cooldowns if not admin
            if not self.validator.is_admin(ctx):
                self.validator.update_cooldowns(symbol, ctx.author.id)
            
            # Handle analysis result
            if not success or (isinstance(result, dict) and "error" in result):
                error_msg = result.get("error", "Analysis failed") if isinstance(result, dict) else "Analysis failed"
                await self.send_tracked_message(ctx, self.response_builder.build_error_message(symbol, error_msg))
            else:
                await self.send_tracked_message(ctx, self.response_builder.build_success_message(symbol))
            
        except Exception as e:
            await self.error_handler.handle_analysis_error(symbol, e, self.send_tracked_message, ctx)
        finally:
            self.validator.remove_ongoing_analysis(symbol)
            # Clear per-user in-progress state
            try:
                self.analysis_handler.remove_user_in_progress(ctx.author.id)
            except Exception:
                pass
            await self._cleanup_analysis_request(symbol)

    async def _cleanup_analysis_request(self, symbol: str) -> None:
        """Clean up analysis request and delete confirmation message."""
        request_info = self.analysis_handler.remove_analysis_request(symbol)
        
        if request_info:
            initial_msg = request_info.get("message")
            if initial_msg:
                try:
                    await self._delete_message_with_retry(initial_msg)
                except Exception as e:
                    await self.error_handler.handle_cleanup_error(symbol, initial_msg, e)

    @commands.command(name='cleanup')
    @commands.is_owner()
    async def cleanup_command(self, ctx: commands.Context) -> None:
        """Force cleanup of expired tracked messages (owner only)."""
        await self.track_user_command(ctx)
        await self.send_tracked_message(ctx, self.response_builder.build_cleanup_start_message())

        deleted_count = 0
        if hasattr(self.bot, 'discord_notifier') and hasattr(self.bot.discord_notifier, 'file_handler'):
            notifier = self.bot.discord_notifier
            deleted_count = await notifier.file_handler.check_and_delete_expired_messages()
        else:
            await self.send_tracked_message(ctx, self.response_builder.build_cleanup_error_message())
            return

        await self.send_tracked_message(ctx, self.response_builder.build_cleanup_complete_message(deleted_count))

    async def cleanup(self) -> None:
        """Clean up resources like pending analysis tasks during shutdown."""
        self.analysis_handler.set_shutdown_flag()
        await self.analysis_handler.cleanup_tasks(self.error_handler)
        if self.logger:
            self.logger.info("CommandHandler cleanup complete.")