"""
Episode-Based Token Blocking

Deterministic safety latch for preventing re-entry after failed attempts.
This is NOT learned - it's immediate risk control.

Key rules:
- S1 failure blocks S1 + S2
- S2 failure blocks S2 only
- Any observed success unblocks (even if we didn't participate)
- Failure only recorded if we actually acted (skipping is correct)

Part of Scaling A/E v2 Implementation (Phase 6)
"""

from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def record_attempt_failure(
    sb_client,
    token_contract: str,
    token_chain: str,
    timeframe: str,
    entered_s1: bool,
    entered_s2: bool,
    book_id: str = "onchain_crypto"
) -> None:
    """
    Called when an attempt ends at S0 (failure).
    Only blocks if we actually acted in S1 or S2.
    
    Args:
        sb_client: Supabase client
        token_contract: Token contract address
        token_chain: Chain name
        timeframe: Position timeframe
        entered_s1: True if we took an S1 entry in this attempt
        entered_s2: True if we took an S2 entry in this attempt
        book_id: Book identifier
    """
    # We skipped - correct decision, no block needed
    if not entered_s1 and not entered_s2:
        logger.debug(
            "EPISODE_BLOCK: Skipping record (no entry) | %s/%s tf=%s",
            token_contract[:12], token_chain, timeframe
        )
        return
    
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    
    # Build upsert payload - record ALL entries that happened
    payload: Dict[str, Any] = {
        "token_contract": token_contract,
        "token_chain": token_chain,
        "timeframe": timeframe,
        "book_id": book_id,
        "updated_at": now_iso,
    }
    
    # Two separate ifs (not elif) so we record BOTH if applicable
    if entered_s1:
        # S1 failure blocks BOTH S1 and S2
        payload["blocked_s1"] = True
        payload["blocked_s2"] = True
        payload["last_s1_failure_ts"] = now_iso
        logger.info(
            "EPISODE_BLOCK: Recording S1 failure (blocks S1+S2) | %s/%s tf=%s",
            token_contract[:12], token_chain, timeframe
        )
    
    if entered_s2:
        # S2 failure blocks S2 and records timestamp
        # (if S1 also failed, S2 is already blocked above, but we still record the timestamp)
        payload["blocked_s2"] = True
        payload["last_s2_failure_ts"] = now_iso
        logger.info(
            "EPISODE_BLOCK: Recording S2 failure (blocks S2) | %s/%s tf=%s",
            token_contract[:12], token_chain, timeframe
        )
    
    try:
        sb_client.table("token_timeframe_blocks").upsert(
            payload,
            on_conflict="token_contract,token_chain,timeframe,book_id"
        ).execute()
    except Exception as e:
        logger.error(
            "EPISODE_BLOCK: Failed to record failure | %s/%s tf=%s | error=%s",
            token_contract[:12], token_chain, timeframe, e
        )


def record_episode_success(
    sb_client,
    token_contract: str,
    token_chain: str,
    timeframe: str,
    book_id: str = "onchain_crypto"
) -> None:
    """
    Called when any episode reaches S3 (success observed).
    Clears blocks if success is after last failure timestamp.
    
    Success can be observed without participation - we don't need to have
    taken an entry to observe that the environment succeeded.
    """
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    
    try:
        # Get current block state
        result = sb_client.table("token_timeframe_blocks").select("*").eq(
            "token_contract", token_contract
        ).eq("token_chain", token_chain).eq(
            "timeframe", timeframe
        ).eq("book_id", book_id).limit(1).execute()
        
        if not result.data:
            logger.debug(
                "EPISODE_BLOCK: No blocks to clear (success observed) | %s/%s tf=%s",
                token_contract[:12], token_chain, timeframe
            )
            return
        
        row = result.data[0]
        updates: Dict[str, Any] = {
            "last_success_ts": now_iso,
            "updated_at": now_iso
        }
        
        # Unblock S1 if success is after last S1 failure
        if row.get("blocked_s1") and row.get("last_s1_failure_ts"):
            last_failure = datetime.fromisoformat(
                row["last_s1_failure_ts"].replace("Z", "+00:00")
            )
            if now > last_failure:
                updates["blocked_s1"] = False
                logger.info(
                    "EPISODE_BLOCK: Unblocking S1 (success observed) | %s/%s tf=%s",
                    token_contract[:12], token_chain, timeframe
                )
        
        # Unblock S2 if success is after last S2 failure
        if row.get("blocked_s2") and row.get("last_s2_failure_ts"):
            last_failure = datetime.fromisoformat(
                row["last_s2_failure_ts"].replace("Z", "+00:00")
            )
            if now > last_failure:
                updates["blocked_s2"] = False
                logger.info(
                    "EPISODE_BLOCK: Unblocking S2 (success observed) | %s/%s tf=%s",
                    token_contract[:12], token_chain, timeframe
                )
        
        sb_client.table("token_timeframe_blocks").update(updates).eq(
            "token_contract", token_contract
        ).eq("token_chain", token_chain).eq(
            "timeframe", timeframe
        ).eq("book_id", book_id).execute()
        
    except Exception as e:
        logger.error(
            "EPISODE_BLOCK: Failed to record success | %s/%s tf=%s | error=%s",
            token_contract[:12], token_chain, timeframe, e
        )


def is_entry_blocked(
    sb_client,
    token_contract: str,
    token_chain: str,
    timeframe: str,
    entry_state: str,
    book_id: str = "onchain_crypto"
) -> bool:
    """
    Check if entry is blocked.
    Called ONCE before allowing S1/S2 entry.
    
    Args:
        entry_state: "S1" or "S2"
    
    Returns:
        True if entry should be blocked
    """
    try:
        result = sb_client.table("token_timeframe_blocks").select(
            "blocked_s1, blocked_s2"
        ).eq(
            "token_contract", token_contract
        ).eq("token_chain", token_chain).eq(
            "timeframe", timeframe
        ).eq("book_id", book_id).limit(1).execute()
        
        if not result.data:
            return False  # No blocks exist
        
        row = result.data[0]
        
        if entry_state == "S1":
            blocked = row.get("blocked_s1", False)
        elif entry_state == "S2":
            blocked = row.get("blocked_s2", False)
        else:
            blocked = False
        
        if blocked:
            logger.info(
                "EPISODE_BLOCK: Entry blocked | %s/%s tf=%s state=%s",
                token_contract[:12], token_chain, timeframe, entry_state
            )
        
        return blocked
        
    except Exception as e:
        logger.error(
            "EPISODE_BLOCK: Failed to check block | %s/%s tf=%s | error=%s",
            token_contract[:12], token_chain, timeframe, e
        )
        return False  # On error, don't block

