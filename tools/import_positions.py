#!/usr/bin/env python3
"""
Import positions from JSON file back into database.

Usage:
    python tools/import_positions.py positions_backup.json [--dry-run]
    
Options:
    --dry-run: Show what would be imported without actually importing
    --skip-existing: Skip positions that already exist (by unique constraint)
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from supabase import create_client, Client

def import_positions(
    sb: Client,
    input_file: str,
    dry_run: bool = False,
    skip_existing: bool = False
) -> dict:
    """
    Import positions from JSON file.
    
    Args:
        sb: Supabase client
        input_file: Path to JSON backup file
        dry_run: If True, don't actually insert, just show what would be imported
        skip_existing: If True, skip positions that already exist
    
    Returns:
        Dict with import statistics
    """
    # Load JSON file
    with open(input_file, "r") as f:
        data = json.load(f)
    
    positions = data.get("positions", [])
    exported_at = data.get("exported_at", "unknown")
    
    print(f"Loading positions from: {input_file}")
    print(f"  Exported at: {exported_at}")
    print(f"  Total positions: {len(positions)}")
    
    if dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made\n")
    
    # Statistics
    stats = {
        "total": len(positions),
        "imported": 0,
        "skipped": 0,
        "errors": 0,
        "errors_detail": []
    }
    
    # Import each position
    for i, pos in enumerate(positions, 1):
        token_ticker = pos.get("token_ticker", pos.get("token_contract", "?")[:20])
        timeframe = pos.get("timeframe", "?")
        status = pos.get("status", "?")
        
        print(f"[{i}/{len(positions)}] {token_ticker}/{pos.get('token_chain', '?')} tf={timeframe} status={status}", end=" ... ")
        
        # Remove id to let database generate new one (or keep it if you want to preserve IDs)
        # For restart, we typically want new IDs, but preserve the unique constraint
        import_data = {k: v for k, v in pos.items() if k != "id"}
        
        # Also remove timestamps to let database set them fresh
        for ts_field in ["created_at", "updated_at"]:
            import_data.pop(ts_field, None)
        
        if dry_run:
            print("✓ (would import)")
            stats["imported"] += 1
            continue
        
        try:
            # Check if exists (if skip_existing)
            if skip_existing:
                existing = sb.table("lowcap_positions").select("id").eq(
                    "token_contract", pos["token_contract"]
                ).eq(
                    "token_chain", pos["token_chain"]
                ).eq(
                    "timeframe", pos["timeframe"]
                ).execute()
                
                if existing.data:
                    print("⊘ (skipped - already exists)")
                    stats["skipped"] += 1
                    continue
            
            # Insert position
            result = sb.table("lowcap_positions").insert(import_data).execute()
            
            if result.data:
                print("✓ (imported)")
                stats["imported"] += 1
            else:
                print("✗ (no data returned)")
                stats["errors"] += 1
                stats["errors_detail"].append(f"{token_ticker}/{timeframe}: No data returned")
        
        except Exception as e:
            error_msg = str(e)
            # Check if it's a unique constraint violation (position already exists)
            if "unique constraint" in error_msg.lower() or "duplicate key" in error_msg.lower():
                print("⊘ (skipped - already exists)")
                stats["skipped"] += 1
            else:
                print(f"✗ (error: {error_msg[:50]})")
                stats["errors"] += 1
                stats["errors_detail"].append(f"{token_ticker}/{timeframe}: {error_msg}")
    
    # Print summary
    print("\n" + "="*60)
    print("IMPORT SUMMARY")
    print("="*60)
    print(f"Total positions: {stats['total']}")
    print(f"✓ Imported: {stats['imported']}")
    print(f"⊘ Skipped: {stats['skipped']}")
    print(f"✗ Errors: {stats['errors']}")
    
    if stats['errors'] > 0:
        print("\nErrors:")
        for err in stats['errors_detail'][:10]:  # Show first 10
            print(f"  - {err}")
        if len(stats['errors_detail']) > 10:
            print(f"  ... and {len(stats['errors_detail']) - 10} more")
    
    return stats


def main():
    parser = argparse.ArgumentParser(description="Import positions from JSON backup")
    parser.add_argument("input_file", help="Path to JSON backup file")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be imported without importing")
    parser.add_argument("--skip-existing", action="store_true", help="Skip positions that already exist")
    
    args = parser.parse_args()
    
    # Check file exists
    if not Path(args.input_file).exists():
        print(f"ERROR: File not found: {args.input_file}")
        sys.exit(1)
    
    # Initialize Supabase
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_KEY environment variables required")
        sys.exit(1)
    
    sb = create_client(url, key)
    
    # Import
    stats = import_positions(
        sb,
        args.input_file,
        dry_run=args.dry_run,
        skip_existing=args.skip_existing
    )
    
    if stats["errors"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()

