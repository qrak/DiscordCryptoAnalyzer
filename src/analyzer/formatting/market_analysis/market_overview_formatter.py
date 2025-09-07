"""
Market overview data formatting for prompt building system.
Handles formatting of market overview data, global metrics, dominance, etc.
"""

from typing import Any, Dict, List, Optional

from src.logger.logger import Logger


class MarketOverviewFormatter:
    """Formats market overview data for prompt inclusion."""
    
    def __init__(self, logger: Optional[Logger] = None):
        """Initialize the market overview formatter.
        
        Args:
            logger: Optional logger instance for debugging
        """
        self.logger = logger
    
    def format_market_overview(self, market_overview: Optional[Dict[str, Any]]) -> str:
        """Format market overview data into a readable section.
        
        Args:
            market_overview: Market overview data dictionary
            
        Returns:
            str: Formatted market overview section
        """
        if not market_overview:
            return ""
            
        sections = [
            "## MARKET OVERVIEW DATA\n",
            "The following market data should be incorporated into your analysis:\n"
        ]
        
        # Add different overview sections
        sections.extend(self._build_top_coins_section(market_overview))
        sections.extend(self._build_global_metrics_section(market_overview))
        sections.extend(self._build_dominance_section(market_overview))
        sections.extend(self._build_market_stats_section(market_overview))
        
        # Add closing note
        sections.append("\n**Note:** When formulating your analysis, explicitly incorporate these market metrics to provide context on how the analyzed asset relates to broader market conditions.\n")
        
        return "\n".join(sections)

    def _build_top_coins_section(self, overview: Dict[str, Any]) -> List[str]:
        """Build top cryptocurrencies performance section.
        
        Args:
            overview: Market overview data
            
        Returns:
            List[str]: Formatted lines for top coins section
        """
        if "top_coins" not in overview:
            return []
            
        sections = [
            "### Top Cryptocurrencies Performance:\n",
            "| Coin | Price | 24h Change | 24h Volume |",
            "|------|-------|------------|------------|"
        ]
        
        for coin, data in overview["top_coins"].items():
            price = f"${data.get('price', 0):,.2f}"
            change = f"{data.get('change24h', 0):.2f}%"
            volume = f"{data.get('volume24h', 0):,.2f}"
            sections.append(f"| {coin} | {price} | {change} | {volume} |")
            
        sections.append("")  # Empty line after table
        return sections

    def _build_global_metrics_section(self, overview: Dict[str, Any]) -> List[str]:
        """Build global market metrics section.
        
        Args:
            overview: Market overview data
            
        Returns:
            List[str]: Formatted lines for global metrics section
        """
        sections = ["### Global Market Metrics:\n"]
        
        # Market cap
        if "market_cap" in overview:
            mcap = overview["market_cap"]
            total_mcap = f"${mcap.get('total_usd', 0):,.2f}" if "total_usd" in mcap else "N/A"
            mcap_change = f"{mcap.get('change_24h', 0):.2f}%" if "change_24h" in mcap else "N/A"
            sections.append(f"- Total Market Cap: {total_mcap} ({mcap_change} 24h change)")
            
        # Volume
        if "volume" in overview and "total_usd" in overview["volume"]:
            volume = f"${overview['volume']['total_usd']:,.2f}"
            sections.append(f"- 24h Trading Volume: {volume}")
            
        return sections

    def _build_dominance_section(self, overview: Dict[str, Any]) -> List[str]:
        """Build market dominance section.
        
        Args:
            overview: Market overview data
            
        Returns:
            List[str]: Formatted lines for dominance section
        """
        if "dominance" not in overview:
            return []
            
        sections = ["\n### Market Dominance:\n"]
        
        for coin, value in overview["dominance"].items():
            if isinstance(value, (int, float)):
                sections.append(f"- {coin.upper()}: {value:.2f}%")
            else:
                sections.append(f"- {coin.upper()}: {value}%")
                
        return sections

    def _build_market_stats_section(self, overview: Dict[str, Any]) -> List[str]:
        """Build general market statistics section.
        
        Args:
            overview: Market overview data
            
        Returns:
            List[str]: Formatted lines for market stats section
        """
        if "stats" not in overview:
            return []
            
        stats = overview["stats"]
        active_coins = stats.get("active_coins", "N/A")
        active_markets = stats.get("active_markets", "N/A")
        
        return [
            f"\n- Active Cryptocurrencies: {active_coins}",
            f"- Active Markets: {active_markets}"
        ]
