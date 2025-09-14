"""
Advanced indicators formatting for technical analysis.
Handles Ichimoku, Demark, Parabolic SAR and other advanced indicators.
"""
import numpy as np
from ..basic_formatter import fmt, fmt_ta


class AdvancedIndicatorsFormatter:
    """Formats advanced indicators section for technical analysis."""
    
    def __init__(self, indicator_calculator, logger=None):
        self.indicator_calculator = indicator_calculator
        self.logger = logger
    
    def format_advanced_indicators_section(self, td: dict, crypto_data: dict) -> str:
        """Format the advanced indicators section."""
        ichimoku_interpretation = self._get_ichimoku_interpretation(td)
        psar_interpretation = self._get_psar_interpretation(td, crypto_data)
        
        # Get vortex values from the technical data
        vortex_pos = fmt_ta(self.indicator_calculator, td, 'vortex_plus', 4)
        vortex_neg = fmt_ta(self.indicator_calculator, td, 'vortex_minus', 4)
        
        return (
            "## Advanced Indicators:\n"
            f"- Ichimoku Cloud: Tenkan: {fmt_ta(self.indicator_calculator, td, 'ichimoku_conversion', 8)}, Kijun: {fmt_ta(self.indicator_calculator, td, 'ichimoku_base', 8)}, \n"
            f"  Senkou A: {fmt_ta(self.indicator_calculator, td, 'ichimoku_span_a', 8)}, Senkou B: {fmt_ta(self.indicator_calculator, td, 'ichimoku_span_b', 8)}{ichimoku_interpretation}\n"
            f"- Parabolic SAR: {fmt_ta(self.indicator_calculator, td, 'sar', 8)}{psar_interpretation}\n"
            f"- SuperTrend: {fmt_ta(self.indicator_calculator, td, 'supertrend', 8)} (Direction: {self._get_supertrend_direction(td)})\n"
            "- Advanced Momentum Indicators:\n"
            f"  * TSI: {fmt_ta(self.indicator_calculator, td, 'tsi', 4)} (True Strength Index)\n"
            f"  * RMI: {fmt_ta(self.indicator_calculator, td, 'rmi', 2)} (Relative Momentum Index)  \n"
            f"  * PPO: {fmt_ta(self.indicator_calculator, td, 'ppo', 4)} (Percentage Price Oscillator)\n"
            f"  * Coppock: {fmt_ta(self.indicator_calculator, td, 'coppock', 4)} (Coppock Curve)\n"
            f"  * UO: {fmt_ta(self.indicator_calculator, td, 'uo', 2)} (Ultimate Oscillator)\n"
            f"  * KST: {fmt_ta(self.indicator_calculator, td, 'kst', 4)} (Know Sure Thing)\n"
            "- Advanced Trend Indicators:\n"
            f"  * TRIX: {fmt_ta(self.indicator_calculator, td, 'trix', 6)} (Rate of change of triple smoothed EMA)\n"
            f"  * PFE: {fmt_ta(self.indicator_calculator, td, 'pfe', 2)} (Polarized Fractal Efficiency)\n"
            f"- Chandelier Exits: Long: {fmt_ta(self.indicator_calculator, td, 'chandelier_long', 8)}, Short: {fmt_ta(self.indicator_calculator, td, 'chandelier_short', 8)}\n"
            f"- VortexIndicator+: {vortex_pos}, VI-: {vortex_neg}\n"
            f"- TD Sequential: {fmt_ta(self.indicator_calculator, td, 'td_sequential', 0)}"
        )
    
    
    
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
