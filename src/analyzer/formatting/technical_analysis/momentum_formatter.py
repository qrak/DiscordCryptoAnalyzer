"""
Momentum indicators formatting for technical analysis.
Handles RSI, MACD, Stochastic, Williams %R and related momentum indicators.
"""
import numpy as np
from typing import List
from ..basic_formatter import fmt


class MomentumSectionFormatter:
    """Formats momentum indicators section for technical analysis."""
    
    def __init__(self, indicator_calculator, logger=None):
        self.indicator_calculator = indicator_calculator
        self.logger = logger
        self.INDICATOR_THRESHOLDS = indicator_calculator.INDICATOR_THRESHOLDS
    
    def format_momentum_section(self, td: dict) -> str:
        """Format the momentum indicators section."""
        return f"""## Momentum Indicators:
- RSI(14): {self._fmt_ta('rsi', td, 1)} [<{self.INDICATOR_THRESHOLDS['rsi']['oversold']}=Oversold, {self.INDICATOR_THRESHOLDS['rsi']['oversold']}-{self.INDICATOR_THRESHOLDS['rsi']['overbought']}=Neutral, >{self.INDICATOR_THRESHOLDS['rsi']['overbought']}=Overbought]
- MACD (12,26,9): [Pattern detector provides crossover analysis]
  * Line: {self._fmt_ta('macd_line', td, 8)}
  * Signal: {self._fmt_ta('macd_signal', td, 8)}
  * Histogram: {self._fmt_ta('macd_hist', td, 8)}
- Stochastic %K(5,3,3): {self._fmt_ta('stoch_k', td, 1)} [<{self.INDICATOR_THRESHOLDS['stoch_k']['oversold']}=Oversold, >{self.INDICATOR_THRESHOLDS['stoch_k']['overbought']}=Overbought]
- Stochastic %D(5,3,3): {self._fmt_ta('stoch_d', td, 1)} [<{self.INDICATOR_THRESHOLDS['stoch_d']['oversold']}=Oversold, >{self.INDICATOR_THRESHOLDS['stoch_d']['overbought']}=Overbought]
- Williams %R(14): {self._fmt_ta('williams_r', td, 1)} [<{self.INDICATOR_THRESHOLDS['williams_r']['oversold']}=Oversold, >{self.INDICATOR_THRESHOLDS['williams_r']['overbought']}=Overbought]"""
    
    def format_basic_momentum_indicators(self, td: dict) -> List[str]:
        """Format basic momentum indicators for advanced section."""
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
    
    def _format_single_momentum_indicator(self, td: dict, key: str, label: str, add_percent: bool) -> List[str]:
        """Format a single momentum indicator."""
        value = self.indicator_calculator.get_indicator_value(td, key)
        if not self._is_valid_value(value):
            return []
        
        bias = self._get_momentum_bias(value)
        suffix = '%' if add_percent else ''
        return [f"- {label}: {self._fmt_val(value)}{suffix} ({bias})"]
    
    def _fmt_ta(self, key: str, td: dict, precision: int = 8, default: str = 'N/A') -> str:
        """Format technical analysis value safely."""
        val = self.indicator_calculator.get_indicator_value(td, key)
        if isinstance(val, (int, float)) and not np.isnan(val):
            return fmt(val, precision)
        return default
    
    def _is_valid_value(self, value) -> bool:
        """Check if a value is valid for formatting."""
        return isinstance(value, (int, float)) and not np.isnan(value)
    
    def _fmt_val(self, value, precision: int = 8) -> str:
        """Format a value safely."""
        return fmt(value, precision) if self._is_valid_value(value) else 'N/A'
    
    def _get_momentum_bias(self, value) -> str:
        """Get bias string for momentum indicators."""
        if not isinstance(value, (int, float)):
            return "neutral"
        return "bullish" if value > 0 else "bearish" if value < 0 else "neutral"
