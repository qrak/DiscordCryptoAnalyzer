"""
Key levels and support/resistance formatting for technical analysis.
Handles pivot points, Fibonacci levels, and key price levels.
"""
import numpy as np
from ..basic_formatter import fmt


class KeyLevelsFormatter:
    """Formats key levels section for technical analysis."""
    
    def __init__(self, indicator_calculator, logger=None):
        self.indicator_calculator = indicator_calculator
        self.logger = logger
    
    def format_key_levels_section(self, td: dict) -> str:
        """Format the key levels section."""
        # Get support/resistance levels
        basic_support = self._fmt_ta('basic_support', td, 8)
        basic_resistance = self._fmt_ta('basic_resistance', td, 8)
        
        # Get advanced support/resistance (volume-weighted analysis)
        adv_support_resistance = td.get('support_resistance', [None, None])
        adv_support = fmt(adv_support_resistance[0], 8) if adv_support_resistance[0] is not None else 'N/A'
        adv_resistance = fmt(adv_support_resistance[1], 8) if adv_support_resistance[1] is not None else 'N/A'
        
        return f"""## Key Levels:
- Pivot Points: R2: {self._fmt_ta('pivot_r2', td, 8)}, R1: {self._fmt_ta('pivot_r1', td, 8)}, 
  PP: {self._fmt_ta('pivot_point', td, 8)}, S1: {self._fmt_ta('pivot_s1', td, 8)}, S2: {self._fmt_ta('pivot_s2', td, 8)}
- Basic Support/Resistance (30-period): Support: {basic_support}, Resistance: {basic_resistance}
- Advanced S/R (Volume-Weighted): Support: {adv_support}, Resistance: {adv_resistance}
- Fibonacci Retracement (if trending): 
  23.6%: {self._fmt_ta('fib_236', td, 8)}, 38.2%: {self._fmt_ta('fib_382', td, 8)}, 
  50%: {self._fmt_ta('fib_500', td, 8)}, 61.8%: {self._fmt_ta('fib_618', td, 8)}"""
    
    def _fmt_ta(self, key: str, td: dict, precision: int = 8, default: str = 'N/A') -> str:
        """Format technical analysis value safely."""
        val = self.indicator_calculator.get_indicator_value(td, key)
        if isinstance(val, (int, float)) and not np.isnan(val):
            return fmt(val, precision)
        return default
