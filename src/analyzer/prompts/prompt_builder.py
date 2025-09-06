import numpy as np
from typing import Any, Dict, List, Optional, TypedDict

from src.logger.logger import Logger
from ..calculations.indicator_calculator import IndicatorCalculator
from .template_manager import TemplateManager
from ..formatting.market_analysis.market_overview_formatter import MarketOverviewFormatter
from ..formatting.technical_analysis.technical_formatter import TechnicalAnalysisFormatter
from .context_builder import ContextBuilder


class AnalysisContext(TypedDict):
    """Expected structure for the analysis context passed to PromptBuilder"""
    symbol: str
    current_price: float
    sentiment: Dict[str, Any]
    market_overview: Optional[Dict[str, Any]]
    technical_data: Dict[str, Any]
    market_metrics: Dict[str, Any]
    long_term_data: Dict[str, Any]
    ohlcv_candles: np.ndarray
    technical_patterns: Optional[Dict[str, Any]]


class PromptBuilder:
    def __init__(self, timeframe: str = "1h", logger: Optional[Logger] = None, indicator_calculator: Optional[IndicatorCalculator] = None) -> None:
        """Initialize the PromptBuilder
        
        Args:
            timeframe: The primary timeframe for analysis (e.g. "1h")
            logger: Optional logger instance for debugging
            indicator_calculator: Calculator for technical indicators
        """
        self.timeframe = timeframe
        self.logger = logger
        self.custom_instructions: list[str] = []
        self.language: Optional[str] = None
        self.context: Optional[AnalysisContext] = None
        self.indicator_calculator = indicator_calculator or IndicatorCalculator(logger)
        
        # Access indicator thresholds from the calculator
        self.INDICATOR_THRESHOLDS = self.indicator_calculator.INDICATOR_THRESHOLDS
        
        # Initialize component managers
        self.template_manager = TemplateManager(logger)
        self.market_overview_formatter = MarketOverviewFormatter(logger)
        self.technical_analysis_formatter = TechnicalAnalysisFormatter(self.indicator_calculator, logger)
        self.context_builder = ContextBuilder(timeframe, logger)

    def build_prompt(self, context: AnalysisContext) -> str:
        """Build the complete prompt using component managers.
        
        Args:
            context: Analysis context containing all required data
            
        Returns:
            str: Complete formatted prompt
        """
        self.context = context

        sections = [
            self.context_builder.build_trading_context(context),
            self.context_builder.build_sentiment_section(context.sentiment),
        ]

        # Add market overview first before technical analysis to give it more prominence
        if context.market_overview:
            sections.append(self.market_overview_formatter.format_market_overview(context.market_overview))

        sections.extend([
            self.context_builder.build_market_data_section(context.ohlcv_candles),
            self.technical_analysis_formatter.format_technical_analysis(context, self.timeframe),
            self.context_builder.build_market_period_metrics_section(context.market_metrics, self.indicator_calculator),
            self.context_builder.build_long_term_analysis_section(context.long_term_data, context.current_price, self.indicator_calculator),
        ])

        # Add custom instructions if available
        if self.custom_instructions:
            sections.append("\n".join(self.custom_instructions))

        # Check if we have advanced support/resistance detected
        advanced_support_resistance_detected = self._has_advanced_support_resistance()

        # Add analysis steps right before response template
        sections.append(self.template_manager.build_analysis_steps(context.symbol, advanced_support_resistance_detected))

        # Response template should always be last
        sections.append(self.template_manager.build_response_template())

        final_prompt = "\n\n".join(filter(None, sections))

        return final_prompt
    
    def build_system_prompt(self, symbol: str) -> str:
        """Build system prompt using template manager.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            str: Formatted system prompt
        """
        return self.template_manager.build_system_prompt(symbol, self.language)

    def add_custom_instruction(self, instruction: str) -> None:
        """Add custom instruction to the prompt.
        
        Args:
            instruction: Custom instruction to add
        """
        self.custom_instructions.append(instruction)
    
    def _has_advanced_support_resistance(self) -> bool:
        """Check if advanced support/resistance indicators are detected.
        
        Returns:
            bool: True if advanced S/R indicators are available
        """
        if not (hasattr(self, 'context') and hasattr(self.context, 'technical_data')):
            return False
            
        td = self.context.technical_data
        if 'support_resistance' not in td:
            return False
            
        sr = td['support_resistance']
        return len(sr) == 2 and not (np.isnan(sr[0]) and np.isnan(sr[1]))

    # ============================================================================
    # BACKWARD COMPATIBILITY METHODS - Delegate to component managers
    # ============================================================================
    
    def _build_trading_context(self) -> str:
        """Build trading context section - delegates to context builder."""
        return self.context_builder.build_trading_context(self.context)
    
    def _build_sentiment_section(self) -> str:
        """Build sentiment section - delegates to context builder."""
        return self.context_builder.build_sentiment_section(self.context.sentiment if hasattr(self.context, 'sentiment') else None)
    
    def _build_market_overview_section(self) -> str:
        """Build market overview section - delegates to market overview formatter."""
        return self.market_overview_formatter.format_market_overview(self.context.market_overview if hasattr(self.context, 'market_overview') else None)
    
    def _build_market_data(self) -> str:
        """Build market data section - delegates to context builder."""
        return self.context_builder.build_market_data_section(self.context.ohlcv_candles if hasattr(self.context, 'ohlcv_candles') else None)
    
    def _build_technical_analysis(self) -> str:
        """Build technical analysis section - delegates to technical analysis formatter."""
        return self.technical_analysis_formatter.format_technical_analysis(self.context, self.timeframe)
    
    def _build_market_period_metrics(self) -> str:
        """Build market period metrics section - delegates to context builder."""
        return self.context_builder.build_market_period_metrics_section(
            self.context.market_metrics if hasattr(self.context, 'market_metrics') else None,
            self.indicator_calculator
        )
    
    def _build_long_term_analysis(self) -> str:
        """Build long-term analysis section - delegates to context builder."""
        return self.context_builder.build_long_term_analysis_section(
            self.context.long_term_data if hasattr(self.context, 'long_term_data') else None,
            self.context.current_price if hasattr(self.context, 'current_price') else None,
            self.indicator_calculator
        )
    
    def _build_analysis_steps(self) -> str:
        """Build analysis steps - delegates to template manager."""
        symbol = self.context.symbol if hasattr(self.context, 'symbol') else 'BTC/USDT'
        return self.template_manager.build_analysis_steps(symbol, self._has_advanced_support_resistance())
    
    @staticmethod
    def _build_response_template() -> str:
        """Build response template - delegates to template manager."""
        template_manager = TemplateManager()
        return template_manager.build_response_template()


