from typing import Dict, List
import numpy as np

from src.logger.logger import Logger


class MarketMetricsCalculator:
    """Handles calculation of market metrics and technical pattern detection"""
    
    def __init__(self, logger: Logger):
        """Initialize the calculator
        
        Args:
            logger: Logger instance
        """
        self.logger = logger
    
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
        
        # Use support/resistance from technical_calculator instead of duplicating
        current_price = data[-1]["close"]
        td = context.technical_data
        
        # Get support/resistance from existing technical indicators
        support_level = current_price
        resistance_level = current_price
        
        if 'advanced_support' in td and 'advanced_resistance' in td:
            adv_support = td.get('advanced_support', np.nan)
            adv_resistance = td.get('advanced_resistance', np.nan)
            
            # Handle array indicators - take the last value, following promptt_builder.py pattern
            try:
                if len(adv_support) > 0:
                    adv_support = adv_support[-1]
            except TypeError:
                # adv_support is already a scalar value
                pass
                
            try:
                if len(adv_resistance) > 0:
                    adv_resistance = adv_resistance[-1]
            except TypeError:
                # adv_resistance is already a scalar value
                pass
            
            # Use valid values or fallback
            if not np.isnan(adv_support):
                support_level = adv_support
            else:
                support_level = min(candle["low"] for candle in data)
                
            if not np.isnan(adv_resistance):
                resistance_level = adv_resistance
            else:
                resistance_level = max(candle["high"] for candle in data)
        else:
            # Fallback to simple min/max
            support_level = min(candle["low"] for candle in data)
            resistance_level = max(candle["high"] for candle in data)
        
        levels = {
            "support": support_level,
            "resistance": resistance_level
        }
        
        return {
            "metrics": basic_metrics,
            "indicator_changes": indicator_changes,
            "key_levels": levels
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
                
            try:
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
            except TypeError:
                # values is a scalar numpy value, not an array
                pass
        
        return indicator_changes
    
