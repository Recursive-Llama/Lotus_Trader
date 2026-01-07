#!/usr/bin/env python3
"""
Reinsert tokens as social signals through the actual ingest system.

This script:
1. Loads tokens from backup JSON
2. Formats them correctly for SocialIngestModule
3. Uses the actual _create_social_strand method to create strands
4. Processes them one by one with error handling
"""

import sys
import os
import json
import argparse
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.supabase_manager import SupabaseManager
from intelligence.social_ingest.social_ingest_simple import SocialIngestModule
from llm_integration.openrouter_client import OpenRouterClient


def load_tokens_from_backup(backup_path: str) -> List[Dict[str, Any]]:
    """Load tokens from backup JSON file"""
    with open(backup_path, 'r') as f:
        data = json.load(f)
    
    tokens = []
    for item in data.get('tokens', []):
        tokens.append(item)
    
    return tokens


def format_token_for_ingest(token: Dict[str, Any], curator: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Format token data for SocialIngestModule._create_social_strand
    
    Returns:
        Dict with 'curator', 'message_data', 'verified_token' keys
    """
    # Format curator
    if curator and 'curator_id' in curator:
        curator_id = curator.get('curator_id', 'unknown')
        curator_dict = {
            'curator_id': curator_id,
            'platform': curator.get('platform', 'twitter'),
            'handle': curator.get('handle', f'@{curator_id}'),
            'weight': float(curator.get('weight', 1.0))
        }
    else:
        # Default curator if none provided
        curator_dict = {
            'curator_id': 'system_reinsert',
            'platform': 'system',
            'handle': '@system',
            'weight': 1.0
        }
    
    # Format message data (minimal, since we're reinserting)
    message_data = {
        'text': f"Reinserted token: {token.get('token_ticker', 'UNKNOWN')}",
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'url': ''
    }
    
    # Format verified token (provide defaults for bucket calculations)
    verified_token = {
        'ticker': token.get('token_ticker', 'UNKNOWN'),
        'contract': token.get('token_contract'),
        'chain': token.get('token_chain', 'solana'),
        'price': 0.0,  # Default value
        'volume_24h': 0.0,  # Default value (required for bucket calculation)
        'market_cap': 0.0,  # Default value
        'liquidity': 0.0,  # Default value (required for bucket calculation)
        'dex': 'Unknown',
        'verified': True  # We trust these tokens since they came from positions
    }
    
    return {
        'curator': curator_dict,
        'message_data': message_data,
        'verified_token': verified_token
    }


async def process_token_via_ingest(
    ingest_module: SocialIngestModule,
    token: Dict[str, Any],
    curator: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Process a single token through the ingest system
    
    Returns:
        Created strand or None if failed
    """
    try:
        # Format token data
        formatted = format_token_for_ingest(token, curator)
        
        # Format the strand data (same as _create_social_strand does)
        strand_data = {
            "id": str(uuid.uuid4()),  # Generate UUID for strand ID
            "module": "social_ingest",
            "kind": "social_lowcap",
            "content": {
                "curator_id": formatted['curator']['curator_id'],
                "platform": formatted['curator']['platform'],
                "handle": formatted['curator']['handle'],
                "token": {
                    "ticker": formatted['verified_token']['ticker'],
                    "contract": formatted['verified_token'].get('contract'),
                    "chain": formatted['verified_token']['chain'],
                    "price": formatted['verified_token'].get('price'),
                    "volume_24h": formatted['verified_token'].get('volume_24h'),
                    "market_cap": formatted['verified_token'].get('market_cap'),
                    "liquidity": formatted['verified_token'].get('liquidity'),
                    "dex": formatted['verified_token'].get('dex'),
                    "verified": formatted['verified_token'].get('verified', False)
                },
                "venue": {
                    "dex": formatted['verified_token'].get('dex', 'Unknown'),
                    "chain": formatted['verified_token']['chain'],
                    "liq_usd": formatted['verified_token'].get('liquidity', 0),
                    "vol24h_usd": formatted['verified_token'].get('volume_24h', 0)
                },
                "message": formatted['message_data'],
                "curator_weight": formatted['curator']['weight'],
                "context_slices": {
                    "liquidity_bucket": ingest_module._get_liquidity_bucket(formatted['verified_token'].get('liquidity', 0)),
                    "volume_bucket": ingest_module._get_volume_bucket(formatted['verified_token'].get('volume_24h', 0)),
                    "time_bucket_utc": ingest_module._get_time_bucket(),
                    "sentiment": "positive"
                }
            },
            "tags": ["curated", "social_signal", "dm_candidate", "verified", "reinsert"],
            "status": "active"
        }
        
        # Use insert_strand (synchronous) instead of create_strand (async)
        strand = ingest_module.supabase_manager.insert_strand(strand_data)
        
        return strand
        
    except Exception as e:
        print(f"  ✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    parser = argparse.ArgumentParser(description='Reinsert tokens as social signals via ingest system')
    parser.add_argument('backup_file', help='Path to tokens backup JSON file')
    parser.add_argument('--dry-run', action='store_true', help='Dry run (no database changes)')
    args = parser.parse_args()
    
    print("="*60)
    print("REINSERT: Via Ingest System")
    print("="*60)
    
    # Load tokens
    print(f"\nLoading tokens from: {args.backup_file}")
    tokens = load_tokens_from_backup(args.backup_file)
    print(f"  Total tokens: {len(tokens)}")
    
    # Initialize ingest system
    print("\nInitializing ingest system...")
    supabase_manager = SupabaseManager()
    llm_client = OpenRouterClient()  # May not be needed, but required for init
    
    # Create ingest module (no config needed for our use case)
    ingest_module = SocialIngestModule(
        supabase_manager=supabase_manager,
        llm_client=llm_client,
        config_path=None  # Use defaults
    )
    print("  ✓ Ingest system initialized")
    
    # Process tokens one by one
    print(f"\nProcessing {len(tokens)} tokens one by one...")
    created = 0
    failed = 0
    
    for i, token in enumerate(tokens, 1):
        ticker = token.get('token_ticker', 'UNKNOWN')
        chain = token.get('token_chain', 'unknown')
        curator_info = token.get('curator', {})
        curator_id = curator_info.get('curator_id', 'system') if curator_info else 'system'
        
        print(f"\n[{i}/{len(tokens)}] {ticker} ({chain}) - curator: {curator_id}...", end=" ")
        
        if args.dry_run:
            print("✓ (dry run)")
            created += 1
            continue
        
        # Process via ingest
        try:
            strand = await process_token_via_ingest(ingest_module, token, curator_info if curator_info else None)
            
            if strand:
                strand_id = strand.get('id', 'unknown')
                print(f"✓ (strand: {strand_id[:8]}...)")
                created += 1
            else:
                print("✗")
                failed += 1
        except Exception as e:
            print(f"✗ ERROR: {str(e)}")
            failed += 1
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Tokens processed: {len(tokens)}")
    print(f"  ✓ Created: {created}")
    print(f"  ✗ Failed: {failed}")
    
    if not args.dry_run:
        print("\n✅ Strands created! Decision Maker will process them automatically.")
    else:
        print("\n(Dry run - no changes made)")


if __name__ == '__main__':
    asyncio.run(main())

