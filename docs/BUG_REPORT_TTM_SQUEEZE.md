"""
CRITICAL BUG FOUND: Pattern Detection Cache Issue
==================================================

BUG LOCATION
------------
File: src/analyzer/calculations/pattern_analyzer.py
Lines: 27-31

CODE:
```python
data_hash = hash_data(ohlcv_data)
cache_key = f"patterns_{data_hash}"

if cache_key in self._pattern_cache:
    if self.logger:
        self.logger.debug("Using cached pattern detection results")
    return self._pattern_cache[cache_key]  # ← RETURNS STALE PATTERNS
```

THE PROBLEM
-----------
The pattern cache key is based ONLY on the hash of OHLCV data.

When new candles arrive:
1. OHLCV array gets NEW candles appended
2. Data hash CHANGES (because array changed)
3. Cache SHOULD miss
4. New patterns SHOULD be detected

BUT in this case:
- The TTM Squeeze pattern was detected at 06:00:00
- Pattern was: "TTM Squeeze detected at 06:00:00"
- Pattern got cached with data_hash_A
- New candles arrived (07:00, 08:00, ..., 20:00)
- Data hash stayed... wait, the hash SHOULD change!

WAIT - Let me reconsider...

If data_hash changes with every new candle, the cache should MISS.
So why is an old pattern showing up?

ALTERNATE HYPOTHESIS
--------------------
The pattern timestamp formatting might be the issue.

Looking at indicator_pattern_engine.py line 541:
```python
'description': f'TTM Squeeze detected (extreme low volatility) {timestamp_str}',
```

Where timestamp_str comes from:
```python
timestamp_str = self._format_pattern_time(0, pattern_index, timestamps)
```

With periods_ago=0 and pattern_index = len(array) - 1

So the timestamp SHOULD be the last candle in the array.

REAL ROOT CAUSE
---------------
The timestamp "now at 2025-11-02 20:00:00" is CORRECT for the last candle in the array.
The problem is that there WAS NO SQUEEZE at 20:00:00.

The squeeze existed from 21:00 on Nov 1 through 06:00 on Nov 2.
By 20:00 on Nov 2, the squeeze had RELEASED (volatility expanded).

But the pattern detection ran and reported "TTM Squeeze detected" with timestamp 20:00
even though at 20:00, BB bands were OUTSIDE KC channels.

This means: THE DETECTION FUNCTION IS BUGGY or there's data inconsistency.

ACTUAL BUG FOUND
----------------
After running test_final_squeeze_check.py:

At 2025-11-02 20:00:00:
- BB Upper: 111,110.59
- KC Upper: 110,938.60
- BB upper > KC upper (111,110.59 > 110,938.60) ← BB is OUTSIDE KC

- BB Lower: 109,767.08
- KC Lower: 109,746.42
- BB lower > KC lower (109,767.08 > 109,746.42) ← BB is OUTSIDE KC (below)

Result: NO SQUEEZE at 20:00:00

Historical squeezes found at:
- 21:00-23:00 on Nov 1
- 00:00-06:00 on Nov 2
- Last squeeze: 06:00:00 (14 hours before reported time)

CONCLUSION
----------
The TTM Squeeze pattern reported in the log is FALSE POSITIVE or STALE DATA.

Possible causes:
1. Pattern was detected hours earlier (at 06:00) and persisted incorrectly
2. Cache not being invalidated properly between analysis runs
3. Pattern timestamps not being updated when patterns persist
4. Bug in how "now" patterns are reported vs when they actually occurred

EVIDENCE FROM TESTS
-------------------
✅ test_indicator_verification_ccxt.py: NO squeeze at 21:00:00 (latest complete)
✅ test_exact_scenario.py: NO squeeze at 19:00:00 (as of 21:34:25)
✅ test_squeeze_investigation.py: NO squeeze at 20:00:00, but found historical squeezes
✅ test_final_squeeze_check.py: CONFIRMED no squeeze at 20:00:00, last squeeze was 14 hours earlier

RECOMMENDED FIX
---------------
1. Add logging to track when patterns are detected vs when they're reported
2. Include pattern detection timestamp (when pattern was found) separate from data timestamp
3. Consider adding pattern TTL or expiration for "now" patterns
4. Review cache invalidation logic in pattern_analyzer.py
5. Add pattern validation to ensure reported patterns still exist in current data

ALTERNATIVELY
-------------
The log might be showing accumulated patterns from the entire analysis period,
not just current patterns. Need to check how patterns are accumulated and reported
in the HTML output and Discord messages.
"""

# Documentation file
print(__doc__)
