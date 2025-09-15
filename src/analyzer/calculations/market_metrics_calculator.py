from typing import Dict, List

from src.logger.logger import Logger
from .indicator_calculator import IndicatorCalculator


class MarketMetricsCalculator:
    """Handles calculation of market metrics and technical pattern detection"""
    
    def __init__(self, logger: Logger, indicator_calculator: IndicatorCalculator = None):
        """Initialize the calculator
        
        Args:
            logger: Logger instance
            indicator_calculator: Optional indicator calculator instance for reuse
        """
        self.logger = logger
        # Initialize indicator calculator if not provided
        self.indicator_calculator = indicator_calculator or IndicatorCalculator(logger=logger)
    
    def update_period_metrics(self, data: List, context) -> None:
        """Calculate and update market metrics for different time periods"""
        period_metrics = {}
        
        hourly_distribution = {}
        for item in data:
            hour = item['timestamp'].hour
            hourly_distribution[hour] = hourly_distribution.get(hour, 0) + 1
            
        periods = {
            "1D": 24,
            "2D": 48,
            "3D": 72,
            "7D": 168,
            "30D": 720
        }
        
        try:
            for period_name, required_candles in periods.items():
                if len(data) >= required_candles:
                    period_metrics[period_name] = self._calculate_period_metrics(data[-required_candles:], period_name, context)
                else:
                    if period_name in ["1D", "2D", "3D"]:
                        self.logger.warning(f"Insufficient data for {period_name} analysis. Need {required_candles}, have {len(data)} candles")
                        period_metrics[period_name] = self._calculate_period_metrics(data, f"{period_name} (Partial)", context)
                    elif period_name == "7D" and len(data) >= 24:
                        self.logger.warning(f"Insufficient data for 7D metrics. Only {len(data)} candles available, need 168")
                        period_metrics["7D"] = self._calculate_period_metrics(data, "7D (Partial)", context)
                    elif period_name == "30D" and len(data) >= 168:
                        self.logger.warning(f"Insufficient data for 30D metrics. Only {len(data)} candles available, need 720")
                        period_metrics["30D"] = self._calculate_period_metrics(data, "30D (Partial)", context)
                    else:
                        self.logger.warning(f"Cannot calculate {period_name} metrics - not enough data")
            
            context.market_metrics = period_metrics
        
        except Exception as e:
            self.logger.error(f"Error updating period metrics: {e}")
            if not period_metrics and len(data) > 0:
                self.logger.warning("Setting fallback period metrics due to error")
                period_metrics["1D"] = self._calculate_period_metrics(data[-min(24, len(data)):], "1D (Fallback)", context)
                context.market_metrics = period_metrics
                
    def _calculate_period_metrics(self, data: List, period_name: str, context) -> Dict:
        """Calculate metrics for a specific time period"""
        # Calculate core metrics directly from data
        basic_metrics = self._calculate_basic_metrics(data, period_name)
        
        # Calculate indicator changes
        start_idx = -len(data)
        end_idx = -1
        indicator_changes = self._calculate_indicator_changes_for_period(context, start_idx, end_idx)
        
        try:
            support_arr, resistance_arr = self.indicator_calculator.ti.support_resistance.support_resistance_advanced(length=min(30, len(data)))
            
            # Extract the most recent valid support/resistance levels
            current_price = data[-1]["close"]
            
            # Find nearest support below current price
            import numpy as np
            valid_support = support_arr[~np.isnan(support_arr)]
            support_below = valid_support[valid_support < current_price]
            support_level = float(np.max(support_below)) if len(support_below) > 0 else min(candle["low"] for candle in data)
            
            # Find nearest resistance above current price  
            valid_resistance = resistance_arr[~np.isnan(resistance_arr)]
            resistance_above = valid_resistance[valid_resistance > current_price]
            resistance_level = float(np.min(resistance_above)) if len(resistance_above) > 0 else max(candle["high"] for candle in data)
            
            levels = {
                "support": support_level,
                "resistance": resistance_level
            }
        except Exception as e:
            self.logger.warning(f"Modern support/resistance calculation failed: {e}, using simple fallback")
            levels = {
                "support": min(candle["low"] for candle in data),
                "resistance": max(candle["high"] for candle in data)
            }
        
        # Calculate divergences
        divergences = self._calculate_divergences_for_period(context, data, start_idx, period_name)
        
        return {
            "metrics": basic_metrics,
            "indicator_changes": indicator_changes,
            "key_levels": levels,
            "divergences": divergences
        }
    
    def _calculate_basic_metrics(self, data: List[Dict], period_name: str) -> Dict:
        """Calculate basic price and volume metrics"""
        prices = [candle["close"] for candle in data]
        highs = [candle["high"] for candle in data]
        lows = [candle["low"] for candle in data]
        volumes = [candle["volume"] for candle in data]
        
        return {
            "highest_price": max(highs),
            "lowest_price": min(lows),
            "avg_price": sum(prices) / len(prices),
            "total_volume": sum(volumes),
            "avg_volume": sum(volumes) / len(volumes),
            "price_change": prices[-1] - prices[0],
            "price_change_percent": ((prices[-1] / prices[0]) - 1) * 100,
            "volatility": (max(highs) - min(lows)) / min(lows) * 100,
            "period": period_name,
            "data_points": len(prices)
        }
    
    def _calculate_indicator_changes_for_period(self, context, start_idx: int, end_idx: int) -> Dict:
        """Calculate changes in technical indicators over the period"""
        indicator_changes = {}
        
        if not hasattr(context, 'technical_history'):
            return indicator_changes
            
        history = context.technical_history
        
        # Signal interpretations are scalar values, not arrays - skip them
        signal_indicators = {'ichimoku_signal', 'bb_signal'}
        
        for ind_name, values in history.items():
            # Skip signal interpretations
            if ind_name in signal_indicators:
                continue
                
            if len(values) >= abs(start_idx):
                try:
                    start_value = float(values[start_idx])
                    end_value = float(values[end_idx])
                    change = end_value - start_value
                    change_pct = (change / abs(start_value)) * 100 if start_value != 0 else 0
                    
                    indicator_changes[f"{ind_name}_start"] = start_value
                    indicator_changes[f"{ind_name}_end"] = end_value
                    indicator_changes[f"{ind_name}_change"] = change
                    indicator_changes[f"{ind_name}_change_pct"] = change_pct
                except (IndexError, ValueError, TypeError):
                    pass
        
        return indicator_changes
    
    def _calculate_divergences_for_period(self, context, data: List, start_idx: int, period_name: str) -> Dict:
        """Calculate divergences for the specific period"""
        divergences = {"bullish": False, "bearish": False}
        
        try:
            if not hasattr(context, 'technical_history') or "rsi" not in context.technical_history:
                return divergences
                
            rsi_values = context.technical_history["rsi"]
            
            if len(rsi_values) < abs(start_idx):
                return divergences
            
            # Try advanced pattern detection
            if not self._try_advanced_divergence_detection(context, data, start_idx, divergences):
                # If advanced detection fails, return empty divergences
                self.logger.debug(f"Advanced divergence detection failed for {period_name}, using empty result")
            
            return divergences
            
        except Exception as e:
            self.logger.warning(f"Error calculating divergences for {period_name}: {e}")
            return divergences
    
    def _try_advanced_divergence_detection(self, context, data: List, start_idx: int, divergences: Dict) -> bool:
        """Try to use advanced pattern detection for divergences"""
        try:
            if not (hasattr(context, 'ohlcv_candles') and context.ohlcv_candles is not None):
                return False
                
            # Use advanced pattern detection if OHLCV data is available
            patterns = self.indicator_calculator.get_all_patterns(
                context.ohlcv_candles[-len(data):], 
                {k: v[start_idx:] for k, v in context.technical_history.items()}
            )
            
            # Look for divergence patterns in results
            for pattern in patterns:
                pattern_type = pattern.get('type', '').lower()
                if 'divergence' in pattern_type:
                    if 'bullish' in pattern_type:
                        divergences["bullish"] = True
                    elif 'bearish' in pattern_type:
                        divergences["bearish"] = True
            
            return True
            
        except Exception:
            return False
