"""
Market metrics formatting for period-based analysis.
"""
from typing import Dict, List
from ..basic_formatter import fmt


class MarketMetricsFormatter:
    """Handles formatting of market metrics for different time periods."""
    
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
