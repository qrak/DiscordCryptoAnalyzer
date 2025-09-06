"""
Trend indicators formatting for technical analysis.
Handles ADX, DI+/DI-, Supertrend and related trend indicators.
"""
import numpy as np
from ..basic_formatter import fmt


class TrendSectionFormatter:
    """Formats trend indicators section for technical analysis."""
    
    def __init__(self, indicator_calculator, logger=None):
        self.indicator_calculator = indicator_calculator
        self.logger = logger
        self.INDICATOR_THRESHOLDS = indicator_calculator.INDICATOR_THRESHOLDS
    
    def format_trend_section(self, td: dict) -> str:
        """Format the trend indicators section."""
        supertrend_direction = self._get_supertrend_direction_string(td.get('supertrend_direction', 0))
        
        return f"""## Trend Indicators:
- ADX(14): {self._fmt_ta('adx', td, 1)} [0-{self.INDICATOR_THRESHOLDS['adx']['weak']}: Weak/No Trend, {self.INDICATOR_THRESHOLDS['adx']['weak']}-{self.INDICATOR_THRESHOLDS['adx']['strong']}: Strong, {self.INDICATOR_THRESHOLDS['adx']['strong']}-{self.INDICATOR_THRESHOLDS['adx']['very_strong']}: Very Strong, >{self.INDICATOR_THRESHOLDS['adx']['very_strong']}: Extremely Strong]
- +DI(14): {self._fmt_ta('plus_di', td, 1)} [Pattern detector analyzes DI crossovers]
- -DI(14): {self._fmt_ta('minus_di', td, 1)}
- Supertrend(7,3.0) Direction: {supertrend_direction}"""
    
    def _fmt_ta(self, key: str, td: dict, precision: int = 8, default: str = 'N/A') -> str:
        """Format technical analysis value safely."""
        val = self.indicator_calculator.get_indicator_value(td, key)
        if isinstance(val, (int, float)) and not np.isnan(val):
            return fmt(val, precision)
        return default
    
    def _get_supertrend_direction_string(self, direction) -> str:
        """Get supertrend direction as string."""
        if direction > 0:
            return 'Bullish'
        elif direction < 0:
            return 'Bearish'
        else:
            return 'Neutral'
