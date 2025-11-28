#!/usr/bin/env python3
"""
Replays a position_closed strand through the pattern scope aggregator.

Usage:
    PYTHONPATH=src:. python scripts/strand_replay.py --strand-id <uuid>
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from typing import Any, Dict, Optional

from dotenv import load_dotenv

from src.intelligence.lowcap_portfolio_manager.diagnostics.tooling import (
    replay_position_closed_strand,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
load_dotenv()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Strand replay diagnostic CLI")
    parser.add_argument(
        "--strand-id",
        help="Specific position_closed strand UUID to replay",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1,
        help="Number of recent strands to scan when strand-id is not provided",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Process the strand even if trade_id already exists in pattern_trade_events",
    )
    return parser.parse_args()


async def _run(args: argparse.Namespace) -> Dict[str, Any]:
    return await replay_position_closed_strand(
        args.strand_id,
        limit=args.limit,
        skip_existing=not args.force,
    )


def main() -> None:
    args = _parse_args()
    result = asyncio.run(_run(args))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

