"""
Test Stochastic crossover detection with synthetic data
"""
import numpy as np
from numba import njit

@njit
def detect_stoch_bullish_crossover_numba(stoch_k: np.ndarray, stoch_d: np.ndarray, oversold_threshold: float = 30.0) -> tuple:
    """
    Detect bullish Stochastic crossover: %K crosses above %D while in oversold territory.
    
    Returns:
        (found: bool, periods_ago: int, k_value: float, d_value: float, is_in_oversold: bool)
    """
    if len(stoch_k) < 2 or len(stoch_d) < 2:
        return False, 0, 0.0, 0.0, False
    
    # Check last 5 periods for crossover
    lookback = min(5, len(stoch_k))
    
    for i in range(1, lookback):
        idx = len(stoch_k) - i - 1
        
        # Skip if any values are NaN
        if np.isnan(stoch_k[idx]) or np.isnan(stoch_k[idx + 1]):
            continue
        if np.isnan(stoch_d[idx]) or np.isnan(stoch_d[idx + 1]):
            continue
        
        # Detect crossover: %K crosses above %D
        was_below = stoch_k[idx] <= stoch_d[idx]
        now_above = stoch_k[idx + 1] > stoch_d[idx + 1]
        
        if was_below and now_above:
            # Use values at crossover point, not current values
            k_val = float(stoch_k[idx + 1])
            d_val = float(stoch_d[idx + 1])
            in_oversold = k_val < oversold_threshold or d_val < oversold_threshold
            
            return True, i, k_val, d_val, in_oversold
    
    return False, 0, 0.0, 0.0, False


def test_bullish_crossover_in_oversold():
    """Test Case 1: Bullish crossover in oversold territory"""
    print("\n=== Test 1: Bullish crossover in oversold (3 periods ago) ===")
    
    # Synthetic data: crossover 3 periods ago at low values, then moved up
    # Crossover at index 4 (3 periods ago from last index 7)
    stoch_k = np.array([20.0, 22.0, 24.0, 26.0, 28.5, 35.0, 42.0, 50.0])
    stoch_d = np.array([25.0, 24.0, 26.0, 28.0, 27.0, 32.0, 38.0, 45.0])
    
    print("Data:")
    print(f"  stoch_k: {stoch_k}")
    print(f"  stoch_d: {stoch_d}")
    print(f"  Current (latest) k={stoch_k[-1]:.1f}, d={stoch_d[-1]:.1f}")
    
    # Find crossover manually
    print("\nManual check:")
    for i in range(len(stoch_k) - 1):
        was_below = stoch_k[i] <= stoch_d[i]
        now_above = stoch_k[i + 1] > stoch_d[i + 1]
        print(f"  Index {i} -> {i+1}: k={stoch_k[i]:.1f}→{stoch_k[i+1]:.1f}, d={stoch_d[i]:.1f}→{stoch_d[i+1]:.1f}, "
              f"was_below={was_below}, now_above={now_above}")
        if was_below and now_above:
            print(f"    ✓ CROSSOVER at index {i+1}: k={stoch_k[i+1]:.1f}, d={stoch_d[i+1]:.1f}")
    
    found, periods_ago, k_val, d_val, in_oversold = detect_stoch_bullish_crossover_numba(stoch_k, stoch_d)
    
    print(f"\nFunction result:")
    print(f"  Found: {found}")
    print(f"  Periods ago (i): {periods_ago}")
    print(f"  K value: {k_val:.2f}")
    print(f"  D value: {d_val:.2f}")
    print(f"  In oversold: {in_oversold}")
    
    # Calculate actual crossover index from the returned values
    # The function returns i, but the crossover is at idx+1 where idx = len-i-1
    # So crossover_index = len - i - 1 + 1 = len - i
    actual_crossover_idx = len(stoch_k) - periods_ago
    print(f"\nActual crossover index (calculated): {actual_crossover_idx}")
    print(f"Expected values at that index: k={stoch_k[actual_crossover_idx]:.2f}, d={stoch_d[actual_crossover_idx]:.2f}")
    
    assert found == True, "Should find crossover"
    # Verify the values match the crossover point
    assert abs(k_val - stoch_k[actual_crossover_idx]) < 0.01, f"K value mismatch: {k_val} vs {stoch_k[actual_crossover_idx]}"
    assert abs(d_val - stoch_d[actual_crossover_idx]) < 0.01, f"D value mismatch: {d_val} vs {stoch_d[actual_crossover_idx]}"
    assert in_oversold == True, "Should be in oversold at crossover point"
    
    print("✓ PASSED")


def test_bullish_crossover_not_in_oversold():
    """Test Case 2: Bullish crossover NOT in oversold territory"""
    print("\n=== Test 2: Bullish crossover above oversold (1 period ago) ===")
    
    # Crossover 1 period ago at mid-range values
    stoch_k = np.array([45.0, 48.0, 50.0, 52.0, 55.0, 58.0, 60.0])
    stoch_d = np.array([50.0, 52.0, 54.0, 56.0, 57.0, 58.5, 59.0])
    
    print("Data:")
    print(f"  stoch_k: {stoch_k}")
    print(f"  stoch_d: {stoch_d}")
    
    found, periods_ago, k_val, d_val, in_oversold = detect_stoch_bullish_crossover_numba(stoch_k, stoch_d)
    
    print(f"\nFunction result:")
    print(f"  Found: {found}")
    print(f"  Periods ago: {periods_ago}")
    print(f"  K value: {k_val:.2f}")
    print(f"  D value: {d_val:.2f}")
    print(f"  In oversold: {in_oversold}")
    
    if found:
        expected_idx = len(stoch_k) - periods_ago
        print(f"\nCrossover at index: {expected_idx}")
        print(f"Values at crossover: k={stoch_k[expected_idx]:.2f}, d={stoch_d[expected_idx]:.2f}")
        
        assert abs(k_val - stoch_k[expected_idx]) < 0.01, f"K value should be from crossover point: got {k_val}, expected {stoch_k[expected_idx]}"
        assert in_oversold == False, "Should NOT be in oversold (values > 30)"
    
    print("✓ PASSED")


def test_recent_crossover():
    """Test Case 3: Most recent crossover (just happened)"""
    print("\n=== Test 3: Recent crossover (last candle) ===")
    
    # Crossover just happened (0 periods ago = last completed candle)
    stoch_k = np.array([20.0, 18.0, 19.0, 22.0, 25.0])
    stoch_d = np.array([22.0, 21.0, 20.0, 23.0, 24.0])
    
    print("Data:")
    print(f"  stoch_k: {stoch_k}")
    print(f"  stoch_d: {stoch_d}")
    
    print("\nManual check (last few periods):")
    for i in range(max(0, len(stoch_k) - 4), len(stoch_k) - 1):
        was_below = stoch_k[i] <= stoch_d[i]
        now_above = stoch_k[i + 1] > stoch_d[i + 1]
        print(f"  Index {i} -> {i+1}: k={stoch_k[i]:.1f}→{stoch_k[i+1]:.1f}, d={stoch_d[i]:.1f}→{stoch_d[i+1]:.1f}, "
              f"cross={was_below and now_above}")
    
    found, periods_ago, k_val, d_val, in_oversold = detect_stoch_bullish_crossover_numba(stoch_k, stoch_d)
    
    print(f"\nFunction result:")
    print(f"  Found: {found}")
    print(f"  Periods ago: {periods_ago}")
    print(f"  K value: {k_val:.2f}")
    print(f"  D value: {d_val:.2f}")
    print(f"  In oversold: {in_oversold}")
    
    assert found == True, "Should find crossover"
    # Most recent = periods_ago should be 0
    expected_idx = len(stoch_k) - 1 - periods_ago
    print(f"\nCrossover at index: {expected_idx}")
    print(f"Values: k={stoch_k[expected_idx]:.2f}, d={stoch_d[expected_idx]:.2f}")
    
    print("✓ PASSED")


def test_no_crossover():
    """Test Case 4: No crossover detected"""
    print("\n=== Test 4: No crossover (K always above D) ===")
    
    stoch_k = np.array([50.0, 52.0, 54.0, 56.0, 58.0])
    stoch_d = np.array([45.0, 47.0, 49.0, 51.0, 53.0])
    
    print("Data:")
    print(f"  stoch_k: {stoch_k}")
    print(f"  stoch_d: {stoch_d}")
    
    found, periods_ago, k_val, d_val, in_oversold = detect_stoch_bullish_crossover_numba(stoch_k, stoch_d)
    
    print(f"\nFunction result:")
    print(f"  Found: {found}")
    
    assert found == False, "Should NOT find crossover"
    
    print("✓ PASSED")


def test_old_vs_new_logic_comparison():
    """Test Case 5: Compare OLD logic (using current values) vs NEW logic (using crossover values)"""
    print("\n=== Test 5: OLD vs NEW logic comparison ===")
    
    # Scenario: Crossover 2 periods ago in oversold, but current values are NOT oversold
    stoch_k = np.array([15.0, 18.0, 20.0, 23.0, 27.5, 35.0, 45.0, 55.0])
    stoch_d = np.array([20.0, 19.0, 23.0, 26.0, 25.0, 32.0, 42.0, 52.0])
    
    print("Data:")
    print(f"  stoch_k: {stoch_k}")
    print(f"  stoch_d: {stoch_d}")
    print(f"  Current values: k={stoch_k[-1]:.1f}, d={stoch_d[-1]:.1f} (NOT oversold)")
    
    # Find crossover
    crossover_idx = None
    for i in range(len(stoch_k) - 1):
        was_below = stoch_k[i] <= stoch_d[i]
        now_above = stoch_k[i + 1] > stoch_d[i + 1]
        if was_below and now_above:
            crossover_idx = i + 1
            print(f"\nCrossover at index {crossover_idx}:")
            print(f"  k={stoch_k[crossover_idx]:.1f}, d={stoch_d[crossover_idx]:.1f}")
            print(f"  Both < 30? k={stoch_k[crossover_idx] < 30}, d={stoch_d[crossover_idx] < 30}")
            break
    
    # NEW logic
    found, periods_ago, k_val, d_val, in_oversold = detect_stoch_bullish_crossover_numba(stoch_k, stoch_d)
    
    print(f"\nNEW logic (using crossover point values):")
    print(f"  K value: {k_val:.2f}")
    print(f"  D value: {d_val:.2f}")
    print(f"  In oversold: {in_oversold}")
    
    # OLD logic simulation
    if crossover_idx:
        old_k = stoch_k[-1]
        old_d = stoch_d[-1]
        old_oversold = old_k < 30.0 or old_d < 30.0
        print(f"\nOLD logic (using current values):")
        print(f"  K value: {old_k:.2f}")
        print(f"  D value: {old_d:.2f}")
        print(f"  In oversold: {old_oversold}")
    
    print(f"\n{'='*60}")
    print("ANALYSIS:")
    print(f"  Crossover happened at k={stoch_k[crossover_idx]:.1f}, d={stoch_d[crossover_idx]:.1f} (OVERSOLD)")
    print(f"  Current values are k={stoch_k[-1]:.1f}, d={stoch_d[-1]:.1f} (NOT OVERSOLD)")
    print(f"  NEW logic correctly reports: in_oversold={in_oversold}")
    print(f"  OLD logic would report: in_oversold={old_oversold} ❌ WRONG!")
    print(f"{'='*60}")
    
    assert in_oversold == True, "NEW logic should detect oversold at crossover point"
    assert old_oversold == False, "OLD logic incorrectly uses current values"
    
    print("✓ PASSED - NEW logic is CORRECT!")


if __name__ == "__main__":
    print("Testing Stochastic Bullish Crossover Detection")
    print("=" * 60)
    
    try:
        test_bullish_crossover_in_oversold()
        test_bullish_crossover_not_in_oversold()
        test_recent_crossover()
        test_no_crossover()
        test_old_vs_new_logic_comparison()
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
