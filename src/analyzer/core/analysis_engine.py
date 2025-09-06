from typing import Dict, Any

import config.config as config
from src.platforms.alternative_me import AlternativeMeAPI
from src.platforms.coingecko import CoinGeckoAPI
from .analysis_context import AnalysisContext
from ..publishing.analysis_publisher import AnalysisPublisher
from .analysis_result_processor import AnalysisResultProcessor
from ..calculations.indicator_calculator import IndicatorCalculator
from ..data.market_data_collector import MarketDataCollector
from ..calculations.market_metrics_calculator import MarketMetricsCalculator
from ..prompts.prompt_builder import PromptBuilder
from src.html.html_generator import AnalysisHtmlGenerator
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
             discord_notifier=None) -> None:
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
            self.timeframe = getattr(config, "TIMEFRAME", "1h")
            self.limit = getattr(config, "CANDLE_LIMIT", 100)
        except Exception as e:
            self.logger.exception(f"Error loading configuration values: {e}.")
            raise

        # Initialize specialized components
        self.model_manager = ModelManager(logger)
        self.indicator_calculator = IndicatorCalculator(logger=logger)
        self.prompt_builder = PromptBuilder(
            timeframe=self.timeframe, 
            logger=logger,
            indicator_calculator=self.indicator_calculator
        )
        self.html_generator = AnalysisHtmlGenerator(logger=logger)
        
        # Create specialized components for separated concerns
        self.data_collector = MarketDataCollector(
            logger=logger, 
            rag_engine=rag_engine,
            alternative_me_api=alternative_me_api
        )
        
        # Pass indicator_calculator to metrics_calculator to reduce code duplication
        self.metrics_calculator = MarketMetricsCalculator(
            logger=logger,
            indicator_calculator=self.indicator_calculator
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
        self.discord_notifier = discord_notifier
        
        # Use the token counter from model_manager
        self.token_counter = self.model_manager.token_counter

    def set_discord_notifier(self, discord_notifier):
        """Set the discord notifier after initialization to avoid circular dependencies"""
        self.discord_notifier = discord_notifier
        self.publisher.set_discord_notifier(discord_notifier)

    def initialize_for_symbol(self, symbol: str, exchange, language=None) -> None:
        """Initialize the analyzer for a specific symbol and exchange"""
        self.symbol = symbol
        self.exchange = exchange
        self.base_symbol = symbol.split('/')[0] if '/' in symbol else symbol
        self.language = language
        
        # Initialize analysis context
        self.context = AnalysisContext(symbol)
        self.context.exchange = exchange.name if hasattr(exchange, 'name') else str(exchange)
        self.context.timeframe = self.timeframe
        
        # Create data fetcher and initialize data collector
        from ..data.data_fetcher import DataFetcher
        data_fetcher = DataFetcher(exchange=exchange, logger=self.logger)
        
        self.data_collector.initialize(
            data_fetcher=data_fetcher, 
            symbol=symbol, 
            exchange=exchange,
            timeframe=self.timeframe,
            limit=self.limit
        )
        
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

    async def analyze_market(self) -> Dict[str, Any]:
        """Orchestrate the complete market analysis workflow"""
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
            
            # Step 2: Calculate technical indicators
            await self._calculate_technical_indicators()
            
            # Step 3: Process long-term data if available
            await self._process_long_term_data()
            
            # Step 4: Calculate market metrics for different periods
            # Use data_collector's method instead of the local _extract_ohlcv_data method
            data = self.data_collector.extract_ohlcv_data(self.context)
            self.metrics_calculator.update_period_metrics(data, self.context)
            
            # Step 5: Run technical pattern analysis
            technical_patterns = self.indicator_calculator.detect_patterns(
                self.context.ohlcv_candles,
                self.context.technical_history
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
            
            # Step 7: Build prompts for AI analysis
            self.prompt_builder.language = self.language
            system_prompt = self.prompt_builder.build_system_prompt(self.symbol)
            prompt = self.prompt_builder.build_prompt(self.context)
            # Step 8: Process analysis through appropriate processor
            if config.TEST_ENVIRONMENT:
                self.logger.debug(f"TEST_ENVIRONMENT is True - using mock analysis")
                analysis_result = self.result_processor.process_mock_analysis(
                    self.symbol, 
                    self.context.current_price,
                    self.language,
                    self.article_urls
                )
            else:
                analysis_result = await self.result_processor.process_analysis(
                    system_prompt, 
                    prompt,
                    self.language
                )
                
            # Add article URLs to result
            analysis_result["article_urls"] = self.article_urls
            

            # Store the result for later publication
            self.last_analysis_result = analysis_result
                
            # Reset custom instructions for next run
            self.prompt_builder.custom_instructions = []
            
            return analysis_result
            
        except Exception as e:
            self.logger.exception(f"Analysis failed: {e}")
            return {"error": str(e), "recommendation": "HOLD"}

    async def _calculate_technical_indicators(self) -> None:
        """Calculate technical indicators using the indicator calculator"""
        indicators = self.indicator_calculator.get_indicators(self.context.ohlcv_candles)
        
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
            long_term_indicators = self.indicator_calculator.get_long_term_indicators(
                self.context.long_term_data['data']
            )
            
            # Update the context with calculated metrics
            self.context.long_term_data.update(long_term_indicators)
            
            self.logger.debug(f"Long-term metrics calculated: price_change={self.context.long_term_data.get('price_change')}, "
                             f"volatility={self.context.long_term_data.get('volatility')}")
        except Exception as e:
            self.logger.error(f"Error processing long-term data: {str(e)}")

    async def publish_analysis(self) -> bool:
        """Publish analysis results using the publisher component"""
        if not self.last_analysis_result:
            self.logger.warning("No analysis results available to publish")
            return False
            
        return await self.publisher.publish_analysis(
            symbol=self.symbol,
            timeframe=self.timeframe,
            analysis_result=self.last_analysis_result,
            context=self.context
        )