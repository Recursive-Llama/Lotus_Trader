#!/usr/bin/env python3
"""
Runs the override materializer once and reports override counts.

Usage:
    PYTHONPATH=src:. python scripts/materializer_dry_run.py
"""

from __future__ import annotations

import argparse
import json
import logging

from dotenv import load_dotenv

from src.intelligence.lowcap_portfolio_manager.diagnostics.tooling import (
    materializer_dry_run,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
load_dotenv()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Override materializer dry-run CLI")
    return parser.parse_args()


def main() -> None:
    _parse_args()  # kept for future expansion / symmetry
    result = materializer_dry_run()
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

