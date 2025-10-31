import json
import re
from typing import Dict, Any, Optional

from src.utils.loader import config
from src.platforms.coingecko import CoinGeckoAPI
from src.html.html_generator import AnalysisHtmlGenerator
from src.logger.logger import Logger


class AnalysisPublisher:
    """Handles publishing of analysis results to Discord"""
    
    def __init__(self, 
                logger: Logger,
                html_generator: AnalysisHtmlGenerator,
                coingecko_api: CoinGeckoAPI,
                discord_notifier=None):
        """Initialize the publisher"""
        self.logger = logger
        self.html_generator = html_generator
        self.coingecko_api = coingecko_api
        self.discord_notifier = discord_notifier
        self.analysis_file_url = None
        
    def set_discord_notifier(self, discord_notifier) -> None:
        """Set Discord notifier after initialization (prevents circular dependencies)"""
        self.discord_notifier = discord_notifier
        
    async def publish_analysis(self, 
                              symbol: str,
                              timeframe: str,
                              analysis_result: Dict[str, Any], 
                              context) -> bool:
        """Publish analysis results to Discord"""
        if not analysis_result:
            self.logger.warning("No analysis results to publish")
            return False
        
        if "error" in analysis_result:
            error_message = analysis_result["error"]
            self.logger.error(f"⚠️ Analysis Error: {error_message}")
            return False
        
        raw_response = analysis_result.get("raw_response", "")
        language = analysis_result.get("language", None)
        
        # Retrieve article URLs from analysis result
        article_urls = analysis_result.get("article_urls", {})
        if not article_urls:
            self.logger.warning("No article URLs found in analysis result")
        
        # Extract detailed markdown content from raw response (simple method)
        detailed_text = self._extract_markdown_simple(raw_response)
        
        if detailed_text:
            self.logger.debug(f"Found {len(article_urls)} article URLs for references")
            
            # Prepare OHLCV data for chart generation
            ohlcv_data = self._prepare_chart_data(context, symbol, timeframe)
            
            if ohlcv_data:  # Only generate HTML if we have data
                # Prepare Discord analysis data for HTML integration
                discord_analysis_data = {
                    "analysis": analysis_result.get("analysis", {}),
                    "symbol": symbol,
                    "language": language,
                    "exchange": context.exchange if hasattr(context, 'exchange') else None,
                    "timeframe": timeframe
                }
                
                html_content = self.html_generator.generate_html_content(
                    f"{symbol} Detailed Analysis{(' in ' + language) if language else ''}",
                    detailed_text,
                    article_urls=article_urls,
                    ohlcv_data=ohlcv_data,
                    discord_analysis=discord_analysis_data
                )
                
                if html_content:
                    self.analysis_file_url = await self.discord_notifier.upload_analysis_content(
                        html_content,
                        symbol,
                        config.TEMPORARY_CHANNEL_ID_DISCORD
                    )
                    self.logger.debug(f"HTML analysis uploaded successfully: {self.analysis_file_url}")
                else:
                    self.logger.warning("HTML content generation failed")
            else:
                self.logger.warning("No OHLCV data available for HTML generation")
        else:
            self.logger.warning("No detailed markdown content found in response for HTML generation")
        
        await self._send_discord_embed(symbol, analysis_result)
        return True
        
    async def _send_discord_embed(self, symbol: str, analysis_result: Dict[str, Any]) -> None:
        """Create and send Discord embed with analysis results"""
        if not self.discord_notifier:
            self.logger.error("Cannot send Discord embed: notifier not initialized")
            return
            
        base_symbol = symbol.split('/')[0] if '/' in symbol else symbol
        
        # Try multiple exchanges for coin image in case one fails
        exchange_names = ["Binance", "KuCoin", "Gate.io"]
        icon_url = None
        
        for exchange_name in exchange_names:
            try:
                icon_url = await self.coingecko_api.get_coin_image(
                    base_symbol,
                    exchange_name
                )
                if icon_url:
                    break
            except Exception as e:
                self.logger.debug(f"Failed to get {base_symbol} image from {exchange_name}: {e}")
        
        embed = self.discord_notifier.create_analysis_embed(
            analysis_result,
            symbol,
            self.analysis_file_url,
            thumbnail_url=icon_url,
            language=analysis_result.get("language")
        )
        
        await self.discord_notifier.send_message(
            message="",
            channel_id=config.MAIN_CHANNEL_ID,
            embed=embed
        )
    
    def _extract_markdown_simple(self, raw_response: str) -> str:
        """Return markdown portion after removing any leading structured JSON dump."""
        if not raw_response:
            return ""

        cleaned_response = self._strip_structured_sections(raw_response)

        lines = cleaned_response.split('\n')
        for i, line in enumerate(lines):
            if line.strip().startswith('##'):
                markdown_body = '\n'.join(lines[i:]).strip()
                return self._strip_structured_sections(markdown_body)
        return self._strip_structured_sections(cleaned_response).strip()

    def _strip_structured_sections(self, text: str) -> str:
        """Remove JSON blocks emitted by the model so the HTML stays readable."""
        if not text:
            return ""

        # Drop fenced code blocks containing JSON or analysis payloads
        fenced_pattern = re.compile(r"```(?:json|analysis|structured)?\s*[\s\S]*?```", re.IGNORECASE)
        text = re.sub(fenced_pattern, "\n", text)

        stripped = text.lstrip()
        if stripped.startswith('{'):
            try:
                obj, end_idx = json.JSONDecoder().raw_decode(stripped)
                if isinstance(obj, dict) and "analysis" in obj:
                    stripped = stripped[end_idx:]
            except json.JSONDecodeError:
                pass
        return stripped.lstrip()
        
    def _prepare_chart_data(self, context, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
        """Prepare OHLCV and indicator data for chart generation"""
        ohlcv_data = None
        if not hasattr(context, 'ohlcv_candles') or context.ohlcv_candles is None:
            self.logger.warning("No OHLCV data available for chart generation")
            return None
            
        # Create OHLCV data package for chart generation
        ohlcv_data = {
            'ohlcv': context.ohlcv_candles,
            'symbol': symbol,
            'timeframe': timeframe
        }
        
        # Add technical indicators if available
        if hasattr(context, 'technical_history') and context.technical_history is not None:
            ohlcv_data['technical_history'] = context.technical_history
            
        if hasattr(context, 'technical_patterns') and context.technical_patterns is not None:
            ohlcv_data['patterns'] = context.technical_patterns
            
        return ohlcv_data
