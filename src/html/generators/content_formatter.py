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
        Process Markdown content and convert to HTML - simplified version.
        
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
            
            # Limit content size to prevent performance issues
            if len(content) > 500000:  # 500KB limit
                if self.logger:
                    self.logger.warning(f"Content too large ({len(content)} chars), truncating to 500KB")
                content = content[:500000] + "\n\n... (content truncated for performance)"
            
            # Convert markdown to HTML with table support
            html_content = markdown.markdown(
                content,
                extensions=['fenced_code', 'nl2br', 'tables']
            )
            
            return html_content
            
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
