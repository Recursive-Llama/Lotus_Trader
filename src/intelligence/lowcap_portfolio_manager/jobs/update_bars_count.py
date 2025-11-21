#!/usr/bin/env python3
"""
Periodic job to update bars_count for all positions and check for dormant → watchlist transitions.

Runs hourly to:
1. Count actual bars in lowcap_price_data_ohlc for each position
2. Update bars_count in lowcap_positions
3. Auto-flip dormant → watchlist when bars_count >= 333 (minimum required)

This ensures positions transition correctly as data accumulates from scheduled jobs.
"""

from __future__ import annotations

import os
import logging
from typing import Dict, Any

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
logger = logging.getLogger(__name__)


def update_all_bars_counts() -> Dict[str, Any]:
    """
    Update bars_count for all positions and check for dormant → watchlist transitions.
    
    Returns:
        Dict with summary stats
    """
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
    
    sb: Client = create_client(url, key)
    
    # Get only dormant positions (watchlist already has enough data, no need to update)
    positions = (
        sb.table("lowcap_positions")
        .select("id,token_contract,token_chain,timeframe,status,bars_count")
        .eq("status", "dormant")  # Only process dormant positions
        .limit(10000)
        .execute()
    ).data or []
    
    if not positions:
        logger.info("No dormant positions to update")
        return {"updated": 0, "flipped": 0, "errors": 0}
    
    logger.info(f"Updating bars_count for {len(positions)} dormant positions")
    
    updated = 0
    flipped = 0
    errors = 0
    
    # Group by (token_contract, chain, timeframe) to avoid duplicate counts
    # Cache bars_count per key since multiple positions can share same token/chain/timeframe
    bars_count_cache: Dict[tuple, int] = {}
    
    for pos in positions:
        try:
            position_id = pos["id"]
            token_contract = pos["token_contract"]
            chain = pos["token_chain"]
            timeframe = pos["timeframe"]
            current_status = pos.get("status", "dormant")
            current_bars_count = pos.get("bars_count", 0)
            
            # Count actual bars in database for this token/chain/timeframe
            key = (token_contract, chain, timeframe)
            if key not in bars_count_cache:
                # Count bars (use count='exact' for accurate count)
                result = (
                    sb.table("lowcap_price_data_ohlc")
                    .select("timestamp", count="exact")
                    .eq("token_contract", token_contract)
                    .eq("chain", chain)
                    .eq("timeframe", timeframe)
                    .execute()
                )
                
                bars_count = result.count if hasattr(result, "count") else len(result.data) if result.data else 0
                bars_count_cache[key] = bars_count
            else:
                # Reuse cached count
                bars_count = bars_count_cache[key]
            
            # Only update if bars_count changed
            if bars_count != current_bars_count:
                update_data = {"bars_count": bars_count}
                
                # Check for dormant → watchlist transition (minimum 333 bars)
                if current_status == "dormant" and bars_count >= 333:
                    update_data["status"] = "watchlist"
                    flipped += 1
                    logger.info(
                        f"Position {position_id} ({timeframe}): "
                        f"dormant → watchlist (bars_count: {current_bars_count} → {bars_count})"
                    )
                
                # Update position
                sb.table("lowcap_positions").update(update_data).eq("id", position_id).execute()
                updated += 1
                
        except Exception as e:
            errors += 1
            logger.warning(f"Error updating bars_count for position {pos.get('id')}: {e}")
    
    logger.info(f"Bars count update complete: {updated} updated, {flipped} flipped (dormant→watchlist), {errors} errors")
    
    return {
        "updated": updated,
        "flipped": flipped,
        "errors": errors,
        "total_processed": len(positions),
    }


def main() -> None:
    """Entry point for periodic job."""
    import logging
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    
    try:
        result = update_all_bars_counts()
        logger.info(f"✅ Bars count update job complete: {result}")
    except Exception as e:
        logger.error(f"❌ Bars count update job failed: {e}")
        raise


if __name__ == "__main__":
    main()

