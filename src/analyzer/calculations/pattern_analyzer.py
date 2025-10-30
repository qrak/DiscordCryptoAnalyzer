from typing import Dict, Any, List, Optional
import numpy as np
from datetime import datetime

from src.analyzer.pattern_engine import PatternEngine
from src.analyzer.pattern_engine.indicator_patterns import IndicatorPatternEngine
from src.logger.logger import Logger


class PatternAnalyzer:
    
    def __init__(self, logger: Optional[Logger] = None):
        self.logger = logger
        self.pattern_engine = PatternEngine(lookback=5, lookahead=5)
        self.indicator_pattern_engine = IndicatorPatternEngine()
        
        self._pattern_cache = {}
    
    def detect_patterns(
        self,
        ohlcv_data: np.ndarray,
        technical_history: Dict[str, np.ndarray],
        long_term_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        data_hash = self._hash_data(ohlcv_data)
        cache_key = f"patterns_{data_hash}"
        
        if cache_key in self._pattern_cache:
            if self.logger:
                self.logger.debug("Using cached pattern detection results")
            return self._pattern_cache[cache_key]
        
        if self.logger:
            self.logger.debug(f"Running pattern detection on {len(ohlcv_data)} candles")
        
        # Extract timestamps from OHLCV data (column 0)
        timestamps = None
        if ohlcv_data is not None and len(ohlcv_data) > 0:
            try:
                # Convert Unix timestamps to datetime objects
                timestamps = [datetime.fromtimestamp(ts / 1000) for ts in ohlcv_data[:, 0]]
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Could not extract timestamps from OHLCV data: {e}")
        
        # Detect chart patterns
        chart_patterns = self.pattern_engine.detect_patterns(ohlcv_data, timestamps)
        
        # Extract SMA values for MA crossover detection
        sma_values = None
        if long_term_data is not None and 'sma_values' in long_term_data:
            sma_values = long_term_data['sma_values']
        
        # Detect indicator patterns
        indicator_patterns = {}
        try:
            indicator_patterns = self.indicator_pattern_engine.detect_patterns(
                technical_history, ohlcv_data, sma_values, timestamps
            )
            if self.logger:
                ind_count = sum(len(p) for p in indicator_patterns.values())
                self.logger.debug(f"Detected {ind_count} indicator patterns")
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Error detecting indicator patterns: {e}")
        
        # Combine both types of patterns
        patterns = {
            **chart_patterns,  # candlestick, trend, reversal patterns
            **indicator_patterns  # RSI, MACD, divergence, volatility, stochastic, MA, volume patterns
        }
        
        self._pattern_cache[cache_key] = patterns
        
        if self.logger:
            total_patterns = sum(len(p) for p in patterns.values())
            chart_count = sum(len(p) for p in chart_patterns.values())
            ind_count = sum(len(p) for p in indicator_patterns.values())
            self.logger.debug(f"Detected {total_patterns} patterns: {chart_count} chart + {ind_count} indicator")
        
        return patterns
        
    def get_all_patterns(
        self,
        ohlcv_data: np.ndarray,
        technical_history: Dict[str, np.ndarray],
        long_term_data: Optional[Dict] = None
    ) -> List[Dict]:
        try:
            patterns_dict = self.detect_patterns(ohlcv_data, technical_history, long_term_data)
            
            all_patterns = []
            for _, patterns_list in patterns_dict.items():
                all_patterns.extend(patterns_list)
            
            if self.logger:
                self.logger.debug(f"Detected {len(all_patterns)} patterns")
                
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