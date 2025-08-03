import numpy as np
from datetime import datetime
from typing import Any, Dict, Optional, TypedDict

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
        
        # Format the section header to stand out
        section = "## MARKET OVERVIEW DATA\n\n"
        section += "The following market data should be incorporated into your analysis:\n\n"
        
        # Add formatted top coins summary
        if "top_coins" in overview:
            section += "### Top Cryptocurrencies Performance:\n\n"
            section += "| Coin | Price | 24h Change | 24h Volume |\n"
            section += "|------|-------|------------|------------|\n"
            
            for coin, data in overview["top_coins"].items():
                price = f"${data.get('price', 0):,.2f}"
                change = f"{data.get('change24h', 0):.2f}%"
                volume = f"{data.get('volume24h', 0):,.2f}"
                section += f"| {coin} | {price} | {change} | {volume} |\n"
            section += "\n"
            
        # Add market metrics summary
        section += "### Global Market Metrics:\n\n"
        
        if "market_cap" in overview:
            mcap = overview["market_cap"]
            total_mcap = f"${mcap.get('total_usd', 0):,.2f}" if "total_usd" in mcap else "N/A"
            mcap_change = f"{mcap.get('change_24h', 0):.2f}%" if "change_24h" in mcap else "N/A"
            section += f"- Total Market Cap: {total_mcap} ({mcap_change} 24h change)\n"
            
        if "volume" in overview and "total_usd" in overview["volume"]:
            volume = f"${overview['volume']['total_usd']:,.2f}"
            section += f"- 24h Trading Volume: {volume}\n"
            
        # Add dominance data - FIX: Loop through the dominance dictionary, not the entire overview
        if "dominance" in overview:
            section += "\n### Market Dominance:\n\n"
            for coin, value in overview["dominance"].items():  # Fixed: use overview["dominance"] instead of overview
                # Ensure value is numeric before formatting
                if isinstance(value, (int, float)):
                    section += f"- {coin.upper()}: {value:.2f}%\n"
                else:
                    section += f"- {coin.upper()}: {value}%\n"
                
        # Add general market stats
        if "stats" in overview:
            active_coins = overview["stats"].get("active_coins", "N/A")
            active_markets = overview["stats"].get("active_markets", "N/A")
            section += f"\n- Active Cryptocurrencies: {active_coins}\n"
            section += f"- Active Markets: {active_markets}\n"
            
        section += "\n**Note:** When formulating your analysis, explicitly incorporate these market metrics to provide context on how the analyzed asset relates to broader market conditions.\n"
        
        return section

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
        
        # --- 2. Format Ichimoku ---
        ichimoku_section = ""
        required_ichi_keys = {"ichimoku_conversion", "ichimoku_base", "ichimoku_span_a", "ichimoku_span_b"}
        # Check if all keys exist and have non-None values before proceeding
        if required_ichi_keys.issubset(td.keys()) and all(td.get(k) is not None for k in required_ichi_keys):
            try:
                tenkan = self.indicator_calculator.get_indicator_value(td, "ichimoku_conversion")
                kijun = self.indicator_calculator.get_indicator_value(td, "ichimoku_base")
                span_a = self.indicator_calculator.get_indicator_value(td, "ichimoku_span_a")
                span_b = self.indicator_calculator.get_indicator_value(td, "ichimoku_span_b")

                cloud_status = "N/A"
                # Ensure values are numeric before comparison
                if isinstance(span_a, (int, float)) and isinstance(span_b, (int, float)):
                    if span_a > span_b:
                        cloud_status = "Bullish (Span A above Span B)"
                    elif span_b > span_a:
                        cloud_status = "Bearish (Span B above Span A)"
                    else:
                        cloud_status = "Neutral (Spans Equal)"

                # Format values for display
                tenkan_str = fmt(tenkan) if isinstance(tenkan, (int, float)) else "N/A"
                kijun_str = fmt(kijun) if isinstance(kijun, (int, float)) else "N/A"
                span_a_str = fmt(span_a) if isinstance(span_a, (int, float)) else "N/A"
                span_b_str = fmt(span_b) if isinstance(span_b, (int, float)) else "N/A"

                ichimoku_section = f"""
## Ichimoku Cloud Analysis:
- Conversion Line (Tenkan-sen): {tenkan_str}
- Base Line (Kijun-sen): {kijun_str}
- Leading Span A (Senkou A): {span_a_str}
- Leading Span B (Senkou B): {span_b_str}
- Cloud Status: {cloud_status}
"""
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Could not format Ichimoku values: {e}")
                ichimoku_section = "\n## Ichimoku Cloud Analysis:\n- Data unavailable or processing error."
        else:
             ichimoku_section = "\n## Ichimoku Cloud Analysis:\n- Data unavailable or insufficient history."

        # --- 3. Format Advanced Indicators ---
        advanced_indicators_section = ""
        try:
            advanced_indicators = []

            # Helper to format value or return N/A - uses imported fmt function
            def fmt_val(val, precision=8):
                if isinstance(val, (int, float)) and not np.isnan(val):
                    return fmt(val, precision)
                return "N/A"

            # Vortex Indicator
            vortex = self.indicator_calculator.get_indicator_values(td, "vortex_indicator", 2)
            if vortex:
                vi_plus, vi_minus = vortex
                trend_bias = "bullish" if vi_plus > vi_minus else "bearish" if vi_minus > vi_plus else "neutral"
                advanced_indicators.append(f"- Vortex Indicator: VI+ {fmt_val(vi_plus)}, VI- {fmt_val(vi_minus)} ({trend_bias} bias)")

            # TRIX
            trix_value = self.indicator_calculator.get_indicator_value(td, "trix")
            if trix_value != 'N/A':
                trix_bias = "bullish" if trix_value > 0 else "bearish" if trix_value < 0 else "neutral"
                advanced_indicators.append(f"- TRIX(18): {fmt_val(trix_value)} ({trix_bias})")

            # PFE
            pfe_value = self.indicator_calculator.get_indicator_value(td, "pfe")
            if pfe_value != 'N/A':
                pfe_signal = "strong trend" if abs(pfe_value) > 80 else "moderate trend" if abs(pfe_value) > 50 else "weak trend"
                advanced_indicators.append(f"- PFE(10): {fmt_val(pfe_value)} ({pfe_signal})")

            # TSI
            tsi_value = self.indicator_calculator.get_indicator_value(td, "tsi")
            if tsi_value != 'N/A':
                tsi_bias = "bullish" if tsi_value > 0 else "bearish" if tsi_value < 0 else "neutral"
                advanced_indicators.append(f"- TSI(25,13): {fmt_val(tsi_value)} ({tsi_bias})")

            # RMI
            rmi_value = self.indicator_calculator.get_indicator_value(td, "rmi")
            if rmi_value != 'N/A':
                rmi_condition = "overbought" if rmi_value > 70 else "oversold" if rmi_value < 30 else "neutral"
                advanced_indicators.append(f"- RMI(14,5): {fmt_val(rmi_value)} ({rmi_condition})")

            # PPO
            ppo_value = self.indicator_calculator.get_indicator_value(td, "ppo")
            if ppo_value != 'N/A':
                ppo_bias = "bullish" if ppo_value > 0 else "bearish" if ppo_value < 0 else "neutral"
                advanced_indicators.append(f"- PPO(12,26): {fmt_val(ppo_value)}% ({ppo_bias})")

            # Coppock Curve
            coppock_value = self.indicator_calculator.get_indicator_value(td, "coppock")
            if coppock_value != 'N/A':
                coppock_signal = "bullish" if coppock_value > 0 else "bearish" if coppock_value < 0 else "neutral"
                advanced_indicators.append(f"- Coppock Curve: {fmt_val(coppock_value)} ({coppock_signal})")

            # Ultimate Oscillator
            uo_value = self.indicator_calculator.get_indicator_value(td, "uo")
            if uo_value != 'N/A':
                uo_condition = "overbought" if uo_value > 70 else "oversold" if uo_value < 30 else "neutral"
                advanced_indicators.append(f"- Ultimate Oscillator: {fmt_val(uo_value)} ({uo_condition})")

            # KST
            kst_value = self.indicator_calculator.get_indicator_value(td, "kst")
            if kst_value != 'N/A':
                kst_bias = "bullish" if kst_value > 0 else "bearish" if kst_value < 0 else "neutral"
                advanced_indicators.append(f"- KST: {fmt_val(kst_value)} ({kst_bias})")

            # Chandelier Exit
            long_exit = self.indicator_calculator.get_indicator_value(td, "chandelier_long")
            short_exit = self.indicator_calculator.get_indicator_value(td, "chandelier_short")
            if long_exit != 'N/A' and short_exit != 'N/A' and hasattr(self.context, 'current_price') and self.context.current_price is not None:
                current_price = float(self.context.current_price)
                chandelier_signal = "neutral"
                if current_price > long_exit:
                    chandelier_signal = f"Price ({fmt(current_price)}) above long exit ({fmt(long_exit)}) - bullish"
                elif current_price < short_exit:
                    chandelier_signal = f"Price ({fmt(current_price)}) below short exit ({fmt(short_exit)}) - bearish"
                else:
                    chandelier_signal = f"Price ({fmt(current_price)}) between exit levels ({fmt(short_exit)} - {fmt(long_exit)}) - neutral"
                advanced_indicators.append(f"- Chandelier Exit: {chandelier_signal}")

            if advanced_indicators:
                advanced_indicators_section = "\n\n## Advanced Technical Indicators:\n" + "\n".join(advanced_indicators)
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Could not extract/format advanced indicator values: {e}")
            advanced_indicators_section = "\n\n## Advanced Technical Indicators:\n- Data unavailable or processing error."

        # --- 4. Build Main TA Section ---
        # Use helper for safe formatting with borrowed fmt function
        def fmt_ta(key, precision=8, default='N/A'):
             val = self.indicator_calculator.get_indicator_value(td, key)
             # Ensure val is numeric before formatting
             if isinstance(val, (int, float)) and not np.isnan(val):
                 return fmt(val, precision)
             return default

        # Build Key Levels Section dynamically
        key_levels_lines = ["## Key Levels:"]
        # Basic S/R (Rolling Min/Max)
        basic_s = self.indicator_calculator.get_indicator_value(td, "basic_support")
        basic_r = self.indicator_calculator.get_indicator_value(td, "basic_resistance")
        if basic_s != 'N/A': key_levels_lines.append(f"- Basic Support (Rolling Min): {fmt(basic_s)}")
        if basic_r != 'N/A': key_levels_lines.append(f"- Basic Resistance (Rolling Max): {fmt(basic_r)}")

        # Bollinger Bands
        bb_l = self.indicator_calculator.get_indicator_value(td, "bb_lower")
        bb_m = self.indicator_calculator.get_indicator_value(td, "bb_middle")
        bb_u = self.indicator_calculator.get_indicator_value(td, "bb_upper")
        if bb_l != 'N/A': key_levels_lines.append(f"- Bollinger Lower: {fmt(bb_l)}")
        if bb_m != 'N/A': key_levels_lines.append(f"- Bollinger Middle: {fmt(bb_m)}")
        if bb_u != 'N/A': key_levels_lines.append(f"- Bollinger Upper: {fmt(bb_u)}")

        # Supertrend
        st_val = self.indicator_calculator.get_indicator_value(td, "supertrend")
        st_dir = td.get("supertrend_direction", None)
        if st_val != 'N/A':
            st_dir_str = "(Direction Unknown)"
            if st_dir is not None:
                 st_dir_str = "(Currently Bullish)" if st_dir == 1 else "(Currently Bearish)" if st_dir == -1 else ""
            key_levels_lines.append(f"- Supertrend Level: {fmt(st_val)} {st_dir_str}")

        # Advanced S/R (Vol-based)
        adv_sr = self.indicator_calculator.get_indicator_values(td, "support_resistance", 2)
        if len(adv_sr) == 2:
            s_level, r_level = adv_sr
            current_price = self.context.current_price if hasattr(self.context, 'current_price') and self.context.current_price is not None else 0
            if s_level != 'N/A':
                support_distance = ((s_level - current_price) / current_price) * 100 if current_price != 0 else 0
                key_levels_lines.append(f"- Advanced Support (Vol-based): {fmt(s_level)} ({support_distance:.2f}% below price)")
            if r_level != 'N/A':
                resistance_distance = ((r_level - current_price) / current_price) * 100 if current_price != 0 else 0
                key_levels_lines.append(f"- Advanced Resistance (Vol-based): {fmt(r_level)} ({resistance_distance:.2f}% above price)")

        key_levels_section = "\n" + "\n".join(key_levels_lines) if len(key_levels_lines) > 1 else ""        # Get pattern information from PatternRecognizer
        pattern_info = ""
        try:
            # Get patterns using the centralized PatternRecognizer
            if hasattr(self.context, 'ohlcv_candles') and hasattr(self.context, 'technical_data'):
                ohlcv_data = self.context.ohlcv_candles
                technical_history = self.context.technical_data.get('history', {})
                patterns = self.indicator_calculator.get_all_patterns(ohlcv_data, technical_history)
                
                if patterns:
                    pattern_descriptions = []
                    for pattern in patterns[-5:]:  # Show last 5 patterns
                        description = pattern.get('description', 'Unknown pattern')
                        pattern_descriptions.append(f"- {description}")
                    pattern_info = "\n\n## Recent Patterns Detected:\n" + "\n".join(pattern_descriptions)
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Could not retrieve pattern information: {e}")

        # --- Add minimal interpretations for critical indicators only ---
        cmf_val = self.indicator_calculator.get_indicator_value(td, "cmf")
        cmf_interpretation = ""
        if isinstance(cmf_val, (int, float)):
            if cmf_val > 0:
                cmf_interpretation = " (Positive suggests buying pressure)"
            elif cmf_val < 0:
                cmf_interpretation = " (Negative suggests selling pressure)"

        technical_analysis = f"""
TECHNICAL ANALYSIS ({self.timeframe}):

## Price Action:
- Current Price: {fmt(self.context.current_price) if hasattr(self.context, 'current_price') else 0.0}
- Rolling VWAP (14): {fmt_ta("vwap", 8)}
- TWAP (14): {fmt_ta("twap", 8)}

## Momentum Indicators:
- RSI(14): {fmt_ta("rsi", 1)} [<{self.INDICATOR_THRESHOLDS['rsi']['oversold']}=Oversold, {self.INDICATOR_THRESHOLDS['rsi']['oversold']}-{self.INDICATOR_THRESHOLDS['rsi']['overbought']}=Neutral, >{self.INDICATOR_THRESHOLDS['rsi']['overbought']}=Overbought]
- MACD (12,26,9): [Pattern detector provides crossover analysis]
  * Line: {fmt_ta("macd_line", 8)}
  * Signal: {fmt_ta("macd_signal", 8)}
  * Histogram: {fmt_ta("macd_hist", 8)}
- Stochastic %K(5,3,3): {fmt_ta("stoch_k", 1)} [<{self.INDICATOR_THRESHOLDS['stoch_k']['oversold']}=Oversold, >{self.INDICATOR_THRESHOLDS['stoch_k']['overbought']}=Overbought]
- Stochastic %D(5,3,3): {fmt_ta("stoch_d", 1)} [<{self.INDICATOR_THRESHOLDS['stoch_d']['oversold']}=Oversold, >{self.INDICATOR_THRESHOLDS['stoch_d']['overbought']}=Overbought]
- Williams %R(14): {fmt_ta("williams_r", 1)} [<{self.INDICATOR_THRESHOLDS['williams_r']['oversold']}=Oversold, >{self.INDICATOR_THRESHOLDS['williams_r']['overbought']}=Overbought]

## Trend Indicators:
- ADX(14): {fmt_ta("adx", 1)} [0-{self.INDICATOR_THRESHOLDS['adx']['weak']}: Weak/No Trend, {self.INDICATOR_THRESHOLDS['adx']['weak']}-{self.INDICATOR_THRESHOLDS['adx']['strong']}: Strong, {self.INDICATOR_THRESHOLDS['adx']['strong']}-{self.INDICATOR_THRESHOLDS['adx']['very_strong']}: Very Strong, >{self.INDICATOR_THRESHOLDS['adx']['very_strong']}: Extremely Strong]
- +DI(14): {fmt_ta("plus_di", 1)} [Pattern detector analyzes DI crossovers]
- -DI(14): {fmt_ta("minus_di", 1)}
- Supertrend(7,3.0) Direction: {'Bullish' if td.get('supertrend_direction', 0) > 0 else 'Bearish' if td.get('supertrend_direction', 0) < 0 else 'Neutral'}

## Volatility Analysis:
- ATR(14): {fmt_ta("atr", 8)}
- Bollinger Band Width (%): {self.indicator_calculator.calculate_bb_width(td):.2f}% [<{self.INDICATOR_THRESHOLDS['bb_width']['tight']}%=Tight, >{self.INDICATOR_THRESHOLDS['bb_width']['wide']}%=Wide]

## Volume Analysis:
- MFI(14): {fmt_ta("mfi", 1)} [<{self.INDICATOR_THRESHOLDS['mfi']['oversold']}=Oversold, >{self.INDICATOR_THRESHOLDS['mfi']['overbought']}=Overbought]
- On Balance Volume (OBV): {fmt_ta("obv", 0)}
- Chaikin MF(20): {fmt_ta("cmf", 4)}{cmf_interpretation}
- Force Index(13): {fmt_ta("force_index", 0)}

## Statistical Metrics:
- Hurst Exponent(20): {fmt_ta("hurst", 2)} [~0.5: Random Walk, >0.5: Trending, <0.5: Mean Reverting]
- Z-Score(30): {fmt_ta("zscore", 2)} [Distance from mean in std deviations]
- Kurtosis(30): {fmt_ta("kurtosis", 2)} [Tail risk indicator; >3 suggests fatter tails]
{key_levels_section}
{ichimoku_section}
{advanced_indicators_section}
{patterns_section}{pattern_info}"""

        return technical_analysis.strip()

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
