import asyncio
import io
from datetime import datetime
from typing import Optional, Any, Dict

import discord
from aiohttp import ClientSession
from discord.ext import commands

from config.config import (BOT_TOKEN_DISCORD, TEMPORARY_CHANNEL_ID_DISCORD)
from config.config import FILE_MESSAGE_EXPIRY, SUPPORTED_LANGUAGES
from src.discord_interface.cogs.anti_spam import AntiSpam
from src.discord_interface.cogs.command_handler import CommandHandler
from src.discord_interface.cogs.reaction_handler import ReactionHandler
from .filehandler import DiscordFileHandler
from src.utils.decorators import retry_async


class DiscordNotifier:
    BOT_LOGO_URL = "https://drive.google.com/uc?export=view&id=1d-6ABQCNgeENR4DMNZZGWhEguR901Lrn"

    def __init__(self,
                 logger,
                 symbol_manager,
                 market_analyzer) -> None:
        self.logger = logger
        self.symbol_manager = symbol_manager
        self.market_analyzer = market_analyzer
        self.session: Optional[ClientSession] = None
        self.spam_allowed_channels = {TEMPORARY_CHANNEL_ID_DISCORD}
        self.is_initialized = False
        self._ready_event = asyncio.Event()  # New event to properly track ready state

        intents = discord.Intents.default()
        intents.message_content = True
        intents.reactions = True
        intents.typing = False
        intents.presences = False

        self.bot = commands.Bot(command_prefix="!", intents=intents)
        
        # Assign self to bot instance early for cogs to access
        self.bot.discord_notifier = self

        # Register event handlers
        self.bot.add_listener(self.on_ready)
        self.bot.add_listener(self.on_command_error)

        # Initialize the file handler
        self.file_handler = DiscordFileHandler(self.bot, self.logger)

        # Register setup_hook correctly
        self.bot.setup_hook = self.setup_bot

    async def setup_bot(self):
        """Runs before the bot logs in, loads cogs."""
        try:
            self.logger.debug("Adding AntiSpam cog...")
            await self.bot.add_cog(AntiSpam(self.bot, self.spam_allowed_channels))
            self.logger.debug("AntiSpam cog added.")

            self.logger.debug("Adding ReactionHandler cog...")
            await self.bot.add_cog(ReactionHandler(self.bot, self.logger))
            self.logger.debug("ReactionHandler cog added.")

            self.logger.debug("Adding CommandHandler cog...")
            await self.bot.add_cog(CommandHandler(
                self.bot,
                self.logger,
                symbol_manager=self.symbol_manager,
                market_analyzer=self.market_analyzer
            ))
            self.logger.debug("CommandHandler cog added.")
        except Exception as e:
            self.logger.error(f"Error during setup_bot (cog loading): {e}", exc_info=True)
            raise

    async def on_ready(self):
        try:
            self.logger.info(f"DiscordNotifier: Logged in as {self.bot.user.name}")

            # Initialize file handler
            self.file_handler.initialize()
            self.logger.debug("FileHandler initialized in on_ready.")

            # Initialize AntiSpam role
            antispam_cog = self.bot.get_cog('AntiSpam')
            if antispam_cog and hasattr(antispam_cog, 'initialize_role'):
                await antispam_cog.initialize_role()
            elif not antispam_cog:
                self.logger.warning("AntiSpam cog not found in on_ready.")

            # Check CommandHandler dependencies (optional check)
            command_handler = self.bot.get_cog('CommandHandler')
            if command_handler and hasattr(command_handler, 'analysis_handler') and command_handler.analysis_handler and hasattr(command_handler.analysis_handler, 'symbol_manager') and command_handler.analysis_handler.symbol_manager:
                self.logger.debug("CommandHandler has access to SymbolManager.")
            elif command_handler:
                self.logger.warning("CommandHandler does not have SymbolManager set (or check failed).")
            else:
                self.logger.warning("CommandHandler cog not found in on_ready.")

            # Set initialized flag and set the ready event
            self.is_initialized = True
            self._ready_event.set()
            self.logger.debug("DiscordNotifier fully initialized and ready.")

        except Exception as e:
            self.logger.error(f"Error in on_ready: {e}", exc_info=True)

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            # Track the user's message for deletion
            await self.file_handler.track_message(
                message_id=ctx.message.id,
                channel_id=ctx.channel.id,
                user_id=ctx.author.id,
                message_type="user_command",
                expire_after=300  # Also expire after 5 minutes
            )
            
            # Provide help message for unknown commands
            help_embed = discord.Embed(
                title="❓ Command Not Found",
                description="I don't recognize that command. Here's how to use this bot:",
                color=discord.Colour.blue()
            )
            
            help_embed.add_field(
                name="Analysis Command",
                value="Type `!analyze base/quote language`\nExample: `!analyze BTC/USDC English`",
                inline=False
            )
            
            help_embed.add_field(
                name="Available Languages",
                value=", ".join(sorted(SUPPORTED_LANGUAGES.keys())),
                inline=False
            )
            
            help_embed.set_footer(text="Market analysis is limited by cooldown periods")
            
            # Use the file handler to track and automatically delete this help message later
            await self.send_message(
                message="",
                channel_id=ctx.channel.id,
                embed=help_embed,
                user_id=ctx.author.id,
                expire_after=300  # Expire after 5 minutes
            )
            return
            
        # Log other errors
        self.logger.error(f"An error occurred while executing a command: {str(error)}")


    async def __aenter__(self):
        if self.session is None:
            self.session = ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            try:
                await self.session.close()
                self.session = None
            except Exception as e:
                self.logger.warning(f"Session close error: {e}")

        if self.file_handler:
            try:
                await self.file_handler.shutdown()
            except Exception as e:
                self.logger.warning(f"Error during file handler shutdown: {e}")
        
        if self.bot:
            try:
                self.logger.info("Closing Discord bot connection...")
                command_handler = self.bot.get_cog('CommandHandler')
                if command_handler and hasattr(command_handler, 'cleanup'):
                    try:
                        await asyncio.wait_for(command_handler.cleanup(), timeout=5.0)
                    except Exception as e:
                        self.logger.warning(f"Error during command handler cleanup: {e}")
                
                await asyncio.sleep(0.5)
                
                try:
                    await asyncio.wait_for(self.bot.close(), timeout=2.0)
                except asyncio.TimeoutError:
                    self.logger.warning("Bot close operation timed out")
            except Exception as e:
                self.logger.warning(f"Error closing Discord bot: {e}")
                
        self.logger.info("Discord notifier resources released")

    async def start(self) -> None:
        if not self.bot:
            self.logger.error("Discord bot is not initialized.")
            return
        try:
            await self.bot.start(BOT_TOKEN_DISCORD)
        except discord.LoginFailure as e:
            self.logger.error(f"Discord Login Failure: {e}. Check your BOT_TOKEN_DISCORD.", exc_info=True)
        except discord.PrivilegedIntentsRequired as e:
            self.logger.error(f"Privileged intents required but not enabled: {e}", exc_info=True)
        except Exception as e:
            self.logger.error(f"Failed to start Discord bot: {e}", exc_info=True)

        return None
    
    # Wait for the bot to fully initialize
    async def wait_until_ready(self) -> None:
        await self._ready_event.wait()
        
    @retry_async(max_retries=3, initial_delay=1, backoff_factor=2, max_delay=30)
    async def send_message(
            self,
            message: str,
            channel_id: int,
            file: Optional[discord.File] = None,
            embed: Optional[discord.Embed] = None,
            user_id: Optional[int] = None,
            expire_after: Optional[int] = FILE_MESSAGE_EXPIRY
    ):
        await self.wait_until_ready()
        channel = self.bot.get_channel(channel_id)
        if not channel:
            self.logger.error(f"Channel with ID {channel_id} not found.")
            return None

        try:
            sent_message = await channel.send(content=message[:2000], file=file, embed=embed)
            
            message_type = "file" if file else ("embed" if embed else "message")
            
            # Track the message for deletion
            await self.file_handler.track_message(
                message_id=sent_message.id,
                channel_id=channel_id,
                user_id=user_id,
                message_type=message_type,
                expire_after=expire_after
            )
            self.logger.debug(f"Automatically tracking sent {message_type} (ID: {sent_message.id})")
            
            return sent_message
        except discord.HTTPException as e:
            self.logger.error(f"Discord HTTPException when sending message: {e}", exc_info=True)
        except Exception as e:
            self.logger.error(f"Unexpected error when sending message: {e}", exc_info=True)
            return None
        
        return None

    def _finalize_embed(self, embed: discord.Embed, thumbnail_url: str, image_url: str) -> None:
        """Add thumbnail, image, and footer to embeds"""
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url or self.BOT_LOGO_URL)
        # Keeping image_url parameter for backward compatibility, but we won't use it for now
        embed.set_footer(
            text=f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"[:2048]
        )

        
    def create_analysis_embed(self, analysis_result: Dict[str, Any], symbol: str, analysis_file_url: Optional[str] = None, 
                            thumbnail_url: Optional[str] = None, image_url: Optional[str] = None, language: Optional[str] = None) -> discord.Embed:
        """Create a Discord embed for market analysis results"""
        analysis = analysis_result.get("analysis", {})
        
        # Create base embed
        embed = self._create_base_embed(analysis, symbol, language)
        
        # Add core analysis fields
        self._add_core_analysis_fields(embed, analysis)
        
        # Add optional fields
        self._add_optional_analysis_fields(embed, analysis)
        
        # Add detailed analysis link if available
        if analysis_file_url:
            embed.add_field(
                name="📊 Detailed Analysis",
                value=f"[Download detailed analysis]({analysis_file_url}) (expires in 24 hours)",
                inline=False
            )
        
        self._finalize_embed(embed, thumbnail_url, image_url)
        return embed
    
    def _create_base_embed(self, analysis: Dict[str, Any], symbol: str, language: Optional[str]) -> discord.Embed:
        """Create the base embed with title, description, and color"""
        summary = analysis.get("summary", "No summary available")
        trend = analysis.get("observed_trend", "NEUTRAL")
        
        # Determine embed color based on trend
        color = self._get_trend_color(trend)
        
        # Add language indicator to title if provided
        language_suffix = f" ({language})" if language else ""
        
        return discord.Embed(
            title=f"🚀 {symbol} Market Analysis{language_suffix}",
            description=summary,
            color=color
        )
    
    def _get_trend_color(self, trend: str) -> discord.Colour:
        """Get the appropriate color for the trend"""
        if trend == "BULLISH":
            return discord.Colour.green()
        elif trend == "BEARISH":
            return discord.Colour.red()
        else:
            return discord.Colour.light_grey()
    
    def _add_core_analysis_fields(self, embed: discord.Embed, analysis: Dict[str, Any]) -> None:
        """Add core analysis fields to the embed"""
        trend = analysis.get("observed_trend", "NEUTRAL")
        trend_strength = analysis.get("trend_strength", 0)
        confidence = analysis.get("confidence_score", 0)
        technical_bias = analysis.get("technical_bias", "NEUTRAL")
        market_structure = analysis.get("market_structure", "NEUTRAL")
        risk_ratio = analysis.get("risk_ratio", None)
        
        embed.add_field(name="Trend", value=trend, inline=True)
        embed.add_field(name="Trend Strength", value=f"{trend_strength}/100", inline=True)
        embed.add_field(name="Analysis Confidence", value=f"{confidence}/100", inline=True)
        embed.add_field(name="Technical Bias", value=technical_bias, inline=False)
        embed.add_field(name="Market Structure", value=market_structure, inline=True)
        
        # Add risk ratio if available
        if risk_ratio is not None:
            embed.add_field(name="Risk/Reward Ratio", value=f"{risk_ratio:.2f}", inline=True)
    
    def _add_optional_analysis_fields(self, embed: discord.Embed, analysis: Dict[str, Any]) -> None:
        """Add optional analysis fields to the embed"""
        # Add timeframes analysis
        timeframes = analysis.get("timeframes", {})
        if timeframes:
            self._add_timeframes_field(embed, timeframes)
        
        # Add news summary
        news_summary = analysis.get("news_summary")
        if news_summary:
            embed.add_field(
                name="📰 News Summary",
                value=news_summary[:1024],  # Limit length for embed field
                inline=False
            )
        
        # Add price scenarios
        price_scenarios = analysis.get("price_scenarios", {})
        if price_scenarios:
            self._add_price_scenarios_field(embed, price_scenarios)
        
        # Add key levels
        key_levels = analysis.get("key_levels", {})
        if key_levels:
            self._add_key_levels_fields(embed, key_levels)
    
    def _add_timeframes_field(self, embed: discord.Embed, timeframes: Dict[str, Any]) -> None:
        """Add timeframes analysis field to the embed"""
        timeframe_values = []
        short_term = timeframes.get("short_term", "NEUTRAL")
        medium_term = timeframes.get("medium_term", "NEUTRAL")
        long_term = timeframes.get("long_term", "NEUTRAL")
        
        timeframe_values.append(f"Short-term: {short_term}")
        timeframe_values.append(f"Medium-term: {medium_term}")
        timeframe_values.append(f"Long-term: {long_term}")
        
        embed.add_field(
            name="Timeframe Analysis",
            value="\n".join(timeframe_values),
            inline=False
        )
    
    def _add_price_scenarios_field(self, embed: discord.Embed, price_scenarios: Dict[str, Any]) -> None:
        """Add price scenarios field to the embed"""
        scenario_values = []
        
        bullish_scenario = price_scenarios.get('bullish_scenario')
        bearish_scenario = price_scenarios.get('bearish_scenario')
        
        if bullish_scenario is not None:
            scenario_values.append(f"Bullish: ${bullish_scenario}")
        else:
            scenario_values.append(f"Bullish: N/A")
            
        if bearish_scenario is not None:
            scenario_values.append(f"Bearish: ${bearish_scenario}")
        else:
            scenario_values.append(f"Bearish: N/A")
            
        embed.add_field(name="Price Scenarios", value="\n".join(scenario_values), inline=False)
    
    def _add_key_levels_fields(self, embed: discord.Embed, key_levels: Dict[str, Any]) -> None:
        """Add support and resistance levels fields to the embed"""
        support_values = [f"${level}" for level in key_levels.get("support", [])]
        resistance_values = [f"${level}" for level in key_levels.get("resistance", [])]
        
        if support_values:
            embed.add_field(name="Support Levels", value="\n".join(support_values), inline=True)
        if resistance_values:
            embed.add_field(name="Resistance Levels", value="\n".join(resistance_values), inline=True)

    async def send_context_message(
            self,
            ctx,
            message: str,
            file: Optional[discord.File] = None,
            embed: Optional[discord.Embed] = None,
            expire_after: Optional[int] = FILE_MESSAGE_EXPIRY
    ):
        user_id = ctx.author.id if ctx and hasattr(ctx, 'author') else None
        return await self.send_message(
            message=message,
            channel_id=ctx.channel.id,
            file=file,
            embed=embed,
            user_id=user_id,
            expire_after=expire_after
        )

    async def upload_analysis_content(self, html_content: str, symbol: str, channel_id: int):
        self.logger.debug(f"Preparing to upload analysis for {symbol}")
        
        # Create filename with symbol
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{symbol.replace('/', '')}_analysis_{timestamp}.html"
        
        try:
            # Convert HTML content to bytes
            content_bytes = html_content.encode('utf-8')
            
            # Create Discord file object from bytes
            file = discord.File(
                fp=io.BytesIO(content_bytes),
                filename=filename
            )
            
            # Use existing send_message method which handles tracking
            message = await self.send_message(
                message=f"📊 Analysis for {symbol}",
                channel_id=channel_id,
                file=file
            )
            
            if message and message.attachments:
                url = message.attachments[0].url
                self.logger.debug(f"Uploaded analysis for {symbol}: {url}")
                return url
            else:
                self.logger.error(f"Failed to upload analysis for {symbol}: No attachments found")
                return None
                
        except Exception as e:
            self.logger.error(f"Error uploading analysis for {symbol}: {e}")
            return None
