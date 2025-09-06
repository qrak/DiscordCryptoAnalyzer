"""
Advanced indicators formatting for technical analysis.
Handles Ichimoku, Demark, Parabolic SAR and other advanced indicators.
"""
import numpy as np
from ..basic_formatter import fmt


class AdvancedIndicatorsFormatter:
    """Formats advanced indicators section for technical analysis."""
    
    def __init__(self, indicator_calculator, logger=None):
        self.indicator_calculator = indicator_calculator
        self.logger = logger
    
    def format_advanced_indicators_section(self, td: dict, crypto_data: dict) -> str:
        """Format the advanced indicators section."""
        ichimoku_interpretation = self._get_ichimoku_interpretation(td)
        psar_interpretation = self._get_psar_interpretation(td, crypto_data)
        
        return f"""## Advanced Indicators:
- Ichimoku Cloud: Tenkan: {self._fmt_ta('ichimoku_tenkan', td, 8)}, Kijun: {self._fmt_ta('ichimoku_kijun', td, 8)}, 
  Senkou A: {self._fmt_ta('ichimoku_senkou_a', td, 8)}, Senkou B: {self._fmt_ta('ichimoku_senkou_b', td, 8)}{ichimoku_interpretation}
- Parabolic SAR: {self._fmt_ta('sar', td, 8)}{psar_interpretation}
- TD Sequential: {self._fmt_ta('td_sequential', td, 0)}
- VortexIndicator+: {self._fmt_ta('vortex_pos', td, 4)}, VI-: {self._fmt_ta('vortex_neg', td, 4)}"""
    
    def _fmt_ta(self, key: str, td: dict, precision: int = 8, default: str = 'N/A') -> str:
        """Format technical analysis value safely."""
        val = self.indicator_calculator.get_indicator_value(td, key)
        if isinstance(val, (int, float)) and not np.isnan(val):
            return fmt(val, precision)
        return default
    
    def _get_ichimoku_interpretation(self, td: dict) -> str:
        """Get Ichimoku Cloud interpretation."""
        ichimoku_signal = self.indicator_calculator.get_indicator_value(td, 'ichimoku_signal')
        if ichimoku_signal == 1:
            return " (Above Cloud - Bullish trend)"
        elif ichimoku_signal == -1:
            return " (Below Cloud - Bearish trend)"
        elif ichimoku_signal == 0:
            return " (In Cloud - Uncertain/Consolidation)"
        return ""
    
    def _get_psar_interpretation(self, td: dict, crypto_data: dict) -> str:
        """Get Parabolic SAR interpretation."""
        current_price = crypto_data.get('current_price', 0)
        psar_val = self.indicator_calculator.get_indicator_value(td, 'sar')
        
        if isinstance(psar_val, (int, float)) and isinstance(current_price, (int, float)):
            if current_price > psar_val:
                return " (Price above SAR - Bullish)"
            elif current_price < psar_val:
                return " (Price below SAR - Bearish)"
        return ""
