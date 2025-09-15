"""
Template processing utilities for HTML generation.
Handles template management, styling, and final HTML assembly.
"""
import html
from datetime import datetime, timedelta
from src.html.html_templates import get_analysis_template, get_error_template


class TemplateProcessor:
    """Handles HTML template processing and styling."""
    
    def __init__(self, logger=None):
        self.logger = logger
    
    def generate_styled_html(self, title: str, html_analysis_content: str, 
                           article_urls=None, chart_html="", discord_summary_html="") -> str:
        """Generate styled HTML content using pre-rendered HTML analysis."""
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            expiry_time = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")

            sources_section = self._build_sources_section(article_urls)
            final_html_structure = self._assemble_content_structure(html_analysis_content, chart_html)

            return get_analysis_template(
                title=title,
                content=final_html_structure,
                sources_section=sources_section,
                current_time=current_time,
                expiry_time=expiry_time,
                discord_summary_section=discord_summary_html
            )
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error generating HTML template: {e}")
            return get_error_template(html.escape(str(e)))
    
    def _build_sources_section(self, article_urls) -> str:
        """Build the sources section HTML."""
        if not article_urls or len(article_urls) == 0:
            if self.logger:
                self.logger.warning("No article URLs provided for sources section")
            return ""

        sources_section = """
        <div class="resources">
            <h4>📰 Sources & Resources</h4>
            <ul>
        """
        
        for title_text, url in article_urls.items():
            if isinstance(url, str) and url.startswith('https://'):
                safe_title = html.escape(str(title_text) if title_text is not None else "Source")
                sources_section += f'<li><a href="{url}" target="_blank">{safe_title}</a></li>'

        sources_section += """
            </ul>
        </div>
        """
        return sources_section
    
    def _assemble_content_structure(self, html_analysis_content: str, chart_html: str) -> str:
        """Assemble the final content structure."""
        if chart_html:
            charts_html_section = f"""
            <div class="chart-section collapsible-section">
                <div class="collapsible-header">
                    <h3>📈 Market Chart</h3>
                    <span class="collapse-icon">▼</span>
                </div>
                <div class="collapsible-content expanded">
                    <div class="market-chart">
                        {chart_html}
                    </div>
                </div>
            </div>
            """
            return f"""
            {charts_html_section}
            <div class="analysis-details">
                <h3>📊 Analysis Details</h3>
                {html_analysis_content}
            </div>
            """
        else:
            return f"""
            <div class="analysis-details">
                <h3>📊 Analysis Details</h3>
                {html_analysis_content}
            </div>
            """
