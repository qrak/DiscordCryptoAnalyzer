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
        
        # Get vortex values from the array
        vortex_array = td.get('vortex_indicator', [None, None])
        vortex_pos = fmt(vortex_array[0], 4) if vortex_array[0] is not None else 'N/A'
        vortex_neg = fmt(vortex_array[1], 4) if vortex_array[1] is not None else 'N/A'
        
        return f"""## Advanced Indicators:
- Ichimoku Cloud: Tenkan: {self._fmt_ta('ichimoku_conversion', td, 8)}, Kijun: {self._fmt_ta('ichimoku_base', td, 8)}, 
  Senkou A: {self._fmt_ta('ichimoku_span_a', td, 8)}, Senkou B: {self._fmt_ta('ichimoku_span_b', td, 8)}{ichimoku_interpretation}
- Parabolic SAR: {self._fmt_ta('sar', td, 8)}{psar_interpretation}
- SuperTrend: {self._fmt_ta('supertrend', td, 8)} (Direction: {self._get_supertrend_direction(td)})
- Advanced Momentum Indicators:
  * TSI: {self._fmt_ta('tsi', td, 4)} (True Strength Index)
  * RMI: {self._fmt_ta('rmi', td, 2)} (Relative Momentum Index)  
  * PPO: {self._fmt_ta('ppo', td, 4)} (Percentage Price Oscillator)
  * Coppock: {self._fmt_ta('coppock', td, 4)} (Coppock Curve)
  * UO: {self._fmt_ta('uo', td, 2)} (Ultimate Oscillator)
  * KST: {self._fmt_ta('kst', td, 4)} (Know Sure Thing)
- Advanced Trend Indicators:
  * TRIX: {self._fmt_ta('trix', td, 6)} (Rate of change of triple smoothed EMA)
  * PFE: {self._fmt_ta('pfe', td, 2)} (Polarized Fractal Efficiency)
- Chandelier Exits: Long: {self._fmt_ta('chandelier_long', td, 8)}, Short: {self._fmt_ta('chandelier_short', td, 8)}
- VortexIndicator+: {vortex_pos}, VI-: {vortex_neg}
- TD Sequential: {self._fmt_ta('td_sequential', td, 0)}"""
    
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
    
    def _get_supertrend_direction(self, td: dict) -> str:
        """Get SuperTrend direction interpretation."""
        direction = self.indicator_calculator.get_indicator_value(td, 'supertrend_direction')
        if direction == 1:
            return "Bullish"
        elif direction == -1:
            return "Bearish"
        return "N/A"
