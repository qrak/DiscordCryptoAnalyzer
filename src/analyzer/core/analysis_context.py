import json
from datetime import datetime
from typing import Dict, Any, List, Optional

import numpy as np


class AnalysisContext:
    """
    Enhanced data container for market analysis data
    Provides proper storage, validation and serialization
    """
    
    def __init__(self, symbol: str):
        # Basic info
        self._symbol = symbol
        self._exchange = None
        self._timeframe = None
        
        # OHLCV data
        self._ohlcv_candles = None
        self._current_price = None
        self._latest_update = None
        
        # Indicator data
        self._technical_data = {}
        self._technical_history = {}
        self._technical_patterns = {}
        
        # Market analysis data
        self._market_metrics = {}
        self._sentiment = None
        self._long_term_data = None
        self._market_overview = {}  # Initialize as an empty dictionary
        
        # News and articles
        self._news_articles = []
        
    @property
    def symbol(self) -> str:
        """Get the trading symbol"""
        return self._symbol
        
    @property
    def exchange(self) -> Optional[str]:
        """Get the exchange name"""
        return self._exchange
        
    @exchange.setter
    def exchange(self, value: str):
        """Set the exchange name"""
        self._exchange = value
        
    @property
    def timeframe(self) -> Optional[str]:
        """Get the analysis timeframe"""
        return self._timeframe
        
    @timeframe.setter
    def timeframe(self, value: str):
        """Set the analysis timeframe"""
        self._timeframe = value
        
    @property
    def ohlcv_candles(self) -> Optional[np.ndarray]:
        """Get the OHLCV candle data"""
        return self._ohlcv_candles
        
    @ohlcv_candles.setter
    def ohlcv_candles(self, value: np.ndarray):
        """Set the OHLCV candle data with validation"""
        if value is not None and not isinstance(value, np.ndarray):
            raise TypeError("OHLCV data must be a numpy array")
        self._ohlcv_candles = value
        self._latest_update = datetime.now()
        
    @property
    def current_price(self) -> Optional[float]:
        """Get the current price"""
        return self._current_price
        
    @current_price.setter
    def current_price(self, value: float):
        """Set the current price with validation"""
        if value is not None:
            try:
                self._current_price = float(value)
            except (ValueError, TypeError):
                raise ValueError("Current price must be a valid number")
        else:
            self._current_price = None
            
    @property
    def technical_data(self) -> Dict[str, Any]:
        """Get technical indicator point data"""
        return self._technical_data
        
    @technical_data.setter
    def technical_data(self, value: Dict[str, Any]):
        """Set technical indicator point data"""
        if not isinstance(value, dict):
            raise TypeError("Technical data must be a dictionary")
        self._technical_data = value
        
    @property
    def technical_history(self) -> Dict[str, Any]:
        """Get historical technical indicator data"""
        return self._technical_history
        
    @technical_history.setter
    def technical_history(self, value: Dict[str, Any]):
        """Set historical technical indicator data"""
        if not isinstance(value, dict):
            raise TypeError("Technical history must be a dictionary")
        self._technical_history = value
        
    @property
    def technical_patterns(self) -> Dict[str, Any]:
        """Get detected technical patterns"""
        return self._technical_patterns
        
    @technical_patterns.setter
    def technical_patterns(self, value: Dict[str, Any]):
        """Set detected technical patterns"""
        if value is not None and not isinstance(value, dict):
            raise TypeError("Technical patterns must be a dictionary")
        self._technical_patterns = value or {}
        
    @property
    def market_metrics(self) -> Dict[str, Any]:
        """Get market metrics by period"""
        return self._market_metrics
        
    @market_metrics.setter
    def market_metrics(self, value: Dict[str, Any]):
        """Set market metrics by period"""
        if not isinstance(value, dict):
            raise TypeError("Market metrics must be a dictionary")
        self._market_metrics = value
        
    @property
    def sentiment(self) -> Optional[Dict[str, Any]]:
        """Get market sentiment data"""
        return self._sentiment
        
    @sentiment.setter
    def sentiment(self, value: Dict[str, Any]):
        """Set market sentiment data"""
        if value is not None and not isinstance(value, dict):
            raise TypeError("Sentiment data must be a dictionary")
        self._sentiment = value
        
    @property
    def long_term_data(self) -> Optional[Dict[str, Any]]:
        """Get long-term historical data"""
        return self._long_term_data
        
    @long_term_data.setter
    def long_term_data(self, value: Dict[str, Any]):
        """Set long-term historical data"""
        if value is not None and not isinstance(value, dict):
            raise TypeError("Long-term data must be a dictionary")
        self._long_term_data = value
        
    @property
    def market_overview(self) -> Optional[Dict[str, Any]]:
        """Get market overview data"""
        return self._market_overview

    @market_overview.setter
    def market_overview(self, value: Dict[str, Any]):
        """Set market overview data"""
        if value is not None and not isinstance(value, dict):
            raise TypeError("Market overview data must be a dictionary")
        self._market_overview = value or {}
        
    @property
    def news_articles(self) -> List[Dict[str, Any]]:
        """Get related news articles"""
        return self._news_articles
        
    @news_articles.setter
    def news_articles(self, value: List[Dict[str, Any]]):
        """Set related news articles"""
        if not isinstance(value, list):
            raise TypeError("News articles must be a list")
        self._news_articles = value
        
    def add_news_article(self, article: Dict[str, Any]):
        """Add a single news article"""
        if not isinstance(article, dict):
            raise TypeError("News article must be a dictionary")
        self._news_articles.append(article)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to a serializable dictionary"""
        result = {
            'symbol': self._symbol,
            'exchange': self._exchange,
            'timeframe': self._timeframe,
            'current_price': self._current_price,
            'latest_update': self._latest_update.isoformat() if self._latest_update else None,
            'technical_data': self._technical_data,
            'market_metrics': self._market_metrics,
            'sentiment': self._sentiment,
            'long_term_data': self._long_term_data,
            'news_articles': self._news_articles,
            'technical_patterns': self._technical_patterns,
            'market_overview': self._market_overview
        }
        
        # Convert numpy arrays to lists for serialization
        if self._ohlcv_candles is not None:
            result['ohlcv_candles'] = self._ohlcv_candles.tolist()
            
        # Convert numpy arrays in technical history to lists
        tech_history_serializable = {}
        for key, value in self._technical_history.items():
            if isinstance(value, np.ndarray):
                tech_history_serializable[key] = value.tolist()
            else:
                tech_history_serializable[key] = value
                
        result['technical_history'] = tech_history_serializable
        
        return result
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnalysisContext':
        """Create a context instance from a dictionary"""
        context = cls(data['symbol'])
        
        # Set basic properties
        context.exchange = data.get('exchange')
        context.timeframe = data.get('timeframe')
        context.current_price = data.get('current_price')
        
        # Convert OHLCV from list back to numpy array if present
        if 'ohlcv_candles' in data and data['ohlcv_candles']:
            context.ohlcv_candles = np.array(data['ohlcv_candles'])
            
        # Set other properties
        context.technical_data = data.get('technical_data', {})
        context.market_metrics = data.get('market_metrics', {})
        context.sentiment = data.get('sentiment')
        context.long_term_data = data.get('long_term_data')
        context.market_overview = data.get('market_overview')
        context.news_articles = data.get('news_articles', [])
        context.technical_patterns = data.get('technical_patterns', {})
        
        # Convert technical history lists back to numpy arrays
        tech_history = data.get('technical_history', {})
        for key, value in tech_history.items():
            if isinstance(value, list):
                tech_history[key] = np.array(value)
        context.technical_history = tech_history
        
        # Set latest update if present
        if 'latest_update' in data and data['latest_update']:
            context._latest_update = datetime.fromisoformat(data['latest_update'])
            
        return context
        
    def to_json(self) -> str:
        """Serialize context to JSON string"""
        return json.dumps(self.to_dict(), default=str)
        
    @classmethod
    def from_json(cls, json_str: str) -> 'AnalysisContext':
        """Create a context instance from a JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)
        
    def is_data_fresh(self, max_age_minutes: int = 30) -> bool:
        """Check if the data is fresh enough"""
        if not self._latest_update:
            return False
            
        age = datetime.now() - self._latest_update
        return age.total_seconds() < max_age_minutes * 60
