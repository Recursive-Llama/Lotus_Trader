#!/usr/bin/env python3
"""Check structure of existing positions to understand required fields."""

import os
import sys
import json

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# Get an example active position
example = (
    sb.table("lowcap_positions")
    .select("*")
    .eq("status", "active")
    .limit(1)
    .execute()
)

if example.data:
    pos = example.data[0]
    print("="*70)
    print("EXAMPLE ACTIVE POSITION STRUCTURE")
    print("="*70)
    print("\nRequired/Important fields:")
    print(f"  id: {pos.get('id')}")
    print(f"  token_chain: {pos.get('token_chain')}")
    print(f"  token_contract: {pos.get('token_contract')}")
    print(f"  token_ticker: {pos.get('token_ticker')}")
    print(f"  total_allocation_pct: {pos.get('total_allocation_pct')}")
    print(f"  status: {pos.get('status')}")
    print(f"  book_id: {pos.get('book_id')}")
    print(f"\nOptional but present:")
    print(f"  token_name: {pos.get('token_name')}")
    print(f"  total_quantity: {pos.get('total_quantity')}")
    print(f"  features type: {type(pos.get('features'))}")
    if pos.get('features'):
        print(f"\nFeatures keys: {list(pos.get('features', {}).keys())[:10]}")
    
    # Check a few more to see ID patterns
    print("\n" + "="*70)
    print("POSITION ID PATTERNS")
    print("="*70)
    positions = (
        sb.table("lowcap_positions")
        .select("id, token_ticker, token_chain")
        .eq("status", "active")
        .limit(5)
        .execute()
    )
    for p in positions.data:
        print(f"\nTicker: {p.get('token_ticker')}")
        print(f"  Chain: {p.get('token_chain')}")
        print(f"  ID: {p.get('id')}")
        print(f"  ID format: {'UUID' if len(p.get('id', '')) > 20 else 'Short'}")
else:
    print("No active positions found")

