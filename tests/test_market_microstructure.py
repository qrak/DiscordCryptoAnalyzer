"""
Test the new market microstructure data fetching methods.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from src.logger.logger import Logger
from src.platforms.exchange_manager import ExchangeManager
from src.analyzer.data.data_fetcher import DataFetcher


async def test_market_microstructure():
    """Test all new market data fetching methods."""
    
    logger = Logger("MicrostructureTest")
    exchange_manager = ExchangeManager(logger)
    
    await exchange_manager.initialize()
    
    # Get or load an exchange (Binance preferred)
    exchange = await exchange_manager.get_or_load_exchange('binance', 'BTC/USDT')
    
    if not exchange:
        print("❌ Failed to load Binance exchange")
        await exchange_manager.shutdown()
        return
    
    fetcher = DataFetcher(exchange, logger)
    
    print("="*70)
    print("TESTING MARKET MICROSTRUCTURE DATA FETCHING")
    print("="*70)
    
    symbol = "BTC/USDT"
    
    # Test 1: Order Book
    print(f"\n1. Testing Order Book for {symbol}")
    print("-"*70)
    order_book = await fetcher.fetch_order_book_depth(symbol, limit=20)
    if order_book:
        print(f"✅ Order Book Retrieved:")
        print(f"   - Best Bid: ${order_book['best_bid']:,.2f}")
        print(f"   - Best Ask: ${order_book['best_ask']:,.2f}")
        print(f"   - Spread: ${order_book['spread']:.2f} ({order_book['spread_percent']:.3f}%)")
        print(f"   - Bid Depth: {order_book['bid_depth']:.4f} BTC")
        print(f"   - Ask Depth: {order_book['ask_depth']:.4f} BTC")
        print(f"   - Imbalance: {order_book['imbalance']:+.3f} ({'More Bids' if order_book['imbalance'] > 0 else 'More Asks'})")
    else:
        print("❌ Failed to fetch order book")
    
    # Test 2: Recent Trades
    print(f"\n2. Testing Recent Trades for {symbol}")
    print("-"*70)
    trades = await fetcher.fetch_recent_trades(symbol, limit=500)
    if trades:
        print(f"✅ Recent Trades Retrieved:")
        print(f"   - Total Trades: {trades['total_trades']}")
        print(f"   - Time Span: {trades['time_span_minutes']:.1f} minutes")
        print(f"   - Trade Velocity: {trades['trade_velocity']:.1f} trades/min")
        print(f"   - Buy Volume: {trades['buy_volume']:.4f} BTC")
        print(f"   - Sell Volume: {trades['sell_volume']:.4f} BTC")
        print(f"   - Buy Pressure: {trades['buy_pressure_percent']:.1f}%")
        print(f"   - Avg Trade Size: {trades['avg_trade_size']:.4f} BTC")
        print(f"   - Buy/Sell Ratio: {trades['buy_sell_ratio']:.2f}")
    else:
        print("❌ Failed to fetch recent trades")
    
    # Test 3: Funding Rate (will be None for spot)
    print(f"\n3. Testing Funding Rate for {symbol}")
    print("-"*70)
    funding = await fetcher.fetch_funding_rate(symbol)
    if funding:
        print(f"✅ Funding Rate Retrieved:")
        print(f"   - Rate: {funding['funding_rate_percent']:.4f}%")
        print(f"   - Annualized: {funding['annualized_rate']:.2f}%")
        print(f"   - Sentiment: {funding['sentiment']}")
    else:
        print("ℹ️  Funding rate not available (spot market or not supported)")
    
    # Test 4: Enhanced Ticker Data
    print(f"\n4. Testing Enhanced Ticker Data for {symbol}")
    print("-"*70)
    ticker_data = await fetcher.fetch_multiple_tickers([symbol])
    if ticker_data and 'RAW' in ticker_data:
        base, quote = symbol.split('/')
        if base in ticker_data['RAW'] and quote in ticker_data['RAW'][base]:
            ticker = ticker_data['RAW'][base][quote]
            print(f"✅ Ticker Data Retrieved:")
            print(f"   - Price: ${ticker['PRICE']:,.2f}")
            print(f"   - 24h Change: {ticker['CHANGEPCT24HOUR']:+.2f}%")
            print(f"   - 24h High: ${ticker['HIGH24HOUR']:,.2f}")
            print(f"   - 24h Low: ${ticker['LOW24HOUR']:,.2f}")
            print(f"   - 24h Volume: {ticker['VOLUME24HOUR']:,.2f} BTC")
            print(f"   - Quote Volume: ${ticker['QUOTEVOLUME24HOUR']:,.0f}")
            print(f"   - VWAP: ${ticker.get('VWAP', 0):,.2f}")
            print(f"   - Bid: ${ticker['BID']:,.2f} (size: {ticker.get('BIDVOLUME', 0):.4f})")
            print(f"   - Ask: ${ticker['ASK']:,.2f} (size: {ticker.get('ASKVOLUME', 0):.4f})")
        else:
            print("❌ Failed to extract ticker data")
    else:
        print("❌ Failed to fetch ticker data")
    
    # Test 5: Comprehensive Market Microstructure
    print(f"\n5. Testing Comprehensive Market Microstructure for {symbol}")
    print("-"*70)
    microstructure = await fetcher.fetch_market_microstructure(symbol)
    if microstructure:
        print(f"✅ Market Microstructure Retrieved:")
        print(f"   - Available Data: {', '.join(microstructure['available_data'])}")
        if microstructure.get('ticker'):
            print(f"   - Has Ticker: ✓")
        if microstructure.get('order_book'):
            print(f"   - Has Order Book: ✓ (spread: {microstructure['order_book']['spread_percent']:.3f}%)")
        if microstructure.get('recent_trades'):
            print(f"   - Has Recent Trades: ✓ ({microstructure['recent_trades']['total_trades']} trades)")
        if microstructure.get('funding_rate'):
            print(f"   - Has Funding Rate: ✓ ({microstructure['funding_rate']['funding_rate_percent']:.4f}%)")
    else:
        print("❌ Failed to fetch market microstructure")
    
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    results = {
        "Order Book": order_book is not None,
        "Recent Trades": trades is not None,
        "Funding Rate": "N/A for spot",
        "Enhanced Ticker": ticker_data is not None,
        "Market Microstructure": microstructure is not None and len(microstructure['available_data']) > 0
    }
    
    for test_name, passed in results.items():
        if passed == "N/A for spot":
            print(f"ℹ️  {test_name}: {passed}")
        elif passed:
            print(f"✅ {test_name}: PASSED")
        else:
            print(f"❌ {test_name}: FAILED")
    
    all_passed = all(p is True or p == "N/A for spot" for p in results.values())
    print("\n" + "="*70)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
    else:
        print("⚠️  SOME TESTS FAILED")
    print("="*70)
    
    await exchange_manager.shutdown()


if __name__ == "__main__":
    asyncio.run(test_market_microstructure())
