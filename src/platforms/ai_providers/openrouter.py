import asyncio
from typing import Optional, Dict, Any, List, TypedDict, cast

import aiohttp

from src.platforms.ai_providers.base import BaseApiClient
from src.utils.decorators import retry_api_call


class ResponseDict(TypedDict, total=False):
    """Type for API responses."""
    choices: List[Dict[str, Any]]
    error: str
    details: str


class OpenRouterClient(BaseApiClient):
    """Client for handling OpenRouter API requests."""
    
    @retry_api_call(max_retries=3, initial_delay=1, backoff_factor=2, max_delay=30)
    async def chat_completion(self, model: str, messages: list, model_config: Dict[str, Any]) -> Optional[ResponseDict]:
        """Send a chat completion request to the OpenRouter API."""
        session = self._ensure_session()
        
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
        
        try:
            request_id = id(messages)
            self.logger.debug(f"Sending request #{request_id} to OpenRouter API with model: {model}")

            async with session.post(
                f"{self.base_url}/chat/completions", 
                headers=headers, 
                json=payload,
                timeout=300 
            ) as response:
                if response.status != 200:
                    return await self._handle_error_response(response, model)
                
                response_json = await response.json()
                if "error" in response_json:
                    self.logger.error(f"API returned error payload for model {model}: {response_json['error']}")
                    return cast(ResponseDict, response_json)
                    
                self.logger.debug(f"Received successful response from OpenRouter for model {model}")
                return cast(ResponseDict, response_json)
                    
        except asyncio.TimeoutError as e:
            self.logger.error(f"Timeout error when requesting model {model}: {e}")
            # Return a timeout error that can be recognized by retry logic
            return {"error": "timeout", "details": str(e)}
        except aiohttp.ClientError as e:
            self.logger.error(f"Network error when requesting model {model}: {type(e).__name__} - {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error when requesting model {model}: {type(e).__name__} - {e}")
            return None