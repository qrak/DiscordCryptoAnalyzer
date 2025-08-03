# Public configuration
# Contains non-sensitive settings that can be safely committed to public repositories

USE_LM_STUDIO = False
LM_STUDIO_BASE_URL = "http://localhost:1234/v1"
LM_STUDIO_MODEL = "local-model"

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_BASE_MODEL = "google/gemini-2.5-flash-preview-05-20:thinking"
OPENROUTER_FALLBACK_MODEL = "deepseek/deepseek-r1:free"
GOOGLE_STUDIO_MODEL = "gemini-2.5-flash-preview-05-20"

LOGGER_DEBUG = False
TEST_ENVIRONMENT = False
TIMEFRAME = "1h"

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
RAG_INITIAL_KNOWN_TICKERS = {
    'BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'ADA', 'DOGE', 'DOT', 'AVAX', 'SHIB',
    'MATIC', 'LTC', 'LINK', 'UNI', 'XLM', 'ATOM', 'ICP', 'FIL', 'VET', 'NEAR',
    'EOS', 'XTZ', 'AAVE', 'GRT', 'ALGO', 'XMR', 'CRO', 'EGLD', 'FLOW', 'HBAR',
    'MATIC', 'ARBITRUM', 'ARB', 'OP', 'BASE', 'TON', 'AVAX', 'FTM', 'ONE',
    'MKR', 'COMP', 'YFI', 'SNX', 'SUSHI', 'BAL', 'CRV', 'UNI', '1INCH', 'AAVE',
    'USDT', 'USDC', 'BUSD', 'DAI', 'TUSD', 'FRAX', 'PYUSD', 'FDUSD', 'USDD',
    'PEPE', 'SHIB', 'DOGE', 'FLOKI', 'BONK', 'WIF', 'MOG', 'TURBO', 'BRETT',
    'CATS', 'MEME', 'PEPU', 'SLERF', 'DOG', 'BOME', 'PONKE', 'TOSHI',
    'AXS', 'SAND', 'MANA', 'ENJ', 'GALA', 'ILV', 'SLP', 'APE'
}
RAG_IMPORTANT_CATEGORIES = {
    'MINING', 'REGULATION', 'BUSINESS', 'MARKET', 'BLOCKCHAIN', 'NFT', 'DEFI',
    'SECURITY', 'TECHNOLOGY', 'ADOPTION', 'EXCHANGE', 'BTC', 'ETH', 'ALTCOIN'
}
RAG_NON_TICKER_CATEGORIES = {
    'OVERVIEW', 'MARKET', 'BLOCKCHAIN', 'TECHNOLOGY', 'EXCHANGE', 'MINING',
    'TRADING', 'REGULATION', 'BUSINESS', 'RESEARCH', 'AIRDROP', 'COMMODITY',
    'FIAT', 'WALLET', 'DATA', 'TOKEN SALE', 'SPONSORED', 'OTHER', 'ASIA',
    'ALTCOIN', 'ICO', 'SECURITY', 'NFT', 'DEFI', 'ADOPTION', 'FORKS',
    'TECHNOLOGY', 'BITTENSOR'
}

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

# google/gemini-2.5-pro-preview-03-25
# google/gemini-2.5-flash-preview:thinking
# google/gemini-2.5-pro-exp-03-25:free