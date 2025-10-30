"""
Consolidated Market Analysis Formatter.
Handles all market analysis formatting in a single comprehensive class.
"""
from typing import Dict, List, Optional, Any
from src.logger.logger import Logger
from src.utils.token_counter import TokenCounter
from src.utils.format_utils import FormatUtils


class MarketFormatter:
    """Consolidated formatter for all market analysis sections."""
    
    def __init__(self, logger: Optional[Logger] = None):
        """Initialize the market formatter."""
        self.logger = logger
        self.token_counter = TokenCounter()
        self.format_utils = FormatUtils()
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
        
        for period, period_data in market_metrics.items():
            if not period_data:
                continue
            
            # Extract metrics from nested structure
            metrics = period_data.get('metrics', {})
            if not metrics:
                continue
                
            period_sections = []
            period_sections.extend(self._format_period_price_section(metrics))
            period_sections.extend(self._format_period_volume_section(metrics))
            
            # Add indicator changes if available
            if 'indicator_changes' in period_data:
                period_sections.extend(self._format_indicator_changes_section(
                    period_data['indicator_changes'], period
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
        
        # Macro trend analysis (365-day SMA context)
        if 'macro_trend' in long_term_data:
            macro_trend_section = self._format_macro_trend_section(long_term_data['macro_trend'])
            if macro_trend_section:
                sections.append(macro_trend_section)
        
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
            sections.append(f"📊 Total Market Cap: ${self.format_utils.fmt(market_cap)}")
        
        if 'bitcoin_dominance' in market_overview:
            btc_dom = market_overview['bitcoin_dominance']
            sections.append(f"₿ Bitcoin Dominance: {self.format_utils.fmt(btc_dom)}%")
        
        if 'ethereum_dominance' in market_overview:
            eth_dom = market_overview['ethereum_dominance']
            sections.append(f"Ξ Ethereum Dominance: {self.format_utils.fmt(eth_dom)}%")
        
        # Market metrics
        if 'total_volume_24h_usd' in market_overview:
            volume = market_overview['total_volume_24h_usd']
            sections.append(f"📈 24h Volume: ${self.format_utils.fmt(volume)}")
        
        if 'market_cap_change_24h_percentage_usd' in market_overview:
            change = market_overview['market_cap_change_24h_percentage_usd']
            direction = "📈" if change >= 0 else "📉"
            sections.append(f"{direction} Market Cap Change (24h): {self.format_utils.fmt(change)}%")
        
        if sections:
            return "## Market Overview:\n" + "\n".join([f"- {section}" for section in sections])
        
        return ""
    
    def _format_period_price_section(self, metrics: dict) -> List[str]:
        """Format price-related metrics for a period."""
        price_sections = []
        
        # Get basic metrics (from _calculate_basic_metrics structure)
        highest_price = metrics.get('highest_price')
        lowest_price = metrics.get('lowest_price')
        price_change = metrics.get('price_change')
        price_change_percent = metrics.get('price_change_percent')
        avg_price = metrics.get('avg_price')
        
        if avg_price is not None:
            price_sections.append(f"  💰 Average Price: ${self.format_utils.fmt(avg_price)}")
        
        if highest_price and lowest_price:
            price_sections.append(f"  📈 Range: ${self.format_utils.fmt(lowest_price)} - ${self.format_utils.fmt(highest_price)}")
        
        if price_change is not None and price_change_percent is not None:
            direction = "📈" if price_change >= 0 else "📉"
            price_sections.append(f"  {direction} Change: ${self.format_utils.fmt(price_change)} ({self.format_utils.fmt(price_change_percent)}%)")
        
        return price_sections
    
    def _format_period_volume_section(self, metrics: dict) -> List[str]:
        """Format volume-related metrics for a period."""
        volume_sections = []
        
        total_volume = metrics.get('total_volume')
        avg_volume = metrics.get('avg_volume')
        
        if total_volume is not None:
            volume_sections.append(f"  📊 Total Volume: {self.format_utils.fmt(total_volume)}")
        
        if avg_volume is not None:
            volume_sections.append(f"  📊 Average Volume: {self.format_utils.fmt(avg_volume)}")
        
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
            changes_sections.append(f"    • RSI: {rsi_direction} {self.format_utils.fmt(abs(rsi_change))} value change")
        
        # MACD changes (use macd_line which is the main MACD indicator)
        macd_change = indicator_changes.get('macd_line_change')
        if macd_change is not None:
            macd_direction = "📈" if macd_change >= 0 else "📉"
            changes_sections.append(f"    • MACD Line: {macd_direction} {self.format_utils.fmt(abs(macd_change))}")
        
        # MACD Histogram changes
        macd_hist_change = indicator_changes.get('macd_hist_change')
        if macd_hist_change is not None:
            macd_hist_direction = "📈" if macd_hist_change >= 0 else "📉"
            changes_sections.append(f"    • MACD Histogram: {macd_hist_direction} {self.format_utils.fmt(abs(macd_hist_change))}")
        
        # ADX changes
        adx_change = indicator_changes.get('adx_change')
        if adx_change is not None:
            adx_direction = "📈" if adx_change >= 0 else "📉"
            changes_sections.append(f"    • ADX: {adx_direction} {self.format_utils.fmt(abs(adx_change))} value change")
        
        # Stochastic %K changes
        stoch_k_change = indicator_changes.get('stoch_k_change')
        if stoch_k_change is not None:
            stoch_direction = "📈" if stoch_k_change >= 0 else "📉"
            changes_sections.append(f"    • Stochastic %K: {stoch_direction} {self.format_utils.fmt(abs(stoch_k_change))} value change")
        
        # Bollinger Bands position changes
        bb_position_change = indicator_changes.get('bb_position_change')
        if bb_position_change is not None:
            bb_direction = "📈" if bb_position_change >= 0 else "📉"
            changes_sections.append(f"    • BB Position: {bb_direction} {self.format_utils.fmt(abs(bb_position_change))}")
        
        return changes_sections
    
    def _format_sma_section(self, long_term_data: dict) -> str:
        """Format Simple Moving Averages section."""
        sma_items = []
        for period in [20, 50, 100, 200]:
            key = f'sma_{period}'
            if key in long_term_data:
                sma_items.append(f"SMA{period}: {self.format_utils.format_value(long_term_data[key])}")
        
        if sma_items:
            return "## Simple Moving Averages:\n" + " | ".join(sma_items)
        return ""
    
    def _format_volume_sma_section(self, long_term_data: dict) -> str:
        """Format Volume SMA section."""
        volume_sma_items = []
        for period in [20, 50]:
            key = f'volume_sma_{period}'
            if key in long_term_data:
                volume_sma_items.append(f"Vol SMA{period}: {self.format_utils.format_value(long_term_data[key])}")
        
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
                position_items.append(f"SMA{period}: {self.format_utils.fmt(abs(percentage))}% {direction}")
        
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
            indicator_items.append(f"Daily RSI: {self.format_utils.format_value(rsi_val)} ({rsi_status})")
        
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
            indicator_items.append(f"Daily Stoch: {self.format_utils.format_value(stoch_val)} ({stoch_status})")
        
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
        
        return f"## Trend Strength (Daily ADX): {self.format_utils.format_value(adx_val)} ({strength})"
    
    def _format_ichimoku_section(self, long_term_data: dict, current_price: float) -> str:
        """Format Ichimoku cloud analysis."""
        ichimoku_items = []
        
        # Tenkan and Kijun
        if 'ichimoku_tenkan' in long_term_data:
            tenkan = long_term_data['ichimoku_tenkan']
            ichimoku_items.append(f"Tenkan: {self.format_utils.format_value(tenkan)}")
        
        if 'ichimoku_kijun' in long_term_data:
            kijun = long_term_data['ichimoku_kijun']
            ichimoku_items.append(f"Kijun: {self.format_utils.format_value(kijun)}")
        
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
    
    def _format_macro_trend_section(self, macro_trend: dict) -> str:
        """Format 365-day macro trend analysis based on SMA relationships."""
        if not macro_trend:
            return ""
            
        trend_direction = macro_trend.get('trend_direction', 'Neutral')
        sma_alignment = macro_trend.get('sma_alignment', 'Mixed')
        sma_50_vs_200 = macro_trend.get('sma_50_vs_200', 'Neutral')
        price_above_200sma = macro_trend.get('price_above_200sma', False)
        golden_cross = macro_trend.get('golden_cross', False)
        death_cross = macro_trend.get('death_cross', False)
        long_term_price_change_pct = macro_trend.get('long_term_price_change_pct')
        
        # Build status indicators
        status_parts = []
        status_parts.append(f"Trend: {trend_direction}")
        
        # Add price change if available
        if long_term_price_change_pct is not None:
            change_sign = "+" if long_term_price_change_pct >= 0 else ""
            status_parts.append(f"365D Change: {change_sign}{self.format_utils.fmt(long_term_price_change_pct)}%")
        
        status_parts.append(f"SMA Alignment: {sma_alignment}")
        status_parts.append(f"50vs200 SMA: {sma_50_vs_200}")
        status_parts.append(f"Price>200SMA: {'✓' if price_above_200sma else '✗'}")
        
        if golden_cross:
            status_parts.append("Golden Cross Detected")
        elif death_cross:
            status_parts.append("Death Cross Detected")
            
        return f"## Macro Trend Analysis (365D):\n{' | '.join(status_parts)}"
    
    def format_coin_details_section(self, coin_details: Dict[str, Any], max_description_tokens: int = 256) -> str:
        """Format coin details into a structured section for prompt building
        
        Args:
            coin_details: Dictionary containing coin details from CryptoCompare API
            max_description_tokens: Maximum tokens allowed for description (default: 150)
            
        Returns:
            str: Formatted coin details section
        """
        if not coin_details:
            return ""
        
        section = "CRYPTOCURRENCY DETAILS:\n"
        
        # Basic information
        if coin_details.get("full_name"):
            section += f"- Full Name: {coin_details['full_name']}\n"
        if coin_details.get("coin_name"):
            section += f"- Project: {coin_details['coin_name']}\n"
        
        # Technical details
        algorithm = coin_details.get("algorithm", "N/A")
        proof_type = coin_details.get("proof_type", "N/A")
        if algorithm != "N/A" or proof_type != "N/A":
            section += f"- Algorithm: {algorithm}\n"
            section += f"- Proof Type: {proof_type}\n"
        
        # Taxonomy classifications
        taxonomy = coin_details.get("taxonomy", {})
        if taxonomy:
            section += "\nRegulatory Classifications:\n"
            if taxonomy.get("Access"):
                section += f"- Access Model: {taxonomy['Access']}\n"
            if taxonomy.get("FCA"):
                section += f"- UK FCA Classification: {taxonomy['FCA']}\n"
            if taxonomy.get("FINMA"):
                section += f"- Swiss FINMA Classification: {taxonomy['FINMA']}\n"
            if taxonomy.get("Industry"):
                section += f"- Industry Category: {taxonomy['Industry']}\n"
            if taxonomy.get("CollateralizedAsset"):
                collateral_text = "Yes" if taxonomy["CollateralizedAsset"] == "Yes" else "No"
                section += f"- Collateralized Asset: {collateral_text}\n"
        
        # Weiss ratings
        rating = coin_details.get("rating", {})
        if rating:
            weiss = rating.get("Weiss", {})
            if weiss:
                section += "\nWeiss Cryptocurrency Ratings:\n"
                section += "- Independent Rating System: Weiss Ratings is a US-based independent agency (since 1971)\n"
                section += "- Scale: A=Excellent (strong buy), B=Good (buy), C=Fair (hold/avoid), D=Weak (sell), E=Very weak (sell)\n"
                section += "- Modifiers: + indicates upper third of grade, - indicates lower third of grade\n"
                section += "- Two Components: Tech/Adoption (long-term potential) + Market Performance (short-term price patterns)\n"
                
                overall_rating = weiss.get("Rating")
                if overall_rating:
                    section += f"- Overall Rating: {overall_rating}\n"
                
                tech_rating = weiss.get("TechnologyAdoptionRating")
                if tech_rating:
                    section += f"- Technology/Adoption Grade: {tech_rating}\n"
                
                market_rating = weiss.get("MarketPerformanceRating")
                if market_rating:
                    section += f"- Market Performance Grade: {market_rating}\n"

        
        # Project description (keep last as it can be long)
        description = coin_details.get("description", "")
        if description:
            # Use token-based truncation instead of character-based
            description_tokens = self.token_counter.count_tokens(description)
            
            if description_tokens > max_description_tokens:
                # Truncate by sentences to maintain readability
                description = self._truncate_description_by_tokens(description, max_description_tokens)
                
            section += f"\nProject Description:\n{description}\n"
        
        return section
    
    def _truncate_description_by_tokens(self, description: str, max_tokens: int) -> str:
        """Truncate description by tokens while preserving sentence boundaries
        
        Args:
            description: The original description text
            max_tokens: Maximum tokens allowed
            
        Returns:
            str: Truncated description ending with complete sentences
        """
        # Split by sentences (simple approach)
        sentences = description.split('. ')
        truncated = ""
        
        for i, sentence in enumerate(sentences):
            # Add sentence with proper punctuation
            test_text = truncated + (sentence if sentence.endswith('.') else sentence + '.')
            if i < len(sentences) - 1:
                test_text += ' '
            
            # Check if adding this sentence would exceed token limit
            if self.token_counter.count_tokens(test_text) > max_tokens:
                # If even the first sentence is too long, truncate it directly
                if not truncated:
                    words = sentence.split()
                    for j, word in enumerate(words):
                        test_word_text = ' '.join(words[:j+1]) + '...'
                        if self.token_counter.count_tokens(test_word_text) > max_tokens:
                            if j == 0:  # Even first word is too long
                                return sentence[:50] + '...'
                            return ' '.join(words[:j]) + '...'
                    return sentence + '...'
                else:
                    # Add ellipsis to indicate truncation
                    return truncated.rstrip() + '...'
            
            truncated = test_text
        
        return truncated
