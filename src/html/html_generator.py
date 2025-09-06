"""
HTML generator utility for creating detailed analysis reports.
"""
import html
import re
from datetime import datetime, timedelta
from pathlib import Path

import markdown

from src.html.html_templates import get_analysis_template, get_error_template
from src.html.chart_generator import ChartGenerator


class AnalysisHtmlGenerator:
    """Generates HTML files for detailed analysis"""

    def __init__(self, temp_dir: str = 'temp_analysis/', logger=None):
        self.logger = logger
        self.temp_dir = temp_dir
        self.chart_generator = ChartGenerator()

        # Create temp directory if it doesn't exist
        Path(self.temp_dir).mkdir(parents=True, exist_ok=True)

        # Dictionary mapping indicator names to documentation links
        self.indicator_docs = {
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
            # Adding missing indicators used in advanced analysis
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

    def generate_html_content(
        self, 
        title: str, 
        content: str, 
        article_urls: dict = None,
        ohlcv_data: dict = None
    ) -> str:
        """Generate HTML content as a string without writing to disk
        
        Args:
            title: The title of the analysis
            content: The analysis content (expected in Markdown format)
            article_urls: Dictionary of article URLs
            ohlcv_data: Dictionary containing OHLCV data, technical indicators, and patterns
        """
        try:
            if not title or not content:
                self.logger.error("Title or content missing")
                return ""

            escaped_title = html.escape(title)
            
            # First, add indicator links to the Markdown content
            enriched_content = self._add_indicator_links(content)
            
            # Next, add news links to the Markdown content if we have article URLs
            if article_urls:
                enriched_content = self._add_news_links(enriched_content, article_urls)
            
            # Then convert the enriched Markdown content to HTML
            html_analysis_content = markdown.markdown(
                enriched_content,
                extensions=['fenced_code', 'tables', 'nl2br']
            )

            # Generate chart HTML if we have OHLCV data
            chart_html = ""
            if ohlcv_data and 'ohlcv' in ohlcv_data:
                try:
                    # Generate the main OHLCV chart with indicators
                    chart_html = self._generate_chart_html(ohlcv_data)
                except Exception as e:
                    self.logger.error(f"Failed to generate chart: {e}")
                    chart_html = f"<p><em>Chart generation failed: {html.escape(str(e))}</em></p>"

            html_content = self._get_styled_html(
                escaped_title,
                html_analysis_content,
                article_urls,
                chart_html
            )

            return html_content
        except Exception as e:
            self.logger.error(f"Failed to create HTML content: {e}")
            return f"<p>Error generating analysis: {html.escape(str(e))}</p>"

    def _generate_chart_html(self, ohlcv_data: dict) -> str:
        """Generate HTML for interactive chart
        
        Args:
            ohlcv_data: Dictionary containing OHLCV data and related information
            
        Returns:
            HTML string with the interactive chart
        """
        try:
            ohlcv = ohlcv_data.get('ohlcv')
            technical_history = ohlcv_data.get('technical_history')
            patterns = ohlcv_data.get('patterns')
            pair_symbol = ohlcv_data.get('symbol', '')
            timeframe = ohlcv_data.get('timeframe', '1h')
            
            if ohlcv is None or len(ohlcv) == 0:
                return "<p><em>No OHLCV data available for chart</em></p>"
                
            # Generate the chart
            chart_html = self.chart_generator.create_ohlcv_chart(
                ohlcv=ohlcv,
                technical_history=technical_history,
                patterns=patterns,
                pair_symbol=pair_symbol,
                timeframe=timeframe
            )
            
            # Wrap the chart in a container for styling
            return f"""
            <div class="chart-container">
                {chart_html}
            </div>
            """
        except Exception as e:
            self.logger.error(f"Chart generation error: {e}")
            return f"<p><em>Chart generation failed: {html.escape(str(e))}</em></p>"

    def _add_indicator_links(self, content: str) -> str:
        """Add links to technical indicators in the Markdown content"""
        try:
            # For each indicator in our dictionary
            for indicator, link in self.indicator_docs.items():
                # Escape special characters in indicator name for regex
                safe_indicator = re.escape(indicator)
                
                # Create a pattern that matches the indicator, being careful about word boundaries
                if "%" in safe_indicator:
                    # Special case for indicators with % - like Williams %R, Stochastic %K
                    pattern = f"({safe_indicator})"
                else:
                    # Normal case with word boundaries
                    pattern = f"\\b({safe_indicator})\\b"
                
                # Find all instances (non-overlapping) of the indicator in the content
                content = re.sub(
                    pattern,
                    f"[\\1]({link})",
                    content,
                    flags=re.IGNORECASE
                )
            
            return content
        except Exception as e:
            self.logger.error(f"Error adding indicator links: {e}")
            return content

    def _add_news_links(self, content: str, article_urls: dict) -> str:
        """Add links to referenced news articles in the Markdown content."""
        try:
            if not article_urls:
                return content

            # Get existing links to avoid nesting
            existing_links = self._find_existing_links(content)
            
            # Validate URLs
            validated_urls = self._validate_article_urls(article_urls)
            if not validated_urls:
                return content

            # Find matches to process
            matches_to_process = self._find_link_matches(content, validated_urls, existing_links)
            
            # Process matches and return final content
            return self._apply_link_replacements(content, matches_to_process)

        except Exception as e:
            self.logger.error(f"Error adding news links to Markdown: {e}")
            return content
    
    def _find_existing_links(self, content: str) -> list:
        """Find existing markdown links to avoid nesting"""
        return [(m.start(), m.end()) for m in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", content)]
    
    def _validate_article_urls(self, article_urls: dict) -> dict:
        """Validate and sanitize article URLs"""
        validated_urls = {}
        for title, url in article_urls.items():
            if isinstance(url, str) and (url.startswith('http://') or url.startswith('https://')):
                safe_title = str(title) if title is not None else ""
                validated_urls[safe_title] = url
            else:
                self.logger.warning(f"Invalid URL skipped: {url}")
        return validated_urls
    
    def _find_link_matches(self, content: str, validated_urls: dict, existing_links: list) -> list:
        """Find all potential link matches for titles and keywords"""
        matches_to_process = []
        
        # Check if position is inside an existing link
        def is_inside_link(pos):
            for start, end in existing_links:
                if start < pos < end:
                    return True
            return False
        
        # Add matches for exact title matches
        matches_to_process.extend(
            self._find_title_matches(content, validated_urls, is_inside_link)
        )
        
        # Add matches for keyword-based linking
        matches_to_process.extend(
            self._find_keyword_matches(content, validated_urls, is_inside_link)
        )
        
        return matches_to_process
    
    def _find_title_matches(self, content: str, validated_urls: dict, is_inside_link) -> list:
        """Find matches for exact article titles"""
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
    
    def _find_keyword_matches(self, content: str, validated_urls: dict, is_inside_link) -> list:
        """Find matches for keywords that appear in article titles"""
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
    
    def _apply_link_replacements(self, content: str, matches_to_process: list) -> str:
        """Apply link replacements to content, avoiding overlaps"""
        # Sort matches by position and priority
        matches_to_process.sort(key=lambda x: (x['start'], -x.get('priority', 1)))

        current_pos = 0
        final_content = ""
        processed_ranges = []

        for match_info in matches_to_process:
            # Check for overlaps with already processed ranges
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

    def _get_styled_html(self, title: str, html_analysis_content: str, article_urls=None, chart_html="") -> str:
        """Generate styled HTML content using pre-rendered HTML analysis"""
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            expiry_time = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")

            sources_section = ""
            if article_urls and len(article_urls) > 0:
                sources_section = """
                <div class="resources">
                    <h4>📰 Sources & Resources</h4>
                    <ul>
                """
                for title_text, url in article_urls.items():
                     if isinstance(url, str) and (url.startswith('http://') or url.startswith('https://')):
                        safe_title = html.escape(str(title_text) if title_text is not None else "Source")
                        sources_section += f'<li><a href="{url}" target="_blank">{safe_title}</a></li>'

                sources_section += """
                    </ul>
                </div>
                """
            else:
                self.logger.warning("No article URLs provided for sources section")

            final_html_structure = html_analysis_content

            if chart_html:
                charts_html_section = f"""
                <div class="chart-section">
                    <div class="market-chart">
                        <h3>📈 Market Chart</h3>
                        {chart_html}
                    </div>
                </div>
                """
                final_html_structure = f"""
                {charts_html_section}
                <div class="analysis-details">
                    <h3>📊 Analysis Details</h3>
                    {html_analysis_content}
                </div>
                """
            else:
                final_html_structure = f"""
                <div class="analysis-details">
                    <h3>📊 Analysis Details</h3>
                    {html_analysis_content}
                </div>
                """

            return get_analysis_template(
                title=title,
                content=final_html_structure,
                sources_section=sources_section,
                current_time=current_time,
                expiry_time=expiry_time
            )
        except Exception as e:
            self.logger.error(f"Error generating HTML template: {e}")
            return get_error_template(html.escape(str(e)))