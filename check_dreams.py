#!/usr/bin/env python3
"""Quick script to check if Dreams exists in positions table"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv("SUPABASE_URL", "")
key = os.getenv("SUPABASE_KEY", "")
if not url or not key:
    print("Missing SUPABASE_URL or SUPABASE_KEY")
    exit(1)

sb = create_client(url, key)

# Search for Dreams (case insensitive)
result = sb.table('lowcap_positions').select('token_ticker, token_contract, token_chain, status').ilike('token_ticker', '%dream%').execute()
print("Dreams positions found:")
if result.data:
    for r in result.data:
        print(f"  {r.get('token_ticker')} - Contract: {r.get('token_contract')} on {r.get('token_chain')} - Status: {r.get('status')}")
else:
    print("  None found")

# Show active positions
print("\nAll active positions:")
active = sb.table('lowcap_positions').select('token_ticker, token_contract, token_chain').eq('status', 'active').execute()
if active.data:
    for a in active.data:
        print(f"  {a.get('token_ticker')} - {a.get('token_contract')[:20]}... on {a.get('token_chain')}")

