#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import sys

# Ensure project root is on path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.intelligence.lowcap_portfolio_manager.jobs.ta_tracker import TATracker
from src.intelligence.lowcap_portfolio_manager.spiral.persist import SpiralPersist


def main() -> None:
    ap = argparse.ArgumentParser(description="Dump TA features for a few positions")
    ap.add_argument("--limit", type=int, default=3)
    ap.add_argument("--contract", type=str, default=None)
    ap.add_argument("--chain", type=str, default=None)
    ap.add_argument("--write", action="store_true", help="Run tracker write before dump")
    args = ap.parse_args()

    if args.write:
        TATracker().run()

    sp = SpiralPersist()
    q = sp.sb.table("lowcap_positions").select("id,token_contract,token_chain,features").eq("status", "active")
    if args.contract:
        q = q.eq("token_contract", args.contract)
    if args.chain:
        q = q.eq("chain", args.chain)
    rows = q.limit(max(1, args.limit)).execute().data or []
    out = []
    for r in rows:
        features = r.get("features") or {}
        out.append({
            "id": r.get("id"),
            "contract": r.get("token_contract"),
            "chain": r.get("token_chain"),
            "ta": (features.get("ta") if isinstance(features, dict) else None) or {}
        })
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
