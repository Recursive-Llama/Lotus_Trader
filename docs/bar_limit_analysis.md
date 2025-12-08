# Bar Limit Analysis: What Can We Reasonably Handle?

**Date**: 2025-12-05  
**Question**: What's a good amount of bars? More is better without overwhelming. Maybe 3333 is fine, but maybe we could do 9999?

---

## Computational Complexity Analysis

### TA Tracker Operations

**Per position, per run:**

| Operation | Complexity | 3333 bars | 9999 bars |
|-----------|------------|-----------|-----------|
| **EMAs (7)** | O(n) | 23,331 ops | 69,993 ops |
| **ATR** | O(n) | 3,333 ops | 9,999 ops |
| **ADX** | O(n) | 3,333 ops | 9,999 ops |
| **RSI** | O(n) | ~60 ops* | ~60 ops* |
| **Volume z-score** | O(n log n) | ~35,000 ops | ~130,000 ops |
| **Slopes** | O(1) | ~50 ops | ~50 ops |
| **Total** | | **~65,000 ops** | **~220,000 ops** |

*RSI only computes last 60 bars regardless of total

**Time estimate**:
- 3333 bars: **~1-2ms** per position
- 9999 bars: **~3-5ms** per position

**Verdict**: ✅ **Both are very fast** - TA Tracker can easily handle 9999 bars

---

### Geometry Builder Operations

**Per position, per run:**

| Operation | Complexity | 3333 bars | 9999 bars |
|-----------|------------|-----------|-----------|
| **Swing detection** | O(n) | 3,333 ops | 9,999 ops |
| **Swing points** | ~0.02n | ~67 swings | ~200 swings |
| **Clustering** | O(n²) | ~4,500 ops | ~40,000 ops |
| **Theil-Sen (if kept)** | O(n²) per line | ~2,200 ops/line | ~20,000 ops/line |
| **Multiple trendlines** | 2-10 lines | ~11,000-110,000 ops | ~100,000-1,000,000 ops |
| **Total (no diagonals)** | | **~8,000 ops** | **~50,000 ops** |
| **Total (with diagonals)** | | **~20,000-120,000 ops** | **~150,000-1,050,000 ops** |

**Time estimate** (without diagonals):
- 3333 bars: **~2-5ms** per position
- 9999 bars: **~10-20ms** per position

**Time estimate** (with diagonals):
- 3333 bars: **~5-15ms** per position
- 9999 bars: **~50-200ms** per position ⚠️

**Verdict**: 
- ✅ **9999 bars is fine** if we remove diagonals
- ⚠️ **9999 bars is heavy** if we keep diagonals (Theil-Sen is O(n²))

---

## Database Query Performance

### Supabase/PostgreSQL Limits

**Query performance**:
- **1,000 bars**: ~10-20ms query time
- **3,333 bars**: ~30-50ms query time
- **9,999 bars**: ~80-150ms query time
- **20,000 bars**: ~200-400ms query time

**Memory per query**:
- Each bar: ~100 bytes (timestamp, 5 floats)
- 9,999 bars: ~1MB per position
- 100 positions: ~100MB (manageable)

**Verdict**: ✅ **9999 bars is fine** - query time is acceptable

---

## Memory Usage

### Per Position

**TA Tracker**:
- 9,999 bars × 6 fields × 8 bytes = ~480KB
- Plus intermediate arrays (EMAs, etc.) = ~1MB total

**Geometry Builder**:
- 9,999 bars × 5 fields × 8 bytes = ~400KB
- Plus swing points, clusters = ~2MB total

**Total per position**: ~3MB

**For 100 positions**: ~300MB (very manageable)

**Verdict**: ✅ **9999 bars is fine** - memory is not a concern

---

## Practical Considerations

### Time Coverage by Timeframe

**9999 bars coverage**:

| Timeframe | Bars | Time Coverage |
|-----------|------|---------------|
| **1m** | 9,999 | ~166.7 hours (~6.9 days) |
| **15m** | 9,999 | ~104.2 days (~3.5 months) |
| **1h** | 9,999 | ~416.6 days (~1.1 years) |
| **4h** | 9,999 | ~1,666.7 days (~4.6 years) |

**3333 bars coverage**:

| Timeframe | Bars | Time Coverage |
|-----------|------|---------------|
| **1m** | 3,333 | ~55.5 hours (~2.3 days) |
| **15m** | 3,333 | ~34.7 days (~1.2 months) |
| **1h** | 3,333 | ~138.9 days (~4.6 months) |
| **4h** | 3,333 | ~555.5 days (~1.5 years) |

### What's Actually Needed?

**For EMAs**:
- EMA333 needs 333+ bars (10x buffer = 3,330 bars)
- **9999 bars gives 30x buffer** ✅

**For Geometry**:
- S/R levels: Need enough swing points for clustering
- 9,999 bars → ~200 swing points (good for clustering)
- 3,333 bars → ~67 swing points (still good)

**For Long-term Structure**:
- 1m: 9,999 bars = ~7 days (catches weekly patterns)
- 1m: 3,333 bars = ~2.3 days (might miss weekly patterns)

---

## Recommendation: **9999 Bars**

### Why 9999 is Better Than 3333

1. ✅ **Better structure detection**:
   - 1m: 7 days vs 2.3 days (catches weekly patterns)
   - More swing points = better S/R clustering

2. ✅ **Still very fast**:
   - TA Tracker: ~3-5ms per position (negligible)
   - Geometry (no diagonals): ~10-20ms per position (acceptable)
   - Database query: ~80-150ms (acceptable)

3. ✅ **Future-proof**:
   - Room for growth (more complex TA in future)
   - Better for backtesting/analysis

4. ✅ **No memory concerns**:
   - ~3MB per position is tiny
   - 100 positions = 300MB (nothing)

### Why Not More (e.g., 20,000)?

**Trade-offs**:
- ⚠️ **Query time**: 20K bars = ~200-400ms (slower but acceptable)
- ⚠️ **Geometry computation**: 20K bars → ~400 swing points → ~160K clustering ops (still OK)
- ⚠️ **Diminishing returns**: More bars doesn't always mean better signals

**Verdict**: 9999 is a good sweet spot - more than enough, not too much

---

## Implementation

### TA Tracker (line 193)

**Change from**:
```python
.limit(400)
```

**To**:
```python
.limit(9999)
```

### Geometry Builder (line 1020)

**Change from**:
```python
bars = self._fetch_bars(contract, chain, now, None)  # All data
```

**To**:
```python
bars = self._fetch_bars(contract, chain, now, None)
if len(bars) > 9999:
    bars = bars[-9999:]  # Keep most recent 9999 bars
```

**Or use lookback_days**:
```python
lookback_minutes = self.lookback_days * 24 * 60
bars = self._fetch_bars(contract, chain, now, lookback_minutes)
if len(bars) > 9999:
    bars = bars[-9999:]  # Hard limit
```

---

## Performance Comparison

### Current (Geometry: unlimited, TA: 400)

**1m position, 90 days old**:
- TA: 400 bars = ~1ms
- Geometry: 129,600 bars = ~500ms-2s ⚠️⚠️

### Proposed (Both: 9999)

**1m position, 90 days old**:
- TA: 9,999 bars = ~3-5ms
- Geometry: 9,999 bars = ~10-20ms (no diagonals)

**Improvement**: **25-100x faster** for geometry

---

## Summary

### Recommendation: **9999 bars for both TA and Geometry**

**Why**:
1. ✅ **Fast enough**: ~3-5ms (TA), ~10-20ms (Geometry)
2. ✅ **Better coverage**: 7 days for 1m (catches weekly patterns)
3. ✅ **More swing points**: Better S/R clustering
4. ✅ **Future-proof**: Room for growth
5. ✅ **No memory concerns**: ~3MB per position

**Trade-off**:
- ⚠️ **Slightly slower** than 3333 (but still very fast)
- ✅ **Much better** than unlimited (current geometry)

**If we remove diagonals** (recommended):
- Geometry: ~10-20ms per position (excellent)
- Total: ~15-25ms per position (very fast)

**If we keep diagonals** (not recommended):
- Geometry: ~50-200ms per position (acceptable but heavy)
- Total: ~55-205ms per position (still acceptable)

---

## Final Answer

**9999 bars is a great choice**:
- ✅ More data = better signals
- ✅ Still very fast computation
- ✅ Reasonable database query time
- ✅ No memory concerns
- ✅ Good balance between coverage and performance

**3333 bars is also fine**, but 9999 gives you:
- 3x more data
- Only 2-3x more computation time
- Better structure detection
- Future-proof

**Recommendation**: **Go with 9999 bars** - the extra computation is negligible, and the benefits are significant.

---

**End of Analysis**

