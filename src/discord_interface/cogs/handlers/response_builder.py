"""
Response building utilities for Discord bot commands.
Handles creating embeds, messages, and formatting responses.
"""
from typing import Optional, TYPE_CHECKING
import discord

if TYPE_CHECKING:
    from src.contracts.config import ConfigProtocol

from src.utils.timeframe_validator import TimeframeValidator


class ResponseBuilder:
    """Handles building Discord responses and embeds."""
    
    def __init__(self, logger, config: 'ConfigProtocol' = None):
        self.logger = logger
        self.config = config
    
    def build_analysis_embed(self, symbol: str, user: discord.Member, language: Optional[str] = None, timeframe: Optional[str] = None, provider: Optional[str] = None, model: Optional[str] = None) -> discord.Embed:
        """Build embed for analysis start confirmation."""
        language_text = f" in {language}" if language else ""
        timeframe_text = f" on {timeframe} timeframe" if timeframe else ""
        provider_text = f"\nProvider: {provider}" if provider else ""
        model_text = f"\nModel: {model}" if model else ""
        embed = discord.Embed(
            title=f"🔍 Analyzing {symbol}{language_text}",
            description=f"Requested by {user.mention}{timeframe_text}{provider_text}{model_text}\nResults will be posted when ready.",
            color=discord.Colour.blue()
        )
        embed.set_footer(text="This may take from one to five minutes, depending on the model's complexity.")
        return embed
    
    def build_success_message(self, symbol: str, action: str = "completed") -> str:
        """Build success message."""
        return f"✅ Analysis of {symbol} {action}!"
    
    def build_error_message(self, symbol: str, error: str) -> str:
        """Build error message."""
        return f"⚠️ Analysis of {symbol} failed: {error}"
    
    def build_shutdown_message(self) -> str:
        """Build shutdown message."""
        return "⚠️ Bot is shutting down, command not available."
    
    def build_wrong_channel_message(self, main_channel_id: int) -> str:
        """Build wrong channel message."""
        return f"⚠️ This command can only be used in <#{main_channel_id}>."
    
    def build_cleanup_start_message(self) -> str:
        """Build cleanup start message."""
        return "🧹 Starting message cleanup..."
    
    def build_cleanup_complete_message(self, deleted_count: int) -> str:
        """Build cleanup completion message."""
        return f"✅ Cleanup complete! Deleted {deleted_count} expired messages."
    
    def build_cleanup_error_message(self) -> str:
        """Build cleanup error message."""
        return "❌ File handler not available."
    
    def build_help_embed(self, title: str = "📖 Bot Help", include_command_not_found: bool = False) -> discord.Embed:
        """Build help embed with bot usage information.
        
        Args:
            title: Embed title (default: "📖 Bot Help")
            include_command_not_found: If True, uses "❓ Command Not Found" title and adjusted description
            
        Returns:
            discord.Embed: Help embed with command examples and supported options
        """
        if include_command_not_found:
            title = "❓ Command Not Found"
            description = "I don't recognize that command. Here's how to use this bot:"
        else:
            description = "Here's how to use this bot:"
        
        help_embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Colour.blue()
        )
        
        # Get supported timeframes from TimeframeValidator
        supported_timeframes = ", ".join(TimeframeValidator.SUPPORTED_TIMEFRAMES)
        
        help_embed.add_field(
            name="Analysis Command",
            value=(
                "Type `!analyze <SYMBOL> [TIMEFRAME] [LANGUAGE]`\n"
                "Examples:\n"
                "`!analyze BTC/USDC` - Default timeframe, English\n"
                "`!analyze BTC/USDC 4h` - 4-hour timeframe\n"
                "`!analyze BTC/USDC Polish` - Polish language\n"
                "`!analyze BTC/USDC 1d English` - Daily, English\n"
                f"Supported timeframes: {supported_timeframes}"
            ),
            inline=False
        )
        
        # Get available languages from config if available
        if self.config and hasattr(self.config, 'SUPPORTED_LANGUAGES'):
            languages = ", ".join(sorted(self.config.SUPPORTED_LANGUAGES.keys()))
        else:
            languages = "English, Polish, Spanish, French, German, Chinese, Japanese, Russian"
        
        help_embed.add_field(
            name="Available Languages",
            value=languages,
            inline=False
        )
        
        help_embed.set_footer(text="Market analysis is limited by cooldown periods")
        
        return help_embed
