from typing import Optional, Dict, Any, List, TypedDict, cast

from src.platforms.ai_providers.base import BaseApiClient
from src.utils.decorators import retry_api_call


class ResponseDict(TypedDict, total=False):
    """Type for API responses."""
    error: str


class OpenRouterClient(BaseApiClient):
    """Client for handling OpenRouter API requests."""
    
    @retry_api_call(max_retries=3, initial_delay=1, backoff_factor=2, max_delay=30)
    async def chat_completion(self, model: str, messages: list, model_config: Dict[str, Any]) -> Optional[ResponseDict]:
        """Send a chat completion request to the OpenRouter API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "Kuruś Crypto Analyzer",
            "X-Title": "Kuruś Crypto Analyzer"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            **model_config
        }
        
        url = f"{self.base_url}/chat/completions"
        response = await self._make_post_request(url, headers, payload, model, timeout=600)
        
        return cast(ResponseDict, response) if response else None