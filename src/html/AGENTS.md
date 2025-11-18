# HTML & Visualization Agents Documentation

**Parent Instructions**: See `/AGENTS.md` for global project context and universal coding guidelines.

**This document** contains HTML/visualization-specific implementation details that extend/override root instructions.

---

## Overview

The HTML and visualization layer provides high-performance report generation and interactive chart creation. It coordinates multiple agents to transform market analysis data into publication-ready HTML reports and visual representations for Discord and web display.

## Directory Structure

The `src/html/` directory contains a comprehensive HTML generation and visualization system organized into the following structure:

### Core Files
- **`AGENTS.md`**: This documentation file describing all HTML agents and their responsibilities
- **`html_generator.py`**: Main orchestrator class (`AnalysisHtmlGenerator`) that coordinates all HTML generation components
- **`chart_generator.py`**: Specialized chart creation utility (`ChartGenerator`) for interactive Plotly charts and PNG exports
- **`html_templates.py`**: Legacy template handling (being phased out in favor of `generators/template_processor.py`)
- **`mock.py`**: Testing utilities for generating sample HTML reports without real analysis data

### Generators Subdirectory (`generators/`)
Specialized content processing agents:
- **`chart_section_generator.py`**: Generates HTML sections containing embedded charts with metadata
- **`content_formatter.py`**: Formats analysis data and technical findings into readable HTML content
- **`content_link_processor.py`**: Processes and optimizes links in HTML content (trading platforms, news, research)
- **`template_processor.py`**: Manages HTML template rendering and variable substitution
- **`__init__.py`**: Package initialization

### Templates Subdirectory (`templates/`)
HTML template files:
- **`base_template.html`**: Main HTML document structure with embedded CSS/JS for complete reports
- **`error_template.html`**: Error handling template for failed report generation

### Styles Subdirectory (`styles/`)
CSS styling files for responsive, accessible design:
- **`base_styles.css`**: Core styling with CSS variables for light/dark theme support
- **`component_styles.css`**: Component-specific styles (buttons, containers, etc.)
- **`table_discord_styles.css`**: Table formatting optimized for Discord display
- **`ui_responsive.css`**: Responsive design rules for mobile and desktop viewing

### Scripts Subdirectory (`scripts/`)
JavaScript files for interactive functionality:
- **`app.js`**: Main application logic and initialization
- **`theme-manager.js`**: Theme switching between light/dark modes with localStorage persistence
- **`collapsible-manager.js`**: Expandable/collapsible content sections
- **`back-to-top.js`**: Smooth scrolling back-to-top functionality

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

#### Chart Configuration Reference

- **Color Themes**: Switch between `default_colors` and `ai_colors` by passing `for_ai=True` into chart helpers. Override colors by subclassing `ChartGenerator` or updating `self.default_colors` at runtime before calling `create_ohlcv_chart`.
- **Candle Limits**: `self.ai_candle_limit` is sourced from `config.AI_CHART_CANDLE_LIMIT` (defaults to 200). Supply `limit_candles` to `create_ohlcv_chart`/`generate_chart_html` to clamp history for faster plots.
- **Line Thickness & Fonts**: The generator automatically widens candles, grid lines, and fonts when `for_ai=True`. For custom styling set `increasing_line_width`/`decreasing_line_width` on the returned Plotly traces before exporting.
- **Formatter Hooks**: Provide a custom `formatter` callable (e.g., `format_utils.fmt`) via the constructor to control price formatting in tooltips and axes.
- **Timestamps**: Pass explicit `timestamps` arrays to avoid relying on millisecond epochs embedded in OHLCV data—useful when candles come from preprocessed pandas frames.

#### HTML Generation Workflows

1. **Full Analysis Report**
    - Collect analysis output (markdown, article URLs, OHLCV payload) from the analyzer pipeline.
    - Call `AnalysisHtmlGenerator.generate_html_content(...)` with the same dictionary shape used by `AnalysisPublisher` (`ohlcv` ndarray, `technical_history`, `patterns`).
    - Persist the returned HTML string to disk or upload directly to Discord via `DiscordNotifier.upload_analysis_content`.
2. **Chart-Only Preview**
    - Build a minimal `ohlcv_data` dict containing `ohlcv`, `symbol`, `timeframe`, and optional `technical_history` (RSI array) and feed into `ChartSectionGenerator.generate_chart_html`.
    - Embed the returned `<div>` fragment inside existing dashboards without running the full template pipeline.
3. **Mock Reports for Testing**
    - Use `src/html/mock.py` utilities (e.g., `get_mock_markdown_content`) to generate deterministic markdown/indicator data.
    - Pass mock data through `AnalysisHtmlGenerator` to validate CSS/JS changes without hitting external services.

#### Embedded Asset Pipeline

- **TemplateProcessor**: `generate_styled_html` pulls the rendered markdown, chart sections, and Discord summary into the modular HTML scaffold while stamping generation/expiry timestamps.
- **Template Engine**: `html_templates.ModularTemplateEngine` base64-encodes CSS assets (`base_styles.css`, `component_styles.css`, `ui_responsive.css`, etc.) so Discord uploads remain self-contained—no external CDNs required.
- **JavaScript Bundling**: Scripts (`theme-manager.js`, `collapsible-manager.js`, `back-to-top.js`, `app.js`) are injected inline to keep embeds interactive even when viewed from static hosting environments.
- **Cache Busting**: Call `html_templates.reload_templates()` during development to force re-read of updated CSS/JS without restarting the bot.

## Report Generation Agents

### HTMLGenerator

**Location**: `src/html/html_generator.py`

**Purpose**: Orchestrates complete HTML report generation from analysis data via the `AnalysisHtmlGenerator` class.

**Responsibilities**:
- Coordinate chart generation, content formatting, and template processing
- Build comprehensive technical analysis reports
- Integrate analysis results with market data
- Generate historical performance summaries
- Create multi-symbol comparison reports

**Key Components**:
- **`TemplateProcessor`**: Handles HTML template loading and variable substitution
- **`ChartSectionGenerator`**: Creates chart HTML sections with embedded Plotly data
- **`ContentLinkProcessor`**: Adds trading platform and news links to content
- **`ContentFormatter`**: Processes Markdown content to HTML with proper formatting

**Main Methods**:
- **`generate_html_content()`**: Core method that processes title, content, article URLs, OHLCV data, and Discord analysis into complete HTML
- **`_enrich_content_with_links()`**: Adds indicator and news links to Markdown content
- **`_generate_chart_section()`**: Creates chart HTML from OHLCV data using ChartSectionGenerator
- **`_generate_discord_summary_section()`**: Formats Discord-specific analysis summaries

**Workflow**:
1. Input: Analysis result from AnalysisEngine
2. Validate inputs through `ContentFormatter.validate_content_inputs()`
3. Process content through link enrichment pipeline
4. Generate chart sections if OHLCV data available
5. Create Discord summary sections
6. Apply base template with embedded CSS/JS
7. Output: Complete HTML report string

**Output Format**: 
- Standalone HTML files ready for Discord upload
- Embeddable HTML snippets for web integration
- Self-contained styles and scripts (no external dependencies)
- Base64-encoded CSS/JS for portability

## Content Formatting Agents

### ContentFormatter

**Location**: `src/html/generators/content_formatter.py`

**Purpose**: Formats analysis data and technical findings into readable HTML content.

**Responsibilities**:
- Convert indicator values to formatted strings with appropriate precision
- Build pattern detection summaries with confidence levels
- Create trend analysis narratives from technical data
- Format price levels (support/resistance) with currency symbols
- Generate statistical summaries for indicators and patterns
- Process Markdown content to HTML with syntax highlighting

**Key Methods**:
- **`validate_content_inputs()`**: Validates title and content before processing
- **`process_markdown_content()`**: Converts Markdown to HTML with custom formatting
- **`format_indicator_value()`**: Formats numerical values based on magnitude (2-8 decimals)
- **`format_timestamp()`**: Converts timestamps to readable format with timezone
- **`create_pattern_summary()`**: Builds HTML summaries of detected chart patterns

**Features**:
- Number formatting with appropriate decimals based on value magnitude
- Timestamp formatting with timezone awareness
- Pattern descriptions with confidence levels and timestamps
- Trading signal generation from technical indicators
- Markdown processing with table support and code highlighting

### TemplateProcessor

**Location**: `src/html/generators/template_processor.py`

**Purpose**: Manages HTML template rendering and variable substitution with embedded assets.

**Responsibilities**:
- Load HTML templates from `src/html/templates/` directory
- Perform variable substitution with analysis data and embedded CSS/JS
- Apply conditional rendering (show/hide sections based on analysis data availability)
- Inject base64-encoded CSS and JavaScript files for self-contained reports
- Handle template caching and error recovery

**Key Methods**:
- **`generate_styled_html()`**: Main method that combines template with content and embedded assets
- **`_load_template()`**: Loads template files from disk with error handling
- **`_embed_css_files()`**: Base64-encodes CSS files for inline embedding
- **`_embed_js_files()`**: Base64-encodes JavaScript files for inline embedding

**Templates**:
- **`base_template.html`**: Main HTML document structure with placeholders for content, CSS, and JS
- **`error_template.html`**: Fallback template for error conditions

**Embedded Assets**:
- Base64-encoded CSS files (`base_styles.css`, `component_styles.css`, etc.)
- Base64-encoded JavaScript files (`theme-manager.js`, `collapsible-manager.js`, etc.)
- Inline Plotly chart data for interactive visualizations

### ContentLinkProcessor

**Location**: `src/html/generators/content_link_processor.py`

**Purpose**: Processes and optimizes links in HTML content for enhanced user experience.

**Responsibilities**:
- Generate trading platform links (TradingView, Binance, Coinbase, etc.)
- Create news and research links from article data
- Validate link URLs and handle broken links gracefully
- Track external resource references for analytics
- Add contextual links for technical indicators mentioned in text

**Key Methods**:
- **`add_indicator_links()`**: Adds links to technical indicators (RSI, MACD, etc.) mentioned in content
- **`add_news_links()`**: Integrates news article links into content with proper formatting
- **`generate_trading_links()`**: Creates platform-specific trading links for symbols
- **`validate_url()`**: Checks URL validity before inclusion

**Supported Platforms**:
- **TradingView**: Chart analysis links
- **Binance**: Direct trading links
- **Coinbase**: Exchange links
- **News Sources**: Integrated article links with titles

## Chart Section Generator

### ChartSectionGenerator

**Location**: `src/html/generators/chart_section_generator.py`

**Purpose**: Generates HTML sections containing embedded charts with metadata and responsive containers.

**Responsibilities**:
- Create chart containers with proper dimensions and responsive sizing
- Embed Plotly chart JSON data directly into HTML
- Add chart metadata (timeframe, analysis timestamp, indicators used)
- Manage chart interactions and responsive behavior
- Generate chart legends and technical indicator overlays

**Key Methods**:
- **`generate_chart_html()`**: Main method that creates complete chart sections from OHLCV data
- **`_create_chart_container()`**: Builds responsive HTML containers for charts
- **`_embed_plotly_data()`**: Converts Plotly figures to embedded HTML/JSON
- **`_add_chart_metadata()`**: Adds timeframe, timestamp, and indicator information

**Features**:
- Responsive chart containers that adapt to different screen sizes
- Embedded Plotly.js data for interactive charts without external dependencies
- Chart metadata display (timeframe, analysis date, indicators)
- Error handling for chart generation failures
- Support for multiple chart types (candlestick, line, indicators)

**Output**: HTML sections that can be individually embedded or combined into complete reports

## HTML Templates

**Location**: `src/html/templates/`

**Structure**:
- **`base_template.html`**: Main HTML document structure with embedded CSS/JS for complete reports
- **`error_template.html`**: Error handling template for failed report generation

**Template Features**:
- **Embedded Assets**: Base64-encoded CSS and JavaScript files for portability
- **Theme Support**: Data attributes for light/dark theme switching
- **Responsive Design**: Mobile-friendly layouts with proper viewport meta tags
- **Accessibility**: ARIA labels and semantic HTML structure
- **Interactive Elements**: Theme toggle, collapsible sections, back-to-top functionality

**Styling**: 
- `src/html/styles/`: CSS files for report formatting
- Responsive design for Discord embeds and web display
- Dark theme optimized for readability
- Print-friendly stylesheets with CSS variables for theming

## Mock Utilities

### MockGenerator

**Location**: `src/html/mock.py`

**Purpose**: Generates example reports without real analysis or AI providers for testing and development.

**Responsibilities**:
- Create sample analysis data with realistic market scenarios
- Generate example HTML reports for UI/UX validation
- Provide mock technical indicators and pattern data
- Enable rapid iteration without external API dependencies
- Support different cryptocurrency symbols and timeframes

**Key Functions**:
- **`get_mock_markdown_content()`**: Generates formatted Markdown analysis for testing
- **`mock_article_urls`**: Dictionary of sample news articles for link testing
- **Sample Data Generation**: Creates realistic OHLCV data and indicators

**Usage**:
```python
from src.html.mock import get_mock_markdown_content
html_content = get_mock_markdown_content(symbol="BTC/USDT", current_price=45000.0)
```

**Features**:
- Realistic mock data for BTC, ETH, and XRP scenarios
- Sample news context and technical analysis narratives
- Multi-timeframe assessment examples
- Indicator value simulations (RSI, MACD, Bollinger Bands, etc.)

## CSS & JavaScript Assets

### Styles (`src/html/styles/`)

**Purpose**: Provide responsive, accessible styling for HTML reports with theme support.

**Files**:
- **`base_styles.css`**: Core styling with CSS variables for light/dark themes, typography, and layout
- **`component_styles.css`**: Component-specific styles (buttons, containers, navigation)
- **`table_discord_styles.css`**: Table formatting optimized for Discord display and readability
- **`ui_responsive.css`**: Media queries and responsive design rules for mobile/desktop

**Features**:
- **CSS Variables**: Dynamic theming with `--text-color`, `--background-color`, etc.
- **Theme Support**: Automatic light/dark mode switching with smooth transitions
- **Responsive Design**: Mobile-first approach with breakpoints for tablets and desktops
- **Discord Optimization**: Styles specifically tuned for Discord embed display

### Scripts (`src/html/scripts/`)

**Purpose**: Provide interactive functionality for HTML reports.

**Files**:
- **`app.js`**: Main application initialization and coordination
- **`theme-manager.js`**: Theme switching between light/dark modes with localStorage persistence
- **`collapsible-manager.js`**: Expandable/collapsible content sections for better UX
- **`back-to-top.js`**: Smooth scrolling back-to-top button functionality

**Key Features**:
- **ThemeManager Class**: Handles theme switching with user preference persistence
- **CollapsibleManager**: Manages expandable sections for long analysis content
- **BackToTop**: Smooth scrolling navigation for lengthy reports
- **Accessibility**: Keyboard navigation and screen reader support

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
from src.html.html_generator import AnalysisHtmlGenerator

generator = AnalysisHtmlGenerator(logger=logger)
html_content = generator.generate_html_content(
    title="BTC/USDT Analysis",
    content=markdown_content,
    article_urls=news_urls,
    ohlcv_data=market_data,
    discord_analysis=analysis_result
)
url = await discord_notifier.upload_analysis_content(
    html_content, 
    "BTC/USDT", 
    channel_id,
    provider="googleai",
    model="gemini-flash-latest"
)
```

### Create AI-Optimized Chart

```python
from src.html.chart_generator import ChartGenerator

chart_gen = ChartGenerator(logger=logger, config=config)
chart_html = chart_gen.generate_chart(ohlcv_data, indicators, use_ai_colors=True)
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
