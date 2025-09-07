"""
Technical analysis formatting for prompt building system.
Handles formatting of technical indicators, patterns, and analysis data.
"""

import numpy as np
from typing import Any, Dict, List, Optional

from src.logger.logger import Logger
from ..basic_formatter import fmt
from .momentum_formatter import MomentumSectionFormatter
from .trend_formatter import TrendSectionFormatter
from .volume_formatter import VolumeSectionFormatter
from .volatility_formatter import VolatilitySectionFormatter
from .advanced_indicators_formatter import AdvancedIndicatorsFormatter
from .key_levels_formatter import KeyLevelsFormatter


class TechnicalAnalysisFormatter:
    """Formats technical analysis data for prompt inclusion."""
    
    def __init__(self, indicator_calculator, logger: Optional[Logger] = None):
        """Initialize the technical analysis formatter.
        
        Args:
            indicator_calculator: IndicatorCalculator instance for thresholds and calculations
            logger: Optional logger instance for debugging
        """
        self.indicator_calculator = indicator_calculator
        self.logger = logger
        self.INDICATOR_THRESHOLDS = indicator_calculator.INDICATOR_THRESHOLDS
        
        # Initialize specialized formatters
        self.momentum_formatter = MomentumSectionFormatter(indicator_calculator, logger)
        self.trend_formatter = TrendSectionFormatter(indicator_calculator, logger)
        self.volume_formatter = VolumeSectionFormatter(indicator_calculator, logger)
        self.volatility_formatter = VolatilitySectionFormatter(indicator_calculator, logger)
        self.advanced_formatter = AdvancedIndicatorsFormatter(indicator_calculator, logger)
        self.key_levels_formatter = KeyLevelsFormatter(indicator_calculator, logger)
    
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
        
        # Build all sections using specialized formatters
        patterns_section = self._format_patterns_section(context)
        momentum_section = self.momentum_formatter.format_momentum_section(td)
        trend_section = self.trend_formatter.format_trend_section(td)
        volume_section = self.volume_formatter.format_volume_section(td)
        volatility_section = self.volatility_formatter.format_volatility_section(td, crypto_data)
        advanced_section = self.advanced_formatter.format_advanced_indicators_section(td, crypto_data)
        key_levels_section = self.key_levels_formatter.format_key_levels_section(td)
        pattern_info = self._format_recent_patterns(context)

        # Build main technical analysis content
        technical_analysis = f"""\nTECHNICAL ANALYSIS ({timeframe}):\n\n## Price Action:\n- Current Price: {fmt(context.current_price) if hasattr(context, 'current_price') else 0.0}\n- Rolling VWAP (14): {self._fmt_ta('vwap', td, 8)}\n- TWAP (14): {self._fmt_ta('twap', td, 8)}\n\n{momentum_section}\n\n{trend_section}\n\n{volatility_section}\n\n{volume_section}\n\n## Statistical Metrics:\n- Hurst Exponent(20): {self._fmt_ta('hurst', td, 2)} [~0.5: Random Walk, >0.5: Trending, <0.5: Mean Reverting]\n- Z-Score(30): {self._fmt_ta('zscore', td, 2)} [Distance from mean in std deviations]\n- Kurtosis(30): {self._fmt_ta('kurtosis', td, 2)} [Tail risk indicator; >3 suggests fatter tails]\n\n{key_levels_section}\n\n{advanced_section}\n\n{patterns_section}{pattern_info}"""
        
        return technical_analysis
    
    def _format_patterns_section(self, context) -> str:
        """Format patterns section using the modern PatternRecognizer.
        
        Args:
            context: Analysis context containing technical data
            
        Returns:
            str: Formatted patterns section
        """
        try:
            if hasattr(context, 'ohlcv_candles') and hasattr(context, 'technical_data'):
                ohlcv_data = context.ohlcv_candles
                technical_history = context.technical_data.get('history', {})
                patterns = self.indicator_calculator.get_all_patterns(ohlcv_data, technical_history)
                
                if patterns:
                    pattern_summaries = []
                    for pattern in patterns[-5:]:  # Show last 5 patterns
                        description = pattern.get('description', 'Unknown pattern')
                        pattern_summaries.append(f"- {description}")
                    
                    if pattern_summaries:
                        return "## Key Patterns (PatternRecognizer):\n" + "\n".join(pattern_summaries)
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Could not use PatternRecognizer for patterns: {e}")
        
        return ""
    
    def _fmt_ta(self, key: str, td: dict, precision: int = 8, default: str = 'N/A') -> str:
        """Format technical analysis value safely.
        
        Args:
            key: Indicator key to format
            td: Technical data dictionary
            precision: Number of decimal places
            default: Default value if indicator unavailable
            
        Returns:
            str: Formatted value or default
        """
        val = self.indicator_calculator.get_indicator_value(td, key)
        if isinstance(val, (int, float)) and not np.isnan(val):
            return fmt(val, precision)
        return default
    
    def _format_recent_patterns(self, context) -> str:
        """Format recent pattern detection information.
        
        Args:
            context: Analysis context containing pattern data
            
        Returns:
            str: Formatted recent patterns section
        """
        if not hasattr(context, 'recent_patterns') or not context.recent_patterns:
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
