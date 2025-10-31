# Discord Interface Agents Documentation

This document describes all Discord bot agents (cogs) and command handlers available in the DiscordCryptoAnalyzer system.

## Overview

The Discord interface layer provides a modular cog-based architecture that handles bot lifecycle, user commands, anti-spam protection, and message interactions. Each cog is a specialized agent responsible for specific Discord integration concerns.

## Directory Structure

The `src/discord_interface/` directory contains a comprehensive Discord bot integration system organized into specialized components:

### Core Files
- **`AGENTS.md`**: This documentation file describing all Discord agents and their responsibilities
- **`notifier.py`**: Main bot orchestrator class (`DiscordNotifier`) managing bot lifecycle and cog coordination
- **`filehandler.py`**: Simplified file handler coordinating message tracking and cleanup operations
- **`__init__.py`**: Package initialization

### Cogs Subdirectory (`cogs/`)
Specialized Discord bot extensions (cogs) for different functionalities:
- **`command_handler.py`**: Main command processing cog for analysis requests
- **`anti_spam.py`**: Rate limiting and spam protection cog
- **`reaction_handler.py`**: User reaction handling cog (extensible for future features)
- **`handlers/`**: Command processing pipeline components
- **`__init__.py`**: Package initialization

### Command Handlers Subdirectory (`cogs/handlers/`)
Analysis command processing pipeline:
- **`analysis_handler.py`**: Core analysis workflow orchestration
- **`command_validator.py`**: Command syntax and parameter validation
- **`error_handler.py`**: Centralized error management and user feedback
- **`response_builder.py`**: Discord response formatting and embed creation
- **`__init__.py`**: Package initialization

### File Handler Components Subdirectory (`filehandler_components/`)
Specialized message lifecycle management:
- **`message_tracker.py`**: Core message tracking logic and expiration management
- **`tracking_persistence.py`**: JSON file persistence for tracked messages
- **`cleanup_scheduler.py`**: Background task scheduling for message cleanup
- **`message_deleter.py`**: Safe message deletion with error handling
- **`__init__.py`**: Package initialization

## Bot Cogs (Discord Agents)

### CommandHandler Cog

**Location**: `src/discord_interface/cogs/command_handler.py`

**Purpose**: Main command processing agent for market analysis and cryptocurrency operations via the `CommandHandler` class.

**Responsibilities**:
- Parse and validate user commands (e.g., `!analyze BTC/USDT 4h`)
- Route commands to appropriate specialized handlers
- Manage command lifecycle and execution with proper error handling
- Track user commands for message expiration and cleanup
- Build and send analysis responses to Discord with rich embeds

**Key Components**:
- **`AnalysisHandler`**: Orchestrates market analysis requests and workflow
- **`CommandValidator`**: Validates command syntax, symbols, and parameters
- **`ResponseBuilder`**: Formats analysis results into Discord-compatible embeds
- **`ErrorHandler`**: Manages command execution errors and user feedback

**Command Processing Pipeline**:
1. User sends command via Discord message
2. `CommandValidator` checks syntax and parameters
3. `AnalysisHandler` validates prerequisites and executes analysis
4. `ResponseBuilder` formats results with embeds and file uploads
5. Message is tracked via `DiscordFileHandler` for automatic cleanup

**Supported Commands**:
- `!analyze <symbol> [timeframe] [language]`: Main analysis command
- `!analyze help`: Display comprehensive help message with usage examples
- Symbol validation against thousands of trading pairs from multiple exchanges
- Timeframe support: 1h, 2h, 4h, 6h, 8h, 12h, 1d (configurable)
- Language support: English, Polish, Spanish, French, German, Chinese, Japanese, Russian
- Admin-only: `!analyze <symbol> [timeframe] [language] <provider> <model>` for AI provider/model override

**Integration**: Auto-loaded in `DiscordNotifier.setup_bot()` with dependencies injected

### AntiSpam Cog

**Location**: `src/discord_interface/cogs/anti_spam.py`

**Purpose**: Protects bot from spam and abuse via rate limiting, user restrictions, and channel controls.

**Responsibilities**:
- Track command usage per user and channel with configurable thresholds
- Enforce rate limits on command execution to prevent abuse
- Maintain anti-spam role assignments for user management
- Prevent spam in non-designated channels while allowing temporary channels
- Monitor and log suspicious activity patterns

**Key Features**:
- **Configurable Thresholds**: Adjustable spam detection parameters
- **Channel Whitelist**: Designated channels for testing and temporary use
- **User-Level Rate Limiting**: Per-user command frequency controls
- **Role-Based Access**: Anti-spam role management for user restrictions
- **Activity Logging**: Comprehensive logging of rate limit violations

**Rate Limiting Logic**:
- Tracks commands per user within time windows
- Applies exponential backoff for repeated violations
- Allows temporary channel overrides for development/testing
- Integrates with Discord role system for persistent restrictions

**Integration**: Loaded in `DiscordNotifier.setup_bot()` and role initialized in `on_ready()`

### ReactionHandler Cog

**Location**: `src/discord_interface/cogs/reaction_handler.py`

**Purpose**: Handles user reactions to bot messages for interactive features and user feedback.

**Responsibilities**:
- Process reaction additions and removals on tracked messages
- Support interactive UI patterns (pagination, action buttons, feedback)
- Trigger analysis refinements or chart re-generations based on user reactions
- Enable user feedback mechanisms for analysis quality assessment
- Route reaction events to appropriate handlers for custom actions

**Current Implementation**:
- **Event Listeners**: Monitors `on_reaction_add` and `on_reaction_remove` events
- **Message Validation**: Checks if reactions are on bot-tracked messages
- **Reaction Filtering**: Ignores reactions from the bot itself
- **Extensible Framework**: Ready for custom reaction-based workflows

**Future Capabilities** (Extensible Design):
- **Pagination Controls**: Navigate through multi-page analysis results
- **Chart Interactions**: Switch timeframes or indicators via reactions
- **User Feedback**: Rate analysis quality or request refinements
- **Quick Actions**: Trigger follow-up analysis or related commands

**Integration**: Loaded in `DiscordNotifier.setup_bot()` with reaction intents enabled

## Command Handler Architecture

### AnalysisHandler

**Location**: `src/discord_interface/cogs/handlers/analysis_handler.py`

**Purpose**: Orchestrates market analysis requests from Discord commands via the `AnalysisHandler` class.

**Key Features**:
- **Symbol Validation**: Validates cryptocurrency symbols and trading pairs against exchange data
- **Timeframe Management**: Supports multiple timeframes (1h, 2h, 4h, 6h, 8h, 12h, 1d) with proper scaling
- **Concurrent Analysis Protection**: Prevents multiple simultaneous analyses per user
- **Analysis Engine Integration**: Executes comprehensive technical analysis with error handling
- **Result Formatting**: Prepares analysis data for Discord display and file uploads

**Core Methods**:
- **`validate_analysis_prerequisites()`**: Ensures all required components (bot, analyzers) are available
- **`execute_analysis()`**: Runs the full analysis pipeline with timeout protection
- **`add_analysis_request()` / `remove_analysis_request()`**: Tracks ongoing analysis requests
- **`handle_analysis_timeout()`**: Manages long-running analysis operations

**Integration Points**:
- Receives validated commands from `CommandValidator` in `CommandHandler`
- Calls `AnalysisEngine` for technical analysis with market data
- Returns structured results to `ResponseBuilder` for Discord formatting
- Integrates with `SymbolManager` for trading pair validation

**Concurrency Management**:
- Global analysis lock to prevent concurrent access to shared analyzers
- Per-user tracking to prevent multiple simultaneous requests
- Graceful shutdown handling for cleanup of pending analyses

### CommandValidator

**Location**: `src/discord_interface/cogs/handlers/command_validator.py`

**Purpose**: Ensures command syntax and semantics are correct before execution via comprehensive validation.

**Validation Rules**:
- **Symbol Format**: Validates trading pair format (e.g., BTC/USDT, ETH/USDC, XRP/BTC)
- **Timeframe Validation**: Checks against supported periods (1h, 2h, 4h, 6h, 8h, 12h, 1d)
- **Parameter Count**: Ensures correct number of arguments for each command
- **Type Checking**: Validates parameter types and ranges
- **User Permissions**: Checks user access rights and rate limits

**Key Methods**:
- **`validate_command()`**: Main validation entry point returning `ValidationResult`
- **`validate_symbol_format()`**: Checks trading pair syntax and supported symbols
- **`validate_timeframe()`**: Verifies timeframe against configuration
- **`validate_user_permissions()`**: Checks anti-spam status and user restrictions

**Validation Result**:
- **`is_valid`**: Boolean indicating success/failure
- **`error_message`**: Detailed error description for user feedback
- **`sanitized_params`**: Cleaned and validated command parameters

**Integration**: Called by `CommandHandler` before routing to `AnalysisHandler`

### ResponseBuilder

**Location**: `src/discord_interface/cogs/handlers/response_builder.py`

**Purpose**: Constructs Discord-compatible responses from analysis data with rich formatting and media.

**Output Formats**:
- **Rich Embeds**: Analysis summaries with formatted fields, colors, and thumbnails
- **File Uploads**: HTML reports and chart images attached to messages
- **Error Messages**: User-friendly error descriptions with recovery suggestions
- **Status Messages**: Progress indicators and completion notifications

**Key Methods**:
- **`build_analysis_embed()`**: Creates rich Discord embeds from analysis results
- **`build_error_embed()`**: Formats error messages with appropriate styling
- **`upload_analysis_content()`**: Handles file uploads with retry logic
- **`format_analysis_summary()`**: Creates concise analysis previews

**Embed Features**:
- **Dynamic Colors**: Success (green), warning (yellow), error (red) color coding
- **Thumbnails**: Bot logo and asset-specific icons
- **Fields**: Organized sections for different analysis components
- **Timestamps**: Analysis generation time and expiry information
- **Links**: Direct links to uploaded HTML reports

**File Upload Handling**:
- **Retry Logic**: Automatic retry on upload failures
- **Size Validation**: Checks file size limits before upload
- **URL Tracking**: Returns public URLs for uploaded content
- **Cleanup Integration**: Coordinates with message tracking for automatic deletion

### ErrorHandler

**Location**: `src/discord_interface/cogs/handlers/error_handler.py`

**Purpose**: Centralized error management for Discord operations with user-friendly feedback.

**Error Categories Handled**:
- **Message Operations**: Deletion failures, upload errors, permission issues
- **Command Execution**: Analysis timeouts, validation failures, API errors
- **Rate Limiting**: Anti-spam violations, cooldown periods
- **User Input**: Invalid commands, unsupported symbols, malformed requests
- **System Issues**: Network timeouts, service unavailability, configuration errors

**Key Methods**:
- **`handle_command_error()`**: Processes command execution exceptions
- **`handle_message_deletion_error()`**: Manages message cleanup failures
- **`handle_analysis_error()`**: Formats analysis-specific error messages
- **`create_error_embed()`**: Builds user-friendly error embeds

**Error Response Strategy**:
- **User-Friendly Messages**: Translates technical errors into actionable feedback
- **Recovery Guidance**: Provides specific steps to resolve common issues
- **Logging**: Comprehensive error logging for debugging while hiding sensitive details
- **Fallback Handling**: Graceful degradation when services are unavailable

**Integration**: Called by `CommandHandler` and other cogs for consistent error handling

## Message Lifecycle Management

### Tracked Messages

**FileHandler Integration**: `src/discord_interface/filehandler.py` via specialized components

**Responsibilities**:
- Track analysis messages sent by the bot for automatic cleanup
- Implement configurable message expiration (TTL) to prevent channel clutter
- Clean up old messages and associated HTML reports
- Manage message lifecycle from creation to deletion

**Core Components**:
- **`MessageTracker`**: Handles tracking logic and expiration calculations
- **`TrackingPersistence`**: JSON file persistence for message data
- **`CleanupScheduler`**: Background task scheduling for periodic cleanup
- **`MessageDeleter`**: Safe message deletion with error handling and retry logic

**Features**:
- **Persistent Storage**: Message tracking data in `data/tracked_messages.json`
- **Configurable Expiry**: `FILE_MESSAGE_EXPIRY` setting controls message lifetime
- **Background Cleanup**: Scheduled tasks run every 2 hours by default
- **Thread-Safe Operations**: Proper locking for concurrent access
- **Error Recovery**: Handles deletion failures gracefully

**Message Data Structure**:
```json
{
  "message_id": {
    "channel_id": 123456789,
    "user_id": 987654321,
    "message_type": "analysis",
    "tracked_at": "2025-10-31T10:30:00",
    "expire_after": 3600,
    "expires_at": 1730373000.0
  }
}
```

**Integration**: All bot messages are automatically tracked via `DiscordNotifier.send_message()`

## DiscordNotifier (Main Orchestrator)

**Location**: `src/discord_interface/notifier.py`

**Purpose**: Main bot orchestrator managing Discord integration, cog coordination, and message handling.

**Key Responsibilities**:
- **Bot Instance Management**: Creates and configures Discord bot with proper intents
- **Cog Loading**: Orchestrates loading of all specialized cogs in correct order
- **Event Handling**: Manages Discord events (ready, command errors, reactions)
- **Message Operations**: Handles sending messages, embeds, and file uploads
- **Lifecycle Coordination**: Ensures proper initialization and shutdown sequences

**Core Methods**:
- **`__init__()`**: Initializes bot with intents and event handlers
- **`setup_bot()`**: Loads all cogs with dependency injection
- **`on_ready()`**: Handles post-login initialization and validation
- **`send_message()`**: Unified message sending with tracking integration
- **`upload_analysis_content()`**: Handles file uploads with retry logic

**Configuration**:
- **Intents**: `message_content`, `reactions` enabled for full functionality
- **Command Prefix**: `!` for all bot commands
- **Channel Whitelist**: Configurable allowed channels for testing
- **Logo URL**: Bot branding for embeds

**Integration Points**:
- **SymbolManager**: Injected into CommandHandler for symbol validation
- **MarketAnalyzer**: Injected for analysis execution
- **FileHandler**: Integrated for automatic message tracking
- **Logger**: Comprehensive logging throughout bot operations

**Error Handling**: Global command error handler with user-friendly responses

## Bot Lifecycle

### Initialization Flow

1. **`DiscordNotifier.__init__()`**: 
   - Creates Discord bot instance with proper intents (messages, reactions)
   - Registers event handlers (`on_ready`, `on_command_error`)
   - Initializes file handler and sets up bot reference

2. **`setup_bot()` (setup_hook)**: 
   - Loads AntiSpam cog with channel whitelist
   - Loads ReactionHandler cog for interactive features
   - Loads CommandHandler cog with injected dependencies (symbol_manager, market_analyzer)
   - All cogs are registered with the bot instance

3. **`on_ready()` Event**:
   - Logs successful login with bot username
   - Initializes file handler and starts background cleanup tasks
   - Initializes AntiSpam role for user management
   - Validates CommandHandler dependencies
   - Sets internal ready state for other components

4. **Commands Ready**: Bot is now fully operational and can process user commands

### Shutdown Flow (Reverse Order)

1. **Signal Handling**: Graceful shutdown initiated
2. **Analysis Cleanup**: Cancel any pending analysis operations
3. **Message Persistence**: Save final state of tracked messages
4. **AntiSpam Cleanup**: Remove temporary roles and restrictions
5. **File Handler Shutdown**: Stop cleanup scheduler and persist data
6. **Discord Connection**: Close bot connection cleanly

### Key Integration Points

- **Dependency Injection**: SymbolManager and MarketAnalyzer injected into CommandHandler
- **Event Coordination**: `asyncio.Event` used for proper initialization sequencing
- **Error Recovery**: Comprehensive error handling during initialization
- **Background Tasks**: Cleanup scheduler runs independently of main bot loop

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

1. **Extend CommandHandler**: Add new command method in `src/discord_interface/cogs/command_handler.py`
2. **Command Decorator**: Use `@commands.command()` decorator with appropriate parameters
3. **Input Validation**: Use `CommandValidator` to validate symbol, timeframe, and user permissions
4. **Business Logic**: Call appropriate analyzer/manager (AnalysisEngine, SymbolManager, etc.)
5. **Response Formatting**: Use `ResponseBuilder` to create embeds and handle file uploads
6. **Message Tracking**: All responses are automatically tracked via `DiscordNotifier.send_message()`

**Example Command Structure**:
```python
@commands.command(name="analyze")
async def analyze_command(self, ctx, symbol: str, timeframe: str = "4h"):
    # Validation
    validation = self.command_validator.validate_command(ctx, symbol, timeframe)
    if not validation.is_valid:
        await ctx.send(embed=self.error_handler.create_error_embed(validation.error_message))
        return
    
    # Analysis execution
    result = await self.analysis_handler.execute_analysis(symbol, timeframe, ctx)
    
    # Response building
    embed = self.response_builder.build_analysis_embed(result)
    url = await self.response_builder.upload_analysis_content(result.html_content, symbol, ctx.channel.id)
    
    # Send response (automatically tracked)
    await ctx.send(embed=embed)
```

### Error Handling in Commands

Use `ErrorHandler` methods for consistent error reporting:
- **`handle_command_execution_error()`**: For analysis failures and timeouts
- **`handle_message_deletion_error()`**: For cleanup operation failures  
- **`create_error_embed()`**: For user-friendly error message formatting
- **Global Handler**: `on_command_error()` listener for unhandled exceptions

### FileHandler Component Usage

**Tracking Messages**:
```python
# Automatic tracking via DiscordNotifier
await discord_notifier.send_message("Analysis complete!", channel_id, embed=embed)

# Manual tracking if needed
await file_handler.track_message(message_id, channel_id, user_id, "analysis", 3600)
```

**Cleanup Operations**:
```python
# Check and delete expired messages
await file_handler.check_and_delete_expired_messages()
```

### Cog Development Pattern

**Adding a New Cog**:
```python
# In DiscordNotifier.setup_bot()
self.logger.debug("Adding MyNewCog...")
await self.bot.add_cog(MyNewCog(self.bot, self.logger, required_deps))
self.logger.debug("MyNewCog added.")
```

**Cog Structure**:
```python
class MyNewCog(commands.Cog):
    def __init__(self, bot, logger, dependencies):
        self.bot = bot
        self.logger = logger
        # Initialize with injected dependencies
    
    # Commands and event listeners go here
```

## Configuration

- `config/config.ini`: Bot settings, timeframes, analysis parameters
- `keys.env`: Discord bot token, API keys
- Rate limits: Configurable via AntiSpam cog settings
- Message expiry: `FILE_MESSAGE_EXPIRY` in config

## Integration with Other Modules

### Core Analysis Components
- **AnalysisEngine** (`src/analyzer/core/analysis_engine.py`): Provides comprehensive market analysis with technical indicators and pattern detection
- **SymbolManager** (`src/platforms/exchange_manager.py`): Validates trading pairs and provides exchange integration
- **RAGEngine** (`src/rag/`): Provides context-aware AI responses and prompt enhancement

### Data Management
- **Config System** (`src/utils/loader.py`): Centralized configuration management for bot settings
- **Logger** (`src/logger/`): Structured logging throughout the Discord interface
- **FormatUtils** (`src/utils/format_utils.py`): Number and timestamp formatting utilities

### HTML Generation (for Reports)
- **HTMLGenerator** (`src/html/html_generator.py`): Creates interactive HTML reports with charts
- **ChartGenerator** (`src/html/chart_generator.py`): Generates Plotly charts for analysis visualization

### External Services
- **Discord API**: Message sending, file uploads, reaction handling via discord.py
- **Exchange APIs**: Real-time market data via integrated platform connectors
- **AI Providers**: Analysis generation via LM Studio, Google AI, or OpenRouter

### Data Flow Architecture

```
User Command → DiscordNotifier → CommandHandler → CommandValidator
                                                        ↓
AnalysisHandler → AnalysisEngine → Technical Analysis
                                                        ↓
ResponseBuilder → DiscordNotifier → Message Tracking
                                                        ↓
FileHandler → Automatic Cleanup
```

### Dependency Injection Pattern

All major components are injected during initialization:
- `SymbolManager` and `MarketAnalyzer` injected into `CommandHandler`
- `Logger` injected into all components for consistent logging
- `Config` accessed globally for settings management
- Event-driven communication between cogs via Discord's event system

## Troubleshooting

### Bot Startup Issues
- **Commands not loading**: Check `setup_bot()` logs in startup output, ensure cog syntax is correct
- **Discord login failure**: Verify `DISCORD_BOT_TOKEN` in `keys.env` is valid
- **Intents not working**: Ensure Discord application has proper intents enabled in Developer Portal
- **Dependency injection failure**: Check that `SymbolManager` and `MarketAnalyzer` are properly initialized before bot startup

### Command Processing Issues
- **Rate limiting too strict**: Adjust thresholds in `AntiSpam` configuration or check `config/config.ini`
- **Symbol validation errors**: Verify symbol format (BTC/USDT) and check `SymbolManager` connectivity
- **Analysis timeouts**: Increase timeout values or check `AnalysisEngine` performance
- **Invalid timeframes**: Ensure timeframe matches supported values (1h, 2h, 4h, 6h, 8h, 12h, 1d)

### Message Management Issues
- **Message tracking not working**: Check `data/tracked_messages.json` file permissions and format
- **Cleanup not running**: Verify `CleanupScheduler` is started in `FileHandler.initialize()`
- **File upload failures**: Check Discord channel permissions and file size limits (8MB)
- **Message deletion errors**: Verify bot has proper permissions in target channels

### Reaction Handling Issues
- **Missing reactions**: Ensure `ReactionHandler` is loaded and Discord intents include `reactions`
- **Reaction events not firing**: Check that reaction intents are enabled in bot initialization
- **Reaction processing errors**: Verify bot can access reaction users and message content

### Performance Issues
- **High memory usage**: Check for message tracking leaks in `tracked_messages.json`
- **Slow command response**: Profile `AnalysisEngine` execution time and optimize queries
- **Background task conflicts**: Ensure cleanup scheduler doesn't conflict with analysis operations

### Configuration Issues
- **Settings not applying**: Check `config/config.ini` file syntax and reload bot after changes
- **Environment variables**: Verify `keys.env` is in project root and properly formatted
- **Path issues**: Ensure all file paths in config are absolute or relative to project root

### Logging and Debugging
- **Enable debug logging**: Set `logger_debug = true` in `config/config.ini` under `[general]`
- **Check log files**: Review `logs/` directory for detailed error information
- **Bot status**: Use Discord's built-in status commands or check bot presence in server
