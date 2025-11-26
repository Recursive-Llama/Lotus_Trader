import unittest
import os
import json
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv
from src.intelligence.lowcap_portfolio_manager.jobs.tuning_miner import TuningMiner

# Load env
load_dotenv()

class TestTuningMiner(unittest.TestCase):
    def setUp(self):
        self.supabase_url = os.environ.get("SUPABASE_URL")
        self.supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not self.supabase_url:
            self.skipTest("No Supabase credentials")
        self.sb: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Clean up
        self.sb.table("pattern_episode_events").delete().neq("id", 0).execute()
        self.sb.table("learning_lessons").delete().eq("lesson_type", "tuning_rates").execute()

    def test_miner_logic(self):
        print("\n[Test] Tuning Miner Rates Logic")
        
        # 1. Seed Events
        # We create a scenario for "Solana + S1"
        # - 10 Acted, 6 Success (WR=0.6, FPR=0.4)
        # - 20 Skipped, 16 Success (MR=0.8, DR=0.2) -> "Missed Opportunity" signal
        
        events = []
        scope = {"chain": "solana", "bucket": "micro"}
        pattern_key = "pm.uptrend.S1.entry"
        
        # Acted Events
        for _ in range(6):
            events.append(self._create_event(scope, pattern_key, "acted", "success"))
        for _ in range(4):
            events.append(self._create_event(scope, pattern_key, "acted", "failure"))
            
        # Skipped Events
        for _ in range(16):
            events.append(self._create_event(scope, pattern_key, "skipped", "success"))
        for _ in range(4):
            events.append(self._create_event(scope, pattern_key, "skipped", "failure"))
            
        # Bulk Insert
        print(f"  -> Seeding {len(events)} events...")
        self.sb.table("pattern_episode_events").insert(events).execute()
        
        # 2. Run Miner
        print("  -> Running Miner...")
        miner = TuningMiner()
        miner.N_MIN = 5 # Lower threshold for test
        miner.run()
        
        # 3. Verify Lessons
        print("  -> Verifying Lessons...")
        
        # Check Global Slice (Empty Scope)
        res_global = self.sb.table("learning_lessons").select("*")\
            .eq("lesson_type", "tuning_rates")\
            .eq("pattern_key", pattern_key)\
            .execute()
            
        # Filter for the empty scope lesson
        lesson_global = next((l for l in res_global.data if l['scope_subset'] == {}), None)
        self.assertIsNotNone(lesson_global, "Global lesson not found")
        stats = lesson_global['stats']
        print(f"  -> Global Stats: {stats}")
        self.assertEqual(stats['wr'], 0.6)
        self.assertEqual(stats['mr'], 0.8)
        
        # Check Slice "chain=solana"
        lesson_sol = next((l for l in res_global.data if l['scope_subset'] == {"chain": "solana"}), None)
        self.assertIsNotNone(lesson_sol, "Solana slice lesson not found")
        stats_sol = lesson_sol['stats']
        print(f"  -> Solana Stats: {stats_sol}")
        self.assertEqual(stats_sol['wr'], 0.6)
        self.assertEqual(stats_sol['mr'], 0.8)
        
        # Check Slice "chain=solana, bucket=micro" (Depth 2)
        # Note: The scope_subset stored in DB matches the input {"chain": "solana", "bucket": "micro"}
        # The order of keys in JSONB equality check might matter, but Supabase/Postgres handles JSONB equality correctly.
        lesson_deep = next((l for l in res_global.data if l['scope_subset'].get("chain") == "solana" and l['scope_subset'].get("bucket") == "micro"), None)
        self.assertIsNotNone(lesson_deep, "Deep slice (Solana+Micro) lesson not found")
        print(f"  -> Deep Stats: {lesson_deep['stats']}")
        self.assertEqual(lesson_deep['stats']['wr'], 0.6)

    def _create_event(self, scope, pattern_key, decision, outcome):
        return {
            "scope": scope,
            "pattern_key": pattern_key,
            "episode_id": f"test_{datetime.utcnow().timestamp()}_{os.urandom(4).hex()}",
            "decision": decision,
            "outcome": outcome,
            "factors": {"ts_score": 50},
            "timestamp": datetime.utcnow().isoformat()
        }

if __name__ == "__main__":
    unittest.main()

