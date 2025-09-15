"""
Consolidated Market Analysis Formatter.
Handles all market analysis formatting in a single comprehensive class.
"""
from typing import Dict, List, Optional
from src.logger.logger import Logger
from .format_utils import fmt, fmt_ta, format_timestamp, format_value


class MarketFormatter:
    """Consolidated formatter for all market analysis sections."""
    
    def __init__(self, logger: Optional[Logger] = None):
        """Initialize the market formatter."""
        self.logger = logger
        # Define indicator thresholds locally since we don't have indicator_calculator here
        self.INDICATOR_THRESHOLDS = {
            'rsi': {'oversold': 30, 'overbought': 70},
            'stoch_k': {'oversold': 20, 'overbought': 80},
            'adx': {'weak': 25, 'strong': 50, 'very_strong': 75},
            'bb_percent_b': {'oversold': 0.2, 'overbought': 0.8}
        }
    
    def format_market_period_metrics(self, market_metrics: dict) -> str:
        """Format market metrics for different periods."""
        if not market_metrics:
            return ""
        
        sections = []
        
        for period, metrics in market_metrics.items():
            if not metrics:
                continue
                
            period_sections = []
            period_sections.extend(self._format_period_price_section(metrics))
            period_sections.extend(self._format_period_volume_section(metrics))
            
            # Add indicator changes if available
            if 'indicator_changes' in metrics:
                period_sections.extend(self._format_indicator_changes_section(
                    metrics['indicator_changes'], period
                ))
            
            if period_sections:
                sections.append(f"\n{period.upper()} Analysis:")
                sections.extend(period_sections)
        
        return "\n".join(sections)
    
    def format_long_term_analysis(self, long_term_data: dict, current_price: float = None) -> str:
        """Format comprehensive long-term analysis from historical data."""
        if not long_term_data:
            return ""
        
        sections = []
        
        # Simple Moving Averages
        sma_section = self._format_sma_section(long_term_data)
        if sma_section:
            sections.append(sma_section)
        
        # Volume SMAs
        volume_sma_section = self._format_volume_sma_section(long_term_data)
        if volume_sma_section:
            sections.append(volume_sma_section)
        
        # Price position analysis
        if current_price:
            price_position_section = self._format_price_position_section(long_term_data, current_price)
            if price_position_section:
                sections.append(price_position_section)
        
        # Daily indicators
        if current_price:
            daily_indicators_section = self._format_daily_indicators_section(long_term_data, current_price)
            if daily_indicators_section:
                sections.append(daily_indicators_section)
        
        # ADX analysis
        adx_section = self._format_adx_section(long_term_data)
        if adx_section:
            sections.append(adx_section)
        
        # Ichimoku analysis
        if current_price:
            ichimoku_section = self._format_ichimoku_section(long_term_data, current_price)
            if ichimoku_section:
                sections.append(ichimoku_section)
        
        if sections:
            return "\n\n".join(sections)
        
        return ""
    
    def format_market_overview(self, market_overview: dict) -> str:
        """Format market overview data."""
        if not market_overview:
            return ""
        
        sections = []
        
        # Market cap and dominance
        if 'total_market_cap_usd' in market_overview:
            market_cap = market_overview['total_market_cap_usd']
            sections.append(f"📊 Total Market Cap: ${fmt(market_cap)}")
        
        if 'bitcoin_dominance' in market_overview:
            btc_dom = market_overview['bitcoin_dominance']
            sections.append(f"₿ Bitcoin Dominance: {fmt(btc_dom)}%")
        
        if 'ethereum_dominance' in market_overview:
            eth_dom = market_overview['ethereum_dominance']
            sections.append(f"Ξ Ethereum Dominance: {fmt(eth_dom)}%")
        
        # Market metrics
        if 'total_volume_24h_usd' in market_overview:
            volume = market_overview['total_volume_24h_usd']
            sections.append(f"📈 24h Volume: ${fmt(volume)}")
        
        if 'market_cap_change_24h_percentage_usd' in market_overview:
            change = market_overview['market_cap_change_24h_percentage_usd']
            direction = "📈" if change >= 0 else "📉"
            sections.append(f"{direction} Market Cap Change (24h): {fmt(change)}%")
        
        if sections:
            return "## Market Overview:\n" + "\n".join([f"- {section}" for section in sections])
        
        return ""
    
    def _format_period_price_section(self, metrics: dict) -> List[str]:
        """Format price-related metrics for a period."""
        price_sections = []
        
        # Price movements
        open_price = metrics.get('open')
        high_price = metrics.get('high')
        low_price = metrics.get('low')
        close_price = metrics.get('close')
        change = metrics.get('change')
        change_percent = metrics.get('change_percent')
        
        if open_price and close_price:
            price_sections.append(f"  💰 Price: ${fmt(open_price)} → ${fmt(close_price)}")
        
        if high_price and low_price:
            price_sections.append(f"  📈 Range: ${fmt(low_price)} - ${fmt(high_price)}")
        
        if change is not None and change_percent is not None:
            direction = "📈" if change >= 0 else "📉"
            price_sections.append(f"  {direction} Change: ${fmt(change)} ({fmt(change_percent)}%)")
        
        return price_sections
    
    def _format_period_volume_section(self, metrics: dict) -> List[str]:
        """Format volume-related metrics for a period."""
        volume_sections = []
        
        volume = metrics.get('volume')
        volume_change = metrics.get('volume_change_percent')
        
        if volume is not None:
            volume_sections.append(f"  📊 Volume: {fmt(volume)}")
        
        if volume_change is not None:
            direction = "🔊" if volume_change >= 0 else "🔉"
            volume_sections.append(f"  {direction} Volume Change: {fmt(volume_change)}%")
        
        return volume_sections
    
    def _format_indicator_changes_section(self, indicator_changes: dict, period_name: str) -> List[str]:
        """Format indicator changes for a period."""
        if not indicator_changes:
            return []
        
        changes_sections = [f"  📊 {period_name.capitalize()} Indicator Changes:"]
        
        # RSI changes
        rsi_change = indicator_changes.get('rsi_change')
        if rsi_change is not None:
            rsi_direction = "📈" if rsi_change >= 0 else "📉"
            changes_sections.append(f"    • RSI: {rsi_direction} {fmt(abs(rsi_change))} value change")
        
        # MACD changes (use macd_line which is the main MACD indicator)
        macd_change = indicator_changes.get('macd_line_change')
        if macd_change is not None:
            macd_direction = "📈" if macd_change >= 0 else "📉"
            changes_sections.append(f"    • MACD Line: {macd_direction} {fmt(abs(macd_change))}")
        
        # MACD Histogram changes
        macd_hist_change = indicator_changes.get('macd_hist_change')
        if macd_hist_change is not None:
            macd_hist_direction = "📈" if macd_hist_change >= 0 else "📉"
            changes_sections.append(f"    • MACD Histogram: {macd_hist_direction} {fmt(abs(macd_hist_change))}")
        
        # ADX changes
        adx_change = indicator_changes.get('adx_change')
        if adx_change is not None:
            adx_direction = "📈" if adx_change >= 0 else "📉"
            changes_sections.append(f"    • ADX: {adx_direction} {fmt(abs(adx_change))} value change")
        
        # Stochastic %K changes
        stoch_k_change = indicator_changes.get('stoch_k_change')
        if stoch_k_change is not None:
            stoch_direction = "📈" if stoch_k_change >= 0 else "📉"
            changes_sections.append(f"    • Stochastic %K: {stoch_direction} {fmt(abs(stoch_k_change))} value change")
        
        # Bollinger Bands position changes
        bb_position_change = indicator_changes.get('bb_position_change')
        if bb_position_change is not None:
            bb_direction = "📈" if bb_position_change >= 0 else "📉"
            changes_sections.append(f"    • BB Position: {bb_direction} {fmt(abs(bb_position_change))}")
        
        return changes_sections
    
    def _format_sma_section(self, long_term_data: dict) -> str:
        """Format Simple Moving Averages section."""
        sma_items = []
        for period in [20, 50, 100, 200]:
            key = f'sma_{period}'
            if key in long_term_data:
                sma_items.append(f"SMA{period}: {format_value(long_term_data[key])}")
        
        if sma_items:
            return "## Simple Moving Averages:\n" + " | ".join(sma_items)
        return ""
    
    def _format_volume_sma_section(self, long_term_data: dict) -> str:
        """Format Volume SMA section."""
        volume_sma_items = []
        for period in [20, 50]:
            key = f'volume_sma_{period}'
            if key in long_term_data:
                volume_sma_items.append(f"Vol SMA{period}: {format_value(long_term_data[key])}")
        
        if volume_sma_items:
            return "## Volume Moving Averages:\n" + " | ".join(volume_sma_items)
        return ""
    
    def _format_price_position_section(self, long_term_data: dict, current_price: float) -> str:
        """Format price position relative to moving averages."""
        position_items = []
        
        for period in [20, 50, 100, 200]:
            key = f'sma_{period}'
            if key in long_term_data and long_term_data[key]:
                sma_value = long_term_data[key]
                percentage = ((current_price - sma_value) / sma_value) * 100
                direction = "above" if percentage > 0 else "below"
                position_items.append(f"SMA{period}: {fmt(abs(percentage))}% {direction}")
        
        if position_items:
            return "## Price Position vs SMAs:\n" + " | ".join(position_items)
        return ""
    
    def _format_daily_indicators_section(self, long_term_data: dict, current_price: float) -> str:
        """Format daily timeframe indicators."""
        indicator_items = []
        
        # RSI
        if 'daily_rsi' in long_term_data:
            rsi_val = long_term_data['daily_rsi']
            rsi_status = "Overbought" if rsi_val > 70 else "Oversold" if rsi_val < 30 else "Neutral"
            indicator_items.append(f"Daily RSI: {format_value(rsi_val)} ({rsi_status})")
        
        # MACD
        if 'daily_macd_line' in long_term_data and 'daily_macd_signal' in long_term_data:
            macd_line = long_term_data['daily_macd_line']
            macd_signal = long_term_data['daily_macd_signal']
            macd_status = "Bullish" if macd_line > macd_signal else "Bearish"
            indicator_items.append(f"Daily MACD: {macd_status}")
        
        # Stochastic
        if 'daily_stoch_k' in long_term_data:
            stoch_val = long_term_data['daily_stoch_k']
            stoch_status = "Overbought" if stoch_val > 80 else "Oversold" if stoch_val < 20 else "Neutral"
            indicator_items.append(f"Daily Stoch: {format_value(stoch_val)} ({stoch_status})")
        
        if indicator_items:
            return "## Daily Indicators:\n" + " | ".join(indicator_items)
        return ""
    
    def _format_adx_section(self, long_term_data: dict) -> str:
        """Format ADX trend strength analysis."""
        if 'daily_adx' not in long_term_data:
            return ""
        
        adx_val = long_term_data['daily_adx']
        if adx_val < 25:
            strength = "Weak/No Trend"
        elif adx_val < 50:
            strength = "Strong Trend"
        elif adx_val < 75:
            strength = "Very Strong Trend"
        else:
            strength = "Extremely Strong Trend"
        
        return f"## Trend Strength (Daily ADX): {format_value(adx_val)} ({strength})"
    
    def _format_ichimoku_section(self, long_term_data: dict, current_price: float) -> str:
        """Format Ichimoku cloud analysis."""
        ichimoku_items = []
        
        # Tenkan and Kijun
        if 'ichimoku_tenkan' in long_term_data:
            tenkan = long_term_data['ichimoku_tenkan']
            ichimoku_items.append(f"Tenkan: {format_value(tenkan)}")
        
        if 'ichimoku_kijun' in long_term_data:
            kijun = long_term_data['ichimoku_kijun']
            ichimoku_items.append(f"Kijun: {format_value(kijun)}")
        
        # Cloud analysis
        if 'ichimoku_span_a' in long_term_data and 'ichimoku_span_b' in long_term_data:
            span_a = long_term_data['ichimoku_span_a']
            span_b = long_term_data['ichimoku_span_b']
            cloud_top = max(span_a, span_b)
            cloud_bottom = min(span_a, span_b)
            
            if current_price > cloud_top:
                cloud_position = "Above Cloud (Bullish)"
            elif current_price < cloud_bottom:
                cloud_position = "Below Cloud (Bearish)"
            else:
                cloud_position = "Inside Cloud (Neutral)"
            
            ichimoku_items.append(f"Cloud Position: {cloud_position}")
        
        if ichimoku_items:
            return "## Ichimoku Analysis:\n" + " | ".join(ichimoku_items)
        return ""