#!/usr/bin/env python3
"""
Fix specific positions by contract address
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.append('src')

from utils.supabase_manager import SupabaseManager
from intelligence.trader_lowcap.trader_lowcap_simple_v2 import TraderLowcapSimpleV2
from communication.direct_table_communicator import DirectTableCommunicator

def calculate_totals_from_exits(exits):
    """Calculate total_extracted_native and total_tokens_sold from exits"""
    total_extracted_native = 0.0
    total_tokens_sold = 0.0
    
    for exit_data in exits:
        if exit_data.get('status') == 'executed':
            # Calculate from actual_tokens_sold and price
            tokens_sold = exit_data.get('actual_tokens_sold', 0.0) or 0.0
            exit_price = exit_data.get('price', 0.0) or 0.0
            cost_native = tokens_sold * exit_price  # Calculate native amount extracted
            
            total_extracted_native += cost_native
            total_tokens_sold += tokens_sold
    
    return total_extracted_native, total_tokens_sold

def calculate_totals_from_entries(entries):
    """Calculate total_investment_native and total_tokens_bought from entries"""
    total_investment_native = 0.0
    total_tokens_bought = 0.0
    
    for entry in entries:
        if entry.get('status') == 'executed':
            # Use amount_native as the native currency invested
            amount_native = entry.get('amount_native', 0.0) or 0.0
            price = entry.get('price', 0.0) or 0.0
            
            # Try to get tokens_bought directly, or calculate from amount_native / price
            tokens_bought = entry.get('tokens_bought', 0.0) or 0.0
            if tokens_bought == 0 and price > 0:
                # Calculate tokens_bought from amount_native / price (old format)
                tokens_bought = amount_native / price
            
            total_investment_native += amount_native
            total_tokens_bought += tokens_bought
    
    return total_investment_native, total_tokens_bought

async def fix_position(supabase, trader, position):
    """Fix a single position by calculating missing totals and updating exits/P&L"""
    position_id = position['id']
    entries = position.get('entries', []) or []
    exits = position.get('exits', []) or []
    
    print(f"🔧 Fixing position {position_id}...")
    
    # Calculate totals from entries
    total_investment_native, total_tokens_bought = calculate_totals_from_entries(entries)
    
    # Calculate totals from exits
    total_extracted_native, total_tokens_sold = calculate_totals_from_exits(exits)
    
    # Calculate average prices
    avg_entry_price = total_investment_native / total_tokens_bought if total_tokens_bought > 0 else 0.0
    avg_exit_price = total_extracted_native / total_tokens_sold if total_tokens_sold > 0 else 0.0
    
    # Prepare update data (clear old P&L data)
    update_data = {
        'total_investment_native': total_investment_native,
        'total_extracted_native': total_extracted_native,
        'total_tokens_bought': total_tokens_bought,
        'total_tokens_sold': total_tokens_sold,
        'avg_entry_price': avg_entry_price,
        'avg_exit_price': avg_exit_price,
        'total_pnl_native': 0.0,  # Will be recalculated
        'total_pnl_usd': 0.0,     # Will be recalculated
        'total_pnl_pct': 0.0,     # Will be recalculated
    }
    
    # Update position in database
    try:
        result = supabase.client.table('lowcap_positions').update(update_data).eq('id', position_id).execute()
        
        if result.data:
            print(f"✅ Updated totals for {position_id}:")
            print(f"   Investment: {total_investment_native:.8f} native")
            print(f"   Extracted: {total_extracted_native:.8f} native")
            print(f"   Tokens bought: {total_tokens_bought:.8f}")
            print(f"   Tokens sold: {total_tokens_sold:.8f}")
            print(f"   Avg entry price: {avg_entry_price:.8f}")
            print(f"   Avg exit price: {avg_exit_price:.8f}")
            
            # Update P&L with current prices
            print(f"💰 Updating P&L...")
            await trader._update_position_pnl(position_id)
            
            print(f"✅ Fully updated {position_id}")
            return True
        else:
            print(f"❌ Failed to update {position_id}")
            return False
            
    except Exception as e:
        print(f"❌ Error updating {position_id}: {e}")
        return False

async def main():
    """Fix specific positions by contract address"""
    
    # Contract addresses to fix
    contract_addresses = [
        "KounQV6YhTgWFHbs4wNjyRp2VoY4ghoysveNQeGuBLV",
        "9223LqDuoJXyhCtvi54DUQPGS8Xf29kUEQRr7Sfhmoon", 
        "0x7d03759E5B41E36899833cb2E008455d69A24444",
        "CmUnSFZCKUFGs2L8eZGQukAj833Y8r2SiJav55Nnrihd"
    ]
    
    print("🔍 Finding and fixing positions by contract address...")
    print("=" * 60)
    
    # Initialize components
    supabase = SupabaseManager()
    supabase_manager = DirectTableCommunicator()
    trader = TraderLowcapSimpleV2(supabase_manager)
    
    found_positions = []
    
    for contract in contract_addresses:
        print(f"\n🔍 Searching for contract: {contract}")
        
        try:
            # Search by token_contract
            result = supabase.client.table('lowcap_positions').select('*').eq('token_contract', contract).execute()
            
            if result.data:
                for position in result.data:
                    position_id = position.get('id', 'Unknown')
                    ticker = position.get('token_ticker', 'Unknown')
                    chain = position.get('token_chain', 'Unknown')
                    
                    print(f"   ✅ Found: {position_id} | {ticker} ({chain})")
                    found_positions.append(position)
            else:
                print(f"   ❌ No position found for contract {contract}")
                
        except Exception as e:
            print(f"   ❌ Error searching for {contract}: {e}")
    
    if not found_positions:
        print("\n❌ No positions found for any of the contract addresses")
        return
    
    print(f"\n📊 Found {len(found_positions)} positions to fix")
    print("=" * 60)
    
    # Fix each position
    fixed_count = 0
    failed_count = 0
    
    for position in found_positions:
        if await fix_position(supabase, trader, position):
            fixed_count += 1
        else:
            failed_count += 1
        print()  # Empty line for readability
    
    # Summary
    print("🎯 Summary:")
    print(f"   ✅ Fixed: {fixed_count}")
    print(f"   ❌ Failed: {failed_count}")
    print(f"   📊 Total: {len(found_positions)}")

if __name__ == "__main__":
    asyncio.run(main())
