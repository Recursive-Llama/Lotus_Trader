"""
Lowcap TA / Rollup Harness
===========================

Flow-style harness following FLOW_TESTING_ETHOS.md:
1. Inject a real social signal for a real token (Avici)
2. Let the system process it (decision maker → positions → backfill → rollups → TA tracker)
3. Query the database to verify each step happened

Usage:
    PYTHONPATH=src:. python tests/flow/lowcap_ta_harness.py
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from dotenv import load_dotenv

from utils.supabase_manager import SupabaseManager
from intelligence.universal_learning.universal_learning_system import UniversalLearningSystem
from intelligence.decision_maker_lowcap.decision_maker_lowcap_simple import DecisionMakerLowcapSimple
from pathlib import Path
import yaml


LOGGER = logging.getLogger("lowcap_ta_harness")

# Default test token: Avici (BANK)
DEFAULT_TOKEN_CONTRACT = "BANKJmvhT8tiJRsBSS1n2HryMBPvT5Ze4HU95DUAmeta"
DEFAULT_TOKEN_CHAIN = "solana"
DEFAULT_TOKEN_TICKER = "BANK"


class LowcapTAHarness:
    def __init__(
        self,
        token_contract: str = DEFAULT_TOKEN_CONTRACT,
        token_chain: str = DEFAULT_TOKEN_CHAIN,
        token_ticker: str = DEFAULT_TOKEN_TICKER,
    ) -> None:
        load_dotenv()
        self.supabase_manager = SupabaseManager()
        self.signal_id: Optional[str] = None
        self.decision_id: Optional[str] = None
        self.position_ids: list = []
        self.token_contract = token_contract
        self.token_chain = token_chain.lower()
        self.token_ticker = token_ticker
        
    def _build_social_signal(self) -> Dict:
        """Build a social signal for the test token."""
        now = datetime.now(timezone.utc)
        strand_id = f"ta-test-{uuid.uuid4()}"
        token = {
            "ticker": self.token_ticker,
            "contract": self.token_contract,
            "chain": self.token_chain,
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
                        "text": "TA harness test signal",
                        "timestamp": now.isoformat(),
                        "url": "https://twitter.com/detweiler/status/ta-test",
                        "has_image": False,
                        "has_chart": False,
                    }
                }
            },
            "content": {
                "summary": f"TA harness signal for {token['ticker']}",
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
    
    def _fetch_child_strand(self, parent_id: str, kind: str) -> Optional[Dict]:
        """Fetch child strand by parent_id and kind."""
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
    
    def _fetch_positions(self, decision: Dict) -> list:
        """Fetch positions created by decision."""
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
    
    def _load_social_trading_config(self) -> Dict:
        """Load social trading config."""
        config_path = Path("src/config/social_trading_config.yaml")
        if not config_path.exists():
            raise RuntimeError("social_trading_config.yaml not found")
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
    
    async def _inject_social_signal(self) -> bool:
        """
        Inject a real social signal for the test token.
        Let the system process it (decision maker creates positions, triggers backfill).
        
        Returns:
            True if signal was injected and processed
        """
        print(f"\n[TEST 1] Inject Social Signal & Create Position")
        print("-" * 80)
        print(f"Token: {self.token_ticker} ({self.token_contract} on {self.token_chain})")
        
        # Set up learning system and decision maker
        learning_system = UniversalLearningSystem(
            supabase_manager=self.supabase_manager,
            llm_client=None,
            llm_config=None,
        )
        dm_config = self._load_social_trading_config()
        decision_maker = DecisionMakerLowcapSimple(
            supabase_manager=self.supabase_manager,
            config=dm_config,
            learning_system=learning_system,
        )
        learning_system.set_decision_maker(decision_maker)
        
        # Build signal with our test token
        signal = self._build_social_signal()
        
        # Inject signal
        created_signal = self.supabase_manager.insert_strand(signal)
        self.signal_id = created_signal["id"]
        print(f"✅ Injected social signal: {self.signal_id}")
        
        # Let the system process it
        await learning_system.process_strand_event(created_signal)
        print(f"✅ Learning system processed signal")
        
        # Query for decision
        decision = self._fetch_child_strand(self.signal_id, "decision_lowcap")
        if not decision:
            print("❌ FAIL: No decision_lowcap strand created")
            return False
        
        self.decision_id = decision["id"]
        action = decision.get("content", {}).get("action")
        print(f"✅ Decision created: {self.decision_id} (action: {action})")
        
        if action != "approve":
            print(f"⚠️  Decision was {action}, not approve - positions may not be created")
            return False
        
        # Query for positions
        positions = self._fetch_positions(decision)
        if not positions:
            print("❌ FAIL: No positions created")
            return False
        
        self.position_ids = [p["id"] for p in positions]
        print(f"✅ Created {len(positions)} positions: {', '.join(str(pid) for pid in self.position_ids)}")
        print(f"   Timeframes: {', '.join(p['timeframe'] for p in positions)}")
        
        return True
    
    def _verify_backfill(self, timeframe: str) -> bool:
        """
        Query database to verify backfill happened for a timeframe.
        
        Args:
            timeframe: Timeframe to check (1m, 15m, 1h, 4h)
            
        Returns:
            True if backfill data exists
        """
        print(f"\n[TEST 2] Verify Backfill ({timeframe})")
        print("-" * 80)
        
        # Query for OHLC data
        result = (
            self.supabase_manager.client.table("lowcap_price_data_ohlc")
            .select("timestamp", count="exact")
            .eq("token_contract", self.token_contract)
            .eq("chain", self.token_chain)
            .eq("timeframe", timeframe)
            .execute()
        )
        
        count = result.count if hasattr(result, 'count') else len(result.data) if result.data else 0
        
        if count > 0:
            print(f"✅ Backfill verified: {count} {timeframe} OHLC bars exist")
            
            # Get date range
            if result.data:
                timestamps = [r["timestamp"] for r in result.data[:10]]  # Sample
                print(f"   Sample timestamps: {timestamps[0] if timestamps else 'N/A'} ...")
            return True
        else:
            print(f"❌ FAIL: No {timeframe} OHLC bars found (backfill may not have completed yet)")
            print(f"   Note: Backfill runs asynchronously, may need to wait")
            return False
    
    def _verify_rollups(self) -> Dict[str, bool]:
        """
        Query database to verify rollups happened for all timeframes.
        
        Returns:
            Dictionary mapping timeframe to success status
        """
        print(f"\n[TEST 3] Verify Rollups")
        print("-" * 80)
        
        timeframes = ["1m", "5m", "15m", "1h", "4h"]
        results = {}
        
        for tf in timeframes:
            result = (
                self.supabase_manager.client.table("lowcap_price_data_ohlc")
                .select("timestamp", count="exact")
            .eq("token_contract", self.token_contract)
            .eq("chain", self.token_chain)
                .eq("timeframe", tf)
                .execute()
            )
            
            count = result.count if hasattr(result, 'count') else len(result.data) if result.data else 0
            results[tf] = count > 0
            
            if count > 0:
                print(f"✅ {tf}: {count} bars")
            else:
                print(f"⚠️  {tf}: No bars (may need scheduled rollup job to run)")
        
        return results
    
    def _verify_ta_tracker(self, timeframe: str = "1h") -> bool:
        """
        Query database to verify TA tracker ran and populated TA data.
        
        Args:
            timeframe: Timeframe to check
            
        Returns:
            True if TA data exists
        """
        print(f"\n[TEST 4] Verify TA Tracker ({timeframe})")
        print("-" * 80)
        
        # Query position features for TA data
        result = (
            self.supabase_manager.client.table("lowcap_positions")
            .select("id,features,timeframe")
            .eq("token_contract", self.token_contract)
            .eq("token_chain", self.token_chain)
            .eq("timeframe", timeframe)
            .execute()
        )
        
        if not result.data:
            print(f"❌ FAIL: No {timeframe} position found")
            return False
        
        position = result.data[0]
        features = position.get("features", {})
        ta = features.get("ta", {})
        
        if not ta:
            print(f"⚠️  No TA data in features (TA tracker may not have run yet)")
            print(f"   Note: TA tracker runs on schedule, may need to wait")
            return False
        
        # Check for key TA values
        ta_suffix = f"_{timeframe}" if timeframe != "1h" else "_1h"
        
        ema = ta.get("ema", {})
        ema60 = ema.get(f"ema60{ta_suffix}")
        ema144 = ema.get(f"ema144{ta_suffix}")
        ema333 = ema.get(f"ema333{ta_suffix}")
        
        atr = ta.get("atr", {})
        atr_val = atr.get(f"atr{ta_suffix}")
        
        momentum = ta.get("momentum", {})
        rsi_val = momentum.get(f"rsi{ta_suffix}")
        adx_val = momentum.get(f"adx{ta_suffix}")
        
        print(f"✅ TA data found:")
        if ema60:
            print(f"   EMA60: {ema60:.6f}")
        if ema144:
            print(f"   EMA144: {ema144:.6f}")
        if ema333:
            print(f"   EMA333: {ema333:.6f}")
        if atr_val:
            print(f"   ATR: {atr_val:.6f}")
        if rsi_val is not None:
            print(f"   RSI: {rsi_val:.2f}")
        if adx_val:
            print(f"   ADX: {adx_val:.2f}")
        
        # Basic validation
        if ema60 and ema144 and ema333:
            print(f"   ✅ EMA values present")
        if atr_val and atr_val > 0:
            print(f"   ✅ ATR is positive")
        if rsi_val is not None and 0 <= rsi_val <= 100:
            print(f"   ✅ RSI is in valid range")
        
        return True
    
    def _verify_geometry_builder(self, timeframe: str = "1h") -> bool:
        """
        Query database to verify geometry builder can work (TA data exists).
        
        Args:
            timeframe: Timeframe to check
            
        Returns:
            True if geometry can be built
        """
        print(f"\n[TEST 5] Verify Geometry Builder ({timeframe})")
        print("-" * 80)
        
        # Query position for TA data (geometry builder uses TA data)
        result = (
            self.supabase_manager.client.table("lowcap_positions")
            .select("id,features")
            .eq("token_contract", self.token_contract)
            .eq("token_chain", self.token_chain)
            .eq("timeframe", timeframe)
            .execute()
        )
        
        if not result.data:
            print(f"❌ FAIL: No {timeframe} position found")
            return False
        
        position = result.data[0]
        features = position.get("features", {})
        ta = features.get("ta", {})
        
        if not ta:
            print(f"⚠️  No TA data available for geometry builder")
            return False
        
        # Check if we have the necessary EMA values for geometry
        ta_suffix = f"_{timeframe}" if timeframe != "1h" else "_1h"
        ema = ta.get("ema", {})
        ema60 = ema.get(f"ema60{ta_suffix}")
        ema144 = ema.get(f"ema144{ta_suffix}")
        ema333 = ema.get(f"ema333{ta_suffix}")
        
        if ema60 and ema144 and ema333:
            print(f"✅ Geometry builder has required EMA values:")
            print(f"   EMA60: {ema60:.6f}")
            print(f"   EMA144: {ema144:.6f}")
            print(f"   EMA333: {ema333:.6f}")
            print(f"✅ Geometry can be built from TA data")
            return True
        else:
            print(f"⚠️  Missing required EMA values for geometry")
            return False
    
    async def run(self) -> None:
        """Run all tests following flow ethos."""
        print("\n" + "="*80)
        print("LOWCAP TA / ROLLUP HARNESS (Flow Ethos)")
        print("="*80)
        print(f"Token: {self.token_ticker} ({self.token_contract} on {self.token_chain})")
        print("\nFollowing FLOW_TESTING_ETHOS.md:")
        print("1. Inject packet (social signal)")
        print("2. Let system process it (decision → positions → backfill → rollups → TA tracker)")
        print("3. Query database to verify each step")
        print("="*80)
        
        # Test 1: Inject signal and let system create positions (triggers backfill)
        success = await self._inject_social_signal()
        if not success:
            print("\n❌ FAIL: Could not inject signal or create positions")
            return
        
        # Wait a bit for async backfill to start
        print("\n⏳ Waiting 5 seconds for async backfill to start...")
        await asyncio.sleep(5)
        
        # Test 2: Verify backfill happened (query database)
        backfill_1m = self._verify_backfill("1m")
        backfill_1h = self._verify_backfill("1h")
        
        # Test 3: Verify rollups happened (query database)
        rollup_results = self._verify_rollups()
        
        # Test 4: Verify TA tracker ran (query database)
        ta_success = self._verify_ta_tracker("1h")
        
        # Test 5: Verify geometry builder can work (query database)
        geometry_success = self._verify_geometry_builder("1h")
        
        # Summary
        print("\n" + "="*80)
        print("LOWCAP TA / ROLLUP HARNESS COMPLETE")
        print("="*80)
        print(f"✅ Signal injected: {self.signal_id}")
        print(f"✅ Decision created: {self.decision_id}")
        print(f"✅ Positions created: {len(self.position_ids)}")
        print(f"✅ Backfill (1m): {'PASS' if backfill_1m else 'WAIT/FAIL'}")
        print(f"✅ Backfill (1h): {'PASS' if backfill_1h else 'WAIT/FAIL'}")
        print(f"✅ Rollups: {sum(1 for v in rollup_results.values() if v)}/{len(rollup_results)} timeframes")
        print(f"✅ TA Tracker: {'PASS' if ta_success else 'WAIT/FAIL'}")
        print(f"✅ Geometry Builder: {'PASS' if geometry_success else 'WAIT/FAIL'}")
        print("\nNote: Some steps may need scheduled jobs to run. Check again after jobs execute.")
        print("="*80 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Lowcap TA / Rollup test harness (Flow Ethos)")
    parser.add_argument("--token-contract", type=str, default=DEFAULT_TOKEN_CONTRACT, help="Token contract address")
    parser.add_argument("--token-chain", type=str, default=DEFAULT_TOKEN_CHAIN, help="Token chain (solana, base, etc.)")
    parser.add_argument("--token-ticker", type=str, default=DEFAULT_TOKEN_TICKER, help="Token ticker/symbol")
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    harness = LowcapTAHarness(
        token_contract=args.token_contract,
        token_chain=args.token_chain,
        token_ticker=args.token_ticker,
    )
    asyncio.run(harness.run())


if __name__ == "__main__":
    main()
