#!/usr/bin/env python3
"""
Fix Existing Positions Script

This script calculates missing totals for existing positions from their entries/exits JSONB data.
It populates:
- total_investment_native
- total_extracted_native  
- total_tokens_bought
- total_tokens_sold
- avg_entry_price
- avg_exit_price

This enables the new native-first tracking system to work with existing positions.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv
from supabase import create_client, Client
from typing import Dict, Any, List

# Load environment variables
load_dotenv()

def get_supabase_client() -> Client:
    """Get Supabase client"""
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    
    if not url or not key:
        print("❌ Missing SUPABASE_URL or SUPABASE_KEY environment variables")
        sys.exit(1)
    
    return create_client(url, key)

def calculate_totals_from_entries(entries: List[Dict]) -> tuple[float, float]:
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

def calculate_totals_from_exits(exits: List[Dict]) -> tuple[float, float]:
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

async def fix_position(supabase: Client, trader, position: Dict[str, Any]) -> bool:
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
        result = supabase.table('lowcap_positions').update(update_data).eq('id', position_id).execute()
        
        if result.data:
            print(f"✅ Updated totals for {position_id}:")
            print(f"   Investment: {total_investment_native:.8f} native")
            print(f"   Extracted: {total_extracted_native:.8f} native")
            print(f"   Tokens bought: {total_tokens_bought:.8f}")
            print(f"   Tokens sold: {total_tokens_sold:.8f}")
            print(f"   Avg entry price: {avg_entry_price:.8f}")
            print(f"   Avg exit price: {avg_exit_price:.8f}")
            
            # Create exit rules if missing or have old values
            exit_rules = position.get('exit_rules', {})
            needs_exit_rules = (
                not exit_rules or 
                not exit_rules.get('stages') or
                exit_rules.get('stages', [{}])[0].get('gain_pct', 0) in [30, 60, 200, 300]  # Old hardcoded values
            )
            
            if needs_exit_rules:
                print(f"📋 Creating exit rules for {position_id}...")
                exit_rules = trader._build_exit_rules_from_config()
                trend_exit_rules = trader._build_trend_exit_rules_from_config()
                
                # Update position with rules using trader's repository
                position['exit_rules'] = exit_rules
                position['trend_exit_rules'] = trend_exit_rules
                trader.repo.update_position(position_id, position)
                print(f"   ✅ Created exit rules and trend exit rules")
            
            # Recalculate exits with new avg_entry_price
            print(f"🔄 Recalculating exits for {position_id}...")
            await trader._recalculate_exits_after_entry(position_id)
            
            # Update total_quantity from wallet (source of truth)
            print(f"💳 Updating total_quantity from wallet for {position_id}...")
            wallet_success = await trader._update_total_quantity_from_wallet(position_id)
            if wallet_success:
                print(f"   ✅ Updated total_quantity from wallet")
            else:
                print(f"   ⚠️  Wallet check failed, using calculated value")
            
            # Update P&L with current prices
            print(f"💰 Updating P&L for {position_id}...")
            await trader._update_position_pnl(position_id)
            
            # Create trend batches for executed exits
            if total_tokens_sold > 0:  # Has executed exits
                print(f"🎯 Creating trend batches for executed exits...")
                executed_exits = [exit for exit in exits if exit.get('status') == 'executed']
                
                for exit_data in executed_exits:
                    try:
                        await trader._spawn_trend_batch_after_standard_exit(position_id, exit_data)
                        print(f"   ✅ Created trend batch for exit {exit_data.get('exit_number', '?')}")
                    except Exception as e:
                        print(f"   ❌ Failed to create trend batch for exit {exit_data.get('exit_number', '?')}: {e}")
            else:
                print(f"ℹ️  No executed exits found for {position_id}")
            
            print(f"✅ Fully updated {position_id}")
            return True
        else:
            print(f"❌ Failed to update {position_id}")
            return False
            
    except Exception as e:
        print(f"❌ Error updating {position_id}: {e}")
        return False

async def populate_native_token_prices(supabase: Client, trader):
    """Populate database with native token prices (WETH, WBNB, SOL)"""
    print("💰 Populating native token prices...")
    
    # Native token addresses
    native_tokens = {
        'ethereum': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',  # WETH
        'bsc': '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c',       # WBNB
        'solana': 'So11111111111111111111111111111111111111112'      # SOL
    }
    
    for chain, contract in native_tokens.items():
        try:
            print(f"   📊 Getting {chain.upper()} price...")
            
            # Get price from Price Oracle
            if chain == 'ethereum':
                price_info = trader.price_oracle.price_eth(contract)
            elif chain == 'bsc':
                price_info = trader.price_oracle.price_bsc(contract)
            elif chain == 'solana':
                price_info = trader.price_oracle.price_solana(contract)
            else:
                continue
            
            if price_info and 'price_usd' in price_info and 'price_native' in price_info:
                # Store in database
                price_data = {
                    'token_contract': contract,
                    'chain': chain,
                    'timestamp': '2025-01-27T00:00:00Z',  # Fixed timestamp for migration
                    'price_usd': float(price_info['price_usd']),
                    'price_native': float(price_info['price_native']),
                    'quote_token': 'USDC',  # Assume USDC for native tokens
                    'liquidity_usd': 0,
                    'liquidity_change_1m': 0,
                    'volume_24h': 0,
                    'volume_change_1m': 0,
                    'price_change_24h': 0,
                    'market_cap': 0,
                    'fdv': 0,
                    'dex_id': 'unknown',
                    'pair_address': 'unknown',
                    'source': 'migration_script'
                }
                
                # Insert into database
                result = supabase.table('lowcap_price_data_1m').upsert(price_data).execute()
                if result.data:
                    print(f"   ✅ Stored {chain.upper()} price: ${price_info['price_usd']:.2f}")
                else:
                    print(f"   ❌ Failed to store {chain.upper()} price")
            else:
                print(f"   ❌ Could not get {chain.upper()} price")
                
        except Exception as e:
            print(f"   ❌ Error getting {chain.upper()} price: {e}")
    
    print("✅ Native token prices populated")

async def main():
    """Main function to fix all existing positions"""
    print("🚀 Starting comprehensive fix for existing positions...")
    
    # Get Supabase client
    supabase = get_supabase_client()
    
    # Import and create trader instance
    print("🔧 Initializing trader...")
    try:
        import sys
        sys.path.append('src')
        from intelligence.trader_lowcap.trader_lowcap_simple_v2 import TraderLowcapSimpleV2
        from communication.direct_table_communicator import DirectTableCommunicator
        
        # Create supabase manager and trader
        supabase_manager = DirectTableCommunicator()
        trader = TraderLowcapSimpleV2(supabase_manager)
        print("✅ Trader initialized")
        
    except Exception as e:
        print(f"❌ Error initializing trader: {e}")
        return
    
    # Populate native token prices first
    await populate_native_token_prices(supabase, trader)
    
    # Get all active positions
    print("📊 Fetching active positions...")
    try:
        result = supabase.table('lowcap_positions').select('*').eq('status', 'active').execute()
        positions = result.data
        
        if not positions:
            print("ℹ️  No active positions found")
            return
        
        print(f"📋 Found {len(positions)} active positions")
        
    except Exception as e:
        print(f"❌ Error fetching positions: {e}")
        return
    
    # Fix each position
    fixed_count = 0
    failed_count = 0
    
    for position in positions:
        if await fix_position(supabase, trader, position):
            fixed_count += 1
        else:
            failed_count += 1
        print()  # Empty line for readability
    
    # Summary
    print("🎯 Summary:")
    print(f"   ✅ Fixed: {fixed_count}")
    print(f"   ❌ Failed: {failed_count}")
    print(f"   📊 Total: {len(positions)}")
    
    if failed_count == 0:
        print("🎉 All positions fully updated and ready for trading!")
    else:
        print(f"⚠️  {failed_count} positions failed to fix")

if __name__ == "__main__":
    asyncio.run(main())
