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
        # Use the is_new_token flag set by the market data collector
        # This is based on actual data availability and completeness
        return long_term_data.get('is_new_token', False)
    
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
    
    def _format_sma_section(self, long_term_data: dict) -> str:
        """Format Simple Moving Average analysis section."""
        sma_lines = []
        if long_term_data.get('sma_values'):
            for period, value in long_term_data['sma_values'].items():
                sma_lines.append(f"- SMA({period}): {fmt(value, 8)}")
        
        return "Moving Averages (Daily):\n" + "\n".join(sma_lines) if sma_lines else ""
    
    def _format_volume_sma_section(self, long_term_data: dict) -> str:
        """Format Volume Simple Moving Average analysis section."""
        vol_sma_lines = []
        if long_term_data.get('volume_sma_values'):
            for period, value in long_term_data['volume_sma_values'].items():
                vol_sma_lines.append(f"- Volume SMA({period}): {value:.2f}")
        
        return "\n\nVolume Moving Averages (Daily):\n" + "\n".join(vol_sma_lines) if vol_sma_lines else ""
    
    def _format_price_position_section(self, long_term_data: dict, current_price: float) -> str:
        """Format price position relative to moving averages."""
        if not (long_term_data.get('sma_values') and current_price):
            return ""
        
        sma_values = long_term_data['sma_values']
        above_count = sum(1 for sma_value in sma_values.values() if current_price > sma_value)
        below_count = sum(1 for sma_value in sma_values.values() if current_price < sma_value)
        
        price_position = ""
        if above_count > below_count:
            price_position = f"\n\nPrice Position: Price is above {above_count}/{len(sma_values)} major SMAs, suggesting overall bullish momentum."
        elif below_count > above_count:
            price_position = f"\n\nPrice Position: Price is below {below_count}/{len(sma_values)} major SMAs, suggesting overall bearish momentum."
        
        # Add Golden/Death Cross analysis
        if 50 in sma_values and 200 in sma_values:
            sma50, sma200 = sma_values[50], sma_values[200]
            if sma50 > sma200:
                cross_pct = ((sma50 / sma200) - 1) * 100
                price_position += f"\nGolden Cross: SMA(50) is {cross_pct:.2f}% above SMA(200), indicating a potential long-term bullish trend."
            elif sma200 > sma50:
                cross_pct = ((sma200 / sma50) - 1) * 100
                price_position += f"\nDeath Cross: SMA(50) is {cross_pct:.2f}% below SMA(200), indicating a potential long-term bearish trend."
        
        return price_position
    
    def _format_daily_indicators_section(self, long_term_data: dict, current_price: float) -> str:
        """Format current daily indicators section with detailed analysis."""
        daily_indicators_text = "\n\nCurrent Daily Indicators:\n"
        
        # RSI
        daily_rsi = long_term_data.get('daily_rsi')
        if daily_rsi is not None:
            rsi_cond = ("Oversold" if daily_rsi < self.INDICATOR_THRESHOLDS['rsi']['oversold'] else
                       "Overbought" if daily_rsi > self.INDICATOR_THRESHOLDS['rsi']['overbought'] else "Neutral")
            daily_indicators_text += f"- Daily RSI(14): {daily_rsi:.1f} ({rsi_cond})\n"
        else:
            daily_indicators_text += "- Daily RSI(14): N/A\n"
        
        # MACD
        macd_line = long_term_data.get('daily_macd_line')
        macd_signal = long_term_data.get('daily_macd_signal')
        macd_hist = long_term_data.get('daily_macd_hist')
        if all(v is not None for v in [macd_line, macd_signal, macd_hist]):
            macd_cond = ("Bullish Momentum" if macd_line > macd_signal and macd_hist > 0 else
                        "Bearish Momentum" if macd_line < macd_signal and macd_hist < 0 else "Neutral")
            daily_indicators_text += f"- Daily MACD(12,26,9): Line={fmt(macd_line, 8)}, Signal={fmt(macd_signal, 8)}, Hist={fmt(macd_hist, 8)} ({macd_cond})\n"
        else:
            daily_indicators_text += "- Daily MACD(12,26,9): N/A\n"
        
        # ATR
        daily_atr = long_term_data.get('daily_atr')
        if daily_atr is not None:
            daily_indicators_text += f"- Daily ATR(14): {fmt(daily_atr, 8)} (Avg True Range)\n"
        else:
            daily_indicators_text += "- Daily ATR(14): N/A\n"
        
        # OBV
        daily_obv = long_term_data.get('daily_obv')
        if daily_obv is not None:
            daily_indicators_text += f"- Daily OBV: {daily_obv:.0f} (Trend indicates volume flow)\n"
        else:
            daily_indicators_text += "- Daily OBV: N/A\n"
        
        return daily_indicators_text if daily_indicators_text != "\n\nCurrent Daily Indicators:\n" else ""
    
    def _format_adx_section(self, long_term_data: dict) -> str:
        """Format ADX (Average Directional Index) analysis section."""
        daily_adx = long_term_data.get('daily_adx')
        daily_plus_di = long_term_data.get('daily_plus_di')
        daily_minus_di = long_term_data.get('daily_minus_di')
        
        if all(v is not None for v in [daily_adx, daily_plus_di, daily_minus_di]):
            adx_cond = ("Extremely Strong Trend" if daily_adx > self.INDICATOR_THRESHOLDS['adx']['very_strong'] else
                       "Very Strong Trend" if daily_adx > self.INDICATOR_THRESHOLDS['adx']['strong'] else
                       "Strong Trend" if daily_adx > self.INDICATOR_THRESHOLDS['adx']['weak'] else "Weak/No Trend")
            
            di_cond = ("Bullish Pressure (+DI > -DI)" if daily_plus_di > daily_minus_di else
                      "Bearish Pressure (-DI > +DI)" if daily_minus_di > daily_plus_di else "Neutral")
            
            return f"- Daily ADX(14): {daily_adx:.1f} ({adx_cond}), +DI={daily_plus_di:.1f}, -DI={daily_minus_di:.1f} ({di_cond})\n"
        else:
            return "- Daily ADX/DI(14): N/A\n"
    
    def _format_ichimoku_section(self, long_term_data: dict, current_price: float) -> str:
        """Format Ichimoku Cloud analysis section."""
        daily_conv = long_term_data.get('daily_ichimoku_conversion')
        daily_base = long_term_data.get('daily_ichimoku_base')
        daily_span_a = long_term_data.get('daily_ichimoku_span_a')
        daily_span_b = long_term_data.get('daily_ichimoku_span_b')
        
        if not all(v is not None for v in [daily_conv, daily_base, daily_span_a, daily_span_b]):
            return "- Daily Ichimoku Cloud: N/A (Requires 52+ days)\n"
        
        cloud_status = ("Bullish Cloud" if daily_span_a > daily_span_b else
                       "Bearish Cloud" if daily_span_b > daily_span_a else "Neutral")
        
        price_cloud = "N/A"
        if current_price:
            if current_price > max(daily_span_a, daily_span_b):
                price_cloud = "Above Cloud (Bullish)"
            elif current_price < min(daily_span_a, daily_span_b):
                price_cloud = "Below Cloud (Bearish)"
            else:
                price_cloud = "Inside Cloud (Neutral/Uncertain)"
        
        tk_cross = ("Bullish TK Cross" if daily_conv > daily_base else
                   "Bearish TK Cross" if daily_base > daily_conv else "Neutral")
        
        return (f"- Daily Ichimoku: Conv={daily_conv:.6f}, Base={daily_base:.6f}, "
                f"SpanA={daily_span_a:.6f}, SpanB={daily_span_b:.6f}\n"
                f"  * Cloud: {cloud_status}, Price: {price_cloud}, TK Cross: {tk_cross}\n")
