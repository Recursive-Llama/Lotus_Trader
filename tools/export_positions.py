#!/usr/bin/env python3
"""
Export positions from database to JSON file.

Usage:
    python tools/export_positions.py [--status active] [--output positions_backup.json]
    
Options:
    --status: Filter by status (active, watchlist, etc.). Default: all
    --output: Output file path. Default: positions_backup_<timestamp>.json
    --timeframe: Filter by timeframe (1m, 15m, 1h, 4h). Default: all
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from supabase import create_client, Client

def export_positions(
    sb: Client,
    status_filter: str = None,
    timeframe_filter: str = None,
    output_file: str = None
) -> str:
    """
    Export positions to JSON file.
    
    Args:
        sb: Supabase client
        status_filter: Filter by status (e.g., 'active', 'watchlist')
        timeframe_filter: Filter by timeframe (e.g., '1h', '4h')
        output_file: Output file path (if None, auto-generates)
    
    Returns:
        Path to exported file
    """
    # Build query
    query = sb.table("lowcap_positions").select("*")
    
    if status_filter:
        query = query.eq("status", status_filter)
    
    if timeframe_filter:
        query = query.eq("timeframe", timeframe_filter)
    
    # Execute query
    result = query.execute()
    positions = result.data
    
    print(f"Found {len(positions)} positions")
    if status_filter:
        print(f"  Status filter: {status_filter}")
    if timeframe_filter:
        print(f"  Timeframe filter: {timeframe_filter}")
    
    # Generate output filename if not provided
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        status_suffix = f"_{status_filter}" if status_filter else ""
        timeframe_suffix = f"_{timeframe_filter}" if timeframe_filter else ""
        output_file = f"positions_backup{status_suffix}{timeframe_suffix}_{timestamp}.json"
    
    # Ensure output directory exists
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Export to JSON
    with open(output_path, "w") as f:
        json.dump({
            "exported_at": datetime.now().isoformat(),
            "count": len(positions),
            "filters": {
                "status": status_filter,
                "timeframe": timeframe_filter,
            },
            "positions": positions
        }, f, indent=2, default=str)
    
    print(f"✓ Exported to: {output_path.absolute()}")
    return str(output_path.absolute())


def main():
    parser = argparse.ArgumentParser(description="Export positions from database")
    parser.add_argument("--status", help="Filter by status (active, watchlist, etc.)")
    parser.add_argument("--timeframe", help="Filter by timeframe (1m, 15m, 1h, 4h)")
    parser.add_argument("--output", "-o", help="Output file path")
    
    args = parser.parse_args()
    
    # Initialize Supabase
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_KEY environment variables required")
        sys.exit(1)
    
    sb = create_client(url, key)
    
    # Export
    export_positions(
        sb,
        status_filter=args.status,
        timeframe_filter=args.timeframe,
        output_file=args.output
    )


if __name__ == "__main__":
    main()

