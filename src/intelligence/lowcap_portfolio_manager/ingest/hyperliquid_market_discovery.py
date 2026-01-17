"""
Hyperliquid Market Discovery

Discovers all available markets on Hyperliquid and creates watchlist positions.

For Hyperliquid, we want to monitor ALL available markets (closed universe),
not just positions we've created. This is different from Solana where we only
track positions we've opened.

Process:
1. Query Hyperliquid for all markets (main DEX + HIP-3)
2. Filter by requirements (min leverage, activity, etc.)
3. Create/update watchlist positions in database
4. WebSocket ingester discovers from these positions

Requirements (configurable):
- Min leverage: Only markets with leverage >= X
- Activity filter: Only markets with recent trading activity
- Exclude delisted: Skip delisted markets
- HIP-3 filter: Include/exclude HIP-3 markets
"""

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

import requests
from supabase import create_client, Client

logger = logging.getLogger(__name__)

INFO_URL = "https://api.hyperliquid.xyz/info"


class HyperliquidMarketDiscovery:
    """Discovers and manages Hyperliquid markets."""
    
    def __init__(self, sb: Client) -> None:
        """
        Initialize market discovery.
        
        Args:
            sb: Supabase client
        """
        self.sb = sb
        
        # Configuration
        self.min_leverage = float(os.getenv("HL_DISCOVERY_MIN_LEVERAGE", "1.0"))  # 1.0 = no filter
        self.include_hip3 = os.getenv("HL_DISCOVERY_INCLUDE_HIP3", "true").lower() == "true"
        self.include_stock_perps = os.getenv("HL_DISCOVERY_INCLUDE_STOCK_PERPS", "true").lower() == "true"
        self.exclude_delisted = os.getenv("HL_DISCOVERY_EXCLUDE_DELISTED", "true").lower() == "true"
        self.default_timeframe = os.getenv("HL_DISCOVERY_TIMEFRAME", "1h")  # Default timeframe for positions
        
        # Allocation config (same as Decision Maker for consistency)
        self.default_allocation_pct = float(os.getenv("DEFAULT_ALLOCATION_PCT", "15.0"))
        self.timeframe_splits = {
            "15m": 0.20,  # 20% of base allocation
            "1h": 0.40,   # 40% of base allocation
            "4h": 0.40    # 40% of base allocation
        }
        
    def discover_all_markets(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Discover all markets from Hyperliquid.
        
        Returns:
            Dict with keys:
            - "main_dex": List of main DEX markets
            - "hip3": List of HIP-3 markets (grouped by DEX)
        """
        markets = {
            "main_dex": [],
            "hip3": {}
        }
        
        # Discover main DEX markets
        try:
            payload = {"type": "meta"}
            response = requests.post(INFO_URL, json=payload, timeout=10)
            
            if response.status_code == 200:
                meta = response.json()
                universe = meta.get("universe", [])
                
                for asset in universe:
                    if self._should_include_market(asset, is_hip3=False):
                        markets["main_dex"].append({
                            "symbol": asset.get("name"),
                            "max_leverage": asset.get("maxLeverage", 0),
                            "sz_decimals": asset.get("szDecimals", 5),
                            "margin_table_id": asset.get("marginTableId"),
                            "is_delisted": asset.get("isDelisted", False),
                            "only_isolated": asset.get("onlyIsolated", False),
                        })
                
                logger.info("Discovered %d main DEX markets", len(markets["main_dex"]))
        except Exception as e:
            logger.error("Failed to discover main DEX markets: %s", e)
        
        # Discover HIP-3 markets
        if self.include_hip3:
            try:
                payload = {"type": "perpDexs"}
                response = requests.post(INFO_URL, json=payload, timeout=10)
                
                if response.status_code == 200:
                    perp_dexs = response.json()
                    
                    for dex in perp_dexs:
                        if dex is None:
                            continue
                        
                        dex_name = dex.get("name") if isinstance(dex, dict) else dex
                        if not dex_name:
                            continue
                        
                        # Query DEX universe
                        dex_payload = {"type": "meta", "dex": dex_name}
                        dex_response = requests.post(INFO_URL, json=dex_payload, timeout=10)
                        
                        if dex_response.status_code == 200:
                            dex_meta = dex_response.json()
                            dex_universe = dex_meta.get("universe", [])
                            
                            dex_markets = []
                            for asset in dex_universe:
                                if self._should_include_market(asset, is_hip3=True, dex_name=dex_name):
                                    symbol = asset.get("name")  # e.g., "xyz:TSLA"
                                    dex_markets.append({
                                        "symbol": symbol,
                                        "dex": dex_name,
                                        "max_leverage": asset.get("maxLeverage", 0),
                                        "sz_decimals": asset.get("szDecimals", 3),
                                        "is_delisted": asset.get("isDelisted", False),
                                        "only_isolated": asset.get("onlyIsolated", False),
                                    })
                            
                            if dex_markets:
                                markets["hip3"][dex_name] = dex_markets
                                logger.info("Discovered %d markets in HIP-3 DEX '%s'", len(dex_markets), dex_name)
            except Exception as e:
                logger.error("Failed to discover HIP-3 markets: %s", e)
        
        return markets
    
    def _should_include_market(
        self,
        asset: Dict[str, Any],
        is_hip3: bool,
        dex_name: Optional[str] = None
    ) -> bool:
        """Check if market should be included based on filters."""
        # Exclude delisted
        if self.exclude_delisted and asset.get("isDelisted", False):
            return False
        
        # Min leverage filter
        max_leverage = asset.get("maxLeverage", 0)
        if max_leverage < self.min_leverage:
            return False
        
        # HIP-3 stock filter
        if is_hip3:
            symbol = asset.get("name", "")
            # Check if it's a stock perp (e.g., "xyz:TSLA")
            # For now, include all HIP-3 if include_stock_perps is True
            # Could add more sophisticated filtering here
            if not self.include_stock_perps and ":" in symbol:
                # Could check if it's a known stock ticker
                pass
        
        return True
    
    def _get_book_id(self, symbol: str, dex_name: Optional[str] = None) -> str:
        """Determine book_id for a symbol."""
        # HIP-3 stock perps (e.g., "xyz:TSLA")
        if ":" in symbol:
            # Check if it's a stock (could be more sophisticated)
            # For now, assume all HIP-3 with ":" are stock_perps
            # Could check against known stock tickers
            return "stock_perps"
        
        # Main DEX crypto
        return "perps"
    
    def sync_positions(self, markets: Optional[Dict[str, List[Dict[str, Any]]]] = None) -> Dict[str, int]:
        """
        Sync discovered markets to positions table.
        
        Creates/updates watchlist positions for all discovered markets.
        Skips HIP-3 tokens that duplicate main DEX tickers (e.g., hyna:BTC when BTC exists).
        
        Args:
            markets: Discovered markets (if None, will discover)
        
        Returns:
            Dict with counts: {"created": X, "updated": Y, "skipped": Z}
        """
        if markets is None:
            markets = self.discover_all_markets()
        
        stats = {"created": 0, "updated": 0, "skipped": 0, "skipped_duplicate": 0, "errors": 0}
        
        # Get existing positions
        existing = self._get_existing_positions()
        
        # Track main DEX tickers to skip HIP-3 duplicates
        main_dex_tickers: Set[str] = set()
        
        # Process main DEX markets FIRST (to build ticker set)
        for market in markets["main_dex"]:
            symbol = market["symbol"]
            main_dex_tickers.add(symbol)  # Main DEX symbols are just tickers
            book_id = self._get_book_id(symbol)
            
            result = self._sync_position(symbol, book_id, market, existing)
            stats[result] = stats.get(result, 0) + 1
        
        # Process HIP-3 markets, skipping duplicates
        for dex_name, dex_markets in markets["hip3"].items():
            for market in dex_markets:
                symbol = market["symbol"]  # e.g., "hyna:BTC"
                
                # Extract ticker from prefixed symbol
                ticker = symbol.split(":")[-1] if ":" in symbol else symbol
                
                # Skip if this ticker exists in main DEX
                if ticker in main_dex_tickers:
                    logger.debug("Skipping HIP-3 duplicate: %s (main DEX has %s)", symbol, ticker)
                    stats["skipped_duplicate"] = stats.get("skipped_duplicate", 0) + 1
                    continue
                
                book_id = self._get_book_id(symbol, dex_name)
                result = self._sync_position(symbol, book_id, market, existing)
                stats[result] = stats.get(result, 0) + 1
        
        logger.info(
            "Market sync complete: created=%d, updated=%d, skipped=%d, duplicates=%d, errors=%d",
            stats["created"], stats["updated"], stats["skipped"], stats.get("skipped_duplicate", 0), stats["errors"]
        )
        
        return stats
    
    def _get_existing_positions(self) -> Set[str]:
        """Get set of existing Hyperliquid position keys (token_contract:book_id)."""
        try:
            res = (
                self.sb.table("lowcap_positions")
                .select("token_contract,book_id")
                .eq("token_chain", "hyperliquid")
                .in_("book_id", ["perps", "stock_perps"])
                .execute()
            )
            
            # Use token_contract:book_id as key (since same token can be in different books)
            return {f"{row['token_contract']}:{row['book_id']}" for row in (res.data or [])}
        except Exception as e:
            logger.error("Failed to get existing positions: %s", e)
            return set()
    
    def _sync_position(
        self,
        symbol: str,
        book_id: str,
        market: Dict[str, Any],
        existing: Set[str]
    ) -> str:
        """
        Create or update a position for a market.
        
        Returns:
            "created", "updated", "skipped", or "error"
        """
        try:
            position_key = f"{symbol}:{book_id}"
            
            # Check if position exists (for any timeframe)
            if position_key in existing:
                # Update existing position (ensure it's watchlist if not active)
                try:
                    res = (
                        self.sb.table("lowcap_positions")
                        .select("id,status")
                        .eq("token_chain", "hyperliquid")
                        .eq("token_contract", symbol)
                        .eq("book_id", book_id)
                        .limit(1)
                        .execute()
                    )
                    
                    if res.data:
                        pos = res.data[0]
                        # Only update if status is not active (don't override active positions)
                        if pos["status"] not in ["active", "dormant"]:
                            self.sb.table("lowcap_positions").update({
                                "status": "watchlist",
                                "updated_at": datetime.now(timezone.utc).isoformat(),
                            }).eq("id", pos["id"]).execute()
                            return "updated"
                        return "skipped"
                except Exception as e:
                    logger.debug("Failed to update position for %s: %s", symbol, e)
                    return "error"
            else:
                # Create new position(s) for all timeframes (no 1m)
                timeframes = ["15m", "1h", "4h"]
                created_count = 0
                
                for timeframe in timeframes:
                    position_id = str(uuid.uuid4())
                    now = datetime.now(timezone.utc).isoformat()
                    
                    # Extract ticker from symbol
                    ticker = symbol.split(":")[-1] if ":" in symbol else symbol
                    
                    # Calculate timeframe-specific allocation (same as Decision Maker)
                    timeframe_pct = self.timeframe_splits.get(timeframe, 0.40)
                    allocation_pct = self.default_allocation_pct * timeframe_pct
                    
                    # Start as 'dormant' until bars_count >= threshold (matching Solana behavior)
                    # PM Core skips dormant positions; update_bars_count job promotes to watchlist
                    position = {
                        "id": position_id,
                        "token_chain": "hyperliquid",
                        "token_contract": symbol,
                        "token_ticker": ticker,
                        "book_id": book_id,
                        "timeframe": timeframe,
                        "status": "dormant",  # Changed from watchlist - will be promoted after backfill
                        "state": "S4",
                        "total_allocation_pct": allocation_pct,  # Set upfront like Solana
                        "total_allocation_usd": 0.0,
                        "total_quantity": 0.0,
                        "bars_count": 0,  # Will be updated after backfill
                        "bars_threshold": 333,  # Matching Solana threshold
                        "features": {
                            "hyperliquid_metadata": {
                                "max_leverage": market.get("max_leverage", 0),
                                "sz_decimals": market.get("sz_decimals", 5),
                                "discovered_at": now,
                            }
                        },
                    }
                    
                    # Add HIP-3 specific metadata
                    if "dex" in market:
                        position["features"]["hyperliquid_metadata"]["dex"] = market["dex"]
                    
                    try:
                        self.sb.table("lowcap_positions").insert(position).execute()
                        created_count += 1
                    except Exception as e:
                        # Handle duplicate key (position already exists)
                        if "duplicate key" in str(e).lower() or "23505" in str(e):
                            continue
                        raise
                
                if created_count > 0:
                    return "created"
                return "skipped"
        
        except Exception as e:
            logger.error("Failed to sync position for %s: %s", symbol, e)
            return "error"
    
    def run_discovery(self) -> Dict[str, Any]:
        """
        Run full discovery and sync process.
        
        Returns:
            Dict with discovery and sync results
        """
        logger.info("Starting Hyperliquid market discovery...")
        
        markets = self.discover_all_markets()
        
        main_dex_count = len(markets["main_dex"])
        hip3_count = sum(len(m) for m in markets["hip3"].values())
        total_count = main_dex_count + hip3_count
        
        logger.info("Discovered %d markets total (%d main DEX, %d HIP-3)", 
                   total_count, main_dex_count, hip3_count)
        
        sync_stats = self.sync_positions(markets)
        
        return {
            "markets_discovered": {
                "main_dex": main_dex_count,
                "hip3": hip3_count,
                "total": total_count,
            },
            "sync_stats": sync_stats,
        }


# CLI for manual discovery
if __name__ == "__main__":
    import argparse
    
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="Discover and sync Hyperliquid markets")
    parser.add_argument("--dry-run", action="store_true", help="Discover but don't create positions")
    parser.add_argument("--min-leverage", type=float, default=1.0, help="Minimum leverage filter")
    parser.add_argument("--include-hip3", action="store_true", default=True, help="Include HIP-3 markets")
    parser.add_argument("--include-stock-perps", action="store_true", default=True, help="Include stock perps")
    
    args = parser.parse_args()
    
    # Initialize Supabase
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_KEY", "")
    if not supabase_url or not supabase_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
    
    sb = create_client(supabase_url, supabase_key)
    
    discovery = HyperliquidMarketDiscovery(sb)
    discovery.min_leverage = args.min_leverage
    discovery.include_hip3 = args.include_hip3
    discovery.include_stock_perps = args.include_stock_perps
    
    if args.dry_run:
        markets = discovery.discover_all_markets()
        print("\n=== Discovered Markets (DRY RUN) ===")
        print(f"Main DEX: {len(markets['main_dex'])} markets")
        print(f"HIP-3: {sum(len(m) for m in markets['hip3'].values())} markets")
        print("\nSample main DEX markets:")
        for m in markets["main_dex"][:10]:
            print(f"  {m['symbol']} - Leverage: {m['max_leverage']}x")
    else:
        results = discovery.run_discovery()
        print("\n=== Discovery Results ===")
        print(f"Markets discovered: {results['markets_discovered']}")
        print(f"Sync stats: {results['sync_stats']}")

