"""
Hyperliquid Historical Data Backfill

Uses the candleSnapshot REST API to backfill historical OHLC data for:
- Main DEX (BTC, ETH, etc.)
- HIP-3 markets (xyz:TSLA, etc.)

API Format:
POST https://api.hyperliquid.xyz/info
{
  "type": "candleSnapshot",
  "req": {
    "coin": "BTC",  // or "xyz:TSLA" for HIP-3
    "interval": "15m",
    "startTime": <epoch_ms>,
    "endTime": <epoch_ms>
  }
}
"""

import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import requests
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# Hyperliquid API endpoint
INFO_URL = "https://api.hyperliquid.xyz/info"


def backfill_from_hyperliquid(
    sb: Client,
    coin: str,
    interval: str,
    days: int = 90,
    end_time: Optional[datetime] = None,
    max_retries: int = 5,
) -> int:
    """
    Backfill historical candle data from Hyperliquid.
    
    Includes retry logic with exponential backoff for rate limiting (429 errors).
    
    Args:
        sb: Supabase client
        coin: Symbol to backfill ("BTC" for main DEX, "xyz:TSLA" for HIP-3)
        interval: Candle interval ("15m", "1h", "4h")
        days: Number of days to backfill (default 90)
        end_time: End time for backfill (default: now)
        max_retries: Maximum number of retries for rate limiting (default 5)
    
    Returns:
        Number of candles written
    """
    import time
    
    if end_time is None:
        end_time = datetime.now(timezone.utc)
    
    start_time = end_time - timedelta(days=days)
    
    # Convert to epoch milliseconds
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)
    
    logger.info(
        "Backfilling %s %s: %s to %s (%d days)",
        coin, interval, start_time.isoformat(), end_time.isoformat(), days
    )
    
    # Request candle snapshot with retry logic
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": coin,
            "interval": interval,
            "startTime": start_ms,
            "endTime": end_ms,
        }
    }
    
    candles = None
    for attempt in range(max_retries):
        try:
            response = requests.post(INFO_URL, json=payload, timeout=30)
            
            if response.status_code == 429:
                # Rate limited - exponential backoff with jitter
                wait_time = (2 ** attempt) + (0.5 * attempt)  # 1, 2.5, 4.5, 8.5, 16.5 seconds
                logger.warning("Rate limited for %s %s, waiting %.1fs (attempt %d/%d)", 
                              coin, interval, wait_time, attempt + 1, max_retries)
                time.sleep(wait_time)
                continue
            
            if response.status_code != 200:
                logger.error("candleSnapshot failed for %s: %d - %s", coin, response.status_code, response.text[:200])
                return 0
            
            candles = response.json()
            break  # Success, exit retry loop
            
        except requests.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt)
                logger.warning("Request failed for %s, retrying in %ds: %s", coin, wait_time, e)
                time.sleep(wait_time)
            else:
                logger.error("Request failed for %s after %d retries: %s", coin, max_retries, e)
                return 0
    
    if candles is None:
        logger.error("Failed to get candles for %s %s after %d retries", coin, interval, max_retries)
        return 0
    
    if not isinstance(candles, list):
        logger.error("Unexpected response format for %s: %s", coin, type(candles))
        return 0
    
    if not candles:
        logger.warning("No candles returned for %s %s", coin, interval)
        return 0
    
    logger.info("Retrieved %d candles for %s %s", len(candles), coin, interval)
    
    # Transform and write to database
    rows = []
    for c in candles:
        ts_ms = c.get("t")
        if not ts_ms:
            continue
        
        rows.append({
            "token": c.get("s", coin),  # Symbol
            "timeframe": c.get("i", interval),  # Interval
            "ts": datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat(),
            "open": float(c.get("o", 0)),
            "high": float(c.get("h", 0)),
            "low": float(c.get("l", 0)),
            "close": float(c.get("c", 0)),
            "volume": float(c.get("v", 0)),
            "trades": int(c.get("n", 0)),
            "source": "hyperliquid_snapshot",
        })
    
    if not rows:
        logger.warning("No valid candles to write for %s %s", coin, interval)
        return 0
    
    # Batch upsert with retry logic for transient errors
    BATCH_SIZE = 500
    MAX_WRITE_RETRIES = 3
    total_written = 0
    failed_batches = 0
    
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        batch_written = False
        
        for retry in range(MAX_WRITE_RETRIES):
            try:
                sb.table("hyperliquid_price_data_ohlc").upsert(
                    batch,
                    on_conflict="token,timeframe,ts"
                ).execute()
                total_written += len(batch)
                batch_written = True
                break  # Success, exit retry loop
            except Exception as e:
                error_str = str(e)
                is_transient = (
                    "Resource temporarily unavailable" in error_str or
                    "connection" in error_str.lower() or
                    "timeout" in error_str.lower() or
                    "Errno 35" in error_str
                )
                
                if is_transient and retry < MAX_WRITE_RETRIES - 1:
                    wait_time = (2 ** retry) + 0.5  # 1.5s, 2.5s, 4.5s
                    logger.warning(
                        "Transient write error for %s batch %d, retrying in %.1fs: %s",
                        coin, i // BATCH_SIZE, wait_time, error_str[:100]
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(
                        "Failed to write batch %d for %s after %d attempts: %s",
                        i // BATCH_SIZE, coin, retry + 1, error_str
                    )
                    failed_batches += 1
                    break  # Give up on this batch
    
    if failed_batches > 0:
        logger.error(
            "BACKFILL INCOMPLETE: %s %s - wrote %d/%d candles, %d batches failed",
            coin, interval, total_written, len(rows), failed_batches
        )
    else:
        logger.info("Wrote %d candles for %s %s", total_written, coin, interval)
    
    return total_written



def backfill_multiple(
    sb: Client,
    coins: List[str],
    intervals: List[str],
    days: int = 90,
) -> Dict[str, int]:
    """
    Backfill multiple coins and intervals.
    
    Args:
        sb: Supabase client
        coins: List of symbols to backfill
        intervals: List of intervals to backfill
        days: Number of days to backfill
    
    Returns:
        Dict mapping "coin:interval" to candles written
    """
    results = {}
    total = len(coins) * len(intervals)
    completed = 0
    
    for coin in coins:
        for interval in intervals:
            key = f"{coin}:{interval}"
            try:
                count = backfill_from_hyperliquid(sb, coin, interval, days)
                results[key] = count
                completed += 1
                logger.info("Progress: %d/%d backfills complete", completed, total)
            except Exception as e:
                logger.error("Failed to backfill %s: %s", key, e)
                results[key] = 0
    
    return results


def backfill_for_position(
    sb: Client,
    token_contract: str,
    intervals: Optional[List[str]] = None,
    days: int = 90,
) -> Dict[str, int]:
    """
    Backfill data for a specific position.
    
    Called when a new Hyperliquid position is created.
    
    Args:
        sb: Supabase client
        token_contract: Symbol (e.g., "BTC" or "xyz:TSLA")
        intervals: List of intervals to backfill (default: ["15m", "1h", "4h"])
        days: Number of days to backfill
    
    Returns:
        Dict mapping interval to candles written
    """
    if intervals is None:
        intervals = ["15m", "1h", "4h"]
    
    results = {}
    for interval in intervals:
        count = backfill_from_hyperliquid(sb, token_contract, interval, days)
        results[interval] = count
    
    return results


# CLI for manual backfill
if __name__ == "__main__":
    import argparse
    
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="Backfill Hyperliquid candle data")
    parser.add_argument("--coins", type=str, default="BTC,ETH", help="Comma-separated list of coins")
    parser.add_argument("--intervals", type=str, default="15m,1h,4h", help="Comma-separated list of intervals")
    parser.add_argument("--days", type=int, default=90, help="Number of days to backfill")
    
    args = parser.parse_args()
    
    # Initialize Supabase
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_KEY", "")
    if not supabase_url or not supabase_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
    
    sb = create_client(supabase_url, supabase_key)
    
    coins = [c.strip() for c in args.coins.split(",") if c.strip()]
    intervals = [i.strip() for i in args.intervals.split(",") if i.strip()]
    
    results = backfill_multiple(sb, coins, intervals, args.days)
    
    print("\n=== Backfill Results ===")
    total = 0
    for key, count in results.items():
        print(f"  {key}: {count} candles")
        total += count
    print(f"  TOTAL: {total} candles")

