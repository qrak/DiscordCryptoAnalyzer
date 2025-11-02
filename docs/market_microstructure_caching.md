# Market Microstructure Data - Caching Behavior

## Summary
**✅ All market microstructure data is fetched fresh on every analysis** - no persistent file cache like CoinGecko.

## Data Sources & Cache Behavior

### 1. **Ticker Data** (from `fetch_multiple_tickers`)
- **Source**: Live CCXT exchange API
- **Cache**: In-memory only, 1-hour TTL (`cache_ttl = 3600`)
- **Cache Location**: `self.ticker_cache` dictionary in `DataFetcher` class
- **Persistent Storage**: ❌ None - cache is lost when bot restarts
- **Refresh**: Every hour OR on bot restart

### 2. **Order Book Depth** (from `fetch_order_book_depth`)
- **Source**: Live CCXT exchange API
- **Cache**: ❌ None - fetched fresh every time
- **Persistent Storage**: ❌ None
- **Refresh**: On every `!analyze` command

### 3. **Recent Trades** (from `fetch_recent_trades`)
- **Source**: Live CCXT exchange API
- **Cache**: ❌ None - fetched fresh every time
- **Persistent Storage**: ❌ None
- **Refresh**: On every `!analyze` command

### 4. **Funding Rate** (from `fetch_funding_rate`)
- **Source**: Live CCXT exchange API (futures/perpetual contracts only)
- **Cache**: ❌ None - fetched fresh every time
- **Persistent Storage**: ❌ None
- **Refresh**: On every `!analyze` command

### 5. **Market Microstructure Combined** (from `fetch_market_microstructure`)
- **Source**: Combines all above data sources
- **Cache**: Only ticker data has 1-hour in-memory cache
- **Persistent Storage**: ❌ None
- **Refresh**: Order book/trades/funding = always fresh, ticker = max 1 hour old

## Comparison with CoinGecko Data

### CoinGecko Global Market Data (market_overview)
- **Source**: CoinGecko API
- **Cache**: Persistent JSON file cache
- **Cache Location**: `data/market_data/coingecko_global.json`
- **Cache Duration**: 4 hours (configurable in config.ini)
- **Persistent Storage**: ✅ Yes - survives bot restarts
- **What's Cached**: 
  - Market cap, volume, dominance stats
  - Top 10 coins by dominance
  - DeFi metrics
  - Ticker data for top coins

## Data Flow in Analysis

When user runs `!analyze BTC/USDT`:

```
1. analysis_engine.analyze_market()
   ├─ Fetch market_overview (CoinGecko) → 4h file cache
   │  └─ Includes ticker data for top 10 coins (cached)
   │
   └─ Fetch market_microstructure (CCXT) → fresh/1h in-memory
      ├─ Ticker for BTC/USDT → 1h in-memory cache
      ├─ Order book depth → always fresh
      ├─ Recent trades → always fresh
      └─ Funding rate → always fresh

2. prompt_builder.build_prompt()
   ├─ Format market_overview (includes top coins ticker - 4h old)
   ├─ Format ticker_data from coin_data (1h old max)
   ├─ Format order_book_depth (fresh)
   ├─ Format trade_flow (fresh)
   └─ Format funding_rate (fresh)
```

## Why This Design?

### Real-Time Data = No Persistent Cache
- **Order book** changes every second → must be fresh
- **Trade flow** changes every second → must be fresh
- **Funding rate** changes every 8 hours → fetch fresh to avoid stale data
- **Ticker VWAP/prices** change frequently → 1h in-memory cache is acceptable

### Market Overview = Persistent Cache
- **Global market stats** change slowly → 4h cache reduces API load
- **Top coins list** rarely changes → 4h cache is acceptable
- **DeFi metrics** change slowly → 4h cache reduces API load

## Configuration

### Ticker Cache TTL
Located in `src/analyzer/data/data_fetcher.py`:
```python
def __init__(self, exchange, logger: Logger):
    self.ticker_cache = {}
    self.cache_ttl = 3600  # Cache data for 1 hour
```

To change ticker cache duration, modify `self.cache_ttl` (value in seconds).

### CoinGecko Cache Duration
Located in `config/config.ini`:
```ini
[general]
coingecko_cache_hours = 4
```

## Summary Table

| Data Type | Fresh on Analysis? | Persistent Cache? | Max Age |
|-----------|-------------------|-------------------|---------|
| Order Book Depth | ✅ Always | ❌ No | 0s (live) |
| Recent Trades | ✅ Always | ❌ No | 0s (live) |
| Funding Rate | ✅ Always | ❌ No | 0s (live) |
| Ticker (analyzed coin) | ⚠️ Usually | ❌ No | 1h max |
| Market Overview | ❌ Cached | ✅ Yes | 4h max |
| Top Coins Tickers | ❌ Cached | ✅ Yes | 4h max |

## Impact on AI Analysis

**✅ Your AI prompts will always have:**
- Real-time order book liquidity and imbalance
- Real-time buy/sell pressure from recent trades
- Current funding rate sentiment (for futures)
- Near real-time ticker data (max 1 hour old)

**⚠️ The only cached data:**
- Global market stats (4h) - acceptable for context
- Top 10 coins tickers (4h) - used for comparison only

**Result**: Analysis is based on fresh market microstructure data, not stale cached files.
