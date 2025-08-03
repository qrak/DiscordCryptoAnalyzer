import json
import re
from typing import Dict, Any, Optional

from src.logger.logger import Logger
from src.models.manager import ModelManager


class AnalysisResultProcessor:
    """Processes and formats market analysis results from AI models"""
    
    def __init__(self, model_manager: ModelManager, logger: Logger):
        """Initialize the processor"""
        self.model_manager = model_manager
        self.logger = logger
        
    async def process_analysis(self, system_prompt: str, prompt: str, language: Optional[str] = None) -> Dict[str, Any]:
        """Process analysis by sending prompts to AI model and formatting response"""
        # Send the prompt to the model
        self.logger.debug("Sending prompt to AI model for analysis")
        
        # Use the send_prompt_streaming method with the correct parameters
        complete_response = await self.model_manager.send_prompt_streaming(
            prompt=prompt,
            system_message=system_prompt
        )
        
        self.logger.debug("Received response from AI model")
        cleaned_response = self._clean_response(complete_response)
        
        parsed_response = self.model_manager.parse_response(cleaned_response)
        
        if not self.model_manager.validate_response(parsed_response):
            self.logger.warning("Invalid response format from AI model")
            return {
                "error": "Invalid response format",
                "raw_response": cleaned_response
            }
        
        # Log the analysis result
        self._log_analysis_result(parsed_response)
        
        # Format the final response
        return self._format_analysis_response(parsed_response, cleaned_response, language)
    
    def process_mock_analysis(self, symbol: str, current_price: float, language: Optional[str] = None,
                              article_urls: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Process mock analysis for testing purposes"""
        from src.html.mock import get_mock_analysis_data  # Import here to avoid circular imports
        
        self.logger.debug("Generating mock analysis instead of calling AI model")
        
        # Get all mock data (JSON analysis, Markdown, article URLs)
        mock_data = get_mock_analysis_data(symbol, current_price)
        
        # Use the JSON part for the structured analysis
        mock_json_string = json.dumps({"analysis": mock_data["analysis"]}, indent=2)
        
        # Use the generated Markdown content
        mock_markdown_content = mock_data["markdown_content"]
        # Use the mock article URLs or the provided ones
        mock_article_urls = article_urls or mock_data["article_urls"]

        mock_analysis = {
            "analysis": mock_data["analysis"], # Use the structured dict here
            "raw_response": f"```json\n{mock_json_string}\n```\n{mock_markdown_content}",
            "language": language,
            "article_urls": mock_article_urls 
        }
        
        return mock_analysis
        
    def _log_analysis_result(self, parsed_response: Dict[str, Any]) -> None:
        """Log analysis result information"""
        if "analysis" in parsed_response:
            analysis = parsed_response["analysis"]
            bias = analysis.get("technical_bias", "UNKNOWN")
            trend = analysis.get("observed_trend", "UNKNOWN")
            confidence = analysis.get("confidence_score", 0)
            self.logger.debug(f"Analysis complete: Technical bias {bias} with {trend} trend ({confidence}% confidence)")
        else:
            self.logger.warning("Analysis complete but response format may be incomplete")
            
    def _format_analysis_response(self, parsed_response: Dict[str, Any], 
                                cleaned_response: str, 
                                language: Optional[str] = None) -> Dict[str, Any]:
        """Format the final analysis response"""
        parsed_response["raw_response"] = cleaned_response
        parsed_response["language"] = language
        
        # Return formatted response - article_urls will be added by the caller
        return parsed_response
    
    @staticmethod
    def _clean_response(text: str) -> str:
        """Remove thinking sections and extra whitespace from AI responses"""
        return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
