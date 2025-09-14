# AI Provider Configuration
# Options: "local", "googleai", "openrouter", "all"
# - "local": Use LM Studio only
# - "googleai": Use Google AI Studio only  
# - "openrouter": Use OpenRouter only
# - "all": Use fallback system
PROVIDER = "googleai"

LM_STUDIO_BASE_URL = "http://localhost:1234/v1"
LM_STUDIO_MODEL = "local-model"

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_BASE_MODEL = "google/gemini-2.5-pro"
OPENROUTER_FALLBACK_MODEL = "deepseek/deepseek-r1:free"
GOOGLE_STUDIO_MODEL = "gemini-2.5-flash"

LOGGER_DEBUG = False
TEST_ENVIRONMENT = False
TIMEFRAME = "1h"

# Logging Configuration
LOG_DIR = "logs"

CANDLE_LIMIT = 999 

ANALYSIS_COOLDOWN_COIN = 3600
ANALYSIS_COOLDOWN_USER = 3600

FILE_MESSAGE_EXPIRY = 86400

DATA_DIR = "data" 

# RAG Engine Configuration
RAG_UPDATE_INTERVAL_HOURS = 1
RAG_CATEGORIES_UPDATE_INTERVAL_HOURS = 24
RAG_COINGECKO_UPDATE_INTERVAL_HOURS = 24
RAG_COINGECKO_GLOBAL_API_URL = "https://api.coingecko.com/api/v3/global"

SUPPORTED_LANGUAGES = {
    "English": "en",
    "Polish": "pl",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Chinese": "zh",
    "Japanese": "ja",
    "Russian": "ru"
}
DEFAULT_LANGUAGE = "English"
