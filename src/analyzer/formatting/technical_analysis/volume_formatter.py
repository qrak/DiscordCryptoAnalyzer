"""
Volume indicators formatting for technical analysis.
Handles MFI, OBV, CMF, Force Index and related volume indicators.
"""
import numpy as np
from ..basic_formatter import fmt


class VolumeSectionFormatter:
    """Formats volume indicators section for technical analysis."""
    
    def __init__(self, indicator_calculator, logger=None):
        self.indicator_calculator = indicator_calculator
        self.logger = logger
        self.INDICATOR_THRESHOLDS = indicator_calculator.INDICATOR_THRESHOLDS
    
    def format_volume_section(self, td: dict) -> str:
        """Format the volume indicators section."""
        cmf_interpretation = self._get_cmf_interpretation(td)
        
        return f"""## Volume Analysis:
- MFI(14): {self._fmt_ta('mfi', td, 1)} [<{self.INDICATOR_THRESHOLDS['mfi']['oversold']}=Oversold, >{self.INDICATOR_THRESHOLDS['mfi']['overbought']}=Overbought]
- On Balance Volume (OBV): {self._fmt_ta('obv', td, 0)}
- Chaikin MF(20): {self._fmt_ta('cmf', td, 4)}{cmf_interpretation}
- Force Index(13): {self._fmt_ta('force_index', td, 0)}"""
    
    def _fmt_ta(self, key: str, td: dict, precision: int = 8, default: str = 'N/A') -> str:
        """Format technical analysis value safely."""
        val = self.indicator_calculator.get_indicator_value(td, key)
        if isinstance(val, (int, float)) and not np.isnan(val):
            return fmt(val, precision)
        return default
    
    def _get_cmf_interpretation(self, td: dict) -> str:
        """Get Chaikin Money Flow interpretation."""
        cmf_val = self.indicator_calculator.get_indicator_value(td, 'cmf')
        if isinstance(cmf_val, (int, float)):
            if cmf_val > 0:
                return " (Positive suggests buying pressure)"
            if cmf_val < 0:
                return " (Negative suggests selling pressure)"
        return ""
