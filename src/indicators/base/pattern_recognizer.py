from typing import Dict, List, Optional, Any

from src.indicators.base.pattern_detector import (
    PatternDetectorInterface,
    MarketData,
    RSISettings,
    MACDSettings,
    DivergenceSettings,
    VolatilitySettings,
    CrossoverSettings
)
from src.indicators.detectors.crossover_pattern_detector import CrossoverPatternDetector
from src.indicators.detectors.divergence_pattern_detector import DivergencePatternDetector
from src.indicators.detectors.macd_pattern_detector import MACDPatternDetector
from src.indicators.detectors.rsi_pattern_detector import RSIPatternDetector
from src.indicators.detectors.volatility_pattern_detector import VolatilityPatternDetector


class PatternRecognizer:
    """Main class for recognizing patterns in market data using multiple detectors"""
    
    def __init__(self, logger=None):
        """Initialize with default settings and detectors"""
        self.logger = logger
        self._detectors = self._initialize_detectors()
    
    def _initialize_detectors(self) -> Dict[str, PatternDetectorInterface]:
        """Initialize all pattern detectors with default settings"""
        return {
            'rsi': RSIPatternDetector(
                RSISettings(
                    overbought=70.0, oversold=30.0,
                    w_bottom_threshold=30.0, bottom_similarity=2.0
                ), logger=self.logger
            ),
            'macd': MACDPatternDetector(
                MACDSettings(signal_lookback=10), logger=self.logger
            ),
            'volatility': VolatilityPatternDetector(
                VolatilitySettings(
                    significant_change_threshold=20.0, spike_threshold=30.0,
                    high_volatility_ratio=1.3, low_volatility_ratio=0.7
                ), logger=self.logger
            ),
            'divergence': DivergencePatternDetector(
                DivergenceSettings(
                    price_lookback=14, short_term_lookback=5
                ), logger=self.logger
            ),
            'crossover': CrossoverPatternDetector(
                CrossoverSettings(lookback_periods=5), logger=self.logger
            )
            # Removed chart_patterns detector completely
        }
    
    @property
    def active_detectors(self) -> List[str]:
        """Get list of active detector names"""
        return list(self._detectors.keys())
    
    def add_detector(self, name: str, detector: PatternDetectorInterface) -> None:
        """Add a new detector or replace an existing one"""
        if self.logger:
            self.logger.debug(f"Adding detector: {name}")
        self._detectors[name] = detector
    
    def remove_detector(self, name: str) -> bool:
        """Remove a detector by name"""
        if name in self._detectors:
            if self.logger:
                self.logger.debug(f"Removing detector: {name}")
            del self._detectors[name]
            return True
        return False
    
    def detect_patterns(self, 
                        ohlcv: Optional[Any] = None, 
                        technical_history: Optional[Dict[str, Any]] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Detect patterns using all registered detectors"""
        # Create market data for analysis
        market_data = MarketData(
            ohlcv=ohlcv,
            technical_history=technical_history
        )
        
        # Initialize results dictionary
        results = {
            "rsi_patterns": [],
            "macd_signals": [],
            "volatility_changes": [],
            "price_divergences": [],
            "significant_crossovers": [],
            "chart_patterns": []  # Keep this empty category for backward compatibility
        }
        
        if not market_data.has_data:
            if self.logger:
                self.logger.warning("No market data available for pattern detection")
            return results
            
        # Run each detector
        for detector_name, detector in self._detectors.items():
            try:
                patterns = detector.detect(market_data)
                
                # Map detector names to result categories
                if detector_name == 'rsi':
                    results["rsi_patterns"] = [p.to_dict() for p in patterns]
                elif detector_name == 'macd':
                    results["macd_signals"] = [p.to_dict() for p in patterns]
                elif detector_name == 'volatility':
                    results["volatility_changes"] = [p.to_dict() for p in patterns]
                elif detector_name == 'divergence':
                    results["price_divergences"] = [p.to_dict() for p in patterns]
                elif detector_name == 'crossover':
                    results["significant_crossovers"] = [p.to_dict() for p in patterns]
                # Removed chart_patterns detector mapping
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error running detector '{detector_name}': {e}", exc_info=True)

        return results