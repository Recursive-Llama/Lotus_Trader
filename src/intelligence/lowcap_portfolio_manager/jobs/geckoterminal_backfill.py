#!/usr/bin/env python3
"""
GeckoTerminal OHLCV backfill job - Clean, Simple Version

- Uses canonical pool from lowcap_positions.features if present
- Otherwise searches pools by mint+chain, prefers native-quoted highest-liquidity
- Supports all timeframes (1m, 15m, 1h, 4h) - writes to lowcap_price_data_ohlc
- Fetches 666 bars per timeframe (target), minimum 333 bars (single API call per timeframe)
- Uses USD prices only (native prices set to 0.0, convert on-demand when needed)
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


def _fetch_gt_ohlcv_by_pool(network: str, pool_address: str, limit: int = 1000, to_ts: Optional[int] = None, timeframe: str = 'hour', aggregate: Optional[int] = None) -> Dict[str, Any]:
    """
    Fetch OHLCV data for a pool from GeckoTerminal with retry logic
    
    Args:
        network: Network name (solana, ethereum, base, bsc)
        pool_address: Pool address
        limit: Maximum number of bars to fetch
        to_ts: Unix timestamp to fetch up to (optional)
        timeframe: Timeframe for OHLCV data ('minute', 'hour', 'day')
        aggregate: Aggregation interval (1, 5, 15 for minute; 1, 4, 12 for hour)
    
    Returns:
        JSON response from GeckoTerminal API
    """
    params = [f"limit={limit}"]
    if to_ts is not None:
        params.append(f"to={to_ts}")
    if aggregate is not None:
        params.append(f"aggregate={aggregate}")
    url = f"{GT_BASE}/networks/{network}/pools/{pool_address}/ohlcv/{timeframe}?" + "&".join(params)
    
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


def _build_rows_for_insert(
    token_contract: str,
    chain: str,
    pool_addr: str,
    dex_id: str,
    quote_symbol: str,
    ohlcv_list: List[List[Any]],
    timeframe: str,
    window_start: datetime,
    window_end: datetime,
) -> List[Dict[str, Any]]:
    """
    Build database rows for OHLCV data using USD prices.
    Native prices are set to 0.0 (convert on-demand when needed).
    """
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

            # Check for extreme jumps (>100x change) - likely bad data
            # Compare close to open as a sanity check
            if close_usd > 0 and open_usd > 0:
                price_change_ratio = max(close_usd / open_usd, open_usd / close_usd)
                if price_change_ratio > 100.0:
                    skipped_count += 1
                    logger.warning(f"Skip entry {ts_iso}: extreme price jump (ratio={price_change_ratio:.2f})")
                    continue

            # Native prices: Set to 0.0 (convert on-demand when needed for display/reporting)
            open_native = 0.0
            high_native = 0.0
            low_native = 0.0
            close_native = 0.0

            rows.append({
                'token_contract': token_contract,
                'chain': chain,
                'timeframe': timeframe,
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


def _update_bars_count_after_backfill(supabase: SupabaseManager, token_contract: str, chain: str, timeframe: str, inserted_rows: int):
    """
    Update bars_count for positions after backfill completes
    
    Args:
        supabase: Supabase manager instance
        token_contract: Token contract address
        chain: Chain name
        timeframe: Timeframe (1m, 15m, 1h, 4h)
        inserted_rows: Number of rows inserted (used to update bars_count)
    """
    try:
        # Get current bars_count for this token/chain/timeframe
        result = supabase.client.table('lowcap_price_data_ohlc').select(
            'timestamp', count='exact'
        ).eq('token_contract', token_contract).eq('chain', chain).eq('timeframe', timeframe).execute()
        
        bars_count = result.count if hasattr(result, 'count') else len(result.data) if result.data else 0
        
        # Update all positions for this token/chain/timeframe
        positions_result = supabase.client.table('lowcap_positions').select('id,status').eq(
            'token_contract', token_contract
        ).eq('token_chain', chain).eq('timeframe', timeframe).execute()
        
        if positions_result.data:
            for pos in positions_result.data:
                position_id = pos['id']
                current_status = pos.get('status', 'dormant')
                
                # Update bars_count
                supabase.client.table('lowcap_positions').update({
                    'bars_count': bars_count
                }).eq('id', position_id).execute()
                
                # Auto-flip dormant → watchlist if bars_count >= 333 (minimum required)
                if current_status == 'dormant' and bars_count >= 333:
                    supabase.client.table('lowcap_positions').update({
                        'status': 'watchlist'
                    }).eq('id', position_id).execute()
                    logger.info(f"Auto-flipped position {position_id} from dormant to watchlist (bars_count={bars_count})")
        
    except Exception as e:
        logger.warning(f"Failed to update bars_count for {token_contract} {timeframe}: {e}")


def backfill_token_timeframe(
    token_contract: str, 
    chain: str, 
    timeframe: str, 
    lookback_minutes: Optional[int] = None
) -> Dict[str, Any]:
    """
    Generic backfill function for any timeframe (1m, 15m, 1h, 4h)
    
    Args:
        token_contract: Token contract address
        chain: Chain name (solana, ethereum, base, bsc)
        timeframe: Timeframe ('1m', '15m', '1h', '4h')
        lookback_minutes: Minutes to look back (default 14 days)
    
    Returns:
        Dict with results summary
    """
    # Map timeframe to GeckoTerminal API endpoint (verified endpoints from test_geckoterminal_timeframes.py)
    gt_endpoint_map = {
        '1m': ('minute', 1),   # /ohlcv/minute?aggregate=1
        '15m': ('minute', 15), # /ohlcv/minute?aggregate=15
        '1h': ('hour', 1),     # /ohlcv/hour?aggregate=1
        '4h': ('hour', 4),    # /ohlcv/hour?aggregate=4
    }
    
    gt_timeframe, gt_aggregate = gt_endpoint_map.get(timeframe, ('hour', 1))
    
    supabase = SupabaseManager()
    chain = (chain or '').lower()
    network = NETWORK_MAP.get(chain, chain)
    
    if network not in NETWORK_MAP.values():
        raise ValueError(f"Unsupported chain/network: {chain}")
    
    if timeframe not in ['1m', '15m', '1h', '4h']:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    
    # Get canonical pool from position features
    try:
        pos = supabase.client.table('lowcap_positions').select('features').eq(
            'token_contract', token_contract
        ).eq('token_chain', chain).limit(1).execute()
        features = (pos.data[0].get('features') if pos.data else None) or {}
    except Exception:
        features = {}
    
    canonical = _get_canonical_pool_from_features(features)
    pool_addr: Optional[str] = None
    dex_id: str = ''
    quote_symbol: str = ''
    
    if canonical:
        pool_addr, dex_id = canonical
        try:
            data = _fetch_gt_pools_by_token(network, token_contract)
            for p in data.get('data', []) or []:
                if (p.get('attributes', {}) or {}).get('address') == pool_addr:
                    quote_symbol = (p.get('attributes', {}).get('name') or '').split('/')[-1].strip().upper()
                    break
        except Exception:
            quote_symbol = NATIVE_SYMBOL_BY_CHAIN.get(chain, '')
    else:
        picked = _select_canonical_pool_from_gt(chain, token_contract)
        if not picked:
            raise RuntimeError("No pools found on GeckoTerminal for token")
        pool_addr, dex_id, quote_symbol = picked
        _update_canonical_pool_features(supabase, token_contract, chain, pool_addr, dex_id)
    
    timeframe_minutes_map = {'1m': 1, '15m': 15, '1h': 60, '4h': 240}
    timeframe_minutes = timeframe_minutes_map[timeframe]
    bars_target = int(os.getenv("BACKFILL_BARS_TARGET", "666"))  # Target 666 bars
    bars_min = int(os.getenv("BACKFILL_BARS_MIN", "333"))  # Minimum 333 bars (same for all timeframes)
    buffer_bars = int(os.getenv("BACKFILL_BARS_BUFFER", "10"))

    if lookback_minutes is None or lookback_minutes <= 0:
        lookback_minutes = timeframe_minutes * (bars_target + buffer_bars)

    end_dt = _minute_floor(_now_utc() - timedelta(minutes=2))
    start_dt = end_dt - timedelta(minutes=lookback_minutes)
    
    logger.info(f"Fetching {bars_target} {timeframe} bars (lookback_minutes={lookback_minutes})")

    limit = bars_target + buffer_bars
    try:
        data = _fetch_gt_ohlcv_by_pool(
            network,
            pool_addr,
            limit=limit,
            timeframe=gt_timeframe,
            aggregate=gt_aggregate
        )
    except Exception as e:
        logger.error(f"Failed to fetch token OHLCV: {e}")
        return {
            'token_contract': token_contract,
            'chain': chain,
            'timeframe': timeframe,
            'pool_address': pool_addr,
            'dex_id': dex_id,
            'inserted_rows': 0,
            'window_start': start_dt.isoformat(),
            'window_end': end_dt.isoformat(),
            'error': str(e)
        }
    
    ohlcv_list = (data.get('data', {}) or {}).get('attributes', {}).get('ohlcv_list', []) or []
    if not ohlcv_list:
        logger.warning(f"No OHLCV data returned for {token_contract} {timeframe}")
        return {
            'token_contract': token_contract,
            'chain': chain,
            'timeframe': timeframe,
            'pool_address': pool_addr,
            'dex_id': dex_id,
            'inserted_rows': 0,
            'window_start': start_dt.isoformat(),
            'window_end': end_dt.isoformat(),
            'error': 'no_data'
        }

    rows_to_insert = _build_rows_for_insert(
        token_contract,
        chain,
        pool_addr,
        dex_id,
        quote_symbol,
        ohlcv_list,
        timeframe,
        start_dt,
        end_dt
    )

    if not rows_to_insert:
        logger.warning(f"No valid rows built for {token_contract} {timeframe}")
        return {
            'token_contract': token_contract,
            'chain': chain,
            'timeframe': timeframe,
            'pool_address': pool_addr,
            'dex_id': dex_id,
            'inserted_rows': 0,
            'window_start': start_dt.isoformat(),
            'window_end': end_dt.isoformat(),
            'error': 'no_valid_rows'
        }

    rows_to_insert.sort(key=lambda r: r['timestamp'])
    # Keep up to bars_target rows, but ensure we have at least bars_min
    if len(rows_to_insert) > bars_target:
        rows_to_insert = rows_to_insert[-bars_target:]
    elif len(rows_to_insert) < bars_min:
        logger.warning(f"Only got {len(rows_to_insert)} bars for {timeframe}, minimum is {bars_min}")
        # Still proceed, but log the warning

    # Deduplicate rows by (token_contract, chain, timeframe, timestamp) before inserting
    seen = set()
    unique_rows = []
    for r in rows_to_insert:
        key = (r['token_contract'], r['chain'], r['timeframe'], r['timestamp'])
        if key not in seen:
            seen.add(key)
            unique_rows.append(r)
    
    if len(unique_rows) < len(rows_to_insert):
        logger.warning(f"Deduplicated {len(rows_to_insert)} rows to {len(unique_rows)} unique rows")
    rows_to_insert = unique_rows

    inserted = 0
    BATCH_SIZE = 500
    for i in range(0, len(rows_to_insert), BATCH_SIZE):
        chunk = rows_to_insert[i:i + BATCH_SIZE]
        try:
            supabase.client.table('lowcap_price_data_ohlc').upsert(chunk).execute()
            inserted += len(chunk)
            logger.info(f"Upserted batch of {len(chunk)} rows")
        except Exception as e:
            logger.error(f"Insert chunk failed: {e}")
    
    logger.info(f"{timeframe} backfill complete: {inserted} rows upserted")
    
    _update_bars_count_after_backfill(supabase, token_contract, chain, timeframe, inserted)

    window_start_ts = rows_to_insert[0]['timestamp']
    window_end_ts = rows_to_insert[-1]['timestamp']
    
    return {
        'token_contract': token_contract,
        'chain': chain,
        'timeframe': timeframe,
        'pool_address': pool_addr,
        'dex_id': dex_id,
        'inserted_rows': inserted,
        'window_start': window_start_ts,
        'window_end': window_end_ts,
    }


# Wrapper functions for each timeframe
def backfill_token_1m(token_contract: str, chain: str, lookback_minutes: Optional[int] = None) -> Dict[str, Any]:
    """Backfill 1m OHLCV data"""
    return backfill_token_timeframe(token_contract, chain, '1m', lookback_minutes)


def backfill_token_15m(token_contract: str, chain: str, lookback_minutes: Optional[int] = None) -> Dict[str, Any]:
    """Backfill 15m OHLCV data"""
    return backfill_token_timeframe(token_contract, chain, '15m', lookback_minutes)


def backfill_token_1h(token_contract: str, chain: str, lookback_minutes: Optional[int] = None) -> Dict[str, Any]:
    """Backfill 1h OHLCV data"""
    return backfill_token_timeframe(token_contract, chain, '1h', lookback_minutes)


def backfill_token_4h(token_contract: str, chain: str, lookback_minutes: Optional[int] = None) -> Dict[str, Any]:
    """Backfill 4h OHLCV data"""
    return backfill_token_timeframe(token_contract, chain, '4h', lookback_minutes)


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