#!/usr/bin/env python3
"""
Add new tokens to the lowcap_positions table for backtesting.

Tokens to add:
- $Optim 86BMwo29TgobuYTCFU7tf3DBhgNvgeCkNTQXbAvUpump
- $Zerith 59yQZzHvGvdM3DvMXuDHWsYdbqzERoD8QfT1Y25Npump
- $ZKSL 9Yn6bnF3eKLqocUVMxduh7WWqgQZ8DvWQDYTX9Ncpump
- $Lumen BkpaxHhE6snExazrPkVAjxDyZa8Nq3oDEzm5GQm2pump
- $Ore oreoU2P8bN6jkk3jbaiVxYnG1dCXcYxwhwyK9jSybcp
- $Dark 8BtoThi2ZoXnF7QQK1Wjmh2JuBw9FjVvhnGMVZ2vpump
"""

import os
import sys
import time

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# Token data: (ticker, contract, chain)
tokens = [
    ("OPTIM", "86BMwo29TgobuYTCFU7tf3DBhgNvgeCkNTQXbAvUpump", "solana"),
    ("ZERITH", "59yQZzHvGvdM3DvMXuDHWsYdbqzERoD8QfT1Y25Npump", "solana"),
    ("ZKSL", "9Yn6bnF3eKLqocUVMxduh7WWqgQZ8DvWQDYTX9Ncpump", "solana"),
    ("LUMEN", "BkpaxHhE6snExazrPkVAjxDyZa8Nq3oDEzm5GQm2pump", "solana"),
    ("ORE", "oreoU2P8bN6jkk3jbaiVxYnG1dCXcYxwhwyK9jSybcp", "solana"),
    ("DARK", "8BtoThi2ZoXnF7QQK1Wjmh2JuBw9FjVvhnGMVZ2vpump", "solana"),
]

def create_position_id(ticker: str, chain: str) -> str:
    """Generate position ID: {TICKER}_{chain}_{timestamp}"""
    timestamp = int(time.time())
    return f"{ticker}_{chain}_{timestamp}"

print("="*70)
print("ADDING NEW TOKENS TO POSITIONS TABLE")
print("="*70)

successful = []
failed = []

for ticker, contract, chain in tokens:
    try:
        # Check if position already exists
        existing = (
            sb.table("lowcap_positions")
            .select("id, token_ticker")
            .eq("token_contract", contract)
            .eq("token_chain", chain)
            .execute()
        )
        
        if existing.data:
            print(f"\n⚠️  {ticker} already exists:")
            print(f"   ID: {existing.data[0].get('id')}")
            print(f"   Ticker: {existing.data[0].get('token_ticker')}")
            continue
        
        # Create position ID
        position_id = create_position_id(ticker, chain)
        
        # Create position record
        position = {
            "id": position_id,
            "token_chain": chain,
            "token_contract": contract,
            "token_ticker": ticker,
            "total_allocation_pct": 0.0,
            "status": "active",
            "book_id": "social",
            "total_quantity": 0.0,
            "features": {},  # Will be populated by geometry/TA tracker
        }
        
        # Insert
        result = sb.table("lowcap_positions").insert(position).execute()
        
        if result.data:
            print(f"\n✅ {ticker} added successfully")
            print(f"   ID: {position_id}")
            print(f"   Contract: {contract[:30]}...")
            successful.append(ticker)
        else:
            print(f"\n❌ {ticker} failed to insert (no data returned)")
            failed.append(ticker)
            
    except Exception as e:
        print(f"\n❌ {ticker} failed: {e}")
        failed.append(ticker)

print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print(f"\n✅ Successful: {len(successful)}/{len(tokens)}")
for ticker in successful:
    print(f"   - {ticker}")

if failed:
    print(f"\n❌ Failed: {len(failed)}/{len(tokens)}")
    for ticker in failed:
        print(f"   - {ticker}")

print("="*70)

