from typing import Dict, Any

class ModelConfigManager:
    """
    Manages model configurations and parameters for different AI models.
    Provides a centralized way to get appropriate configurations based on model type.
    """
    
    DEFAULT_CONFIG = {
        "temperature": 0.7,
        "top_p": 0.9,
        "freq_penalty": 0.1,
        "pres_penalty": 0.1,
        "max_tokens": 16000
    }
    
    # Configuration specifically for Google AI models
    GOOGLE_CONFIG = {
        "temperature": 0.7,  # Matching OpenRouter settings
        "top_p": 0.9,
        "top_k": 40,  # Google-specific parameter
        "max_tokens": 32768
    }
    
    def __init__(self, custom_configs: Dict[str, Dict[str, Any]] = None):
        """
        Initialize the ModelConfigManager.
        
        Args:
            custom_configs: Optional custom configurations to override the defaults
        """
        self.config = self.DEFAULT_CONFIG.copy()
        
        # Apply any custom configurations if provided
        if custom_configs and "global" in custom_configs:
            self.config.update(custom_configs["global"])
    
    def get_config(self, model_name: str, overrides: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get configuration parameters for a specific model.
        
        Args:
            model_name: The name of the model
            overrides: Optional parameter overrides for this specific call
            
        Returns:
            A dictionary with configuration parameters
        """
        # Use Google-specific config for Google models
        if 'gemini' in model_name.lower():
            config = self.GOOGLE_CONFIG.copy()
        else:
            config = self.config.copy()
        
        # Apply any overrides
        if overrides:
            config.update(overrides)
            
        return config