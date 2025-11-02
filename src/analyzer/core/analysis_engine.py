from typing import Dict, Any, Optional
import io

from src.utils.loader import config
from src.utils.timeframe_validator import TimeframeValidator
from src.platforms.alternative_me import AlternativeMeAPI
from src.platforms.coingecko import CoinGeckoAPI
from .analysis_context import AnalysisContext
from ..publishing.analysis_publisher import AnalysisPublisher
from .analysis_result_processor import AnalysisResultProcessor
from ..calculations.technical_calculator import TechnicalCalculator
from ..calculations.pattern_analyzer import PatternAnalyzer
from ..data.market_data_collector import MarketDataCollector
from ..calculations.market_metrics_calculator import MarketMetricsCalculator
from ..prompts.prompt_builder import PromptBuilder
from src.html.html_generator import AnalysisHtmlGenerator
from src.html.chart_generator import ChartGenerator
from src.logger.logger import Logger
from src.models.manager import ModelManager
from src.rag import RagEngine

import numpy as np


class AnalysisEngine:
    """Orchestrates market data collection, analysis, and publication"""
    
    def __init__(self, logger: Logger,
             rag_engine: RagEngine,
             coingecko_api: CoinGeckoAPI,
             alternative_me_api: AlternativeMeAPI = None,
             cryptocompare_api=None,
             discord_notifier=None,
             format_utils=None,
             data_processor=None) -> None:
        self.logger = logger

        # Basic properties
        self.exchange = None
        self.symbol = None
        self.base_symbol = None
        self.context = None
        self.language = None
        self.article_urls = {}
        self.last_analysis_result = None

        # Load configuration
        try:
            self.timeframe = config.TIMEFRAME
            self.limit = config.CANDLE_LIMIT
            
            # Validate timeframe
            if not TimeframeValidator.validate(self.timeframe):
                self.logger.warning(
                    f"Timeframe '{self.timeframe}' is not fully supported. "
                    f"Supported timeframes: {', '.join(TimeframeValidator.SUPPORTED_TIMEFRAMES)}. "
                    f"Proceeding but expect potential calculation errors."
                )
        except Exception as e:
            self.logger.exception(f"Error loading configuration values: {e}.")
            raise

        # Initialize specialized components
        self.model_manager = ModelManager(logger)
        self.technical_calculator = TechnicalCalculator(logger=logger, format_utils=format_utils)
        self.pattern_analyzer = PatternAnalyzer(logger=logger, format_utils=format_utils)
        self.prompt_builder = PromptBuilder(
            timeframe=self.timeframe, 
            logger=logger,
            technical_calculator=self.technical_calculator,
            config=config,
            format_utils=format_utils,
            data_processor=data_processor
        )
        self.html_generator = AnalysisHtmlGenerator(logger=logger, format_utils=format_utils)
        self.chart_generator = ChartGenerator(logger=logger, config=config, format_utils=format_utils)
        
        # Create specialized components for separated concerns
        self.data_collector = MarketDataCollector(
            logger=logger, 
            rag_engine=rag_engine,
            alternative_me_api=alternative_me_api
        )
        
        # Pass indicator_calculator to metrics_calculator to reduce code duplication
        self.metrics_calculator = MarketMetricsCalculator(
            logger=logger
        )
        
        self.result_processor = AnalysisResultProcessor(
            model_manager=self.model_manager, 
            logger=logger
        )
        
        self.publisher = AnalysisPublisher(
            logger=logger,
            html_generator=self.html_generator,
            coingecko_api=coingecko_api,
            discord_notifier=discord_notifier
        )

        # Store references to external services
        self.rag_engine = rag_engine
        self.coingecko_api = coingecko_api
        self.cryptocompare_api = cryptocompare_api
        self.discord_notifier = discord_notifier
        
        # Use the token counter from model_manager
        self.token_counter = self.model_manager.token_counter

    def set_discord_notifier(self, discord_notifier):
        """Set the discord notifier after initialization to avoid circular dependencies"""
        self.discord_notifier = discord_notifier
        self.publisher.set_discord_notifier(discord_notifier)

    def initialize_for_symbol(self, symbol: str, exchange, language=None, timeframe=None) -> None:
        """
        Initialize the analyzer for a specific symbol and exchange.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            exchange: Exchange instance
            language: Optional language for analysis output
            timeframe: Optional timeframe override (uses config default if None)
        """
        self.symbol = symbol
        self.exchange = exchange
        self.base_symbol = symbol.split('/')[0] if '/' in symbol else symbol
        self.language = language
        
        # Use provided timeframe or fall back to config
        effective_timeframe = timeframe if timeframe else self.timeframe
        
        # Validate effective timeframe
        try:
            effective_timeframe = TimeframeValidator.validate_and_normalize(effective_timeframe)
        except ValueError as e:
            self.logger.warning(f"Timeframe validation failed: {e}. Using config default: {self.timeframe}")
            effective_timeframe = self.timeframe
        
        # Initialize analysis context with effective timeframe
        self.context = AnalysisContext(symbol)
        self.context.exchange = exchange.name if hasattr(exchange, 'name') else str(exchange)
        self.context.timeframe = effective_timeframe
        
        # Create data fetcher and initialize data collector
        from ..data.data_fetcher import DataFetcher
        data_fetcher = DataFetcher(exchange=exchange, logger=self.logger)
        
        self.data_collector.initialize(
            data_fetcher=data_fetcher, 
            symbol=symbol, 
            exchange=exchange,
            timeframe=effective_timeframe,
            limit=self.limit
        )
        
        # Update prompt builder and context builder with effective timeframe
        if hasattr(self, 'prompt_builder'):
            self.prompt_builder.timeframe = effective_timeframe
        
        if hasattr(self.prompt_builder, 'context_builder'):
            self.prompt_builder.context_builder.timeframe = effective_timeframe
        
        # Reset analysis state
        self.article_urls = {}
        self.last_analysis_result = None
        
        # Reset token counter for new analysis using the model manager's token counter
        self.token_counter.reset_session_stats()

    async def close(self) -> None:
        """Clean up resources with proper null checks"""
        try:
            if hasattr(self, 'exchange') and self.exchange is not None:
                await self.exchange.close()
                
            if hasattr(self, 'model_manager') and self.model_manager is not None:
                await self.model_manager.close()
                
            if hasattr(self, 'rag_engine') and self.rag_engine is not None:
                await self.rag_engine.close()
        except Exception as e:
            self.logger.error(f"Error during MarketAnalyzer cleanup: {e}")

    async def analyze_market(self, provider: Optional[str] = None, model: Optional[str] = None) -> Dict[str, Any]:
        """
        Orchestrate the complete market analysis workflow.
        
        Args:
            provider: Optional AI provider override (admin only)
            model: Optional AI model override (admin only)
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            # Step 1: Collect all required data
            data_result = await self.data_collector.collect_data(self.context)
            if not data_result["success"]:
                self.logger.error(f"Failed to collect market data: {data_result['errors']}")
                return {"error": "Failed to collect market data", "details": data_result['errors']}
            
            # Store article URLs
            self.article_urls = self.data_collector.article_urls
            
            # Fetch market overview
            try:
                market_overview = await self.rag_engine.get_market_overview()
                self.context.market_overview = market_overview
                self.logger.debug("Market overview data fetched and added to context")
            except Exception as e:
                self.logger.warning(f"Failed to fetch market overview: {e}")
                # Initialize as empty dict to avoid AttributeError
                self.context.market_overview = {}
            
            # Fetch market microstructure (order book, trades, funding rate)
            try:
                microstructure = await self.data_collector.data_fetcher.fetch_market_microstructure(self.symbol)
                self.context.market_microstructure = microstructure
                self.logger.debug(f"Market microstructure data fetched for {self.symbol}")
            except Exception as e:
                self.logger.warning(f"Failed to fetch market microstructure: {e}")
                self.context.market_microstructure = {}
            
            # Fetch cryptocurrency details if CryptoCompare is available
            if self.cryptocompare_api:
                try:
                    coin_details = await self.cryptocompare_api.get_coin_details(self.base_symbol)
                    self.context.coin_details = coin_details
                    if coin_details:
                        self.logger.debug(f"Coin details for {self.base_symbol} fetched and added to context")
                    else:
                        self.logger.warning(f"No coin details found for {self.base_symbol}")
                except Exception as e:
                    self.logger.warning(f"Failed to fetch coin details for {self.base_symbol}: {e}")
                    self.context.coin_details = {}
            
            # Step 2: Calculate technical indicators
            await self._calculate_technical_indicators()
            
            # Step 3: Process long-term data if available
            await self._process_long_term_data()
            
            # Step 4: Calculate market metrics for different periods
            # Use data_collector's method instead of the local _extract_ohlcv_data method
            data = self.data_collector.extract_ohlcv_data(self.context)
            self.metrics_calculator.update_period_metrics(data, self.context)
            
            # Step 5: Run technical pattern analysis
            technical_patterns = self.pattern_analyzer.detect_patterns(
                self.context.ohlcv_candles,
                self.context.technical_history,
                self.context.long_term_data if hasattr(self.context, 'long_term_data') else None,
                self.context.timestamps
            )
            
            # If we found meaningful patterns, add them to context
            if any(technical_patterns.values()):
                self.context.technical_patterns = technical_patterns
            
            # Step 6: Add market context to prompt builder if available
            market_context = data_result.get("market_context")
            if market_context:
                self.prompt_builder.add_custom_instruction(market_context)
            else:
                self.logger.warning(f"No market context available for {self.symbol}")
            
                        # Step 7: Check if chart analysis is supported and build system prompt accordingly
            self.prompt_builder.language = self.language
            has_chart_analysis = self.model_manager.supports_image_analysis(provider)
            system_prompt = self.prompt_builder.build_system_prompt(self.symbol, has_chart_analysis)
            
            # Step 8: Generate chart image for AI analysis (Google AI only)
            chart_image = None
            if has_chart_analysis:
                try:
                    self.logger.info("Generating chart image for AI pattern analysis")
                    chart_image = self.chart_generator.create_chart_image(
                        ohlcv=self.context.ohlcv_candles,
                        technical_history=self.context.technical_history,
                        pair_symbol=self.symbol,
                        timeframe=self.context.timeframe,
                        save_to_disk=config.DEBUG_SAVE_CHARTS,
                        timestamps=self.context.timestamps
                    )
                    
                except Exception as e:
                    self.logger.warning(f"Failed to generate chart image for AI analysis: {e}")
                    chart_image = None
                    has_chart_analysis = False
            
            # Build prompt with chart analysis information
            prompt = self.prompt_builder.build_prompt(self.context, has_chart_analysis)
            
            # Step 9: Process analysis through appropriate processor
            if config.TEST_ENVIRONMENT:
                self.logger.debug(f"TEST_ENVIRONMENT is True - using mock analysis")
                analysis_result = self.result_processor.process_mock_analysis(
                    self.symbol,
                    self.context.current_price,
                    self.language,
                    self.article_urls,
                    technical_history=getattr(self.context, 'technical_history', None),
                    technical_data=getattr(self.context, 'technical_data', None)
                )
            else:
                # Log provider/model override if provided
                if provider and model:
                    self.logger.info(f"Using admin-specified provider: {provider}, model: {model}")
                
                # First try chart analysis if available
                if chart_image is not None and self.model_manager.supports_image_analysis(provider):
                    prov_name, model_name = self.model_manager.describe_provider_and_model(provider, model, chart=True)
                    prov_label = prov_name.upper() if prov_name else "UNKNOWN"
                    self.logger.info(
                        "Attempting chart image analysis via %s (model: %s)",
                        prov_label,
                        model_name
                    )
                    try:
                        analysis_result = await self.result_processor.process_analysis(
                            system_prompt, 
                            prompt,
                            self.language,
                            chart_image=chart_image,
                            provider=provider,
                            model=model
                        )
                    except ValueError:
                        # Chart analysis failed, rebuild prompts without chart analysis and try again
                        self.logger.warning("Chart analysis failed, rebuilding prompts for text-only analysis")
                        has_chart_analysis = False
                        system_prompt = self.prompt_builder.build_system_prompt(self.symbol, has_chart_analysis)
                        prompt = self.prompt_builder.build_prompt(self.context, has_chart_analysis)
                        
                        analysis_result = await self.result_processor.process_analysis(
                            system_prompt, 
                            prompt,
                            self.language,
                            chart_image=None,
                            provider=provider,
                            model=model
                        )
                else:
                    # No chart analysis available, use text-only
                    analysis_result = await self.result_processor.process_analysis(
                        system_prompt, 
                        prompt,
                        self.language,
                        chart_image=None,
                        provider=provider,
                        model=model
                    )
                
            # Add article URLs to result
            analysis_result["article_urls"] = self.article_urls
            # Add timeframe to result for Discord embed and HTML
            analysis_result["timeframe"] = self.context.timeframe
            # Add provider and model info to result
            actual_provider, actual_model = self.model_manager.describe_provider_and_model(provider, model, chart=has_chart_analysis)
            analysis_result["provider"] = actual_provider
            analysis_result["model"] = actual_model
            

            # Store the result for later publication
            self.last_analysis_result = analysis_result
                
            # Reset custom instructions for next run
            self.prompt_builder.custom_instructions = []
            
            return analysis_result
            
        except Exception as e:
            self.logger.exception(f"Analysis failed: {e}")
            return {"error": str(e), "recommendation": "HOLD"}

    async def _calculate_technical_indicators(self) -> None:
        """Calculate technical indicators using the technical calculator"""
        indicators = self.technical_calculator.get_indicators(self.context.ohlcv_candles)
        
        # Store history in context
        self.context.technical_history = indicators
        
        # Extract latest values for each indicator for the technical_data
        technical_data = {}
        for key, values in indicators.items():
            try:
                # Handle different types of NumPy array returns based on shape
                if values is None or np.isnan(values).all():
                    continue
                    
                # Check if it's a standard 1D array (most indicators)
                if isinstance(values, np.ndarray) and values.ndim == 1:
                    technical_data[key] = float(values[-1])
                    
                # Handle 2D arrays - common for indicators that return multiple series like vortex_indicator
                elif isinstance(values, np.ndarray) and values.ndim > 1:
                    # For 2D array, take the last value from each series
                    technical_data[key] = [float(values[i, -1]) for i in range(values.shape[0])]
                    
                # Handle tuples - common return type from indicator functions (e.g., MACD, support_resistance)
                elif isinstance(values, tuple) and all(isinstance(item, np.ndarray) for item in values):
                    # For tuple of arrays, store as list of last values
                    technical_data[key] = [float(array[-1]) for array in values]
                    
                # Handle lists - could be lists of arrays or scalar values
                elif isinstance(values, list):
                    if all(isinstance(item, np.ndarray) for item in values):
                        technical_data[key] = [float(array[-1]) for array in values]
                    else:
                        technical_data[key] = values
                        
                # Handle scalar values
                else:
                    technical_data[key] = float(values)
                    
            except (IndexError, TypeError, ValueError) as e:
                self.logger.warning(f"Could not process indicator '{key}': {e}")
                continue
                
        self.context.technical_data = technical_data

    async def _process_long_term_data(self) -> None:
        """Process long-term historical data and calculate metrics"""
        if not hasattr(self.context, 'long_term_data') or self.context.long_term_data is None:
            self.logger.debug("No long-term data available to process")
            return
            
        if 'data' not in self.context.long_term_data or self.context.long_term_data['data'] is None:
            self.logger.debug("Long-term data contains no OHLCV data")
            return
            
        try:
            # Get long-term indicators and metrics
            long_term_indicators = self.technical_calculator.get_long_term_indicators(
                self.context.long_term_data['data']
            )
            
            # Update the context with calculated metrics
            self.context.long_term_data.update(long_term_indicators)
            
            self.logger.debug(f"Long-term metrics calculated: price_change={self.context.long_term_data.get('price_change')}, "
                             f"volatility={self.context.long_term_data.get('volatility')}")
        except Exception as e:
            self.logger.error(f"Error processing long-term data: {str(e)}")
        
        # Calculate weekly macro (if available)
        if hasattr(self.context, 'weekly_ohlcv') and self.context.weekly_ohlcv is not None:
            try:
                self.logger.info("Calculating weekly macro indicators...")
                weekly_macro = self.technical_calculator.get_weekly_macro_indicators(self.context.weekly_ohlcv)
                self.context.weekly_macro_indicators = weekly_macro
                
                if 'weekly_macro_trend' in weekly_macro:
                    trend = weekly_macro['weekly_macro_trend']
                    self.logger.info(f"Weekly Macro: {trend.get('trend_direction')} ({trend.get('confidence_score')}%)")
                    if trend.get('cycle_phase'):
                        self.logger.info(f"Cycle Phase: {trend['cycle_phase']}")
            except Exception as e:
                self.logger.error(f"Error calculating weekly macro indicators: {str(e)}")
                self.context.weekly_macro_indicators = None
        else:
            self.context.weekly_macro_indicators = None

    async def publish_analysis(self) -> bool:
        """Publish analysis results using the publisher component"""
        if not self.last_analysis_result:
            self.logger.warning("No analysis results available to publish")
            return False
            
        return await self.publisher.publish_analysis(
            symbol=self.symbol,
            timeframe=self.context.timeframe,
            analysis_result=self.last_analysis_result,
            context=self.context
        )