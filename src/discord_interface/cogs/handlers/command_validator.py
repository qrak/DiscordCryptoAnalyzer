"""
Command validation utilities for Discord bot commands.
Handles input validation, permission checks, and cooldown management.
"""
import re
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Union
from dataclasses import dataclass
from discord.ext import commands

from src.utils.loader import config
from src.utils.timeframe_validator import TimeframeValidator


@dataclass
class ValidationResult:
    """Result of command validation."""
    is_valid: bool
    symbol: Optional[str] = None
    timeframe: Optional[str] = None
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
        if requested_lang in config.SUPPORTED_LANGUAGES:
            return True, requested_lang
        return False, None
    
    def validate_channel(self, channel_id: int) -> bool:
        """Validate that command is used in correct channel."""
        return channel_id == config.MAIN_CHANNEL_ID
    
    def _is_valid_timeframe(self, arg: str) -> bool:
        """
        Check if argument looks like a valid timeframe.
        
        Args:
            arg: Potential timeframe string
            
        Returns:
            bool: True if argument is a valid timeframe
        """
        if not arg:
            return False
        
        arg_lower = arg.lower()
        # Only accept timeframes explicitly in our supported list
        return arg_lower in TimeframeValidator.TIMEFRAME_MINUTES
    
    def validate_command_args(self, args: list) -> Tuple[bool, Optional[str], Optional[str], Tuple[Optional[str], Optional[str], Optional[str]]]:
        """
        Validate command arguments for analyze command with flexible timeframe and language support.
        
        Supported patterns:
        - !analyze BTC/USDT               → symbol, default timeframe, English
        - !analyze BTC/USDT 4h            → symbol, 4h timeframe, English
        - !analyze BTC/USDT Polish        → symbol, default timeframe, Polish
        - !analyze BTC/USDT 4h Polish     → symbol, 4h timeframe, Polish
        
        Returns:
            Tuple of (is_valid, error_message, usage_message, (symbol, timeframe, language))
        """
        if not args:
            return False, "Missing arguments", self._get_usage_message(), (None, None, None)
        
        symbol = args[0].upper()
        if not self.validate_symbol_format(symbol):
            return False, "Invalid symbol format. Use format like `BTC/USDT`.", None, (None, None, None)
        
        timeframe = None  # Will use config default if None
        language = None
        
        # Parse remaining arguments (can be timeframe, language, or both)
        if len(args) == 2:
            # Could be timeframe or language
            arg = args[1]
            
            # Try as timeframe first
            if self._is_valid_timeframe(arg):
                timeframe = arg.lower()
            else:
                # Try as language
                is_valid_lang, validated_lang = self.validate_language(arg)
                if is_valid_lang:
                    language = validated_lang
                else:
                    # Not a valid timeframe or language
                    return False, f"Invalid argument '{arg}'. Must be a timeframe (1h, 2h, 4h, 6h, 8h, 12h, 1d) or language.", None, (None, None, None)
        
        elif len(args) >= 3:
            # Two optional args: assume timeframe then language
            timeframe_arg = args[1]
            language_arg = args[2]
            
            # Validate timeframe
            if not self._is_valid_timeframe(timeframe_arg):
                return False, f"Invalid timeframe '{timeframe_arg}'. Supported: 1h, 2h, 4h, 6h, 8h, 12h, 1d", None, (None, None, None)
            timeframe = timeframe_arg.lower()
            
            # Validate language
            is_valid_lang, validated_lang = self.validate_language(language_arg)
            if not is_valid_lang:
                supported_langs = ", ".join(config.SUPPORTED_LANGUAGES.keys())
                return False, f"Unsupported language '{language_arg}'. Available: {supported_langs}", None, (None, None, None)
            language = validated_lang
        
        return True, None, None, (symbol, timeframe, language)
    
    def _get_usage_message(self) -> str:
        """Get command usage message."""
        return (
            "Usage: `!analyze <SYMBOL> [TIMEFRAME] [LANGUAGE]`\n"
            "Examples:\n"
            "  `!analyze BTC/USDT` - Analyze with default settings\n"
            "  `!analyze BTC/USDT 4h` - Analyze on 4-hour timeframe\n"
            "  `!analyze BTC/USDT Polish` - Analyze in Polish\n"
            "  `!analyze BTC/USDT 1d English` - Daily timeframe in English\n"
            "Supported timeframes: 1h, 2h, 4h, 6h, 8h, 12h, 1d"
        )
    
    def check_analysis_in_progress(self, symbol: str) -> bool:
        """Check if analysis is already in progress for symbol."""
        is_in_progress = symbol in self.ongoing_analyses
        if is_in_progress and self.logger:
            self.logger.debug(f"Analysis already in progress for {symbol}")
        return is_in_progress

    def add_ongoing_analysis(self, symbol: str) -> None:
        """Mark symbol as having analysis in progress."""
        if symbol in self.ongoing_analyses and self.logger:
            self.logger.warning(f"Attempt to add ongoing analysis for {symbol} but it's already marked as ongoing - potential race condition")
        self.ongoing_analyses.add(symbol)
        if self.logger:
            self.logger.debug(f"Marked {symbol} as having analysis in progress. Current ongoing: {list(self.ongoing_analyses)}")

    def remove_ongoing_analysis(self, symbol: str) -> None:
        """Remove symbol from ongoing analyses."""
        if symbol not in self.ongoing_analyses and self.logger:
            self.logger.warning(f"Attempt to remove ongoing analysis for {symbol} but it's not marked as ongoing")
        self.ongoing_analyses.discard(symbol)
        if self.logger:
            self.logger.debug(f"Removed {symbol} from ongoing analyses. Current ongoing: {list(self.ongoing_analyses)}")
    
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
        # Validate arguments (now returns 4-tuple)
        is_valid, error_msg, usage, (symbol, timeframe, language) = self.validate_command_args(args)
        if not is_valid:
            return ValidationResult(is_valid=False, error_message=f"{error_msg}\n{usage}" if usage else error_msg)

        # If timeframe provided, validate it's fully supported
        if timeframe:
            try:
                timeframe = TimeframeValidator.validate_and_normalize(timeframe)
            except ValueError as e:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"⚠️ {str(e)}"
                )

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

        return ValidationResult(is_valid=True, symbol=symbol, timeframe=timeframe, language=language)
    
    def is_admin(self, ctx: commands.Context) -> bool:
        """Check if user has admin permissions."""
        return ctx.author.guild_permissions.administrator
