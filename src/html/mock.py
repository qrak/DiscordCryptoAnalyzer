# Mock article URLs for testing
mock_article_urls = {
    "Bitcoin Shows Relative Strength Amid Uncertainty": "https://bitcoinist.com/bitcoin-shows-relative-strength-amid-uncertainty-can-btc-outperform-equities/",
    "ETH Price Analysis: Ethereum Drop to $1100 Not Impossible": "https://cryptopotato.com/eth-price-analysis-ethereum-drop-to-1100-not-impossible/",
    "SEC Delays Decision on Ethereum ETFs Again": "https://www.coindesk.com/policy/2024/03/04/sec-delays-decision-on-blackrock-fidelity-spot-ethereum-etfs/",
    "XRP Ledger Sees Surge in Activity": "https://u.today/xrp-ledger-activity-explodes-amid-price-plunge",
    "Bearish Case For Bitcoin": "https://www.newsbtc.com/news/bitcoin/bearish-case-for-bitcoin-analyst-warns-falling-wedge-is-a-whale-trap-that-could-drag-price-to-67k/"
}

def get_mock_markdown_content(symbol: str, current_price: float) -> str:
    """
    Generates a mock Markdown analysis string for testing purposes. Includes mock article titles.

    Args:
        symbol: The trading symbol (e.g., 'BTC/USDT').
        current_price: The current price of the asset.

    Returns:
        A formatted Markdown string containing the mock analysis.
    """
    # Determine if the symbol is BTC or ETH for context
    is_btc = "BTC" in symbol.upper()
    is_eth = "ETH" in symbol.upper()
    is_xrp = "XRP" in symbol.upper()

    news_context_line = "News context simulation: Recent news mentions potential regulation changes (mock)."
    if is_btc:
        news_context_line = "News context simulation: Bitcoin Shows Relative Strength Amid Uncertainty according to recent reports."
    elif is_eth:
        news_context_line = "News context simulation: Concerns raised in ETH Price Analysis: Ethereum Drop to $1100 Not Impossible."
        news_context_line += " Also, the SEC Delays Decision on Ethereum ETFs Again."
    elif is_xrp:
        news_context_line = "News context simulation: XRP Ledger Sees Surge in Activity despite price action."


    return f"""
## Mock Analysis for {symbol} (Test Environment)

This is a **test analysis** designed to verify Markdown rendering, including tables and links.

### 1. Mock Multi-Timeframe Assessment
- **Short-Term (1h):** Neutral, price around {current_price:.4f}. ADX is low.
- **Medium-Term (7D):** Slightly Bearish, recent pullback noted.
- **Long-Term (365D):** Bullish based on mock Golden Cross.

### 2. Mock Technical Indicator Analysis
*   **Momentum:** RSI is neutral (around 50), Stochastic is overbought (mock value > 80).
*   **Trend:** ADX is weak (< 25). Price is near the mock Supertrend.
*   **Volatility:** Bollinger Bands are contracting (mock data).

### 3. Mock Key Pattern Recognition
- Mock Bullish MACD Crossover detected recently.
- Mock Volatility Squeeze identified.

### 4. Mock Support/Resistance Validation

| Type       | Level (USDT) | Source      | Notes                     |
| :--------- | :----------- | :---------- | :------------------------ |
| Resistance | {round(current_price * 1.10, 4):.4f} | Mock 30D    | Upper target              |
| Resistance | {round(current_price * 1.05, 4):.4f} | Mock 7D     | Immediate resistance      |
| **Current**| **{current_price:.4f}** | **Live**    | **Current Price**         |
| Support    | {round(current_price * 0.95, 4):.4f} | Mock 7D     | Immediate support       |
| Support    | {round(current_price * 0.90, 4):.4f} | Mock 30D    | Lower target / Stronger |

### 5. Mock Market Context Integration

Market sentiment is currently in **Fear** (mock value 32), according to the Fear & Greed Index.

| Date         | Fear & Greed Index | Classification |
| :----------- | :----------------- | :------------- |
| 2025-04-19   | 32                 | Fear           |
| 2025-04-18   | 33                 | Fear           |

{news_context_line}

### 6. Mock Risk Assessment & Trade Planning
**Trading Recommendation:** NONE (Wait for confirmation)

*   **Rationale:** Mixed signals and low volatility in a mock environment.
*   **Risk:** Market context (Fear) suggests caution.
*   **Potential Long:** Above {round(current_price * 1.05, 4):.4f} targeting {round(current_price * 1.10, 4):.4f}.
*   **Potential Short:** Below {round(current_price * 0.95, 4):.4f} targeting {round(current_price * 0.90, 4):.4f}.

*This is generated mock data.*
"""

def get_mock_analysis_data(symbol: str, current_price: float) -> dict:
    """
    Generates a complete mock analysis dictionary including JSON, Markdown, and article URLs.

    Args:
        symbol: The trading symbol.
        current_price: The current price.

    Returns:
        A dictionary containing 'analysis' (JSON part), 'markdown_content', and 'article_urls'.
    """
    mock_json_analysis = {
        "analysis": {
            "summary": f"This is a **test analysis** for {symbol} at price {current_price}. TEST_ENVIRONMENT is enabled. Includes *Markdown* formatting.",
            "observed_trend": "NEUTRAL",
            "trend_strength": 50,
            "timeframes": {
                "short_term": "NEUTRAL",
                "medium_term": "BEARISH",
                "long_term": "BULLISH"
            },
            "key_levels": {
                "support": [round(current_price * 0.95, 4), round(current_price * 0.90, 4)],
                "resistance": [round(current_price * 1.05, 4), round(current_price * 1.10, 4)]
            },
            "price_scenarios": {
                "bullish_scenario": round(current_price * 1.10, 4),
                "bearish_scenario": round(current_price * 0.90, 4)
            },
            "confidence_score": 75,
            "technical_bias": "NEUTRAL",
            "risk_ratio": 1.5,
            "market_structure": "NEUTRAL"
        }
    }
    markdown_content = get_mock_markdown_content(symbol, current_price)

    return {
        "analysis": mock_json_analysis["analysis"],
        "markdown_content": markdown_content,
        "article_urls": mock_article_urls.copy() # Return a copy
    }
