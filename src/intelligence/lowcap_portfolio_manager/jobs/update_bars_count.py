#!/usr/bin/env python3
"""
Periodic job to update bars_count for all positions and check for dormant → watchlist transitions.

Runs hourly to:
1. Count actual bars in lowcap_price_data_ohlc for each position
2. Update bars_count in lowcap_positions
3. Auto-flip dormant → watchlist when bars_count >= 333 (minimum required)
4. For 1m timeframe: only allow watchlist if NO higher timeframe (15m/1h/4h) has >= 333 bars

This ensures positions transition correctly as data accumulates from scheduled jobs.
"""

from __future__ import annotations

import os
import logging
from typing import Dict, Any, List

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
logger = logging.getLogger(__name__)

HIGHER_TIMEFRAMES = ["15m", "1h", "4h"]
MIN_BARS_REQUIRED = 333


def _check_higher_tf_ready(sb: Client, token_contract: str, chain: str, bars_count_cache: Dict[tuple, int]) -> bool:
    """
    Check if any higher timeframe (15m/1h/4h) has >= 333 bars for this token.
    
    Returns True if any higher TF is ready (meaning 1m should stay dormant).
    """
    for tf in HIGHER_TIMEFRAMES:
        key = (token_contract, chain, tf)
        if key not in bars_count_cache:
            result = (
                sb.table("lowcap_price_data_ohlc")
                .select("timestamp", count="exact")
                .eq("token_contract", token_contract)
                .eq("chain", chain)
                .eq("timeframe", tf)
                .execute()
            )
            bars_count = result.count if hasattr(result, "count") else len(result.data) if result.data else 0
            bars_count_cache[key] = bars_count
        else:
            bars_count = bars_count_cache[key]
        
        if bars_count >= MIN_BARS_REQUIRED:
            return True
    return False


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
    
    # Get dormant positions AND 1m watchlist positions (to check for demotion)
    positions = (
        sb.table("lowcap_positions")
        .select("id,token_contract,token_chain,timeframe,status,bars_count")
        .in_("status", ["dormant", "watchlist"])
        .limit(10000)
        .execute()
    ).data or []
    
    if not positions:
        logger.info("No dormant/watchlist positions to update")
        return {"updated": 0, "flipped": 0, "demoted": 0, "errors": 0}
    
    logger.info(f"Updating bars_count for {len(positions)} dormant/watchlist positions")
    
    updated = 0
    flipped = 0
    demoted = 0
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
            
            update_data: Dict[str, Any] = {}
            
            # Only update bars_count if changed
            if bars_count != current_bars_count:
                update_data["bars_count"] = bars_count
            
            # Handle 1m timeframe special logic
            if timeframe == "1m":
                higher_tf_ready = _check_higher_tf_ready(sb, token_contract, chain, bars_count_cache)
                
                if current_status == "watchlist" and higher_tf_ready:
                    # Demote 1m watchlist → dormant because higher TF is now ready
                    update_data["status"] = "dormant"
                    demoted += 1
                    logger.info(
                        f"Position {position_id} (1m): "
                        f"watchlist → dormant (higher timeframe now has >= {MIN_BARS_REQUIRED} bars)"
                    )
                elif current_status == "dormant" and bars_count >= MIN_BARS_REQUIRED and not higher_tf_ready:
                    # Only promote 1m if it has enough bars AND no higher TF is ready
                    update_data["status"] = "watchlist"
                    flipped += 1
                    logger.info(
                        f"Position {position_id} (1m): "
                        f"dormant → watchlist (bars_count: {current_bars_count} → {bars_count}, no higher TF ready)"
                    )
                # If dormant with enough bars but higher TF ready, stay dormant (no action needed)
            else:
                # Non-1m timeframes: normal logic
                if current_status == "dormant" and bars_count >= MIN_BARS_REQUIRED:
                    update_data["status"] = "watchlist"
                    flipped += 1
                    logger.info(
                        f"Position {position_id} ({timeframe}): "
                        f"dormant → watchlist (bars_count: {current_bars_count} → {bars_count})"
                    )
            
            # Update position if there are changes
            if update_data:
                sb.table("lowcap_positions").update(update_data).eq("id", position_id).execute()
                updated += 1
                
        except Exception as e:
            errors += 1
            logger.warning(f"Error updating bars_count for position {pos.get('id')}: {e}")
    
    logger.info(
        f"Bars count update complete: {updated} updated, {flipped} flipped (dormant→watchlist), "
        f"{demoted} demoted (1m watchlist→dormant), {errors} errors"
    )
    
    return {
        "updated": updated,
        "flipped": flipped,
        "demoted": demoted,
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

