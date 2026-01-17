"""
PriceDataReader - Universal abstraction for reading OHLC data from any venue.

Routes queries to the correct table based on (chain, book_id):
- chain="hyperliquid" → hyperliquid_price_data_ohlc
- chain="solana"|"ethereum"|etc. → lowcap_price_data_ohlc

Handles schema differences:
- Hyperliquid: token, ts, open, high, low, close, volume
- Lowcap: token_contract, chain, timestamp, open_usd, high_usd, low_usd, close_usd, volume
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from supabase import Client


class PriceDataReader:
    """Universal interface for reading OHLC data from any venue."""
    
    def __init__(self, sb_client: Client):
        self.sb = sb_client
    
    def get_table_name(self, chain: str, book_id: Optional[str] = None) -> str:
        """
        Determine which table to read from based on chain and book_id.
        
        Args:
            chain: Venue namespace (hyperliquid, solana, ethereum, etc.)
            book_id: Asset class (perps, stock_perps, onchain_crypto, etc.) - optional for now
        
        Returns:
            Table name
        """
        chain_lower = chain.lower()
        
        if chain_lower == 'hyperliquid':
            return 'hyperliquid_price_data_ohlc'
        else:
            # Default: lowcap_price_data_ohlc (Solana, Ethereum, Base, BSC, etc.)
            return 'lowcap_price_data_ohlc'
    
    def _normalize_rows(self, rows: List[Dict[str, Any]], chain: str) -> List[Dict[str, Any]]:
        """
        Normalize rows from different schemas to a common format.
        
        Hyperliquid schema: token, ts, open, high, low, close, volume
        Lowcap schema: token_contract, chain, timestamp, open_usd, high_usd, low_usd, close_usd, volume
        
        Returns normalized format: timestamp, open_usd, high_usd, low_usd, close_usd, volume
        """
        if not rows:
            return []
        
        chain_lower = chain.lower()
        
        if chain_lower == 'hyperliquid':
            # Hyperliquid: map token→token_contract, ts→timestamp, open→open_usd, etc.
            normalized = []
            for row in rows:
                normalized.append({
                    'token_contract': row.get('token'),  # "BTC" or "xyz:TSLA"
                    'chain': chain,
                    'timestamp': row.get('ts'),
                    'open_usd': float(row.get('open', 0)),
                    'high_usd': float(row.get('high', 0)),
                    'low_usd': float(row.get('low', 0)),
                    'close_usd': float(row.get('close', 0)),
                    'volume': float(row.get('volume', 0)),
                })
            return normalized
        else:
            # Lowcap: already in correct format, just ensure types
            normalized = []
            for row in rows:
                normalized.append({
                    'token_contract': row.get('token_contract'),
                    'chain': row.get('chain', chain),
                    'timestamp': row.get('timestamp'),
                    'open_usd': float(row.get('open_usd', 0)),
                    'high_usd': float(row.get('high_usd', 0)),
                    'low_usd': float(row.get('low_usd', 0)),
                    'close_usd': float(row.get('close_usd', 0)),
                    'volume': float(row.get('volume', 0)),
                })
            return normalized
    
    def fetch_recent_ohlc(
        self, 
        contract: str, 
        chain: str, 
        timeframe: str,
        limit: int = 400,
        until_iso: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch recent OHLC bars for any venue.
        
        Args:
            contract: Token contract/symbol (e.g., "BTC" for Hyperliquid, contract address for lowcap)
            chain: Venue namespace (hyperliquid, solana, etc.)
            timeframe: Timeframe (15m, 1h, 4h, etc.)
            limit: Maximum number of bars to fetch
            until_iso: Optional ISO timestamp to fetch up to (for backtesting)
        
        Returns:
            List of normalized OHLC rows with fields: timestamp, open_usd, high_usd, low_usd, close_usd, volume
        """
        table = self.get_table_name(chain)
        chain_lower = chain.lower()
        
        if chain_lower == 'hyperliquid':
            # Hyperliquid: query by token (not token_contract)
            query = (
                self.sb.table(table)
                .select("token, ts, open, high, low, close, volume")
                .eq("token", contract)  # Hyperliquid uses "token" field
                .eq("timeframe", timeframe)
            )
            if until_iso:
                query = query.lte("ts", until_iso)
            query = query.order("ts", desc=True).limit(limit)
        else:
            # Lowcap: query by token_contract and chain
            query = (
                self.sb.table(table)
                .select("token_contract, chain, timestamp, open_usd, high_usd, low_usd, close_usd, volume")
                .eq("token_contract", contract)
                .eq("chain", chain)
                .eq("timeframe", timeframe)
            )
            if until_iso:
                query = query.lte("timestamp", until_iso)
            query = query.order("timestamp", desc=True).limit(limit)
        
        rows = query.execute().data or []
        
        # DEBUG LOGGING
        if chain_lower == 'hyperliquid' and len(rows) == 0:
            import logging
            import logging
            logging.getLogger("HL_DEBUG").debug(f"PriceDataReader: No rows found for {contract} {timeframe}. Query table: {table}")

        # Reverse to chronological order (oldest first) for consistency
        rows = list(reversed(rows))
        
        return self._normalize_rows(rows, chain)
    
    def fetch_ohlc_since(
        self,
        contract: str,
        chain: str,
        timeframe: str,
        since_iso: str,
        limit: int = 500
    ) -> List[Dict[str, Any]]:
        """
        Fetch OHLC bars since a timestamp.
        
        Args:
            contract: Token contract/symbol
            chain: Venue namespace
            timeframe: Timeframe
            since_iso: ISO timestamp to fetch from
            limit: Maximum number of bars
        
        Returns:
            List of normalized OHLC rows
        """
        table = self.get_table_name(chain)
        chain_lower = chain.lower()
        
        if chain_lower == 'hyperliquid':
            query = (
                self.sb.table(table)
                .select("token, ts, open, high, low, close, volume")
                .eq("token", contract)
                .eq("timeframe", timeframe)
                .gte("ts", since_iso)
                .order("ts", desc=False)
                .limit(limit)
            )
        else:
            query = (
                self.sb.table(table)
                .select("token_contract, chain, timestamp, open_usd, high_usd, low_usd, close_usd, volume")
                .eq("token_contract", contract)
                .eq("chain", chain)
                .eq("timeframe", timeframe)
                .gte("timestamp", since_iso)
                .order("timestamp", desc=False)
                .limit(limit)
            )
        
        rows = query.execute().data or []
        return self._normalize_rows(rows, chain)
    
    def fetch_bars_for_geometry(
        self,
        contract: str,
        chain: str,
        timeframe: str,
        end: datetime,
        lookback_minutes: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch bars for geometry building (with optional lookback).
        
        Args:
            contract: Token contract/symbol
            chain: Venue namespace
            timeframe: Timeframe
            end: End timestamp
            lookback_minutes: Optional lookback window
        
        Returns:
            List of normalized OHLC rows
        """
        table = self.get_table_name(chain)
        chain_lower = chain.lower()
        end_iso = end.isoformat()
        
        if chain_lower == 'hyperliquid':
            query = (
                self.sb.table(table)
                .select("token, ts, open, high, low, close, volume")
                .eq("token", contract)
                .eq("timeframe", timeframe)
                .lte("ts", end_iso)
                .order("ts", desc=True)
            )
            if lookback_minutes:
                from datetime import timedelta
                start = end - timedelta(minutes=lookback_minutes)
                query = query.gte("ts", start.isoformat())
        else:
            query = (
                self.sb.table(table)
                .select("token_contract, chain, timestamp, open_usd, high_usd, low_usd, close_usd, volume")
                .eq("token_contract", contract)
                .eq("chain", chain)
                .eq("timeframe", timeframe)
                .lte("timestamp", end_iso)
                .order("timestamp", desc=True)
            )
            if lookback_minutes:
                from datetime import timedelta
                start = end - timedelta(minutes=lookback_minutes)
                query = query.gte("timestamp", start.isoformat())
        
        rows = query.limit(9999).execute().data or []
        # Reverse to chronological order for geometry
        rows = list(reversed(rows))
        return self._normalize_rows(rows, chain)
    
    def latest_close(
        self,
        contract: str,
        chain: str,
        timeframe: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get latest close price and low for a token.
        
        Args:
            contract: Token contract/symbol
            chain: Venue namespace
            timeframe: Timeframe
        
        Returns:
            Dict with 'timestamp', 'close', 'low' or None
        """
        rows = self.fetch_recent_ohlc(contract, chain, timeframe, limit=1)
        if not rows:
            return None
        
        row = rows[-1]  # Last row (most recent)
        return {
            'ts': row.get('timestamp'),
            'close': row.get('close_usd'),
            'low': row.get('low_usd'),
        }

