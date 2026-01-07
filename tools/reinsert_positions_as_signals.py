#!/usr/bin/env python3
"""
Export tokens from positions, then later reinsert them as social signals.

Two-step process:
1. EXPORT: Extract tokens to JSON file (run before database wipe)
2. REINSERT: Read from JSON file and create social signals (run after restart)

Usage:
    # Step 1: Export tokens (before wipe)
    python tools/reinsert_positions_as_signals.py export --status active --output tokens_backup.json
    
    # Step 2: Reinsert tokens (after restart)
    python tools/reinsert_positions_as_signals.py reinsert tokens_backup.json [--auto-process]
    
Options:
    export:
        --status: Filter by status (active, watchlist, etc.). Default: all
        --output: Output JSON file. Default: tokens_backup_<timestamp>.json
    
    reinsert:
        --auto-process: Automatically trigger learning system to process signals
        --dry-run: Show what would happen without making changes
"""

import os
import sys
import json
import argparse
import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from supabase import create_client, Client

# Default curator for reinserted signals (you can change this)
DEFAULT_CURATOR = {
    "id": "system_reinsert",
    "name": "System Reinsert",
    "platform": "system",
    "handle": "@system_reinsert",
    "weight": 1.0,
    "priority": 1,
    "tags": ["system", "reinsert"]
}


def get_unique_tokens(sb: Client, status_filter: str = None) -> List[Dict[str, Any]]:
    """
    Get unique tokens from positions, including curator information.
    
    Returns list of {token_contract, token_chain, token_ticker, curator} dicts.
    For tokens with multiple curators, picks the primary one (is_primary=True) or first one.
    """
    query = sb.table("lowcap_positions").select("token_contract,token_chain,token_ticker,curator_sources")
    
    if status_filter:
        query = query.eq("status", status_filter)
    
    result = query.execute()
    positions = result.data
    
    # Get unique tokens (by contract + chain), preserving curator info
    seen = {}
    
    for pos in positions:
        contract = pos.get("token_contract")
        chain = pos.get("token_chain")
        ticker = pos.get("token_ticker", contract[:20] if contract else "UNKNOWN")
        curator_sources = pos.get("curator_sources") or []
        
        if not contract or not chain:
            continue
        
        key = (contract, chain)
        
        # If we haven't seen this token, or if this position has a primary curator we haven't captured
        if key not in seen:
            # Find primary curator (is_primary=True) or first curator
            curator = None
            if isinstance(curator_sources, list) and len(curator_sources) > 0:
                # Look for primary curator first
                primary = next((c for c in curator_sources if c.get("is_primary")), None)
                curator = primary or curator_sources[0]
            
            seen[key] = {
                "token_contract": contract,
                "token_chain": chain,
                "token_ticker": ticker,
                "curator": curator  # Can be None if no curator_sources
            }
        else:
            # Token already seen - check if this position has a primary curator we should use instead
            if isinstance(curator_sources, list) and len(curator_sources) > 0:
                primary = next((c for c in curator_sources if c.get("is_primary")), None)
                if primary and (not seen[key]["curator"] or not seen[key]["curator"].get("is_primary")):
                    seen[key]["curator"] = primary
    
    return list(seen.values())


def delete_positions(sb: Client, tokens: List[Dict[str, Any]], dry_run: bool = False) -> int:
    """
    Delete positions for given tokens.
    
    Returns number of positions deleted.
    """
    if dry_run:
        print(f"  [DRY RUN] Would delete positions for {len(tokens)} tokens")
        return 0
    
    deleted_count = 0
    
    for token in tokens:
        contract = token["token_contract"]
        chain = token["token_chain"]
        
        # Delete all positions for this token (all timeframes)
        result = sb.table("lowcap_positions").delete().eq(
            "token_contract", contract
        ).eq(
            "token_chain", chain
        ).execute()
        
        deleted_count += len(result.data) if result.data else 0
    
    return deleted_count


def create_social_signal_strand(
    sb: Client,
    token: Dict[str, Any],
    curator: Dict[str, Any] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Create a social_lowcap strand for a token (as if someone mentioned it).
    
    This mimics what social_ingest would create, but with minimal data.
    
    Args:
        token: Token dict with token_contract, token_chain, token_ticker, and optionally curator
        curator: Curator dict (if None, uses token.curator or DEFAULT_CURATOR)
    """
    # Use curator from token if available, otherwise use provided or default
    if curator is None:
        curator = token.get("curator") or DEFAULT_CURATOR
    
    # If curator is from curator_sources (has curator_id, confidence, etc.), convert to curator format
    if curator and "curator_id" in curator:
        curator_id = curator.get("curator_id", "unknown")
        
        # Try to look up curator from database for complete info
        try:
            result = sb.table("curators").select("*").eq("curator_id", curator_id).limit(1).execute()
            if result.data:
                db_curator = result.data[0]
                # Use database info (has proper platform, handle, etc.)
                curator_info = {
                    "id": curator_id,
                    "name": db_curator.get("name", curator_id.replace("_", " ").title()),
                    "platform": "twitter" if db_curator.get("twitter_handle") else "telegram" if db_curator.get("telegram_handle") else "twitter",
                    "handle": db_curator.get("twitter_handle") or db_curator.get("telegram_handle") or f"@{curator_id}",
                    "weight": db_curator.get("final_weight", curator.get("confidence", 1.0)),
                    "priority": 1,
                    "tags": db_curator.get("tags", []) + ["reinsert"]
                }
            else:
                # Curator not in database - use defaults with confidence as weight
                curator_info = {
                    "id": curator_id,
                    "name": curator_id.replace("_", " ").title(),
                    "platform": "twitter",  # Default assumption
                    "handle": f"@{curator_id}",
                    "weight": curator.get("confidence", 1.0),  # Use confidence as weight
                    "priority": 1,
                    "tags": ["reinsert", "system"]
                }
        except Exception as e:
            # If lookup fails, use defaults
            curator_info = {
                "id": curator_id,
                "name": curator_id.replace("_", " ").title(),
                "platform": "twitter",
                "handle": f"@{curator_id}",
                "weight": curator.get("confidence", 1.0),
                "priority": 1,
                "tags": ["reinsert", "system"]
            }
        
        curator = curator_info
    
    now = datetime.now(timezone.utc)
    contract = token["token_contract"]
    chain = token["token_chain"]
    ticker = token["token_ticker"]
    
    # Generate unique ID for the strand (same format as social_ingest)
    strand_id = str(uuid.uuid4())
    
    # Build minimal social_lowcap strand
    # This structure matches what social_ingest_basic creates
    strand = {
        "id": strand_id,
        "module": "social_ingest",
        "kind": "social_lowcap",
        "symbol": ticker,  # Required field
        "timeframe": None,  # Not applicable for social signals
        "session_bucket": f"social_{now.strftime('%Y%m%d_%H')}",  # Hourly session
        "target_agent": "decision_maker_lowcap",
        "status": "active",
        "tags": ["curated", "social_signal", "dm_candidate", "verified", "system_reinsert"],
        "signal_pack": {
            "token": {
                "ticker": ticker,
                "contract": contract,
                "chain": chain,
                # Minimal data - Decision Maker will verify/fetch more if needed
                "price": 0.0,  # Will be fetched by DM
                "volume_24h": 0,  # Will be fetched by DM
                "market_cap": 0,  # Will be fetched by DM
                "liquidity": 0,  # Will be fetched by DM
                "dex": "jupiter" if chain == "solana" else "uniswap",
                "verified": True
            },
            "venue": {
                "dex": "jupiter" if chain == "solana" else "uniswap",
                "chain": chain,
                "liq_usd": 0,  # Will be fetched by DM
                "vol24h_usd": 0  # Will be fetched by DM
            },
            "curator": curator,
            "trading_signals": {
                "action": "buy",
                "timing": "immediate",
                "confidence": 0.8,
            },
            "intent_analysis": {
                "intent_analysis": {
                    "intent_type": "new_discovery",
                    "allocation_multiplier": 1.0,
                    "confidence": 0.8,
                }
            },
        },
        "module_intelligence": {
            "social_signal": {
                "message": {
                    "text": f"System reinsert: {ticker}",
                    "timestamp": now.isoformat(),
                    "url": f"https://system/reinsert/{ticker}",
                    "has_image": False,
                    "has_chart": False,
                }
            }
        },
        "content": {
            "summary": f"System reinsert signal for {ticker}",
            "curator_id": curator["id"],
            "platform": curator["platform"],
            "token_ticker": ticker,
            "source_strand_id": None,  # No parent signal
        },
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    
    if dry_run:
        print(f"  [DRY RUN] Would create social_lowcap strand for {ticker}")
        return strand
    
    # Insert strand
    result = sb.table("ad_strands").insert(strand).execute()
    
    if result.data:
        created = result.data[0]
        print(f"  ✓ Created social_lowcap strand for {ticker} (id: {created.get('id', '?')[:8]}...)")
        return created
    else:
        print(f"  ✗ Failed to create strand for {ticker}")
        return None


async def process_signals_with_learning_system(sb: Client, strand_ids: List[str]):
    """
    Trigger learning system to process the created signals.
    
    This will:
    1. Learning system picks up social_lowcap strands
    2. Routes to Decision Maker
    3. Decision Maker creates positions
    4. Triggers backfill
    """
    try:
        from intelligence.universal_learning.universal_learning_system import UniversalLearningSystem
        from utils.supabase_manager import SupabaseManager
        
        print("\n🔄 Processing signals with learning system...")
        
        supabase_manager = SupabaseManager()
        learning_system = UniversalLearningSystem(
            supabase_manager=supabase_manager,
            llm_client=None,  # Not needed for routing
            llm_config=None,
        )
        
        # Fetch the strands we created
        for strand_id in strand_ids:
            result = sb.table("ad_strands").select("*").eq("id", strand_id).execute()
            if result.data:
                strand = result.data[0]
                await learning_system.process_strand_event(strand)
                print(f"  ✓ Processed strand {strand_id[:8]}...")
        
        print("✅ Learning system processing complete")
        print("   (Decision Maker will create positions and trigger backfill)")
        
    except ImportError as e:
        print(f"⚠️  Could not import learning system: {e}")
        print("   Signals created but not processed. They will be picked up by the scheduled learning system.")
    except Exception as e:
        print(f"⚠️  Error processing signals: {e}")
        print("   Signals created but not processed. They will be picked up by the scheduled learning system.")


def export_tokens(sb: Client, status_filter: str = None, output_file: str = None) -> str:
    """
    Export tokens to JSON file (Step 1: before database wipe).
    
    Returns path to exported file.
    """
    print("="*60)
    print("EXPORT: Extract Tokens from Positions")
    print("="*60)
    
    # Get unique tokens
    print("\nExtracting unique tokens from positions...")
    tokens = get_unique_tokens(sb, status_filter=status_filter)
    print(f"  Found {len(tokens)} unique tokens")
    
    if status_filter:
        print(f"  (Filtered by status: {status_filter})")
    
    if len(tokens) == 0:
        print("  No tokens found. Exiting.")
        sys.exit(0)
    
    # Show tokens
    print("\n  Tokens to export:")
    for i, token in enumerate(tokens[:10], 1):  # Show first 10
        curator_info = ""
        if token.get("curator"):
            curator_id = token["curator"].get("curator_id", "unknown")
            curator_info = f" (curator: {curator_id})"
        print(f"    {i}. {token['token_ticker']} ({token['token_chain']}) - {token['token_contract'][:30]}...{curator_info}")
    if len(tokens) > 10:
        print(f"    ... and {len(tokens) - 10} more")
    
    # Count tokens with/without curators
    tokens_with_curator = sum(1 for t in tokens if t.get("curator"))
    print(f"\n  Curator info: {tokens_with_curator}/{len(tokens)} tokens have curator information")
    
    # Generate output filename if not provided
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        status_suffix = f"_{status_filter}" if status_filter else ""
        output_file = f"tokens_backup{status_suffix}_{timestamp}.json"
    
    # Save to file
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump({
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "count": len(tokens),
            "status_filter": status_filter,
            "tokens": tokens
        }, f, indent=2)
    
    print(f"\n✓ Exported {len(tokens)} tokens to: {output_path.absolute()}")
    print("\nNext steps:")
    print("  1. Delete database / restart system")
    print("  2. When ready, run: python tools/reinsert_positions_as_signals.py reinsert " + output_file)
    
    return str(output_path.absolute())


def reinsert_tokens(sb: Client, input_file: str, auto_process: bool = False, dry_run: bool = False):
    """
    Reinsert tokens from JSON file as social signals (Step 2: after restart).
    """
    print("="*60)
    print("REINSERT: Create Social Signals from Tokens")
    print("="*60)
    
    if dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made\n")
    
    # Load tokens from file
    if not Path(input_file).exists():
        print(f"ERROR: File not found: {input_file}")
        sys.exit(1)
    
    with open(input_file, "r") as f:
        data = json.load(f)
    
    tokens = data.get("tokens", [])
    exported_at = data.get("exported_at", "unknown")
    
    print(f"\nLoading tokens from: {input_file}")
    print(f"  Exported at: {exported_at}")
    print(f"  Total tokens: {len(tokens)}")
    
    if len(tokens) == 0:
        print("  No tokens in file. Exiting.")
        return
    
    # Show tokens
    print("\n  Tokens to reinsert:")
    for i, token in enumerate(tokens[:10], 1):
        curator_info = ""
        if token.get("curator"):
            curator_id = token["curator"].get("curator_id", "unknown")
            curator_info = f" (curator: {curator_id})"
        print(f"    {i}. {token['token_ticker']} ({token['token_chain']}) - {token['token_contract'][:30]}...{curator_info}")
    if len(tokens) > 10:
        print(f"    ... and {len(tokens) - 10} more")
    
    # Count tokens with/without curators
    tokens_with_curator = sum(1 for t in tokens if t.get("curator"))
    print(f"\n  Curator info: {tokens_with_curator}/{len(tokens)} tokens have curator information")
    
    # Create social signals one by one with error handling
    print(f"\nCreating social_lowcap strands for {len(tokens)} tokens (one by one)...")
    created_strands = []
    failed_tokens = []
    
    for i, token in enumerate(tokens, 1):
        ticker = token.get("token_ticker", "UNKNOWN")
        print(f"\n[{i}/{len(tokens)}] Processing {ticker}...", end=" ")
        
        try:
            strand = create_social_signal_strand(sb, token, dry_run=dry_run)
            if strand and not dry_run:
                strand_id = strand.get("id") if isinstance(strand, dict) else None
                if strand_id:
                    created_strands.append(strand_id)
                    print(f"✓")
                else:
                    print(f"✗ (no ID returned)")
                    failed_tokens.append(ticker)
            elif dry_run:
                print(f"✓ (dry run)")
            else:
                print(f"✗ (strand creation failed)")
                failed_tokens.append(ticker)
        except Exception as e:
            print(f"✗ ERROR: {str(e)[:50]}")
            failed_tokens.append(ticker)
            # Continue with next token even if this one fails
    
    if not dry_run:
        print(f"\n  ✓ Created {len(created_strands)} social_lowcap strands")
        if failed_tokens:
            print(f"  ✗ Failed: {len(failed_tokens)} tokens")
            print(f"    Failed tokens: {', '.join(failed_tokens[:10])}")
            if len(failed_tokens) > 10:
                print(f"    ... and {len(failed_tokens) - 10} more")
    
    # Process with learning system (optional)
    if auto_process and not dry_run and created_strands:
        asyncio.run(process_signals_with_learning_system(sb, created_strands))
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Tokens loaded: {len(tokens)}")
    if not dry_run:
        print(f"Social signals created: {len(created_strands)}")
        if auto_process:
            print("Learning system: Processed (positions should be created)")
        else:
            print("Learning system: Not processed (signals will be picked up by scheduled job)")
    else:
        print("(Dry run - no changes made)")
    
    print("\n✅ Complete!")
    if not dry_run:
        print("\nNext steps:")
        if auto_process:
            print("  ✓ Positions should be created automatically")
        else:
            print("  1. Wait for scheduled learning system to process signals")
        print("  2. Decision Maker will create positions and trigger backfill")
        print("  3. Positions will start as 'dormant' or 'watchlist' based on bars_count")


def main():
    parser = argparse.ArgumentParser(
        description="Export tokens from positions, then reinsert as social signals",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Step 1: Export tokens (before database wipe)
  python tools/reinsert_positions_as_signals.py export --status active --output my_tokens.json
  
  # Step 2: Reinsert tokens (after restart)
  python tools/reinsert_positions_as_signals.py reinsert my_tokens.json --auto-process
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export tokens to JSON file (before wipe)")
    export_parser.add_argument("--status", help="Filter by status (active, watchlist, etc.)")
    export_parser.add_argument("--output", "-o", help="Output JSON file")
    
    # Reinsert command
    reinsert_parser = subparsers.add_parser("reinsert", help="Reinsert tokens from JSON file (after restart)")
    reinsert_parser.add_argument("input_file", help="JSON file with tokens to reinsert")
    reinsert_parser.add_argument("--auto-process", action="store_true", help="Automatically trigger learning system")
    reinsert_parser.add_argument("--dry-run", action="store_true", help="Show what would happen without making changes")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Initialize Supabase
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_KEY environment variables required")
        sys.exit(1)
    
    sb = create_client(url, key)
    
    # Run command
    if args.command == "export":
        export_tokens(sb, status_filter=args.status, output_file=args.output)
    elif args.command == "reinsert":
        reinsert_tokens(sb, args.input_file, auto_process=args.auto_process, dry_run=args.dry_run)


if __name__ == "__main__":
    main()

