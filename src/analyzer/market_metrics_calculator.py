from typing import Dict, List, Optional

from src.logger.logger import Logger
from src.analyzer.indicator_calculator import IndicatorCalculator


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
        prices = [candle["close"] for candle in data]
        highs = [candle["high"] for candle in data]
        lows = [candle["low"] for candle in data]
        volumes = [candle["volume"] for candle in data]
        
        start_idx = -len(data)
        end_idx = -1
        
        basic_metrics = {
            "highest_price": max(highs),
            "lowest_price": min(lows),
            "avg_price": sum(prices) / len(prices),
            "total_volume": sum(volumes),
            "avg_volume": sum(volumes) / len(volumes),
            "price_change": prices[-1] - prices[0],
            "price_change_percent": ((prices[-1] / prices[0]) - 1) * 100,
            "volatility": (max(highs) - min(lows)) / min(lows) * 100,
            "period": period_name,
            "data_points": len(data)
        }
        
        indicator_changes = {}
        if hasattr(context, 'technical_history'):
            history = context.technical_history
            for ind_name, values in history.items():
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
                    except (IndexError, ValueError):
                        pass        
        # Use the common method to identify key levels
        levels = self._identify_key_levels(highs + lows, prices[-1])
        
        divergences = {"bullish": False, "bearish": False}
        try:
            if hasattr(context, 'technical_history'):
                history = context.technical_history
                if "rsi" in history:
                    rsi_values = history["rsi"]
                    
                    if len(rsi_values) >= abs(start_idx) and len(rsi_values) > 0:
                        # Try to use PatternRecognizer for advanced divergence detection first
                        try:
                            if hasattr(context, 'ohlcv_candles') and context.ohlcv_candles is not None:
                                # Use advanced pattern detection if OHLCV data is available
                                patterns = self.indicator_calculator.get_all_patterns(
                                    context.ohlcv_candles[-len(data):], 
                                    {k: v[start_idx:] for k, v in history.items()}
                                )
                                # Look for divergence patterns in results
                                for pattern in patterns:
                                    pattern_type = pattern.get('type', '').lower()
                                    if 'divergence' in pattern_type:
                                        if 'bullish' in pattern_type:
                                            divergences["bullish"] = True
                                        elif 'bearish' in pattern_type:
                                            divergences["bearish"] = True
                            else:
                                # Fallback to legacy divergence detection
                                rsi_slice = rsi_values[start_idx:]
                                if len(rsi_slice) > 0:
                                    divergences = self._check_divergences(prices[start_idx:], rsi_slice)
                        except Exception as pattern_error:
                            # If PatternRecognizer fails, fallback to legacy method
                            rsi_slice = rsi_values[start_idx:]
                            if len(rsi_slice) > 0:
                                divergences = self._check_divergences(prices[start_idx:], rsi_slice)
        except Exception as e:
            self.logger.warning(f"Error calculating divergences for {period_name}: {e}")
            
        return {
            "metrics": basic_metrics,
            "indicator_changes": indicator_changes,
            "key_levels": levels,
            "divergences": divergences
        }
    
    def _calculate_indicator_changes(self, context, start_idx: int, end_idx: int) -> Dict:
        """Calculate changes in technical indicators over the period"""
        indicator_changes = {}
        
        if not hasattr(context, 'technical_history'):
            return indicator_changes
            
        history = context.technical_history
        
        for ind_name, values in history.items():
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
                except (IndexError, ValueError, TypeError, ZeroDivisionError):
                    pass
                    
        return indicator_changes
    
    # These methods are kept for backward compatibility if indicator_calculator is not provided
    
    def _identify_key_levels(self, price_points: List[float], current_price: float) -> Dict:
        """Identify key support and resistance levels from price data (legacy method)"""
        from collections import Counter

        # Determine appropriate precision based on price magnitude
        if current_price < 0.000001:
            precision = 10
        elif current_price < 0.001:
            precision = 6
        elif current_price < 1:
            precision = 4
        else:
            precision = 1
            
        rounded_prices = [round(p, precision) for p in price_points]
        price_counts = Counter(rounded_prices)
        
        # Find levels with at least 3 touches
        significant_levels = [price for price, count in price_counts.items() if count >= 3]
        
        # Separate into support and resistance
        support_levels = sorted([p for p in significant_levels if p < current_price], reverse=True)
        resistance_levels = sorted([p for p in significant_levels if p > current_price])
        
        # Limit to top 3 levels each
        support = support_levels[:3]
        resistance = resistance_levels[:3]
        
        return {
            "support": support,
            "resistance": resistance
        }
    
    def _check_divergences(self, prices: List[float], rsi_values: List[float]) -> Dict:
        """Check for bullish and bearish divergences between price and indicators (legacy method)"""
        try:
            if len(prices) < 10 or len(rsi_values) < 10:
                return {"bullish": False, "bearish": False}
            
            first_price = float(prices[0])
            last_price = float(prices[-1])
            first_rsi = float(rsi_values[0])
            last_rsi = float(rsi_values[-1])
                
            price_increased = last_price > first_price
            rsi_increased = last_rsi > first_rsi
                
            bullish_div = bool(not price_increased and rsi_increased)
            bearish_div = bool(price_increased and not rsi_increased)
                
            return {
                "bullish": bullish_div,
                "bearish": bearish_div
            }
        except Exception as e:
            self.logger.warning(f"General error in divergence calculation: {e}")
            return {"bullish": False, "bearish": False}
