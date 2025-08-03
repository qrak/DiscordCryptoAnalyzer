import asyncio
import functools
import logging
import traceback
import socket
from typing import Any

import ccxt
import aiohttp
import aiodns


def retry_async(max_retries: int = -1, initial_delay: float = 1, backoff_factor: float = 2, max_delay: float = 3600):
    def decorator(func: Any):
        @functools.wraps(func)
        async def wrapper(self, *args: Any, **kwargs: Any):
            logger = getattr(self, 'logger', None)
            pair = kwargs.get('pair') or (args[0] if args and isinstance(args[0], str) else None)

            def log_message(level: str, message: str) -> None:
                full_message = f"{pair} - {message}" if pair else message
                log_func = getattr(logger, level) if logger else getattr(logging, level)
                if logger and hasattr(logger, 'findCaller'):
                    # stacklevel=3 makes the log record show the caller of log_message as the source
                    log_func(full_message, stacklevel=3)
                else:
                    log_func(full_message)

            class_name = self.__class__.__name__
            func_name = func.__name__
            num_retries_done = 0
            current_retry_delay = initial_delay

            # Helper to determine log prefix template for common retryable errors
            def _get_log_prefix_template_for_common_errors(e: Exception) -> str:
                error_msg_lower = str(e).lower()
                if isinstance(e, (ccxt.RateLimitExceeded, ccxt.DDoSProtection)) or \
                   "rate limit" in error_msg_lower or "too many requests" in error_msg_lower:
                    return "Rate limit/DDoS. Retry {}"
                elif isinstance(e, (ccxt.RequestTimeout, TimeoutError, asyncio.TimeoutError)) or "timeout" in error_msg_lower:
                    # Retry on any error message containing 'timeout'
                    return "Timeout. Retry {}"
                elif isinstance(e, (ccxt.NetworkError, aiohttp.ClientConnectorError, aiohttp.ClientOSError, socket.gaierror, ConnectionResetError)):
                    return "Network issue. Retry {}"
                elif isinstance(e, OSError) and 'network is unreachable' in error_msg_lower:
                    return "Network unreachable. Retry {}"
                # Default for ConnectionResetError and other errors in this category
                return "Retry {}"

            # Helper to check if a ccxt.ExchangeError is due to rate limiting
            def _is_exchange_rate_limit_error(e: ccxt.ExchangeError) -> bool:
                error_msg_lower = str(e).lower()
                rate_limit_phrases = [
                    'too many requests', 'rate limit', '429', 
                    'ratelimit', 'ddos protection', 'system-level rate limit exceeded'
                ]
                return any(phrase in error_msg_lower for phrase in rate_limit_phrases)

            # Helper to perform a single retry attempt (check max, log, sleep, update delay)
            async def _handle_retry_attempt(current_exception: Exception, log_prefix_template: str):
                nonlocal num_retries_done, current_retry_delay # Allow modification of wrapper's variables
                
                error_type_str = type(current_exception).__name__
                error_msg_str = str(current_exception)

                if max_retries != -1 and num_retries_done >= max_retries:
                    log_message('error', f"Function {class_name}.{func_name} failed after {max_retries} retries. Last error: {error_type_str} - {error_msg_str}")
                    raise current_exception # Re-raise the original exception to signal exhaustion
                
                num_retries_done += 1
                actual_log_prefix = log_prefix_template.format(num_retries_done)
                
                log_message('warning',
                            f"{actual_log_prefix} for {class_name}.{func_name} in {current_retry_delay:.2f} seconds. "
                            f"Type: {error_type_str}, Error: {error_msg_str}")
                await asyncio.sleep(current_retry_delay)
                current_retry_delay = min(current_retry_delay * backoff_factor, max_delay)
                # If this function completes without raising, the main loop will continue for another attempt

            while True:
                try:
                    result = await func(self, *args, **kwargs)
                    return result # Success 

                except (ccxt.NetworkError, ccxt.RequestTimeout,
                        ccxt.DDoSProtection, ccxt.RateLimitExceeded, TimeoutError, ConnectionResetError,
                        aiohttp.ClientConnectorError, aiohttp.ClientOSError, asyncio.TimeoutError, socket.gaierror, OSError, aiodns.error.DNSError) as e:
                    log_prefix_template = _get_log_prefix_template_for_common_errors(e)
                    await _handle_retry_attempt(e, log_prefix_template)
                    # If _handle_retry_attempt re-raised 'e' (max retries), it propagates out.
                    # Otherwise, the loop continues.
                
                except ccxt.ExchangeError as e:
                    if _is_exchange_rate_limit_error(e):
                        log_prefix_template = "Rate limit (ExchangeError). Retry {}"
                        await _handle_retry_attempt(e, log_prefix_template)
                    else:
                        # Non-retryable ExchangeErrors
                        log_message('error', f"Non-retryable ExchangeError in {class_name}.{func_name}: {type(e).__name__} - {str(e)}")
                        raise
                except Exception as e: # Catch-all for truly unexpected errors
                    log_message('error', f"Unexpected error in {class_name}.{func_name}: {type(e).__name__} - {str(e)}\n{traceback.format_exc()}")
                    raise
        return wrapper
    return decorator

def retry_api_call(max_retries: int = 3, initial_delay: float = 1, backoff_factor: float = 2, max_delay: float = 60):
    def decorator(func: Any):
        @functools.wraps(func)
        async def wrapper(self, *args: Any, **kwargs: Any):
            logger = getattr(self, 'logger', None)
            if not logger:
                logger = logging.getLogger(__name__)
                
            # Get model name for better logging
            model = kwargs.get('model', args[0] if args else "unknown")
            
            retries = 0
            delay = initial_delay
            
            while retries <= max_retries:
                try:
                    response = await func(self, *args, **kwargs)
                    
                    # Check if we got an error response that should be retried
                    if isinstance(response, dict) and response.get('error'):
                        error_type = response.get('error')
                        
                        # Check for error types that should trigger retries
                        should_retry = False
                        
                        # Handle 500 errors
                        if isinstance(error_type, dict) and error_type.get('code') == 500:
                            should_retry = True
                        
                        # Handle timeout errors
                        elif error_type == "timeout":
                            should_retry = True
                            
                        if should_retry:
                            retries += 1
                            if retries > max_retries:
                                logger.error(f"API call to model {model} failed after {max_retries} retries")
                                return response
                                
                            wait_time = min(delay * (backoff_factor ** (retries - 1)), max_delay)
                            logger.warning(f"API returned error '{error_type}' for model {model}. Retrying in {wait_time:.2f}s ({retries}/{max_retries})")
                            await asyncio.sleep(wait_time)
                            continue
                    
                    # No error or different error, return the response
                    return response
                    
                except Exception as e:
                    logger.error(f"Error in API call to model {model}: {type(e).__name__} - {str(e)}")
                    logger.error(f"Traceback:\n{traceback.format_exc()}")
                    raise
                    
            # This should not be reached due to the return in the loop
            logger.error(f"API call to model {model} failed after exhausting all retries")
            return None
            
        return wrapper
    return decorator