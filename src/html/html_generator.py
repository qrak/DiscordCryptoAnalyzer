"""
HTML generator utility for creating detailed analysis reports.
"""
import html
from pathlib import Path
from src.html.generators.template_processor import TemplateProcessor
from src.html.generators.chart_section_generator import ChartSectionGenerator
from src.html.generators.content_link_processor import ContentLinkProcessor
from src.html.generators.content_formatter import ContentFormatter
from src.utils.format_utils import FormatUtils


class AnalysisHtmlGenerator:
    """Generates HTML files for detailed analysis using specialized components."""
    
    def __init__(self, temp_dir: str = 'temp_analysis/', logger=None):
        self.logger = logger
        self.temp_dir = temp_dir
        # Format utilities instance for number/timestamp formatting
        self.format_utils = FormatUtils()

        # Initialize specialized components
        self.template_processor = TemplateProcessor(logger)
        self.chart_generator = ChartSectionGenerator(logger)
        self.link_processor = ContentLinkProcessor(logger)
        self.content_formatter = ContentFormatter(logger)

        # Create temp directory if it doesn't exist
        Path(self.temp_dir).mkdir(parents=True, exist_ok=True)

    def generate_html_content(
        self, 
        title: str, 
        content: str, 
        article_urls: dict = None,
        ohlcv_data: dict = None,
        discord_analysis: dict = None
    ) -> str:
        """
        Generate HTML content as a string without writing to disk.
        
        Args:
            title: The title of the analysis
            content: The analysis content (expected in Markdown format)
            article_urls: Dictionary of article URLs
            ohlcv_data: Dictionary containing OHLCV data, technical indicators, and patterns
            discord_analysis: Dictionary containing Discord analysis data
        """
        try:
            # Validate inputs
            if not self.content_formatter.validate_content_inputs(title, content):
                return ""

            escaped_title = html.escape(title)
            
            # Process content through the pipeline
            enriched_content = self._enrich_content_with_links(content, article_urls)
            html_analysis_content = self.content_formatter.process_markdown_content(enriched_content)
            chart_html = self._generate_chart_section(ohlcv_data)
            discord_summary_html = self._generate_discord_summary_section(discord_analysis)

            # Generate final HTML
            html_content = self.template_processor.generate_styled_html(
                escaped_title,
                html_analysis_content,
                article_urls,
                chart_html,
                discord_summary_html
            )

            return html_content
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to create HTML content: {e}")
            return f"<p>Error generating analysis: {html.escape(str(e))}</p>"

    def _enrich_content_with_links(self, content: str, article_urls: dict) -> str:
        """Enrich content with indicator and news links."""
        # First, add indicator links to the Markdown content
        enriched_content = self.link_processor.add_indicator_links(content)
        
        # Next, add news links to the Markdown content if we have article URLs
        if article_urls:
            enriched_content = self.link_processor.add_news_links(enriched_content, article_urls)
        
        return enriched_content

    def _generate_chart_section(self, ohlcv_data: dict) -> str:
        """Generate chart HTML if OHLCV data is available."""
        if not ohlcv_data or 'ohlcv' not in ohlcv_data:
            return ""
        
        try:
            return self.chart_generator.generate_chart_html(ohlcv_data)
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to generate chart: {e}")
            return f"<p><em>Chart generation failed: {html.escape(str(e))}</em></p>"

    def _generate_discord_summary_section(self, discord_analysis: dict) -> str:
        """Generate Discord summary HTML if analysis data is available."""
        if not discord_analysis:
            return ""
        
        try:
            return self._format_discord_analysis_html(discord_analysis)
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to generate Discord summary: {e}")
            return f"<p><em>Discord summary generation failed: {html.escape(str(e))}</em></p>"

    def _format_discord_analysis_html(self, discord_analysis: dict) -> str:
        """Format Discord analysis data into HTML."""
        analysis = discord_analysis.get("analysis", {})
        symbol = discord_analysis.get("symbol", "Unknown")
        language = discord_analysis.get("language", "")
        
        # Build the HTML structure with collapsible functionality
        html_parts = ['<div class="discord-summary">']
        
        # Collapsible header
        language_suffix = f" ({language})" if language else ""
        html_parts.append('<div class="discord-summary-header">')
        html_parts.append(f'<h3>Discord Analysis Summary - {html.escape(symbol)}{html.escape(language_suffix)}</h3>')
        html_parts.append('<span class="collapse-icon">▼</span>')
        html_parts.append('</div>')
        
        html_parts.append('<div class="discord-summary-content collapsed">')
        
        # Summary description
        summary = analysis.get("summary", "")
        if summary:
            html_parts.append(f'<div class="discord-summary-description">{html.escape(summary)}</div>')
        
        # Core metrics
        self._add_core_metrics_html(html_parts, analysis)
        
        # Timeframes
        self._add_timeframes_html(html_parts, analysis)
        
        # News summary
        self._add_news_summary_html(html_parts, analysis)
        
        # Price scenarios
        self._add_price_scenarios_html(html_parts, analysis)
        
        # Support and resistance levels
        self._add_key_levels_html(html_parts, analysis)
        
        html_parts.append('</div>')  # Close discord-summary-content
        html_parts.append('</div>')  # Close discord-summary
        
        return '\n'.join(html_parts)

    def _add_core_metrics_html(self, html_parts: list, analysis: dict) -> None:
        """Add core metrics to the Discord summary HTML."""
        metrics = [
            ("Trend", analysis.get("observed_trend", "NEUTRAL"), self._get_trend_class),
            ("Trend Strength", f"{analysis.get('trend_strength', 0)}/100", None),
            ("Analysis Confidence", f"{analysis.get('confidence_score', 0)}/100", None),
            ("Technical Bias", analysis.get("technical_bias", "NEUTRAL"), self._get_trend_class),
            ("Market Structure", analysis.get("market_structure", "NEUTRAL"), self._get_trend_class),
        ]
        
        # Add risk ratio if available
        risk_ratio = analysis.get("risk_ratio")
        if risk_ratio is not None:
            metrics.append(("Risk/Reward Ratio", f"{risk_ratio:.2f}", None))
        
        for name, value, class_func in metrics:
            css_class = class_func(value) if class_func else ""
            html_parts.append(f'<div class="discord-field">')
            html_parts.append(f'<span class="discord-field-name">{html.escape(name)}</span>')
            html_parts.append(f'<span class="discord-field-value {css_class}">{html.escape(str(value))}</span>')
            html_parts.append('</div>')

    def _add_timeframes_html(self, html_parts: list, analysis: dict) -> None:
        """Add timeframes analysis to the Discord summary HTML."""
        timeframes = analysis.get("timeframes", {})
        if not timeframes:
            return
        
        html_parts.append('<div class="discord-section-title" data-icon="⏱️">Timeframe Analysis</div>')
        html_parts.append('<div class="discord-timeframes">')
        
        timeframe_data = [
            ("Short-term", timeframes.get("short_term", "NEUTRAL")),
            ("Medium-term", timeframes.get("medium_term", "NEUTRAL")),
            ("Long-term", timeframes.get("long_term", "NEUTRAL"))
        ]
        
        for label, value in timeframe_data:
            css_class = self._get_trend_class(value)
            html_parts.append('<div class="discord-timeframe">')
            html_parts.append(f'<div class="discord-timeframe-label">{html.escape(label)}</div>')
            html_parts.append(f'<div class="discord-timeframe-value {css_class}">{html.escape(value)}</div>')
            html_parts.append('</div>')
        
        html_parts.append('</div>')

    def _add_news_summary_html(self, html_parts: list, analysis: dict) -> None:
        """Add news summary to the Discord summary HTML."""
        news_summary = analysis.get("news_summary")
        if not news_summary:
            return
        
        html_parts.append('<div class="discord-news-summary">')
        html_parts.append('<h5>News Summary</h5>')
        html_parts.append(f'<p>{html.escape(news_summary)}</p>')
        html_parts.append('</div>')

    def _add_price_scenarios_html(self, html_parts: list, analysis: dict) -> None:
        """Add price scenarios to the Discord summary HTML."""
        price_scenarios = analysis.get("price_scenarios", {})
        if not price_scenarios:
            return
        
        bullish_scenario = price_scenarios.get('bullish_scenario')
        bearish_scenario = price_scenarios.get('bearish_scenario')
        
        if bullish_scenario is None and bearish_scenario is None:
            return
        
        html_parts.append('<div class="discord-section-title" data-icon="💰">Price Scenarios</div>')
        html_parts.append('<div class="discord-scenarios">')
        
        if bullish_scenario is not None:
            html_parts.append('<div class="discord-scenario bullish">')
            html_parts.append('<div class="discord-scenario-label">Bullish</div>')
            html_parts.append(f'<div class="discord-scenario-value">${self.format_utils.fmt(bullish_scenario)}</div>')
            html_parts.append('</div>')
        
        if bearish_scenario is not None:
            html_parts.append('<div class="discord-scenario bearish">')
            html_parts.append('<div class="discord-scenario-label">Bearish</div>')
            html_parts.append(f'<div class="discord-scenario-value">${self.format_utils.fmt(bearish_scenario)}</div>')
            html_parts.append('</div>')
        
        html_parts.append('</div>')

    def _add_key_levels_html(self, html_parts: list, analysis: dict) -> None:
        """Add support and resistance levels to the Discord summary HTML."""
        key_levels = analysis.get("key_levels", {})
        if not key_levels:
            return
        
        support_levels = key_levels.get("support", [])
        resistance_levels = key_levels.get("resistance", [])
        
        if not support_levels and not resistance_levels:
            return
        
        html_parts.append('<div class="discord-section-title" data-icon="📊">Key Levels</div>')
        html_parts.append('<div class="discord-levels">')
        
        if support_levels:
            html_parts.append('<div class="discord-level-group support">')
            html_parts.append('<div class="discord-level-title support">Support Levels</div>')
            for level in support_levels:
                html_parts.append(f'<div class="discord-level-value">${self.format_utils.fmt(level)}</div>')
            html_parts.append('</div>')
        
        if resistance_levels:
            html_parts.append('<div class="discord-level-group resistance">')
            html_parts.append('<div class="discord-level-title resistance">Resistance Levels</div>')
            for level in resistance_levels:
                html_parts.append(f'<div class="discord-level-value">${self.format_utils.fmt(level)}</div>')
            html_parts.append('</div>')
        
        html_parts.append('</div>')

    def _get_trend_class(self, value: str) -> str:
        """Get CSS class for trend-based styling."""
        value_upper = str(value).upper()
        if value_upper == "BULLISH":
            return "bullish"
        elif value_upper == "BEARISH":
            return "bearish"
        else:
            return "neutral"
