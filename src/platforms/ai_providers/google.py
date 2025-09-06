import asyncio
from typing import Optional, Dict, Any, List

import aiohttp

from src.logger.logger import Logger
from src.platforms.ai_providers.base import BaseApiClient
from src.platforms.ai_providers.openrouter import ResponseDict
from src.utils.decorators import retry_api_call


class GoogleAIClient(BaseApiClient):
    """Client for handling Google AI API requests."""
    
    def __init__(self, api_key: str, model: str, base_url: str, logger: Logger) -> None:
        super().__init__(api_key, base_url, logger)
        self.model = model
    
    def _convert_messages_to_google_format(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert OpenAI format messages to Google API format."""
        google_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if isinstance(content, list):
                parts = []
                for part in content:
                    if part.get("type") == "text":
                        parts.append({"text": part.get("text", "")})
                if parts:
                    google_messages.append({"role": "user" if role != "assistant" else "model", "parts": parts})
                continue
            
            if role == "system":
                role = "user"
                content = f"System: {content}"
            elif role == "assistant":
                role = "model"
                
            google_messages.append({
                "role": role,
                "parts": [{"text": content}]
            })
        
        return google_messages
    
    @retry_api_call(max_retries=3, initial_delay=1, backoff_factor=2, max_delay=30)
    async def chat_completion(self, messages: List[Dict[str, Any]], model_config: Dict[str, Any]) -> Optional[ResponseDict]:
        """Send a chat completion request to the Google AI API."""
        # Convert messages to Google format
        google_messages = self._convert_messages_to_google_format(messages)
        
        payload = {
            "contents": google_messages,
            "generationConfig": {
                "temperature": model_config.get("temperature", 0.7),
                "topP": model_config.get("top_p", 0.9),
                "topK": model_config.get("top_k", 40),
                "maxOutputTokens": model_config.get("max_tokens", 32768), # Increased default
            }
        }
        
        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        
        try:
            response_data = await self._make_post_request(url, headers, payload, self.model)
            
            if not response_data:
                return None
                
            # Check for empty response
            if "candidates" not in response_data or not response_data["candidates"]:
                self.logger.error(f"Empty response from Google API: {response_data}")
                return None
            
            candidate = response_data["candidates"][0]
            
            # Check for truncation due to token limits
            if "finishReason" in candidate and candidate["finishReason"] == "MAX_TOKENS":
                self.logger.warning(f"Response truncated due to token limit for model {self.model}")
            
            # Format response to match OpenRouter format
            content = candidate["content"]["parts"][0]["text"]
            self.logger.debug(f"Received successful response from Google API")
            
            return {
                "choices": [{
                    "message": {
                        "content": content,
                        "role": "assistant"
                    }
                }]
            }
            
        except Exception:
            return await self._handle_common_exceptions(self.model, "requesting Google API")