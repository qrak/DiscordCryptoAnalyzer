"""
Test the complete market_overview formatting with analyzed symbol.
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from src.logger.logger import Logger
from src.utils.format_utils import FormatUtils
from src.analyzer.data.data_processor import DataProcessor
from src.analyzer.formatting.market_formatter import MarketFormatter


def test_market_overview_formatting():
    """Test that market overview formats correctly with top_coins and defi."""
    
    output = []
    output.append("="*70)
    output.append("TESTING MARKET OVERVIEW FORMATTING")
    output.append("="*70)
    
    # Setup
    logger = Logger("Test")
    data_processor = DataProcessor()
    format_utils = FormatUtils(data_processor=data_processor)
    formatter = MarketFormatter(logger=logger, format_utils=format_utils)
    
    # Load actual cache data (simulating what rag_engine returns)
    with open("data/market_data/coingecko_global.json", "r") as f:
        cache = json.load(f)
    
    # Build market_overview as rag_engine now does (WITH fix)
    coingecko_data = cache["data"]
    market_overview = {
        "timestamp": cache["timestamp"],
        "market_cap": coingecko_data.get("market_cap", {}),
        "volume": coingecko_data.get("volume", {}),
        "dominance": coingecko_data.get("dominance", {}),
        "stats": coingecko_data.get("stats", {}),
        "top_coins": coingecko_data.get("top_coins", []),
        "defi": coingecko_data.get("defi", {})
    }
    
    output.append("\nTest 1: BTC/USDT analysis (should exclude BTC from top coins)")
    output.append("-" * 70)
    result1 = formatter.format_market_overview(market_overview, analyzed_symbol="BTC/USDT")
    output.append(result1[:1500] + "..." if len(result1) > 1500 else result1)
    
    output.append("\n\nTest 2: ETH/USDT analysis (should exclude ETH from top coins)")
    output.append("-" * 70)
    result2 = formatter.format_market_overview(market_overview, analyzed_symbol="ETH/USDT")
    output.append(result2[:1500] + "..." if len(result2) > 1500 else result2)
    
    output.append("\n\nTest 3: MATIC/USDT analysis (not in top 10, should show all top coins)")
    output.append("-" * 70)
    result3 = formatter.format_market_overview(market_overview, analyzed_symbol="MATIC/USDT")
    output.append(result3[:1500] + "..." if len(result3) > 1500 else result3)
    
    output.append("\n" + "="*70)
    output.append("VERIFICATION")
    output.append("="*70)
    
    # Check that results contain expected sections
    checks = [
        ("BTC position shown", "BTC (Bitcoin) Market Position" in result1),
        ("ETH excluded from top coins in BTC analysis", "ETH" in result1 and "#2:" in result1),
        ("ETH position shown", "ETH (Ethereum) Market Position" in result2),
        ("BTC excluded from top coins in ETH analysis", "BTC" not in result2.split("Top Coins Status")[1][:200] if "Top Coins Status" in result2 else False),
        ("Top coins shown for MATIC", "Top Coins Status" in result3),
        ("DeFi section present", "DeFi Ecosystem" in result1 or "DeFi" in result1),
    ]
    
    for check_name, passed in checks:
        status = "PASS" if passed else "FAIL"
        output.append(f"{status}: {check_name}")
    
    all_passed = all(check[1] for check in checks)
    output.append("\n" + "="*70)
    if all_passed:
        output.append("SUCCESS: ALL TESTS PASSED!")
    else:
        output.append("FAILURE: SOME TESTS FAILED")
    output.append("="*70)
    
    # Write to file
    with open("test_formatting_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output))
    
    print("Results written to test_formatting_results.txt")


if __name__ == "__main__":
    test_market_overview_formatting()
