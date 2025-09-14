"""
Trend indicators formatting for technical analysis.
Handles ADX, DI+/DI-, Supertrend and related trend indicators.
"""
import numpy as np
from ..basic_formatter import fmt, fmt_ta


class TrendSectionFormatter:
    """Formats trend indicators section for technical analysis."""
    
    def __init__(self, indicator_calculator, logger=None):
        self.indicator_calculator = indicator_calculator
        self.logger = logger
        self.INDICATOR_THRESHOLDS = indicator_calculator.INDICATOR_THRESHOLDS
    
    def format_trend_section(self, td: dict) -> str:
        """Format the trend indicators section."""
        supertrend_direction = self._get_supertrend_direction_string(td.get('supertrend_direction', 0))

        return (
            "## Trend Indicators:\n"
            f"- ADX(14): {fmt_ta(self.indicator_calculator, td, 'adx', 1)} [0-{self.INDICATOR_THRESHOLDS['adx']['weak']}: Weak/No Trend, {self.INDICATOR_THRESHOLDS['adx']['weak']}-{self.INDICATOR_THRESHOLDS['adx']['strong']}: Strong, {self.INDICATOR_THRESHOLDS['adx']['strong']}-{self.INDICATOR_THRESHOLDS['adx']['very_strong']}: Very Strong, >{self.INDICATOR_THRESHOLDS['adx']['very_strong']}: Extremely Strong]\n"
            f"- +DI(14): {fmt_ta(self.indicator_calculator, td, 'plus_di', 1)} [Pattern detector analyzes DI crossovers]\n"
            f"- -DI(14): {fmt_ta(self.indicator_calculator, td, 'minus_di', 1)}\n"
            f"- Supertrend(7,3.0) Direction: {supertrend_direction}"
        )
    
    def _get_supertrend_direction_string(self, direction) -> str:
        """Get supertrend direction as string."""
        if direction > 0:
            return 'Bullish'
        elif direction < 0:
            return 'Bearish'
        else:
            return 'Neutral'
