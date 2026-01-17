"""
Hyperliquid Market Cap Fetcher

Fetches market cap data from CoinGecko for Hyperliquid tokens and stores
in token_cap_bucket table for bucket tagging.

Usage:
    - At bootstrap: fetch_hl_market_caps() 
    - Daily: same function via scheduler
    
This integrates with the existing Solana bucket tagging flow - PM Core
queries token_cap_bucket for both Solana and Hyperliquid positions.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional
from urllib.request import urlopen, Request

from supabase import Client

from .hl_coingecko_mapping import HL_TO_COINGECKO, get_all_coingecko_ids

logger = logging.getLogger(__name__)

# CoinGecko API
COINGECKO_API = "https://api.coingecko.com/api/v3"

# Bucket thresholds (same as cap_bucket_tagging.py)
BUCKET_THRESHOLDS = [
    ("nano", 0, 100_000),
    ("micro", 100_000, 5_000_000),
    ("mid", 5_000_000, 50_000_000),
    ("big", 50_000_000, 500_000_000),
    ("large", 500_000_000, 1_000_000_000),
    ("xl", 1_000_000_000, float("inf")),
]


def classify_bucket(market_cap: float) -> str:
    """Classify market cap into bucket."""
    for name, lower, upper in BUCKET_THRESHOLDS:
        if lower <= market_cap < upper:
            return name
    return "xl"


def _fetch_coingecko_prices(cg_ids: List[str]) -> Dict[str, Dict]:
    """
    Fetch prices and market caps from CoinGecko.
    
    Args:
        cg_ids: List of CoinGecko IDs
        
    Returns:
        Dict mapping CoinGecko ID -> {usd, usd_market_cap}
    """
    all_data = {}
    batch_size = 100  # CoinGecko allows up to 100 IDs per request
    
    for i in range(0, len(cg_ids), batch_size):
        batch = cg_ids[i:i + batch_size]
        ids_str = ",".join(batch)
        url = f"{COINGECKO_API}/simple/price?ids={ids_str}&vs_currencies=usd&include_market_cap=true"
        
        req = Request(url, headers={
            "Accept": "application/json",
            "User-Agent": "LotusPM/1.0"
        })
        
        try:
            with urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                all_data.update(data)
        except Exception as e:
            logger.warning(f"CoinGecko batch {i//batch_size + 1} failed: {e}")
            # Rate limit - wait and retry
            if "429" in str(e):
                time.sleep(60)
                try:
                    with urlopen(req, timeout=30) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        all_data.update(data)
                except Exception as e2:
                    logger.error(f"CoinGecko retry failed: {e2}")
        
        # Small delay between batches to avoid rate limiting
        if i + batch_size < len(cg_ids):
            time.sleep(1)
    
    return all_data


def fetch_hl_market_caps(sb: Client) -> Dict[str, any]:
    """
    Fetch market caps for all Hyperliquid tokens and store in token_cap_bucket.
    
    Args:
        sb: Supabase client
        
    Returns:
        Dict with status, counts
    """
    logger.info("Fetching Hyperliquid market caps from CoinGecko...")
    
    # Get all unique CoinGecko IDs
    cg_ids = get_all_coingecko_ids()
    logger.info(f"Fetching {len(cg_ids)} unique CoinGecko IDs")
    
    # Fetch from CoinGecko
    cg_data = _fetch_coingecko_prices(cg_ids)
    if not cg_data:
        logger.error("No data returned from CoinGecko")
        return {"status": "error", "error": "No CoinGecko data", "updated": 0}
    
    logger.info(f"Got data for {len(cg_data)} tokens from CoinGecko")
    
    # Build rows for upsert
    rows = []
    now = datetime.now(timezone.utc).isoformat()
    
    for hl_symbol, cg_id in HL_TO_COINGECKO.items():
        if cg_id not in cg_data:
            logger.debug(f"No CoinGecko data for {hl_symbol} ({cg_id})")
            continue
            
        market_cap = cg_data[cg_id].get("usd_market_cap", 0)
        if not market_cap or market_cap <= 0:
            continue
            
        bucket = classify_bucket(market_cap)
        
        rows.append({
            "token_contract": hl_symbol,  # HL uses symbol as contract
            "chain": "hyperliquid",
            "bucket": bucket,
            "market_cap_usd": market_cap,
            "updated_at": now,
        })
    
    if not rows:
        logger.warning("No valid market cap data to store")
        return {"status": "no_data", "updated": 0}
    
    # Upsert to token_cap_bucket
    try:
        sb.table("token_cap_bucket").upsert(
            rows, 
            on_conflict="token_contract,chain"
        ).execute()
        
        logger.info(f"Upserted {len(rows)} Hyperliquid bucket tags to token_cap_bucket")
        
        # Log bucket distribution
        bucket_counts = {}
        for row in rows:
            b = row["bucket"]
            bucket_counts[b] = bucket_counts.get(b, 0) + 1
        logger.info(f"Bucket distribution: {bucket_counts}")
        
        return {
            "status": "ok",
            "updated": len(rows),
            "bucket_distribution": bucket_counts,
        }
        
    except Exception as e:
        logger.error(f"Failed to upsert bucket tags: {e}")
        return {"status": "error", "error": str(e), "updated": 0}


def main():
    """CLI entry point for testing."""
    import os
    from supabase import create_client
    
    logging.basicConfig(level=logging.INFO)
    
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", os.getenv("SUPABASE_KEY", ""))
    
    if not url or not key:
        print("SUPABASE_URL and SUPABASE_KEY required")
        return
        
    sb = create_client(url, key)
    result = fetch_hl_market_caps(sb)
    print(f"Result: {result}")


if __name__ == "__main__":
    main()
