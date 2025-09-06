"""
HTML generator utility for creating detailed analysis reports.
"""
import html
from pathlib import Path

from src.html.generators.template_processor import TemplateProcessor
from src.html.generators.chart_section_generator import ChartSectionGenerator
from src.html.generators.content_link_processor import ContentLinkProcessor
from src.html.generators.content_formatter import ContentFormatter


class AnalysisHtmlGenerator:
    """Generates HTML files for detailed analysis using specialized components."""

    def __init__(self, temp_dir: str = 'temp_analysis/', logger=None):
        self.logger = logger
        self.temp_dir = temp_dir
        
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
        ohlcv_data: dict = None
    ) -> str:
        """
        Generate HTML content as a string without writing to disk.
        
        Args:
            title: The title of the analysis
            content: The analysis content (expected in Markdown format)
            article_urls: Dictionary of article URLs
            ohlcv_data: Dictionary containing OHLCV data, technical indicators, and patterns
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

            # Generate final HTML
            html_content = self.template_processor.generate_styled_html(
                escaped_title,
                html_analysis_content,
                article_urls,
                chart_html
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