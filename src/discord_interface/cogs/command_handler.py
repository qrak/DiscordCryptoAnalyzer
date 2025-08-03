import asyncio
import re
from datetime import datetime, timedelta
from typing import Optional, Any, Dict, Union, Set, TYPE_CHECKING

import discord
from discord.ext import commands

from config.config import (
    MAIN_CHANNEL_ID,
    ANALYSIS_COOLDOWN_COIN,
    ANALYSIS_COOLDOWN_USER,
    FILE_MESSAGE_EXPIRY,
    SUPPORTED_LANGUAGES
)
from src.utils.decorators import retry_async

if TYPE_CHECKING:
    from logging import Logger
    from src.analyzer.market_analyzer import MarketAnalyzer
    from src.platforms.exchange_manager import ExchangeManager


class CommandHandler(commands.Cog):
    """Handles bot commands like market analysis."""
    def __init__(self, bot: commands.Bot, logger: 'Logger', symbol_manager: 'ExchangeManager', market_analyzer: 'MarketAnalyzer') -> None:
        """Initializes the CommandHandler cog."""
        self.bot = bot
        self.logger = logger
        self._command_lock = asyncio.Lock()
        self.ongoing_analyses: Set[str] = set()
        self.coin_cooldowns: Dict[str, datetime] = {}
        self.user_cooldowns: Dict[int, datetime] = {}
        self.analysis_requests: Dict[str, Dict[str, Any]] = {}
        self.trading_strategies: Dict[str, Any] = {}
        self._shutdown_in_progress: bool = False
        self._analysis_tasks: Set[asyncio.Task] = set()
        self.symbol_manager = symbol_manager
        self.market_analyzer = market_analyzer

    @retry_async(max_retries=3, initial_delay=1, backoff_factor=2)
    async def _delete_message_with_retry(self, message: discord.Message) -> bool:
        """Helper method to delete a Discord message with retry logic."""
        try:
            await message.delete()
            return True
        except discord.NotFound:
            # Already deleted is fine
            return True
        except discord.HTTPException as e:
            self.logger.warning(f"Could not delete message {message.id}: {e}")
            raise  # Let retry decorator handle this
        except Exception as e:
            self.logger.error(f"Unexpected error deleting message {message.id}: {e}")
            return False

    async def track_user_command(self, ctx: commands.Context, expire_after: Optional[int] = FILE_MESSAGE_EXPIRY) -> None:
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

    async def _handle_cooldown(self, ctx: commands.Context, cooldown_type: str, key: Union[str, int], cooldown_duration: int, cooldown_dict: Dict[Union[str, int], datetime]) -> bool:
        """Check and message user about command cooldowns."""
        now = datetime.now()
        if key in cooldown_dict:
            time_diff = now - cooldown_dict[key]
            if time_diff.total_seconds() < cooldown_duration:
                remaining = cooldown_duration - int(time_diff.total_seconds())
                delta = timedelta(seconds=remaining)
                hours, remainder = divmod(delta.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                time_str = f"{minutes}m {seconds}s"
                if hours > 0:
                    time_str = f"{hours}h {time_str}"

                message = ""
                if cooldown_type == "coin":
                    message = f"⌛ {key} was analyzed recently. Try again in {time_str}."
                elif cooldown_type == "user":
                    message = f"⌛ {ctx.author.mention}, you can request another analysis in {time_str}."

                if message:
                    await self.send_tracked_message(ctx, message)
                return True
        return False

    @commands.command(name='analyze')
    async def analyze_command(self, ctx: commands.Context, symbol_arg: Optional[str] = None, lang_arg: Optional[str] = None) -> None:
        """Initiates market analysis for a given trading pair."""
        await self.track_user_command(ctx)

        if self._shutdown_in_progress:
            await self.send_tracked_message(ctx, "⚠️ Bot is shutting down, command not available.")
            return

        if ctx.channel.id != MAIN_CHANNEL_ID:
            await self.send_tracked_message(ctx, f"⚠️ This command can only be used in <#{MAIN_CHANNEL_ID}>.")
            return

        args = ctx.message.content.split()[1:]

        if not args:
            await self.send_tracked_message(ctx, f"Usage: `!analyze <SYMBOL> [Language]`. Example: `!analyze BTC/USDT Polish`")
            return

        symbol = args[0].upper()

        if not re.match(r'^[A-Za-z0-9]+/USD[TC]?$', symbol):
            await self.send_tracked_message(ctx, f"Invalid symbol format. Use format like `BTC/USDT`.")
            return

        language = None
        if len(args) > 1:
            requested_lang = args[1].capitalize()
            if requested_lang in SUPPORTED_LANGUAGES:
                language = requested_lang
            else:
                supported_langs = ", ".join(SUPPORTED_LANGUAGES.keys())
                await self.send_tracked_message(ctx, f"⚠️ Unsupported language '{requested_lang}'. Available: {supported_langs}")
                return

        is_admin = ctx.author.guild_permissions.administrator

        if symbol in self.ongoing_analyses:
            await self.send_tracked_message(ctx, f"⏳ {symbol} is currently being analyzed. Please wait.")
            return

        if not is_admin:
            if await self._handle_cooldown(ctx, "coin", symbol, ANALYSIS_COOLDOWN_COIN, self.coin_cooldowns):
                return
            if await self._handle_cooldown(ctx, "user", ctx.author.id, ANALYSIS_COOLDOWN_USER, self.user_cooldowns):
                return

        self.ongoing_analyses.add(symbol)
        language_text = f" in {language}" if language else ""
        embed = discord.Embed(
            title=f"🔍 Analyzing {symbol}{language_text}",
            description=f"Requested by {ctx.author.mention}\nResults will be posted when ready.",
            color=discord.Colour.blue()
        )
        embed.set_footer(text="This may take up to a minute.")

        confirmation_message = await self.send_tracked_message(ctx, "", embed=embed)

        self.analysis_requests[symbol] = {
            "message": confirmation_message,
            "user": ctx.author,
            "channel": ctx.channel,
            "requested_at": datetime.now(),
            "language": language
        }

        analysis_task = self.bot.loop.create_task(
            self.perform_analysis(symbol, ctx, language),
            name=f"Analysis-{symbol}"
        )
        self._analysis_tasks.add(analysis_task)
        analysis_task.add_done_callback(self._analysis_tasks.discard)

    @commands.command(name='cleanup')
    @commands.is_owner()
    async def cleanup_command(self, ctx: commands.Context) -> None:
        """Force cleanup of expired tracked messages (owner only)."""
        await self.track_user_command(ctx)
        await self.send_tracked_message(ctx, "🧹 Starting message cleanup...")

        deleted_count = 0
        if hasattr(self.bot, 'discord_notifier') and hasattr(self.bot.discord_notifier, 'file_handler'):
            notifier = self.bot.discord_notifier
            deleted_count = await notifier.file_handler.check_and_delete_expired_messages()
        else:
            await self.send_tracked_message(ctx, "❌ File handler not available.")
            return

        await self.send_tracked_message(ctx, f"✅ Cleanup complete! Deleted {deleted_count} expired messages.")

    async def perform_analysis(self, symbol: str, ctx: commands.Context, language: Optional[str]) -> None:
        """Performs the actual market analysis for a symbol."""
        if self.logger:
            self.logger.info(f"Starting analysis: {symbol}, Lang: {language or 'English'}, User: {ctx.author}")

        try:
            if not hasattr(self.bot, 'discord_notifier'):
                if self.logger:
                    self.logger.error("Discord notifier not found on bot instance")
                await self.send_tracked_message(ctx, f"⚠️ System error: Notifier unavailable.")
                return

            if not self.symbol_manager:
                if self.logger:
                    self.logger.error("Symbol manager not available")
                await self.send_tracked_message(ctx, f"⚠️ System error: Symbol manager unavailable.")
                return

            if not self.market_analyzer:
                if self.logger:
                    self.logger.error("Market analyzer not available")
                await self.send_tracked_message(ctx, f"⚠️ System error: Market analyzer unavailable.")
                return

            exchange, exchange_id = await self.symbol_manager.find_symbol_exchange(symbol)
            if not exchange:
                if self.logger:
                    self.logger.warning(f"Symbol {symbol} not found on supported exchanges")
                await self.send_tracked_message(ctx, f"⚠️ Symbol {symbol} not available.")
                return

            if self.logger:
                self.logger.info(f"Using {exchange_id} for {symbol} analysis")

            self.market_analyzer.initialize_for_symbol(symbol, exchange, language)
            result = await self.market_analyzer.analyze_market()
            self.market_analyzer.last_analysis_result = result

            is_admin = ctx.author.guild_permissions.administrator
            if not is_admin:
                self.coin_cooldowns[symbol] = datetime.now()
                self.user_cooldowns[ctx.author.id] = datetime.now()

            success = await self.market_analyzer.publish_analysis()

            if not success or (isinstance(result, dict) and "error" in result):
                error_msg = result.get("error", "Analysis failed") if isinstance(result, dict) else "Analysis failed"
                await self.send_tracked_message(ctx, f"⚠️ Analysis of {symbol} failed: {error_msg}")
            else:
                await self.send_tracked_message(ctx, f"✅ Analysis of {symbol} completed!")

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error analyzing {symbol}: {str(e)}", exc_info=True)
            await self.send_tracked_message(ctx, f"⚠️ Failed to analyze {symbol}: Error occurred.")
        finally:
            self.ongoing_analyses.discard(symbol)
            if symbol in self.analysis_requests:
                request_info = self.analysis_requests.pop(symbol)
                initial_msg = request_info.get("message")
                if initial_msg:
                    try:
                        # Use the retry-enabled method instead of direct deletion
                        await self._delete_message_with_retry(initial_msg)
                    except Exception as e_del:
                        if self.logger:
                            self.logger.warning(f"Could not delete initial analysis msg for {symbol} after retries: {e_del}")

    async def cleanup(self) -> None:
        """Clean up resources like pending analysis tasks during shutdown."""
        self._shutdown_in_progress = True
        if self.logger:
            self.logger.info(f"Cancelling {len(self._analysis_tasks)} ongoing analysis tasks.")

        tasks_to_cancel = list(self._analysis_tasks)
        for task in tasks_to_cancel:
            task.cancel()

        if tasks_to_cancel:
            await asyncio.gather(*tasks_to_cancel, return_exceptions=True)

        self._analysis_tasks.clear()
        if self.logger:
            self.logger.info("CommandHandler cleanup complete.")