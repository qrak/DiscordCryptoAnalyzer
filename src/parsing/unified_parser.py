"""
Unified parsing system that consolidates all parsing functionality.
Eliminates duplication and unnecessary delegation layers.
"""
import json
import re
from datetime import datetime
from typing import Dict, Any, Set, Optional, Union, List

from src.logger.logger import Logger


class UnifiedParser:
    """
    Consolidated parser that handles all parsing needs across the application.
    Replaces multiple scattered parsing components with a single, comprehensive solution.
    """
    
    def __init__(self, logger: Logger, format_utils=None):
        self.logger = logger
        self.format_utils = format_utils
        
        # Numeric fields that should be converted from strings with their defaults
        self._numeric_fields = {
            'risk_ratio': 1.0,
            'trend_strength': 50,
            'confidence_score': 50,
            'bullish_scenario': 0.0,
            'bearish_scenario': 0.0
        }
    
    # ============================================================================
    # AI RESPONSE PARSING
    # ============================================================================
    
    def parse_ai_response(self, raw_text: str) -> Dict[str, Any]:
        """
        Parse AI model response from raw string to structured data.
        Supports all AI providers: OpenRouter, Google AI, LM Studio.
        """
        try:
            cleaned_text = self._clean_tool_response_tags(raw_text)
            parsing_errors = []
            
            # Step 1: Try parsing entire response as JSON (pure JSON responses)
            try:
                result = json.loads(cleaned_text)
                return self._normalize_numeric_fields(result)
            except json.JSONDecodeError as e:
                parsing_errors.append(f"Direct JSON parse failed at position {e.pos}: {e.msg}")

            # Step 2: Extract from ```json``` blocks (Google AI format)
            if "```json" in cleaned_text:
                json_start = cleaned_text.find("```json") + 7
                json_end = cleaned_text.find("```", json_start)
                if json_end > json_start:
                    json_content = cleaned_text[json_start:json_end].strip()
                    try:
                        result = json.loads(json_content)
                        return self._normalize_numeric_fields(result)
                    except json.JSONDecodeError as e:
                        parsing_errors.append(f"JSON block parse failed at position {e.pos}: {e.msg}")
                else:
                    parsing_errors.append("Found ```json marker but couldn't locate closing ```")
            else:
                parsing_errors.append("No ```json``` code blocks found")

            # Step 3: Extract JSON from start (OpenRouter format)
            if cleaned_text.strip().startswith('{'):
                brace_count = 0
                for i, char in enumerate(cleaned_text):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_content = cleaned_text[:i+1]
                            try:
                                result = json.loads(json_content)
                                return self._normalize_numeric_fields(result)
                            except json.JSONDecodeError as e:
                                parsing_errors.append(f"Brace-balanced JSON parse failed at position {e.pos}: {e.msg}")
                            break
                else:
                    parsing_errors.append("Found opening brace but braces never balanced")
            else:
                parsing_errors.append(f"Response doesn't start with '{{' (starts with: {cleaned_text[:50]}...)")

            # If all parsing methods fail, create fallback response with detailed diagnostics
            response_preview = cleaned_text[:500] if len(cleaned_text) > 500 else cleaned_text
            self.logger.warning(
                f"Unable to parse AI response as JSON, creating fallback response. "
                f"Parsing attempts failed: {' | '.join(parsing_errors)}. "
                f"Response preview: {response_preview}"
            )
            return self._create_fallback_response(cleaned_text)
            
        except Exception as e:
            self.logger.error(f"Failed to parse AI response: {e}")
            return self._create_error_response(str(e), raw_text)
    
    def validate_ai_response(self, response: Dict[str, Any]) -> bool:
        """Validate that AI response has required structure."""
        return (isinstance(response, dict) and 
                "analysis" in response and 
                isinstance(response["analysis"], dict))
    
    # ============================================================================
    # TIMESTAMP PARSING (consolidates multiple timestamp parsers)
    # ============================================================================
    
    def parse_timestamp(self, timestamp_field: Union[int, float, str, None]) -> float:
        """
        Universal timestamp parser supporting all formats used across the application.
        Consolidates timestamp parsing from MarketDataProcessor and ArticleProcessor.
        """
        if timestamp_field is None:
            return 0.0

        if isinstance(timestamp_field, (int, float)):
            return float(timestamp_field)
        
        if isinstance(timestamp_field, str):
            return self._parse_timestamp_string(timestamp_field)
        
        return 0.0
    
    def _parse_timestamp_string(self, timestamp_str: str) -> float:
        """Parse timestamp string to float timestamp.
        
        Uses centralized FormatUtils for consistency.
        """
        return self.format_utils.timestamp_from_iso(timestamp_str)
    
    # ============================================================================
    # CATEGORY PARSING (consolidates category-related parsing)
    # ============================================================================
    
    def parse_article_categories(self, categories_string: str) -> Set[str]:
        """Parse categories from article category string."""
        if not categories_string:
            return set()
        
        categories = set()
        
        # Split by common separators
        for separator in [',', ';', '|']:
            if separator in categories_string:
                parts = categories_string.split(separator)
                for part in parts:
                    clean_category = part.strip().lower()
                    if clean_category and len(clean_category) > 2:
                        categories.add(clean_category)
                break
        else:
            # No separator found, use as single category
            clean_category = categories_string.strip().lower()
            if clean_category and len(clean_category) > 2:
                categories.add(clean_category)
        
        return categories
    
    # ============================================================================
    # JSON DATA PARSING (consolidates API response parsing)
    # ============================================================================
    
    def parse_api_response(self, api_data: Any) -> Optional[Dict[str, Any]]:
        """
        Parse API responses from various external services.
        Consolidates logic from CryptoCompareDataProcessor and similar components.
        """
        # Handle string data - possible serialized JSON
        if isinstance(api_data, str):
            try:
                api_data = json.loads(api_data)
                self.logger.debug("Converted string to JSON object")
            except json.JSONDecodeError:
                self.logger.warning("Received string data that is not valid JSON")
                return None
        
        # Handle dictionary data with nested structures
        if isinstance(api_data, dict):
            return self._extract_data_from_api_dict(api_data)
        
        # Handle list data directly
        if isinstance(api_data, list):
            self.logger.debug(f"Processing list with {len(api_data)} items")
            return {"data": api_data}
        
        self.logger.warning(f"Unexpected data type for API response: {type(api_data)}")
        return None
    
    def _extract_data_from_api_dict(self, data_dict: Dict) -> Optional[Dict[str, Any]]:
        """Extract useful data from API dictionary structures."""
        self.logger.debug(f"Processing dictionary with keys: {list(data_dict.keys())}")
        
        # Check standard API response format with Response, Message, Type, Data structure
        if "Response" in data_dict and "Data" in data_dict:
            if data_dict["Response"] in ("Success", "success"):
                self.logger.debug(f"Using data from 'Data' key: {type(data_dict['Data'])}")
                return {"data": data_dict["Data"], "metadata": {k: v for k, v in data_dict.items() if k != "Data"}}
            else:
                self.logger.warning(f"API response not successful: {data_dict.get('Message', 'Unknown error')}")
                return None
        
        # Simple Data key structure
        elif "Data" in data_dict:
            self.logger.debug(f"Using data from 'Data' key: {type(data_dict['Data'])}")
            return {"data": data_dict["Data"]}
        
        # Return the dictionary as-is if no standard structure detected
        return data_dict
    
    # ============================================================================
    # SYMBOL AND COIN PARSING
    # ============================================================================
    
    def extract_base_coin(self, symbol: str) -> str:
        """Extract base coin from trading pair symbol."""
        if not symbol:
            return ""
        
        # Handle symbols with explicit separators first
        if '/' in symbol:
            return symbol.split('/')[0].upper()
        if '-' in symbol:
            return symbol.split('-')[0].upper()
        
        # Handle concatenated symbols by removing common quote currencies
        common_quotes = ['USDT', 'USD', 'BTC', 'ETH', 'BNB', 'BUSD']
        symbol_upper = symbol.upper()
        
        for quote in common_quotes:
            if symbol_upper.endswith(quote):
                return symbol_upper[:-len(quote)]
        
        return symbol_upper
    
    def detect_coins_in_text(self, text: str, known_tickers: Set[str]) -> Set[str]:
        """Detect cryptocurrency mentions in text content."""
        if not text:
            return set()
            
        coins_mentioned = set()
        text_upper = text.upper()
        
        # Find potential tickers using regex
        potential_tickers = set(re.findall(r'\b[A-Z]{2,6}\b', text_upper))
        
        # Validate against known tickers
        for ticker in potential_tickers:
            if ticker in known_tickers:
                coins_mentioned.add(ticker)
        
        # Special handling for major cryptocurrencies
        text_lower = text.lower()
        if 'bitcoin' in text_lower:
            coins_mentioned.add('BTC')
        if 'ethereum' in text_lower:
            coins_mentioned.add('ETH')
            
        return coins_mentioned
    
    # ============================================================================
    # INDICATOR VALUE PARSING
    # ============================================================================
    
    def extract_indicator_value(self, data: dict, key: str) -> Union[float, str]:
        """Extract indicator value with proper type handling."""
        try:
            value = data[key]
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, (list, tuple)) and len(value) >= 1:
                return float(value[-1])  # Use last value
            return 'N/A'
        except (KeyError, TypeError, ValueError, IndexError):
            return 'N/A'
        
    def extract_indicator_values(self, data: dict, key: str, expected_count: int = 2) -> List[float]:
        """Extract multiple indicator values with proper type checking."""
        try:
            values = data[key]
            if not isinstance(values, (list, tuple)) or len(values) != expected_count:
                return []
            return [float(val) for val in values]
        except (KeyError, TypeError, ValueError):
            return []
    
    # ============================================================================
    # PRIVATE HELPER METHODS
    # ============================================================================
    
    def _clean_tool_response_tags(self, text: str) -> str:
        """Remove tool_response tags from AI responses."""
        if "<tool_response>" in text:
            self.logger.warning("Found tool_response tags in response, cleaning up")
            cleaned = re.sub(r'<tool_response>[\s\n]*</tool_response>|<tool_response>|</tool_response>', '', text)
            return re.sub(r'\n\s*\n', '\n', cleaned).strip()
        return text
    
    def _normalize_numeric_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure numeric fields are properly typed at the data source."""
        if not isinstance(data, dict):
            return data
            
        # Check analysis section
        analysis = data.get('analysis', {})
        for field, default_value in self._numeric_fields.items():
            if field in analysis and isinstance(analysis[field], str):
                try:
                    analysis[field] = float(analysis[field])
                except ValueError:
                    # Use default value for invalid strings (fix at source)
                    analysis[field] = default_value
        
        # Normalize key_levels arrays (support/resistance)
        key_levels = analysis.get('key_levels', {})
        if isinstance(key_levels, dict):
            for level_type in ['support', 'resistance']:
                levels = key_levels.get(level_type, [])
                if isinstance(levels, list):
                    normalized_levels = []
                    for level in levels:
                        if isinstance(level, (int, float)):
                            normalized_levels.append(float(level))
                        elif isinstance(level, str):
                            try:
                                normalized_levels.append(float(level))
                            except ValueError:
                                # Skip invalid string values - don't add them to the list
                                continue
                    key_levels[level_type] = normalized_levels
        
        # Check root level
        for field, default_value in self._numeric_fields.items():
            if field in data and isinstance(data[field], str):
                try:
                    data[field] = float(data[field])
                except ValueError:
                    data[field] = default_value
        
        return data
    
    def _create_fallback_response(self, cleaned_text: str) -> Dict[str, Any]:
        """Create fallback response when parsing fails."""
        return {
            "analysis": {
                "summary": "Unable to parse the AI response. The analysis may have been in an invalid format.",
                "observed_trend": "NEUTRAL",
                "trend_strength": 50,
                "confidence_score": 0
            },
            "raw_response": cleaned_text,
            "parse_error": "Failed to parse response"
        }
    
    def _create_error_response(self, error_message: str, raw_text: str) -> Dict[str, Any]:
        """Create error response for parsing exceptions."""
        return {
            "error": error_message, 
            "raw_response": raw_text,
            "analysis": {
                "summary": "Error parsing response",
                "observed_trend": "NEUTRAL",
                "confidence_score": 0
            }
        }