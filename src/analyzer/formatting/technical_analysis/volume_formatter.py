"""
Volume indicators formatting for technical analysis.
Handles MFI, OBV, CMF, Force Index and related volume indicators.
"""
import numpy as np
from ..basic_formatter import fmt, fmt_ta


class VolumeSectionFormatter:
    """Formats volume indicators section for technical analysis."""
    
    def __init__(self, indicator_calculator, logger=None):
        self.indicator_calculator = indicator_calculator
        self.logger = logger
        self.INDICATOR_THRESHOLDS = indicator_calculator.INDICATOR_THRESHOLDS
    
    def format_volume_section(self, td: dict) -> str:
        """Format the volume indicators section."""
        cmf_interpretation = self._get_cmf_interpretation(td)
        
        return (
            "## Volume Analysis:\n"
            f"- MFI(14): {fmt_ta(self.indicator_calculator, td, 'mfi', 1)} [<{self.INDICATOR_THRESHOLDS['mfi']['oversold']}=Oversold, >{self.INDICATOR_THRESHOLDS['mfi']['overbought']}=Overbought]\n"
            f"- On Balance Volume (OBV): {fmt_ta(self.indicator_calculator, td, 'obv', 0)}\n"
            f"- Chaikin MF(20): {fmt_ta(self.indicator_calculator, td, 'cmf', 4)}{cmf_interpretation}\n"
            f"- Force Index(13): {fmt_ta(self.indicator_calculator, td, 'force_index', 0)}"
        )
    
    def _get_cmf_interpretation(self, td: dict) -> str:
        """Get Chaikin Money Flow interpretation."""
        cmf_val = self.indicator_calculator.get_indicator_value(td, 'cmf')
        if isinstance(cmf_val, (int, float)):
            if cmf_val > 0:
                return " (Positive suggests buying pressure)"
            if cmf_val < 0:
                return " (Negative suggests selling pressure)"
        return ""
