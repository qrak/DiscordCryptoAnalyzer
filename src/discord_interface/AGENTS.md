# Discord Interface Agents Documentation

This document describes all Discord bot agents (cogs) and command handlers available in the DiscordCryptoAnalyzer system.

## Overview

The Discord interface layer provides a modular cog-based architecture that handles bot lifecycle, user commands, anti-spam protection, and message interactions. Each cog is a specialized agent responsible for specific Discord integration concerns.

## Bot Cogs (Discord Agents)

### CommandHandler Cog

**Location**: `src/discord_interface/cogs/command_handler.py`

**Purpose**: Main command processing agent for market analysis and cryptocurrency operations.

**Responsibilities**:
- Parse and validate user commands (e.g., `!analyze BTC/USDT 4h`)
- Route commands to appropriate handlers
- Manage command lifecycle and execution
- Track user commands for message expiration
- Build and send analysis responses to Discord

**Key Components**:
- `CommandValidator`: Validates command syntax and parameters
- `ResponseBuilder`: Formats and structures bot responses
- `ErrorHandler`: Manages command execution errors
- `AnalysisHandler`: Routes analysis requests to the market analyzer

**Usage**:
- Commands are auto-loaded via `setup_bot()` in `DiscordNotifier`
- Handles symbol validation, timeframe selection, and analysis triggers
- Returns rich embeds with analysis results and charts

### AntiSpam Cog

**Location**: `src/discord_interface/cogs/anti_spam.py`

**Purpose**: Protects bot from spam and abuse via rate limiting and user restrictions.

**Responsibilities**:
- Track command usage per user and channel
- Enforce rate limits on command execution
- Maintain anti-spam role assignments
- Prevent abuse in non-designated channels

**Features**:
- Configurable spam thresholds
- Channel whitelist for temporary/testing channels
- User-level rate limiting
- Role-based access control

**Integration**: Loaded in `DiscordNotifier.setup_bot()` and initialized in `on_ready()`

### ReactionHandler Cog

**Location**: `src/discord_interface/cogs/reaction_handler.py`

**Purpose**: Handles user reactions to bot messages for interactive features.

**Responsibilities**:
- Process reaction additions to tracked messages
- Support interactive UI patterns (e.g., pagination, action buttons)
- Trigger analysis refinements or chart re-generations based on reactions

**Current Status**: Placeholder for future reaction-based functionality

**Extensibility**: Can be extended for interactive analysis workflows

## Command Handler Architecture

### AnalysisHandler

**Purpose**: Orchestrates market analysis requests from Discord commands.

**Features**:
- Validates cryptocurrency symbols and trading pairs
- Manages timeframe selection (1h, 2h, 4h, 6h, 8h, 12h, 1d)
- Executes analysis engine with proper error handling
- Formats analysis results for Discord display

**Integration Points**:
- Receives validated commands from `CommandValidator`
- Calls `MarketAnalyzer` (AnalysisEngine) for technical analysis
- Returns results via `ResponseBuilder` for Discord formatting

### CommandValidator

**Purpose**: Ensures command syntax and semantics are correct before execution.

**Validation Rules**:
- Symbol format validation (e.g., BTC/USDT, ETH/USDC)
- Timeframe validation against supported periods
- Parameter count and type checking
- User permission validation

**Returns**: `ValidationResult` with pass/fail status and error messages

### ResponseBuilder

**Purpose**: Constructs Discord-compatible responses from analysis data.

**Output Formats**:
- Rich embeds with analysis summary
- File uploads with HTML charts and reports
- Error messages with helpful guidance
- Status messages with formatting

### ErrorHandler

**Purpose**: Centralized error management for Discord operations.

**Handles**:
- Message deletion failures
- Command execution exceptions
- API rate limiting and timeouts
- User input validation errors

**Behavior**: Logs errors, sends user-friendly error messages, provides recovery guidance

## Message Lifecycle Management

### Tracked Messages

**FileHandler Integration**: `src/discord_interface/filehandler.py`

**Responsibilities**:
- Track analysis messages sent by the bot
- Implement automatic message expiration (configurable TTL)
- Clean up old messages to prevent channel clutter
- Manage associated files and HTML reports

**Features**:
- Persistent message tracking (`data/tracked_messages.json`)
- Scheduled cleanup tasks
- Integration with analysis response workflow

## Bot Lifecycle

### Initialization Flow

1. `DiscordNotifier.__init__()`: Creates bot instance and event handlers
2. `setup_bot()` (setup_hook): Loads all cogs (AntiSpam, ReactionHandler, CommandHandler)
3. `on_ready()`: Initializes file handler and finalizes setup
4. Commands are now ready to process

### Shutdown Flow (Reverse Order)

1. Flush any pending messages
2. Save tracked message state
3. Clean up resources in AntiSpam cog
4. Close Discord connection

## Cog Loading Pattern (for adding new cogs)

```python
# In DiscordNotifier.setup_bot():
self.logger.debug("Adding MyNewCog...")
await self.bot.add_cog(MyNewCog(self.bot, self.logger, other_deps))
self.logger.debug("MyNewCog added.")
```

## Usage in Analysis

These cogs work together to provide a complete Discord bot experience:
1. User sends command via Discord
2. CommandHandler validates and routes
3. AnalysisHandler executes analysis
4. ResponseBuilder formats response
5. DiscordNotifier sends message and tracks it
6. FileHandler manages message lifecycle
7. AntiSpam enforces rate limits

## Common Patterns

### Adding a New Command

1. Extend `CommandHandler` cog
2. Add command method with `@commands.command()` decorator
3. Use `CommandValidator` to validate inputs
4. Call appropriate analyzer/manager
5. Use `ResponseBuilder` to format output
6. Track message with `FileHandler`

### Error Handling in Commands

Use `ErrorHandler.handle_*()` methods for consistent error reporting:
- `handle_message_deletion_error()`: For message cleanup failures
- `handle_command_execution_error()`: For general command errors
- Custom error handling via `on_command_error()` listener

## Configuration

- `config/config.ini`: Bot settings, timeframes, analysis parameters
- `keys.env`: Discord bot token, API keys
- Rate limits: Configurable via AntiSpam cog settings
- Message expiry: `FILE_MESSAGE_EXPIRY` in config

## Integration with Other Modules

- **AnalysisEngine** (`src/analyzer/core/analysis_engine.py`): Provides market analysis
- **DiscordNotifier** (`notifier.py`): Manages bot lifecycle and message sending
- **DiscordFileHandler** (`filehandler.py`): Manages message tracking and cleanup
- **SymbolManager** (`src/platforms/exchange_manager.py`): Validates trading pairs
- **RAGEngine** (`src/rag/`): Provides context-aware responses

## Troubleshooting

- **Commands not loading**: Check `setup_bot()` logs, ensure cog syntax is correct
- **Rate limiting too strict**: Adjust thresholds in `AntiSpam` configuration
- **Message tracking issues**: Check `data/tracked_messages.json` format
- **Missing reactions**: Ensure `ReactionHandler` is loaded and Discord intents are enabled
