"""
PM Runtime Sizing Harness

Verifies that apply_pattern_strength_overrides correctly queries the pm_overrides table
and applies the sizing multiplier to the plan levers.
"""

import asyncio
import logging
import os
import uuid
from typing import Dict, Any

from supabase import create_client, Client
from src.intelligence.lowcap_portfolio_manager.pm.overrides import apply_pattern_strength_overrides

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("RuntimeSizingHarness")

async def setup_test_override(sb: Client, pattern_key: str, multiplier: float) -> None:
    """Inject a test override."""
    payload = {
        'pattern_key': pattern_key,
        'action_category': 'entry',
        'scope_subset': {"chain": "solana", "mcap_bucket": "micro"}, # Specific slice
        'multiplier': multiplier,
        'confidence_score': 0.9,
        'last_updated_at': "2023-01-01T00:00:00Z"
    }
    # Upsert
    sb.table("pm_overrides").upsert(
        payload, on_conflict="pattern_key,action_category,scope_subset"
    ).execute()
    logger.info(f"Inserted override: {pattern_key} -> {multiplier}x")

async def run_harness():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        logger.error("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
        return
        
    sb = create_client(url, key)
    pattern_key = f"TEST_RUNTIME_{uuid.uuid4().hex[:8]}"
    
    print("\n=================================================================")
    print("🚀 STARTING PM RUNTIME SIZING HARNESS")
    print("=================================================================")
    
    try:
        # 1. Setup Override (Multiplier = 1.5x)
        TEST_MULT = 1.5
        await setup_test_override(sb, pattern_key, TEST_MULT)
        
        # 2. Define Context
        # Case A: Matching Scope
        scope_match = {
            "chain": "solana",
            "mcap_bucket": "micro",
            "timeframe": "1h",
            "intent": "pump"
        }
        
        # Case B: Non-Matching Scope
        scope_miss = {
            "chain": "ethereum", # Mismatch
            "mcap_bucket": "micro"
        }
        
        base_levers = {
            "A_value": 0.5,
            "E_value": 0.5,
            "position_size_frac": 0.10 # Base 10%
        }
        
        # 3. Test Matching
        print("\n[Test 1] Matching Scope...")
        adjusted_match = apply_pattern_strength_overrides(
            pattern_key, "entry", scope_match, base_levers, sb_client=sb
        )
        final_size = adjusted_match['position_size_frac']
        expected_size = 0.10 * TEST_MULT
        
        print(f"  -> Base Size: 0.10")
        print(f"  -> Multiplier: {TEST_MULT}")
        print(f"  -> Final Size: {final_size:.4f}")
        
        if abs(final_size - expected_size) < 0.001:
            print("  ✅ PASS: Multiplier applied correctly.")
        else:
            print(f"  ❌ FAIL: Expected {expected_size}, got {final_size}")
            
        # 4. Test Mismatch
        print("\n[Test 2] Non-Matching Scope...")
        adjusted_miss = apply_pattern_strength_overrides(
            pattern_key, "entry", scope_miss, base_levers, sb_client=sb
        )
        final_size_miss = adjusted_miss['position_size_frac']
        
        print(f"  -> Final Size: {final_size_miss:.4f}")
        
        if abs(final_size_miss - 0.10) < 0.001:
            print("  ✅ PASS: Mismatch ignored (Base size preserved).")
        else:
            print(f"  ❌ FAIL: Expected 0.10, got {final_size_miss}")

        print("\n=================================================================")
        print("🎉 HARNESS COMPLETE")
        print("=================================================================\n")

    except Exception as e:
        logger.error(f"Harness failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(run_harness())

