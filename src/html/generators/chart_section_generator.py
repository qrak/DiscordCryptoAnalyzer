"""
Chart section generation utilities for HTML reports.
Handles chart generation, validation, and HTML formatting.
"""
import html
from src.html.chart_generator import ChartGenerator


class ChartSectionGenerator:
    """Handles chart generation and formatting for HTML reports."""
    
    def __init__(self, logger=None):
        self.logger = logger
        self.chart_generator = ChartGenerator()
    
    def generate_chart_html(self, ohlcv_data: dict) -> str:
        """
        Generate HTML for interactive chart.
        
        Args:
            ohlcv_data: Dictionary containing OHLCV data and related information
            
        Returns:
            HTML string with the interactive chart
        """
        try:
            if not self._validate_ohlcv_data(ohlcv_data):
                return "<p><em>No OHLCV data available for chart</em></p>"
                
            chart_params = self._extract_chart_parameters(ohlcv_data)
            chart_html = self._create_chart(chart_params)
            
            return self._wrap_chart_in_container(chart_html)
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Chart generation error: {e}")
            return f"<p><em>Chart generation failed: {html.escape(str(e))}</em></p>"
    
    def _validate_ohlcv_data(self, ohlcv_data: dict) -> bool:
        """Validate OHLCV data for chart generation."""
        if not ohlcv_data or 'ohlcv' not in ohlcv_data:
            return False
        
        ohlcv = ohlcv_data.get('ohlcv')
        return ohlcv is not None and len(ohlcv) > 0
    
    def _extract_chart_parameters(self, ohlcv_data: dict) -> dict:
        """Extract chart parameters from OHLCV data."""
        return {
            'ohlcv': ohlcv_data.get('ohlcv'),
            'technical_history': ohlcv_data.get('technical_history'),
            'patterns': ohlcv_data.get('patterns'),
            'pair_symbol': ohlcv_data.get('symbol', ''),
            'timeframe': ohlcv_data.get('timeframe', '1h')
        }
    
    def _create_chart(self, chart_params: dict) -> str:
        """Create the chart using the chart generator."""
        return self.chart_generator.create_ohlcv_chart(
            ohlcv=chart_params['ohlcv'],
            technical_history=chart_params['technical_history'],
            patterns=chart_params['patterns'],
            pair_symbol=chart_params['pair_symbol'],
            timeframe=chart_params['timeframe']
        )
    
    def _wrap_chart_in_container(self, chart_html: str) -> str:
        """Wrap the chart in a styled container."""
        return f"""
        <div class="chart-container">
            {chart_html}
        </div>
        """
