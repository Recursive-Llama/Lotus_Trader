#!/usr/bin/env python3
"""
GeckoTerminal OHLCV backfill job - Clean, Simple Version

- Uses canonical pool from lowcap_positions.features if present
- Otherwise searches pools by mint+chain, prefers native-quoted highest-liquidity
- Supports 15m granularity only (writes to lowcap_price_data_ohlc with timeframe='15m')
- Smart chunking: calculates actual 15m bars needed, makes minimal API calls
- Computes native prices using SOL/USDC reference series
- Idempotent: skips existing timestamps
"""

import os
import sys
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

import requests

from src.utils.supabase_manager import SupabaseManager


logger = logging.getLogger(__name__)


NETWORK_MAP = {
    'solana': 'solana',
    'ethereum': 'ethereum', 
    'base': 'base',
    'bsc': 'bsc',
}

NATIVE_SYMBOL_BY_CHAIN = {
    'solana': 'SOL',
    'ethereum': 'WETH',
    'base': 'WETH', 
    'bsc': 'WBNB',
}

NATIVE_ADDRESS_BY_CHAIN = {
    'solana': 'So11111111111111111111111111111111111111112',
    'ethereum': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
    'base': '0x4200000000000000000000000000000000000006',
    'bsc': '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c',
}

GT_BASE = "https://api.geckoterminal.com/api/v2"
GT_HEADERS = {"accept": "application/json;version=20230302"}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _minute_floor(ts: datetime) -> datetime:
    return ts.replace(second=0, microsecond=0)


def _unix(ts: datetime) -> int:
    return int(ts.timestamp())


def _fetch_gt_pools_by_token(network: str, token_mint: str) -> Dict[str, Any]:
    """Fetch pools for a token from GeckoTerminal"""
    url = f"{GT_BASE}/networks/{network}/tokens/{token_mint}/pools?include=dex,base_token,quote_token&per_page=50"
    resp = requests.get(url, headers=GT_HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _fetch_gt_ohlcv_by_pool(network: str, pool_address: str, limit: int = 1000, to_ts: Optional[int] = None) -> Dict[str, Any]:
    """Fetch OHLCV data for a pool from GeckoTerminal with retry logic"""
    params = [f"limit={limit}"]
    if to_ts is not None:
        params.append(f"to={to_ts}")
    url = f"{GT_BASE}/networks/{network}/pools/{pool_address}/ohlcv/hour?" + "&".join(params)
    
    # Retry with exponential backoff
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=GT_HEADERS, timeout=60)
            if resp.status_code == 404:
                return {"data": None}
            if resp.status_code == 429:
                # Rate limited - wait longer
                wait_time = (2 ** attempt) * 2  # 2, 4, 8 seconds
                logger.warning(f"Rate limited, waiting {wait_time}s (attempt {attempt + 1})")
                time.sleep(wait_time)
                continue
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt == 2:  # Last attempt
                raise e
            wait_time = (2 ** attempt) * 1  # 1, 2, 4 seconds
            logger.warning(f"Request failed, retrying in {wait_time}s: {e}")
            time.sleep(wait_time)
    
    raise Exception("All retry attempts failed")


def _select_canonical_pool_from_gt(chain: str, token_mint: str) -> Optional[Tuple[str, str, str]]:
    """
    Select best pool for a token from GeckoTerminal.
    Returns (pool_address, dex_id, quote_symbol)
    """
    network = NETWORK_MAP.get(chain, chain)
    data = _fetch_gt_pools_by_token(network, token_mint)
    pools = data.get('data', []) or []
    if not pools:
        return None

    native_symbol = NATIVE_SYMBOL_BY_CHAIN.get(chain)
    
    def liquidity_usd(p):
        try:
            return float(p.get('attributes', {}).get('reserve_in_usd') or 0)
        except Exception:
            return 0.0

    # Check if this is the native token
    is_native_token = (token_mint == NATIVE_ADDRESS_BY_CHAIN.get(chain))
    
    if is_native_token:
        # For native tokens: prefer NATIVE/USD pairs
        usd_pairs = []
        others = []
        
        for p in pools:
            name = p.get('attributes', {}).get('name', '')
            base_symbol = name.split('/')[0].strip().upper()
            quote_symbol = name.split('/')[-1].strip().upper()
            
            if base_symbol == native_symbol and quote_symbol in ['USDC', 'USDT', 'USD']:
                usd_pairs.append(p)
            else:
                others.append(p)
        
        chosen = max(usd_pairs, key=liquidity_usd) if usd_pairs else max(others, key=liquidity_usd)
    else:
        # For non-native tokens: prefer TOKEN/NATIVE pairs
        native_quoted = []
        others = []
        
        for p in pools:
            name = p.get('attributes', {}).get('name', '')
            quote_symbol = name.split('/')[-1].strip().upper()
            
            if quote_symbol == native_symbol:
                native_quoted.append(p)
            else:
                others.append(p)
        
        chosen = max(native_quoted, key=liquidity_usd) if native_quoted else max(others, key=liquidity_usd)

    attr = chosen.get('attributes', {})
    pool_address = attr.get('address')
    quote_symbol = (attr.get('name') or '').split('/')[-1].strip().upper()
    dex_id = (chosen.get('relationships', {}).get('dex', {}) or {}).get('data', {}).get('id', '')
    return (pool_address, dex_id, quote_symbol)


def _get_canonical_pool_from_features(features: Optional[Dict[str, Any]]) -> Optional[Tuple[str, str]]:
    """Extract canonical pool from position features"""
    if not features:
        return None
    cp = features.get('canonical_pool') if isinstance(features, dict) else None
    if isinstance(cp, dict):
        pair = cp.get('pair_address')
        dex_id = cp.get('dex_id')
        if pair and dex_id:
            return (pair, dex_id)
    return None


def _update_canonical_pool_features(supabase: SupabaseManager, token_contract: str, chain: str, pool_addr: str, dex_id: str):
    """Update position features with canonical pool info"""
    try:
        # Find latest position for this token/chain
        res = (
            supabase.client
            .table('lowcap_positions')
            .select('id,features,created_at')
            .eq('token_contract', token_contract)
            .eq('token_chain', chain)
            .eq('status', 'active')
            .order('created_at', desc=True)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            # Fallback: latest row regardless of status
            res = (
                supabase.client
                .table('lowcap_positions')
                .select('id,features,created_at')
                .eq('token_contract', token_contract)
                .eq('token_chain', chain)
                .order('created_at', desc=True)
                .limit(1)
                .execute()
            )
            rows = res.data or []
        
        if not rows:
            return
            
        row = rows[0]
        features = row.get('features') or {}
        if not isinstance(features, dict):
            features = {}
        features['canonical_pool'] = {'pair_address': pool_addr, 'dex_id': dex_id}
        supabase.client.table('lowcap_positions').update({'features': features}).eq('id', row['id']).execute()
    except Exception as e:
        logger.warning(f"Failed to persist canonical_pool for {token_contract} on {chain}: {e}")


def _get_existing_timestamps_15m(supabase: SupabaseManager, token_contract: str, chain: str, start_ts: datetime, end_ts: datetime) -> set:
    """Get existing 15m timestamps to avoid duplicates"""
    try:
        result = (
            supabase.client
            .table('lowcap_price_data_ohlc')
            .select('timestamp')
            .eq('token_contract', token_contract)
            .eq('chain', chain)
            .eq('timeframe', '15m')
            .gte('timestamp', start_ts.isoformat())
            .lte('timestamp', end_ts.isoformat())
            .limit(100000)
            .execute()
        )
        data = result.data or []
        return set([row['timestamp'] for row in data])
    except Exception as e:
        logger.warning(f"Failed to load existing 15m timestamps: {e}")
        return set()


def _fetch_sol_reference_15m(chain: str, start_ts: datetime, end_ts: datetime) -> Dict[str, float]:
    """Fetch SOL/USDC 15m reference series for native price conversion"""
    logger.info(f"Starting SOL reference fetch for {chain} from {start_ts} to {end_ts}")
    network = NETWORK_MAP.get(chain, chain)
    native_address = NATIVE_ADDRESS_BY_CHAIN.get(chain)
    
    if not native_address:
        logger.warning(f"No native address for chain {chain}")
        return {}
    
    # Find SOL/USDC pool
    logger.info(f"Finding SOL pool for {native_address}")
    try:
        picked = _select_canonical_pool_from_gt(chain, native_address)
        if not picked:
            logger.warning(f"No SOL pool found for {chain}")
            return {}
        pool_addr, _, _ = picked
        logger.info(f"Found SOL pool: {pool_addr}")
    except Exception as e:
        logger.error(f"Failed to find SOL pool: {e}")
        return {}
    
    sol_map = {}
    try:
        # Fetch SOL data in chunks (max 1000 bars per call)
        window_end = end_ts
        total_minutes = int((end_ts - start_ts).total_seconds() / 60)
        fetched_minutes = 0
        chunk_count = 0
        
        logger.info(f"Starting SOL fetch: {total_minutes} total minutes")
        
        while fetched_minutes < total_minutes:
            chunk_count += 1
            remaining_minutes = total_minutes - fetched_minutes
            chunk_bars = min(500, (remaining_minutes // 60) + 1)
            to_ts = _unix(window_end)
            
            logger.info(f"SOL chunk {chunk_count}: fetching {chunk_bars} bars, to_ts={to_ts}")
            
            data = _fetch_gt_ohlcv_by_pool(network, pool_addr, limit=chunk_bars)
            
            if not data or not data.get('data'):
                logger.warning(f"SOL chunk {chunk_count}: No data returned")
                break
                
            ohlcv_list = (data.get('data', {}) or {}).get('attributes', {}).get('ohlcv_list', []) or []
            if not ohlcv_list:
                logger.warning(f"SOL chunk {chunk_count}: Empty OHLCV list")
                break
            
            logger.info(f"SOL chunk {chunk_count}: Got {len(ohlcv_list)} bars")
            
            # Store 15-minute SOL data directly
            for entry in ohlcv_list:
                try:
                    ts_sec = int(entry[0])
                    close_usd = float(entry[4])  # Close price in USD
                    ts_dt = datetime.fromtimestamp(ts_sec, tz=timezone.utc)
                    ts_iso = ts_dt.isoformat()
                    
                    sol_map[ts_iso] = close_usd
                except Exception as e:
                    logger.debug(f"Skip malformed SOL entry: {e}")
                    continue
            
            # Update progress (1-hour bars)
            chunk_minutes = len(ohlcv_list) * 60
            fetched_minutes += chunk_minutes
            
            logger.info(f"SOL chunk {chunk_count}: fetched {chunk_minutes} minutes, total progress: {fetched_minutes}/{total_minutes}")
            
            # If we consumed a full 1000-bar chunk, pause to respect GT throttling
            if chunk_bars >= 1000:
                logger.info(f"SOL chunk {chunk_count}: Pausing 33s after 1000-bar chunk")
                time.sleep(33)
                logger.info(f"SOL chunk {chunk_count}: Resume after pause")

            # Move to next chunk
            oldest_ts = datetime.fromtimestamp(int(ohlcv_list[-1][0]), tz=timezone.utc)
            window_end = oldest_ts - timedelta(minutes=1)
                
            # Be polite to the API
            time.sleep(0.5)
                
    except Exception as e:
        logger.error(f"Failed to fetch SOL reference: {e}")
    
    # Clean up temporary keys
    clean_sol_map = {k: v for k, v in sol_map.items() if not k.endswith('_latest')}
    
    logger.info(f"SOL reference fetch complete: {len(clean_sol_map)} prices")
    return clean_sol_map


def _build_rows_for_insert_1h(
    token_contract: str,
    chain: str,
    pool_addr: str,
    dex_id: str,
    quote_symbol: str,
    ohlcv_list: List[List[Any]],
    sol_usd_map: Dict[str, float],
) -> List[Dict[str, Any]]:
    """Build database rows for 1h OHLCV data with safeguards"""
    rows = []
    skipped_count = 0
    for entry in ohlcv_list:
        try:
            # [ts, o, h, l, c, v] - GeckoTerminal returns [timestamp, open, high, low, close, volume]
            ts_sec = int(entry[0])
            open_usd = float(entry[1])
            high_usd = float(entry[2])
            low_usd = float(entry[3])
            close_usd = float(entry[4])
            volume_usd = float(entry[5])  # Volume is already in USD from GeckoTerminal
            ts_dt = datetime.fromtimestamp(ts_sec, tz=timezone.utc)
            ts_iso = ts_dt.isoformat()

            # Safeguards: reject invalid prices
            if open_usd <= 0 or high_usd <= 0 or low_usd <= 0 or close_usd <= 0:
                skipped_count += 1
                logger.debug(f"Skip entry {ts_iso}: non-positive USD prices")
                continue
            
            # Check OHLC logic: high >= max(open,close) and low <= min(open,close)
            if high_usd < max(open_usd, close_usd) or low_usd > min(open_usd, close_usd):
                skipped_count += 1
                logger.warning(f"Skip entry {ts_iso}: invalid OHLC relationship (high={high_usd}, low={low_usd}, open={open_usd}, close={close_usd})")
                continue

            # Compute native prices using SOL reference
            sol_usd = sol_usd_map.get(ts_iso, 0.0)
            if sol_usd <= 0:
                skipped_count += 1
                logger.debug(f"Skip entry {ts_iso}: no SOL reference price")
                continue
            
            open_native = open_usd / sol_usd
            high_native = high_usd / sol_usd
            low_native = low_usd / sol_usd
            close_native = close_usd / sol_usd

            # Check native prices are valid (should be positive after conversion)
            if open_native <= 0 or high_native <= 0 or low_native <= 0 or close_native <= 0:
                skipped_count += 1
                logger.warning(f"Skip entry {ts_iso}: non-positive native prices after conversion")
                continue

            # Check for extreme jumps (>100x change) - likely bad data
            # Compare close to open as a sanity check
            if close_usd > 0 and open_usd > 0:
                price_change_ratio = max(close_usd / open_usd, open_usd / close_usd)
                if price_change_ratio > 100.0:
                    skipped_count += 1
                    logger.warning(f"Skip entry {ts_iso}: extreme price jump (ratio={price_change_ratio:.2f})")
                    continue

            rows.append({
                'token_contract': token_contract,
                'chain': chain,
                'timeframe': '1h',
                'timestamp': ts_iso,
                'open_native': open_native,
                'high_native': high_native,
                'low_native': low_native,
                'close_native': close_native,
                'open_usd': open_usd,
                'high_usd': high_usd,
                'low_usd': low_usd,
                'close_usd': close_usd,
                'volume': max(0.0, volume_usd),  # Ensure non-negative volume
                'source': 'geckoterminal'
            })
        except Exception as e:
            skipped_count += 1
            logger.debug(f"Skip malformed OHLCV entry: {e}")
    
    if skipped_count > 0:
        logger.info(f"Skipped {skipped_count} invalid entries during row building")
    
    return rows


def backfill_token_1h(token_contract: str, chain: str, lookback_minutes: int = 10080) -> Dict[str, Any]:
    """
    Backfill 1h OHLCV data for a token from GeckoTerminal.
    
    Args:
        token_contract: Token contract address
        chain: Chain name (e.g., 'solana')
        lookback_minutes: Minutes to look back (default 7 days)
    
    Returns:
        Dict with results summary
    """
    supabase = SupabaseManager()
    chain = (chain or '').lower()
    network = NETWORK_MAP.get(chain, chain)
    
    if network not in NETWORK_MAP.values():
        raise ValueError(f"Unsupported chain/network: {chain}")

    # Get canonical pool from position features
    try:
        pos = supabase.client.table('lowcap_positions').select('features').eq('token_contract', token_contract).eq('token_chain', chain).limit(1).execute()
        features = (pos.data[0].get('features') if pos.data else None) or {}
    except Exception:
        features = {}

    canonical = _get_canonical_pool_from_features(features)
    pool_addr: Optional[str] = None
    dex_id: str = ''
    quote_symbol: str = ''

    if canonical:
        pool_addr, dex_id = canonical
        # Get quote symbol from pool listing
        try:
            data = _fetch_gt_pools_by_token(network, token_contract)
            for p in data.get('data', []) or []:
                if (p.get('attributes', {}) or {}).get('address') == pool_addr:
                    quote_symbol = (p.get('attributes', {}).get('name') or '').split('/')[-1].strip().upper()
                    break
        except Exception:
            quote_symbol = NATIVE_SYMBOL_BY_CHAIN.get(chain, '')
    else:
        # Find canonical pool
        picked = _select_canonical_pool_from_gt(chain, token_contract)
        if not picked:
            raise RuntimeError("No pools found on GeckoTerminal for token")
        pool_addr, dex_id, quote_symbol = picked
        _update_canonical_pool_features(supabase, token_contract, chain, pool_addr, dex_id)

    # Determine time window
    end_dt = _minute_floor(_now_utc() - timedelta(minutes=2))
    start_dt = end_dt - timedelta(minutes=lookback_minutes)

    # Fetch SOL reference series for native price conversion
    sol_usd_map = _fetch_sol_reference_15m(chain, start_dt, end_dt)

    # Calculate how many 15m bars we need
    duration_minutes = int((end_dt - start_dt).total_seconds() / 60)
    bars_needed = (duration_minutes // 15) + 1
    
    logger.info(f"Need {bars_needed} 15m bars for {duration_minutes} minutes")

    # Fetch token OHLCV data
    logger.info("Starting token OHLCV fetch")
    rows_to_insert = []
    newest_inserted_ts = None
    
    try:
        # Fetch token data in chunks (max 1000 bars per call)
        window_end = end_dt
        total_minutes = int((end_dt - start_dt).total_seconds() / 60)
        fetched_minutes = 0
        chunk_count = 0
        
        logger.info(f"Starting token fetch: {total_minutes} total minutes")
        
        while fetched_minutes < total_minutes:
            chunk_count += 1
            remaining_minutes = total_minutes - fetched_minutes
            chunk_bars = min(500, (remaining_minutes // 60) + 1)
            to_ts = _unix(window_end)
            
            logger.info(f"Token chunk {chunk_count}: fetching {chunk_bars} bars, to_ts={to_ts}")
            
            data = _fetch_gt_ohlcv_by_pool(network, pool_addr, limit=chunk_bars)
            
            if not data or not data.get('data'):
                logger.warning(f"Token chunk {chunk_count}: No data returned")
                break
                
            ohlcv_list = (data.get('data', {}) or {}).get('attributes', {}).get('ohlcv_list', []) or []
            if not ohlcv_list:
                logger.warning(f"Token chunk {chunk_count}: Empty OHLCV list")
                break
            
            logger.info(f"Token chunk {chunk_count}: Got {len(ohlcv_list)} bars")
            
            # Build rows for insertion
            batch_rows = _build_rows_for_insert_1h(
                token_contract, chain, pool_addr, dex_id, quote_symbol, ohlcv_list, sol_usd_map
            )
            
            # Deduplicate by timestamp (keep the last occurrence)
            seen_timestamps = set()
            deduplicated_rows = []
            for row in reversed(batch_rows):  # Process in reverse to keep last occurrence
                if row['timestamp'] not in seen_timestamps:
                    deduplicated_rows.append(row)
                    seen_timestamps.add(row['timestamp'])
            batch_rows = list(reversed(deduplicated_rows))  # Restore original order
            
            # Include all rows (will upsert existing ones)
            rows_to_insert.extend(batch_rows)
            
            logger.info(f"Token chunk {chunk_count}: {len(batch_rows)} rows to upsert")
            
            if batch_rows:
                # Track newest timestamp
                for r in batch_rows:
                    ts_dt = datetime.fromisoformat(r['timestamp'])
                    if newest_inserted_ts is None or ts_dt > newest_inserted_ts:
                        newest_inserted_ts = ts_dt
            
            # Update progress
            # Update progress (1-hour bars)
            chunk_minutes = len(ohlcv_list) * 60
            fetched_minutes += chunk_minutes
            
            logger.info(f"Token chunk {chunk_count}: fetched {chunk_minutes} minutes, total progress: {fetched_minutes}/{total_minutes}")
            
            # If we consumed a full 1000-bar chunk, pause to respect GT throttling
            if chunk_bars >= 1000:
                logger.info(f"Token chunk {chunk_count}: Pausing 33s after 1000-bar chunk")
                time.sleep(33)
                logger.info(f"Token chunk {chunk_count}: Resume after pause")

            # Move to next chunk
            oldest_ts = datetime.fromtimestamp(int(ohlcv_list[-1][0]), tz=timezone.utc)
            window_end = oldest_ts - timedelta(minutes=1)
                
            # Be polite to the API
            time.sleep(0.5)

    except Exception as e:
        logger.error(f"Failed to fetch token OHLCV: {e}")
        return {
            'token_contract': token_contract,
            'chain': chain,
            'pool_address': pool_addr,
            'dex_id': dex_id,
            'inserted_rows': 0,
            'window_start': start_dt.isoformat(),
            'window_end': end_dt.isoformat(),
            'error': str(e)
        }

    # Insert rows in batches
    inserted = 0
    if rows_to_insert:
        BATCH_SIZE = 500
        for i in range(0, len(rows_to_insert), BATCH_SIZE):
            chunk = rows_to_insert[i:i+BATCH_SIZE]
            try:
                supabase.client.table('lowcap_price_data_ohlc').upsert(chunk).execute()
                inserted += len(chunk)
                logger.info(f"Upserted batch of {len(chunk)} rows")
            except Exception as e:
                logger.error(f"Insert chunk failed: {e}")

    logger.info(f"Backfill complete: {inserted} rows upserted")

    return {
        'token_contract': token_contract,
        'chain': chain,
        'pool_address': pool_addr,
        'dex_id': dex_id,
        'inserted_rows': inserted,
        'window_start': start_dt.isoformat(),
        'window_end': end_dt.isoformat(),
        'sol_reference_bars': len(sol_usd_map),
    }


def main():
    """Main entry point"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    if len(sys.argv) < 4:
        print("Usage: geckoterminal_backfill.py <chain> <token_contract> <granularity:15m> [lookback_minutes]")
        print("Example: geckoterminal_backfill.py solana METAwkXcqyXKy1AtsSgJ8JiUHwGCafnZL38n3vYmeta 15m 20160")
        sys.exit(1)
    
    chain = sys.argv[1]
    token = sys.argv[2]
    gran = sys.argv[3].lower()
    lookback = int(sys.argv[4]) if len(sys.argv) > 4 else 10080  # Default 7 days
    
    if gran != '15m':
        print("Only 15m granularity is supported")
        sys.exit(1)
    
    try:
        result = backfill_token_15m(token, chain, lookback)
        print(f"Backfill result: {result}")
    except Exception as e:
        logger.error(f"Backfill failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()