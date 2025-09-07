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
            "Senkou B": "https://www.investopedia.com/terms/i/ichimoku-cloud.asp"
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
        keywords = ["Trump", "SEC", "regulation", "policy", "options expiry", "Fear & Greed", 
                   "Bitcoin", "ETH", "stablecoin", "XRP", "Cardano", "Conflux", "BTC"]
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
