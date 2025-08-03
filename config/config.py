try:
    from config.config_private import *
except ImportError:
    import logging
    logging.warning("Private configuration not found. Using development defaults.")
    # Set default development values (or raise error for production)
    BOT_TOKEN_DISCORD = 'development_token'
    OPENROUTER_API_KEY = 'development_key'
    GOOGLE_STUDIO_API_KEY = 'development_key'
    CRYPTOCOMPARE_API_KEY = 'development_key'
    GUILD_ID_DISCORD = 0
    MAIN_CHANNEL_ID = 0
    TEMPORARY_CHANNEL_ID_DISCORD = 0

from config.config_public import *

RAG_NEWS_API_URL = f"https://min-api.cryptocompare.com/data/v2/news/?lang=EN&limit=200&extraParams=KurusDiscordCryptoBot&api_key={CRYPTOCOMPARE_API_KEY}"
RAG_CATEGORIES_API_URL = f"https://min-api.cryptocompare.com/data/news/categories?api_key={CRYPTOCOMPARE_API_KEY}"
RAG_PRICE_API_URL = f"https://min-api.cryptocompare.com/data/pricemultifull?fsyms=BTC,ETH,BNB,SOL,XRP&tsyms=USD&api_key={CRYPTOCOMPARE_API_KEY}"
