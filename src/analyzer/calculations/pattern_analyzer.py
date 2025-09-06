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
        self.formatter = IndicatorFormatter(logger=logger)
        
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
            for category, patterns_list in patterns_dict.items():
                all_patterns.extend(patterns_list)
            
            if self.logger:
                self.logger.debug(f"Detected {len(all_patterns)} patterns using PatternRecognizer")
                
            return all_patterns
                
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Error in pattern detection: {e}")
            return []

    def extract_key_patterns(self, context) -> str:
        """Extract key technical patterns from context data
        
        DEPRECATED: This method provides basic pattern extraction. 
        Use get_all_patterns() for more sophisticated pattern detection via PatternRecognizer.
        
        Args:
            context: Analysis context with technical data and market metrics
            
        Returns:
            str: Formatted key patterns section
        """
        if self.logger:
            self.logger.debug("extract_key_patterns is deprecated. Use get_all_patterns() for advanced pattern detection.")
        
        # Try PatternRecognizer first
        pattern_recognizer_result = self._try_pattern_recognizer(context)
        if pattern_recognizer_result:
            return pattern_recognizer_result
        
        # Fallback to basic pattern extraction
        patterns_summary = []
        patterns_summary.extend(self._extract_market_move_patterns(context))
        patterns_summary.extend(self._extract_technical_patterns(context))
        patterns_summary.extend(self._extract_sma_proximity_patterns(context))
        
        return "KEY PATTERNS DETECTED:\n- " + "\n- ".join(patterns_summary) if patterns_summary else ""
    
    # ---------- Pattern extraction helper methods ----------
    def _try_pattern_recognizer(self, context) -> str:
        """Try to use PatternRecognizer for advanced pattern detection"""
        try:
            if hasattr(context, 'ohlcv_candles') and hasattr(context, 'technical_data'):
                ohlcv_data = context.ohlcv_candles
                technical_history = context.technical_data.get('history', {})
                patterns = self.get_all_patterns(ohlcv_data, technical_history)
                
                if patterns:
                    pattern_summaries = [f"- {p.get('description', 'Unknown pattern')}" for p in patterns[-3:]]
                    return "## Key Patterns (PatternRecognizer):\n" + "\n".join(pattern_summaries)
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Could not use PatternRecognizer, falling back to basic: {e}")
        return ""
    
    def _extract_market_move_patterns(self, context) -> list:
        """Extract patterns from market metrics (large moves, momentum changes)"""
        patterns = []
        if not context.market_metrics:
            return patterns
        
        # Daily price moves
        if '1D' in context.market_metrics:
            daily_change = context.market_metrics['1D']['metrics'].get('price_change_percent', 0)
            if abs(daily_change) > 5:
                patterns.append(f"Large daily move: {daily_change:.2f}% in the last 24 hours")
        
        # Weekly trend changes
        if '7D' in context.market_metrics and 'indicator_changes' in context.market_metrics['7D']:
            changes = context.market_metrics['7D']['indicator_changes']
            
            # RSI momentum change
            rsi_change = changes.get('rsi_change', 0)
            if abs(rsi_change) > 15:
                direction = "strengthening" if rsi_change > 0 else "weakening"
                patterns.append(f"Significant momentum {direction}: RSI changed by {abs(rsi_change):.1f} points in 7 days")
            
            # MACD zero line cross
            macd_start = changes.get('macd_line_start', 0)
            macd_end = changes.get('macd_line_end', 0)
            if macd_start * macd_end < 0:
                direction = "bullish" if macd_end > 0 else "bearish" if macd_end < 0 else "neutral"
                patterns.append(f"MACD crossed zero line ({direction})")
        
        return patterns
    
    def _extract_technical_patterns(self, context) -> list:
        """Extract patterns from technical indicators (RSI, Bollinger Bands)"""
        patterns = []
        if not (context.technical_data and context.ohlcv_candles.size > 0):
            return patterns
        
        td = context.technical_data
        ts_str = self.formatter.format_timestamp(context.ohlcv_candles[-1, 0])
        
        # RSI conditions
        rsi = self.data_processor.get_indicator_value(td, 'rsi')
        if rsi != 'N/A':
            if rsi < self.INDICATOR_THRESHOLDS['rsi']['oversold']:
                patterns.append(f"{ts_str}Currently Oversold: RSI below {self.INDICATOR_THRESHOLDS['rsi']['oversold']}")
            elif rsi > self.INDICATOR_THRESHOLDS['rsi']['overbought']:
                patterns.append(f"{ts_str}Currently Overbought: RSI above {self.INDICATOR_THRESHOLDS['rsi']['overbought']}")
        
        # Bollinger Bands volatility
        bb_width = self.data_processor.calculate_bb_width(td)
        if bb_width < self.INDICATOR_THRESHOLDS['bb_width']['tight']:
            tightness = (self.INDICATOR_THRESHOLDS['bb_width']['tight'] - bb_width) / self.INDICATOR_THRESHOLDS['bb_width']['tight'] * 100
            patterns.append(f"{ts_str}Tight Bollinger Bands ({bb_width:.2f}% width) suggesting potential volatility expansion. {tightness:.1f}% tighter than threshold.")
        elif bb_width > self.INDICATOR_THRESHOLDS['bb_width']['wide']:
            patterns.append(f"{ts_str}Wide Bollinger Bands ({bb_width:.2f}% width) indicating high volatility phase.")
        
        return patterns
    
    def _extract_sma_proximity_patterns(self, context) -> list:
        """Extract patterns related to price proximity to key SMAs"""
        patterns = []
        if not (context.long_term_data and context.long_term_data.get('sma_values') and context.current_price):
            return patterns
        
        ts_str = self.formatter.format_timestamp(context.ohlcv_candles[-1, 0]) if context.ohlcv_candles.size > 0 else ""
        
        for period, value in context.long_term_data['sma_values'].items():
            if value and abs((context.current_price / value - 1) * 100) < 1:
                patterns.append(f"{ts_str}Price near critical SMA({period}): {value:.2f}")
        
        return patterns
    
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
