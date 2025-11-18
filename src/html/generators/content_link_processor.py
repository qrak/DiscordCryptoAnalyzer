"""
Content link processing utilities for HTML generation.
Handles adding links to indicators and news articles in Markdown content.
"""
import html
import re
from typing import Dict, List, Tuple


class ContentLinkProcessor:
    """Handles adding links to technical indicators and news articles."""
    
    def __init__(self, logger=None):
        self.logger = logger
        self.indicator_docs = self._initialize_indicator_docs()
    
    def _initialize_indicator_docs(self) -> Dict[str, str]:
        """Initialize the dictionary mapping indicator names to documentation links."""
        return {
            # Technical Indicators (Original)
            "RSI": "https://www.investopedia.com/terms/r/rsi.asp",
            "MACD": "https://www.investopedia.com/terms/m/macd.asp",
            "Bollinger Bands": "https://www.investopedia.com/terms/b/bollingerbands.asp",
            "Stochastic": "https://www.investopedia.com/terms/s/stochasticoscillator.asp",
            "Williams %R": "https://www.investopedia.com/terms/w/williamsr.asp",
            "ADX": "https://www.investopedia.com/terms/a/adx.asp",
            "Supertrend": "https://www.investopedia.com/supertrend-indicator-7976167",
            "Parabolic SAR": "https://www.investopedia.com/terms/p/parabolicindicator.asp",
            "ATR": "https://www.investopedia.com/terms/a/atr.asp",
            "MFI": "https://www.investopedia.com/terms/m/mfi.asp",
            "OBV": "https://www.investopedia.com/terms/o/onbalancevolume.asp",
            "CMF": "https://www.investopedia.com/ask/answers/071414/whats-difference-between-chaikin-money-flow-cmf-and-money-flow-index-mfi.asp",
            "Chaikin MF": "https://www.investopedia.com/ask/answers/071414/whats-difference-between-chaikin-money-flow-cmf-and-money-flow-index-mfi.asp",
            "Force Index": "https://www.investopedia.com/articles/trading/03/031203.asp",
            "Hurst Exponent": "https://www.investopedia.com/terms/r/rescaled-rangeanalysis.asp",
            "Z-Score": "https://www.investopedia.com/terms/z/zscore.asp",
            "Kurtosis": "https://www.investopedia.com/terms/k/kurtosis.asp",
            "VWAP": "https://www.investopedia.com/terms/v/vwap.asp",
            "TWAP": "https://en.wikipedia.org/wiki/Time-weighted_average_price",
            "Fear & Greed Index": "https://alternative.me/crypto/fear-and-greed-index/",
            "SMA": "https://www.investopedia.com/terms/s/sma.asp",
            "EMA": "https://www.investopedia.com/terms/e/ema.asp",
            "DI+": "https://www.investopedia.com/terms/p/positivedirectionalindicator.asp",
            "DI-": "https://www.investopedia.com/terms/n/negativedirectionalindicator.asp",
            "Stochastic %K": "https://www.investopedia.com/terms/s/stochasticoscillator.asp",
            "Stochastic %D": "https://www.investopedia.com/terms/s/stochasticoscillator.asp",
            "Volume": "https://www.investopedia.com/terms/v/volume.asp",
            "Fibonacci": "https://www.investopedia.com/terms/f/fibonacciretracement.asp",
            "Ichimoku Cloud": "https://www.investopedia.com/terms/i/ichimoku-cloud.asp",
            "CCI": "https://www.investopedia.com/terms/c/commoditychannelindex.asp",
            "TRIX": "https://www.investopedia.com/terms/t/trix.asp",
            "PPO": "https://www.investopedia.com/terms/p/ppo.asp",
            "RMI": "https://www.investopedia.com/terms/r/rmi.asp",
            "TSI": "https://www.investopedia.com/terms/t/tsi.asp",
            "PFE": "https://www.investopedia.com/terms/f/fractal.asp",
            "Coppock Curve": "https://www.investopedia.com/terms/c/coppockcurve.asp",
            "Ultimate Oscillator": "https://www.investopedia.com/terms/u/ultimateoscillator.asp",
            "Vortex Indicator": "https://www.investopedia.com/terms/v/vortex-indicator-vi.asp",
            "Chandelier Exit": "https://www.investopedia.com/terms/c/chandelierexit.asp",
            "KST": "https://www.investopedia.com/terms/k/know-sure-thing-kst.asp",
            "Tenkan-sen": "https://www.investopedia.com/terms/i/ichimoku-cloud.asp",
            "Kijun-sen": "https://www.investopedia.com/terms/i/ichimoku-cloud.asp",
            "Senkou A": "https://www.investopedia.com/terms/i/ichimoku-cloud.asp",
            "Senkou B": "https://www.investopedia.com/terms/i/ichimoku-cloud.asp",
            "Weiss Rating": "https://weissratings.com/en/rating-definitions",
            "Weiss Ratings": "https://weissratings.com/en/rating-definitions",
            "Weiss Cryptocurrency Rating": "https://weissratings.com/en/rating-definitions",
            "Weiss Cryptocurrency Ratings": "https://weissratings.com/en/rating-definitions",
            "Weiss Crypto Rating": "https://weissratings.com/en/rating-definitions",
            "Weiss Crypto Ratings": "https://weissratings.com/en/rating-definitions",
            
            # Chart Patterns (NEW)
            "Head and Shoulders": "https://www.investopedia.com/terms/h/head-shoulders.asp",
            "Head & Shoulders": "https://www.investopedia.com/terms/h/head-shoulders.asp",
            "Double Top": "https://www.investopedia.com/terms/d/double-top-and-bottom.asp",
            "Double Bottom": "https://www.investopedia.com/terms/d/double-top-and-bottom.asp",
            "Triple Top": "https://www.investopedia.com/terms/t/tripletop.asp",
            "Triple Bottom": "https://www.investopedia.com/terms/t/triplebottom.asp",
            "Flag": "https://www.investopedia.com/terms/f/flag.asp",
            "Pennant": "https://www.investopedia.com/terms/p/pennant.asp",
            "Triangle": "https://www.investopedia.com/articles/technical/03/091003.asp",
            "Ascending Triangle": "https://www.investopedia.com/terms/a/ascendingtriangle.asp",
            "Descending Triangle": "https://www.investopedia.com/terms/d/descendingtriangle.asp",
            "Symmetrical Triangle": "https://www.investopedia.com/terms/s/symmetricaltriangle.asp",
            "Wedge": "https://www.investopedia.com/terms/w/wedge.asp",
            "Rising Wedge": "https://www.investopedia.com/terms/r/rising-wedge.asp",
            "Falling Wedge": "https://www.investopedia.com/terms/f/falling-wedge.asp",
            "Cup and Handle": "https://www.investopedia.com/terms/c/cupandhandle.asp",
            "Rounding Bottom": "https://www.investopedia.com/terms/r/roundingbottom.asp",
            "Channel": "https://www.investopedia.com/articles/trading/05/020905.asp",
            
            # Market Structure & Trading Concepts (NEW)
            "Support": "https://www.investopedia.com/terms/s/support.asp",
            "Resistance": "https://www.investopedia.com/terms/r/resistance.asp",
            "Trend": "https://www.investopedia.com/terms/t/trend.asp",
            "Uptrend": "https://www.investopedia.com/terms/u/uptrend.asp",
            "Downtrend": "https://www.investopedia.com/terms/d/downtrend.asp",
            "Breakout": "https://www.investopedia.com/articles/trading/08/trading-breakouts.asp",
            "Breakdown": "https://www.investopedia.com/terms/b/breakdown.asp",
            "Consolidation": "https://www.investopedia.com/terms/c/consolidation.asp",
            "Retracement": "https://www.investopedia.com/terms/r/retracement.asp",
            "Reversal": "https://www.investopedia.com/terms/r/reversal.asp",
            "Correction": "https://www.investopedia.com/terms/c/correction.asp",
            "Rally": "https://www.investopedia.com/terms/r/rally.asp",
            "Pullback": "https://www.investopedia.com/terms/p/pullback.asp",
            "Momentum": "https://www.investopedia.com/terms/m/momentum.asp",
            "Volatility": "https://www.investopedia.com/terms/v/volatility.asp",
            "Liquidity": "https://www.investopedia.com/terms/l/liquidity.asp",
            "Market Cap": "https://www.investopedia.com/terms/m/marketcapitalization.asp",
            "Market Capitalization": "https://www.investopedia.com/terms/m/marketcapitalization.asp",
            "Trading Volume": "https://www.investopedia.com/terms/v/volumeoftrade.asp",
            "Order Book": "https://www.investopedia.com/terms/o/order-book.asp",
            "Bid": "https://www.investopedia.com/terms/b/bid.asp",
            "Ask": "https://www.investopedia.com/terms/a/ask.asp",
            "Spread": "https://www.investopedia.com/terms/s/spread.asp",
            "Liquidation": "https://www.investopedia.com/terms/l/liquidationlevel.asp",
            "Margin Call": "https://www.investopedia.com/terms/m/margincall.asp",
            "Leverage": "https://www.investopedia.com/terms/l/leverage.asp",
            "Long Position": "https://www.investopedia.com/terms/l/long.asp",
            "Short Position": "https://www.investopedia.com/terms/s/short.asp",
            "Stop Loss": "https://www.investopedia.com/terms/s/stop-lossorder.asp",
            "Take Profit": "https://www.investopedia.com/terms/t/take-profitorder.asp",
            "Limit Order": "https://www.investopedia.com/terms/l/limitorder.asp",
            "Market Order": "https://www.investopedia.com/terms/m/marketorder.asp",
            "Candlestick": "https://www.investopedia.com/terms/c/candlestick.asp",
            "Doji": "https://www.investopedia.com/terms/d/doji.asp",
            "Hammer": "https://www.investopedia.com/terms/h/hammer.asp",
            "Shooting Star": "https://www.investopedia.com/terms/s/shootingstar.asp",
            "Engulfing": "https://www.investopedia.com/terms/b/bullishengulfingpattern.asp",
            "Divergence": "https://www.investopedia.com/terms/d/divergence.asp",
            "Convergence": "https://www.investopedia.com/terms/c/convergence.asp",
            "Oversold": "https://www.investopedia.com/terms/o/oversold.asp",
            "Overbought": "https://www.investopedia.com/terms/o/overbought.asp",
            "Golden Cross": "https://www.investopedia.com/terms/g/goldencross.asp",
            "Death Cross": "https://www.investopedia.com/terms/d/deathcross.asp",
            
            # Market Psychology & Sentiment (NEW)
            "FOMO": "https://www.investopedia.com/deal-with-crypto-fomo-6455103",
            "Fear": "https://alternative.me/crypto/fear-and-greed-index/",
            "Greed": "https://alternative.me/crypto/fear-and-greed-index/",
            "Panic Selling": "https://www.investopedia.com/terms/p/panicselling.asp",
            "Capitulation": "https://www.investopedia.com/terms/c/capitulation.asp",
            
            # Market Participants & Structure (NEW)
            "Whale": "https://www.investopedia.com/terms/b/bitcoin-whale.asp",
            "Crypto Whale": "https://www.investopedia.com/terms/b/bitcoin-whale.asp",
            "Bitcoin Whale": "https://www.investopedia.com/terms/b/bitcoin-whale.asp",
            "Institutional Investors": "https://www.investopedia.com/terms/i/institutionalinvestor.asp",
            "Retail Investors": "https://www.investopedia.com/retail-investors-are-back-in-crypto-markets-5095407",
            "Retail": "https://www.investopedia.com/retail-investors-are-back-in-crypto-markets-5095407",
            "Institutional": "https://www.investopedia.com/terms/i/institutionalinvestor.asp",
            
            # Crypto-Specific Concepts (NEW)
            "Altcoin": "https://www.investopedia.com/terms/a/altcoin.asp",
            "Altcoins": "https://www.investopedia.com/terms/a/altcoin.asp",
            "Bitcoin Dominance": "https://www.investopedia.com/bitcoin-dominance-of-crypto-market-reaches-highest-level-since-2021-8744927",
            "Dominance": "https://www.investopedia.com/bitcoin-dominance-of-crypto-market-reaches-highest-level-since-2021-8744927",
            "Deleveraging": "https://www.investopedia.com/terms/d/deleverage.asp",
            "Futures": "https://www.investopedia.com/terms/f/futures.asp",
            "Crypto Futures": "https://www.investopedia.com/terms/f/futures.asp",
            "Bull Market": "https://www.investopedia.com/insights/digging-deeper-bull-and-bear-markets/",
            "Bear Market": "https://www.investopedia.com/terms/b/bearmarket.asp",
            "Bullish": "https://www.investopedia.com/insights/digging-deeper-bull-and-bear-markets/",
            "Bearish": "https://www.investopedia.com/terms/b/bearmarket.asp",
            
            # Distribution & Accumulation (NEW)
            "Distribution": "https://www.investopedia.com/articles/trading/08/stock-cycle-trend-price.asp",
            "Accumulation": "https://www.investopedia.com/articles/trading/08/accumulation-distribution-line.asp",
            "Accumulation Phase": "https://www.investopedia.com/articles/trading/08/stock-cycle-trend-price.asp",
            "Distribution Phase": "https://www.investopedia.com/articles/trading/08/stock-cycle-trend-price.asp",
            
            # Trading Pressure & Flow (NEW)
            "Buy Pressure": "https://www.investopedia.com/terms/v/volume-price-trend-indicator.asp",
            "Sell Pressure": "https://www.investopedia.com/terms/v/volume-price-trend-indicator.asp",
            "Buying Pressure": "https://www.investopedia.com/terms/v/volume-price-trend-indicator.asp",
            "Selling Pressure": "https://www.investopedia.com/terms/v/volume-price-trend-indicator.asp"
        }
    
    def add_indicator_links(self, content: str) -> str:
        """Add links to technical indicators in the Markdown content."""
        try:
            for indicator, link in self.indicator_docs.items():
                content = self._add_single_indicator_link(content, indicator, link)
            return content
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error adding indicator links: {e}")
            return content
    
    def _add_single_indicator_link(self, content: str, indicator: str, link: str) -> str:
        """Add a link for a single indicator in the content."""
        safe_indicator = re.escape(indicator)
        
        if "%" in safe_indicator:
            # Special case for indicators with % - like Williams %R, Stochastic %K
            pattern = f"({safe_indicator})"
        else:
            # Normal case with word boundaries
            pattern = f"\\b({safe_indicator})\\b"
        
        return re.sub(
            pattern,
            f"[\\1]({link})",
            content,
            flags=re.IGNORECASE
        )
    
    def add_news_links(self, content: str, article_urls: dict) -> str:
        """Add links to referenced news articles in the Markdown content."""
        try:
            if not article_urls:
                return content

            existing_links = self._find_existing_links(content)
            validated_urls = self._validate_article_urls(article_urls)
            
            if not validated_urls:
                return content

            matches_to_process = self._find_link_matches(content, validated_urls, existing_links)
            return self._apply_link_replacements(content, matches_to_process)

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error adding news links to Markdown: {e}")
            return content
    
    def _find_existing_links(self, content: str) -> List[Tuple[int, int]]:
        """Find existing markdown links to avoid nesting."""
        return [(m.start(), m.end()) for m in re.finditer(r"\[([^]]+)]\(([^)]+)\)", content)]

    def _validate_article_urls(self, article_urls: dict) -> dict:
        """Validate and sanitize article URLs: accept HTTPS only."""
        validated_urls = {}
        for title, url in article_urls.items():
            if isinstance(url, str):
                if url.startswith('https://'):
                    safe_title = str(title) if title is not None else ""
                    validated_urls[safe_title] = url
                else:
                    if self.logger:
                        self.logger.debug(f"Non-HTTPS URL skipped: {url}")
            else:
                if self.logger:
                    self.logger.debug(f"Invalid URL skipped: {url}")
        return validated_urls
    
    def _find_link_matches(self, content: str, validated_urls: dict, existing_links: List[Tuple[int, int]]) -> List[dict]:
        """Find all potential link matches for titles and keywords."""
        def is_inside_link(pos):
            return any(start < pos < end for start, end in existing_links)
        
        matches = []
        matches.extend(self._find_title_matches(content, validated_urls, is_inside_link))
        matches.extend(self._find_keyword_matches(content, validated_urls, is_inside_link))
        return matches
    
    def _find_title_matches(self, content: str, validated_urls: dict, is_inside_link) -> List[dict]:
        """Find matches for exact article titles."""
        matches = []
        for title, url in validated_urls.items():
            if not title:
                continue
            safe_title_pattern = re.escape(title)
            pattern = re.compile(rf"\b({safe_title_pattern})\b", re.IGNORECASE)
            for match in pattern.finditer(content):
                if not is_inside_link(match.start()):
                    link_text = match.group(1)
                    title_attr = "Read full article"
                    replacement = f'[{link_text}]({url} "{title_attr}")'
                    matches.append({
                        "start": match.start(),
                        "end": match.end(),
                        "replacement": replacement,
                        "priority": 2
                    })
        return matches
    
    def _find_keyword_matches(self, content: str, validated_urls: dict, is_inside_link) -> List[dict]:
        """Find matches for keywords that appear in article titles."""
        matches = []
        # Dynamic keywords from categories and known tickers
        keywords = self._get_dynamic_keywords()
        linked_urls_for_keywords = set()

        for keyword in keywords:
            for title, url in validated_urls.items():
                if keyword.lower() in title.lower() and url not in linked_urls_for_keywords:
                    pattern = re.compile(rf"(\b{re.escape(keyword)}['s]?\b)", re.IGNORECASE)
                    for match in pattern.finditer(content):
                        if not is_inside_link(match.start()):
                            link_text = match.group(1)
                            title_attr = f"Source: {html.escape(title)}"
                            replacement = f'[{link_text}]({url} "{title_attr}")'
                            matches.append({
                                "start": match.start(),
                                "end": match.end(),
                                "replacement": replacement,
                                "priority": 2
                            })
                            linked_urls_for_keywords.add(url)
        return matches
    
    def _get_dynamic_keywords(self) -> List[str]:
        """Get dynamic keywords from known tickers and important categories."""
        keywords = []
        
        # Add hardcoded important terms that are always relevant
        static_keywords = ["Trump", "SEC", "regulation", "policy", "options expiry", "Fear & Greed", "stablecoin"]
        keywords.extend(static_keywords)
        
        # Try to load known tickers from file
        try:
            import os
            import json
            from src.utils.loader import config
            
            tickers_file = os.path.join(config.DATA_DIR, "known_tickers.json")
            if os.path.exists(tickers_file):
                with open(tickers_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    tickers = data.get('tickers', [])
                    keywords.extend(tickers)
                    
                    # Add common names for major cryptocurrencies
                    ticker_names = {
                        'BTC': 'Bitcoin',
                        'ETH': 'Ethereum', 
                        'XRP': 'Ripple',
                        'ADA': 'Cardano',
                        'DOT': 'Polkadot',
                        'AVAX': 'Avalanche',
                        'MATIC': 'Polygon',
                        'LTC': 'Litecoin',
                        'LINK': 'Chainlink',
                        'UNI': 'Uniswap',
                        'ATOM': 'Cosmos'
                    }
                    for ticker in tickers:
                        if ticker in ticker_names:
                            keywords.append(ticker_names[ticker])
        except Exception:
            # Fallback to basic set if loading fails
            fallback_keywords = ["Bitcoin", "ETH", "BTC", "XRP", "Cardano", "Conflux"]
            keywords.extend(fallback_keywords)
        
        return list(set(keywords))  # Remove duplicates
    
    def _apply_link_replacements(self, content: str, matches_to_process: List[dict]) -> str:
        """Apply link replacements to content, avoiding overlaps."""
        matches_to_process.sort(key=lambda x: (x['start'], -x.get('priority', 1)))

        current_pos = 0
        final_content = ""
        processed_ranges = []

        for match_info in matches_to_process:
            is_overlapping = any(
                max(match_info['start'], p_start) < min(match_info['end'], p_end)
                for p_start, p_end in processed_ranges
            )

            if not is_overlapping:
                final_content += content[current_pos:match_info['start']]
                final_content += match_info['replacement']
                current_pos = match_info['end']
                processed_ranges.append((match_info['start'], match_info['end']))

        final_content += content[current_pos:]
        return final_content
