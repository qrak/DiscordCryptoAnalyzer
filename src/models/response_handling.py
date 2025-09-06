import json
import re
from typing import Dict, Any

from src.logger.logger import Logger


class ResponseParser:
    """
    Parses and validates AI model responses from various formats.
    """
    
    def __init__(self, logger: Logger):
        self.logger = logger
    
    def parse_response(self, raw_text: str) -> Dict[str, Any]:
        """
        Parse the model's response from raw string to structured data.
        
        Args:
            raw_text: The raw text response from the model
            
        Returns:
            A dictionary representing the parsed response
        """
        try:
            # First, clean up any tool_response tags that sometimes appear in model outputs
            cleaned_text = self._clean_tool_response_tags(raw_text)
            
            # Try parsing as direct JSON
            try:
                return json.loads(cleaned_text)
            except json.JSONDecodeError:
                pass

            # Try extracting JSON from markdown code block
            if "```json" in cleaned_text:
                json_content = cleaned_text.split("```json")[1].split("```")[0].strip()
                return json.loads(json_content)

            self.logger.warning(f"Unable to parse response as JSON, creating fallback response")
            
            # Create a more descriptive error message that includes what was received
            short_response = cleaned_text[:100] + "..." if len(cleaned_text) > 100 else cleaned_text
            
            return {
                "analysis": {
                    "summary": f"Unable to parse the AI response. The analysis may have been in an invalid format.",
                    "observed_trend": "NEUTRAL",  # Changed from "trend" to "observed_trend"
                    "trend_strength": 50,
                    "confidence_score": 0
                    # Removed "trading_recommendation" as it's not used
                },
                "raw_response": cleaned_text,
                "parse_error": f"Failed to parse response: {short_response}"
            }
        except Exception as e:
            self.logger.error(f"Failed to parse JSON response: {e}")
            return {
                "error": str(e), 
                "raw_response": raw_text,
                "analysis": {
                    "summary": "Error parsing response",
                    "observed_trend": "NEUTRAL",  # Changed from "trend" to "observed_trend"
                    "confidence_score": 0
                    # Removed "trading_recommendation" as it's not used
                }
            }
    
    def _clean_tool_response_tags(self, text: str) -> str:
        """Remove tool_response tags from the response."""
        if "<tool_response>" in text:
            self.logger.warning("Found tool_response tags in response, cleaning up")
            # Remove all instances of <tool_response> tags
            cleaned = re.sub(r'<tool_response>[\s\n]*</tool_response>|<tool_response>|</tool_response>', '', text)
            # Further clean up any empty lines
            return re.sub(r'\n\s*\n', '\n', cleaned).strip()
        return text
    
    def validate_response(self, response: Dict[str, Any]) -> bool:
        """
        Validate that the response has the required structure.
        
        Args:
            response: The parsed response dictionary
            
        Returns:
            True if the response is valid, False otherwise
        """
        if not isinstance(response, dict):
            return False
        
        required_fields = ["analysis"]
        if not all(field in response for field in required_fields):
            return False
            
        analysis = response.get("analysis", {})
        if not isinstance(analysis, dict):
            return False
            
        return True
    
    @staticmethod
    def create_error_response(error_message: str) -> Dict[str, Any]:
        """
        Create a standardized error response.
        
        Args:
            error_message: The error message to include
            
        Returns:
            A dictionary with the error response
        """
        return {
            "error": error_message,
            "analysis": {
                "summary": f"Analysis unavailable: {error_message}. Please try again later.",
                "observed_trend": "NEUTRAL",  # Changed from "trend" to "observed_trend"
                "confidence_score": 0
                # Removed "trading_recommendation" as it's not used
            }
        }


class ResponseFormatter:
    """
    Formats and processes model responses for better readability.
    """
    
    def __init__(self, logger: Logger):
        self.logger = logger
    
    def format_scientific_notation(self, content: str) -> str:
        """
        Format scientific notation numbers in text to decimal format.
        Also formats JSON blocks with numbers.
        
        Args:
            content: Text content with possible scientific notation
            
        Returns:
            Formatted text with decimal numbers
        """
        # Format scientific notation numbers in regular text
        pattern = r'(\d+\.?\d*e[+-]?\d+)'
        formatted_content = re.sub(pattern, self._format_number_match, content)
        
        # Format numbers in JSON blocks
        json_pattern = r'```json\s*(\{.*?\})\s*```'
        formatted_content = re.sub(json_pattern, self._format_json_block, formatted_content, flags=re.DOTALL)
        
        return formatted_content
    
    def _format_number_match(self, match):
        """Format a single number from scientific to decimal notation."""
        number_str = match.group(0)
        try:
            number = float(number_str)
            if number < 0.0001:
                return f"{number:.8f}".rstrip('0').rstrip('.')
            elif number < 0.01:
                return f"{number:.6f}".rstrip('0').rstrip('.')
            else:
                return f"{number:.4f}".rstrip('0').rstrip('.')
        except ValueError:
            return number_str
    
    def _format_json_block(self, match):
        """Format all numbers in a JSON block."""
        try:
            json_str = match.group(1)
            data = json.loads(json_str)
            self._process_nested_dict(data)
            return f"```json\n{json.dumps(data, indent=2)}\n```"
        except (json.JSONDecodeError, AttributeError) as e:
            self.logger.warning(f"Failed to format JSON: {e}")
            return match.group(0)
    
    def _process_nested_dict(self, obj):
        """Process numbers in nested dictionary structures."""
        if isinstance(obj, dict):
            self._process_dict_values(obj)
        elif isinstance(obj, list):
            self._process_list_items(obj)
    
    def _process_dict_values(self, obj_dict: dict):
        """Process values in a dictionary"""
        for key, value in obj_dict.items():
            if isinstance(value, (int, float)) and abs(value) < 0.01:
                obj_dict[key] = self._format_small_number(value)
            elif isinstance(value, (dict, list)):
                self._process_nested_dict(value)
    
    def _process_list_items(self, obj_list: list):
        """Process items in a list"""
        for i, item in enumerate(obj_list):
            if isinstance(item, (int, float)) and abs(item) < 0.01:
                obj_list[i] = self._format_small_number(item)
            elif isinstance(item, (dict, list)):
                self._process_nested_dict(item)
    
    def _format_small_number(self, value: float) -> str:
        """Format a small number to appropriate decimal places"""
        if abs(value) < 0.0001:
            return f"{value:.8f}".rstrip('0').rstrip('.')
        else:
            return f"{value:.6f}".rstrip('0').rstrip('.')