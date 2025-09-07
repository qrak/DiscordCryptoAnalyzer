from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime

import numpy as np


@dataclass
class PatternConfig:
    """Base class for pattern detection configuration"""
    pass


@dataclass
class RSISettings(PatternConfig):
    """Settings specific to RSI pattern detection"""
    overbought: int = 70
    oversold: int = 30
    w_bottom_threshold: int = 35 # RSI level below which W-bottoms are considered
    m_top_threshold: int = 65 # RSI level above which M-tops are considered
    bottom_similarity: float = 5.0 # Max difference between W-bottom troughs
    peak_similarity: float = 5.0 # Max difference between M-top peaks
    intermediate_peak_ratio: float = 1.15 # Intermediate peak must be > 115% of avg bottom for W
    intermediate_trough_ratio: float = 0.85 # Intermediate trough must be < 85% of avg peak for M


@dataclass
class MACDSettings(PatternConfig):
    """Settings for MACD pattern detection"""
    signal_lookback: int = 10


@dataclass
class DivergenceSettings(PatternConfig):
    """Settings for divergence pattern detection"""
    price_lookback: int = 14
    short_term_lookback: int = 5


@dataclass
class VolatilitySettings(PatternConfig):
    """Settings for volatility pattern detection"""
    significant_change_threshold: float = 20.0
    spike_threshold: float = 30.0
    high_volatility_ratio: float = 1.3
    low_volatility_ratio: float = 0.7


@dataclass
class CrossoverSettings(PatternConfig):
    """Settings for crossover pattern detection"""
    lookback_periods: int = 5


@dataclass
class ChartPatternSettings(PatternConfig):
    """Settings for chart pattern detection"""
    min_pattern_length: int = 10  # Minimum number of candles required for detection context


class MarketData:
    """Container for market data used by pattern detectors"""
    def __init__(self, 
                 ohlcv: Optional[np.ndarray] = None,
                 technical_history: Optional[Dict[str, np.ndarray]] = None):
        self.ohlcv = ohlcv
        self.technical_history = technical_history or {}
        
    @property
    def has_data(self) -> bool:
        return self.ohlcv is not None and len(self.ohlcv) > 0
        
    @property
    def prices(self) -> List[float]:
        """Extract closing prices from OHLCV data"""
        if not self.has_data:
            return []
        # Ensure correct type casting if needed, though numpy usually handles it
        return self.ohlcv[:, 4].astype(float).tolist()
    
    def get_indicator_history(self, name: str) -> np.ndarray: # Return numpy array for consistency
        """Get indicator historical values as a numpy array"""
        # Ensure returned value is a numpy array, handle potential list storage if any
        values = self.technical_history.get(name, np.array([]))
        if isinstance(values, list):
            return np.array(values)
        return values

    def get_timestamp_at_index(self, index: int) -> Optional[datetime]:
        """Get the datetime timestamp for a given candle index"""
        if self.has_data and 0 <= index < len(self.ohlcv):
            try:
                # Assuming timestamp is the first element (index 0) and in milliseconds
                return datetime.fromtimestamp(self.ohlcv[index, 0] / 1000.0)
            except (IndexError, ValueError, TypeError):
                # Handle potential errors if data format is unexpected
                return None
        return None


class Pattern:
    """Base class for all detected patterns"""
    def __init__(self, 
                 type_name: str, 
                 description: str,
                 timestamp: Optional[datetime] = None, # Add timestamp
                 **kwargs):
        self.type = type_name
        self.description = description
        self.timestamp = timestamp # Store timestamp
        self.__dict__.update(kwargs)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert pattern to dictionary"""
        # Ensure timestamp is serialized correctly if needed, e.g., ISO format string
        d = self.__dict__.copy()
        if isinstance(self.timestamp, datetime):
            d['timestamp'] = self.timestamp.isoformat()
        return d


class PatternDetectorInterface(ABC):
    """Interface for all pattern detectors"""
    @abstractmethod
    def detect(self, data: MarketData) -> List[Pattern]:
        """Detect patterns in the provided data"""
        pass


class BasePatternDetector(PatternDetectorInterface):
    """Base implementation for pattern detectors"""
    def __init__(self, config: PatternConfig, logger=None):
        self.config = config
        self.logger = logger
    
    def _validate_input(self, data: MarketData) -> bool:
        """Validate input data"""
        if not data.has_data:
            if self.logger:
                self.logger.warning(f"{self.__class__.__name__}: Invalid input data")
            return False
        return True
    
    def _log_detection(self, pattern: Pattern) -> None:
        """Log detected pattern"""
        if self.logger:
            self.logger.debug(f"Detected {pattern.type}: {pattern.description}")
    
    def _detect_line_crossovers(self, 
                               line1: List[float], 
                               line2: List[float],
                               market_data: MarketData,
                               original_start_index: int,
                               lookback: int,
                               pattern_prefix: str,
                               value_formatter: str = ".4f",
                               additional_data: Optional[Dict[str, Any]] = None) -> List[Pattern]:
        """
        Generic utility to detect crossovers between two lines.
        
        Args:
            line1: First line values (recent values)
            line2: Second line values (recent values) 
            market_data: Market data for timestamp extraction
            original_start_index: Starting index in original data
            lookback: Number of periods to look back
            pattern_prefix: Prefix for pattern type (e.g., "macd", "di")
            value_formatter: Format string for values (default: ".4f")
            additional_data: Optional additional data to include in pattern
            
        Returns:
            List of detected crossover patterns
        """
        patterns = []
        additional_data = additional_data or {}
        
        for i in range(2, lookback):
            # Bullish crossover (line1 crosses above line2)
            if line1[-i] <= line2[-i] and line1[-i+1] > line2[-i+1]:
                timestamp = market_data.get_timestamp_at_index(original_start_index + len(line1) - i + 1)
                
                pattern = Pattern(
                    f"{pattern_prefix}_bullish_crossover",
                    f"Bullish {pattern_prefix.upper()} crossover {i-1} periods ago with value at {line1[-i+1]:{value_formatter}}.",
                    timestamp=timestamp,
                    periods_ago=i-1,
                    value=line1[-i+1],
                    **additional_data
                )
                self._log_detection(pattern)
                patterns.append(pattern)
                
            # Bearish crossover (line1 crosses below line2)
            if line1[-i] >= line2[-i] and line1[-i+1] < line2[-i+1]:
                timestamp = market_data.get_timestamp_at_index(original_start_index + len(line1) - i + 1)
                
                pattern = Pattern(
                    f"{pattern_prefix}_bearish_crossover",
                    f"Bearish {pattern_prefix.upper()} crossover {i-1} periods ago with value at {line1[-i+1]:{value_formatter}}.",
                    timestamp=timestamp,
                    periods_ago=i-1,
                    value=line1[-i+1],
                    **additional_data
                )
                self._log_detection(pattern)
                patterns.append(pattern)
        
        return patterns
    
    def _detect_zero_line_crossovers(self,
                                   line: List[float],
                                   market_data: MarketData,
                                   original_start_index: int,
                                   lookback: int,
                                   pattern_prefix: str) -> List[Pattern]:
        """
        Generic utility to detect zero line crossovers.
        
        Args:
            line: Line values to check for zero crossovers
            market_data: Market data for timestamp extraction
            original_start_index: Starting index in original data
            lookback: Number of periods to look back
            pattern_prefix: Prefix for pattern type
            
        Returns:
            List of detected zero line crossover patterns
        """
        patterns = []
        
        for i in range(2, lookback):
            # Bullish zero line crossover
            if line[-i] <= 0 and line[-i+1] > 0:
                timestamp = market_data.get_timestamp_at_index(original_start_index + len(line) - i + 1)
                
                pattern = Pattern(
                    f"{pattern_prefix}_zero_line_bullish",
                    f"{pattern_prefix.upper()} crossed above zero line {i-1} periods ago.",
                    timestamp=timestamp,
                    periods_ago=i-1,
                    value=line[-i+1]
                )
                self._log_detection(pattern)
                patterns.append(pattern)
                
            # Bearish zero line crossover
            if line[-i] >= 0 and line[-i+1] < 0:
                timestamp = market_data.get_timestamp_at_index(original_start_index + len(line) - i + 1)
                
                pattern = Pattern(
                    f"{pattern_prefix}_zero_line_bearish",
                    f"{pattern_prefix.upper()} crossed below zero line {i-1} periods ago.",
                    timestamp=timestamp,
                    periods_ago=i-1,
                    value=line[-i+1]
                )
                self._log_detection(pattern)
                patterns.append(pattern)
        
        return patterns
    
    def detect(self, data: MarketData) -> List[Pattern]:
        """Default implementation that validates input"""
        if not self._validate_input(data):
            return []
        return []