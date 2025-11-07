#!/usr/bin/env python3
"""
Extract token registry from lowcap_positions table.
Saves: token_id (id), chain_id (token_chain), contract_address (token_contract)
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables from .env file
load_dotenv()

# Get Supabase credentials from environment
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY (or SUPABASE_SERVICE_ROLE_KEY) must be set")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("Extracting token registry from lowcap_positions table...")

# Query all positions to get unique token data
response = supabase.table("lowcap_positions").select("id, token_chain, token_contract").execute()

# Extract unique tokens (in case there are duplicates)
tokens = {}
for row in response.data:
    token_id = row.get("id")
    chain_id = row.get("token_chain")
    contract_address = row.get("token_contract")
    
    # Use (chain, contract) as unique key to avoid duplicates
    key = f"{chain_id}_{contract_address}"
    if key not in tokens:
        tokens[key] = {
            "token_id": token_id,
            "chain_id": chain_id,
            "contract_address": contract_address
        }

# Convert to list
token_list = list(tokens.values())

# Save to JSON file
output_file = "token_registry_backup.json"
with open(output_file, "w") as f:
    json.dump({
        "extracted_at": datetime.now().isoformat(),
        "total_tokens": len(token_list),
        "tokens": token_list
    }, f, indent=2)

print(f"✅ Extracted {len(token_list)} unique tokens")
print(f"✅ Saved to {output_file}")
print(f"\nSample tokens:")
for token in token_list[:5]:
    print(f"  - {token['token_id']} ({token['chain_id']}): {token['contract_address']}")

