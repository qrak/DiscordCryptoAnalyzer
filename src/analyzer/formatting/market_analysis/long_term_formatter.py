"""
Long-term analysis formatting for historical data and trends.
"""
from typing import Dict, Optional
from ..basic_formatter import fmt


class LongTermFormatter:
    """Handles formatting of long-term analysis data and trends."""
    
    def __init__(self):
        # Define indicator thresholds for formatting context
        self.INDICATOR_THRESHOLDS = {
            'rsi': {'oversold': 30, 'overbought': 70},
            'stoch_k': {'oversold': 20, 'overbought': 80},
            'stoch_d': {'oversold': 20, 'overbought': 80},
            'williams_r': {'oversold': -80, 'overbought': -20},
            'adx': {'weak': 25, 'strong': 50, 'very_strong': 75},
            'mfi': {'oversold': 20, 'overbought': 80},
            'bb_width': {'tight': 2, 'wide': 10}
        }
    
    def format_long_term_analysis(self, long_term_data: dict, current_price: float = None) -> str:
        """Format comprehensive long-term analysis from historical data."""
        if not long_term_data:
            return self._format_no_data_analysis()
        
        # Check if this is a new token with limited data
        if self._is_new_token(long_term_data):
            return self._format_new_token_analysis(long_term_data)
        
        sections = []
        
        # SMA Analysis
        sma_section = self._format_sma_section(long_term_data)
        if sma_section:
            sections.append(sma_section)
        
        # Volume SMA Analysis
        volume_sma_section = self._format_volume_sma_section(long_term_data)
        if volume_sma_section:
            sections.append(volume_sma_section)
        
        # Price Position Analysis
        if current_price:
            price_position_section = self._format_price_position_section(long_term_data, current_price)
            if price_position_section:
                sections.append(price_position_section)
        
        # Daily Indicators Analysis
        if current_price:
            daily_indicators_section = self._format_daily_indicators_section(long_term_data, current_price)
            if daily_indicators_section:
                sections.append(daily_indicators_section)
        
        # ADX Analysis
        adx_section = self._format_adx_section(long_term_data)
        if adx_section:
            sections.append(adx_section)
        
        # Ichimoku Analysis
        if current_price:
            ichimoku_section = self._format_ichimoku_section(long_term_data, current_price)
            if ichimoku_section:
                sections.append(ichimoku_section)
        
        return "\n".join(sections) if sections else self._format_no_data_analysis()
    
    def _is_new_token(self, long_term_data: dict) -> bool:
        """Check if this appears to be a new token with limited historical data."""
        # Check for presence of key long-term indicators
        key_indicators = ['sma_20', 'sma_50', 'sma_200', 'volume_sma_20']
        missing_indicators = sum(1 for indicator in key_indicators 
                               if long_term_data.get(indicator) is None)
        
        return missing_indicators >= len(key_indicators) // 2
    
    def _format_no_data_analysis(self) -> str:
        """Format message when no long-term data is available."""
        return "\n🔍 Long-term Historical Analysis:\n  ⚠️ Insufficient historical data for comprehensive long-term analysis."
    
    def _format_new_token_analysis(self, long_term_data: dict) -> str:
        """Format analysis for tokens with limited historical data."""
        analysis = "\n🔍 Long-term Historical Analysis:\n"
        analysis += "  🆕 This appears to be a newer token with limited historical data.\n"
        analysis += "  📊 Available data points suggest:\n"
        
        # Check what data we do have
        if long_term_data.get('daily_rsi') is not None:
            rsi = long_term_data['daily_rsi']
            analysis += f"    • Current RSI: {fmt(rsi)} "
            if rsi < 30:
                analysis += "(Oversold territory)\n"
            elif rsi > 70:
                analysis += "(Overbought territory)\n"
            else:
                analysis += "(Neutral territory)\n"
        
        if long_term_data.get('daily_volume') is not None:
            analysis += f"    • Current volume activity level available\n"
        
        analysis += "  ⏳ More comprehensive analysis will be available as historical data accumulates."
        
        return analysis
