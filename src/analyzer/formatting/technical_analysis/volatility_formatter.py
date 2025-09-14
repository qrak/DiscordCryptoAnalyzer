"""
Volatility indicators formatting for technical analysis.
Handles BB, ATR, Keltner Channels, VIX and related volatility indicators.
"""
import numpy as np
from ..basic_formatter import fmt, fmt_ta


class VolatilitySectionFormatter:
    """Formats volatility indicators section for technical analysis."""
    
    def __init__(self, indicator_calculator, logger=None):
        self.indicator_calculator = indicator_calculator
        self.logger = logger
    
    def format_volatility_section(self, td: dict, crypto_data: dict) -> str:
        """Format the volatility indicators section."""
        bb_interpretation = self._get_bb_interpretation(td)
        current_price = crypto_data.get('current_price', 0)
        
        return (
            "## Volatility Analysis:\n"
            f"- Bollinger Bands(20,2): {fmt_ta(self.indicator_calculator, td, 'bb_upper', 8)} | {fmt_ta(self.indicator_calculator, td, 'bb_middle', 8)} | {fmt_ta(self.indicator_calculator, td, 'bb_lower', 8)}{bb_interpretation}\n"
            f"- Current Price vs BB: {fmt(current_price, 8)}\n"
            f"- ATR(14): {fmt_ta(self.indicator_calculator, td, 'atr', 8)}\n"
            f"- Keltner Channels(20,2): {fmt_ta(self.indicator_calculator, td, 'kc_upper', 8)} | {fmt_ta(self.indicator_calculator, td, 'kc_middle', 8)} | {fmt_ta(self.indicator_calculator, td, 'kc_lower', 8)}"
        )
    
    
    def _get_bb_interpretation(self, td: dict) -> str:
        """Get Bollinger Bands interpretation."""
        bb_signal = self.indicator_calculator.get_indicator_value(td, 'bb_signal')
        if bb_signal == 1:
            return " (Price near Upper Band - potential resistance)"
        elif bb_signal == -1:
            return " (Price near Lower Band - potential support)"
        elif bb_signal == 0:
            return " (Price near Middle Band - neutral)"
        return ""
