import numpy as np
from typing import Any, Dict, Optional

from src.logger.logger import Logger
from ..core.analysis_context import AnalysisContext
from ..calculations.indicator_calculator import IndicatorCalculator
from .template_manager import TemplateManager
from ..formatting.market_formatter import MarketFormatter
from ..formatting.technical_formatter import TechnicalFormatter
from .context_builder import ContextBuilder


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
        self.market_formatter = MarketFormatter(logger)
        self.technical_analysis_formatter = TechnicalFormatter(self.indicator_calculator, logger)
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
            sections.append(self.market_formatter.format_market_overview(context.market_overview))

        # Add cryptocurrency details if available
        coin_details_section = self.context_builder.build_coin_details_section(
            context.coin_details, self.indicator_calculator
        )
        if coin_details_section:
            sections.append(coin_details_section)

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
            bool: True if advanced S/R indicators are available and valid
        """
        td = self.context.technical_data
        
        # Get advanced indicators with defaults
        adv_support = td.get('advanced_support', np.nan)
        adv_resistance = td.get('advanced_resistance', np.nan)
        
        # Handle array indicators - take the last value
        try:
            if len(adv_support) > 0:
                adv_support = adv_support[-1]
        except TypeError:
            # adv_support is already a scalar value
            pass
            
        try:
            if len(adv_resistance) > 0:
                adv_resistance = adv_resistance[-1]
        except TypeError:
            # adv_resistance is already a scalar value
            pass
        
        # Both values must be valid (not NaN)
        return not np.isnan(adv_support) and not np.isnan(adv_resistance)
