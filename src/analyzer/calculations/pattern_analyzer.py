from typing import Dict, Any, List, Optional
import numpy as np

from src.indicators.base.pattern_recognizer import PatternRecognizer
from ..data.data_processor import DataProcessor
from ..formatting.indicator_formatter import IndicatorFormatter
from src.logger.logger import Logger


class PatternAnalyzer:
    """Handles pattern detection and analysis for technical indicators"""
    
    def __init__(self, logger: Optional[Logger] = None):
        """Initialize the market pattern analyzer"""
        self.logger = logger
        self.pattern_recognizer = PatternRecognizer(logger=logger)
        self.data_processor = DataProcessor()
        
        # Cache storage for pattern detection
        self._pattern_cache = {}
        
        # Define indicator thresholds for pattern detection
        self.INDICATOR_THRESHOLDS = {
            'rsi': {'oversold': 30, 'overbought': 70},
            'stoch_k': {'oversold': 20, 'overbought': 80},
            'stoch_d': {'oversold': 20, 'overbought': 80},
            'williams_r': {'oversold': -80, 'overbought': -20},
            'adx': {'weak': 25, 'strong': 50, 'very_strong': 75},
            'mfi': {'oversold': 20, 'overbought': 80},
            'bb_width': {'tight': 2, 'wide': 10}
        }
    
    def detect_patterns(self, ohlcv_data: np.ndarray, technical_history: Dict[str, np.ndarray]) -> Dict[str, Any]:
        """Detect technical patterns using the pattern recognizer"""
        data_hash = self._hash_data(ohlcv_data)
        cache_key = f"patterns_{data_hash}"
        
        if cache_key in self._pattern_cache:
            if self.logger:
                self.logger.debug("Using cached pattern detection results")
            return self._pattern_cache[cache_key]
            
        patterns = self.pattern_recognizer.detect_patterns(
            ohlcv=ohlcv_data,
            technical_history=technical_history
        )
        
        # Store in cache
        self._pattern_cache[cache_key] = patterns
        return patterns
        
    def get_all_patterns(self, ohlcv_data: np.ndarray, technical_history: Dict[str, np.ndarray]) -> List[Dict]:
        """Centralized pattern detection using PatternRecognizer
        
        Args:
            ohlcv_data: OHLCV data array
            technical_history: Dictionary of technical indicator histories
            
        Returns:
            List of all detected patterns as dictionaries
        """
        try:
            # Use the existing PatternRecognizer instead of duplicating logic
            patterns_dict = self.pattern_recognizer.detect_patterns(
                ohlcv=ohlcv_data, 
                technical_history=technical_history
            )
            
            # Flatten all pattern categories into a single list
            all_patterns = []
            for _, patterns_list in patterns_dict.items():
                all_patterns.extend(patterns_list)
            
            if self.logger:
                self.logger.debug(f"Detected {len(all_patterns)} patterns using PatternRecognizer")
                
            return all_patterns
                
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Error in pattern detection: {e}")
            return []

    def _hash_data(self, data: np.ndarray) -> str:
        """Create a simple hash of the data for caching"""
        if data is None or len(data) == 0:
            return "empty"
            
        # Use last few candles and length for hashing
        # This is faster than hashing the entire array
        try:
            last_candle = data[-1].tobytes()
            data_len = len(data)
            return f"{hash(last_candle)}_{data_len}"
        except (AttributeError, IndexError):
            # Fallback if tobytes() is not available
            return str(hash(str(data[-1])) + len(data))