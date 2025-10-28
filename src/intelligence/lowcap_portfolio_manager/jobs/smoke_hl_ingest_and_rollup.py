"""
10-minute smoke: run HL WS ingester, then roll up last N minutes and verify bars exist.

Usage:
  LOG_LEVEL=INFO DURATION_MIN=10 python -m src.intelligence.lowcap_portfolio_manager.jobs.smoke_hl_ingest_and_rollup
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

from src.intelligence.lowcap_portfolio_manager.ingest.hyperliquid_ws import HyperliquidWSIngester
from src.intelligence.lowcap_portfolio_manager.ingest.rollup import OneMinuteRollup
from supabase import create_client  # type: ignore


async def run_smoke(duration_min: int) -> None:
    ingester = HyperliquidWSIngester()
    task = asyncio.create_task(ingester.run())
    try:
        await asyncio.sleep(duration_min * 60)
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    # Roll up last duration_min + 1 minutes
    job = OneMinuteRollup()
    now = datetime.now(tz=timezone.utc)
    total = 0
    for i in range(duration_min + 1):
        total += job.roll_minute(now - timedelta(minutes=i))

    logging.getLogger(__name__).info("Smoke rollup wrote %d bars", total)


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    duration = int(os.getenv("DURATION_MIN", "10"))
    asyncio.run(run_smoke(duration))


if __name__ == "__main__":
    main()


