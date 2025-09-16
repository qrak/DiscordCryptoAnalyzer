# Discord Crypto Analyzer

<p align="left">
  <img src="https://img.shields.io/badge/python-3.13-blue.svg" />
  <img src="https://img.shields.io/badge/discord.py-2.6.3-blue.svg" />
  <img src="https://img.shields.io/badge/numpy-2.2.3-blue.svg" />
  <img src="https://img.shields.io/badge/pandas-2.3.2-blue.svg" />
  <img src="https://img.shields.io/badge/plotly-6.3.0-blue.svg" />
  <img src="https://img.shields.io/badge/ccxt-4.5.3-blue.svg" />
</p>

A powerful Discord Crypto Analyzer for real-time cryptocurrency market analysis using AI models.

## Try It Live

Join our Discord server to see the bot in action and test features in real time:

[👉 Discord Invitation Link](https://discord.gg/ZC48aTTqR2)

Channel: #ai-analysis

## Overview

Discord Crypto Analyzer is a powerful bot that provides real-time cryptocurrency analysis directly to your Discord server. It uses advanced AI models to generate detailed reports, forecasts, and detect key market patterns. It's perfect for traders and enthusiasts looking for instant, data-driven insights into the market.

## Features

- **Real-time Market Analysis**: Analyze any cryptocurrency trading pair with a simple command
- **AI-Powered Insights**: Utilizes advanced AI models to interpret complex market data
- **Technical Indicators**: Comprehensive analysis using RSI, MACD, Bollinger Bands, and many more indicators
- **Multi-Timeframe Analysis**: Examines data across multiple timeframes (1D, 2D, 3D, 7D, 30D)
- **Support & Resistance Levels**: Identifies key price levels
- **Price Targets**: Provides short-term and medium-term price targets
- **Sentiment Analysis**: Incorporates Fear & Greed index for market sentiment
- **Detailed Reports**: Generates in-depth HTML reports for comprehensive analysis
- **Anti-Spam Protection**: Built-in measures to prevent channel spam and abuse
- **Context-Aware Analysis**: Uses RAG (Retrieval-Augmented Generation) for enhanced market context
- **Multi-Language Support**: Analyze markets in multiple languages
- **Auto-Categorization**: Automatically identifies and categorizes crypto assets
- **Fault-Tolerant Design**: Multiple AI model fallbacks for continuous operation
- **Smart Caching**: Optimized data retrieval with minimal API calls
- **Educational Resources**: Automated linking to indicator explanations and definitions
- **Pattern Recognition**: Detects common chart patterns like head and shoulders, wedges, etc.
- **Market Metrics**: Calculates key metrics across various timeframes

## Installation


### Prerequisites

- Python 3.13 or higher
- Discord Bot Token
- OpenRouter API Key or Local LM Studio setup
- CryptoCompare API Key (for market data)
- Google Studio API Key (optional, for Gemini models via official Google GenAI SDK)

### Steps

1. Clone the repository or download the source code:

```bash
git clone https://github.com/qrak/DiscordCryptoAnalyzer
cd DiscordCryptoAnalyzer
```

2. (Recommended) Create a Python virtual environment:

```bash
python -m venv .venv
```

Activate the virtual environment:
- On Windows (PowerShell):
  ```bash
  .venv\Scripts\Activate.ps1
  ```
- On Windows (cmd):
  ```cmd
  .venv\Scripts\activate.bat
  ```
- On macOS/Linux:
  ```bash
  source .venv/bin/activate
  ```

3. Install the required dependencies:

```bash
pip install -r requirements.txt
```

4. Create configuration files:
   - Copy `keys.env.example` to `keys.env`
   - Set your API keys and Discord settings in the `keys.env` file
   - Adjust other settings in `config/config.ini` as needed

5. Run the bot:

```bash
python start.py
```


## Configuration

The configuration is split across two files:

### `keys.env`

Contains sensitive information that should not be committed to version control:

- `BOT_TOKEN_DISCORD`: Your Discord bot token
- `OPENROUTER_API_KEY`: API key for OpenRouter AI services
- `GOOGLE_STUDIO_API_KEY`: API key for Google Studio (Gemini) models
- `CRYPTOCOMPARE_API_KEY`: API key for CryptoCompare data
- `GUILD_ID_DISCORD`: ID of your Discord server
- `MAIN_CHANNEL_ID`: Main channel for bot communication
- `TEMPORARY_CHANNEL_ID_DISCORD`: Channel for temporary file uploads

### `config/config.ini`

Contains non-sensitive configuration that can be safely committed.

How AI Provider Selection Works

Use the `provider` setting in the `[ai_providers]` section of `config/config.ini` to select the AI provider. This section explains the available options and exact runtime behavior.

- `provider` (string) — valid values and behavior:
  - `"local"`: Use LM Studio only (local models). LM Studio is the only provider used; streaming is supported when LM Studio is available. If LM Studio fails, the request will fail — there is no automatic fallback.
  - `"googleai"`: Use Google AI Studio only (Gemini models). Google is the single provider; no automatic fallbacks to other providers on failure.
  - `"openrouter"`: Use OpenRouter only. OpenRouter is the single provider; no automatic fallbacks to other providers on failure.
  - `"all"`: Use the fallback chain. In this mode the runtime will try providers in this order until one returns a valid response:
    1. Google AI Studio
    2. LM Studio (local)
    3. OpenRouter

  When `provider` is set to `"all"`, the system preserves the original fallback behavior. For single-provider settings (`"local"`, `"googleai"`, `"openrouter"`) there is no cross-provider fallback.

- `lm_studio_base_url`: URL for LM Studio (default: "http://localhost:1234/v1")
- `lm_studio_model`: Model identifier for LM Studio (default: "local-model")
- `OPENROUTER_BASE_URL`: Base URL for OpenRouter API (default: "https://openrouter.ai/api/v1")
- `OPENROUTER_BASE_MODEL`: Default OpenRouter model identifier (e.g. "google/gemini-2.5-flash")
- `OPENROUTER_FALLBACK_MODEL`: Fallback model identifier for OpenRouter
- `GOOGLE_STUDIO_MODEL`: Default Google model identifier (e.g. "gemini-2.5-flash")
- `TIMEFRAME`: Default timeframe for analysis (default: "1h")
- `LOG_DIR`: Directory for log files (default: "logs")
- `LOGGER_DEBUG`: Enable debug logging
- `ANALYSIS_COOLDOWN_COIN`: Time between analyses of the same coin (in seconds)
- `ANALYSIS_COOLDOWN_USER`: Time between user requests (in seconds)
- `RAG_UPDATE_INTERVAL_HOURS`: How often to update the RAG (Retrieval-Augmented Generation) system
- `SUPPORTED_LANGUAGES`: Dictionary of supported languages for analysis output

## Usage

### Commands

- `!analyze <symbol>`: Analyze a trading pair (e.g., `!analyze BTC/USDT`)
- `!analyze <symbol> <language>`: Analyze in a specific language (e.g., `!analyze BTC/USDT Polish`)
- `!cleanup`: Force cleanup of expired messages (owner only)
- `!shutdown`: Shutdown the bot (owner only)
- `!restart`: Restart the bot (owner only)
- `!unmute <user>`: Unmute a user that was muted for spamming

### Example



```
!analyze BTC/USDT
!analyze BTC/USDT Polish
!analyze BTC/USDT Spanish
!analyze BTC/USDT French
!analyze BTC/USDT German
!analyze BTC/USDT Chinese
!analyze BTC/USDT Japanese
!analyze BTC/USDT Russian
```

Supported languages: English, Polish, Spanish, French, German, Chinese, Japanese, Russian

The bot will process the request and provide:
1. A confirmation message that analysis is in progress
2. A detailed embed with the analysis results including trend direction, strength.
3. An HTML file with the complete in-depth analysis

## Architecture

The bot is structured into a well-organized architecture with several key components:

- **Core Application**: Handles initialization, shutdown, and coordination between components
- **Market Analysis Engine**: Orchestrates data collection, indicator calculation, and analysis generation
  - Data Collector: Fetches market data from exchanges and APIs
  - Indicator Calculator: Computes technical indicators and detects patterns
  - Result Processor: Interprets data through AI models
  - Analysis Publisher: Distributes results through Discord
- **Discord Interface**: Manages commands, message handling, and user interactions
  - Command Handler: Processes user commands and coordinates responses
  - Anti-Spam System: Prevents abuse through request rate limiting
  - Reaction Handler: Enables interactive elements through emoji reactions
  - File Handler: Manages temporary file uploads and cleanup
- **RAG Engine**: Retrieval-Augmented Generation system for enhanced analysis
  - News Database: Maintains indexed repository of recent crypto news
  - Market Context: Provides real-time market data for analysis
  - Periodic Updates: Automatically refreshes data at configured intervals
  - Symbol Recognition: Identifies cryptocurrency symbols in news articles
- **Platform APIs**: Interfaces with data sources
  - CoinGecko API: Market caps, dominance metrics, and global data
  - CryptoCompare API: News, OHLCV data, and price information
  - Alternative.me API: Fear & Greed index for sentiment analysis
- **AI Model Management**: 
  - Multi-Provider Strategy: Uses local and cloud-based AI models
  - Official Google GenAI SDK: Integrated official Google AI SDK for enhanced reliability
  - Fallback Chain: Gracefully handles API failures and rate limits
  - Response Parsing: Transforms raw AI output to structured data
  - Token Tracking: Monitors and optimizes token usage
- **HTML Generator**: Creates visual reports of analysis results
- **Logger System**: Comprehensive logging with error tracking

## Technical Analysis System

The bot implements a comprehensive technical analysis system that combines traditional indicators with AI interpretation:

### Technical Indicators

- **Trend Indicators**: ADX, Directional Movement (DI+/DI-), Supertrend
- **Momentum Indicators**: RSI, MACD, Stochastic Oscillator, Williams %R
- **Volume Indicators**: MFI, OBV, Chaikin Money Flow, Force Index
- **Volatility Indicators**: ATR, Bollinger Bands
- **Price Indicators**: VWAP, TWAP, Simple Moving Averages, Exponential Moving Averages
- **Statistical Indicators**: Z-Score, Kurtosis, Hurst Exponent

### Pattern Recognition

The system automatically detects chart patterns including:
- Head and Shoulders (bullish/bearish)
- Double Top/Bottom
- Wedges (rising/falling)
- Triangles (ascending/descending/symmetrical)
- Support/Resistance breakouts
- Trend lines and channels

### Performance Optimization

- **Smart Caching**: Indicators are cached using data hashing to avoid redundant calculations
- **Parallelized Computation**: Leverages numpy vectorization for performance
- **Progressive Loading**: HTML reports load essential components first for better user experience

## HTML Report System

The bot generates detailed HTML analysis reports that include:

### Interactive Charts

- Candlestick charts with price and volume data, RSI
- Interactive controls for zooming, panning, and data exploration

### Content Enrichment

- **Smart Indicator Linking**: Technical terms automatically link to educational resources
- **News Integration**: Relevant news articles are referenced and linked
- **Source Attribution**: News sources are properly cited and accessible
- **Responsive Design**: Reports display properly on mobile and desktop devices

### Analysis Components

- Technical analysis summary
- Trend direction and strength assessment
- Support and resistance levels
- Price target projections
- Timeframe comparisons
- Confidence scores
- Risk assessment metrics

## AI Analysis System

The bot leverages advanced AI models to interpret market data and generate insights through a sophisticated prompt engineering system:

### Prompt Engineering

- **Structured Data Format**: Market data is organized into clearly defined sections for optimal AI processing
- **Context Enrichment**: Current market data is enhanced with historical context and sentiment indicators
- **Multi-Timeframe Integration**: Analysis spans from hourly to yearly data for comprehensive perspective
- **Pattern Highlighting**: Notable patterns and setups are automatically emphasized for the AI model
- **Guided Analysis Framework**: Step-by-step analysis instructions ensure thorough examination of all factors

### Response Processing

- **JSON Parsing**: Extracts structured data from AI responses for standardized display in Discord
- **Markdown Formatting**: Converts detailed analysis into well-formatted, readable content
- **Language Adaptation**: Processes analysis in multiple languages while maintaining technical accuracy
- **Error Handling**: Gracefully handles malformed AI responses with fallback strategies

### AI Model Orchestration

- **Tiered Provider Strategy**:
  1. Local models (LM Studio) for speed and privacy when available
  2. OpenRouter for access to state-of-the-art models
  3. Google AI Studio as fallback for reliability
- **Adaptive Selection**: Dynamically switches between models based on availability and response quality
- **Session Persistence**: Maintains context across analysis requests when beneficial
- **Token Optimization**: Intelligently manages prompt length to balance detail and token usage

## RAG System (Retrieval-Augmented Generation)

The bot includes a sophisticated RAG engine that enhances market analysis with relevant context:

- **News Indexing**: Automatically collects and indexes cryptocurrency news articles
- **Market Context**: Provides real-time market data including global metrics and sentiment
- **Multi-dimensional Search**: Finds relevant information across categories, tags, and content
- **Content Ranking**: Prioritizes information based on recency, relevance, and importance
- **Contextual Integration**: Seamlessly incorporates retrieved information into AI prompts
- **Automated Updates**: Periodically refreshes knowledge base with latest market information
- **Symbol Recognition**: Automatically identifies cryptocurrency mentions in news articles

 
## Example Output

You can find a sample HTML analysis report in the `example_html` directory:

- `example_html/ETHUSDT_analysis_20250915155439.html`

This file demonstrates the bot's output for a typical market analysis, including interactive charts and technical indicators.

## Example Images

Below are sample images generated by the bot, located in the `img` directory:

![Chart Example 1](img/1.png)
![Chart Example 2](img/2.png)

## License

MIT

## Disclaimer

This bot is for informational and educational purposes only. It does not provide trading signals or financial recommendations, and should not be considered as financial advice. Always do your own research before making investment decisions.
