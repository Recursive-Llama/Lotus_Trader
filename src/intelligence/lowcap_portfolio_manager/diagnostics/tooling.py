"""
Shared diagnostics helpers used by CLI scripts and flow harnesses.

These helpers intentionally operate on the live Supabase database so we can
verify each learning component independently of the full PM loop.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

from supabase import Client, create_client

from src.intelligence.lowcap_portfolio_manager.jobs.lesson_builder_v5 import (
    mine_lessons,
)
from src.intelligence.lowcap_portfolio_manager.jobs.override_materializer import (
    run_override_materializer,
)
from src.intelligence.lowcap_portfolio_manager.jobs.pattern_scope_aggregator import (
    process_position_closed_strand,
)

try:  # Best-effort .env loading for CLI invocations
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is optional in tests
    pass

logger = logging.getLogger(__name__)


class DiagnosticsError(RuntimeError):
    """Raised when a diagnostics helper cannot complete its task."""


def _build_supabase_client(sb_client: Optional[Client] = None) -> Client:
    if sb_client is not None:
        return sb_client

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not supabase_key:
        raise DiagnosticsError(
            "Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY env vars"
        )

    return create_client(supabase_url, supabase_key)


async def replay_position_closed_strand(
    strand_id: Optional[str] = None,
    *,
    sb_client: Optional[Client] = None,
    limit: int = 1,
    skip_existing: bool = True,
) -> Dict[str, Any]:
    """
    Replays a position_closed strand through the aggregator logic.

    Args:
        strand_id: optional UUID to target a specific strand. If omitted, the
            latest strand is replayed.
        sb_client: optional Supabase client for reuse.
        limit: number of recent strands to scan when strand_id is not provided.
        skip_existing: when True, strands whose trade_id already exists in
            pattern_trade_events are skipped to avoid duplicate rows.
    """

    sb = _build_supabase_client(sb_client)

    strand_query = (
        sb.table("ad_strands")
        .select("*")
        .eq("kind", "position_closed")
        .eq("module", "pm")
    )

    if strand_id:
        strand_query = strand_query.eq("id", strand_id).limit(1)
    else:
        strand_query = strand_query.order("created_at", desc=True).limit(limit)

    strands = strand_query.execute().data or []
    if not strands:
        raise DiagnosticsError(
            "No position_closed strands found for the provided parameters"
        )

    summary = []
    total_rows_written = 0
    processed_ids = []

    for strand in strands:
        strand_uuid = strand.get("id")
        trade_id = strand.get("content", {}).get("trade_id")
        processed_ids.append(strand_uuid)

        if skip_existing and trade_id:
            exists = (
                sb.table("pattern_trade_events")
                .select("id")
                .eq("trade_id", trade_id)
                .limit(1)
                .execute()
            )
            if exists.data:
                summary.append(
                    {
                        "strand_id": strand_uuid,
                        "trade_id": trade_id,
                        "status": "skipped_existing",
                        "rows_written": 0,
                    }
                )
                continue

        rows_written = await process_position_closed_strand(sb, strand)
        total_rows_written += rows_written
        summary.append(
            {
                "strand_id": strand_uuid,
                "trade_id": trade_id,
                "status": (
                    "processed" if rows_written else "processed_no_actions"
                ),
                "rows_written": rows_written,
            }
        )

    return {
        "processed": len(strands),
        "strand_ids": processed_ids,
        "total_rows_written": total_rows_written,
        "summary": summary,
    }


async def lesson_builder_dry_run(
    module: str = "pm",
    *,
    sb_client: Optional[Client] = None,
) -> Dict[str, Any]:
    """Runs the lesson builder once and reports mined lesson counts."""

    sb = _build_supabase_client(sb_client)

    lessons_mined = await mine_lessons(sb, module)
    return {
        "module": module,
        "lessons_mined": lessons_mined,
        "timestamp": datetime.utcnow().isoformat(),
    }


def materializer_dry_run(
    *,
    sb_client: Optional[Client] = None,
) -> Dict[str, Any]:
    """Runs the override materializer once and returns its counts."""

    sb = _build_supabase_client(sb_client)
    return run_override_materializer(sb)


async def run_all_diagnostics(
    *,
    strand_id: Optional[str] = None,
    module: str = "pm",
    skip_existing: bool = True,
) -> Dict[str, Any]:
    """
    Convenience helper that runs all diagnostics sequentially.

    Useful for the diagnostics harness where we want to assert the entire tool
    belt still works.
    """

    sb = _build_supabase_client()

    strand_result = await replay_position_closed_strand(
        strand_id,
        sb_client=sb,
        skip_existing=skip_existing,
    )
    lesson_result = await lesson_builder_dry_run(module, sb_client=sb)
    materializer_result = materializer_dry_run(sb_client=sb)

    return {
        "strand_replay": strand_result,
        "lesson_builder": lesson_result,
        "materializer": materializer_result,
    }

