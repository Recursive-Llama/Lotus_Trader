#!/usr/bin/env python3
"""
Quick test script to verify portfolio tracking is working.
Tests that positions are being captured in the JSONB column.
"""
import asyncio
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    # Try parent directory
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from supabase import create_client, Client
from intelligence.system_observer.jobs.balance_snapshot import BalanceSnapshotJob

async def test_portfolio_tracking():
    """Test that portfolio tracking captures positions correctly"""
    
    # Initialize Supabase client
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        return False
    
    sb: Client = create_client(supabase_url, supabase_key)
    
    print("🔍 Testing Portfolio Tracking...")
    print("-" * 60)
    
    # 1. Check active positions
    print("\n1. Checking active positions...")
    positions = (
        sb.table("lowcap_positions")
        .select("token_ticker,token_contract,token_chain,timeframe,current_usd_value,total_pnl_usd,rpnl_usd,total_extracted_usd,total_allocation_usd")
        .eq("status", "active")
        .execute()
    ).data or []
    
    print(f"   Found {len(positions)} active positions")
    if positions:
        for pos in positions[:3]:  # Show first 3
            ticker = pos.get("token_ticker", "?")
            value = pos.get("current_usd_value", 0)
            print(f"   - {ticker}: ${value:.2f}")
    
    # 2. Create a test snapshot
    print("\n2. Creating test snapshot...")
    snapshot_job = BalanceSnapshotJob(sb)
    
    try:
        snapshot = await snapshot_job.capture_snapshot("hourly")
        print(f"   ✅ Snapshot created: ${snapshot['total_balance_usd']:.2f}")
        print(f"   - USDC: ${snapshot['usdc_total']:.2f}")
        print(f"   - Active positions: ${snapshot['active_positions_value']:.2f} ({snapshot['active_positions_count']} positions)")
        
        # 3. Check if positions array was saved
        print("\n3. Verifying positions array in database...")
        latest = (
            sb.table("wallet_balance_snapshots")
            .select("id,positions,captured_at")
            .order("captured_at", desc=True)
            .limit(1)
            .execute()
        ).data
        
        if latest:
            latest_snapshot = latest[0]
            positions_array = latest_snapshot.get("positions", [])
            
            print(f"   ✅ Positions array found: {len(positions_array)} positions")
            
            if positions_array:
                print("\n   Position details:")
                for pos in positions_array[:3]:  # Show first 3
                    ticker = pos.get("ticker", "?")
                    value = pos.get("value", 0)
                    current_pnl = pos.get("current_pnl", 0)
                    realized_pnl = pos.get("realized_pnl", 0)
                    print(f"   - {ticker}: value=${value:.2f}, current_pnl=${current_pnl:.2f}, realized_pnl=${realized_pnl:.2f}")
                
                # Verify structure
                first_pos = positions_array[0]
                required_fields = ["ticker", "value", "current_pnl", "realized_pnl", "extracted", "allocated"]
                missing = [f for f in required_fields if f not in first_pos]
                if missing:
                    print(f"   ⚠️  Missing fields: {missing}")
                else:
                    print("   ✅ All required fields present")
            else:
                print("   ⚠️  Positions array is empty (no active positions?)")
        else:
            print("   ❌ Could not retrieve latest snapshot")
            return False
        
        print("\n" + "=" * 60)
        print("✅ Portfolio tracking test PASSED")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_portfolio_tracking())
    sys.exit(0 if success else 1)

