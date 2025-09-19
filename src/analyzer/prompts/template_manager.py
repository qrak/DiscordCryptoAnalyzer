"""
Template management for prompt building system.
Handles system prompts, response templates, and analysis steps.
"""

from typing import Optional

from src.logger.logger import Logger


class TemplateManager:
    """Manages prompt templates, system prompts, and analysis steps."""
    
    def __init__(self, logger: Optional[Logger] = None):
        """Initialize the template manager.
        
        Args:
            logger: Optional logger instance for debugging
        """
        self.logger = logger
    
    def build_system_prompt(self, symbol: str, language: Optional[str] = None, has_chart_image: bool = False) -> str:
        """Build the system prompt for the AI model.
        
        Args:
            symbol: Trading symbol (e.g., "BTC/USDT")
            language: Optional language for response (defaults to English)
            has_chart_image: Whether a chart image is being provided for visual analysis
            
        Returns:
            str: Formatted system prompt
        """
        # Import here to avoid circular dependency
        from src.utils.loader import config

        language = language or config.DEFAULT_LANGUAGE

        # Refined header with more specific instructions
        header_base = f"""You are providing educational crypto market analysis of {symbol} on 1h timeframe along with multi-timeframe technical metrics and recent market data.
Focus on objective technical indicator readings and historical pattern recognition (e.g., identify potential chart patterns like triangles, head and shoulders, flags based on OHLCV data) for educational purposes only.
Present clear, data-driven observations with specific numeric values from the provided metrics. Prioritize recent price action and technical indicators over older news unless the news is highly significant.
Identify key price levels based solely on technical analysis concepts (Support, Resistance, Pivot Points, Fibonacci levels if applicable)."""

        # Add chart analysis instructions if image is provided
        if has_chart_image:
            header_base += """
IMPORTANT: You have been provided with a price chart IMAGE showing recent candlestick data. Use BOTH the numerical technical data AND the visual patterns you can observe in the chart image for your analysis. Pay special attention to visual chart patterns, candlestick formations, support/resistance levels that are clearly visible in the image, and price structure patterns you can see."""

        header_base += """
THIS IS EDUCATIONAL CONTENT ONLY. All analysis is for informational and educational purposes - NOT financial advice.
Always include disclaimers that this is not investment advice and users must do their own research."""

        if language == config.DEFAULT_LANGUAGE or language == "English":
            header = header_base
        else:
            header = f"""{header_base}
Write your entire response in {language} language. Only the JSON structure should remain in English, but all text content must be in {language}.
Use appropriate {language} terminology for technical analysis concepts."""

        return header
    
    def build_response_template(self, has_chart_analysis: bool = False) -> str:
        """Build the response template for structured output.
        
        Args:
            has_chart_analysis: Whether chart image analysis is available
            
        Returns:
            str: Formatted response template
        """
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
        **IMPORTANT: Format this detailed analysis using Markdown syntax.** Use headings (`##`), bold (`**text**`), italics (`*text*`), bullet points (`-` or `*`), numbered lists for enhanced readability. 
        **Quantify observations where possible (e.g., "Price is X% below the 50-period MA", "RSI dropped Y points").**
        
        **IMPORTANT: Begin your analysis with a clear disclaimer that this is educational content only and not financial advice.**
        
        Organize the Markdown analysis into these sections:
        
        - Disclaimer (emphasize this is for educational purposes only, not financial advice)
        - Technical Analysis Overview (objective description of what the indicators show, quantified)
        - Multi-Timeframe Assessment (describe short, medium, long-term patterns with quantified changes)
        - Technical Indicators Summary (describe indicators in organized paragraphs grouped by category)
        - Key Technical Levels (describe support and resistance levels in text format with specific prices and distances)
        - Market Context (describe asset performance vs broader market)
        - News Summary (summarize relevant recent news and their potential impact on the asset)'''
        
        # Add chart analysis sections only if chart images are available
        if has_chart_analysis:
            response_template += '''
        - Chart Pattern Analysis & Visual Integration (describe visual patterns observed in the price chart image and how they align with technical indicators)'''
        
        response_template += '''
        - Potential Catalysts (Summarize factors like news, events, strong technical signals that could drive future price movement)
        - Educational Context (explain technical concepts related to the current market conditions)
        - Historical Patterns (similar technical setups in the past and what they typically indicate)
        - Risk Considerations (discuss technical factors that may invalidate the analysis)
        
        End with another reminder that users must do their own research and that this analysis is purely educational.
        '''
        
        return response_template
    
    def build_analysis_steps(self, symbol: str, has_advanced_support_resistance: bool = False, has_chart_analysis: bool = False) -> str:
        """Build analysis steps instructions for the AI model.
        
        Args:
            symbol: Trading symbol being analyzed
            has_advanced_support_resistance: Whether advanced S/R indicators are detected
            has_chart_analysis: Whether chart image analysis is available (Google AI only)
            
        Returns:
            str: Formatted analysis steps
        """
        # Get the base asset for market comparisons
        analyzed_base = symbol.split('/')[0] if '/' in symbol else symbol
        
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
           - Assess volatility cycles and potential expansion/contraction phases"""
        
        # Add chart analysis steps only if chart images are available
        step_number = 8
        if has_chart_analysis:
            analysis_steps += f"""
        
            {step_number}. Chart Pattern Analysis & Visual Integration:
           - Analyze the provided price chart IMAGE showing the last 200 candles
           - Look at the VISUAL candlestick patterns in the image (doji, hammer, engulfing, shooting star, etc.)
           - Identify support and resistance levels that are VISUALLY apparent on the chart
           - Detect trend lines, channels, and price patterns that you can SEE in the image (triangles, flags, head & shoulders)
           - Note key breakout or breakdown levels and price structure patterns visible in the chart image
           - Combine the numerical technical indicators with the VISUAL chart patterns you observed in the image
           - Cross-reference chart patterns you can SEE with momentum and trend indicators from the data
           - Validate support/resistance levels using both price history data AND visual confirmation from the chart
           - Integrate candlestick analysis from the IMAGE with volume and momentum readings from the data
           - Look for convergences and divergences between technical data and the visual patterns in the chart image
           - Focus on what you can observe visually in the image, not just the numerical data"""
            step_number += 1
        
        analysis_steps += f"""
        
        {step_number}. Educational Information:
           - Explain possible scenarios based on technical analysis concepts
           - Describe what traders typically watch for in similar situations
           - Present educational information about risk management concepts
           - Focus on explaining the "what" and "why" of technical patterns
           - Offer context about typical behavior of similar assets in comparable market conditions
        
        TECHNICAL INDICATORS NOTE:
           - Current candle is incomplete and not included in indicator calculations
           - Technical indicators calculated using only completed candles"""
        
        if has_advanced_support_resistance:
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
