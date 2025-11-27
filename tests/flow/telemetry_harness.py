"""
Telemetry Harness

Loads recent `pm_action` strands from Supabase and asserts that telemetry
fields required by the test plan are present:
  - content.pm_strength_applied
  - content.exposure_skew_applied
  - content.pm_final_multiplier
  - content.learning_multipliers with keys (pm_strength, exposure_skew, combined_multiplier)

Usage:
    PYTHONPATH=src:. python tests/flow/telemetry_harness.py --limit 20
"""

import argparse
import logging
import os
from typing import Any, Dict, List, Tuple

from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("TelemetryHarness")

REQUIRED_FIELDS = [
    "pm_strength_applied",
    "exposure_skew_applied",
    "pm_final_multiplier",
]

REQUIRED_MULT_KEYS = [
    "pm_strength",
    "exposure_skew",
    "combined_multiplier",
]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate pm_action telemetry strands")
    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Number of recent pm_action strands to inspect (default 25)",
    )
    parser.add_argument(
        "--timeframe",
        help="Optional timeframe filter (e.g., 1h)",
    )
    parser.add_argument(
        "--decision",
        help="Optional decision_type filter (entry/add/trim/etc.)",
    )
    parser.add_argument(
        "--pattern-key",
        help="Optional pattern_key filter (exact match)",
    )
    parser.add_argument(
        "--token-contract",
        help="Optional token_contract filter (exact match)",
    )
    return parser


def _connect_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
    return create_client(url, key)


def _fetch_strands(
    sb: Client,
    *,
    limit: int,
    timeframe: str | None,
) -> List[Dict[str, Any]]:
    query = (
        sb.table("ad_strands")
        .select("*")
        .eq("module", "pm")
        .eq("kind", "pm_action")
        .order("created_at", desc=True)
        .limit(limit)
    )
    if timeframe:
        query = query.eq("timeframe", timeframe)
    data = query.execute().data or []
    return data


def _filter_strands(
    rows: List[Dict[str, Any]],
    *,
    decision: str | None,
    pattern_key: str | None,
    token_contract: str | None,
) -> List[Dict[str, Any]]:
    if not (decision or pattern_key or token_contract):
        return rows
    filtered: List[Dict[str, Any]] = []
    for row in rows:
        content = row.get("content") or {}
        if decision:
            if (content.get("decision_type") or "").lower() != decision.lower():
                continue
        if pattern_key:
            if content.get("pattern_key") != pattern_key:
                continue
        if token_contract:
            if content.get("token_contract") != token_contract:
                continue
        filtered.append(row)
    return filtered


def _validate_row(row: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    content = row.get("content") or {}

    for field in REQUIRED_FIELDS:
        if field not in content:
            errors.append(f"missing field '{field}'")
        else:
            val = content[field]
            if val is None:
                errors.append(f"field '{field}' is None")

    multipliers = content.get("learning_multipliers")
    if not isinstance(multipliers, dict) or not multipliers:
        errors.append("missing or empty learning_multipliers")
    else:
        for key in REQUIRED_MULT_KEYS:
            if key not in multipliers:
                errors.append(f"learning_multipliers missing '{key}'")

    return (len(errors) == 0, errors)


def main() -> None:
    args = _build_parser().parse_args()
    sb = _connect_client()

    print("\n=================================================================")
    print("📡 TELEMETRY HARNESS – pm_action strand validation")
    print(f"  Limit      : {args.limit}")
    if args.timeframe:
        print(f"  Timeframe  : {args.timeframe}")
    if args.decision:
        print(f"  Decision   : {args.decision}")
    if args.pattern_key:
        print(f"  Pattern key: {args.pattern_key}")
    print("=================================================================\n")

    rows = _fetch_strands(sb, limit=args.limit, timeframe=args.timeframe)
    rows = _filter_strands(
        rows,
        decision=args.decision,
        pattern_key=args.pattern_key,
        token_contract=args.token_contract,
    )

    if not rows:
        print("No matching strands found. Exiting.")
        return

    failures = 0
    for idx, row in enumerate(rows, start=1):
        ok, errors = _validate_row(row)
        content = row.get("content") or {}
        desc = f"[{idx}/{len(rows)}] {row.get('id')} decision={content.get('decision_type')} size={content.get('size_frac')}"
        if ok:
            logger.info("✅ %s", desc)
        else:
            failures += 1
            logger.error("❌ %s", desc)
            for msg in errors:
                logger.error("    - %s", msg)

    print("\n=================================================================")
    if failures:
        print(f"❌ HARNESS FAILED: {failures} strands missing telemetry fields.")
    else:
        print("🎉 HARNESS PASSED: All inspected strands carry required telemetry.")
    print("=================================================================\n")

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

