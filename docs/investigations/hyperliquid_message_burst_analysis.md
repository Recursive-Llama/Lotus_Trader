# Hyperliquid Message Burst Analysis

**Date**: 2025-12-31  
**Question**: Will all 15m candles close at the same time, causing a message burst?

---

## Candle Close Timing

### How Candle Closes Work

**15m Candles**:
- Close at: :00, :15, :30, :45 of each hour
- All markets close at the **exact same time**
- Example: At 14:15:00, all 260 markets' 15m candles close simultaneously

**1h Candles**:
- Close at: Top of each hour (:00)
- All markets close at the **exact same time**
- Example: At 15:00:00, all 260 markets' 1h candles close simultaneously

**4h Candles**:
- Close at: :00, :04, :08, :12, :16, :20 (every 4 hours)
- All markets close at the **exact same time**

---

## Message Burst Analysis

### Scenario: 15m Candle Close

**At 14:15:00**:
- All 260 markets' 15m candles close
- **Burst**: ~260 messages in a few seconds (one per market)
- **Then**: Partial updates spread over next 15 minutes

**Message Pattern**:
```
14:15:00 - 260 messages (candle closes)
14:15:01 - 5 messages (partial updates)
14:15:02 - 3 messages (partial updates)
...
14:15:15 - 2 messages (partial updates)
...
14:29:59 - 1 message (final partial update)
14:30:00 - 260 messages (next candle closes)
```

**Peak Load**: 260 messages in ~1-2 seconds

---

## Potential Issues

### 1. Database Write Burst

**Risk**: 260 simultaneous writes could bottleneck

**Mitigation**:
- Modern databases (PostgreSQL/Supabase) handle this easily
- Batch inserts are efficient
- Test: Should handle 260 writes in <1 second

**If Issue**:
- Batch writes (50 per batch, spread over 5 seconds)
- Use async writes with queue

### 2. Processing Burst

**Risk**: All positions get new bars simultaneously

**Current Behavior**:
- PM Core Tick already processes all positions
- Runs on schedule (every 15m, 1h, 4h)
- Already handles "all positions at once"

**Impact**: 
- PM Core Tick runs at :15, :30, :45, :00 anyway
- Candle close burst happens at same time
- **No additional load** - PM tick would run anyway

### 3. WebSocket Message Queue

**Risk**: Message queue could fill up during burst

**Mitigation**:
- Bounded queue (max 1000 messages)
- Drop oldest if queue full (backpressure)
- Process queue with workers

---

## Recommendation

### ✅ Accept the Burst (Initially)

**Rationale**:
1. **Database**: Modern DBs handle 260 writes easily
2. **PM Core Tick**: Already processes all positions at once
3. **Timing**: Burst happens at same time as PM tick (no extra load)
4. **Frequency**: Only happens 4 times per hour (15m candles)

**Monitoring**:
- Track database write latency during candle closes
- Track PM Core Tick processing time
- Add batching if latency > 1 second

### ⚠️ If Issues Arise

**Add Batching**:
```python
class HyperliquidCandleWSIngester:
    def __init__(self):
        self.candle_buffer = []
        self.batch_size = 50
        self.batch_interval = 0.1  # 100ms between batches
    
    async def _write_candles(self):
        while True:
            if len(self.candle_buffer) >= self.batch_size:
                batch = self.candle_buffer[:self.batch_size]
                self.candle_buffer = self.candle_buffer[self.batch_size:]
                await self._write_batch(batch)
            await asyncio.sleep(self.batch_interval)
```

---

## Test Plan

1. **Monitor Message Burst**:
   - Log message count per second
   - Track during candle closes (:00, :15, :30, :45)

2. **Monitor Database Writes**:
   - Track write latency during bursts
   - Check for connection pool exhaustion

3. **Monitor PM Core Tick**:
   - Track processing time during candle closes
   - Check if it slows down

4. **Load Test**:
   - Simulate 260 simultaneous candle closes
   - Measure system performance

---

## Conclusion

**Likely Not an Issue**:
- Database handles 260 writes easily
- PM Core Tick already processes all positions
- Burst happens at scheduled PM tick time (no extra load)

**Action**: Start with accepting the burst, monitor, add batching if needed.

