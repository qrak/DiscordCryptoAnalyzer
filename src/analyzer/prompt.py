import numpy as np
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

from src.logger.logger import Logger
from src.analyzer.indicator_calculator import IndicatorCalculator, fmt


class AnalysisContext(TypedDict):
    """Expected structure for the analysis context passed to PromptBuilder"""
    symbol: str
    current_price: float
    sentiment: Dict[str, Any]
    market_overview: Optional[Dict[str, Any]]
    technical_data: Dict[str, Any]
    market_metrics: Dict[str, Any]
    long_term_data: Dict[str, Any]
    ohlcv_candles: np.ndarray
    technical_patterns: Optional[Dict[str, Any]]


class PromptBuilder:
    def __init__(self, timeframe: str = "1h", logger: Optional[Logger] = None, indicator_calculator: Optional[IndicatorCalculator] = None) -> None:
        """Initialize the PromptBuilder
        
        Args:
            timeframe: The primary timeframe for analysis (e.g. "1h")
            logger: Optional logger instance for debugging
            indicator_calculator: Calculator for technical indicators
        """
        self.timeframe = timeframe
        self.logger = logger
        self.custom_instructions: list[str] = []
        self.language: Optional[str] = None
        self.context: Optional[AnalysisContext] = None
        self.indicator_calculator = indicator_calculator or IndicatorCalculator(logger)
        
        # Access indicator thresholds from the calculator
        self.INDICATOR_THRESHOLDS = self.indicator_calculator.INDICATOR_THRESHOLDS

    def build_prompt(self, context: AnalysisContext) -> str:
        self.context = context

        sections = [
            self._build_trading_context(),
            self._build_sentiment_section(),
        ]

        # Add market overview first before technical analysis to give it more prominence
        if self.context.market_overview:
            sections.append(self._build_market_overview_section())

        sections.extend([
            self._build_market_data(),
            self._build_technical_analysis(),
            self._build_market_period_metrics(),
            self._build_long_term_analysis(),
        ])

        # Add custom instructions if available
        if self.custom_instructions:
            sections.append("\n".join(self.custom_instructions))

        # Add analysis steps right before response template
        sections.append(self._build_analysis_steps()) # Modified instructions

        # Response template should always be last
        sections.append(self._build_response_template())

        final_prompt = "\n\n".join(filter(None, sections)) # Use a clearer separator

        return final_prompt
    
    def build_system_prompt(self, symbol: str) -> str:
        # Assuming DEFAULT_LANGUAGE is accessible, e.g., from config
        from config.config import DEFAULT_LANGUAGE

        language = getattr(self, 'language', None) or DEFAULT_LANGUAGE

        # Refined header with more specific instructions
        header_base = f"""You are providing educational crypto market analysis of {symbol} on {self.timeframe} timeframe along with multi-timeframe technical metrics and recent market data.
Focus on objective technical indicator readings and historical pattern recognition (e.g., identify potential chart patterns like triangles, head and shoulders, flags based on OHLCV data) for educational purposes only.
Present clear, data-driven observations with specific numeric values from the provided metrics. Prioritize recent price action and technical indicators over older news unless the news is highly significant.
Identify key price levels based solely on technical analysis concepts (Support, Resistance, Pivot Points, Fibonacci levels if applicable).
THIS IS EDUCATIONAL CONTENT ONLY. All analysis is for informational and educational purposes - NOT financial advice.
Always include disclaimers that this is not investment advice and users must do their own research."""

        if language == DEFAULT_LANGUAGE or language == "English":
            header = header_base
        else:
            header = f"""{header_base}
Write your entire response in {language} language. Only the JSON structure should remain in English, but all text content must be in {language}.
Use appropriate {language} terminology for technical analysis concepts."""

        return header

    def add_custom_instruction(self, instruction: str) -> None:
        self.custom_instructions.append(instruction)

    def _build_market_overview_section(self) -> str:
        """Create a well-formatted market overview section that's easier for models to parse"""
        if not hasattr(self.context, 'market_overview') or not self.context.market_overview:
            return ""
            
        overview = self.context.market_overview
        sections = []
        
        # Add header
        sections.append("## MARKET OVERVIEW DATA\n")
        sections.append("The following market data should be incorporated into your analysis:\n")
        
        # Add different overview sections
        sections.extend(self._build_top_coins_section(overview))
        sections.extend(self._build_global_metrics_section(overview))
        sections.extend(self._build_dominance_section(overview))
        sections.extend(self._build_market_stats_section(overview))
        
        # Add closing note
        sections.append("\n**Note:** When formulating your analysis, explicitly incorporate these market metrics to provide context on how the analyzed asset relates to broader market conditions.\n")
        
        return "\n".join(sections)

    def _build_top_coins_section(self, overview: Dict[str, Any]) -> List[str]:
        """Build top cryptocurrencies performance section."""
        if "top_coins" not in overview:
            return []
            
        sections = [
            "### Top Cryptocurrencies Performance:\n",
            "| Coin | Price | 24h Change | 24h Volume |",
            "|------|-------|------------|------------|"
        ]
        
        for coin, data in overview["top_coins"].items():
            price = f"${data.get('price', 0):,.2f}"
            change = f"{data.get('change24h', 0):.2f}%"
            volume = f"{data.get('volume24h', 0):,.2f}"
            sections.append(f"| {coin} | {price} | {change} | {volume} |")
            
        sections.append("")  # Empty line after table
        return sections

    def _build_global_metrics_section(self, overview: Dict[str, Any]) -> List[str]:
        """Build global market metrics section."""
        sections = ["### Global Market Metrics:\n"]
        
        # Market cap
        if "market_cap" in overview:
            mcap = overview["market_cap"]
            total_mcap = f"${mcap.get('total_usd', 0):,.2f}" if "total_usd" in mcap else "N/A"
            mcap_change = f"{mcap.get('change_24h', 0):.2f}%" if "change_24h" in mcap else "N/A"
            sections.append(f"- Total Market Cap: {total_mcap} ({mcap_change} 24h change)")
            
        # Volume
        if "volume" in overview and "total_usd" in overview["volume"]:
            volume = f"${overview['volume']['total_usd']:,.2f}"
            sections.append(f"- 24h Trading Volume: {volume}")
            
        return sections

    def _build_dominance_section(self, overview: Dict[str, Any]) -> List[str]:
        """Build market dominance section."""
        if "dominance" not in overview:
            return []
            
        sections = ["\n### Market Dominance:\n"]
        
        for coin, value in overview["dominance"].items():
            if isinstance(value, (int, float)):
                sections.append(f"- {coin.upper()}: {value:.2f}%")
            else:
                sections.append(f"- {coin.upper()}: {value}%")
                
        return sections

    def _build_market_stats_section(self, overview: Dict[str, Any]) -> List[str]:
        """Build general market statistics section."""
        if "stats" not in overview:
            return []
            
        stats = overview["stats"]
        active_coins = stats.get("active_coins", "N/A")
        active_markets = stats.get("active_markets", "N/A")
        
        return [
            f"\n- Active Cryptocurrencies: {active_coins}",
            f"- Active Markets: {active_markets}"
        ]

    def _build_trading_context(self) -> str:
        # Get the current time to understand candle formation
        current_time = datetime.now()
        
        # Create candle status message for hourly timeframes
        candle_status = ""
        if self.timeframe == "1h" or self.timeframe == "1H":
            minutes_into_hour = current_time.minute
            candle_progress = (minutes_into_hour / 60) * 100
            candle_status = f"\n- Current Candle: {minutes_into_hour} minutes into formation ({candle_progress:.1f}% complete)"
            candle_status += f"\n- Analysis Note: Technical indicators calculated using only completed candles"
        
        trading_context = f"""
        TRADING CONTEXT:
        - Symbol: {self.context.symbol if hasattr(self.context, 'symbol') else 'BTC/USDT'}
        - Current Day: {current_time.strftime("%A")}
        - Current Price: {self.context.current_price}
        - Analysis Time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}{candle_status}
        - Primary Timeframe: {self.timeframe}
        - Analysis Includes: 1H, 1D, 7D, 30D, and 365D timeframes"""
        
        return trading_context

    def _build_sentiment_section(self) -> str:
        if not self.context.sentiment:
            return ""
        
        historical_data = self.context.sentiment.get('historical', [])
        
        sentiment_section = f"""
        MARKET SENTIMENT:
        - Current Fear & Greed Index: {self.context.sentiment.get('fear_greed_index', 'N/A')}
        - Classification: {self.context.sentiment.get('value_classification', 'N/A')}"""
        
        if historical_data:
            sentiment_section += "\n\n    Historical Fear & Greed (Last 7 days):"
            for day in historical_data:
                date_str = day['timestamp'].strftime('%Y-%m-%d') if isinstance(day['timestamp'], datetime) else day['timestamp']
                sentiment_section += f"\n    - {date_str}: {day['value']} ({day['value_classification']})"
        
        return sentiment_section

    @staticmethod
    def _build_response_template() -> str:
        response_template = '''RESPONSE FORMAT:
        Please structure your response in JSON format as follows:
        ```json
        {
            "analysis": {
                "summary": "Concise overview of the current market situation",
                "observed_trend": "BULLISH|BEARISH|NEUTRAL", // Justify this based on indicators/patterns
                "trend_strength": 0-100, // Based on ADX or similar
                "timeframes": {
                    "short_term": "BULLISH|BEARISH|NEUTRAL",
                    "medium_term": "BULLISH|BEARISH|NEUTRAL",
                    "long_term": "BULLISH|BEARISH|NEUTRAL"
                },
                "key_levels": {
                    "support": [level1, level2],
                    "resistance": [level1, level2]
                },
                "price_scenarios": {
                    "bullish_scenario": number, // Potential target/resistance if trend turns bullish
                    "bearish_scenario": number // Potential target/support if trend continues bearish
                },
                "confidence_score": 0-100, // Overall confidence in the analysis
                "technical_bias": "BULLISH|BEARISH|NEUTRAL", // Justify this based on indicator confluence
                "risk_ratio": number, // Estimated risk/reward based on scenarios/levels
                "market_structure": "BULLISH|BEARISH|NEUTRAL", // Based on price action patterns (higher highs/lows etc.)
                "news_summary": "Brief summary of relevant recent news and their potential market impact"
            }
        }
        ```        
        After the JSON block, include a detailed human-readable analysis. 
        **IMPORTANT: Format this detailed analysis using Markdown syntax.** Use headings (`##`), bold (`**text**`), italics (`*text*`), bullet points (`-` or `*`), and numbered lists where appropriate to enhance readability. 
        **Quantify observations where possible (e.g., "Price is X% below the 50-period MA", "RSI dropped Y points").**
        
        **IMPORTANT: Begin your analysis with a clear disclaimer that this is educational content only and not financial advice.**
        
        Organize the Markdown analysis into these sections:
        
        1. Disclaimer (emphasize this is for educational purposes only, not financial advice)
        2. Technical Analysis Overview (objective description of what the indicators show, quantified)
        3. Multi-Timeframe Assessment (short, medium, long-term patterns, quantified changes)
        4. Key Technical Levels (support/resistance identified by technical analysis, potentially with % distance from current price)
        5. News Summary (summarize relevant recent news and their potential impact on the asset)
        6. Potential Catalysts (Summarize factors like news, events, strong technical signals that could drive future price movement)
        7. Educational Context (explain technical concepts related to the current market conditions)
        8. Historical Patterns (similar technical setups in the past and what they typically indicate)
        9. Risk Considerations (discuss technical factors that may invalidate the analysis)
        10. Market Context (discuss how the asset relates to the overall market conditions using the provided Market Overview data)
        
        End with another reminder that users must do their own research and that this analysis is purely educational.
        '''
        
        return response_template

    def _build_market_data(self) -> str:
        """Build the market data section of the prompt (Optional: Keep summary, remove raw data)"""
        if self.context.ohlcv_candles is None or self.context.ohlcv_candles.size == 0:
            return "MARKET DATA:\nNo OHLCV data available"

        if self.context.ohlcv_candles.shape[0] < 24:
            return "MARKET DATA:\nInsufficient historical data (less than 25 candles)"

        available_candles = self.context.ohlcv_candles.shape[0]
        data = "MARKET DATA:\n" # Keep header or remove if desired

        # Keep multi-timeframe price summary if desired
        if available_candles >= 100:
            last_close = float(self.context.ohlcv_candles[-1, 4])
            periods = {
                "4h": 4,
                "12h": 12,
                "24h": 24,
                "3d": 72,
                "7d": 168
            }

            data += "\nMulti-Timeframe Price Summary (Based on 1h candles):\n" # Clarify source
            for period_name, candle_count in periods.items():
                if candle_count < available_candles:
                    period_start = float(self.context.ohlcv_candles[-candle_count, 4])
                    change_pct = ((last_close / period_start) - 1) * 100
                    high = max([float(candle[2]) for candle in self.context.ohlcv_candles[-candle_count:]])
                    low = min([float(candle[3]) for candle in self.context.ohlcv_candles[-candle_count:]])
                    
                    # Format very small numbers using the imported fmt function
                    high_formatted = fmt(high)
                    low_formatted = fmt(low)
                    
                    data += f"{period_name}: {change_pct:.2f}% change | High: {high_formatted} | Low: {low_formatted}\n"

        return data if data != "MARKET DATA:\n" else "" # Return empty if nothing was added

    def _build_technical_analysis(self) -> str:
        """Build technical analysis section from indicator data
        
        Args:
            context: AnalysisContext containing technical data
            
        Returns:
            str: Formatted technical analysis section
        """
        if not self.context.technical_data:
            return "TECHNICAL ANALYSIS:\nNo technical data available."

        td = self.context.technical_data
        patterns_section = self.indicator_calculator.extract_key_patterns(self.context)
        ichimoku_section = self._ta_ichimoku_section(td)
        advanced_indicators_section = self._ta_advanced_indicators_section(td)
        key_levels_section = self._ta_key_levels_section(td)
        pattern_info = self._ta_recent_patterns()
        cmf_interpretation = self._ta_cmf_interpretation(td)

        def fmt_ta(key, precision=8, default='N/A'):
            val = self.indicator_calculator.get_indicator_value(td, key)
            if isinstance(val, (int, float)) and not np.isnan(val):
                return fmt(val, precision)
            return default

        technical_analysis = f"""\nTECHNICAL ANALYSIS ({self.timeframe}):\n\n## Price Action:\n- Current Price: {fmt(self.context.current_price) if hasattr(self.context, 'current_price') else 0.0}\n- Rolling VWAP (14): {fmt_ta('vwap', 8)}\n- TWAP (14): {fmt_ta('twap', 8)}\n\n## Momentum Indicators:\n- RSI(14): {fmt_ta('rsi', 1)} [<{self.INDICATOR_THRESHOLDS['rsi']['oversold']}=Oversold, {self.INDICATOR_THRESHOLDS['rsi']['oversold']}-{self.INDICATOR_THRESHOLDS['rsi']['overbought']}=Neutral, >{self.INDICATOR_THRESHOLDS['rsi']['overbought']}=Overbought]\n- MACD (12,26,9): [Pattern detector provides crossover analysis]\n  * Line: {fmt_ta('macd_line', 8)}\n  * Signal: {fmt_ta('macd_signal', 8)}\n  * Histogram: {fmt_ta('macd_hist', 8)}\n- Stochastic %K(5,3,3): {fmt_ta('stoch_k', 1)} [<{self.INDICATOR_THRESHOLDS['stoch_k']['oversold']}=Oversold, >{self.INDICATOR_THRESHOLDS['stoch_k']['overbought']}=Overbought]\n- Stochastic %D(5,3,3): {fmt_ta('stoch_d', 1)} [<{self.INDICATOR_THRESHOLDS['stoch_d']['oversold']}=Oversold, >{self.INDICATOR_THRESHOLDS['stoch_d']['overbought']}=Overbought]\n- Williams %R(14): {fmt_ta('williams_r', 1)} [<{self.INDICATOR_THRESHOLDS['williams_r']['oversold']}=Oversold, >{self.INDICATOR_THRESHOLDS['williams_r']['overbought']}=Overbought]\n\n## Trend Indicators:\n- ADX(14): {fmt_ta('adx', 1)} [0-{self.INDICATOR_THRESHOLDS['adx']['weak']}: Weak/No Trend, {self.INDICATOR_THRESHOLDS['adx']['weak']}-{self.INDICATOR_THRESHOLDS['adx']['strong']}: Strong, {self.INDICATOR_THRESHOLDS['adx']['strong']}-{self.INDICATOR_THRESHOLDS['adx']['very_strong']}: Very Strong, >{self.INDICATOR_THRESHOLDS['adx']['very_strong']}: Extremely Strong]\n- +DI(14): {fmt_ta('plus_di', 1)} [Pattern detector analyzes DI crossovers]\n- -DI(14): {fmt_ta('minus_di', 1)}\n- Supertrend(7,3.0) Direction: {'Bullish' if td.get('supertrend_direction', 0) > 0 else 'Bearish' if td.get('supertrend_direction', 0) < 0 else 'Neutral'}\n\n## Volatility Analysis:\n- ATR(14): {fmt_ta('atr', 8)}\n- Bollinger Band Width (%): {self.indicator_calculator.calculate_bb_width(td):.2f}% [<{self.INDICATOR_THRESHOLDS['bb_width']['tight']}%=Tight, >{self.INDICATOR_THRESHOLDS['bb_width']['wide']}%=Wide]\n\n## Volume Analysis:\n- MFI(14): {fmt_ta('mfi', 1)} [<{self.INDICATOR_THRESHOLDS['mfi']['oversold']}=Oversold, >{self.INDICATOR_THRESHOLDS['mfi']['overbought']}=Overbought]\n- On Balance Volume (OBV): {fmt_ta('obv', 0)}\n- Chaikin MF(20): {fmt_ta('cmf', 4)}{cmf_interpretation}\n- Force Index(13): {fmt_ta('force_index', 0)}\n\n## Statistical Metrics:\n- Hurst Exponent(20): {fmt_ta('hurst', 2)} [~0.5: Random Walk, >0.5: Trending, <0.5: Mean Reverting]\n- Z-Score(30): {fmt_ta('zscore', 2)} [Distance from mean in std deviations]\n- Kurtosis(30): {fmt_ta('kurtosis', 2)} [Tail risk indicator; >3 suggests fatter tails]\n{key_levels_section}\n{ichimoku_section}\n{advanced_indicators_section}\n{patterns_section}{pattern_info}"""

        return technical_analysis.strip()

    # ---------- Helper sub-builders (extracted to reduce complexity) ----------
    def _ta_ichimoku_section(self, td: dict) -> str:
        required = {"ichimoku_conversion", "ichimoku_base", "ichimoku_span_a", "ichimoku_span_b"}
        if not (required.issubset(td.keys()) and all(td.get(k) is not None for k in required)):
            return "\n## Ichimoku Cloud Analysis:\n- Data unavailable or insufficient history."
        try:
            tenkan = self.indicator_calculator.get_indicator_value(td, "ichimoku_conversion")
            kijun = self.indicator_calculator.get_indicator_value(td, "ichimoku_base")
            span_a = self.indicator_calculator.get_indicator_value(td, "ichimoku_span_a")
            span_b = self.indicator_calculator.get_indicator_value(td, "ichimoku_span_b")
            cloud_status = "N/A"
            if isinstance(span_a, (int, float)) and isinstance(span_b, (int, float)):
                cloud_status = ("Bullish (Span A above Span B)" if span_a > span_b else
                                "Bearish (Span B above Span A)" if span_b > span_a else
                                "Neutral (Spans Equal)")
            return (f"\n## Ichimoku Cloud Analysis:\n" \
                    f"- Conversion Line (Tenkan-sen): {fmt(tenkan) if isinstance(tenkan, (int, float)) else 'N/A'}\n" \
                    f"- Base Line (Kijun-sen): {fmt(kijun) if isinstance(kijun, (int, float)) else 'N/A'}\n" \
                    f"- Leading Span A (Senkou A): {fmt(span_a) if isinstance(span_a, (int, float)) else 'N/A'}\n" \
                    f"- Leading Span B (Senkou B): {fmt(span_b) if isinstance(span_b, (int, float)) else 'N/A'}\n" \
                    f"- Cloud Status: {cloud_status}\n")
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Could not format Ichimoku values: {e}")
            return "\n## Ichimoku Cloud Analysis:\n- Data unavailable or processing error."

    def _ta_advanced_indicators_section(self, td: dict) -> str:
        try:
            lines = []
            
            # Process vortex indicator
            lines.extend(self._format_vortex_indicator(td))
            
            # Process basic momentum indicators
            lines.extend(self._format_momentum_indicators(td))
            
            # Process oscillators
            lines.extend(self._format_oscillator_indicators(td))
            
            # Process chandelier exit
            lines.extend(self._format_chandelier_exit(td))
            
            return ("\n\n## Advanced Technical Indicators:\n" + "\n".join(lines)) if lines else ""
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Could not extract/format advanced indicator values: {e}")
            return "\n\n## Advanced Technical Indicators:\n- Data unavailable or processing error."
    
    def _format_vortex_indicator(self, td: dict) -> list[str]:
        """Format vortex indicator data."""
        vortex = self.indicator_calculator.get_indicator_values(td, "vortex_indicator", 2)
        if not vortex:
            return []
        
        vi_plus, vi_minus = vortex
        if self._is_valid_value(vi_plus) and self._is_valid_value(vi_minus):
            bias = "bullish" if vi_plus > vi_minus else "bearish" if vi_minus > vi_plus else "neutral"
            return [f"- Vortex Indicator: VI+ {self._fmt_val(vi_plus)}, VI- {self._fmt_val(vi_minus)} ({bias} bias)"]
        return []
    
    def _format_momentum_indicators(self, td: dict) -> list[str]:
        """Format basic momentum indicators."""
        lines = []
        momentum_indicators = [
            ("trix", "TRIX(18)", False),
            ("tsi", "TSI(25,13)", False),
            ("ppo", "PPO(12,26)", True),  # True means add % suffix
            ("coppock", "Coppock Curve", False),
            ("kst", "KST", False)
        ]
        
        for key, label, add_percent in momentum_indicators:
            lines.extend(self._format_single_momentum_indicator(td, key, label, add_percent))
        
        return lines
    
    def _format_single_momentum_indicator(self, td: dict, key: str, label: str, add_percent: bool) -> list[str]:
        """Format a single momentum indicator."""
        value = self.indicator_calculator.get_indicator_value(td, key)
        if not self._is_valid_value(value):
            return []
        
        bias = self._get_momentum_bias(value)
        suffix = '%' if add_percent else ''
        return [f"- {label}: {self._fmt_val(value)}{suffix} ({bias})"]
    
    def _format_oscillator_indicators(self, td: dict) -> list[str]:
        """Format oscillator indicators (RMI, Ultimate Oscillator)."""
        lines = []
        
        # RMI indicator
        rmi_value = self.indicator_calculator.get_indicator_value(td, "rmi")
        if self._is_valid_value(rmi_value):
            condition = self._get_oscillator_condition(rmi_value)
            lines.append(f"- RMI(14,5): {self._fmt_val(rmi_value)} ({condition})")
        
        # Ultimate Oscillator
        uo_value = self.indicator_calculator.get_indicator_value(td, "uo")
        if self._is_valid_value(uo_value):
            condition = self._get_oscillator_condition(uo_value)
            lines.append(f"- Ultimate Oscillator: {self._fmt_val(uo_value)} ({condition})")
        
        return lines
    
    def _format_chandelier_exit(self, td: dict) -> list[str]:
        """Format chandelier exit indicator."""
        long_exit = self.indicator_calculator.get_indicator_value(td, "chandelier_long")
        short_exit = self.indicator_calculator.get_indicator_value(td, "chandelier_short")
        
        if (not self._is_valid_value(long_exit) or 
            not self._is_valid_value(short_exit) or 
            not hasattr(self.context, 'current_price') or 
            self.context.current_price is None):
            return []
        
        current_price = float(self.context.current_price)
        message = self._get_chandelier_message(current_price, long_exit, short_exit)
        return [f"- Chandelier Exit: {message}"]
    
    def _get_chandelier_message(self, price: float, long_exit: float, short_exit: float) -> str:
        """Generate chandelier exit message based on price position."""
        if price > long_exit:
            return f"Price ({fmt(price)}) above long exit ({fmt(long_exit)}) - bullish"
        elif price < short_exit:
            return f"Price ({fmt(price)}) below short exit ({fmt(short_exit)}) - bearish"
        else:
            return f"Price ({fmt(price)}) between exit levels ({fmt(short_exit)} - {fmt(long_exit)}) - neutral"
    
    def _is_valid_value(self, value) -> bool:
        """Check if a value is valid for formatting."""
        return isinstance(value, (int, float)) and not np.isnan(value)
    
    def _fmt_val(self, value, precision=8) -> str:
        """Format a value safely."""
        return fmt(value, precision) if self._is_valid_value(value) else 'N/A'
    
    def _get_momentum_bias(self, value) -> str:
        """Get bias string for momentum indicators."""
        if not isinstance(value, (int, float)):
            return "neutral"
        return "bullish" if value > 0 else "bearish" if value < 0 else "neutral"
    
    def _get_oscillator_condition(self, value) -> str:
        """Get condition string for oscillator indicators."""
        if value > 70:
            return "overbought"
        elif value < 30:
            return "oversold"
        else:
            return "neutral"

    def _ta_key_levels_section(self, td: dict) -> str:
        """Build key levels section with support and resistance data."""
        lines = ["## Key Levels:"]
        
        # Add basic support and resistance
        self._add_basic_levels(lines, td)
        
        # Add Bollinger Bands
        self._add_bollinger_levels(lines, td)
        
        # Add Supertrend level
        self._add_supertrend_level(lines, td)
        
        # Add advanced support/resistance
        self._add_advanced_levels(lines, td)
        
        return "\n" + "\n".join(lines) if len(lines) > 1 else ""
    
    def _add_basic_levels(self, lines: list[str], td: dict) -> None:
        """Add basic support and resistance levels."""
        basic_support = self.indicator_calculator.get_indicator_value(td, "basic_support")
        basic_resistance = self.indicator_calculator.get_indicator_value(td, "basic_resistance")
        
        if basic_support != 'N/A':
            lines.append(f"- Basic Support (Rolling Min): {fmt(basic_support)}")
        if basic_resistance != 'N/A':
            lines.append(f"- Basic Resistance (Rolling Max): {fmt(basic_resistance)}")
    
    def _add_bollinger_levels(self, lines: list[str], td: dict) -> None:
        """Add Bollinger Band levels."""
        bollinger_levels = [
            ("bb_lower", "Bollinger Lower"),
            ("bb_middle", "Bollinger Middle"),
            ("bb_upper", "Bollinger Upper")
        ]
        
        for key, label in bollinger_levels:
            value = self.indicator_calculator.get_indicator_value(td, key)
            if value != 'N/A':
                lines.append(f"- {label}: {fmt(value)}")
    
    def _add_supertrend_level(self, lines: list[str], td: dict) -> None:
        """Add Supertrend level and direction."""
        st_val = self.indicator_calculator.get_indicator_value(td, "supertrend")
        if st_val == 'N/A':
            return
            
        st_dir = td.get('supertrend_direction')
        dir_str = self._get_supertrend_direction_string(st_dir)
        lines.append(f"- Supertrend Level: {fmt(st_val)} {dir_str}")
    
    def _get_supertrend_direction_string(self, direction) -> str:
        """Get formatted direction string for Supertrend."""
        if direction is None:
            return "(Direction Unknown)"
        elif direction == 1:
            return "(Currently Bullish)"
        elif direction == -1:
            return "(Currently Bearish)"
        else:
            return ""
    
    def _add_advanced_levels(self, lines: list[str], td: dict) -> None:
        """Add advanced support and resistance levels."""
        adv_levels = self.indicator_calculator.get_indicator_values(td, "support_resistance", 2)
        if len(adv_levels) != 2:
            return
            
        current_price = getattr(self.context, 'current_price', 0) or 0
        if not current_price:
            return
            
        support_level, resistance_level = adv_levels
        
        if support_level != 'N/A':
            support_distance = ((support_level - current_price) / current_price) * 100
            lines.append(f"- Advanced Support (Vol-based): {fmt(support_level)} ({support_distance:.2f}% below price)")
            
        if resistance_level != 'N/A':
            resistance_distance = ((resistance_level - current_price) / current_price) * 100
            lines.append(f"- Advanced Resistance (Vol-based): {fmt(resistance_level)} ({resistance_distance:.2f}% above price)")

    def _ta_recent_patterns(self) -> str:
        try:
            if hasattr(self.context, 'ohlcv_candles') and hasattr(self.context, 'technical_data'):
                ohlcv = self.context.ohlcv_candles
                history = self.context.technical_data.get('history', {})
                patterns = self.indicator_calculator.get_all_patterns(ohlcv, history)
                if patterns:
                    desc = [f"- {p.get('description', 'Unknown pattern')}" for p in patterns[-5:]]
                    return "\n\n## Recent Patterns Detected:\n" + "\n".join(desc)
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Could not retrieve pattern information: {e}")
        return ""

    def _ta_cmf_interpretation(self, td: dict) -> str:
        cmf_val = self.indicator_calculator.get_indicator_value(td, 'cmf')
        if isinstance(cmf_val, (int, float)):
            if cmf_val > 0:
                return " (Positive suggests buying pressure)"
            if cmf_val < 0:
                return " (Negative suggests selling pressure)"
        return ""

    def _build_market_period_metrics(self) -> str:
        """Build market period metrics section using the indicator calculator"""
        if not hasattr(self.context, 'market_metrics') or not self.context.market_metrics:
            return ""
        
        return self.indicator_calculator.format_market_period_metrics(self.context.market_metrics)

    def _build_long_term_analysis(self) -> str:
        """Build long-term analysis section from daily historical data using the indicator calculator"""
        if not hasattr(self.context, 'long_term_data') or not self.context.long_term_data:
            return ""
        
        current_price = getattr(self.context, 'current_price', None)
        return self.indicator_calculator.format_long_term_analysis(self.context.long_term_data, current_price)

    def _build_analysis_steps(self) -> str:
        # Check if we have advanced support/resistance detected (not the basic ones)
        advanced_support_resistance_detected = False
        
        # Check if context and technical_data are available
        if hasattr(self, 'context') and hasattr(self.context, 'technical_data'):
            td = self.context.technical_data
            # Check specifically for the advanced support_resistance (not basic_support/basic_resistance)
            if 'support_resistance' in td:
                sr = td['support_resistance']
                if len(sr) == 2 and not (np.isnan(sr[0]) and np.isnan(sr[1])):
                    advanced_support_resistance_detected = True
        
        # Get the symbol being analyzed to customize market comparisons
        analyzed_symbol = self.context.symbol if hasattr(self.context, 'symbol') else "BTC/USDT"
        analyzed_base = analyzed_symbol.split('/')[0] if '/' in analyzed_symbol else analyzed_symbol
        
        analysis_steps = """
        ANALYSIS STEPS:
        Follow these steps to generate the analysis. In the final JSON response, briefly justify the 'observed_trend' and 'technical_bias' fields by referencing specific indicators or patterns from the provided data (e.g., "Bearish due to MACD crossover and price below Supertrend").

        1. Multi-Timeframe Assessment:
           - Analyze short-term price action (1-4h) for immediate trend
           - Review medium-term trends (1-7d) for broader context
           - Consider long-term trends (30d+) for market cycle positioning
           - Analyze 365d historical data and SMA positions for macro trend
           - Compare price action across different timeframes for confirmation/divergence
        
        2. Technical Indicator Analysis:
           - Evaluate core momentum indicators (RSI, MACD, Stochastic)
           - Observe trend strength using ADX, DI readings
           - Check volatility levels with ATR and Bollinger Bands
           - Analyze volume indicators (MFI, OBV, Force Index) for context
           - Consider SMA relationships (e.g., 50 vs 200) for trend context
           - Assess advanced indicators (TSI, Vortex, PFE, RMI, Ultimate Oscillator)
           
        3. Key Pattern Recognition:
           - Identify chart patterns (wedges, triangles, H&S, double tops/bottoms)
           - Detect divergences between price and momentum indicators
           - Look for candlestick reversal patterns
           - Note potential harmonic patterns and Fibonacci relationships
           - Identify overbought/oversold conditions across indicators
        
        4. Support/Resistance Validation:
           - Map key price levels from all timeframes
           - Identify historical price reaction zones
           - Determine areas with multiple technical confluences
           - Compare current price with historical significant levels
           - Basic Support/Resistance Indicator: Rolling min/max of high/low over specified period
           - Volume profile analysis: Note price levels with high historical volume
        
        5. Market Context Integration:
           - Reference the provided Market Overview data in your analysis
           - Compare the asset's performance with the broader market (market cap %, dominance trends)"""
        
        # Customize market comparison instructions based on the asset being analyzed
        if "BTC" not in analyzed_base:
            analysis_steps += "\n           - Compare the asset's performance relative to BTC"
        
        if "ETH" not in analyzed_base:
            analysis_steps += "\n           - Compare the asset's performance relative to ETH if relevant"
        
        # Continue with the rest of the market context integration steps
        analysis_steps += """
           - Consider market sentiment metrics including Fear & Greed Index
           - Analyze if the asset is aligned with or diverging from general market trends
           - Note relevant market events and their historical impact
           - Consider market structures observed in similar historical contexts
        
        6. News Analysis:
           - Summarize relevant recent news articles about the asset
           - Identify potential market-moving events or announcements
           - Evaluate sentiment from news coverage
           - Connect news events to recent price action when applicable
           - Note institutional actions or corporate developments mentioned in news
           - Identify any regulatory news that might impact the asset
        
        7. Statistical Analysis:
           - Evaluate statistical indicators like Z-Score and Kurtosis
           - Consider Hurst Exponent for trending vs mean-reverting behavior
           - Note abnormal distribution patterns in price/volume
           - Assess volatility cycles and potential expansion/contraction phases
        
        8. Educational Information:
           - Explain possible scenarios based on technical analysis concepts
           - Describe what traders typically watch for in similar situations
           - Present educational information about risk management concepts
           - Focus on explaining the "what" and "why" of technical patterns
           - Offer context about typical behavior of similar assets in comparable market conditions
        
        TECHNICAL INDICATORS NOTE:
           - Current candle is incomplete and not included in indicator calculations
           - Technical indicators calculated using only completed candles"""
        
        if advanced_support_resistance_detected:
            analysis_steps += """
        
        CUSTOM INDICATORS REFERENCE:
        
        Advanced Support/Resistance:
           - Volume-weighted pivot points with strength thresholds
           - Creates pivot points using (H+L+C)/3 formula
           - Calculates S1 = (2*PP)-H and R1 = (2*PP)-L levels
           - Tracks consecutive touches to measure level strength
           - Filters for above-average volume at reaction points
           - Returns ONLY strong support and resistance levels that meet all criteria 
           - Uses price momentum and volume confirmations"""

        return analysis_steps
