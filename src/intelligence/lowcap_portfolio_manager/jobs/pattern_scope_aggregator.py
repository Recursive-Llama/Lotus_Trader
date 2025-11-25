"""
Pattern Scope Stats Aggregator Job (V5 Simplified)

Aggregates trade events into pattern_trade_events table.
Reads from position_closed strands (which have final R/R) and writes one raw event row per action.
The combinatorial learning logic has been moved to the Lesson Builder (Mining).

Runs periodically to log new trade outcomes.
"""

import logging
import os
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone

from supabase import create_client, Client

from src.intelligence.lowcap_portfolio_manager.pm.pattern_keys_v5 import (
    generate_canonical_pattern_key,
    extract_scope_from_context
)

logger = logging.getLogger(__name__)

# Scope dimension order (reference only, we store full JSONB)
SCOPE_DIMS = [
    "curator", "chain", "mcap_bucket", "vol_bucket", "age_bucket", "intent",
    "mcap_vol_ratio_bucket", "market_family", "timeframe",
    "A_mode", "E_mode", "macro_phase", "meso_phase", "micro_phase",
    "bucket_leader", "bucket_rank_position"
]

ENTRY_SCOPE_KEYS = [
    "curator", "chain", "mcap_bucket", "vol_bucket", "age_bucket", "intent",
    "mcap_vol_ratio_bucket", "market_family", "timeframe", "A_mode", "E_mode",
    "macro_phase", "meso_phase", "micro_phase", "bucket_leader", "bucket_rank_position"
]


def _merge_entry_scope(scope: Dict[str, Any], entry_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge entry-context dimensions into the unified scope dict."""
    merged = dict(scope)
    entry = entry_context or {}
    
    def set_if_value(key: str, value: Any):
        if value is None:
            return
        if isinstance(value, str) and value.strip() == "":
            return
        merged[key] = value
    
    set_if_value("curator", entry.get("curator") or entry.get("curator_id"))
    set_if_value("chain", entry.get("chain") or entry.get("token_chain"))
    
    for key in ENTRY_SCOPE_KEYS[2:]:
        set_if_value(key, entry.get(key))
    
    bucket_value = (
        entry.get("mcap_bucket")
        or entry.get("bucket")
        or merged.get("mcap_bucket")
        or merged.get("bucket")
    )
    if bucket_value:
        merged["mcap_bucket"] = bucket_value
        merged["bucket"] = bucket_value
    
    if "intent" not in merged:
        merged["intent"] = entry.get("intent", "unknown")
    
    return merged


async def process_position_closed_strand(
    sb_client: Client,
    strand: Dict[str, Any]
) -> int:
    """
    Process a position_closed strand to log pattern trade events.
    Writes 1 row per action to pattern_trade_events.
    """
    try:
        content = strand.get('content', {})
        trade_id = content.get('trade_id')
        entry_context = content.get('entry_context') or {}
        trade_summary = content.get('trade_summary')
        
        if not trade_summary or not isinstance(trade_summary, dict):
            return 0
            
        rr = float(trade_summary.get('rr', 0.0))
        pnl_usd = float(trade_summary.get('pnl_usd', 0.0))
        
        # Find linked actions
        action_entries: List[Dict[str, Any]] = []
        if trade_id:
            try:
                action_rows = (
                    sb_client.table('ad_strands')
                    .select('content')
                    .eq('kind', 'pm_action')
                    .eq('trade_id', trade_id)
                    .order('created_at')
                    .execute()
                ).data or []
                for row in action_rows:
                    entry = row.get('content') or {}
                    action_entries.append(entry)
            except Exception as e:
                logger.warning(f"Error loading pm_action strands for trade {trade_id}: {e}")
        
        if not action_entries:
            # Fallback for legacy/test data without trade_id linkage if needed
            # But we strictly prefer trade_id linkage for V4.
            return 0
        
        rows_written = 0
        now_iso = datetime.now(timezone.utc).isoformat()
        
        for action_entry in action_entries:
            if not isinstance(action_entry, dict):
                continue
            
            pattern_key = action_entry.get('pattern_key')
            action_category = action_entry.get('action_category')
            scope = action_entry.get('scope', {})
            
            if not pattern_key or not action_category:
                continue
            
            # Merge scope to ensure full context
            scope = _merge_entry_scope(scope, entry_context)
            
            # Write Fact Row
            try:
                sb_client.table('pattern_trade_events').insert({
                    'pattern_key': pattern_key,
                    'action_category': action_category,
                    'scope': scope,
                    'rr': rr,
                    'pnl_usd': pnl_usd,
                    'trade_id': trade_id,
                    'timestamp': now_iso, # Or strand.created_at? prefer now for ingestion time
                    'created_at': now_iso
                }).execute()
                rows_written += 1
            except Exception as e:
                # Duplicate trade_id+action might fail if we had uniqueness constraints, 
                # but events table usually allows multiples unless we id-dedupe.
                # Actually, we should probably dedupe by checking if event exists for this trade_id+action
                # For simplicity in V1 miner, we just insert.
                logger.warning(f"Error writing event row: {e}")

        return rows_written
        
    except Exception as e:
        logger.error(f"Error processing position_closed strand: {e}")
        return 0


async def run_aggregator(
    sb_client: Optional[Client] = None,
    limit: int = 100,
    since: Optional[datetime] = None
) -> Dict[str, int]:
    """
    Run pattern event logger on recent position_closed strands.
    """
    if sb_client is None:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not supabase_url or not supabase_key:
            logger.error("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
            return {'processed': 0, 'rows_updated': 0}
        sb_client = create_client(supabase_url, supabase_key)
    
    try:
        # Query position_closed strands
        query = (
            sb_client.table('ad_strands')
            .select('*')
            .eq('kind', 'position_closed')
            .eq('module', 'pm')
            .order('created_at', desc=True)
            .limit(limit)
        )
        
        if since:
            query = query.gte('created_at', since.isoformat())
        
        result = query.execute()
        strands = result.data or []
        
        total_written = 0
        for strand in strands:
            # Check if already processed? 
            # Ideally we have a cursor. For now, we rely on idempotent inserts or short lookback.
            # Since pattern_trade_events doesn't have a unique constraint on trade_id yet (it's an append log),
            # we risk duplicates if we re-run.
            # PRO TIP: Check if trade_id exists in events table first.
            trade_id = strand.get('content', {}).get('trade_id')
            if trade_id:
                exists = sb_client.table('pattern_trade_events').select('id').eq('trade_id', trade_id).limit(1).execute()
                if exists.data:
                    continue

            written = await process_position_closed_strand(sb_client, strand)
            total_written += written
        
        logger.info(f"Processed {len(strands)} trade strands, wrote {total_written} event rows")
        return {
            'processed': len(strands),
            'rows_updated': total_written
        }
        
    except Exception as e:
        logger.error(f"Error running aggregator: {e}")
        return {'processed': 0, 'rows_updated': 0}


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    result = asyncio.run(run_aggregator())
    print(f"Aggregator result: {result}")
