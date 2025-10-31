import json
import io
from typing import Optional, Dict, Any, List, Union, cast, Tuple

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

        # Create API clients - always initialize all available clients to support runtime provider overrides
        self.openrouter_client: Optional[OpenRouterClient] = None
        self.google_client: Optional[GoogleAIClient] = None
        self.google_paid_client: Optional[GoogleAIClient] = None
        self.lm_studio_client: Optional[LMStudioClient] = None

        # Initialize OpenRouter client if API key is available
        if config.OPENROUTER_API_KEY:
            self.openrouter_client = OpenRouterClient(
                api_key=config.OPENROUTER_API_KEY,
                base_url=config.OPENROUTER_BASE_URL,
                logger=logger
            )
            self.logger.info("OpenRouter client initialized")

        # Initialize Google AI client if API key is available
        if config.GOOGLE_STUDIO_API_KEY:
            self.google_client = GoogleAIClient(
                api_key=config.GOOGLE_STUDIO_API_KEY,
                model=config.GOOGLE_STUDIO_MODEL,
                logger=logger
            )
            self.logger.info("Google AI client initialized")
            
            # Initialize paid client if paid API key is available
            if config.GOOGLE_STUDIO_PAID_API_KEY:
                self.google_paid_client = GoogleAIClient(
                    api_key=config.GOOGLE_STUDIO_PAID_API_KEY,
                    model=config.GOOGLE_STUDIO_MODEL,
                    logger=logger
                )
                self.logger.info("Google AI paid client initialized as fallback for overloaded free tier")

        # Initialize LM Studio client (no API key required)
        if config.LM_STUDIO_BASE_URL:
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

    async def send_prompt(self, prompt: str, system_message: str = None, prepared_messages: List[Dict[str, str]] = None,
                         provider: Optional[str] = None, model: Optional[str] = None) -> str:
        """
        Send a prompt to the model and get a response.
        
        Args:
            prompt: User prompt
            system_message: Optional system instructions
            prepared_messages: Pre-prepared message list (if None, will be created from prompt)
            provider: Optional provider override (admin only)
            model: Optional model override (admin only)
            
        Returns:
            Response text from the AI model
        """
        messages = prepared_messages if prepared_messages is not None else self._prepare_messages(prompt, system_message)
        response_json = await self._get_model_response(messages, provider=provider, model=model)
        return self._process_response(response_json)

    async def send_prompt_streaming(self, prompt: str, system_message: str = None, 
                                    provider: Optional[str] = None, model: Optional[str] = None) -> str:
        """
        Send a prompt to the model and get a streaming response.
        
        Args:
            prompt: User prompt
            system_message: Optional system instructions
            provider: Optional provider override (admin only)
            model: Optional model override (admin only)
            
        Returns:
            Complete response text from the AI model
        """
        messages = self._prepare_messages(prompt, system_message)
        
        # Use admin-specified provider if provided
        effective_provider = provider if provider else self.provider
        
        # Only try streaming if using local provider (LM Studio) or all providers
        if (effective_provider == "local" or effective_provider == "all") and self.lm_studio_client:
            try:
                # Use admin-specified model if provided, otherwise use default
                effective_model = model if model else config.LM_STUDIO_MODEL
                response_json = await self.lm_studio_client.console_stream(effective_model, messages, self.model_config)
                if response_json is not None:  # Check for valid response before processing
                    return self._process_response(response_json)
                else:
                    self.logger.warning("LM Studio streaming returned None. Falling back to non-streaming mode.")
            except Exception as e:
                self.logger.warning(f"LM Studio streaming failed: {str(e)}. Falling back to non-streaming mode.")
        
        # Fallback to regular prompt for other providers or if streaming fails
        return await self.send_prompt(prompt, system_message, prepared_messages=messages, provider=provider, model=model)
    
    async def send_prompt_with_chart_analysis(self, prompt: str, chart_image: Union[io.BytesIO, bytes, str], 
                                            system_message: str = None, provider: Optional[str] = None, 
                                            model: Optional[str] = None) -> str:
        """
        Send a prompt with chart image for pattern analysis.
        
        Args:
            prompt: User prompt
            chart_image: Chart image data
            system_message: Optional system instructions
            provider: Optional provider override (admin only)
            model: Optional model override (admin only)
            
        Returns:
            Response text from the AI model
        """
        messages = self._prepare_messages(prompt, system_message)
        
        # Use admin-specified provider if provided
        effective_provider = provider if provider else self.provider
        
        # Use the fallback system for chart analysis based on provider configuration
        if effective_provider == "all":
            response_json = await self._get_chart_analysis_fallback_response(messages, chart_image, model)
        elif effective_provider == "googleai" and self.google_client:
            response_json = await self._try_google_chart_analysis_only(messages, chart_image, model)
        elif effective_provider == "openrouter" and self.openrouter_client:
            response_json = await self._try_openrouter_chart_analysis_only(messages, chart_image, model)
        elif effective_provider == "local" and self.lm_studio_client:
            # Local models typically don't support images - fall back to text-only
            self.logger.warning("Chart analysis requested but local provider doesn't support images. Falling back to text-only analysis.")
            raise ValueError("Chart analysis unavailable - local models don't support images")
        else:
            self.logger.error(f"Chart analysis not supported for provider '{effective_provider}' or client not available")
            self._log_provider_unavailable_guidance(effective_provider)
            raise ValueError(f"Chart analysis unavailable - provider '{effective_provider}' not supported")
        
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

    def _log_provider_action(self, provider: str, *, action: str, chart: bool = False, model: Optional[str] = None) -> None:
        # action: "attempting" for fallback path, "using" for single-provider path
        noun = "chart analysis" if chart else "request"
        if provider == "googleai":
            effective_model = model if model else config.GOOGLE_STUDIO_MODEL
            if action == "attempting":
                self.logger.info(f"Attempting {noun} with Google AI Studio model: {effective_model}")
            else:
                self.logger.info(f"Using Google AI Studio model: {effective_model}")
        elif provider == "local":
            effective_model = model if model else config.LM_STUDIO_MODEL
            if action == "attempting":
                self.logger.info(f"Attempting {noun} with LM Studio model: {effective_model}")
            else:
                self.logger.info(f"Using LM Studio model: {effective_model}")
        elif provider == "openrouter":
            effective_model = model if model else config.OPENROUTER_BASE_MODEL
            if action == "attempting":
                self.logger.info(f"Attempting {noun} with OpenRouter model: {effective_model}")
            else:
                self.logger.info(f"Using OpenRouter model: {effective_model}")

    def _log_provider_unavailable_guidance(self, provider: str) -> None:
        """Log helpful guidance when a provider is unavailable."""
        if provider == "openrouter" and not self.openrouter_client:
            self.logger.error("OpenRouter client not initialized. Check that OPENROUTER_API_KEY is set in keys.env")
        elif provider == "googleai" and not self.google_client:
            self.logger.error("Google AI client not initialized. Check that GOOGLE_STUDIO_API_KEY is set in keys.env")
        elif provider == "local" and not self.lm_studio_client:
            self.logger.error("LM Studio client not initialized. Check that LM_STUDIO_BASE_URL is set in config.ini and server is running")
        elif provider == "local":
            self.logger.error("Local models don't support image analysis")

    async def _invoke_provider(self, provider: str, messages: List[Dict[str, str]], *, chart: bool = False,
                               chart_image: Optional[Union[io.BytesIO, bytes, str]] = None, 
                               model: Optional[str] = None) -> Dict[str, Any]:
        """
        Invoke a provider for normal or chart analysis requests and return its raw response dict.
        
        Args:
            provider: Provider name (googleai, local, openrouter)
            messages: Message list for the AI model
            chart: Whether this is a chart analysis request
            chart_image: Optional chart image data
            model: Optional model override (admin only)
            
        Returns:
            Response dictionary from the provider
        """
        if provider == "googleai" and self.google_client:
            # Use admin-specified model if provided, otherwise use default
            effective_model = model if model else config.GOOGLE_STUDIO_MODEL
            
            # Determine if model supports free tier (only Flash variants)
            is_free_tier_model = "flash" in effective_model.lower()
            tier_info = "free tier" if is_free_tier_model else "paid tier"
            self.logger.info(f"Attempting chart analysis with Google AI {tier_info} API (model: {effective_model})")
            
            if chart:
                response = await self.google_client.chat_completion_with_chart_analysis(messages, cast(Any, chart_image), self.google_config, model=effective_model)
            else:
                response = await self.google_client.chat_completion(messages, self.google_config, model=effective_model)
            
            # If free tier is overloaded and paid client is available, retry with paid API
            if response and response.get("error") == "overloaded" and self.google_paid_client:
                self.logger.warning("Google AI free tier overloaded, retrying with paid API key")
                if chart:
                    response = await self.google_paid_client.chat_completion_with_chart_analysis(messages, cast(Any, chart_image), self.google_config, model=effective_model)
                else:
                    response = await self.google_paid_client.chat_completion(messages, self.google_config, model=effective_model)
                
                if self._is_valid_response(response):
                    self.logger.info("Successfully used paid Google AI API after free tier overload")
            elif self._is_valid_response(response):
                tier_success = "free tier" if is_free_tier_model else "paid tier"
                self.logger.info(f"Successfully used {tier_success} Google AI API")
            
            return response

        if provider == "local" and self.lm_studio_client:
            if chart:
                # Local models typically don't support image inputs
                return cast(ResponseDict, {"error": "Chart analysis unavailable - local models don't support images"})
            # LM Studio can raise connection errors; keep try/except parity with previous behavior
            # Use admin-specified model if provided, otherwise use default
            effective_model = model if model else config.LM_STUDIO_MODEL
            try:
                return await self.lm_studio_client.chat_completion(effective_model, messages, self.model_config)
            except Exception as e:
                return cast(ResponseDict, {"error": f"LM Studio connection failed: {str(e)}"})

        if provider == "openrouter" and self.openrouter_client:
            # Use admin-specified model if provided, otherwise use default
            effective_model = model if model else config.OPENROUTER_BASE_MODEL
            if chart:
                return await self.openrouter_client.chat_completion_with_chart_analysis(
                    effective_model, messages, cast(Any, chart_image), self.openrouter_config
                )
            return await self.openrouter_client.chat_completion(effective_model, messages, self.openrouter_config)

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
                              model: Optional[str] = None, warn_on_fail: bool = True) -> Dict[str, Any]:
        """Try providers in order, returning the first valid response."""
        for idx, provider in enumerate(providers):
            if not self._provider_available(provider):
                continue
            self._log_provider_action(provider, action="attempting", chart=chart, model=model)
            response_json = await self._invoke_provider(provider, messages, chart=chart, chart_image=chart_image, model=model)
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

    async def _get_chart_analysis_fallback_response(self, messages: List[Dict[str, str]], 
                                                    chart_image: Union[io.BytesIO, bytes, str],
                                                    model: Optional[str] = None) -> Dict[str, Any]:
        """Chart analysis fallback logic when provider is 'all'"""
        # Try Google first, then OpenRouter
        response = await self._first_success(["googleai", "openrouter"], messages, chart=True, chart_image=chart_image, model=model)
        if self._is_valid_response(response):
            return response
        return cast(ResponseDict, {"error": "No chart analysis providers available"})

    async def _try_google_chart_analysis_only(self, messages: List[Dict[str, str]], 
                                              chart_image: Union[io.BytesIO, bytes, str],
                                              model: Optional[str] = None) -> Dict[str, Any]:
        """Use Google AI Studio only for chart analysis"""
        self._log_provider_action("googleai", action="using", chart=True, model=model)
        response_json = await self._invoke_provider("googleai", messages, chart=True, chart_image=chart_image, model=model)
        if not self._is_valid_response(response_json):
            self.logger.error("Google AI Studio chart analysis failed or returned invalid response")
            error_detail = response_json.get("error", "Unknown Google API failure") if response_json else "No response from Google API"
            return cast(ResponseDict, {"error": f"Google AI Studio chart analysis failed: {error_detail}"})
        return response_json

    async def _try_openrouter_chart_analysis_only(self, messages: List[Dict[str, str]], 
                                                  chart_image: Union[io.BytesIO, bytes, str],
                                                  model: Optional[str] = None) -> Dict[str, Any]:
        """Use OpenRouter only for chart analysis"""
        self._log_provider_action("openrouter", action="using", chart=True, model=model)
        response_json = await self._invoke_provider("openrouter", messages, chart=True, chart_image=chart_image, model=model)
        if not self._is_valid_response(response_json) or self._rate_limited(response_json):
            self.logger.error("OpenRouter chart analysis failed or returned invalid response")
            error_detail = response_json.get("error", "Unknown OpenRouter failure") if response_json else "No response from OpenRouter"
            return cast(ResponseDict, {"error": f"OpenRouter chart analysis failed: {error_detail}"})
        return response_json
        
    def supports_image_analysis(self, provider_override: Optional[str] = None) -> bool:
        """Check if the selected provider supports image analysis."""
        provider_name = (provider_override or self.provider or "").lower()
        if provider_name == "all":
            return (self.google_client is not None or self.openrouter_client is not None)
        if provider_name == "googleai":
            return self.google_client is not None
        if provider_name == "openrouter":
            return self.openrouter_client is not None
        if provider_name == "local":
            return False
        return False

    def describe_provider_and_model(
        self,
        provider_override: Optional[str],
        model_override: Optional[str],
        *,
        chart: bool = False,
    ) -> Tuple[str, str]:
        """Return provider + model description for logging and telemetry."""
        provider_name = (provider_override or self.provider or "unknown").lower()

        if model_override:
            return provider_name, model_override

        if provider_name == "googleai":
            return provider_name, config.GOOGLE_STUDIO_MODEL
        if provider_name == "openrouter":
            return provider_name, config.OPENROUTER_BASE_MODEL
        if provider_name == "local":
            return provider_name, config.LM_STUDIO_MODEL
        if provider_name == "all":
            chain: List[str] = []
            # Always list configured defaults, even if client is temporarily unavailable.
            if config.GOOGLE_STUDIO_MODEL:
                chain.append(config.GOOGLE_STUDIO_MODEL)
            if chart:
                if config.OPENROUTER_BASE_MODEL:
                    chain.append(config.OPENROUTER_BASE_MODEL)
            else:
                if config.LM_STUDIO_MODEL:
                    chain.append(config.LM_STUDIO_MODEL)
                if config.OPENROUTER_BASE_MODEL:
                    chain.append(config.OPENROUTER_BASE_MODEL)

            model_chain = " -> ".join(chain) if chain else "fallback chain unavailable"
            return provider_name, model_chain

        return provider_name, "unspecified"
        
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

    async def _get_model_response(self, messages: List[Dict[str, str]], provider: Optional[str] = None, 
                                  model: Optional[str] = None) -> Dict[str, Any]:
        """
        Get response from the selected provider(s).
        
        Args:
            messages: Message list for the AI model
            provider: Optional provider override (admin only)
            model: Optional model override (admin only)
            
        Returns:
            Response dictionary from the AI provider
        """
        # Use admin-specified provider if provided
        effective_provider = provider if provider else self.provider
        
        # If provider is "all", use fallback system (current behavior)
        if effective_provider == "all":
            return await self._get_fallback_response(messages, model)
        
        # Use single provider only
        if effective_provider == "googleai" and self.google_client:
            return await self._try_google_only(messages, model)
        elif effective_provider == "local" and self.lm_studio_client:
            return await self._try_lm_studio_only(messages, model)
        elif effective_provider == "openrouter" and self.openrouter_client:
            return await self._try_openrouter_only(messages, model)
        else:
            # Fallback if provider is misconfigured or client not available
            self.logger.error(f"Provider '{effective_provider}' is not properly configured or client not available")
            self._log_provider_unavailable_guidance(effective_provider)
            return cast(ResponseDict, {"error": f"Provider '{effective_provider}' is not available"})

    async def _get_fallback_response(self, messages: List[Dict[str, str]], model: Optional[str] = None) -> Dict[str, Any]:
        """Original fallback logic when provider is 'all'"""
        # Try Google, then LM Studio, then OpenRouter
        response = await self._first_success(["googleai", "local", "openrouter"], messages, model=model)
        if self._is_valid_response(response):
            return response
        # If still no success but OpenRouter is available, log the explicit fallback message then try once more
        if self.openrouter_client:
            return await self._try_openrouter(messages, model)
        return response

    async def _try_google_only(self, messages: List[Dict[str, str]], model: Optional[str] = None) -> Dict[str, Any]:
        """Use Google AI Studio only"""
        self._log_provider_action("googleai", action="using", model=model)
        response_json = await self._invoke_provider("googleai", messages, model=model)

        if not self._is_valid_response(response_json):
            self.logger.error("Google AI Studio request failed or returned invalid response")
            error_detail = response_json.get("error", "Unknown Google API failure") if response_json else "No response from Google API"
            return cast(ResponseDict, {"error": f"Google AI Studio failed: {error_detail}"})

        return response_json

    async def _try_lm_studio_only(self, messages: List[Dict[str, str]], model: Optional[str] = None) -> Dict[str, Any]:
        """Use LM Studio only"""
        self._log_provider_action("local", action="using", model=model)
        response_json = await self._invoke_provider("local", messages, model=model)

        if not self._is_valid_response(response_json):
            self.logger.error("LM Studio request failed or returned invalid response")
            error_detail = response_json.get("error", "Unknown LM Studio failure") if response_json else "No response from LM Studio"
            return cast(ResponseDict, {"error": f"LM Studio failed: {error_detail}"})

        return response_json

    async def _try_openrouter_only(self, messages: List[Dict[str, str]], model: Optional[str] = None) -> Dict[str, Any]:
        """Use OpenRouter only"""
        self._log_provider_action("openrouter", action="using", model=model)
        response_json = await self._invoke_provider("openrouter", messages, model=model)

        if not self._is_valid_response(response_json) or self._rate_limited(response_json):
            self.logger.error("OpenRouter request failed or returned invalid response")
            error_detail = response_json.get("error", "Unknown OpenRouter failure") if response_json else "No response from OpenRouter"
            return cast(ResponseDict, {"error": f"OpenRouter failed: {error_detail}"})

        return response_json

    async def _try_openrouter(self, messages: List[Dict[str, str]], model: Optional[str] = None) -> Optional[ResponseDict]:
        """Use OpenRouter as fallback"""
        self.logger.warning("Google AI Studio and LM Studio (if enabled) failed. Falling back to OpenRouter...")
        response_json = await self._invoke_provider("openrouter", messages, model=model)

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
