"""
Integration tests for timeframe functionality.

Tests the complete analysis pipeline with different timeframes to ensure:
- Correct data fetching
- Proper period calculations  
- Accurate prompt generation
- Chart generation with correct timeframe labels
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import numpy as np

from src.analyzer.core.analysis_engine import AnalysisEngine
from src.analyzer.prompts.context_builder import ContextBuilder
from src.utils.timeframe_validator import TimeframeValidator


class TestTimeframeIntegration:
    """Integration tests for timeframe functionality across the analysis pipeline."""
    
    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        logger = Mock()
        logger.info = Mock()
        logger.debug = Mock()
        logger.warning = Mock()
        logger.error = Mock()
        logger.exception = Mock()
        return logger
    
    @pytest.fixture
    def mock_exchange(self):
        """Create a mock exchange with timeframe support."""
        exchange = Mock()
        exchange.name = "binance"
        exchange.id = "binance"
        exchange.timeframes = {
            '1h': '1h',
            '2h': '2h',
            '4h': '4h',
            '6h': '6h',
            '8h': '8h',
            '12h': '12h',
            '1d': '1d'
        }
        exchange.fetch_ohlcv = AsyncMock(return_value=self._generate_mock_ohlcv(100))
        return exchange
    
    def _generate_mock_ohlcv(self, count):
        """Generate mock OHLCV data."""
        data = []
        base_price = 50000
        base_time = 1700000000000
        
        for i in range(count):
            timestamp = base_time + (i * 3600000)  # 1 hour intervals
            open_price = base_price + (i * 10)
            high = open_price + 100
            low = open_price - 100
            close = open_price + 50
            volume = 100 + (i * 2)
            data.append([timestamp, open_price, high, low, close, volume])
        
        return data
    
    def test_timeframe_validator_all_supported(self):
        """Test that all supported timeframes are valid."""
        supported = ['1h', '2h', '4h', '6h', '8h', '12h', '1d']
        for tf in supported:
            assert TimeframeValidator.validate(tf), f"{tf} should be valid"
    
    def test_timeframe_to_minutes_conversions(self):
        """Test minute conversions for all timeframes."""
        expected = {
            '1h': 60,
            '2h': 120,
            '4h': 240,
            '6h': 360,
            '8h': 480,
            '12h': 720,
            '1d': 1440
        }
        for tf, minutes in expected.items():
            assert TimeframeValidator.to_minutes(tf) == minutes
    
    def test_period_calculations_accuracy(self):
        """Test period calculations maintain accuracy across timeframes."""
        test_cases = [
            ('1h', '24h', 24),
            ('4h', '24h', 6),
            ('1d', '7d', 7),
            ('1h', '7d', 168),
            ('4h', '7d', 42),
        ]
        
        for base_tf, target_period, expected_candles in test_cases:
            result = TimeframeValidator.calculate_period_candles(base_tf, target_period)
            assert result == expected_candles, \
                f"{base_tf} -> {target_period}: expected {expected_candles}, got {result}"
    
    def test_context_builder_dynamic_periods(self):
        """Test ContextBuilder period calculations for different timeframes."""
        # Test 1h timeframe
        builder_1h = ContextBuilder(timeframe="1h")
        periods_1h = builder_1h._calculate_period_candles()
        assert periods_1h["4h"] == 4
        assert periods_1h["24h"] == 24
        assert periods_1h["7d"] == 168
        
        # Test 4h timeframe
        builder_4h = ContextBuilder(timeframe="4h")
        periods_4h = builder_4h._calculate_period_candles()
        assert periods_4h["4h"] == 1
        assert periods_4h["24h"] == 6
        assert periods_4h["7d"] == 42
        
        # Test 1d timeframe
        builder_1d = ContextBuilder(timeframe="1d")
        periods_1d = builder_1d._calculate_period_candles()
        assert periods_1d["24h"] == 1
        assert periods_1d["3d"] == 3
        assert periods_1d["7d"] == 7
    
    def test_candle_limit_calculations(self):
        """Test automatic candle limit calculations for 30 days."""
        target_days = 30
        expected = {
            '1h': 720,
            '4h': 180,
            '1d': 30,
            '12h': 60
        }
        
        for tf, expected_limit in expected.items():
            limit = TimeframeValidator.get_candle_limit_for_days(tf, target_days)
            assert limit == expected_limit, \
                f"{tf} for {target_days} days: expected {expected_limit}, got {limit}"
    
    def test_cryptocompare_format_conversion(self):
        """Test CryptoCompare API format conversion for all timeframes."""
        test_cases = [
            ('1h', 'hour', 1),
            ('2h', 'hour', 2),
            ('4h', 'hour', 4),
            ('12h', 'hour', 12),
            ('1d', 'day', 1),
        ]
        
        for tf, expected_endpoint, expected_multiplier in test_cases:
            endpoint, multiplier = TimeframeValidator.to_cryptocompare_format(tf)
            assert endpoint == expected_endpoint, \
                f"{tf}: expected endpoint '{expected_endpoint}', got '{endpoint}'"
            assert multiplier == expected_multiplier, \
                f"{tf}: expected multiplier {expected_multiplier}, got {multiplier}"
    
    def test_ccxt_compatibility(self):
        """Test CCXT compatibility checking."""
        # All supported timeframes should be CCXT compatible
        for tf in ['1h', '2h', '4h', '6h', '8h', '12h', '1d']:
            assert TimeframeValidator.is_ccxt_compatible(tf), \
                f"{tf} should be CCXT compatible"
        
        # Unsupported timeframes should not be compatible
        assert not TimeframeValidator.is_ccxt_compatible('15m')
        assert not TimeframeValidator.is_ccxt_compatible('2d')
    
    def test_trading_context_includes_timeframe(self):
        """Test that trading context includes correct timeframe information."""
        mock_context = Mock()
        mock_context.symbol = "BTC/USDT"
        mock_context.current_price = "$50,000"
        
        # Test different timeframes
        for tf in ['1h', '4h', '1d']:
            builder = ContextBuilder(timeframe=tf)
            trading_context = builder.build_trading_context(mock_context)
            
            assert f"Primary Timeframe: {tf}" in trading_context, \
                f"Trading context should include timeframe {tf}"
            assert f"{tf.upper()}, 1D, 7D, 30D, and 365D timeframes" in trading_context, \
                f"Analysis timeframes should include {tf.upper()}"
    
    def test_market_data_section_timeframe_label(self):
        """Test that market data section uses correct timeframe in labels."""
        # Create mock OHLCV data with sufficient candles
        ohlcv = np.array(self._generate_mock_ohlcv(200))
        
        # Test different timeframes
        for tf in ['1h', '4h', '1d']:
            builder = ContextBuilder(timeframe=tf)
            market_data = builder.build_market_data_section(ohlcv)
            
            assert f"Based on {tf} candles" in market_data, \
                f"Market data should mention '{tf}' timeframe"
    
    def test_timeframe_normalization(self):
        """Test timeframe normalization handles case variations."""
        test_cases = [
            ('1h', '1h'),
            ('1H', '1h'),
            ('4H', '4h'),
            ('1D', '1d'),
        ]
        
        for input_tf, expected in test_cases:
            normalized = TimeframeValidator.validate_and_normalize(input_tf)
            assert normalized == expected, \
                f"Normalizing '{input_tf}': expected '{expected}', got '{normalized}'"
    
    def test_invalid_timeframes_raise_errors(self):
        """Test that invalid timeframes raise appropriate errors."""
        invalid = ['15m', '30m', '2d', '1w', 'invalid', '']
        
        for tf in invalid:
            with pytest.raises(ValueError):
                TimeframeValidator.validate_and_normalize(tf)
    
    def test_candle_progress_calculation_logic(self):
        """Test candle progress calculation for intraday timeframes."""
        from datetime import datetime
        
        # Mock a specific time: 10:35 AM (635 minutes into day)
        with patch('src.analyzer.prompts.context_builder.datetime') as mock_dt:
            mock_now = Mock()
            mock_now.hour = 10
            mock_now.minute = 35
            mock_dt.now.return_value = mock_now
            
            mock_context = Mock()
            mock_context.symbol = "BTC/USDT"
            mock_context.current_price = "$50,000"
            
            # Test 1h timeframe: should be 35 minutes into candle
            builder_1h = ContextBuilder(timeframe="1h")
            context_1h = builder_1h.build_trading_context(mock_context)
            assert "35/60 minutes" in context_1h
            
            # Test 4h timeframe: 10:35 = 635 mins, 635 % 240 = 155 mins into candle
            builder_4h = ContextBuilder(timeframe="4h")
            context_4h = builder_4h.build_trading_context(mock_context)
            assert "155/240 minutes" in context_4h
    
    def test_display_format_helper(self):
        """Test human-readable timeframe formatting."""
        expected = {
            '1h': '1-Hour',
            '4h': '4-Hour',
            '12h': '12-Hour',
            '1d': 'Daily'
        }
        
        for tf, expected_display in expected.items():
            display = TimeframeValidator.format_timeframe_display(tf)
            assert display == expected_display, \
                f"Display for '{tf}': expected '{expected_display}', got '{display}'"
    
    def test_is_intraday_classification(self):
        """Test intraday vs. daily timeframe classification."""
        intraday = ['1h', '2h', '4h', '6h', '8h', '12h']
        not_intraday = ['1d']
        
        for tf in intraday:
            assert TimeframeValidator.is_intraday(tf), f"{tf} should be intraday"
        
        for tf in not_intraday:
            assert not TimeframeValidator.is_intraday(tf), f"{tf} should not be intraday"


class TestCommandValidatorIntegration:
    """Integration tests for command validation with timeframe support."""
    
    @pytest.fixture
    def mock_logger(self):
        return Mock()
    
    def test_command_parsing_all_combinations(self):
        """Test command parsing for all valid argument combinations."""
        from src.discord_interface.cogs.handlers.command_validator import CommandValidator
        
        validator = CommandValidator(Mock())
        
        test_cases = [
            # (args, expected_symbol, expected_timeframe, expected_language)
            (['BTC/USDT'], 'BTC/USDT', None, None),
            (['BTC/USDT', '4h'], 'BTC/USDT', '4h', None),
            (['BTC/USDT', 'Polish'], 'BTC/USDT', None, 'Polish'),
            (['BTC/USDT', '1d', 'Polish'], 'BTC/USDT', '1d', 'Polish'),
            (['ETH/USDT', '12h', 'Spanish'], 'ETH/USDT', '12h', 'Spanish'),
        ]
        
        for args, exp_symbol, exp_tf, exp_lang in test_cases:
            is_valid, error, usage, (symbol, timeframe, language) = validator.validate_command_args(args)
            assert is_valid, f"Args {args} should be valid, got error: {error}"
            assert symbol == exp_symbol
            assert timeframe == exp_tf
            assert language == exp_lang
    
    def test_command_parsing_invalid_timeframes(self):
        """Test that invalid timeframes are rejected."""
        from src.discord_interface.cogs.handlers.command_validator import CommandValidator
        
        validator = CommandValidator(Mock())
        
        invalid_cases = [
            ['BTC/USDT', '15m'],  # Sub-hourly not supported
            ['BTC/USDT', '2d'],   # Multi-day not supported
            ['BTC/USDT', '3h'],   # Not in supported list
        ]
        
        for args in invalid_cases:
            is_valid, error, usage, (symbol, timeframe, language) = validator.validate_command_args(args)
            assert not is_valid, f"Args {args} should be invalid"
            assert "Invalid timeframe" in error or "Invalid argument" in error


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
