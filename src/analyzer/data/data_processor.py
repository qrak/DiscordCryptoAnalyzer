from typing import Union, List


class DataProcessor:
    """Handles processing, validation, and extraction of indicator values"""
    
    def __init__(self):
        """Initialize the indicator data processor"""
        pass
        
    def get_indicator_value(self, td: dict, key: str) -> Union[float, str]:
        """Get indicator value with proper type checking and error handling
        
        Args:
            td: Technical data dictionary
            key: Indicator key to retrieve
            
        Returns:
            float or str: Indicator value or 'N/A' if invalid
        """
        try:
            value = td[key]
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, (list, tuple)) and len(value) == 1:
                return float(value[0])
            if isinstance(value, (list, tuple)) and len(value) > 1:
                return float(value[-1])
            return 'N/A'
        except (KeyError, TypeError, ValueError, IndexError):
            return 'N/A'
        
    def get_indicator_values(self, td: dict, key: str, expected_count: int = 2) -> List[float]:
        """Get multiple indicator values with proper type checking
        
        Args:
            td: Technical data dictionary
            key: Indicator key to retrieve
            expected_count: Number of values expected
            
        Returns:
            list[float]: List of indicator values or empty list if invalid
        """
        try:
            values = td[key]
            if not isinstance(values, (list, tuple)) or len(values) != expected_count:
                return []
            return [float(val) if not isinstance(val, str) else val for val in values]
        except (KeyError, TypeError, ValueError):
            return []
    
    def calculate_bb_width(self, td: dict) -> float:
         """Calculate Bollinger Band width percentage.
         
         Args:
             td: Technical data dictionary with bb_upper, bb_lower, bb_middle
             
         Returns:
             float: BB width as percentage or 0.0 if calculation fails
         """
         upper = self.get_indicator_value(td, "bb_upper")
         lower = self.get_indicator_value(td, "bb_lower")
         middle = self.get_indicator_value(td, "bb_middle")

         if upper != 'N/A' and lower != 'N/A' and middle != 'N/A' and middle != 0:
             try:
                 return ((upper - lower) / middle) * 100
             except (ZeroDivisionError, TypeError):
                 return 0.0
         return 0.0
    
    def format_numeric_value(self, value, precision: int = 2) -> str:
        """Helper to safely format numeric values with fallback to 'N/A'"""
        if isinstance(value, (int, float)):
            return f"{value:.{precision}f}"
        return "N/A"
