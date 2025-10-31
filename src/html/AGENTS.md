# HTML & Visualization Agents Documentation

This document describes the HTML report generation and chart visualization agents in the DiscordCryptoAnalyzer system.

## Overview

The HTML and visualization layer provides high-performance report generation and interactive chart creation. It coordinates multiple agents to transform market analysis data into publication-ready HTML reports and visual representations for Discord and web display.

## Chart Generation Agents

### ChartGenerator

**Location**: `src/html/chart_generator.py`

**Purpose**: Creates interactive and static charts for market data visualization.

**Responsibilities**:
- Generate Plotly-based interactive candlestick charts
- Render technical indicators (RSI, MACD, Bollinger Bands, etc.) as chart overlays
- Export charts to PNG format for AI analysis
- Create volume profiles and multi-timeframe visualizations
- Apply theme customization for different use cases (default, AI-optimized)

**Key Features**:
- **AI-Optimized Charts**: High-contrast colors (bright green/red for candles, pure black background) for better AI pattern recognition
- **Multi-Indicator Support**: Supports RSI, MACD, Bollinger Bands, ATR, Stochastic, and more
- **Image Export**: Thread-safe PNG export with timeout protection and retry logic
- **Responsive Design**: Charts adapt to different timeframes and data ranges
- **Performance**: Configurable candle limits (`AI_CHART_CANDLE_LIMIT`) to prevent performance degradation

**Configuration**:
```python
self.default_colors = {
    'background': '#1a1a1a',
    'grid': '#333333',
    'text': '#e0e0e0',
    'candle_up': '#26a69a',
    'candle_down': '#ef5350',
}

self.ai_colors = {
    'background': '#000000',  # Pure black
    'candle_up': '#00ff00',   # Bright green
    'candle_down': '#ff0000', # Bright red
}
```

**Export Methods**:
- `generate_chart()`: Creates interactive HTML chart
- `export_to_image()`: Converts to PNG with kaleido library
- `_image_export_with_timeout()`: Safe image export with timeout protection
- `_retry_image_export()`: Resilient export with exponential backoff

## Report Generation Agents

### HTMLGenerator

**Location**: `src/html/html_generator.py`

**Purpose**: Orchestrates complete HTML report generation from analysis data.

**Responsibilities**:
- Coordinate chart generation, content formatting, and template processing
- Build comprehensive technical analysis reports
- Integrate analysis results with market data
- Generate historical performance summaries
- Create multi-symbol comparison reports

**Workflow**:
1. Input: Analysis result from AnalysisEngine
2. Extract technical indicators and patterns
3. Generate charts using ChartGenerator
4. Format content using content_formatter
5. Apply HTML templates
6. Output: Complete HTML report string

**Output Format**: 
- Standalone HTML files ready for Discord upload
- Embeddable HTML snippets for web integration
- Self-contained styles and scripts (no external dependencies)

## Content Formatting Agents

### ContentFormatter

**Location**: `src/html/generators/content_formatter.py`

**Purpose**: Formats analysis data and technical findings into readable HTML content.

**Responsibilities**:
- Convert indicator values to formatted strings
- Build pattern detection summaries
- Create trend analysis narratives
- Format price levels (support/resistance)
- Generate statistical summaries

**Features**:
- Number formatting with appropriate decimals based on value magnitude
- Timestamp formatting with timezone awareness
- Pattern descriptions with confidence levels
- Trading signal generation from technical indicators

### TemplateProcessor

**Location**: `src/html/generators/template_processor.py`

**Purpose**: Manages HTML template rendering and variable substitution.

**Responsibilities**:
- Load HTML templates from `src/html/templates/`
- Perform variable substitution with analysis data
- Apply conditional rendering (show/hide sections based on analysis)
- Inject custom styling for different report types

**Templates**:
- `analysis_template.html`: Main analysis report template
- `chart_section_template.html`: Chart embedding sections
- `summary_template.html`: Quick summary cards
- `pattern_summary_template.html`: Pattern detection results

### ContentLinkProcessor

**Location**: `src/html/generators/content_link_processor.py`

**Purpose**: Processes and optimizes links in HTML content.

**Responsibilities**:
- Generate trading platform links (TradingView, Binance, etc.)
- Create news and research links
- Validate link URLs
- Track external resource references

## Chart Section Generator

### ChartSectionGenerator

**Location**: `src/html/generators/chart_section_generator.py`

**Purpose**: Generates HTML sections containing embedded charts with metadata.

**Responsibilities**:
- Create chart containers with proper dimensions
- Embed Plotly chart JSON data
- Add chart metadata (timeframe, analysis timestamp, indicators used)
- Manage chart interactions and responsive behavior

**Output**: HTML sections that can be individually embedded or combined

## HTML Templates

**Location**: `src/html/templates/`

**Structure**:
- **Base Template**: Contains document structure, styles, and script includes
- **Section Templates**: Reusable components for charts, indicators, patterns
- **Theme Variations**: Different templates for different use cases (analysis, summary, alert)

**Styling**: 
- `src/html/styles/`: CSS files for report formatting
- Responsive design for Discord embeds and web display
- Dark theme optimized for readability
- Print-friendly stylesheets

## Mock Utilities

### MockGenerator

**Location**: `src/html/mock.py`

**Purpose**: Generates example reports without real analysis or AI providers.

**Responsibilities**:
- Create sample analysis data
- Generate example HTML reports for testing
- Provide realistic data for UI/UX validation
- Enable rapid iteration without external dependencies

**Usage**:
```python
from src.html.mock import generate_sample_report
html_content = generate_sample_report(symbol="BTC/USDT", timeframe="4h")
```

## Integration Points

### Input: From Analysis Engine

- OHLCV market data
- Technical indicators (RSI, MACD, Bollinger Bands, etc.)
- Detected chart patterns (head & shoulders, triangles, etc.)
- Detected indicator patterns (W-bottoms, crossovers, divergences)
- Trading signals and confidence scores

### Output: To Discord

- HTML files uploaded as Discord message attachments
- Rich embeds with chart previews
- Summary statistics in message text
- Automatic message tracking and expiration

### Data Flow

```
AnalysisEngine.analyze_market()
    ↓
AnalysisResultProcessor (formats data)
    ↓
ChartGenerator (creates charts)
    ↓
ContentFormatter (formats text)
    ↓
TemplateProcessor (applies templates)
    ↓
HTMLGenerator (assembles final HTML)
    ↓
DiscordNotifier (uploads and sends)
```

## Performance Considerations

### Chart Rendering
- **Timeout Protection**: 30-second timeout on image exports to prevent hangs
- **Retry Logic**: Exponential backoff for transient kaleido failures
- **Memory Management**: Streaming for large datasets, candle limit configuration
- **Threading**: Thread-safe image export to prevent blocking

### Template Processing
- **Caching**: Compiled templates for faster rendering
- **Lazy Loading**: Charts loaded on-demand in browser
- **Compression**: Minified CSS and JavaScript

### File Size Optimization
- **Image Compression**: PNG optimization for charts
- **Inline Styles**: Avoid external CSS for Discord compatibility
- **Data Reduction**: Limit chart history based on configuration

## Customization

### Adding New Report Types

1. Create new template in `src/html/templates/`
2. Add template processor for the new type
3. Extend `HTMLGenerator` with new report method
4. Update chart configuration as needed

### Modifying Chart Appearance

1. Edit color schemes in `ChartGenerator`
2. Adjust layout in `ChartSectionGenerator`
3. Update CSS in `src/html/styles/`

### Custom Content Formatting

1. Add formatter methods to `ContentFormatter`
2. Register in template variable substitution
3. Test with mock generator

## Common Patterns

### Generate and Upload Analysis Report

```python
from src.html.html_generator import HTMLGenerator

generator = HTMLGenerator(logger, config)
html_content = generator.generate_analysis_report(analysis_result)
url = await discord_notifier.upload_analysis_content(html_content, "BTC/USDT", channel_id)
```

### Create AI-Optimized Chart

```python
from src.html.chart_generator import ChartGenerator

chart_gen = ChartGenerator(config=config)
chart_html = chart_gen.generate_chart(ohlcv, indicators, use_ai_colors=True)
png_bytes = chart_gen.export_to_image(chart_html)
```

## Configuration

- `AI_CHART_CANDLE_LIMIT`: Maximum candles to display on AI charts (default: 200)
- Theme colors: Configurable in `ChartGenerator.__init__()`
- Template paths: Configurable in `TemplateProcessor`
- Export timeout: 30 seconds (adjustable in `_image_export_with_timeout()`)

## Troubleshooting

- **Timeout errors on image export**: Increase timeout value or reduce candle count
- **Kaleido hangs**: Ensure system has available memory, restart bot
- **Templates not loading**: Check `src/html/templates/` directory existence
- **Chart rendering issues**: Verify Plotly version and kaleido installation
- **File upload failures**: Check Discord channel permissions and file size limits
