"""
Volatility indicators formatting for technical analysis.
Handles BB, ATR, Keltner Channels, VIX and related volatility indicators.
"""
import numpy as np
from ..basic_formatter import fmt


class VolatilitySectionFormatter:
    """Formats volatility indicators section for technical analysis."""
    
    def __init__(self, indicator_calculator, logger=None):
        self.indicator_calculator = indicator_calculator
        self.logger = logger
    
    def format_volatility_section(self, td: dict, crypto_data: dict) -> str:
        """Format the volatility indicators section."""
        bb_interpretation = self._get_bb_interpretation(td)
        current_price = crypto_data.get('current_price', 0)
        
        return f"""## Volatility Analysis:
- Bollinger Bands(20,2): {self._fmt_ta('bb_upper', td, 8)} | {self._fmt_ta('bb_middle', td, 8)} | {self._fmt_ta('bb_lower', td, 8)}{bb_interpretation}
- Current Price vs BB: {fmt(current_price, 8)}
- ATR(14): {self._fmt_ta('atr', td, 8)}
- Keltner Channels(20,2): {self._fmt_ta('kc_upper', td, 8)} | {self._fmt_ta('kc_middle', td, 8)} | {self._fmt_ta('kc_lower', td, 8)}"""
    
    def _fmt_ta(self, key: str, td: dict, precision: int = 8, default: str = 'N/A') -> str:
        """Format technical analysis value safely."""
        val = self.indicator_calculator.get_indicator_value(td, key)
        if isinstance(val, (int, float)) and not np.isnan(val):
            return fmt(val, precision)
        return default
    
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
