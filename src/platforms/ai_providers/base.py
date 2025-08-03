from typing import Optional, Dict, Any

import aiohttp

from src.logger.logger import Logger


class BaseApiClient:
    """Base class for API clients with common functionality."""
    
    def __init__(self, api_key: str, base_url: str, logger: Logger) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.logger = logger
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def close(self) -> None:
        """Close the aiohttp session."""
        if self.session:
            try:
                self.logger.debug(f"Closing {self.__class__.__name__} session")
                await self.session.close()
                self.session = None
            except Exception as e:
                self.logger.error(f"Error closing session in {self.__class__.__name__}: {e}")
    
    def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure a session exists and return it."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def _handle_error_response(self, response: aiohttp.ClientResponse, model: str) -> Dict[str, Any]:
        """Handle error responses from APIs."""
        error_text = await response.text()
        self.logger.error(f"API Error for model {model}: Status {response.status} - {error_text}")
        
        error_details = {
            401: "Authentication error with API key. Check your API key.",
            403: "Permission denied. Your API key may not have access to this model.",
            404: f"Model {model} not found.",
            408: "Request timeout. The server took too long to respond.",
            429: "Rate limit exceeded. Consider upgrading your plan." if "Rate limit exceeded" in error_text else "Too many requests. Temporary rate limit."
        }
        
        if response.status in error_details:
            self.logger.error(error_details[response.status])
            
        if response.status >= 500:
            self.logger.error(f"Server error. The service may be experiencing issues.")
            
        if "Rate limit exceeded" in error_text:
            return {"error": "rate_limit", "details": error_text}
        
        if response.status == 408 or "timeout" in error_text.lower():
            return {"error": "timeout", "details": error_text}
                
        return {"error": f"http_{response.status}", "details": error_text}