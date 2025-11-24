"""
Majors Feed Harness
====================

Flow-style harness that exercises the Hyperliquid > rollup > TA/phase stack:
1. (Optional) Spins up the Hyperliquid WS ingester for a short burst to ingest real ticks.
2. Rolls ticks into 1m OHLC bars (`OneMinuteRollup`) and higher timeframes (`GenericOHLCRollup`).
3. Runs the tracker job (`jobs.tracker`) to refresh macro/meso/micro regime + A/E context.
4. Prints verification summaries (recent ticks, fresh OHLC rows, updated phase_state entries).

Usage:
    PYTHONPATH=src python tests/flow/majors_feed_harness.py \
        --ingest-seconds 15 \
        --run-ws \
        --timeframes 5m 15m 1h 4h

Defaults:
- Skips the live WS unless `--run-ws` is passed (useful when data already exists).
- Always runs rollups + tracker so we can re-test derived metrics even with historical ticks.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from dotenv import load_dotenv

from postgrest import exceptions as postgrest_exceptions
from utils.supabase_manager import SupabaseManager
from intelligence.lowcap_portfolio_manager.ingest.hyperliquid_ws import HyperliquidWSIngester
from intelligence.lowcap_portfolio_manager.ingest.rollup import OneMinuteRollup
from intelligence.lowcap_portfolio_manager.ingest.rollup_ohlc import GenericOHLCRollup, DataSource, Timeframe
from intelligence.lowcap_portfolio_manager.jobs.tracker import main as tracker_main


LOGGER = logging.getLogger("majors_feed_harness")


TIMEFRAME_MAP = {
    "5m": Timeframe.M5,
    "15m": Timeframe.M15,
    "1h": Timeframe.H1,
    "4h": Timeframe.H4,
    "1d": Timeframe.D1,
}


class MajorsFeedHarness:
    def __init__(
        self,
        ingest_seconds: int,
        run_ws: bool,
        timeframes: List[str],
        tracker_enabled: bool,
    ) -> None:
        load_dotenv()
        self.ingest_seconds = ingest_seconds
        self.run_ws = run_ws
        self.timeframes = [TIMEFRAME_MAP[tf] for tf in timeframes]
        self.tracker_enabled = tracker_enabled

        self.supabase_manager = SupabaseManager()
        self.run_start = datetime.now(timezone.utc)

    async def _ingest_ticks_once(self) -> None:
        LOGGER.info("Starting Hyperliquid WS ingester for %d seconds", self.ingest_seconds)
        ingester = HyperliquidWSIngester()
        task = asyncio.create_task(ingester.run())
        try:
            await asyncio.sleep(self.ingest_seconds)
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                LOGGER.info("WS ingester cancelled (expected)")
            await ingester.flush_on_shutdown()
        LOGGER.info("Hyperliquid WS ingester burst completed")

    def _run_rollups(self) -> Dict[str, int]:
        LOGGER.info("Running OneMinuteRollup → majors_price_data_ohlc (1m)")
        rollup_1m = OneMinuteRollup()
        written_1m = self._roll_minute_with_fallback(rollup_1m)
        LOGGER.info("1m rollup wrote %d bars", written_1m)

        generic_rollup = GenericOHLCRollup()
        now = datetime.now(timezone.utc)
        written_by_tf: Dict[str, int] = {"1m": written_1m}
        for tf in self.timeframes:
            LOGGER.info("Rolling up majors data to %s", tf.value)
            written = generic_rollup.rollup_timeframe(DataSource.MAJORS, tf, when=now)
            written_by_tf[tf.value] = written
            LOGGER.info("%s rollup wrote %d bars", tf.value, written)
        return written_by_tf

    def _run_tracker(self) -> None:
        if not self.tracker_enabled:
            LOGGER.info("Tracker run skipped (--no-tracker)")
            return
        LOGGER.info("Running tracker job (macro/meso/micro + A/E)")
        tracker_main()
        LOGGER.info("Tracker job completed")

    def _fetch_recent_ticks(self) -> List[Dict]:
        five_min_ago = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        resp = (
            self.supabase_manager.client.table("majors_trades_ticks")
            .select("token,ts,price,size")
            .gte("ts", five_min_ago)
            .order("ts", desc=True)
            .limit(5)
            .execute()
        )
        return resp.data or []

    def _roll_minute_with_fallback(self, job: OneMinuteRollup) -> int:
        try:
            return job.roll_minute()
        except postgrest_exceptions.APIError as exc:
            if "exec_sql" not in (exc.message or ""):
                raise
            LOGGER.warning("exec_sql RPC missing; using local 1m rollup fallback")
            return self._roll_minute_manual(job)

    def _roll_minute_manual(self, job: OneMinuteRollup) -> int:
        when = datetime.now(timezone.utc) - timedelta(seconds=5)
        when = job._to_utc(when)
        start, end = job._minute_bounds(when)
        token_resp = (
            job.sb.table("majors_trades_ticks")
            .select("token")
            .gte("ts", start.isoformat())
            .lt("ts", end.isoformat())
            .execute()
        )
        tokens = sorted({row["token"] for row in (token_resp.data or []) if row.get("token")})
        if not tokens:
            return 0
        bars = []
        for token in tokens:
            tick_resp = (
                job.sb.table("majors_trades_ticks")
                .select("token,ts,price,size")
                .gte("ts", start.isoformat())
                .lt("ts", end.isoformat())
                .eq("token", token)
                .execute()
            )
            ticks = tick_resp.data or []
            bar = job._compute_bar(token, ticks)
            if bar:
                bars.append(bar)
        if not bars:
            return 0
        ohlc_rows = []
        for b in bars:
            ohlc_rows.append(
                {
                    "token_contract": b.token,
                    "chain": "hyperliquid",
                    "timeframe": "1m",
                    "timestamp": b.ts.isoformat(),
                    "open_native": 0.0,
                    "high_native": 0.0,
                    "low_native": 0.0,
                    "close_native": 0.0,
                    "open_usd": b.open,
                    "high_usd": b.high,
                    "low_usd": b.low,
                    "close_usd": b.close,
                    "volume": b.volume,
                    "source": "hyperliquid",
                }
            )
        job.sb.table("majors_price_data_ohlc").upsert(
            ohlc_rows, on_conflict="token_contract,chain,timeframe,timestamp"
        ).execute()
        return len(bars)

    def _fetch_recent_ohlc(self) -> List[Dict]:
        five_min_ago = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        resp = (
            self.supabase_manager.client.table("majors_price_data_ohlc")
            .select("token_contract,timeframe,timestamp,close_usd,volume")
            .gte("timestamp", five_min_ago)
            .order("timestamp", desc=True)
            .limit(5)
            .execute()
        )
        return resp.data or []

    def _fetch_phase_state(self) -> List[Dict]:
        resp = (
            self.supabase_manager.client.table("phase_state")
            .select("id,macro_phase,meso_phase,micro_phase,updated_at")
            .order("updated_at", desc=True)
            .limit(5)
            .execute()
        )
        return resp.data or []

    async def run(self) -> None:
        tick_window_start = datetime.now(timezone.utc)
        if self.run_ws:
            await self._ingest_ticks_once()
        else:
            LOGGER.info("Skipping HL WS ingest (use --run-ws to enable)")
        self._verify_ticks(tick_window_start)

        written = self._run_rollups()
        minute_target = (datetime.now(timezone.utc) - timedelta(seconds=5)).replace(second=0, microsecond=0)
        self._verify_ohlc(minute_target)

        self._run_tracker()

        ticks = self._fetch_recent_ticks()
        ohlc = self._fetch_recent_ohlc()
        phases = self._fetch_phase_state()

        print("\n=== Majors Feed Harness Summary ===")
        print(f"Rollup counts: {written}")
        print(f"Recent ticks ({len(ticks)}):")
        for row in ticks:
            print(f"  {row['token']} @ {row['ts']} price={row['price']} size={row.get('size')}")
        print(f"Recent OHLC rows ({len(ohlc)}):")
        for row in ohlc:
            print(
                f"  {row['token_contract']} tf={row['timeframe']} ts={row['timestamp']} "
                f"close={row['close_usd']:.4f} vol={row['volume']:.2f}"
            )
        print(f"Phase_state snapshots ({len(phases)}):")
        for row in phases:
            print(
                f"  id={row['id']} macro={row.get('macro_phase')} meso={row.get('meso_phase')} "
                f"micro={row.get('micro_phase')} updated={row['updated_at']}"
            )

    def _verify_ticks(self, window_start: datetime) -> None:
        query = (
            self.supabase_manager.client.table("majors_trades_ticks")
            .select("token", count="exact")
            .gte("ts", window_start.isoformat())
        )
        resp = query.execute()
        count = resp.count if resp.count is not None else len(resp.data or [])
        if count > 0:
            print(f"[PASS] Hyperliquid ingest wrote {count} ticks since {window_start.isoformat()}")
        else:
            print(f"[FAIL] No ticks ingested since {window_start.isoformat()} (WS or schema issue)")

    def _verify_ohlc(self, minute_ts: datetime) -> None:
        query = (
            self.supabase_manager.client.table("majors_price_data_ohlc")
            .select("token_contract,timeframe", count="exact")
            .eq("timeframe", "1m")
            .eq("timestamp", minute_ts.isoformat())
        )
        resp = query.execute()
        count = resp.count if resp.count is not None else len(resp.data or [])
        if count > 0:
            print(f"[PASS] 1m rollup inserted {count} bars at {minute_ts.isoformat()}")
        else:
            print(f"[FAIL] 1m rollup produced no bars for {minute_ts.isoformat()} – check rollup logic/schema")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Majors feed + A/E harness")
    parser.add_argument("--run-ws", action="store_true", help="Start the Hyperliquid WS ingester for a short burst")
    parser.add_argument("--ingest-seconds", type=int, default=15, help="Seconds to keep the WS ingester alive")
    parser.add_argument(
        "--timeframes",
        nargs="+",
        default=["5m", "15m", "1h", "4h"],
        choices=list(TIMEFRAME_MAP.keys()),
        help="Higher timeframes to roll up after 1m conversion",
    )
    parser.add_argument("--no-tracker", action="store_true", help="Skip tracker run (macro/meso/micro update)")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    return parser.parse_args()


async def async_main() -> None:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    tracker_enabled = not args.no_tracker
    harness = MajorsFeedHarness(
        ingest_seconds=args.ingest_seconds,
        run_ws=args.run_ws,
        timeframes=args.timeframes,
        tracker_enabled=tracker_enabled,
    )
    await harness.run()


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()

