"""
Momentum indicators formatting for technical analysis.
Handles RSI, MACD, Stochastic, Williams %R and related momentum indicators.
"""
import numpy as np
from typing import List
from ..basic_formatter import fmt, fmt_ta
from .base_formatter import BaseTechnicalFormatter


class MomentumSectionFormatter(BaseTechnicalFormatter):
    """Formats momentum indicators section for technical analysis."""
    
    def __init__(self, indicator_calculator, logger=None):
        super().__init__(indicator_calculator, logger)
        self.INDICATOR_THRESHOLDS = indicator_calculator.INDICATOR_THRESHOLDS
    
    def format_momentum_section(self, td: dict) -> str:
        """Format the momentum indicators section."""
        return f"""## Momentum Indicators:
- RSI(14): {fmt_ta(self.indicator_calculator, td, 'rsi', 1)} [<{self.INDICATOR_THRESHOLDS['rsi']['oversold']}=Oversold, {self.INDICATOR_THRESHOLDS['rsi']['oversold']}-{self.INDICATOR_THRESHOLDS['rsi']['overbought']}=Neutral, >{self.INDICATOR_THRESHOLDS['rsi']['overbought']}=Overbought]
- MACD (12,26,9): [Pattern detector provides crossover analysis]
  * Line: {fmt_ta(self.indicator_calculator, td, 'macd_line', 8)}
  * Signal: {fmt_ta(self.indicator_calculator, td, 'macd_signal', 8)}
  * Histogram: {fmt_ta(self.indicator_calculator, td, 'macd_hist', 8)}
- Stochastic %K(5,3,3): {fmt_ta(self.indicator_calculator, td, 'stoch_k', 1)} [<{self.INDICATOR_THRESHOLDS['stoch_k']['oversold']}=Oversold, >{self.INDICATOR_THRESHOLDS['stoch_k']['overbought']}=Overbought]
- Stochastic %D(5,3,3): {fmt_ta(self.indicator_calculator, td, 'stoch_d', 1)} [<{self.INDICATOR_THRESHOLDS['stoch_d']['oversold']}=Oversold, >{self.INDICATOR_THRESHOLDS['stoch_d']['overbought']}=Overbought]
- Williams %R(14): {fmt_ta(self.indicator_calculator, td, 'williams_r', 1)} [<{self.INDICATOR_THRESHOLDS['williams_r']['oversold']}=Oversold, >{self.INDICATOR_THRESHOLDS['williams_r']['overbought']}=Overbought]"""
