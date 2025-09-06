"""
Content formatting utilities for HTML generation.
Handles Markdown processing and content enrichment.
"""
import markdown


class ContentFormatter:
    """Handles content formatting and Markdown processing."""
    
    def __init__(self, logger=None):
        self.logger = logger
    
    def process_markdown_content(self, content: str) -> str:
        """
        Process Markdown content and convert to HTML.
        
        Args:
            content: Raw Markdown content
            
        Returns:
            HTML-formatted content
        """
        try:
            if not content:
                if self.logger:
                    self.logger.warning("Empty content provided for Markdown processing")
                return ""
            
            return markdown.markdown(
                content,
                extensions=['fenced_code', 'tables', 'nl2br']
            )
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error processing Markdown content: {e}")
            return content  # Return original content if processing fails
    
    def validate_content_inputs(self, title: str, content: str) -> bool:
        """
        Validate that required content inputs are provided.
        
        Args:
            title: Content title
            content: Content body
            
        Returns:
            True if inputs are valid, False otherwise
        """
        if not title or not content:
            if self.logger:
                self.logger.error("Title or content missing")
            return False
        return True
