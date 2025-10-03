#!/usr/bin/env python3
"""
Check positions with executed exits to see if they need trend batch creation
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Add src to path
sys.path.append('src')

# Load environment variables
load_dotenv()

from utils.supabase_manager import SupabaseManager

async def check_executed_exits():
    """Check positions with executed exits to see if they need trend batch creation"""
    
    # Initialize Supabase
    supabase = SupabaseManager()
    
    print("🔍 Checking positions with executed exits...")
    print("=" * 80)
    
    try:
        # Get all positions
        result = supabase.client.table('lowcap_positions').select('*').order('created_at', desc=True).execute()
        
        if not result.data:
            print("❌ No positions found")
            return
            
        positions_with_executed_exits = []
        
        for position in result.data:
            exits = position.get('exits', [])
            executed_exits = [e for e in exits if e.get('status') == 'executed']
            
            if executed_exits:
                positions_with_executed_exits.append({
                    'position': position,
                    'executed_exits': executed_exits
                })
        
        print(f"📊 Found {len(positions_with_executed_exits)} positions with executed exits")
        print("=" * 80)
        
        for i, data in enumerate(positions_with_executed_exits):
            position = data['position']
            executed_exits = data['executed_exits']
            
            position_id = position.get('id', 'Unknown')
            ticker = position.get('token_ticker', 'Unknown')
            chain = position.get('token_chain', 'Unknown')
            
            print(f"\n{i+1}. {position_id[:20]}... | {ticker} ({chain})")
            print(f"   ✅ {len(executed_exits)} exits executed")
            
            # Check if trend batches exist
            trend_entries = position.get('trend_entries', [])
            trend_exits = position.get('trend_exits', [])
            
            print(f"   📊 Trend entries: {len(trend_entries)}")
            print(f"   📊 Trend exits: {len(trend_exits)}")
            
            # Check if trend batches were created for executed exits
            for exit_data in executed_exits:
                exit_num = exit_data.get('exit_number', '?')
                native_amount = exit_data.get('native_amount', 0)
                tx_hash = exit_data.get('tx_hash', 'None')
                
                print(f"      Exit {exit_num}: {native_amount} native | TX: {tx_hash[:20]}...")
                
                # Check if this exit has spawned trend batches
                exit_trend_entries = [te for te in trend_entries if te.get('source_exit_id') == exit_num]
                if exit_trend_entries:
                    print(f"         ✅ Has {len(exit_trend_entries)} trend entries")
                else:
                    print(f"         ⚠️  No trend entries spawned")
                    
            # Check if there are any trend entries without corresponding trend exits
            if trend_entries and not trend_exits:
                print(f"   ⚠️  Has trend entries but no trend exits - this might be the issue!")
                
    except Exception as e:
        print(f"❌ Error checking positions: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_executed_exits())
