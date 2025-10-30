import json
import io
from typing import Optional, Dict, Any, List, Union, cast

from src.utils.loader import config
from src.logger.logger import Logger
from src.parsing.unified_parser import UnifiedParser
from src.platforms.ai_providers.openrouter import ResponseDict
from src.platforms.ai_providers import OpenRouterClient, GoogleAIClient, LMStudioClient
from src.utils.token_counter import TokenCounter


class ModelManager:
    """Manages interactions with AI models"""

    def __init__(self, logger: Logger) -> None:
        """Initialize the ModelManager with its component parts"""
        self.logger = logger
        self.provider = config.PROVIDER.lower()

        # Create API clients based on provider configuration
        self.openrouter_client: Optional[OpenRouterClient] = None
        self.google_client: Optional[GoogleAIClient] = None
        self.google_paid_client: Optional[GoogleAIClient] = None
        self.lm_studio_client: Optional[LMStudioClient] = None

        # Initialize clients based on provider setting
        if self.provider in ["openrouter", "all"]:
            self.openrouter_client = OpenRouterClient(
                api_key=config.OPENROUTER_API_KEY,
                base_url=config.OPENROUTER_BASE_URL,
                logger=logger
            )

        if self.provider in ["googleai", "all"]:
            self.google_client = GoogleAIClient(
                api_key=config.GOOGLE_STUDIO_API_KEY,
                model=config.GOOGLE_STUDIO_MODEL,
                logger=logger
            )
            
            # Initialize paid client if paid API key is available
            if config.GOOGLE_STUDIO_PAID_API_KEY:
                self.google_paid_client = GoogleAIClient(
                    api_key=config.GOOGLE_STUDIO_PAID_API_KEY,
                    model=config.GOOGLE_STUDIO_MODEL,
                    logger=logger
                )
                self.logger.info("Google AI paid client initialized as fallback for overloaded free tier")

        if self.provider in ["local", "all"]:
            self.lm_studio_client = LMStudioClient(
                base_url=config.LM_STUDIO_BASE_URL,
                logger=logger
            )
            self.logger.info(f"LM Studio client initialized for URL: {config.LM_STUDIO_BASE_URL}")

        # Create helper components
        self.unified_parser = UnifiedParser(logger)
        self.token_counter = TokenCounter()

        # Create model configurations as instance variables
        self.model_config = config.get_model_config(config.LM_STUDIO_MODEL)
        self.google_config = config.get_model_config(config.GOOGLE_STUDIO_MODEL)
        self.openrouter_config = config.get_model_config(config.OPENROUTER_BASE_MODEL)

        # Set up models and their configurations
        if self.provider == "local":
            self.model = config.LM_STUDIO_MODEL
        else:
            self.model = config.OPENROUTER_BASE_MODEL

    async def __aenter__(self):
        if self.openrouter_client:
            await self.openrouter_client.__aenter__()
        if self.google_client:
            await self.google_client.__aenter__()
        if self.google_paid_client:
            await self.google_paid_client.__aenter__()
        if self.lm_studio_client:
            await self.lm_studio_client.__aenter__()
        return self

    async def __aexit__(self, _exc_type, _exc_val, _exc_tb):
        await self.close()

    async def close(self) -> None:
        """Close all client connections"""
        try:
            if self.openrouter_client:
                await self.openrouter_client.close()

            if self.google_client:
                await self.google_client.close()
            
            if self.google_paid_client:
                await self.google_paid_client.close()

            if self.lm_studio_client:
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
        
        # Only try streaming if using local provider (LM Studio) or all providers
        if (self.provider == "local" or self.provider == "all") and self.lm_studio_client:
            try:
                response_json = await self.lm_studio_client.console_stream(config.LM_STUDIO_MODEL, messages, self.model_config)
                if response_json is not None:  # Check for valid response before processing
                    return self._process_response(response_json)
                else:
                    self.logger.warning("LM Studio streaming returned None. Falling back to non-streaming mode.")
            except Exception as e:
                self.logger.warning(f"LM Studio streaming failed: {str(e)}. Falling back to non-streaming mode.")
        
        # Fallback to regular prompt for other providers or if streaming fails
        return await self.send_prompt(prompt, system_message, prepared_messages=messages)
    
    async def send_prompt_with_chart_analysis(self, prompt: str, chart_image: Union[io.BytesIO, bytes, str], 
                                            system_message: str = None) -> str:
        """Send a prompt with chart image for pattern analysis"""
        messages = self._prepare_messages(prompt, system_message)
        
        # Use the fallback system for chart analysis based on provider configuration
        if self.provider == "all":
            response_json = await self._get_chart_analysis_fallback_response(messages, chart_image)
        elif self.provider == "googleai" and self.google_client:
            response_json = await self._try_google_chart_analysis_only(messages, chart_image)
        elif self.provider == "openrouter" and self.openrouter_client:
            response_json = await self._try_openrouter_chart_analysis_only(messages, chart_image)
        elif self.provider == "local" and self.lm_studio_client:
            # Local models typically don't support images - fall back to text-only
            self.logger.warning("Chart analysis requested but local provider doesn't support images. Falling back to text-only analysis.")
            raise ValueError("Chart analysis unavailable - local models don't support images")
        else:
            self.logger.error(f"Chart analysis not supported for provider '{self.provider}' or client not available")
            raise ValueError(f"Chart analysis unavailable - provider '{self.provider}' not supported")
        
        if self._is_valid_response(response_json):
            return self._process_response(response_json)
        else:
            self.logger.warning("Chart analysis failed. Falling back to text-only analysis.")
            raise ValueError("Chart analysis failed - invalid response")

    # ----------------------------
    # Internal DRY helper methods
    # ----------------------------
    def _provider_available(self, provider: str) -> bool:
        if provider == "googleai":
            return self.google_client is not None
        if provider == "openrouter":
            return self.openrouter_client is not None
        if provider == "local":
            return self.lm_studio_client is not None
        return False

    def _log_provider_action(self, provider: str, *, action: str, chart: bool = False) -> None:
        # action: "attempting" for fallback path, "using" for single-provider path
        noun = "chart analysis" if chart else "request"
        if provider == "googleai":
            if action == "attempting":
                self.logger.info(f"Attempting {noun} with Google AI Studio model: {config.GOOGLE_STUDIO_MODEL}")
            else:
                self.logger.info(f"Using Google AI Studio model: {config.GOOGLE_STUDIO_MODEL}")
        elif provider == "local":
            if action == "attempting":
                self.logger.info(f"Attempting {noun} with LM Studio model: {config.LM_STUDIO_MODEL}")
            else:
                self.logger.info(f"Using LM Studio model: {config.LM_STUDIO_MODEL}")
        elif provider == "openrouter":
            if action == "attempting":
                self.logger.info(f"Attempting {noun} with OpenRouter model: {config.OPENROUTER_BASE_MODEL}")
            else:
                self.logger.info(f"Using OpenRouter model: {config.OPENROUTER_BASE_MODEL}")

    async def _invoke_provider(self, provider: str, messages: List[Dict[str, str]], *, chart: bool = False,
                               chart_image: Optional[Union[io.BytesIO, bytes, str]] = None) -> Dict[str, Any]:
        """Invoke a provider for normal or chart analysis requests and return its raw response dict."""
        if provider == "googleai" and self.google_client:
            self.logger.info("Attempting chart analysis with Google AI free tier API")
            if chart:
                response = await self.google_client.chat_completion_with_chart_analysis(messages, cast(Any, chart_image), self.google_config)
            else:
                response = await self.google_client.chat_completion(messages, self.google_config)
            
            # If free tier is overloaded and paid client is available, retry with paid API
            if response and response.get("error") == "overloaded" and self.google_paid_client:
                self.logger.warning("Google AI free tier overloaded, retrying with paid API key")
                if chart:
                    response = await self.google_paid_client.chat_completion_with_chart_analysis(messages, cast(Any, chart_image), self.google_config)
                else:
                    response = await self.google_paid_client.chat_completion(messages, self.google_config)
                
                if self._is_valid_response(response):
                    self.logger.info("Successfully used paid Google AI API after free tier overload")
            elif self._is_valid_response(response):
                self.logger.info("Successfully used free Google AI API")
            
            return response

        if provider == "local" and self.lm_studio_client:
            if chart:
                # Local models typically don't support image inputs
                return cast(ResponseDict, {"error": "Chart analysis unavailable - local models don't support images"})
            # LM Studio can raise connection errors; keep try/except parity with previous behavior
            try:
                return await self.lm_studio_client.chat_completion(config.LM_STUDIO_MODEL, messages, self.model_config)
            except Exception as e:
                return cast(ResponseDict, {"error": f"LM Studio connection failed: {str(e)}"})

        if provider == "openrouter" and self.openrouter_client:
            if chart:
                return await self.openrouter_client.chat_completion_with_chart_analysis(
                    config.OPENROUTER_BASE_MODEL, messages, cast(Any, chart_image), self.openrouter_config
                )
            return await self.openrouter_client.chat_completion(config.OPENROUTER_BASE_MODEL, messages, self.openrouter_config)

        return cast(ResponseDict, {"error": f"Provider '{provider}' is not available"})

    def _valid_for_provider(self, provider: str, response: Optional[Dict[str, Any]]) -> bool:
        """Check validity and rate-limit conditions per provider."""
        if not self._is_valid_response(response):
            return False
        if provider == "openrouter" and response and self._rate_limited(response):
            return False
        return True

    async def _first_success(self, providers: List[str], messages: List[Dict[str, str]], *, chart: bool = False,
                              chart_image: Optional[Union[io.BytesIO, bytes, str]] = None,
                              warn_on_fail: bool = True) -> Dict[str, Any]:
        """Try providers in order, returning the first valid response."""
        for idx, provider in enumerate(providers):
            if not self._provider_available(provider):
                continue
            self._log_provider_action(provider, action="attempting", chart=chart)
            response_json = await self._invoke_provider(provider, messages, chart=chart, chart_image=chart_image)
            if self._valid_for_provider(provider, response_json):
                return response_json
            if warn_on_fail:
                # Keep similar warning tone to existing code
                if provider == "googleai":
                    self.logger.warning("Google AI Studio model failed. Trying alternatives...")
                elif provider == "local":
                    self.logger.warning("LM Studio failed. Falling back to next provider.")
                elif provider == "openrouter":
                    self.logger.warning("OpenRouter failed or rate limited.")
        return cast(ResponseDict, {"error": "No providers available"})

    async def _get_chart_analysis_fallback_response(self, messages: List[Dict[str, str]], chart_image: Union[io.BytesIO, bytes, str]) -> Dict[str, Any]:
        """Chart analysis fallback logic when provider is 'all'"""
        # Try Google first, then OpenRouter
        response = await self._first_success(["googleai", "openrouter"], messages, chart=True, chart_image=chart_image)
        if self._is_valid_response(response):
            return response
        return cast(ResponseDict, {"error": "No chart analysis providers available"})

    async def _try_google_chart_analysis_only(self, messages: List[Dict[str, str]], chart_image: Union[io.BytesIO, bytes, str]) -> Dict[str, Any]:
        """Use Google AI Studio only for chart analysis"""
        self._log_provider_action("googleai", action="using", chart=True)
        response_json = await self._invoke_provider("googleai", messages, chart=True, chart_image=chart_image)
        if not self._is_valid_response(response_json):
            self.logger.error("Google AI Studio chart analysis failed or returned invalid response")
            error_detail = response_json.get("error", "Unknown Google API failure") if response_json else "No response from Google API"
            return cast(ResponseDict, {"error": f"Google AI Studio chart analysis failed: {error_detail}"})
        return response_json

    async def _try_openrouter_chart_analysis_only(self, messages: List[Dict[str, str]], chart_image: Union[io.BytesIO, bytes, str]) -> Dict[str, Any]:
        """Use OpenRouter only for chart analysis"""
        self._log_provider_action("openrouter", action="using", chart=True)
        response_json = await self._invoke_provider("openrouter", messages, chart=True, chart_image=chart_image)
        if not self._is_valid_response(response_json) or self._rate_limited(response_json):
            self.logger.error("OpenRouter chart analysis failed or returned invalid response")
            error_detail = response_json.get("error", "Unknown OpenRouter failure") if response_json else "No response from OpenRouter"
            return cast(ResponseDict, {"error": f"OpenRouter chart analysis failed: {error_detail}"})
        return response_json
        
    def supports_image_analysis(self) -> bool:
        """Check if current configuration supports image analysis"""
        # Google AI and OpenRouter both support image analysis
        if self.provider == "all":
            return (self.google_client is not None or self.openrouter_client is not None)
        elif self.provider == "googleai":
            return self.google_client is not None
        elif self.provider == "openrouter":
            return self.openrouter_client is not None
        elif self.provider == "local":
            # Local models typically don't support image analysis
            return False
        return False
        
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
        """Get response from the selected provider(s)"""
        
        # If provider is "all", use fallback system (current behavior)
        if self.provider == "all":
            return await self._get_fallback_response(messages)
        
        # Use single provider only
        if self.provider == "googleai" and self.google_client:
            return await self._try_google_only(messages)
        elif self.provider == "local" and self.lm_studio_client:
            return await self._try_lm_studio_only(messages)
        elif self.provider == "openrouter" and self.openrouter_client:
            return await self._try_openrouter_only(messages)
        else:
            # Fallback if provider is misconfigured or client not available
            self.logger.error(f"Provider '{self.provider}' is not properly configured or client not available")
            return cast(ResponseDict, {"error": f"Provider '{self.provider}' is not available"})

    async def _get_fallback_response(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Original fallback logic when provider is 'all'"""
        # Try Google, then LM Studio, then OpenRouter
        response = await self._first_success(["googleai", "local", "openrouter"], messages)
        if self._is_valid_response(response):
            return response
        # If still no success but OpenRouter is available, log the explicit fallback message then try once more
        if self.openrouter_client:
            return await self._try_openrouter(messages)
        return response

    async def _try_google_only(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Use Google AI Studio only"""
        self._log_provider_action("googleai", action="using")
        response_json = await self._invoke_provider("googleai", messages)

        if not self._is_valid_response(response_json):
            self.logger.error("Google AI Studio request failed or returned invalid response")
            error_detail = response_json.get("error", "Unknown Google API failure") if response_json else "No response from Google API"
            return cast(ResponseDict, {"error": f"Google AI Studio failed: {error_detail}"})

        return response_json

    async def _try_lm_studio_only(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Use LM Studio only"""
        self._log_provider_action("local", action="using")
        response_json = await self._invoke_provider("local", messages)

        if not self._is_valid_response(response_json):
            self.logger.error("LM Studio request failed or returned invalid response")
            error_detail = response_json.get("error", "Unknown LM Studio failure") if response_json else "No response from LM Studio"
            return cast(ResponseDict, {"error": f"LM Studio failed: {error_detail}"})

        return response_json

    async def _try_openrouter_only(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Use OpenRouter only"""
        self._log_provider_action("openrouter", action="using")
        response_json = await self._invoke_provider("openrouter", messages)

        if not self._is_valid_response(response_json) or self._rate_limited(response_json):
            self.logger.error("OpenRouter request failed or returned invalid response")
            error_detail = response_json.get("error", "Unknown OpenRouter failure") if response_json else "No response from OpenRouter"
            return cast(ResponseDict, {"error": f"OpenRouter failed: {error_detail}"})

        return response_json

    async def _try_openrouter(self, messages: List[Dict[str, str]]) -> Optional[ResponseDict]:
        """Use OpenRouter as fallback"""
        self.logger.warning("Google AI Studio and LM Studio (if enabled) failed. Falling back to OpenRouter...")
        response_json = await self._invoke_provider("openrouter", messages)

        if not self._is_valid_response(response_json) or self._rate_limited(response_json):
            self.logger.error("OpenRouter request failed or returned invalid response")
            error_detail = response_json.get("error", "Unknown OpenRouter failure") if response_json else "No response from OpenRouter"
            return cast(ResponseDict, {"error": f"All models failed. Last attempt (OpenRouter): {error_detail}"})

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

    async def _try_google_api(self, messages: List[Dict[str, str]]) -> Optional[ResponseDict]:
        """Use Google Studio API as fallback"""
        self.logger.warning("OpenRouter rate limit hit or LM Studio/OpenRouter failed. Switching to Google Studio API...")
        response_json = await self.google_client.chat_completion(messages, self.google_config)

        if not response_json or not self._is_valid_response(response_json):
            self.logger.error("Google Studio API request failed or returned invalid response")
            error_detail = response_json.get("error", "Unknown Google API failure") if response_json else "No response from Google API"
            return cast(ResponseDict, {"error": f"All models failed. Last attempt (Google): {error_detail}"})

        return response_json

    def _process_response(self, response_json: Union[Dict[str, Any], ResponseDict]) -> str:
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

            formatted_content = content

            response_tokens = self.token_counter.track_prompt_tokens(formatted_content, "completion")
            self.logger.info(f"Response token count: {response_tokens}")

            stats = self.token_counter.get_usage_stats()
            self.logger.info(f"Total tokens used: {stats['total']}")

            self.logger.debug(f"Full response content: {formatted_content}")

            return formatted_content

        except Exception as e:
            self.logger.error(f"Error processing response: {e}")
            return self._format_error_response(f"Error processing response: {str(e)}")


    def _format_error_response(self, error_message: str) -> str:
        """Create a standardized error response in JSON format"""
        json_fallback = {
            "analysis": {
                "summary": f"Analysis unavailable: {error_message}. Please try again later.",
            }
        }
        return f"```json\n{json.dumps(json_fallback, indent=2)}\n```\n\nThe analysis failed due to a technical issue. Please try again later."
