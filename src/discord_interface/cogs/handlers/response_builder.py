"""
Response building utilities for Discord bot commands.
Handles creating embeds, messages, and formatting responses.
"""
from datetime import datetime
from typing import Optional
import discord


class ResponseBuilder:
    """Handles building Discord responses and embeds."""
    
    def __init__(self, logger):
        self.logger = logger
    
    def build_analysis_embed(self, symbol: str, user: discord.Member, language: Optional[str] = None) -> discord.Embed:
        """Build embed for analysis start confirmation."""
        language_text = f" in {language}" if language else ""
        embed = discord.Embed(
            title=f"🔍 Analyzing {symbol}{language_text}",
            description=f"Requested by {user.mention}\nResults will be posted when ready.",
            color=discord.Colour.blue()
        )
        embed.set_footer(text="This may take up to a minute.")
        return embed
    
    def build_cooldown_message(self, cooldown_type: str, key: str, time_remaining: str, user_mention: str = None) -> str:
        """Build cooldown notification message."""
        if cooldown_type == "coin":
            return f"⌛ {key} was analyzed recently. Try again in {time_remaining}."
        elif cooldown_type == "user":
            return f"⌛ {user_mention}, you can request another analysis in {time_remaining}."
        return f"⌛ Please wait {time_remaining} before trying again."
    
    def build_validation_error_message(self, error: str, usage: Optional[str] = None) -> str:
        """Build validation error message."""
        if usage:
            return f"{error}\n{usage}"
        return f"⚠️ {error}"
    
    def build_success_message(self, symbol: str, action: str = "completed") -> str:
        """Build success message."""
        return f"✅ Analysis of {symbol} {action}!"
    
    def build_error_message(self, symbol: str, error: str) -> str:
        """Build error message."""
        return f"⚠️ Analysis of {symbol} failed: {error}"
    
    def build_system_error_message(self, component: str) -> str:
        """Build system error message."""
        return f"⚠️ System error: {component} unavailable."
    
    def build_shutdown_message(self) -> str:
        """Build shutdown message."""
        return "⚠️ Bot is shutting down, command not available."
    
    def build_wrong_channel_message(self, main_channel_id: int) -> str:
        """Build wrong channel message."""
        return f"⚠️ This command can only be used in <#{main_channel_id}>."
    
    def build_analysis_in_progress_message(self, symbol: str) -> str:
        """Build analysis in progress message."""
        return f"⏳ {symbol} is currently being analyzed. Please wait."
    
    def build_symbol_not_found_message(self, symbol: str) -> str:
        """Build symbol not found message."""
        return f"⚠️ Symbol {symbol} not available."
    
    def build_cleanup_start_message(self) -> str:
        """Build cleanup start message."""
        return "🧹 Starting message cleanup..."
    
    def build_cleanup_complete_message(self, deleted_count: int) -> str:
        """Build cleanup completion message."""
        return f"✅ Cleanup complete! Deleted {deleted_count} expired messages."
    
    def build_cleanup_error_message(self) -> str:
        """Build cleanup error message."""
        return "❌ File handler not available."
