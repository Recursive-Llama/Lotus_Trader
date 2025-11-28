"""
Diagnostics harness ensures the standalone tooling in §4.1 stays healthy.

It runs:
1. Strand replay CLI logic (position_closed -> pattern_trade_events)
2. Lesson builder dry run (pm module)
3. Override materializer dry run

Each step queries the real Supabase database, so make sure SUPABASE_URL and
SUPABASE_SERVICE_ROLE_KEY are configured before running.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from supabase import Client, create_client

from src.intelligence.lowcap_portfolio_manager.diagnostics.tooling import (
    DiagnosticsError,
    lesson_builder_dry_run,
    materializer_dry_run,
    replay_position_closed_strand,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
load_dotenv()


class DiagnosticsHarness:
    def __init__(self, strand_id: str | None, module: str, skip_existing: bool):
        self.strand_id = strand_id
        self.module = module
        self.skip_existing = skip_existing
        self.sb_client = self._build_client()
        self.failures: List[str] = []
        self.results: Dict[str, Any] = {}

    @staticmethod
    def _build_client() -> Client:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not supabase_url or not supabase_key:
            raise DiagnosticsError(
                "Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY env vars"
            )
        return create_client(supabase_url, supabase_key)

    async def run(self) -> Dict[str, Any]:
        await self._run_strand_replay()
        await self._run_lesson_builder()
        self._run_materializer()

        if self.failures:
            raise DiagnosticsError("; ".join(self.failures))

        return self.results

    async def _run_strand_replay(self) -> None:
        try:
            res = await replay_position_closed_strand(
                self.strand_id,
                sb_client=self.sb_client,
                skip_existing=self.skip_existing,
            )
            self.results["strand_replay"] = res

            statuses = {item["status"] for item in res.get("summary", [])}
            actionable = {"processed", "processed_no_actions"}
            if not statuses:
                self.failures.append("Strand replay returned no strands")
            elif statuses.isdisjoint(actionable):
                logging.warning(
                    "Strand replay skipped %s strand(s); trade events already exist.",
                    res.get("processed"),
                )
        except Exception as exc:  # pragma: no cover - integration
            self.failures.append(f"Strand replay failed: {exc}")

    async def _run_lesson_builder(self) -> None:
        try:
            res = await lesson_builder_dry_run(
                module=self.module,
                sb_client=self.sb_client,
            )
            self.results["lesson_builder"] = res

            if res.get("lessons_mined", 0) < 0:
                self.failures.append("Lesson builder returned negative count")
        except Exception as exc:  # pragma: no cover - integration
            self.failures.append(f"Lesson builder failed: {exc}")

    def _run_materializer(self) -> None:
        try:
            res = materializer_dry_run(sb_client=self.sb_client)
            self.results["materializer"] = res

            if (
                res.get("strength_overrides", 0) < 0
                or res.get("tuning_overrides", 0) < 0
            ):
                self.failures.append("Materializer returned negative counts")
        except Exception as exc:  # pragma: no cover - integration
            self.failures.append(f"Materializer failed: {exc}")


async def _run_harness(args: argparse.Namespace) -> Dict[str, Any]:
    harness = DiagnosticsHarness(
        strand_id=args.strand_id,
        module=args.module,
        skip_existing=not args.force,
    )
    return await harness.run()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnostics flow harness")
    parser.add_argument(
        "--strand-id",
        help="Optional strand UUID to replay (defaults to most recent strand)",
    )
    parser.add_argument(
        "--module",
        default="pm",
        help="Lesson builder module (default: pm)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Process strand even if its trade_id already has trade events",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print full JSON results instead of short summary",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    try:
        result = asyncio.run(_run_harness(args))
    except DiagnosticsError as exc:
        logging.error("Diagnostics harness failed: %s", exc)
        raise SystemExit(1) from exc

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        strand = result["strand_replay"]
        lesson = result["lesson_builder"]
        materializer = result["materializer"]
        print(
            "Diagnostics PASS | "
            f"strand rows={strand.get('total_rows_written')} "
            f"lessons={lesson.get('lessons_mined')} "
            f"overrides={materializer}"
        )


if __name__ == "__main__":
    main()

