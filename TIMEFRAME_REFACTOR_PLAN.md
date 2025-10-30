# Timeframe Configuration Refactor Plan

## Problem Analysis

The `timeframe = 1h` configuration in `config.ini` **cannot be changed effectively** due to multiple hardcoded dependencies throughout the codebase. Changing it to values like `4h`, `15m`, or `1d` will cause incorrect analysis, broken prompts, and calculation errors.

## Root Causes

### 1. **Hardcoded Hourly Assumptions in Candle Progress Calculation**
**Location:** `src/analyzer/prompts/context_builder.py` (lines 44-48)

```python
if self.timeframe == "1h" or self.timeframe == "1H":
    minutes_into_hour = current_time.minute
    candle_progress = (minutes_into_hour / 60) * 100
```

**Issue:** Only calculates candle progress for 1h timeframe. Other timeframes (15m, 4h, 1d) won't show accurate completion percentage.

**Impact:** Misleading prompt context about current candle formation state.

---

### 2. **Hardcoded Multi-Timeframe Period Calculations**
**Location:** `src/analyzer/prompts/context_builder.py` (lines 115-121)

```python
periods = {
    "4h": 4,      # Assumes 1h candles
    "12h": 12,    # Assumes 1h candles
    "24h": 24,    # Assumes 1h candles
    "3d": 72,     # Assumes 1h candles
    "7d": 168     # Assumes 1h candles
}
```

**Issue:** All period conversions assume 1h base candles. If config uses `4h` timeframe, these calculations become wrong:
- "4h" period would use only 4 candles (16 hours instead of 4 hours)
- "24h" period would use 24 candles (96 hours instead of 24 hours)

**Impact:** Multi-timeframe price summaries show incorrect historical ranges and price changes.

---

### 3. **Hardcoded Text References**
**Location:** `src/analyzer/prompts/context_builder.py` (line 123)

```python
data += "\nMulti-Timeframe Price Summary (Based on 1h candles):\n"
```

**Issue:** Hardcoded text states "Based on 1h candles" regardless of actual timeframe.

**Impact:** Misleading AI prompts causing incorrect analysis interpretation.

---

### 4. **Prompt Template Hardcoded Timeframe**
**Location:** `src/analyzer/prompts/template_manager.py` (line 39)

```python
header_base = f"""You are providing educational crypto market analysis of {symbol} on 1h timeframe..."""
```

**Issue:** Template explicitly states "1h timeframe" in AI instructions, overriding actual config.

**Impact:** AI believes it's analyzing 1h data even when different timeframe is configured.

---

### 5. **Hardcoded Timeframe in Analysis Instructions**
**Location:** `src/analyzer/prompts/context_builder.py` (line 57)

```python
- Analysis Includes: 1H, 1D, 7D, 30D, and 365D timeframes"""
```

**Issue:** Claims to include "1H" timeframe regardless of base configuration.

**Impact:** Misleading documentation in prompts.

---

### 6. **Daily Historical Data Assumptions**
**Location:** `src/analyzer/data/data_fetcher.py` (line 76)

```python
timeframe="1d",
```

**Issue:** Long-term indicator calculations use hardcoded "1d" for daily data fetch. This is correct, but the relationship to the primary timeframe is not clear or documented.

**Impact:** If primary timeframe changes, the relationship between short-term and long-term calculations becomes unclear.

---

### 7. **Default Limit Assumption**
**Location:** `src/analyzer/data/market_data_collector.py` (line 28)

```python
self.limit = 720  # Default to 30 days of hourly data
```

**Issue:** Comment says "30 days of hourly data" but if timeframe changes to 4h, 720 candles = 120 days, not 30.

**Impact:** Confusing and potentially excessive data fetching for longer timeframes.

---

### 8. **AI Chart Generation with Hardcoded Defaults**
**Location:** `src/html/chart_generator.py` (lines 163, 398, 472)

```python
def create_ohlcv_chart(..., timeframe: str = "1h", ...):
def create_chart_image(..., timeframe: str = "1h", ...):
```

**Issue:** Chart generation functions default to "1h" in their signatures. While they accept timeframe as a parameter, the default suggests 1h is the expected value.

**Impact:** Charts may display "1h" timeframe label even when different timeframe is configured if timeframe parameter is not explicitly passed.

---

### 9. **Chart Generator Timeframe Display**
**Location:** `src/html/generators/chart_section_generator.py` (line 55)

```python
'timeframe': ohlcv_data.get('timeframe', '1h')
```

**Issue:** Falls back to '1h' if timeframe not present in ohlcv_data dictionary.

**Impact:** Chart titles and labels may incorrectly show "1h" timeframe.

---

### 10. **No Timeframe Validation in Config Loader**
**Location:** `src/utils/loader.py` (line 219)

```python
return self.get_config('general', 'timeframe', '1h')
```

**Issue:** Config loader returns '1h' as default fallback but doesn't validate if the configured timeframe is supported. No warning or error if user sets unsupported value like "2h" or "6h".

**Impact:** Silent failures - system runs with unsupported timeframe without warnings.

---

### 11. **CryptoCompare API URL Template**
**Location:** `src/platforms/utils/cryptocompare_market_api.py` (line 15)

```python
OHLCV_API_URL_TEMPLATE = f"https://min-api.cryptocompare.com/data/v2/histo{{timeframe}}?..."
```

**Issue:** This template uses `{timeframe}` placeholder, which must be converted to CryptoCompare's format:
- "1h" → "hour"
- "1d" → "day"
- "1m" → "minute"

There's **no conversion function** to map our timeframe format to CryptoCompare's API format. This is a **critical missing piece**.

**Impact:** If timeframe changes, API calls to CryptoCompare will fail or return wrong data because "4h" is not a valid CryptoCompare endpoint (should use "hour" with appropriate limit calculation).

---

### 12. **CCXT Exchange Timeframe Support**
**Location:** `src/analyzer/data/data_fetcher.py` (line 30)

```python
ohlcv = await self.exchange.fetch_ohlcv(pair, timeframe, since=start_time, limit=limit + 1)
```

**Issue:** CCXT exchanges support different timeframe formats and not all exchanges support all timeframes:
- Common: "1m", "5m", "15m", "1h", "4h", "1d"
- Not all exchanges support "3h", "6h", "12h", etc.

**Impact:** Changing timeframe may fail silently on some exchanges that don't support that specific interval.

---

### 13. **Discord Command Parsing - No Timeframe Parameter Support**
**Location:** `src/discord_interface/cogs/handlers/command_validator.py` (lines 61-76)

**Current Command Format:**
```python
# validate_command_args() expects:
# args[0] = symbol (required)
# args[1] = language (optional)
# Example: !analyze BTC/USDT Polish
```

**Issue:** Command parser doesn't support timeframe parameter. Current structure:
- `!analyze BTC/USDT` → English, uses config timeframe (1h)
- `!analyze BTC/USDT Polish` → Polish, uses config timeframe (1h)
- `!analyze BTC/USDT 4h` → Would be interpreted as language "4h" and fail validation
- `!analyze BTC/USDT 4h Polish` → **Not supported**, only 2 args handled

**Impact:** Users cannot override timeframe per-analysis. To analyze on different timeframes, admin must:
1. Stop the bot
2. Edit `config.ini`
3. Restart the bot

This is **not user-friendly** for multi-timeframe analysis.

---

### 14. **Analysis Engine Doesn't Accept Timeframe Parameter**
**Location:** `src/analyzer/core/analysis_engine.py` (line 102)

```python
def initialize_for_symbol(self, symbol: str, exchange, language=None) -> None:
    # Uses self.timeframe from config, cannot override per-analysis
    self.context.timeframe = self.timeframe
```

**Issue:** `initialize_for_symbol()` doesn't accept timeframe parameter. Always uses `self.timeframe` loaded from config at startup.

**Impact:** Even if command parsing is fixed, the analysis engine can't use per-request timeframe.

---

### 15. **Discord Bot Help Messages Hardcoded**
**Location:** `src/discord_interface/notifier.py` (line 131) and `command_validator.py` (line 63)

```python
value="Type `!analyze base/quote language`\nExample: `!analyze BTC/USDC English`"
# ...
"Usage: `!analyze <SYMBOL> [Language]`. Example: `!analyze BTC/USDT Polish`"
```

**Issue:** Help messages don't mention timeframe parameter option.

**Impact:** Users won't know they can specify timeframe (once implemented).

---

## Affected Components

### Core Analysis Flow
1. **AnalysisEngine** (`src/analyzer/core/analysis_engine.py`)
   - Sets `self.timeframe` from config but passes it without validation
   - Assumes timeframe compatibility throughout pipeline

2. **MarketDataCollector** (`src/analyzer/data/market_data_collector.py`)
   - Uses timeframe for data fetching
   - Default limit assumes hourly candles

3. **ContextBuilder** (`src/analyzer/prompts/context_builder.py`)
   - All hardcoded period conversions
   - Candle progress calculation
   - Prompt text generation

4. **PromptBuilder** (`src/analyzer/prompts/prompt_builder.py`)
   - Passes timeframe to formatters but doesn't validate

5. **TemplateManager** (`src/analyzer/prompts/template_manager.py`)
   - Hardcoded "1h" in AI instruction templates

### Supporting Utilities
6. **FormatUtils** (`src/utils/format_utils.py`)
   - `format_periods_ago_with_context()` correctly handles different timeframes
   - `_get_timeframe_minutes()` provides correct conversion logic

### Pattern Recognition
7. **Pattern Analyzers** (`src/analyzer/pattern_engine/`)
   - Pattern detection uses `periods_ago` without timeframe validation
   - May produce incorrect timing reports for non-1h timeframes

### Chart Generation
8. **ChartGenerator** (`src/html/chart_generator.py`)
   - Multiple functions default to `timeframe: str = "1h"`
   - Chart titles include timeframe label
   - AI chart generation uses `config.AI_CHART_CANDLE_LIMIT` which is timeframe-agnostic

9. **ChartSectionGenerator** (`src/html/generators/chart_section_generator.py`)
   - Falls back to '1h' if timeframe missing from ohlcv_data

### External APIs
10. **CryptoCompare API** (`src/platforms/utils/cryptocompare_market_api.py`)
    - **CRITICAL**: No timeframe format conversion for CryptoCompare API
    - Template uses `{timeframe}` but CryptoCompare expects "hour", "day", "minute"
    - Missing: converter function for our format → CryptoCompare format

11. **CCXT Exchanges** (`src/analyzer/data/data_fetcher.py`)
    - Passes timeframe directly to `exchange.fetch_ohlcv()`
    - Not all exchanges support all timeframes
    - No validation of exchange-specific timeframe support

### Discord Command Interface (NEW)
12. **CommandValidator** (`src/discord_interface/cogs/handlers/command_validator.py`)
    - Currently parses: `args[0]` (symbol), `args[1]` (language)
    - No timeframe parameter support
    - Would need to parse 3 arguments: symbol, timeframe (optional), language (optional)

13. **AnalysisHandler** (`src/discord_interface/cogs/handlers/analysis_handler.py`)
    - `execute_analysis()` doesn't accept timeframe parameter
    - Needs to pass timeframe to `initialize_for_symbol()`

14. **AnalysisEngine.initialize_for_symbol()** (`src/analyzer/core/analysis_engine.py`)
    - Doesn't accept timeframe parameter
    - Always uses `self.timeframe` from config
    - Needs refactor to accept optional timeframe override

15. **Help Messages** (`src/discord_interface/notifier.py`, `command_validator.py`)
    - Hardcoded usage examples don't mention timeframe
    - Need updating to show: `!analyze BTC/USDT 4h Polish`

---

## Refactor Strategy

### Phase 1: Validation & Safety (Priority: HIGH)
**Goal:** Prevent silent failures and document current limitations

#### 1.1 Add Timeframe Validator
**File:** `src/utils/timeframe_validator.py` (NEW)

```python
class TimeframeValidator:
    """Validates and manages timeframe configurations"""
    
    SUPPORTED_TIMEFRAMES = ['1h']  # Expand later
    TIMEFRAME_MINUTES = {
        '1m': 1, '5m': 5, '15m': 15, '30m': 30,
        '1h': 60, '4h': 240, '1d': 1440
    }
    
    # CryptoCompare API format mapping
    CRYPTOCOMPARE_FORMAT = {
        '1m': 'minute', '5m': 'minute', '15m': 'minute', '30m': 'minute',
        '1h': 'hour', '2h': 'hour', '4h': 'hour',
        '1d': 'day', '7d': 'day', '30d': 'day'
    }
    
    # CCXT-compatible timeframes (common across major exchanges)
    CCXT_STANDARD_TIMEFRAMES = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w']
    
    @classmethod
    def validate(cls, timeframe: str) -> bool:
        """Check if timeframe is fully supported"""
        return timeframe in cls.SUPPORTED_TIMEFRAMES
    
    @classmethod
    def to_minutes(cls, timeframe: str) -> int:
        """Convert timeframe to minutes"""
        return cls.TIMEFRAME_MINUTES.get(timeframe, 60)
    
    @classmethod
    def calculate_period_candles(cls, base_timeframe: str, target_period: str) -> int:
        """Calculate how many candles needed for target period"""
        # e.g., base="4h", target="24h" -> 6 candles
        base_mins = cls.to_minutes(base_timeframe)
        target_mins = cls.to_minutes(target_period)
        return target_mins // base_mins
    
    @classmethod
    def to_cryptocompare_format(cls, timeframe: str) -> tuple[str, int]:
        """
        Convert our timeframe to CryptoCompare API format.
        
        Returns:
            tuple: (endpoint_type, multiplier)
            Example: "4h" -> ("hour", 4)
        """
        if timeframe not in cls.CRYPTOCOMPARE_FORMAT:
            raise ValueError(f"Timeframe {timeframe} not supported by CryptoCompare API")
        
        endpoint = cls.CRYPTOCOMPARE_FORMAT[timeframe]
        
        # Extract multiplier from timeframe
        if 'm' in timeframe:
            multiplier = int(timeframe.replace('m', ''))
        elif 'h' in timeframe:
            multiplier = int(timeframe.replace('h', ''))
        elif 'd' in timeframe:
            multiplier = int(timeframe.replace('d', ''))
        else:
            multiplier = 1
        
        return endpoint, multiplier
    
    @classmethod
    def is_ccxt_compatible(cls, timeframe: str, exchange_name: str = None) -> bool:
        """
        Check if timeframe is compatible with CCXT exchanges.
        
        Args:
            timeframe: Timeframe string like "1h", "4h"
            exchange_name: Optional specific exchange name for exact validation
        
        Returns:
            bool: True if timeframe is likely supported
        """
        # Basic check for standard timeframes
        if timeframe in cls.CCXT_STANDARD_TIMEFRAMES:
            return True
        
        # Could be extended to check specific exchange support
        # via exchange.timeframes property if exchange instance is available
        return False
```

#### 1.2 Add Startup Validation
**File:** `src/analyzer/core/analysis_engine.py` (modify `__init__`)

```python
from src.utils.timeframe_validator import TimeframeValidator

def __init__(self, ...):
    # ...existing code...
    self.timeframe = config.TIMEFRAME
    
    # NEW: Validate timeframe
    if not TimeframeValidator.validate(self.timeframe):
        self.logger.warning(
            f"Timeframe '{self.timeframe}' is not fully supported. "
            f"Supported: {TimeframeValidator.SUPPORTED_TIMEFRAMES}. "
            f"Proceeding but expect incorrect calculations."
        )
```

#### 1.3 Update README
**File:** `README.md`

Add clear warning in configuration section:

```markdown
### ⚠️ Timeframe Configuration Limitation

**Current Status:** The `timeframe` setting in `config/config.ini` is **hardcoded to `1h`** throughout the codebase. 

**Do NOT change this value** until the timeframe refactor is complete. Changing it will cause:
- Incorrect multi-timeframe calculations
- Wrong candle progress reporting
- Misleading AI analysis prompts
- Broken period-to-time conversions

**Supported:** `1h` only  
**Planned:** `15m`, `4h`, `1d` (see `TIMEFRAME_REFACTOR_PLAN.md`)
```

---

### Phase 2: Dynamic Period Calculations (Priority: HIGH)
**Goal:** Make multi-timeframe calculations timeframe-agnostic

#### 2.1 Refactor ContextBuilder Period Logic
**File:** `src/analyzer/prompts/context_builder.py`

**Current Code (lines 115-121):**
```python
periods = {
    "4h": 4,
    "12h": 12,
    "24h": 24,
    "3d": 72,
    "7d": 168
}
```

**Refactored Code:**
```python
from src.utils.timeframe_validator import TimeframeValidator

def _calculate_period_candles(self) -> Dict[str, int]:
    """Calculate candle counts for standard periods based on current timeframe"""
    base_minutes = TimeframeValidator.to_minutes(self.timeframe)
    
    period_targets = {
        "4h": 4 * 60,      # 240 minutes
        "12h": 12 * 60,    # 720 minutes
        "24h": 24 * 60,    # 1440 minutes
        "3d": 72 * 60,     # 4320 minutes
        "7d": 168 * 60     # 10080 minutes
    }
    
    return {
        name: target_mins // base_minutes 
        for name, target_mins in period_targets.items()
    }

def build_market_data_section(self, ohlcv_candles: np.ndarray) -> str:
    # ...existing validation...
    
    periods = self._calculate_period_candles()
    
    # Update text to be dynamic
    data += f"\nMulti-Timeframe Price Summary (Based on {self.timeframe} candles):\n"
    # ...rest of logic...
```

#### 2.2 Refactor Candle Progress Calculation
**File:** `src/analyzer/prompts/context_builder.py` (lines 42-48)

**Current Code:**
```python
candle_status = ""
if self.timeframe == "1h" or self.timeframe == "1H":
    minutes_into_hour = current_time.minute
    candle_progress = (minutes_into_hour / 60) * 100
    candle_status = f"\n- Current Candle: {minutes_into_hour} minutes into formation..."
```

**Refactored Code:**
```python
from src.utils.timeframe_validator import TimeframeValidator

candle_status = ""
timeframe_minutes = TimeframeValidator.to_minutes(self.timeframe)

if timeframe_minutes < 1440:  # Less than 1 day
    # Calculate current position within the candle
    current_time = datetime.now()
    
    if timeframe_minutes < 60:  # Sub-hourly (1m, 5m, 15m, 30m)
        total_minutes = current_time.hour * 60 + current_time.minute
        minutes_into_candle = total_minutes % timeframe_minutes
    elif timeframe_minutes == 60:  # 1h
        minutes_into_candle = current_time.minute
    else:  # Multi-hour (4h, 6h, etc.)
        total_minutes = current_time.hour * 60 + current_time.minute
        minutes_into_candle = total_minutes % timeframe_minutes
    
    candle_progress = (minutes_into_candle / timeframe_minutes) * 100
    candle_status = (
        f"\n- Current Candle: {minutes_into_candle}/{timeframe_minutes} minutes "
        f"({candle_progress:.1f}% complete)"
    )
    candle_status += f"\n- Analysis Note: Technical indicators calculated using only completed candles"
```

---

### Phase 3: Dynamic Prompt Templates (Priority: MEDIUM)
**Goal:** Make AI instruction templates timeframe-aware

#### 3.1 Update TemplateManager
**File:** `src/analyzer/prompts/template_manager.py` (line 39)

**Current Code:**
```python
header_base = f"""You are providing educational crypto market analysis of {symbol} on 1h timeframe..."""
```

**Refactored Code:**
```python
def build_system_prompt(self, symbol: str, timeframe: str, language: str = "English") -> str:
    """Build system prompt with dynamic timeframe"""
    
    header_base = f"""You are providing educational crypto market analysis of {symbol} on {timeframe} timeframe along with multi-timeframe technical metrics and recent market data."""
    # ...rest of logic...
```

**Update Caller:**
```python
# In PromptBuilder or wherever template is used
system_prompt = self.template_manager.build_system_prompt(
    symbol=context.symbol,
    timeframe=self.timeframe,
    language=language
)
```

#### 3.2 Fix Analysis Timeframe Text
**File:** `src/analyzer/prompts/context_builder.py` (line 57)

**Current Code:**
```python
- Analysis Includes: 1H, 1D, 7D, 30D, and 365D timeframes"""
```

**Refactored Code:**
```python
def _get_analysis_timeframes_text(self) -> str:
    """Get analysis timeframes description based on primary timeframe"""
    # Always include these standard analysis windows
    return f"- Analysis Includes: {self.timeframe.upper()}, 1D, 7D, 30D, and 365D timeframes"

# In build_trading_context():
trading_context = f"""
TRADING CONTEXT:
- Symbol: {context.symbol if hasattr(context, 'symbol') else 'BTC/USDT'}
- Current Day: {self.format_utils.format_current_time("%A")}
- Current Price: {context.current_price}
- Analysis Time: {self.format_utils.format_current_time('%Y-%m-%d %H:%M:%S')}{candle_status}
- Primary Timeframe: {self.timeframe}
{self._get_analysis_timeframes_text()}"""
```

---

### Phase 4: Data Fetching Adjustments (Priority: MEDIUM)
**Goal:** Ensure appropriate data quantities for all timeframes

#### 4.1 Add CryptoCompare Timeframe Converter
**File:** `src/platforms/utils/cryptocompare_market_api.py`

**Add new method:**
```python
from src.utils.timeframe_validator import TimeframeValidator

def build_ohlcv_url(self, base: str, quote: str, timeframe: str, limit: int) -> str:
    """
    Build CryptoCompare OHLCV API URL with proper endpoint format.
    
    Args:
        base: Base currency (e.g., "BTC")
        quote: Quote currency (e.g., "USDT")
        timeframe: Our timeframe format (e.g., "1h", "4h")
        limit: Number of candles to fetch
    
    Returns:
        Complete API URL
    """
    endpoint_type, multiplier = TimeframeValidator.to_cryptocompare_format(timeframe)
    
    # CryptoCompare uses "aggregate" parameter for multipliers
    aggregate_param = f"&aggregate={multiplier}" if multiplier > 1 else ""
    
    url = (
        f"https://min-api.cryptocompare.com/data/v2/histo{endpoint_type}"
        f"?fsym={base}&tsym={quote}&limit={limit}"
        f"{aggregate_param}&api_key={config.CRYPTOCOMPARE_API_KEY}"
    )
    
    return url
```

**Update usage in data_fetcher or wherever CryptoCompare OHLCV is called:**
```python
# Instead of string template replacement
url = self.cryptocompare_api.build_ohlcv_url(base, quote, timeframe, limit)
```

#### 4.2 Dynamic Candle Limit Calculation
**File:** `src/analyzer/data/market_data_collector.py`

**Current Code:**
```python
self.limit = 720  # Default to 30 days of hourly data
```

**Refactored Code:**
```python
from src.utils.timeframe_validator import TimeframeValidator

def initialize(self, ..., timeframe: str = "1h", limit: int = None):
    """Initialize with smart limit calculation"""
    self.timeframe = timeframe
    
    if limit is None:
        # Calculate limit to get ~30 days of data
        timeframe_minutes = TimeframeValidator.to_minutes(timeframe)
        target_days = 30
        target_minutes = target_days * 24 * 60
        self.limit = target_minutes // timeframe_minutes
        
        self.logger.debug(
            f"Calculated limit: {self.limit} candles "
            f"(~{target_days} days at {timeframe} timeframe)"
        )
    else:
        self.limit = limit
```

#### 4.2 Update Config Documentation
**File:** `config/config.ini`

```ini
[general]
# Primary timeframe for analysis (WARNING: Only "1h" is fully supported currently)
# Changing this will cause calculation errors until timeframe refactor is complete
# See TIMEFRAME_REFACTOR_PLAN.md for details
timeframe = 1h

# Maximum number of candles to fetch for primary timeframe analysis
# Default: 999 gives ~41 days at 1h, ~166 days at 4h
candle_limit = 999

# Candle limit for AI chart generation (keep this smaller for performance)
ai_chart_candle_limit = 200
```

---

### Phase 5: Discord Command Interface Updates (Priority: HIGH)
**Goal:** Allow users to specify timeframe per-analysis via Discord commands

#### 5.1 Update Command Parsing Logic
**File:** `src/discord_interface/cogs/handlers/command_validator.py`

**Current parsing logic (lines 61-76):**
```python
def validate_command_args(self, args: list) -> Tuple[bool, Optional[str], Optional[str]]:
    if not args:
        return False, "Missing arguments", "Usage: `!analyze <SYMBOL> [Language]`..."
    
    symbol = args[0].upper()
    # ...symbol validation...
    
    language = None
    if len(args) > 1:
        is_valid_lang, validated_lang = self.validate_language(args[1])
        # ...language validation...
    
    return True, None, None
```

**Refactored to support 3 flexible argument patterns:**
```python
from src.utils.timeframe_validator import TimeframeValidator

def validate_command_args(self, args: list) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
    """
    Validate command arguments with flexible timeframe and language support.
    
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
                return False, f"Invalid argument '{arg}'. Must be a timeframe (1h, 4h, 15m, 1d) or language.", None, (None, None, None)
    
    elif len(args) >= 3:
        # Two optional args: assume timeframe then language
        timeframe_arg = args[1]
        language_arg = args[2]
        
        # Validate timeframe
        if not self._is_valid_timeframe(timeframe_arg):
            return False, f"Invalid timeframe '{timeframe_arg}'. Supported: 1m, 5m, 15m, 30m, 1h, 4h, 1d", None, (None, None, None)
        timeframe = timeframe_arg.lower()
        
        # Validate language
        is_valid_lang, validated_lang = self.validate_language(language_arg)
        if not is_valid_lang:
            supported_langs = ", ".join(config.SUPPORTED_LANGUAGES.keys())
            return False, f"Unsupported language '{language_arg}'. Available: {supported_langs}", None, (None, None, None)
        language = validated_lang
    
    return True, None, None, (symbol, timeframe, language)

def _is_valid_timeframe(self, arg: str) -> bool:
    """Check if argument looks like a timeframe."""
    # Simple pattern check: ends with m, h, or d
    if not arg:
        return False
    
    arg_lower = arg.lower()
    if arg_lower in TimeframeValidator.TIMEFRAME_MINUTES:
        return True
    
    # Additional check for common patterns
    import re
    return bool(re.match(r'^\d+[mhd]$', arg_lower))

def _get_usage_message(self) -> str:
    """Get command usage message."""
    return (
        "Usage: `!analyze <SYMBOL> [TIMEFRAME] [LANGUAGE]`\n"
        "Examples:\n"
        "  `!analyze BTC/USDT` - Analyze with default settings\n"
        "  `!analyze BTC/USDT 4h` - Analyze on 4-hour timeframe\n"
        "  `!analyze BTC/USDT Polish` - Analyze in Polish\n"
        "  `!analyze BTC/USDT 15m English` - 15-minute timeframe in English"
    )
```

**Update ValidationResult dataclass:**
```python
@dataclass
class ValidationResult:
    """Result of command validation."""
    is_valid: bool
    symbol: Optional[str] = None
    timeframe: Optional[str] = None  # NEW
    language: Optional[str] = None
    error_message: Optional[str] = None
```

**Update validate_full_analysis_request():**
```python
def validate_full_analysis_request(self, ctx: commands.Context, args: list, 
                                  analysis_cooldown_coin: int, analysis_cooldown_user: int) -> ValidationResult:
    # Validate arguments (now returns 4-tuple)
    is_valid, error_msg, usage, (symbol, timeframe, language) = self.validate_command_args(args)
    if not is_valid:
        return ValidationResult(is_valid=False, error_message=f"{error_msg}\n{usage}" if usage else error_msg)
    
    # If timeframe provided, validate it's fully supported
    if timeframe:
        if not TimeframeValidator.validate(timeframe):
            return ValidationResult(
                is_valid=False,
                error_message=f"⚠️ Timeframe '{timeframe}' is experimental. Fully supported: {', '.join(TimeframeValidator.SUPPORTED_TIMEFRAMES)}"
            )
    
    # ...rest of validation (cooldowns, etc.)...
    
    return ValidationResult(is_valid=True, symbol=symbol, timeframe=timeframe, language=language)
```

#### 5.2 Update Analysis Flow to Use Timeframe
**File:** `src/discord_interface/cogs/command_handler.py`

**Update analyze_command:**
```python
@commands.command(name='analyze')
async def analyze_command(self, ctx: commands.Context, *, args: Optional[str] = None) -> None:
    # ...existing validation code...
    
    symbol = validation_result.symbol
    timeframe = validation_result.timeframe  # NEW
    language = validation_result.language
    
    # Pass timeframe to workflow
    analysis_task = self.bot.loop.create_task(
        self._perform_analysis_workflow(symbol, ctx, language, timeframe),  # NEW parameter
        name=f"Analysis-{symbol}"
    )
```

**Update _perform_analysis_workflow signature:**
```python
async def _perform_analysis_workflow(self, symbol: str, ctx: commands.Context, 
                                    language: Optional[str], timeframe: Optional[str] = None) -> None:
    """Perform the complete analysis workflow using the specialized components."""
    # ...existing validation...
    
    # Perform analysis with optional timeframe override
    success, result = await self.analysis_handler.execute_analysis(
        symbol, exchange, language, timeframe  # NEW parameter
    )
```

#### 5.3 Update Analysis Handler
**File:** `src/discord_interface/cogs/handlers/analysis_handler.py`

**Update execute_analysis signature:**
```python
async def execute_analysis(self, symbol: str, exchange: Any, language: Optional[str],
                          timeframe: Optional[str] = None) -> Tuple[bool, Any]:
    """Execute the market analysis with optional timeframe override."""
    async with self._analysis_lock:
        self.market_analyzer.initialize_for_symbol(symbol, exchange, language, timeframe)  # Pass timeframe
        result = await self.market_analyzer.analyze_market()
        self.market_analyzer.last_analysis_result = result
        success = await self.market_analyzer.publish_analysis()
        return success, result
```

#### 5.4 Update Analysis Engine
**File:** `src/analyzer/core/analysis_engine.py`

**Update initialize_for_symbol signature:**
```python
def initialize_for_symbol(self, symbol: str, exchange, language=None, timeframe=None) -> None:
    """Initialize the analyzer for a specific symbol and exchange with optional timeframe override."""
    self.symbol = symbol
    self.exchange = exchange
    self.base_symbol = symbol.split('/')[0] if '/' in symbol else symbol
    self.language = language
    
    # Use provided timeframe or fall back to config
    effective_timeframe = timeframe if timeframe else self.timeframe
    
    # Initialize analysis context with effective timeframe
    self.context = AnalysisContext(symbol)
    self.context.exchange = exchange.name if hasattr(exchange, 'name') else str(exchange)
    self.context.timeframe = effective_timeframe
    
    # Create data fetcher and initialize data collector with effective timeframe
    from ..data.data_fetcher import DataFetcher
    data_fetcher = DataFetcher(exchange=exchange, logger=self.logger)
    
    self.data_collector.initialize(
        data_fetcher=data_fetcher, 
        symbol=symbol, 
        exchange=exchange,
        timeframe=effective_timeframe,  # Use effective timeframe
        limit=self.limit
    )
    
    # Update prompt builder and context builder with effective timeframe
    if hasattr(self, 'prompt_builder'):
        self.prompt_builder.timeframe = effective_timeframe
    
    if hasattr(self.prompt_builder, 'context_builder'):
        self.prompt_builder.context_builder.timeframe = effective_timeframe
    
    # ...rest of initialization...
```

#### 5.5 Update Help Messages
**File:** `src/discord_interface/notifier.py`

**Update bot status/help embed:**
```python
# Around line 131
value="Type `!analyze <SYMBOL> [TIMEFRAME] [LANGUAGE]`\n"
      "Examples:\n"
      "`!analyze BTC/USDC` - Default timeframe, English\n"
      "`!analyze BTC/USDC 4h` - 4-hour timeframe\n"
      "`!analyze BTC/USDC Polish` - Polish language\n"
      "`!analyze BTC/USDC 15m English` - 15-min, English"
```

---

### Phase 6: Testing (Priority: HIGH)
**Goal:** Ensure refactored code works for all target timeframes

#### 5.1 Create Unit Tests
**File:** `tests/test_timeframe_calculations.py` (NEW)

```python
import pytest
from src.utils.timeframe_validator import TimeframeValidator
from src.analyzer.prompts.context_builder import ContextBuilder

class TestTimeframeCalculations:
    
    @pytest.mark.parametrize("timeframe,expected_minutes", [
        ("1m", 1),
        ("5m", 5),
        ("15m", 15),
        ("1h", 60),
        ("4h", 240),
        ("1d", 1440),
    ])
    def test_timeframe_to_minutes(self, timeframe, expected_minutes):
        assert TimeframeValidator.to_minutes(timeframe) == expected_minutes
    
    def test_period_candle_calculation_1h(self):
        """Test that 1h timeframe calculates periods correctly"""
        validator = TimeframeValidator()
        assert validator.calculate_period_candles("1h", "4h") == 4
        assert validator.calculate_period_candles("1h", "24h") == 24
        assert validator.calculate_period_candles("1h", "7d") == 168
    
    def test_period_candle_calculation_4h(self):
        """Test that 4h timeframe calculates periods correctly"""
        validator = TimeframeValidator()
        assert validator.calculate_period_candles("4h", "4h") == 1
        assert validator.calculate_period_candles("4h", "24h") == 6
        assert validator.calculate_period_candles("4h", "7d") == 42
    
    def test_context_builder_dynamic_periods(self):
        """Test ContextBuilder uses dynamic period calculations"""
        builder_1h = ContextBuilder(timeframe="1h")
        periods_1h = builder_1h._calculate_period_candles()
        assert periods_1h["24h"] == 24
        
        builder_4h = ContextBuilder(timeframe="4h")
        periods_4h = builder_4h._calculate_period_candles()
        assert periods_4h["24h"] == 6
```

#### 5.2 Integration Testing Strategy
Create test scripts for each timeframe:

**File:** `tests/integration/test_15m_analysis.py`
**File:** `tests/integration/test_4h_analysis.py`
**File:** `tests/integration/test_1d_analysis.py`

Each should:
1. Set timeframe in config
2. Run full analysis pipeline
3. Validate prompt text correctness
4. Validate period calculations
5. Verify AI receives correct context

---

### Phase 6: Documentation Updates (Priority: LOW)
**Goal:** Document new flexibility and usage patterns

#### 6.1 Update README
**File:** `README.md`

**Add New Section:**
```markdown
### Timeframe Configuration

The bot now supports multiple timeframes for analysis:

**Fully Supported Timeframes:**
- `1h` - Hourly analysis (default, most tested)
- `15m` - 15-minute analysis (good for day trading)
- `4h` - 4-hour analysis (good for swing trading)
- `1d` - Daily analysis (good for position trading)

**How It Works:**
- The `timeframe` setting in `config/config.ini` controls the primary candle period
- Multi-timeframe calculations automatically adjust based on your setting
- AI prompts dynamically reflect the chosen timeframe
- Candle limits auto-calculate to provide ~30 days of data

**Configuration Example:**
```ini
[general]
timeframe = 4h      # Analyze using 4-hour candles
candle_limit = 999  # Auto-adjusts to appropriate data range
```

**Choosing Your Timeframe:**
- **1m-15m**: Very short-term, high-frequency trading (requires more API calls)
- **1h-4h**: Short to medium-term, good balance of detail and performance
- **1d**: Long-term analysis, most stable and least API-intensive
```

#### 6.2 Update Instructions File
**File:** `.github/instructions/discordcryptoanalyzer.instructions.md`

Add section:
```markdown
### Timeframe Configuration Notes

The codebase uses a dynamic timeframe system. When working with timeframe-related code:

1. **Never hardcode "1h" or specific timeframe values** - always use `self.timeframe` or config
2. **Use TimeframeValidator utility** for all timeframe conversions and calculations
3. **Period calculations must be dynamic** - calculate candle counts based on `self.timeframe`
4. **Prompt text must reflect actual timeframe** - no hardcoded "1h" in AI instructions
5. **Test across multiple timeframes** - if adding timeframe-dependent logic, test with 15m, 1h, 4h, 1d

**Common Patterns:**
```python
# ❌ WRONG: Hardcoded
periods = {"24h": 24}

# ✅ CORRECT: Dynamic
from src.utils.timeframe_validator import TimeframeValidator
base_minutes = TimeframeValidator.to_minutes(self.timeframe)
candle_count = (24 * 60) // base_minutes
```
```

---

## Implementation Checklist

### Immediate Actions (Do First)
- [ ] Create `src/utils/timeframe_validator.py` with validation logic
- [ ] Add `to_cryptocompare_format()` method for API compatibility
- [ ] Add `is_ccxt_compatible()` method for exchange validation
- [ ] Add startup warning in `AnalysisEngine.__init__()` for unsupported timeframes
- [ ] Update `README.md` with timeframe limitation warning
- [ ] Document all hardcoded locations in code comments

### Core Refactoring (Do Second)
- [ ] Refactor `ContextBuilder._calculate_period_candles()` to be dynamic
- [ ] Refactor `ContextBuilder` candle progress calculation
- [ ] Update multi-timeframe summary text to use `self.timeframe`
- [ ] Refactor `TemplateManager.build_system_prompt()` to accept timeframe parameter
- [ ] Update all template calls to pass timeframe
- [ ] Fix chart generator timeframe defaults and fallbacks

### Discord Command Interface (Do Second Priority)
- [ ] Update `CommandValidator.validate_command_args()` to parse 3 arguments (symbol, timeframe, language)
- [ ] Add `_is_valid_timeframe()` helper method
- [ ] Update `ValidationResult` dataclass to include `timeframe` field
- [ ] Update `validate_full_analysis_request()` to validate timeframe
- [ ] Update `command_handler.analyze_command()` to extract and pass timeframe
- [ ] Update `AnalysisHandler.execute_analysis()` to accept timeframe parameter
- [ ] Update `AnalysisEngine.initialize_for_symbol()` to accept timeframe parameter
- [ ] Update bot help messages to show timeframe usage
- [ ] Update Discord notifier status messages with new command examples

### Data Layer Updates (Do Third)
- [ ] Add `build_ohlcv_url()` method to CryptoCompare API handler
- [ ] Add dynamic limit calculation in `MarketDataCollector.initialize()`
- [ ] Add CCXT timeframe validation in `DataFetcher.fetch_candlestick_data()`
- [ ] Update config comments explaining candle_limit behavior
- [ ] Validate data fetching works correctly across timeframes

### Testing (Do Fourth)
- [ ] Create `tests/test_timeframe_calculations.py` with unit tests
- [ ] Test CryptoCompare API URL generation for multiple timeframes
- [ ] Test CCXT timeframe validation logic
- [ ] **Test command parsing with all combinations:**
  - [ ] `!analyze BTC/USDT` → default timeframe, English
  - [ ] `!analyze BTC/USDT 4h` → 4h timeframe, English
  - [ ] `!analyze BTC/USDT Polish` → default timeframe, Polish
  - [ ] `!analyze BTC/USDT 15m Polish` → 15m timeframe, Polish
  - [ ] `!analyze BTC/USDT invalid` → error message
  - [ ] `!analyze BTC/USDT 2h Polish` → unsupported timeframe warning
- [ ] Create integration tests for each target timeframe
- [ ] Run full analysis pipeline with 15m, 1h, 4h, 1d configurations
- [ ] Validate AI receives correct prompts for each timeframe
- [ ] Test that config default timeframe still works when no timeframe specified

### Documentation (Do Last)
- [ ] Update `README.md` with new timeframe flexibility
- [ ] Update `.github/instructions/*.instructions.md` with patterns
- [ ] Add inline code comments explaining timeframe dependencies
- [ ] Create example configs for different trading styles

---

## Risk Assessment

### High Risk Changes
1. **CryptoCompare API URL format conversion** - Critical for data fetching
   - **Mitigation:** Extensive testing with multiple timeframes, fallback to 1h if conversion fails, add unit tests for URL generation
   
2. **Period calculation refactor** - Could break existing analysis if wrong
   - **Mitigation:** Extensive unit tests, gradual rollout, keep 1h as default
   
3. **Candle progress calculation** - Complex time math
   - **Mitigation:** Test across timezones, edge cases (midnight, hour boundaries)

4. **CCXT exchange compatibility** - Different exchanges support different timeframes
   - **Mitigation:** Pre-flight validation, clear error messages, document exchange-specific limitations

### Medium Risk Changes
5. **Prompt template changes** - Could affect AI output quality
   - **Mitigation:** A/B testing, monitor analysis quality metrics

6. **Data fetching limits** - Could cause over/under-fetching
   - **Mitigation:** Log actual data ranges, add monitoring

### Low Risk Changes
7. **Documentation updates** - No runtime impact
8. **Validation warnings** - Helpful, non-breaking

---

## Rollout Strategy

### Phase 1: Foundation (Week 1)
- Add validator and warnings
- Document limitations
- No behavior changes yet

### Phase 2: Core Logic (Week 2)
- Refactor period calculations
- Test thoroughly with 1h (should be no-op)
- Deploy with 1h still as default

### Phase 3: Enable New Timeframes (Week 3)
- Add 15m, 4h support to validator
- Test integration thoroughly
- Update docs with "experimental" tag

### Phase 4: Stabilization (Week 4)
- Add 1d support
- Remove experimental tags
- Full documentation update

---

## Success Metrics

- [ ] Changing `timeframe` in config works without code changes
- [ ] All prompts reflect actual configured timeframe
- [ ] Multi-timeframe calculations correct for all supported timeframes
- [ ] No hardcoded "1h" references in active code paths
- [ ] Unit test coverage > 90% for timeframe-related code
- [ ] Integration tests pass for 15m, 1h, 4h, 1d
- [ ] AI analysis quality maintained across timeframes

---

## Future Enhancements (Post-Refactor)

1. **Multiple Simultaneous Timeframes**
   - Allow analysis of same symbol on multiple timeframes
   - Cross-timeframe correlation analysis

2. **Auto-Timeframe Selection**
   - AI suggests optimal timeframe based on trading style
   - Dynamic switching based on volatility

3. **Timeframe-Specific Indicators**
   - Some indicators work better on certain timeframes
   - Auto-adjust indicator parameters per timeframe

4. **Timeframe Comparison Views**
   - Side-by-side analysis across timeframes
   - Highlight divergences between timeframes

---

## Questions & Clarifications Needed

1. **Should we support sub-minute timeframes (30s, 1s)?**
   - Likely requires different exchange APIs
   - Much higher API rate limits needed

2. **Should candle_limit be timeframe-aware in config?**
   - Option A: One global limit, auto-adjust
   - Option B: Per-timeframe limits in config

3. **How to handle indicator periods across timeframes?**
   - RSI(14) on 1h vs 4h has different meanings
   - Should indicator periods scale with timeframe?

4. **AI model token limits per timeframe?**
   - Longer timeframes = more data history
   - May need different prompt strategies

---

## Conclusion

The current hardcoded `1h` timeframe is deeply embedded in:
- Candle progress calculations
- Multi-timeframe period conversions  
- AI prompt templates
- Documentation strings
- Data fetching logic
- **CryptoCompare API URL generation** (critical - requires format conversion)
- **CCXT exchange compatibility** (not all timeframes work on all exchanges)
- Chart generation defaults and fallbacks
- **Discord command parsing** (doesn't support timeframe parameter yet)
- **Analysis workflow** (doesn't accept per-request timeframe override)

**This explains why changing the config value doesn't work** - the code assumes hourly candles throughout, AND there's no way for users to specify different timeframes via commands.

### Critical Missing Pieces Found
1. **No CryptoCompare timeframe format converter**: Our "4h" format needs conversion to CryptoCompare's "hour" endpoint with aggregate parameter
2. **No CCXT timeframe validation**: Different exchanges support different timeframes; system doesn't validate before attempting fetch
3. **No config validation**: System accepts any timeframe value without warning
4. **No Discord command timeframe parameter**: Users cannot specify timeframe per-analysis (e.g., `!analyze BTC/USDT 4h`)
5. **No per-request timeframe override**: Analysis engine always uses config timeframe, can't override for individual requests

### User Experience Impact
**Currently:** To analyze BTC on both 1h and 4h timeframes, a user must:
1. Request `!analyze BTC/USDT` (gets 1h from config)
2. Wait for admin to stop bot
3. Admin edits `config.ini` to change `timeframe = 4h`
4. Admin restarts bot
5. Request `!analyze BTC/USDT` again (gets 4h)

**After Refactor:** User can simply:
- `!analyze BTC/USDT` → Uses config default (1h)
- `!analyze BTC/USDT 4h` → Uses 4h timeframe
- `!analyze BTC/USDT 15m Polish` → 15-minute in Polish
- All in real-time without bot restart

The refactor requires systematic replacement of hardcoded values with dynamic calculations based on `self.timeframe`, validation to prevent silent failures, API compatibility layers for external services, Discord command interface updates to parse and pass timeframe parameter, and extensive testing across multiple timeframes and command variations.

**Estimated Effort:** 3-4 weeks for complete implementation and testing (increased from 2-4 weeks due to Discord command interface work).

**Recommended Approach:** Phased rollout starting with validation/warnings, then core logic refactoring, API compatibility layer, Discord command interface updates, followed by enabling new timeframes one at a time with thorough testing.

---

## Additional Findings Summary

**New Issues Discovered (Total: 15, up from 12):**

1. **CryptoCompare API Incompatibility** (Critical)
   - Template uses `{timeframe}` but CryptoCompare expects "hour"/"day"/"minute"
   - Need converter: "1h" → ("hour", 1), "4h" → ("hour", 4), "15m" → ("minute", 15)

2. **CCXT Exchange Variance** (High)
   - Not all exchanges support all timeframes
   - Need pre-flight validation using `exchange.timeframes` property

3. **Chart Generator Defaults** (Medium)
   - Multiple functions default to `timeframe="1h"` in signatures
   - Chart labels fallback to "1h" if not explicitly passed

4. **Config Loader No Validation** (Medium)
   - Returns '1h' as fallback but doesn't warn on unsupported values
   - Silent acceptance of any timeframe string

5. **Discord Command Parsing** (Critical for UX)
   - Current format: `!analyze <SYMBOL> [LANGUAGE]`
   - No support for timeframe parameter
   - Need flexible parsing: `!analyze <SYMBOL> [TIMEFRAME] [LANGUAGE]`
   - Must handle: `!analyze BTC/USDT 4h Polish`, `!analyze BTC/USDT Polish`, `!analyze BTC/USDT 4h`

6. **Analysis Engine No Timeframe Override** (High)
   - `initialize_for_symbol()` doesn't accept timeframe parameter
   - Always uses config timeframe, can't override per-request
   - Limits user flexibility significantly

These additional findings increase the complexity of the refactor but are essential for proper multi-timeframe support with good user experience. The Discord command interface is particularly important as it's the primary user interaction point.

