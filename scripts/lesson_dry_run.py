#!/usr/bin/env python3
"""
Runs the Lesson Builder v5 once and reports the mined lesson count.

Usage:
    PYTHONPATH=src:. python scripts/lesson_dry_run.py --module pm
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging

from dotenv import load_dotenv

from src.intelligence.lowcap_portfolio_manager.diagnostics.tooling import (
    lesson_builder_dry_run,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
load_dotenv()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lesson builder dry-run CLI")
    parser.add_argument(
        "--module",
        default="pm",
        help="Module to target (default: pm)",
    )
    return parser.parse_args()


async def _run(args: argparse.Namespace):
    return await lesson_builder_dry_run(module=args.module)


def main() -> None:
    args = _parse_args()
    result = asyncio.run(_run(args))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

