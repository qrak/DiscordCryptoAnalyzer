"""
Key levels and support/resistance formatting for technical analysis.
Handles pivot points, Fibonacci levels, and key price levels.
"""
import numpy as np
from ..basic_formatter import fmt, fmt_ta


class KeyLevelsFormatter:
    """Formats key levels section for technical analysis."""
    
    def __init__(self, indicator_calculator, logger=None):
        self.indicator_calculator = indicator_calculator
        self.logger = logger
    
    def format_key_levels_section(self, td: dict) -> str:
        """Format the key levels section."""
        # Get support/resistance levels
        basic_support = fmt_ta(self.indicator_calculator, td, 'basic_support', 8)
        basic_resistance = fmt_ta(self.indicator_calculator, td, 'basic_resistance', 8)
        
        # Get advanced support/resistance (volume-weighted analysis)
        adv_support_resistance = td.get('support_resistance', [None, None])
        adv_support = fmt(adv_support_resistance[0], 8) if adv_support_resistance[0] is not None else 'N/A'
        adv_resistance = fmt(adv_support_resistance[1], 8) if adv_support_resistance[1] is not None else 'N/A'
        
        return (
            "## Key Levels:\n"
            f"- Pivot Points: R4: {fmt_ta(self.indicator_calculator, td, 'pivot_r4', 8)}, R3: {fmt_ta(self.indicator_calculator, td, 'pivot_r3', 8)}, R2: {fmt_ta(self.indicator_calculator, td, 'pivot_r2', 8)}, R1: {fmt_ta(self.indicator_calculator, td, 'pivot_r1', 8)},\n"
            f"  PP: {fmt_ta(self.indicator_calculator, td, 'pivot_point', 8)}, S1: {fmt_ta(self.indicator_calculator, td, 'pivot_s1', 8)}, S2: {fmt_ta(self.indicator_calculator, td, 'pivot_s2', 8)}, S3: {fmt_ta(self.indicator_calculator, td, 'pivot_s3', 8)}, S4: {fmt_ta(self.indicator_calculator, td, 'pivot_s4', 8)}\n"
            f"- Basic Support/Resistance (30-period): Support: {basic_support}, Resistance: {basic_resistance}\n"
            f"- Advanced S/R (Volume-Weighted): Support: {adv_support}, Resistance: {adv_resistance}\n"
            "- Fibonacci Retracement (if trending): \n"
            f"  23.6%: {fmt_ta(self.indicator_calculator, td, 'fib_236', 8)}, 38.2%: {fmt_ta(self.indicator_calculator, td, 'fib_382', 8)}, \n"
            f"  50%: {fmt_ta(self.indicator_calculator, td, 'fib_500', 8)}, 61.8%: {fmt_ta(self.indicator_calculator, td, 'fib_618', 8)}"
        )
    
