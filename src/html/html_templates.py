"""
Modular HTML templates for the crypto bot analysis reports.
Refactored to use separate CSS/JS files and keep the main file under 500 lines.
"""

import os
import base64
from pathlib import Path

class TemplateLoader:
    """Loads and manages HTML template components."""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.styles_dir = self.base_dir / "styles"
        self.scripts_dir = self.base_dir / "scripts"
        self.templates_dir = self.base_dir / "templates"
    
    def _load_file(self, file_path: Path) -> str:
        """Load a file and return its contents as string."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"Warning: Template file not found: {file_path}")
            return ""
    
    def _encode_css_for_inline(self, css_content: str) -> str:
        """Encode CSS content for inline data URLs."""
        return base64.b64encode(css_content.encode('utf-8')).decode('utf-8')
    
    def load_styles(self) -> dict:
        """Load all CSS files and return as dictionary."""
        styles = {}
        css_files = [
            'base_styles.css',
            'component_styles.css', 
            'table_discord_styles.css',
            'ui_responsive.css'
        ]
        
        for css_file in css_files:
            css_path = self.styles_dir / css_file
            css_content = self._load_file(css_path)
            # Encode for data URL usage
            styles[css_file.replace('.css', '_css')] = self._encode_css_for_inline(css_content)
        
        return styles
    
    def load_scripts(self) -> dict:
        """Load all JavaScript files and return as dictionary."""
        scripts = {}
        js_files = [
            'theme-manager.js',
            'collapsible-manager.js',
            'back-to-top.js',
            'app.js'
        ]
        
        for js_file in js_files:
            js_path = self.scripts_dir / js_file
            js_content = self._load_file(js_path)
            scripts[js_file.replace('-', '_').replace('.js', '_js')] = js_content
        
        return scripts
    
    def load_template(self, template_name: str) -> str:
        """Load an HTML template file."""
        template_path = self.templates_dir / template_name
        return self._load_file(template_path)


class ModularTemplateEngine:
    """Main template engine that combines all modular components."""
    
    def __init__(self):
        self.loader = TemplateLoader()
        self._styles_cache = None
        self._scripts_cache = None
        self._templates_cache = {}
    
    @property
    def styles(self) -> dict:
        """Get cached styles or load them."""
        if self._styles_cache is None:
            self._styles_cache = self.loader.load_styles()
        return self._styles_cache
    
    @property 
    def scripts(self) -> dict:
        """Get cached scripts or load them."""
        if self._scripts_cache is None:
            self._scripts_cache = self.loader.load_scripts()
        return self._scripts_cache
    
    def get_template(self, template_name: str) -> str:
        """Get cached template or load it."""
        if template_name not in self._templates_cache:
            self._templates_cache[template_name] = self.loader.load_template(template_name)
        return self._templates_cache[template_name]
    
    def render_analysis_template(self, title: str, content: str, sources_section: str = "", 
                                current_time: str = "", expiry_time: str = "", 
                                discord_summary_section: str = "") -> str:
        """
        Render the main analysis template with all components.
        
        Args:
            title: The title of the analysis
            content: The analysis content with enhanced links
            sources_section: HTML containing the sources list
            current_time: Generation time of the report
            expiry_time: Time when the report link will expire
            discord_summary_section: HTML containing the Discord analysis summary
        """
        template = self.get_template('base_template.html')
        
        # Combine all styles and scripts
        template_vars = {
            'title': title,
            'content': content,
            'sources_section': sources_section,
            'current_time': current_time,
            'expiry_time': expiry_time,
            'discord_summary_section': discord_summary_section,
            **self.styles,
            **self.scripts
        }
        
        return template.format(**template_vars)
    
    def render_error_template(self, error_message: str) -> str:
        """
        Render a simple error template.
        
        Args:
            error_message: The error message to display
        """
        template = self.get_template('error_template.html')
        return template.format(error_message=error_message)


# Global template engine instance
_template_engine = None

def get_template_engine() -> ModularTemplateEngine:
    """Get the global template engine instance."""
    global _template_engine
    if _template_engine is None:
        _template_engine = ModularTemplateEngine()
    return _template_engine


def get_analysis_template(title: str, content: str, sources_section: str = "", 
                         current_time: str = "", expiry_time: str = "", 
                         discord_summary_section: str = "") -> str:
    """
    Public API function for getting analysis templates.
    Maintains backward compatibility with existing code.
    
    Args:
        title: The title of the analysis
        content: The analysis content with enhanced links
        sources_section: HTML containing the sources list
        current_time: Generation time of the report
        expiry_time: Time when the report link will expire
        discord_summary_section: HTML containing the Discord analysis summary
    """
    engine = get_template_engine()
    return engine.render_analysis_template(
        title=title,
        content=content,
        sources_section=sources_section,
        current_time=current_time,
        expiry_time=expiry_time,
        discord_summary_section=discord_summary_section
    )


def get_error_template(error_message: str) -> str:
    """
    Public API function for getting error templates.
    Maintains backward compatibility with existing code.
    
    Args:
        error_message: The error message to display
    """
    engine = get_template_engine()
    return engine.render_error_template(error_message)


# Additional utility functions for development and debugging
def reload_templates():
    """Force reload of all template components (useful for development)."""
    global _template_engine
    _template_engine = None


def list_available_templates() -> list:
    """List all available template files."""
    engine = get_template_engine()
    templates_dir = engine.loader.templates_dir
    return [f.name for f in templates_dir.glob("*.html")]


def validate_template_structure() -> dict:
    """Validate that all required template files exist and are readable."""
    engine = get_template_engine()
    validation_results = {
        'styles': {},
        'scripts': {},
        'templates': {},
        'overall_status': 'ok'
    }
    
    # Check styles
    try:
        styles = engine.styles
        validation_results['styles'] = {name: 'ok' for name in styles.keys()}
    except Exception as e:
        validation_results['styles']['error'] = str(e)
        validation_results['overall_status'] = 'error'
    
    # Check scripts
    try:
        scripts = engine.scripts
        validation_results['scripts'] = {name: 'ok' for name in scripts.keys()}
    except Exception as e:
        validation_results['scripts']['error'] = str(e)
        validation_results['overall_status'] = 'error'
    
    # Check templates
    try:
        templates = list_available_templates()
        validation_results['templates'] = {name: 'ok' for name in templates}
    except Exception as e:
        validation_results['templates']['error'] = str(e)
        validation_results['overall_status'] = 'error'
    
    return validation_results


if __name__ == "__main__":
    # Quick test/validation when run directly
    print("HTML Templates Module - Validation Results:")
    results = validate_template_structure()
    
    for category, items in results.items():
        if category == 'overall_status':
            continue
        print(f"\n{category.upper()}:")
        for name, status in items.items():
            print(f"  {name}: {status}")
    
    print(f"\nOverall Status: {results['overall_status']}")
    
    # Test template generation
    try:
        test_html = get_analysis_template(
            title="Test Analysis", 
            content="<p>Test content</p>",
            sources_section="<h4>Test Sources</h4>",
            current_time="2025-09-15 12:00:00",
            expiry_time="2025-09-15 13:00:00"
        )
        print(f"\nTest template generated successfully: {len(test_html)} characters")
    except Exception as e:
        print(f"\nError generating test template: {e}")