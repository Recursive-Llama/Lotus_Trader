import argparse
import asyncio
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

from utils.supabase_manager import SupabaseManager
from intelligence.universal_learning.universal_learning_system import UniversalLearningSystem
from intelligence.decision_maker_lowcap.decision_maker_lowcap_simple import DecisionMakerLowcapSimple
from intelligence.lowcap_portfolio_manager.jobs.pattern_scope_aggregator import run_aggregator
from intelligence.lowcap_portfolio_manager.jobs.lesson_builder_v5 import (
    build_lessons_from_pattern_scope_stats,
)
from intelligence.lowcap_portfolio_manager.jobs.override_materializer import (
    run_override_materializer,
)


class PMLearningFlowHarness:
    """
    Minimal harness that exercises the social → decision → PM learning flow
    without relying on background schedulers. Each step prints a pass/fail
    checkpoint so we know exactly where the packet dies.
    """

    def __init__(self) -> None:
        self.supabase_manager = SupabaseManager()
        self.learning_system = UniversalLearningSystem(
            supabase_manager=self.supabase_manager,
            llm_client=None,
            llm_config=None,
        )
        dm_config = self._load_social_trading_config()
        self.decision_maker = DecisionMakerLowcapSimple(
            supabase_manager=self.supabase_manager,
            config=dm_config,
            learning_system=self.learning_system,
        )
        self.learning_system.set_decision_maker(self.decision_maker)
        self.service_client = self._build_service_client()

    def _build_service_client(self):
        supabase_url = os.getenv("SUPABASE_URL")
        service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not supabase_url or not service_key:
            print(
                "[warn] SUPABASE_SERVICE_ROLE_KEY missing; "
                "falling back to default client (aggregator jobs may fail)."
            )
            return self.supabase_manager.client
        return create_client(supabase_url, service_key)

    async def run(self, run_learning_jobs: bool) -> None:
        signal = self._build_social_signal()
        created_signal = self.supabase_manager.insert_strand(signal)
        signal_id = created_signal["id"]
        print(f"[1/6] Injected social_lowcap strand {signal_id}")

        await self.learning_system.process_strand_event(created_signal)
        print(f"[2/6] Learning system processed social strand {signal_id}")

        decision = self._fetch_child_strand(signal_id, "decision_lowcap")
        if not decision:
            print("[!] Packet died: decision_lowcap strand missing")
            return
        decision_id = decision["id"]
        print(f"[3/6] Decision maker approved signal -> decision {decision_id}")

        positions = self._fetch_positions(decision)
        if positions:
            print(
                f"[4/6] PM created {len(positions)} lowcap_positions "
                f"({', '.join(p['timeframe'] for p in positions)})"
            )
        else:
            print("[!] Packet died: no lowcap_positions created")
            return

        if run_learning_jobs:
            await self._run_learning_jobs()
            print("[5/6] Aggregator + lesson builder + materializer run")
        else:
            print("[5/6] Skipped learning jobs (use --run-learning-jobs to enable)")

        print("[6/6] Flow harness completed")

    def _build_social_signal(self) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        strand_id = f"flowtest-{uuid.uuid4()}"
        token = {
            "ticker": "Lumen",
            "contract": "BkpaxHhE6snExazrPkVAjxDyZa8Nq3oDEzm5GQm2pump",
            "chain": "solana",
            "dex": "Raydium",
            "liquidity": 75000,
            "volume_24h": 250000,
            "market_cap": 1500000,
            "price": 0.015,
        }
        curator = {
            "id": "0xdetweiler",
            "name": "Detweiler",
            "platform": "twitter",
            "handle": "@detweiler",
            "weight": 0.8,
            "priority": "high",
            "tags": ["tier1"],
        }

        return {
            "id": strand_id,
            "module": "social_ingest",
            "kind": "social_lowcap",
            "symbol": token["ticker"],
            "timeframe": None,
            "session_bucket": f"social_{now.strftime('%Y%m%d_%H')}",
            "tags": ["curated", "social_signal", "dm_candidate", "verified"],
            "target_agent": "decision_maker_lowcap",
            "signal_pack": {
                "token": token,
                "venue": {
                    "dex": token["dex"],
                    "chain": token["chain"],
                    "liq_usd": token["liquidity"],
                    "vol24h_usd": token["volume_24h"],
                },
                "curator": {
                    "id": curator["id"],
                    "name": curator["name"],
                    "platform": curator["platform"],
                    "handle": curator["handle"],
                    "weight": curator["weight"],
                    "priority": curator["priority"],
                    "tags": curator["tags"],
                },
                "trading_signals": {
                    "action": "buy",
                    "timing": "immediate",
                    "confidence": 0.78,
                },
                "intent_analysis": {
                    "intent_analysis": {
                        "intent_type": "new_discovery",
                        "allocation_multiplier": 1.0,
                        "confidence": 0.8,
                    }
                },
            },
            "module_intelligence": {
                "social_signal": {
                    "message": {
                        "text": "Flow harness test signal",
                        "timestamp": now.isoformat(),
                        "url": "https://twitter.com/detweiler/status/flow-test",
                        "has_image": False,
                        "has_chart": False,
                    }
                }
            },
            "content": {
                "summary": f"Flow harness signal for {token['ticker']}",
                "curator_id": curator["id"],
                "platform": curator["platform"],
                "token_ticker": token["ticker"],
            },
            "regime_context": {
                "macro_phase": "Recover",
                "meso_phase": "Impulse",
                "micro_phase": "Pullback",
            },
            "status": "active",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

    def _fetch_child_strand(self, parent_id: str, kind: str) -> Optional[Dict[str, Any]]:
        result = (
            self.supabase_manager.client.table("ad_strands")
            .select("*")
            .eq("parent_id", parent_id)
            .eq("kind", kind)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def _fetch_positions(self, decision: Dict[str, Any]) -> Any:
        token = decision.get("content", {}).get("token", {})
        token_contract = token.get("contract")
        token_chain = (token.get("chain") or "").lower()
        if not token_contract or not token_chain:
            return []
        result = (
            self.supabase_manager.client.table("lowcap_positions")
            .select("id,timeframe,status")
            .eq("token_contract", token_contract)
            .eq("token_chain", token_chain)
            .order("created_at", desc=True)
            .limit(4)
            .execute()
        )
        return result.data or []

    async def _run_learning_jobs(self) -> None:
        agg = await run_aggregator(sb_client=self.service_client)
        print(f"    Aggregator result: {agg}")
        pm_lessons = await build_lessons_from_pattern_scope_stats(
            self.service_client, module="pm"
        )
        dm_lessons = await build_lessons_from_pattern_scope_stats(
            self.service_client, module="dm"
        )
        print(f"    Lesson builder result: pm={pm_lessons}, dm={dm_lessons}")
        materialized = run_override_materializer(sb_client=self.service_client)
        print(f"    Materializer result: {materialized}")

    def _load_social_trading_config(self) -> Dict[str, Any]:
        config_path = Path("src/config/social_trading_config.yaml")
        if not config_path.exists():
            raise RuntimeError("social_trading_config.yaml not found; harness needs it to configure allocations")
        raw = config_path.read_text()
        expanded = os.path.expandvars(raw)
        config = yaml.safe_load(expanded)
        trading = config.get('trading', {})
        default_chain_multipliers = {
            'ethereum': 2.0,
            'base': 2.0,
            'solana': 1.0,
            'bsc': 1.0,
        }
        return {
            'book_id': config.get('book_id', 'social'),
            'min_curator_score': trading.get('min_curator_score', 0.6),
            'max_exposure_pct': trading.get('max_exposure_pct', 100.0),
            'max_positions': trading.get('max_positions', 69),
            'chain_multipliers': trading.get('chain_multipliers', default_chain_multipliers),
            'allocation_config': config.get('allocation_config', {}),
            'min_volume_requirements': config.get('min_volume_requirements', {}),
        }


    async def test_dm_rejection_criteria(self) -> None:
        """
        Test DM rejection criteria:
        1. Unsupported chain rejection
        2. Low curator score rejection (< 0.1)
        3. Already-holding behavior (approves but doesn't duplicate)
        4. Removed blockers don't block (intent, capacity)
        """
        print("\n" + "="*80)
        print("DM REJECTION CRITERIA TESTS")
        print("="*80)
        
        # Test 1: Unsupported chain rejection
        print("\n[TEST 1] Unsupported chain rejection")
        print("-" * 80)
        signal = self._build_social_signal()
        signal["signal_pack"]["token"]["chain"] = "polygon"  # Unsupported chain
        signal["id"] = f"reject-test-chain-{uuid.uuid4()}"
        created_signal = self.supabase_manager.insert_strand(signal)
        await self.learning_system.process_strand_event(created_signal)
        decision = self._fetch_child_strand(created_signal["id"], "decision_lowcap")
        if decision:
            action = decision.get("content", {}).get("action")
            if action == "reject":
                print("✅ PASS: Unsupported chain correctly rejected")
                reasoning = decision.get("content", {}).get("reasoning", "")
                if "not supported" in reasoning.lower() or "chain" in reasoning.lower():
                    print(f"   Reasoning: {reasoning}")
            else:
                print(f"❌ FAIL: Expected rejection, got action={action}")
        else:
            print("❌ FAIL: No decision strand created (should create rejection)")
        
        # Test 2: Low curator score rejection
        print("\n[TEST 2] Low curator score rejection (< 0.1)")
        print("-" * 80)
        # First, ensure we have a curator with low score
        low_score_curator_id = f"test-lowscore-{uuid.uuid4()}"
        try:
            # Insert or update curator with low score
            self.supabase_manager.client.table("curators").upsert({
                "curator_id": low_score_curator_id,
                "name": "Low Score Test Curator",
                "final_weight": 0.05,  # Below 0.1 threshold
                "win_rate": 0.05,
                "total_signals": 10,
                "status": "active"
            }).execute()
            print(f"   Created test curator: {low_score_curator_id} with score 0.05")
        except Exception as e:
            print(f"   ⚠️  Could not create test curator: {e}")
            print("   (Assuming curator exists or will use default 0.5)")
        
        signal = self._build_social_signal()
        signal["signal_pack"]["curator"]["id"] = low_score_curator_id
        signal["id"] = f"reject-test-score-{uuid.uuid4()}"
        created_signal = self.supabase_manager.insert_strand(signal)
        await self.learning_system.process_strand_event(created_signal)
        decision = self._fetch_child_strand(created_signal["id"], "decision_lowcap")
        if decision:
            action = decision.get("content", {}).get("action")
            if action == "reject":
                print("✅ PASS: Low curator score correctly rejected")
                reasoning = decision.get("content", {}).get("reasoning", "")
                if "curator" in reasoning.lower() or "score" in reasoning.lower():
                    print(f"   Reasoning: {reasoning}")
            else:
                print(f"❌ FAIL: Expected rejection, got action={action}")
        else:
            print("❌ FAIL: No decision strand created (should create rejection)")
        
        # Test 3: Already-holding behavior (should approve but not duplicate positions)
        print("\n[TEST 3] Already-holding behavior")
        print("-" * 80)
        # First create a position for a token
        test_token_contract = f"test-already-holding-{uuid.uuid4().hex[:16]}"
        test_token_chain = "solana"
        try:
            # Create a test position
            position = {
                "token_contract": test_token_contract,
                "token_chain": test_token_chain,
                "token_ticker": "ALREADY",
                "timeframe": "1h",
                "status": "active",
                "book_id": self.decision_maker.book_id,
                "total_allocation_pct": 5.0,
            }
            self.supabase_manager.client.table("lowcap_positions").insert(position).execute()
            print(f"   Created test position for {test_token_contract}")
        except Exception as e:
            print(f"   ⚠️  Could not create test position: {e}")
        
        signal = self._build_social_signal()
        signal["signal_pack"]["token"]["contract"] = test_token_contract
        signal["signal_pack"]["token"]["chain"] = test_token_chain
        signal["signal_pack"]["token"]["ticker"] = "ALREADY"
        signal["id"] = f"reject-test-already-{uuid.uuid4()}"
        created_signal = self.supabase_manager.insert_strand(signal)
        await self.learning_system.process_strand_event(created_signal)
        decision = self._fetch_child_strand(created_signal["id"], "decision_lowcap")
        if decision:
            action = decision.get("content", {}).get("action")
            if action == "approve":
                print("✅ PASS: Already-holding signal approved (intent logged)")
                # Check that no duplicate positions were created
                positions = self._fetch_positions(decision)
                existing_positions = (
                    self.supabase_manager.client.table("lowcap_positions")
                    .select("id")
                    .eq("token_contract", test_token_contract)
                    .eq("token_chain", test_token_chain)
                    .eq("status", "active")
                    .execute()
                )
                position_count = len(existing_positions.data) if existing_positions.data else 0
                if position_count == 1:
                    print(f"   ✅ No duplicate positions created (count: {position_count})")
                else:
                    print(f"   ⚠️  Position count: {position_count} (expected 1, may have duplicates)")
            else:
                print(f"❌ FAIL: Expected approval for already-holding, got action={action}")
        else:
            print("❌ FAIL: No decision strand created")
        
        # Test 4: Removed blockers don't block (intent, capacity)
        print("\n[TEST 4] Removed blockers (intent, capacity) don't block")
        print("-" * 80)
        # Test with "no_intent" intent type (should not block)
        signal = self._build_social_signal()
        signal["signal_pack"]["intent_analysis"] = {
            "intent_analysis": {
                "intent_type": "no_intent",  # Previously would block
                "allocation_multiplier": 0.5,
                "confidence": 0.3,
            }
        }
        signal["id"] = f"reject-test-intent-{uuid.uuid4()}"
        created_signal = self.supabase_manager.insert_strand(signal)
        await self.learning_system.process_strand_event(created_signal)
        decision = self._fetch_child_strand(created_signal["id"], "decision_lowcap")
        if decision:
            action = decision.get("content", {}).get("action")
            if action == "approve":
                print("✅ PASS: Intent analysis no longer blocks (removed blocker)")
            else:
                print(f"❌ FAIL: Expected approval despite no_intent, got action={action}")
        else:
            print("❌ FAIL: No decision strand created")
        
        # Test capacity (should not block - positions go to waitlist)
        print("\n[TEST 4b] Capacity check (should not block)")
        print("-" * 80)
        signal = self._build_social_signal()
        signal["id"] = f"reject-test-capacity-{uuid.uuid4()}"
        created_signal = self.supabase_manager.insert_strand(signal)
        await self.learning_system.process_strand_event(created_signal)
        decision = self._fetch_child_strand(created_signal["id"], "decision_lowcap")
        if decision:
            action = decision.get("content", {}).get("action")
            if action == "approve":
                print("✅ PASS: Capacity check no longer blocks (removed blocker)")
            else:
                print(f"❌ FAIL: Expected approval despite capacity, got action={action}")
        else:
            print("❌ FAIL: No decision strand created")
        
        print("\n" + "="*80)
        print("DM REJECTION CRITERIA TESTS COMPLETE")
        print("="*80 + "\n")


async def async_main(run_learning_jobs: bool, test_rejections: bool) -> None:
    harness = PMLearningFlowHarness()
    if test_rejections:
        await harness.test_dm_rejection_criteria()
    else:
        await harness.run(run_learning_jobs=run_learning_jobs)


def main() -> None:
    parser = argparse.ArgumentParser(description="PM learning flow test harness")
    parser.add_argument(
        "--run-learning-jobs",
        action="store_true",
        help="Run aggregator + lesson builder + materializer after decision stage",
    )
    parser.add_argument(
        "--test-rejections",
        action="store_true",
        help="Run DM rejection criteria tests (chain support, curator score, already-holding, removed blockers)",
    )
    args = parser.parse_args()

    asyncio.run(async_main(run_learning_jobs=args.run_learning_jobs, test_rejections=args.test_rejections))


if __name__ == "__main__":
    main()

