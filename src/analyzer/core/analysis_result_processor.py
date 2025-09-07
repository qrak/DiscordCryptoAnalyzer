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

    def _serialize_for_json(self, obj):
        """Recursively convert numpy arrays/scalars and other non-JSON types to JSON-serializable types."""
        try:
            import numpy as _np
        except Exception:
            _np = None

        # Dict
        if isinstance(obj, dict):
            return {k: self._serialize_for_json(v) for k, v in obj.items()}

        # List/Tuple
        if isinstance(obj, (list, tuple)):
            return [self._serialize_for_json(v) for v in obj]

        # Numpy array
        if _np is not None and isinstance(obj, _np.ndarray):
            try:
                return obj.tolist()
            except Exception:
                return [self._serialize_for_json(v) for v in obj]

        # Numpy scalar
        if _np is not None and isinstance(obj, _np.generic):
            try:
                return obj.item()
            except Exception:
                return str(obj)

        # Primitive types
        if isinstance(obj, (str, int, float, bool)) or obj is None:
            return obj

        # Fallback to string representation
        try:
            return str(obj)
        except Exception:
            return None
        
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
                              article_urls: Optional[Dict[str, str]] = None,
                              technical_history: Optional[Dict[str, Any]] = None,
                              technical_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process mock analysis for testing purposes"""
        from src.html.mock import get_mock_analysis_data  # Import here to avoid circular imports
        
        self.logger.debug("Generating mock analysis instead of calling AI model")
        
        # Get all mock data (JSON analysis, Markdown, article URLs)
        mock_data = get_mock_analysis_data(symbol, current_price)
        
        # Compose the JSON part for the structured analysis and include indicators if available
        analysis_obj = mock_data["analysis"].copy()
        if technical_history is not None:
            analysis_obj["technical_history"] = {}
            # convert numpy arrays to lists for JSON serialization where applicable
            for k, v in technical_history.items():
                try:
                    analysis_obj["technical_history"][k] = v.tolist() if hasattr(v, 'tolist') else v
                except Exception:
                    analysis_obj["technical_history"][k] = str(type(v))

        if technical_data is not None:
            analysis_obj["technical_data"] = technical_data

        # Create a JSON-serializable copy for the raw_response
        serializable_analysis = self._serialize_for_json(analysis_obj)
        mock_json_string = json.dumps({"analysis": serializable_analysis}, indent=2)

        # Use the generated Markdown content and append indicators if available
        mock_markdown_content = mock_data["markdown_content"]

        # Build compact indicators section to append to markdown
        indicators_section = ""
        try:
            if technical_data:
                indicators_section += "\n\n### Live Indicator Snapshot\n"
                for k, v in technical_data.items():
                    indicators_section += f"- **{k}**: {v}\n"

            if technical_history:
                indicators_section += "\n### Indicator Series (last 5 values each)\n"
                for k, series in list(technical_history.items())[:20]:
                    try:
                        vals = series.tolist() if hasattr(series, 'tolist') else list(series)
                        sample = vals[-5:]
                        indicators_section += f"- **{k}** (last 5): {sample}\n"
                    except Exception:
                        indicators_section += f"- **{k}**: [unserializable]\n"
        except Exception:
            indicators_section = ""

        if indicators_section:
            mock_markdown_content = mock_markdown_content + "\n\n" + indicators_section
        # Use the mock article URLs or the provided ones
        mock_article_urls = article_urls or mock_data["article_urls"]

        mock_analysis = {
            "analysis": analysis_obj, # Use the structured dict here (with indicators)
            "raw_response": f"```json\n{mock_json_string}\n```\n{mock_markdown_content}",
            "language": language,
            "article_urls": mock_article_urls,
            "technical_history_included": technical_history is not None,
            "technical_data_included": technical_data is not None
        }
        # Also attempt to parse the mock raw_response using the real model parser to surface parsing issues
        try:
            parsed = self.model_manager.parse_response(mock_analysis["raw_response"])
            mock_analysis["parsed_response"] = parsed
            mock_analysis["parse_valid"] = self.model_manager.validate_response(parsed)
            if not mock_analysis["parse_valid"]:
                mock_analysis["parse_error"] = "Parsed response failed validation"
        except Exception as e:
            self.logger.error(f"Error while parsing mock response: {e}")
            mock_analysis["parse_exception"] = str(e)

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
