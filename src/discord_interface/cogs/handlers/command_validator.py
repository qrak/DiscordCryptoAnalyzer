"""
Command validation utilities for Discord bot commands.
Handles input validation, permission checks, and cooldown management.
"""
import re
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Union
from dataclasses import dataclass
from discord.ext import commands

from config import MAIN_CHANNEL_ID, SUPPORTED_LANGUAGES


@dataclass
class ValidationResult:
    """Result of command validation."""
    is_valid: bool
    symbol: Optional[str] = None
    language: Optional[str] = None
    error_message: Optional[str] = None


class CommandValidator:
    """Handles validation of commands and user permissions."""
    
    def __init__(self, logger):
        self.logger = logger
        self.coin_cooldowns: Dict[str, datetime] = {}
        self.user_cooldowns: Dict[int, datetime] = {}
        self.ongoing_analyses: set[str] = set()
    
    def validate_symbol_format(self, symbol: str) -> bool:
        """Validate that symbol follows the correct format."""
        return bool(re.match(r'^[A-Za-z0-9]+/USD[TC]?$', symbol))
    
    def validate_language(self, language: str) -> Tuple[bool, Optional[str]]:
        """
        Validate requested language.
        
        Returns:
            Tuple of (is_valid, validated_language)
        """
        if not language:
            return True, None
            
        requested_lang = language.capitalize()
        if requested_lang in SUPPORTED_LANGUAGES:
            return True, requested_lang
        return False, None
    
    def validate_channel(self, channel_id: int) -> bool:
        """Validate that command is used in correct channel."""
        return channel_id == MAIN_CHANNEL_ID
    
    def validate_command_args(self, args: list) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate command arguments for analyze command.
        
        Returns:
            Tuple of (is_valid, error_message, suggested_usage)
        """
        if not args:
            return False, "Missing arguments", "Usage: `!analyze <SYMBOL> [Language]`. Example: `!analyze BTC/USDT Polish`"
        
        symbol = args[0].upper()
        if not self.validate_symbol_format(symbol):
            return False, "Invalid symbol format. Use format like `BTC/USDT`.", None
        
        language = None
        if len(args) > 1:
            is_valid_lang, validated_lang = self.validate_language(args[1])
            if not is_valid_lang:
                supported_langs = ", ".join(SUPPORTED_LANGUAGES.keys())
                return False, f"Unsupported language '{args[1]}'. Available: {supported_langs}", None
            language = validated_lang
        
        return True, None, None
    
    def check_analysis_in_progress(self, symbol: str) -> bool:
        """Check if analysis is already in progress for symbol."""
        return symbol in self.ongoing_analyses
    
    def add_ongoing_analysis(self, symbol: str) -> None:
        """Mark symbol as having analysis in progress."""
        self.ongoing_analyses.add(symbol)
    
    def remove_ongoing_analysis(self, symbol: str) -> None:
        """Remove symbol from ongoing analyses."""
        self.ongoing_analyses.discard(symbol)
    
    def check_cooldown(self, key: Union[str, int], cooldown_duration: int, 
                      cooldown_dict: Dict[Union[str, int], datetime]) -> Tuple[bool, Optional[str]]:
        """
        Check if key is on cooldown.
        
        Returns:
            Tuple of (is_on_cooldown, time_remaining_message)
        """
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
                return True, time_str
        return False, None
    
    def check_coin_cooldown(self, symbol: str, cooldown_duration: int) -> Tuple[bool, Optional[str]]:
        """Check coin-specific cooldown."""
        return self.check_cooldown(symbol, cooldown_duration, self.coin_cooldowns)
    
    def check_user_cooldown(self, user_id: int, cooldown_duration: int) -> Tuple[bool, Optional[str]]:
        """Check user-specific cooldown."""
        return self.check_cooldown(user_id, cooldown_duration, self.user_cooldowns)
    
    def update_cooldowns(self, symbol: str, user_id: int) -> None:
        """Update cooldowns for symbol and user."""
        current_time = datetime.now()
        self.coin_cooldowns[symbol] = current_time
        self.user_cooldowns[user_id] = current_time
    
    def validate_full_analysis_request(self, ctx: commands.Context, args: list, 
                                      analysis_cooldown_coin: int, analysis_cooldown_user: int) -> ValidationResult:
        """
        Perform complete validation of analysis request.
        
        Returns ValidationResult with all validation outcomes.
        """
        # Validate arguments
        is_valid, error_msg, usage = self.validate_command_args(args)
        if not is_valid:
            return ValidationResult(is_valid=False, error_message=f"{error_msg}\n{usage}" if usage else error_msg)

        symbol = args[0].upper()
        language = None
        if len(args) > 1:
            _, language = self.validate_language(args[1])

        # Check if analysis is already in progress
        if self.check_analysis_in_progress(symbol):
            return ValidationResult(is_valid=False, error_message=f"⏳ {symbol} is currently being analyzed. Please wait.")

        # Check cooldowns for non-admin users
        if not self.is_admin(ctx):
            # Check coin cooldown
            is_on_cooldown, time_remaining = self.check_coin_cooldown(symbol, analysis_cooldown_coin)
            if is_on_cooldown:
                return ValidationResult(is_valid=False, error_message=f"⌛ {symbol} was analyzed recently. Try again in {time_remaining}.")
            
            # Check user cooldown
            is_on_cooldown, time_remaining = self.check_user_cooldown(ctx.author.id, analysis_cooldown_user)
            if is_on_cooldown:
                return ValidationResult(is_valid=False, error_message=f"⌛ {ctx.author.mention}, you can request another analysis in {time_remaining}.")

        return ValidationResult(is_valid=True, symbol=symbol, language=language)
    
    def is_admin(self, ctx: commands.Context) -> bool:
        """Check if user has admin permissions."""
        return ctx.author.guild_permissions.administrator
