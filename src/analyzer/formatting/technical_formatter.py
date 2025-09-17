"""
Consolidated Technical Analysis Formatter.
Handles all technical analysis formatting in a single comprehensive class.
"""
from typing import Any, Dict, List, Optional
from src.logger.logger import Logger
from .format_utils import fmt, fmt_ta, get_supertrend_direction_string, format_bollinger_interpretation, format_cmf_interpretation


class TechnicalFormatter:
    """Consolidated formatter for all technical analysis sections."""
    
    def __init__(self, indicator_calculator, logger: Optional[Logger] = None):
        """Initialize the technical analysis formatter.
        
        Args:
            indicator_calculator: IndicatorCalculator instance for thresholds and calculations
            logger: Optional logger instance for debugging
        """
        self.indicator_calculator = indicator_calculator
        self.logger = logger
        self.INDICATOR_THRESHOLDS = indicator_calculator.INDICATOR_THRESHOLDS
    
    def format_technical_analysis(self, context, timeframe: str) -> str:
        """Format complete technical analysis section.
        
        Args:
            context: Analysis context containing technical data
            timeframe: Primary timeframe for analysis
            
        Returns:
            str: Formatted technical analysis section
        """
        if not context.technical_data:
            return "TECHNICAL ANALYSIS:\nNo technical data available."

        td = context.technical_data
        crypto_data = {'current_price': getattr(context, 'current_price', 0)}
        
        # Build all sections
        patterns_section = self._format_patterns_section(context)
        momentum_section = self.format_momentum_section(td)
        trend_section = self.format_trend_section(td)
        volume_section = self.format_volume_section(td)
        volatility_section = self.format_volatility_section(td, crypto_data)
        advanced_section = self.format_advanced_indicators_section(td, crypto_data)
        key_levels_section = self.format_key_levels_section(td)
        pattern_info = self._format_recent_patterns(context)

        # Build main technical analysis content
        technical_analysis = f"""\nTECHNICAL ANALYSIS ({timeframe}):\n\n## Price Action:\n- Current Price: {fmt(context.current_price)}\n- Rolling VWAP (20): {fmt_ta(self.indicator_calculator, td, 'vwap', 8)}\n- TWAP (20): {fmt_ta(self.indicator_calculator, td, 'twap', 8)}\n\n{momentum_section}\n\n{trend_section}\n\n{volatility_section}\n\n{volume_section}\n\n## Statistical Metrics:\n- Hurst Exponent(20): {fmt_ta(self.indicator_calculator, td, 'hurst', 2)} [~0.5: Random Walk, >0.5: Trending, <0.5: Mean Reverting]\n- Z-Score(20): {fmt_ta(self.indicator_calculator, td, 'zscore', 2)} [Distance from mean in std deviations]\n- Kurtosis(20): {fmt_ta(self.indicator_calculator, td, 'kurtosis', 2)} [Tail risk indicator; >3 suggests fatter tails]\n\n{key_levels_section}\n\n{advanced_section}\n\n{patterns_section}{pattern_info}"""

        return technical_analysis
    
    def format_momentum_section(self, td: dict) -> str:
        """Format the momentum indicators section."""
        return f"""## Momentum Indicators:
- RSI(14): {fmt_ta(self.indicator_calculator, td, 'rsi', 1)} [<{self.INDICATOR_THRESHOLDS['rsi']['oversold']}=Oversold, {self.INDICATOR_THRESHOLDS['rsi']['oversold']}-{self.INDICATOR_THRESHOLDS['rsi']['overbought']}=Neutral, >{self.INDICATOR_THRESHOLDS['rsi']['overbought']}=Overbought]
- MACD (12,26,9): [Pattern detector provides crossover analysis]
  * Line: {fmt_ta(self.indicator_calculator, td, 'macd_line', 8)}
  * Signal: {fmt_ta(self.indicator_calculator, td, 'macd_signal', 8)}
  * Histogram: {fmt_ta(self.indicator_calculator, td, 'macd_hist', 8)}
- Stochastic %K(14,3,3): {fmt_ta(self.indicator_calculator, td, 'stoch_k', 1)} [<{self.INDICATOR_THRESHOLDS['stoch_k']['oversold']}=Oversold, >{self.INDICATOR_THRESHOLDS['stoch_k']['overbought']}=Overbought]
- Stochastic %D(14,3,3): {fmt_ta(self.indicator_calculator, td, 'stoch_d', 1)} [<{self.INDICATOR_THRESHOLDS['stoch_d']['oversold']}=Oversold, >{self.INDICATOR_THRESHOLDS['stoch_d']['overbought']}=Overbought]
- Williams %R(14): {fmt_ta(self.indicator_calculator, td, 'williams_r', 1)} [<{self.INDICATOR_THRESHOLDS['williams_r']['oversold']}=Oversold, >{self.INDICATOR_THRESHOLDS['williams_r']['overbought']}=Overbought]"""

    def format_trend_section(self, td: dict) -> str:
        """Format the trend indicators section."""
        supertrend_direction = get_supertrend_direction_string(td.get('supertrend_direction', 0))

        return (
            "## Trend Indicators:\n"
            f"- ADX(14): {fmt_ta(self.indicator_calculator, td, 'adx', 1)} [0-{self.INDICATOR_THRESHOLDS['adx']['weak']}: Weak/No Trend, {self.INDICATOR_THRESHOLDS['adx']['weak']}-{self.INDICATOR_THRESHOLDS['adx']['strong']}: Strong, {self.INDICATOR_THRESHOLDS['adx']['strong']}-{self.INDICATOR_THRESHOLDS['adx']['very_strong']}: Very Strong, >{self.INDICATOR_THRESHOLDS['adx']['very_strong']}: Extremely Strong]\n"
            f"- +DI(14): {fmt_ta(self.indicator_calculator, td, 'plus_di', 1)} [Pattern detector analyzes DI crossovers]\n"
            f"- -DI(14): {fmt_ta(self.indicator_calculator, td, 'minus_di', 1)}\n"
            f"- Supertrend(20,3.0) Direction: {supertrend_direction}"
        )

    def format_volume_section(self, td: dict) -> str:
        """Format the volume indicators section."""
        cmf_interpretation = format_cmf_interpretation(self.indicator_calculator, td)
        
        return (
            "## Volume Indicators:\n"
            f"- MFI(14): {fmt_ta(self.indicator_calculator, td, 'mfi', 1)} [<{self.INDICATOR_THRESHOLDS['mfi']['oversold']}=Oversold, >{self.INDICATOR_THRESHOLDS['mfi']['overbought']}=Overbought]\n"
            f"- On Balance Volume (OBV): {fmt_ta(self.indicator_calculator, td, 'obv', 0)}\n"
            f"- Chaikin MF(20): {fmt_ta(self.indicator_calculator, td, 'cmf', 4)}{cmf_interpretation}\n"
            f"- Force Index(20): {fmt_ta(self.indicator_calculator, td, 'force_index', 0)}"
        )

    def format_volatility_section(self, td: dict, crypto_data: dict) -> str:
        """Format the volatility indicators section."""
        bb_interpretation = format_bollinger_interpretation(self.indicator_calculator, td)
        
        return (
            "## Volatility Indicators:\n"
            f"- Bollinger Bands(20,2): {fmt_ta(self.indicator_calculator, td, 'bb_upper', 8)} | {fmt_ta(self.indicator_calculator, td, 'bb_middle', 8)} | {fmt_ta(self.indicator_calculator, td, 'bb_lower', 8)}{bb_interpretation}\n"
            f"- BB %B: {fmt_ta(self.indicator_calculator, td, 'bb_percent_b', 2)} [0-1 range, >0.8=near upper, <0.2=near lower]\n"
            f"- ATR(14): {fmt_ta(self.indicator_calculator, td, 'atr', 8)}\n"
            f"- Keltner Channels(20,2): {fmt_ta(self.indicator_calculator, td, 'kc_upper', 8)} | {fmt_ta(self.indicator_calculator, td, 'kc_middle', 8)} | {fmt_ta(self.indicator_calculator, td, 'kc_lower', 8)}"
        )

    def format_key_levels_section(self, td: dict) -> str:
        """Format key levels section."""
        return (
            "## Key Levels:\n"
            f"- Basic Support: {fmt_ta(self.indicator_calculator, td, 'basic_support', 8)}\n"
            f"- Basic Resistance: {fmt_ta(self.indicator_calculator, td, 'basic_resistance', 8)}\n"
            f"- Pivot Point: {fmt_ta(self.indicator_calculator, td, 'pivot_point', 8)}\n"
            f"- Pivot S1: {fmt_ta(self.indicator_calculator, td, 'pivot_s1', 8)} | S2: {fmt_ta(self.indicator_calculator, td, 'pivot_s2', 8)} | S3: {fmt_ta(self.indicator_calculator, td, 'pivot_s3', 8)} | S4: {fmt_ta(self.indicator_calculator, td, 'pivot_s4', 8)}\n"
            f"- Pivot R1: {fmt_ta(self.indicator_calculator, td, 'pivot_r1', 8)} | R2: {fmt_ta(self.indicator_calculator, td, 'pivot_r2', 8)} | R3: {fmt_ta(self.indicator_calculator, td, 'pivot_r3', 8)} | R4: {fmt_ta(self.indicator_calculator, td, 'pivot_r4', 8)}"
        )

    def format_advanced_indicators_section(self, td: dict, crypto_data: dict) -> str:
        """Format advanced indicators section."""
        return (
            "## Advanced Indicators:\n"
            f"- Advanced Support: {fmt_ta(self.indicator_calculator, td, 'advanced_support', 8)}\n"
            f"- Advanced Resistance: {fmt_ta(self.indicator_calculator, td, 'advanced_resistance', 8)}\n"
            f"- Commodity Channel Index CCI(14): {fmt_ta(self.indicator_calculator, td, 'cci', 1)} [>100=Overbought, <-100=Oversold]\n"
            f"- Average True Range %: {fmt_ta(self.indicator_calculator, td, 'atr_percent', 2)}%\n"
            f"- Parabolic SAR: {fmt_ta(self.indicator_calculator, td, 'sar', 8)} [Price above SAR=Bullish, below=Bearish]\n"
            f"- Donchian Channels(20): {fmt_ta(self.indicator_calculator, td, 'donchian_upper', 8)} | {fmt_ta(self.indicator_calculator, td, 'donchian_lower', 8)}\n"
            f"- Ultimate Oscillator: {fmt_ta(self.indicator_calculator, td, 'uo', 1)} [>70=Overbought, <30=Oversold]"
        )
    
    def _format_patterns_section(self, context) -> str:
        """Format patterns section using detected patterns from context.
        
        Args:
            context: Analysis context containing technical data
            
        Returns:
            str: Formatted patterns section
        """
        # Use stored technical_patterns from analysis engine
        if context.technical_patterns:
            try:
                pattern_summaries = []
                for category, patterns_list in context.technical_patterns.items():
                    if patterns_list:  # Only process non-empty pattern lists
                        for pattern_dict in patterns_list:
                            description = pattern_dict.get('description', f'Unknown {category} pattern')
                            pattern_summaries.append(f"- {description}")
                
                if pattern_summaries:
                    if self.logger:
                        self.logger.debug(f"Including {len(pattern_summaries)} detected patterns in technical analysis")
                    return "\n\n## Detected Patterns:\n" + "\n".join(pattern_summaries[-10:])  # Show last 10 patterns
            except Exception as e:
                if self.logger:
                    self.logger.debug(f"Error using stored technical_patterns: {e}")
        
        # Fallback: try direct pattern detection
        try:
            ohlcv_data = context.ohlcv_candles
            technical_history = context.technical_data.get('history', {})
            
            patterns = self.indicator_calculator.get_all_patterns(ohlcv_data, technical_history)
            
            if self.logger:
                self.logger.debug(f"Using fallback pattern detection, found {len(patterns)} patterns")
            
            if patterns:
                pattern_summaries = []
                for pattern in patterns[-5:]:  # Show last 5 patterns
                    description = pattern.get('description', 'Unknown pattern')
                    pattern_summaries.append(f"- {description}")
                
                if pattern_summaries:
                    return "\n\n## Detected Patterns:\n" + "\n".join(pattern_summaries)
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Could not use fallback pattern detection: {e}")
        
        return ""
    
    def _format_recent_patterns(self, context) -> str:
        """Format recent pattern detection information.
        
        Args:
            context: Analysis context containing pattern data
            
        Returns:
            str: Formatted recent patterns section
        """
        if not context.recent_patterns:
            return ""
        
        try:
            pattern_lines = []
            for pattern_info in context.recent_patterns[-3:]:  # Last 3 patterns
                pattern_type = pattern_info.get('type', 'Unknown')
                confidence = pattern_info.get('confidence', 0)
                timeframe = pattern_info.get('timeframe', 'N/A')
                pattern_lines.append(f"  - {pattern_type} (Confidence: {confidence:.1f}%, Timeframe: {timeframe})")
            
            if pattern_lines:
                return f"\n\n## Recent Pattern Detection:\n" + "\n".join(pattern_lines)
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Error formatting recent patterns: {e}")
        
        return ""