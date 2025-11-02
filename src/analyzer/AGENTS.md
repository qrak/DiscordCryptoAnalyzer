# Analyzer Agents Documentation

This document describes the market analysis engine agents in the DiscordCryptoAnalyzer system.

## Overview

The analyzer layer orchestrates comprehensive cryptocurrency market analysis by coordinating data collection, technical indicator calculation, pattern detection, AI prompt generation, and result publication. It transforms raw market data into actionable insights through a sophisticated multi-stage pipeline.

## Directory Structure

### Core Files (`core/`)
- **`analysis_engine.py`**: Main orchestrator (`AnalysisEngine`) - coordinates all analysis components
- **`analysis_context.py`**: Context object holding all analysis state and data
- **`analysis_result_processor.py`**: Processes raw AI responses into structured results

### Data Layer (`data/`)
- **`market_data_collector.py`**: Fetches multi-timeframe OHLCV data, sentiment, and news context
- **`data_fetcher.py`**: Low-level exchange data fetching with retry logic
- **`data_processor.py`**: Transforms raw data into analysis-ready formats

### Calculations (`calculations/`)
- **`technical_calculator.py`**: Computes all technical indicators (50+ indicators)
- **`pattern_analyzer.py`**: Detects chart and indicator patterns
- **`market_metrics_calculator.py`**: Calculates multi-timeframe market metrics

### Pattern Engine (`pattern_engine/`)
See **`pattern_engine/AGENTS.md`** for comprehensive pattern detection documentation:
- **`pattern_engine.py`**: Chart pattern detection (head & shoulders, triangles, wedges)
- **`indicator_patterns/indicator_pattern_engine.py`**: Indicator pattern detection (RSI W-bottoms, MACD crossovers)

### Prompts (`prompts/`)
- **`prompt_builder.py`**: Assembles complete AI prompts from all analysis components
- **`template_manager.py`**: Manages prompt templates and analysis instructions
- **`context_builder.py`**: Builds contextual information sections

### Publishing (`publishing/`)
- **`analysis_publisher.py`**: Publishes analysis to Discord with HTML reports

### Formatting (`formatting/`)
- **`indicator_formatter.py`**: Formats indicator values for display
- **`market_formatter.py`**: Formats market overview and microstructure data
- **`technical_formatter.py`**: Formats technical analysis sections

## Core Analysis Engine

### AnalysisEngine

**Location**: `src/analyzer/core/analysis_engine.py`

**Purpose**: Main orchestrator that coordinates the entire analysis pipeline from data collection to publication.

**Key Responsibilities**:
- Initialize all analysis components with proper dependency injection
- Coordinate multi-timeframe data collection (1h, 2h, 4h, 6h, 8h, 12h, 1d)
- Manage analysis context lifecycle
- Execute analysis pipeline: data → indicators → patterns → AI → publication
- Handle errors and provide graceful degradation

**Core Methods**:
- **`initialize_for_symbol(symbol, exchange, language, timeframe)`**: Set up analyzer for specific trading pair
- **`analyze_market(channel_id, provider, model)`**: Main analysis entry point - full pipeline execution
- **`_execute_analysis_pipeline()`**: Internal pipeline orchestration
- **`set_discord_notifier(discord_notifier)`**: Set Discord integration (avoids circular dependencies)

**Component Initialization**:
```python
# Specialized components
self.model_manager = ModelManager(logger)
self.technical_calculator = TechnicalCalculator(logger, format_utils)
self.pattern_analyzer = PatternAnalyzer(logger, format_utils)
self.prompt_builder = PromptBuilder(timeframe, logger, technical_calculator, config, format_utils)
self.html_generator = AnalysisHtmlGenerator(logger, format_utils)
self.chart_generator = ChartGenerator(logger, config, format_utils)
self.data_collector = MarketDataCollector(logger, rag_engine, alternative_me_api)
self.metrics_calculator = MarketMetricsCalculator(logger)
self.result_processor = AnalysisResultProcessor(model_manager, logger)
self.publisher = AnalysisPublisher(logger, html_generator, coingecko_api, discord_notifier)
```

**Analysis Pipeline Flow**:
```
initialize_for_symbol() → set context
    ↓
analyze_market() → main entry
    ↓
data_collector.collect_data() → OHLCV, news, sentiment
    ↓
technical_calculator.get_indicators() → 50+ technical indicators
    ↓
pattern_analyzer.analyze_patterns() → chart & indicator patterns
    ↓
metrics_calculator.calculate_metrics() → multi-timeframe metrics
    ↓
prompt_builder.build_prompt() → assemble AI context
    ↓
model_manager.send_prompt() → AI analysis
    ↓
result_processor.process_response() → parse & structure results
    ↓
publisher.publish_analysis() → Discord embed + HTML report
```

**Configuration**:
- Uses `TimeframeValidator` to ensure valid timeframe selection
- Supports timeframe override per analysis request
- Adaptive candle limits based on timeframe (~30 days of data)

### AnalysisContext

**Location**: `src/analyzer/core/analysis_context.py`

**Purpose**: Centralized data container holding all analysis state throughout the pipeline.

**Key Attributes**:
- **`symbol`**: Trading pair (e.g., "BTC/USDT")
- **`exchange`**: Exchange name
- **`timeframe`**: Analysis timeframe (1h-1d)
- **`current_price`**: Latest market price
- **`ohlcv_candles`**: Raw OHLCV data array
- **`timestamps`**: Datetime timestamps for each candle
- **`indicators`**: Dictionary of calculated technical indicators
- **`patterns`**: Detected chart and indicator patterns
- **`market_metrics`**: Multi-period market metrics
- **`sentiment`**: Fear & Greed index data
- **`market_overview`**: CoinGecko global market data
- **`coin_details`**: Specific coin information
- **`long_term_data`**: Daily macro indicators (200D SMA, etc.)
- **`weekly_macro_indicators`**: Weekly macro trends (200W SMA)
- **`market_microstructure`**: Order book, trades, funding rate

**Usage Pattern**:
```python
context = AnalysisContext(symbol)
context.exchange = "Binance"
context.timeframe = "4h"
# Components populate context as pipeline progresses
await data_collector.collect_data(context)
indicators = await technical_calculator.calculate_all_indicators(context)
context.indicators = indicators
```

### AnalysisResultProcessor

**Location**: `src/analyzer/core/analysis_result_processor.py`

**Purpose**: Transforms raw AI model responses into structured, validated analysis results.

**Responsibilities**:
- Parse JSON from AI responses (handles markdown fences, formatting issues)
- Validate required fields in analysis results
- Extract structured data (trend, strength, price targets, confidence)
- Handle parsing failures gracefully with error details
- Preserve raw response for HTML generation

**Key Methods**:
- **`process_response(raw_response, provider, model, language, article_urls)`**: Main processing entry point
- **`_parse_structured_data(raw_response)`**: Extract JSON from response
- **`_validate_analysis(analysis_dict)`**: Ensure required fields present

**Output Structure**:
```python
{
    "analysis": {
        "trend": "BULLISH",
        "strength": 7.5,
        "confidence": 0.82,
        "short_term_target": 67500.00,
        "medium_term_target": 72000.00,
        "key_levels": {...}
    },
    "raw_response": "## Market Analysis\n...",
    "provider": "googleai",
    "model": "gemini-2.5-flash",
    "language": "English",
    "article_urls": {...}
}
```

## Data Collection Layer

### MarketDataCollector

**Location**: `src/analyzer/data/market_data_collector.py`

**Purpose**: Comprehensive market data aggregation from multiple sources with intelligent caching.

**Responsibilities**:
- Fetch multi-timeframe OHLCV data with adaptive candle limits
- Retrieve Fear & Greed sentiment index
- Gather news context via RAG engine
- Collect long-term historical data (daily/weekly)
- Fetch market microstructure (order book, trades, funding)
- Process and normalize all data for analysis

**Key Methods**:
- **`initialize(data_fetcher, symbol, exchange, timeframe, limit)`**: Configure collector for symbol
- **`collect_data(context)`**: Main entry - fetch all data sources
- **`fetch_ohlcv(context)`**: Get primary timeframe OHLCV data
- **`fetch_long_term_historical_data(context)`**: Daily macro indicators (200D SMA)
- **`fetch_weekly_macro_data(context, target_weeks)`**: Weekly analysis (200W SMA)
- **`fetch_and_process_sentiment_data(context)`**: Fear & Greed index

**Adaptive Candle Limits**:
```python
# Automatically calculates candles needed for ~30 days
if limit is None:
    target_days = 30
    self.limit = TimeframeValidator.get_candle_limit_for_days(timeframe, target_days)
    # 1h: 720 candles, 4h: 180 candles, 1d: 30 candles
```

**Data Sources**:
- Exchange: OHLCV data via ccxt
- RAG Engine: News articles and market context
- Alternative.me: Fear & Greed sentiment
- CoinGecko (via RAG): Global market metrics

**Integration**:
```python
# Used by AnalysisEngine
result = await self.data_collector.collect_data(context)
if result["success"]:
    self.article_urls = result["article_urls"]
    # Context now populated with all market data
```

### DataFetcher

**Location**: `src/analyzer/data/data_fetcher.py`

**Purpose**: Low-level exchange data fetching with robust error handling and retry logic.

**Responsibilities**:
- Fetch candlestick data from exchanges
- Handle exchange-specific quirks and rate limits
- Implement exponential backoff retry logic
- Convert exchange timestamps to consistent format
- Extract current price from latest candle

**Key Methods**:
- **`fetch_candlestick_data(pair, timeframe, limit)`**: Fetch OHLCV with retries
- **`_convert_to_numpy(ohlcv_list)`**: Convert to numpy array for calculations

**Error Handling**:
- Retries up to 3 times with exponential backoff
- Handles `ccxt.NetworkError`, `ccxt.ExchangeError`
- Logs detailed error information for debugging
- Returns `None` on failure (caller handles gracefully)

### DataProcessor

**Location**: `src/analyzer/data/data_processor.py`

**Purpose**: Transforms and normalizes raw data into analysis-ready formats.

**Responsibilities**:
- Convert timestamps to datetime objects
- Normalize price/volume data
- Calculate derived metrics (returns, volatility)
- Handle missing data and outliers

## Technical Calculations

### TechnicalCalculator

**Location**: `src/analyzer/calculations/technical_calculator.py`

**Purpose**: Comprehensive technical indicator calculation engine with 50+ indicators.

**Key Features**:
- **No caching**: Always calculates fresh to avoid stale data
- **Timeframe-adaptive**: Indicator periods scale with timeframe
- **Vectorized**: Uses numpy/numba for performance
- **Complete coverage**: Momentum, trend, volatility, volume, statistical indicators

**Indicator Categories**:

**Momentum Indicators**:
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Stochastic Oscillator (%K, %D)
- Williams %R
- Ultimate Oscillator (UO)

**Trend Indicators**:
- ADX (Average Directional Index) + DI+/DI-
- Supertrend with direction
- Ichimoku Cloud (conversion, base, spans A/B)
- Parabolic SAR

**Volatility Indicators**:
- ATR (Average True Range) + ATR%
- Bollinger Bands (upper/middle/lower) + %B
- Keltner Channels
- Donchian Channels

**Volume Indicators**:
- VWAP (Volume Weighted Average Price)
- TWAP (Time Weighted Average Price)
- MFI (Money Flow Index)
- OBV (On Balance Volume)
- CMF (Chaikin Money Flow)
- Force Index
- CCI (Commodity Channel Index)

**Statistical Indicators**:
- Z-Score
- Kurtosis
- Hurst Exponent

**Support/Resistance**:
- Basic support/resistance levels
- Advanced support/resistance with volume confirmation
- Fibonacci retracement levels (23.6%, 38.2%, 50%, 61.8%)
- Pivot Points (PP, R1-R4, S1-S4)

**Key Methods**:
- **`get_indicators(ohlcv_data)`**: Calculate all indicators - main entry point
- **`format_indicator_value(value, decimals)`**: Format for display
- **`get_indicator_thresholds()`**: Return threshold configurations

**Threshold Configuration**:
```python
INDICATOR_THRESHOLDS = {
    'rsi': {'oversold': 30, 'overbought': 70},
    'stoch_k': {'oversold': 20, 'overbought': 80},
    'williams_r': {'oversold': -80, 'overbought': -20},
    'adx': {'weak': 25, 'strong': 50, 'very_strong': 75},
    'mfi': {'oversold': 20, 'overbought': 80},
    'bb_width': {'tight': 2, 'wide': 10}
}
```

**Integration**:
```python
# Called by AnalysisEngine after data collection
indicators = self.technical_calculator.get_indicators(context.ohlcv_candles)
context.indicators = indicators
```

### PatternAnalyzer

**Location**: `src/analyzer/calculations/pattern_analyzer.py`

**Purpose**: Detects chart patterns and indicator patterns using specialized engines.

**Responsibilities**:
- Coordinate chart pattern detection via `PatternEngine`
- Coordinate indicator pattern detection via `IndicatorPatternEngine`
- Aggregate pattern results into unified structure
- Filter patterns by confidence and timestamp

**Key Methods**:
- **`analyze_patterns(context)`**: Main entry - detect all patterns
- **`detect_chart_patterns(ohlcv_data)`**: Use PatternEngine for chart patterns
- **`detect_indicator_patterns(indicators, ohlcv_data)`**: Use IndicatorPatternEngine

**Pattern Types Detected**:

**Chart Patterns** (via PatternEngine):
- Head and Shoulders / Inverse H&S
- Double Top / Double Bottom
- Ascending/Descending/Symmetrical Triangles
- Rising/Falling Wedges
- Channels (ascending/descending/horizontal)
- Flags and Pennants

**Indicator Patterns** (via IndicatorPatternEngine):
- RSI: W-bottoms, M-tops, oversold/overbought
- MACD: Bullish/bearish crossovers, zero-line crosses, divergences
- Stochastic: Crossovers, oversold/overbought
- Divergences: RSI, MACD, Stochastic vs price
- Volume: Spikes, expansion, contraction
- Volatility: ATR spikes, Bollinger Band squeezes

**Output Structure**:
```python
{
    "chart_patterns": [
        {
            "type": "head_and_shoulders",
            "confidence": 0.85,
            "timestamp": datetime(...),
            "description": "Bearish H&S pattern detected..."
        }
    ],
    "indicator_patterns": {
        "rsi": [...],
        "macd": [...],
        "divergences": [...]
    }
}
```

**Integration**: See **`pattern_engine/AGENTS.md`** for detailed pattern detection algorithms.

### MarketMetricsCalculator

**Location**: `src/analyzer/calculations/market_metrics_calculator.py`

**Purpose**: Calculates aggregated metrics across multiple time periods for context.

**Metrics Calculated**:
- **Price changes**: 1h, 4h, 24h, 7d, 30d percentage changes
- **Volume metrics**: Average volume, volume trend
- **Volatility**: Standard deviation, ATR-based volatility
- **Trend strength**: Multi-period momentum indicators
- **Market structure**: Higher highs/lows, support/resistance breaks

**Key Methods**:
- **`calculate_metrics(context)`**: Calculate all period-based metrics
- **`_calculate_period_metrics(ohlcv_data, period_name)`**: Single period calculation

**Output**:
```python
{
    "1h": {"change_pct": 2.5, "volume": 1234.5, ...},
    "4h": {"change_pct": 5.2, "volume": 5678.9, ...},
    "24h": {"change_pct": 12.3, "volume": 9876.5, ...},
    ...
}
```

## Prompt Generation

### PromptBuilder

**Location**: `src/analyzer/prompts/prompt_builder.py`

**Purpose**: Assembles comprehensive AI prompts from all analysis components using modular formatters.

**Responsibilities**:
- Aggregate data from context into coherent sections
- Format technical indicators for AI consumption
- Include market overview and sentiment
- Add pattern detection results with timestamps
- Provide analysis instructions and response template
- Optimize token usage while maintaining completeness

**Component Managers**:
- **`TemplateManager`**: Analysis instructions and response format
- **`MarketFormatter`**: Market overview, order book, funding rate
- **`TechnicalFormatter`**: Technical indicator formatting
- **`ContextBuilder`**: Trading context, sentiment, coin details

**Key Methods**:
- **`build_prompt(context, has_chart_analysis)`**: Main assembly method
- **`_has_advanced_support_resistance()`**: Check for advanced S/R detection

**Prompt Structure**:
```
1. Trading Context (symbol, exchange, timeframe, current price)
2. Market Sentiment (Fear & Greed index)
3. Market Overview (global metrics, dominance, DeFi data)
4. Coin Details (market cap, supply, description)
5. Market Microstructure (order book, trade flow, funding)
6. OHLCV Summary (recent price action)
7. Technical Analysis (all indicators with current values)
8. Pattern Detection Results (chart + indicator patterns)
9. Long-term Analysis (daily + weekly macro trends)
10. Analysis Instructions (step-by-step guidance)
11. Response Template (structured JSON format)
```

**Token Optimization**:
- Prioritizes recent data over historical
- Summarizes large datasets
- Uses the `TokenCounter` to estimate prompt size
- Adaptively reduces context if approaching limits

**Integration**:
```python
prompt = self.prompt_builder.build_prompt(context, has_chart_analysis=True)
response = await self.model_manager.send_prompt(prompt)
```

### TemplateManager

**Location**: `src/analyzer/prompts/template_manager.py`

**Purpose**: Manages prompt templates, analysis instructions, and response formats.

**Responsibilities**:
- Provide step-by-step analysis instructions
- Define structured response JSON template
- Customize instructions based on available data
- Support multiple languages

**Key Methods**:
- **`build_analysis_steps(symbol, has_advanced_sr, has_chart_analysis, available_periods)`**: Create analysis instructions
- **`build_response_template(has_chart_analysis)`**: Define expected response structure

**Analysis Steps Template**:
```
1. Analyze current price action and recent candles
2. Evaluate technical indicators (momentum, trend, volatility, volume)
3. Identify support/resistance levels
4. Assess pattern formations
5. Consider market sentiment and global conditions
6. Determine trend direction and strength
7. Calculate price targets with confidence levels
8. Provide actionable recommendations
```

**Response Template**:
```json
{
  "trend": "BULLISH/BEARISH/NEUTRAL",
  "strength": 0-10,
  "confidence": 0-1,
  "short_term_target": number,
  "medium_term_target": number,
  "key_levels": {
    "support": [levels],
    "resistance": [levels]
  },
  "risk_assessment": "LOW/MEDIUM/HIGH"
}
```

### ContextBuilder

**Location**: `src/analyzer/prompts/context_builder.py`

**Purpose**: Builds contextual information sections for prompts.

**Sections Generated**:
- **Trading context**: Symbol, exchange, timeframe, current price
- **Sentiment section**: Fear & Greed index with interpretation
- **Coin details**: Market cap, circulating supply, description
- **Market data summary**: OHLCV statistics
- **Period metrics**: Multi-timeframe performance summary
- **Long-term analysis**: Daily/weekly macro trends

**Key Methods**:
- **`build_trading_context(context)`**: Basic trading information
- **`build_sentiment_section(sentiment_data)`**: Fear & Greed formatting
- **`build_coin_details_section(coin_details)`**: Coin-specific information
- **`build_market_data_section(ohlcv_candles)`**: OHLCV summary
- **`build_market_period_metrics_section(market_metrics)`**: Multi-period metrics
- **`build_long_term_analysis_section(long_term_data, current_price)`**: Macro trends

## Publishing Layer

### AnalysisPublisher

**Location**: `src/analyzer/publishing/analysis_publisher.py`

**Purpose**: Publishes analysis results to Discord with rich embeds and HTML reports.

**Responsibilities**:
- Generate HTML reports with charts and formatted analysis
- Upload HTML to Discord temporary channel
- Create rich Discord embeds with analysis summary
- Fetch coin images for embed thumbnails
- Handle publication errors gracefully

**Key Methods**:
- **`publish_analysis(symbol, timeframe, analysis_result, context)`**: Main publication entry
- **`_send_discord_embed(symbol, analysis_result)`**: Create and send embed
- **`_extract_markdown_simple(raw_response)`**: Extract markdown from AI response
- **`_prepare_chart_data(context, symbol, timeframe)`**: Prepare data for HTML charts

**Publication Flow**:
```
1. Extract detailed markdown from AI response
2. Prepare OHLCV data for chart generation
3. Generate HTML report with AnalysisHtmlGenerator
4. Upload HTML to Discord temporary channel
5. Fetch coin thumbnail image
6. Create rich Discord embed with summary
7. Send embed to main analysis channel
```

**Discord Embed Structure**:
```python
embed = {
    "title": f"{symbol} Market Analysis",
    "description": "Trend direction and key insights",
    "color": 0x00ff00,  # Green for bullish
    "fields": [
        {"name": "Trend", "value": "BULLISH"},
        {"name": "Strength", "value": "7.5/10"},
        {"name": "Confidence", "value": "82%"},
        {"name": "Targets", "value": "ST: $67,500 | MT: $72,000"}
    ],
    "thumbnail": {"url": coin_image_url},
    "footer": {"text": "Provider: Google AI | Model: gemini-2.5-flash"},
    "url": html_report_url
}
```

**Integration with HTML Generator**: See **`src/html/AGENTS.md`** for detailed HTML report generation.

## Formatting Layer

### IndicatorFormatter

**Location**: `src/analyzer/formatting/indicator_formatter.py`

**Purpose**: Formats technical indicator values for consistent display.

**Responsibilities**:
- Format numbers with appropriate decimal places
- Add units and percentages
- Highlight oversold/overbought conditions
- Format indicator arrays for prompt inclusion

**Key Methods**:
- **`format_value(value, decimals, suffix)`**: Basic value formatting
- **`format_rsi(rsi_value)`**: RSI with condition labels
- **`format_percentage(value)`**: Percentage formatting
- **`format_array_summary(array, name)`**: Summarize indicator arrays

### MarketFormatter

**Location**: `src/analyzer/formatting/market_formatter.py`

**Purpose**: Formats market overview, global metrics, and microstructure data.

**Responsibilities**:
- Format CoinGecko global market data
- Format market dominance percentages
- Format order book depth
- Format trade flow and funding rates
- Format weekly macro trends (200W SMA)

**Key Methods**:
- **`format_market_overview(market_overview, analyzed_symbol)`**: Global market section
- **`format_ticker_data(ticker_info, symbol)`**: Coin-specific ticker data
- **`format_order_book_depth(order_book, symbol)`**: Bid/ask levels
- **`format_trade_flow(recent_trades, symbol)`**: Recent trades summary
- **`format_funding_rate(funding_rate, symbol)`**: Perpetual futures funding
- **`_format_weekly_macro_section(weekly_macro_trend)`**: 200W SMA cycle analysis

### TechnicalFormatter

**Location**: `src/analyzer/formatting/technical_formatter.py`

**Purpose**: Formats complete technical analysis sections for prompts.

**Responsibilities**:
- Format all indicator categories (momentum, trend, volatility, volume)
- Highlight significant indicator levels
- Format pattern detection results
- Include indicator interpretations

**Key Methods**:
- **`format_technical_analysis(context, timeframe)`**: Main formatting entry
- **`_format_momentum_indicators(indicators)`**: RSI, MACD, Stochastic, etc.
- **`_format_trend_indicators(indicators)`**: ADX, Supertrend, Ichimoku
- **`_format_volatility_indicators(indicators)`**: ATR, Bollinger Bands, Keltner
- **`_format_volume_indicators(indicators)`**: VWAP, OBV, MFI, CMF
- **`_format_statistical_indicators(indicators)`**: Z-Score, Kurtosis, Hurst
- **`_format_support_resistance(indicators)`**: S/R levels, Fibonacci, Pivots
- **`_format_patterns(context)`**: Chart and indicator patterns

## Integration Points

### Input: From Discord Commands

Analysis triggered by:
- User command: `!analyze BTC/USDT 4h`
- CommandHandler validates and routes to AnalysisHandler
- AnalysisHandler calls `AnalysisEngine.analyze_market()`

### Output: To Discord & HTML

Results published via:
- AnalysisPublisher creates Discord embed
- HTMLGenerator creates interactive HTML report
- Discord receives embed + HTML link

### Data Flow

```
Discord Command
    ↓
AnalysisEngine.analyze_market()
    ↓
MarketDataCollector → fetch data from exchanges/APIs
    ↓
TechnicalCalculator → calculate 50+ indicators
    ↓
PatternAnalyzer → detect chart/indicator patterns
    ↓
MarketMetricsCalculator → aggregate period metrics
    ↓
PromptBuilder → assemble AI prompt
    ↓
ModelManager → get AI analysis (see platforms/AGENTS.md)
    ↓
AnalysisResultProcessor → parse & validate response
    ↓
AnalysisPublisher → Discord embed + HTML report
```

## Configuration

**Timeframe Settings** (`config/config.ini`):
```ini
[general]
timeframe = 1h
candle_limit = 720  # Auto-calculated if not specified
```

**Supported Timeframes**:
- 1h, 2h, 4h, 6h, 8h, 12h, 1d
- Validated by `TimeframeValidator`
- Adaptive candle limits for ~30 days of data

**Indicator Thresholds**:
- Defined in `TechnicalCalculator.INDICATOR_THRESHOLDS`
- Customizable per indicator category
- Used for pattern detection and signal generation

## Common Patterns

### Running Analysis

```python
# Initialize engine
engine = AnalysisEngine(logger, rag_engine, coingecko_api, ...)
await engine.initialize()

# Set up for symbol
engine.initialize_for_symbol("BTC/USDT", exchange, language="English", timeframe="4h")

# Run analysis
await engine.analyze_market(channel_id, provider="googleai", model="gemini-2.5-flash")
```

### Accessing Analysis Results

```python
# Results available after analysis
last_result = engine.last_analysis_result
trend = last_result["analysis"]["trend"]
confidence = last_result["analysis"]["confidence"]
targets = last_result["analysis"]["short_term_target"]
```

### Custom Indicator Calculation

```python
# Calculate specific indicators
calculator = TechnicalCalculator(logger)
indicators = calculator.get_indicators(ohlcv_data)
rsi = indicators["rsi"][-1]  # Latest RSI value
```

### Pattern Detection

```python
# Detect patterns
analyzer = PatternAnalyzer(logger)
patterns = await analyzer.analyze_patterns(context)
chart_patterns = patterns["chart_patterns"]
rsi_patterns = patterns["indicator_patterns"]["rsi"]
```

## Performance Considerations

### Indicator Calculation
- **No caching**: Always fresh calculations to avoid stale data
- **Vectorized operations**: Uses numpy/numba for speed
- **Parallel safe**: Each analysis gets its own calculator instance

### Data Collection
- **Adaptive limits**: Fetches only necessary candles based on timeframe
- **Concurrent fetching**: News, sentiment, and OHLCV fetched in parallel where possible
- **Retry logic**: Exponential backoff for transient failures

### Prompt Generation
- **Token optimization**: Summarizes large datasets to stay within limits
- **Prioritization**: Recent data prioritized over historical
- **Modular sections**: Only includes available data

## Error Handling

### Data Collection Failures
- Graceful degradation if news/sentiment unavailable
- Continues analysis with partial data
- Logs warnings for missing components

### Indicator Calculation Errors
- NaN handling for insufficient data periods
- Validation of input data ranges
- Error logging with context

### AI Response Parsing
- Multiple parsing strategies (JSON, markdown, text)
- Validation of required fields
- Fallback to raw response if parsing fails

## Troubleshooting

**Insufficient Data Warning**:
- Occurs when less than 30 days of candles available
- Check exchange history availability
- Consider using shorter timeframe

**Indicator NaN Values**:
- Normal for indicators requiring warm-up period
- RSI needs 14+ candles, MACD needs 26+
- Only latest values matter for analysis

**Pattern Detection Failures**:
- Requires sufficient data for pattern formation
- Check indicator values are not all NaN
- Verify OHLCV data quality

**AI Parsing Errors**:
- AI may return malformed JSON
- `AnalysisResultProcessor` has fallback parsing
- Raw response always preserved

## Files for Deeper Context

- **Core orchestration**: `core/analysis_engine.py`, `core/analysis_context.py`
- **Data collection**: `data/market_data_collector.py`, `data/data_fetcher.py`
- **Calculations**: `calculations/technical_calculator.py`, `calculations/pattern_analyzer.py`
- **Pattern detection**: `pattern_engine/` → See **`pattern_engine/AGENTS.md`**
- **Prompts**: `prompts/prompt_builder.py`, `prompts/template_manager.py`
- **Publishing**: `publishing/analysis_publisher.py`
- **AI integration**: `src/models/manager.py` → See **`platforms/AGENTS.md`**
