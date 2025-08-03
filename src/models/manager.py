import json
from typing import Optional, Dict, Any, List

from config.config import (
    OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_BASE_MODEL,
    GOOGLE_STUDIO_API_KEY, GOOGLE_STUDIO_MODEL,
    USE_LM_STUDIO, LM_STUDIO_BASE_URL, LM_STUDIO_MODEL
)
from src.logger.logger import Logger
from src.models.config import ModelConfigManager
from src.models.response_handling import ResponseParser, ResponseFormatter
from src.platforms.ai_providers import OpenRouterClient, GoogleAIClient, LMStudioClient
from src.utils.token_counter import TokenCounter


class ModelManager:
    """Manages interactions with AI models"""

    def __init__(self, logger: Logger) -> None:
        """Initialize the ModelManager with its component parts"""
        self.logger = logger
        self.use_lm_studio = USE_LM_STUDIO

        # Create API clients
        self.openrouter_client = OpenRouterClient(
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL,
            logger=logger
        )

        self.google_client = GoogleAIClient(
            api_key=GOOGLE_STUDIO_API_KEY,
            model=GOOGLE_STUDIO_MODEL,
            base_url="https://generativelanguage.googleapis.com/v1beta/models",
            logger=logger
        )

        # Conditionally create LM Studio client
        self.lm_studio_client: Optional[LMStudioClient] = None
        if self.use_lm_studio:
            self.lm_studio_client = LMStudioClient(
                base_url=LM_STUDIO_BASE_URL,
                logger=logger
            )
            self.logger.info(f"LM Studio client initialized for URL: {LM_STUDIO_BASE_URL}")

        # Create configuration manager
        self.config_manager = ModelConfigManager()

        # Create helper components
        self.response_parser = ResponseParser(logger)
        self.response_formatter = ResponseFormatter(logger)
        self.token_counter = TokenCounter()

        # Set up models and their configurations
        self.model = LM_STUDIO_MODEL if self.use_lm_studio else OPENROUTER_BASE_MODEL

    async def __aenter__(self):
        await self.openrouter_client.__aenter__()
        await self.google_client.__aenter__()
        if self.lm_studio_client:
            await self.lm_studio_client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self) -> None:
        """Close all client connections"""
        try:
            if hasattr(self, 'openrouter_client') and self.openrouter_client:
                await self.openrouter_client.close()
            
            if hasattr(self, 'google_client') and self.google_client:
                await self.google_client.close()
                
            if hasattr(self, 'lm_studio_client') and self.lm_studio_client:
                await self.lm_studio_client.close()
                
            self.logger.debug("All model clients closed successfully")
        except Exception as e:
            self.logger.error(f"Error during model manager cleanup: {e}")

    async def send_prompt(self, prompt: str, system_message: str = None, prepared_messages: List[Dict[str, str]] = None) -> str:
        """Send a prompt to the model and get a response"""
        messages = prepared_messages if prepared_messages is not None else self._prepare_messages(prompt, system_message)
        response_json = await self._get_model_response(messages)
        return self._process_response(response_json)

    async def send_prompt_streaming(self, prompt: str, system_message: str = None) -> str:
        """Send a prompt to the model and get a streaming response"""
        messages = self._prepare_messages(prompt, system_message)
        
        if self.use_lm_studio and self.lm_studio_client:
            try:
                model_config = self.config_manager.get_config(self.model)
                response_json = await self.lm_studio_client.console_stream(self.model, messages, model_config)
                if response_json is not None:  # Check for valid response before processing
                    return self._process_response(response_json)
                else:
                    self.logger.warning("LM Studio streaming returned None. Falling back to non-streaming mode.")
            except Exception as e:
                self.logger.warning(f"LM Studio streaming failed: {str(e)}. Falling back to non-streaming mode.")
        
        return await self.send_prompt(prompt, system_message, prepared_messages=messages)
        
    def _prepare_messages(self, prompt: str, system_message: Optional[str] = None) -> List[Dict[str, str]]:
        """Prepare message structure and track tokens"""
        messages = []
    
        if system_message:
            combined_prompt = f"System instructions: {system_message}\n\nUser query: {prompt}"
            messages.append({"role": "user", "content": combined_prompt})
            
            system_tokens = self.token_counter.track_prompt_tokens(system_message, "system")
            prompt_tokens = self.token_counter.track_prompt_tokens(prompt, "prompt")
            self.logger.info(f"System message token count: {system_tokens}")
            self.logger.info(f"Prompt token count: {prompt_tokens}")
            self.logger.debug(f"Full prompt content: {combined_prompt}")
        else:
            messages.append({"role": "user", "content": prompt})
            prompt_tokens = self.token_counter.track_prompt_tokens(prompt, "prompt")
            self.logger.info(f"Prompt token count: {prompt_tokens}")
            self.logger.debug(f"Full prompt content: {prompt}")
    
        return messages

    async def _get_model_response(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Try models in sequence until we get a valid response, starting with Google AI Studio"""

        # Start with Google AI Studio
        self.logger.info(f"Attempting request with Google AI Studio model: {GOOGLE_STUDIO_MODEL}")
        google_config = self.config_manager.get_config(GOOGLE_STUDIO_MODEL)
        response_json = await self.google_client.chat_completion(messages, google_config)

        if self._is_valid_response(response_json):
            return response_json
        else:
            self.logger.warning(f"Google AI Studio model {GOOGLE_STUDIO_MODEL} failed. Trying alternatives...")

        # Try LM Studio if enabled (as second priority)
        if self.use_lm_studio and self.lm_studio_client:
            try:
                self.logger.info(f"Attempting request with LM Studio model: {self.model}")
                model_config = self.config_manager.get_config(self.model)
                response_json = await self.lm_studio_client.chat_completion(self.model, messages, model_config)

                if self._is_valid_response(response_json):
                    return response_json
                else:
                    self.logger.warning(f"LM Studio model {self.model} failed. Falling back to OpenRouter.")
            except Exception as e:
                # Catch connection errors and other exceptions
                self.logger.warning(f"LM Studio connection failed: {str(e)}. Falling back to OpenRouter.")

        # Finally try OpenRouter as last resort
        return await self._try_openrouter(messages)

    async def _try_openrouter(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Use OpenRouter as fallback"""
        self.logger.warning("Google AI Studio and LM Studio (if enabled) failed. Falling back to OpenRouter...")
        
        model_config = self.config_manager.get_config(OPENROUTER_BASE_MODEL)
        response_json = await self.openrouter_client.chat_completion(OPENROUTER_BASE_MODEL, messages, model_config)

        if not self._is_valid_response(response_json) or self._rate_limited(response_json):
            self.logger.error("OpenRouter request failed or returned invalid response")
            error_detail = response_json.get("error", "Unknown OpenRouter failure") if response_json else "No response from OpenRouter"
            return {"error": f"All models failed. Last attempt (OpenRouter): {error_detail}"}

        return response_json

    def _rate_limited(self, response: Dict[str, Any]) -> bool:
        """Check if the response indicates rate limiting"""
        return (response and 
                isinstance(response, dict) and 
                response.get("error") == "rate_limit")

    def _is_valid_response(self, response: Optional[Dict[str, Any]]) -> bool:
        """Check if response contains valid choices"""
        return (response and 
                "choices" in response and 
                response["choices"])

    async def _try_google_api(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Use Google Studio API as fallback"""
        self.logger.warning("OpenRouter rate limit hit or LM Studio/OpenRouter failed. Switching to Google Studio API...")
        google_config = self.config_manager.get_config(GOOGLE_STUDIO_MODEL)
        response_json = await self.google_client.chat_completion(messages, google_config)

        if not response_json or not self._is_valid_response(response_json):
            self.logger.error("Google Studio API request failed or returned invalid response")
            error_detail = response_json.get("error", "Unknown Google API failure") if response_json else "No response from Google API"
            return {"error": f"All models failed. Last attempt (Google): {error_detail}"}

        return response_json

    def _process_response(self, response_json: Dict[str, Any]) -> str:
        """Extract and process content from the response"""
        try:
            if response_json is None:
                return self._format_error_response("Empty response from API")
                
            if "error" in response_json:
                return self._format_error_response(response_json["error"])

            if not self._is_valid_response(response_json):
                self.logger.error(f"Missing 'choices' key in API response: {response_json}")
                return self._format_error_response("Invalid API response format")

            content = response_json["choices"][0]["message"]["content"]
            if not content:
                self.logger.error(f"Missing content in API response: {response_json}")
                return self._format_error_response("Missing content in API response")

            formatted_content = self.response_formatter.format_scientific_notation(content)

            response_tokens = self.token_counter.track_prompt_tokens(formatted_content, "completion")
            self.logger.info(f"Response token count: {response_tokens}")

            stats = self.token_counter.get_usage_stats()
            self.logger.info(f"Total tokens used: {stats['total']}")

            self.logger.debug(f"Full response content: {formatted_content}")

            return formatted_content

        except Exception as e:
            self.logger.error(f"Error processing response: {e}")
            return self._format_error_response(f"Error processing response: {str(e)}")

    def parse_response(self, raw: str) -> Dict[str, Any]:
        """Parse the model's response from raw string to structured data"""
        return self.response_parser.parse_response(raw)

    def validate_response(self, response: Dict[str, Any]) -> bool:
        """Validate that the response has the required structure"""
        return self.response_parser.validate_response(response)

    def _format_error_response(self, error_message: str) -> str:
        """Create a standardized error response in JSON format"""
        json_fallback = {
            "analysis": {
                "summary": f"Analysis unavailable: {error_message}. Please try again later.",
            }
        }
        return f"```json\n{json.dumps(json_fallback, indent=2)}\n```\n\nThe analysis failed due to a technical issue. Please try again later."