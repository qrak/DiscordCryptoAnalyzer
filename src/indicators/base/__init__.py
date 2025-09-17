# Base indicators module initialization
from src.indicators.base.pattern_detector import (
    BasePatternDetector,
    Pattern,
    MarketData,
    PatternConfig,
    RSISettings,
    MACDSettings,
    DivergenceSettings,
    VolatilitySettings,
    CrossoverSettings,
)
from .indicator_base import IndicatorBase, IndicatorCategory
from .indicator_categories import (
    MomentumIndicators, OverlapIndicators, PriceTransformIndicators,
    SentimentIndicators, StatisticalIndicators, SupportResistanceIndicators,
    TrendIndicators, VolatilityIndicators, VolumeIndicators
)
from .technical_indicators import TechnicalIndicators

# Import PatternRecognizer lazily to avoid circular imports
def get_pattern_recognizer():
    """Lazy import of PatternRecognizer to avoid circular imports."""
    from src.indicators.base.pattern_recognizer import PatternRecognizer
    return PatternRecognizer

__all__ = [
    'IndicatorBase',
    'IndicatorCategory',
    'TechnicalIndicators',
    'MomentumIndicators',
    'OverlapIndicators',
    'PriceTransformIndicators',
    'SentimentIndicators',
    'StatisticalIndicators',
    'SupportResistanceIndicators',
    'TrendIndicators',
    'VolatilityIndicators',
    'VolumeIndicators',
    'BasePatternDetector',
    'Pattern',
    'MarketData',
    'PatternConfig',
    'RSISettings',
    'MACDSettings',
    'DivergenceSettings',
    'VolatilitySettings',
    'CrossoverSettings',
    'get_pattern_recognizer',
]
