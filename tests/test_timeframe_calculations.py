"""
Unit tests for timeframe calculations and validation.

Tests TimeframeValidator utility class methods including:
- Timeframe validation
- Time conversions
- Period candle calculations
- CryptoCompare API format conversion
- CCXT compatibility checks
"""

import pytest
from src.utils.timeframe_validator import TimeframeValidator


class TestTimeframeValidation:
    """Test timeframe validation methods."""
    
    @pytest.mark.parametrize("timeframe,expected", [
        ("1h", True),
        ("2h", True),
        ("4h", True),
        ("6h", True),
        ("8h", True),
        ("12h", True),
        ("1d", True),
        ("15m", False),  # Sub-hourly not supported
        ("30m", False),  # Sub-hourly not supported
        ("2d", False),   # Multi-day not supported
        ("invalid", False),
    ])
    def test_validate(self, timeframe, expected):
        """Test timeframe validation."""
        assert TimeframeValidator.validate(timeframe) == expected
    
    def test_validate_and_normalize(self):
        """Test validation and normalization of timeframes."""
        # Valid timeframes
        assert TimeframeValidator.validate_and_normalize("1h") == "1h"
        assert TimeframeValidator.validate_and_normalize("1H") == "1h"
        assert TimeframeValidator.validate_and_normalize("4H") == "4h"
        assert TimeframeValidator.validate_and_normalize("1D") == "1d"
        
        # Invalid timeframes should raise ValueError
        with pytest.raises(ValueError, match="Unsupported timeframe"):
            TimeframeValidator.validate_and_normalize("15m")
        
        with pytest.raises(ValueError, match="Unsupported timeframe"):
            TimeframeValidator.validate_and_normalize("invalid")


class TestTimeframeConversions:
    """Test timeframe conversion methods."""
    
    @pytest.mark.parametrize("timeframe,expected_minutes", [
        ("1h", 60),
        ("2h", 120),
        ("4h", 240),
        ("6h", 360),
        ("8h", 480),
        ("12h", 720),
        ("1d", 1440),
    ])
    def test_to_minutes(self, timeframe, expected_minutes):
        """Test conversion of timeframe to minutes."""
        assert TimeframeValidator.to_minutes(timeframe) == expected_minutes
    
    def test_to_minutes_invalid(self):
        """Test to_minutes with invalid timeframe."""
        with pytest.raises(ValueError, match="Unrecognized timeframe"):
            TimeframeValidator.to_minutes("invalid")
    
    def test_format_timeframe_display(self):
        """Test human-readable timeframe formatting."""
        assert TimeframeValidator.format_timeframe_display("1h") == "1-Hour"
        assert TimeframeValidator.format_timeframe_display("4h") == "4-Hour"
        assert TimeframeValidator.format_timeframe_display("1d") == "Daily"
    
    def test_is_intraday(self):
        """Test intraday timeframe detection."""
        assert TimeframeValidator.is_intraday("1h") is True
        assert TimeframeValidator.is_intraday("4h") is True
        assert TimeframeValidator.is_intraday("12h") is True
        assert TimeframeValidator.is_intraday("1d") is False


class TestPeriodCalculations:
    """Test period candle calculation methods."""
    
    def test_calculate_period_candles_1h(self):
        """Test period calculations for 1h timeframe."""
        assert TimeframeValidator.calculate_period_candles("1h", "4h") == 4
        assert TimeframeValidator.calculate_period_candles("1h", "24h") == 24
        assert TimeframeValidator.calculate_period_candles("1h", "7d") == 168
    
    def test_calculate_period_candles_4h(self):
        """Test period calculations for 4h timeframe."""
        assert TimeframeValidator.calculate_period_candles("4h", "4h") == 1
        assert TimeframeValidator.calculate_period_candles("4h", "24h") == 6
        assert TimeframeValidator.calculate_period_candles("4h", "7d") == 42
    
    def test_calculate_period_candles_1d(self):
        """Test period calculations for 1d timeframe."""
        assert TimeframeValidator.calculate_period_candles("1d", "1d") == 1
        assert TimeframeValidator.calculate_period_candles("1d", "7d") == 7
    
    def test_get_candle_limit_for_days(self):
        """Test candle limit calculation for target days."""
        # 30 days at different timeframes
        assert TimeframeValidator.get_candle_limit_for_days("1h", 30) == 720
        assert TimeframeValidator.get_candle_limit_for_days("4h", 30) == 180
        assert TimeframeValidator.get_candle_limit_for_days("1d", 30) == 30
        
        # 7 days at different timeframes
        assert TimeframeValidator.get_candle_limit_for_days("1h", 7) == 168
        assert TimeframeValidator.get_candle_limit_for_days("4h", 7) == 42
        assert TimeframeValidator.get_candle_limit_for_days("1d", 7) == 7


class TestCryptoCompareAPIFormat:
    """Test CryptoCompare API format conversion."""
    
    @pytest.mark.parametrize("timeframe,expected_endpoint,expected_multiplier", [
        ("1h", "hour", 1),
        ("2h", "hour", 2),
        ("4h", "hour", 4),
        ("6h", "hour", 6),
        ("8h", "hour", 8),
        ("12h", "hour", 12),
        ("1d", "day", 1),
    ])
    def test_to_cryptocompare_format(self, timeframe, expected_endpoint, expected_multiplier):
        """Test conversion to CryptoCompare API format."""
        endpoint, multiplier = TimeframeValidator.to_cryptocompare_format(timeframe)
        assert endpoint == expected_endpoint
        assert multiplier == expected_multiplier
    
    def test_to_cryptocompare_format_invalid(self):
        """Test CryptoCompare conversion with unsupported timeframe."""
        with pytest.raises(ValueError, match="not supported by CryptoCompare API"):
            TimeframeValidator.to_cryptocompare_format("15m")


class TestCCXTCompatibility:
    """Test CCXT exchange compatibility checks."""
    
    @pytest.mark.parametrize("timeframe,expected", [
        ("1h", True),
        ("2h", True),
        ("4h", True),
        ("6h", True),
        ("8h", True),
        ("12h", True),
        ("1d", True),
        ("15m", False),  # Not in standard list
    ])
    def test_is_ccxt_compatible(self, timeframe, expected):
        """Test CCXT compatibility check."""
        assert TimeframeValidator.is_ccxt_compatible(timeframe) == expected


class TestContextBuilderIntegration:
    """Integration tests for ContextBuilder period calculations."""
    
    def test_context_builder_dynamic_periods(self):
        """Test that ContextBuilder uses dynamic period calculations."""
        from src.analyzer.prompts.context_builder import ContextBuilder
        
        # Test 1h timeframe
        builder_1h = ContextBuilder(timeframe="1h")
        periods_1h = builder_1h._calculate_period_candles()
        assert periods_1h["24h"] == 24
        assert periods_1h["7d"] == 168
        
        # Test 4h timeframe
        builder_4h = ContextBuilder(timeframe="4h")
        periods_4h = builder_4h._calculate_period_candles()
        assert periods_4h["24h"] == 6
        assert periods_4h["7d"] == 42
        
        # Test 1d timeframe
        builder_1d = ContextBuilder(timeframe="1d")
        periods_1d = builder_1d._calculate_period_candles()
        assert periods_1d["24h"] == 1
        assert periods_1d["3d"] == 3
        assert periods_1d["7d"] == 7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
