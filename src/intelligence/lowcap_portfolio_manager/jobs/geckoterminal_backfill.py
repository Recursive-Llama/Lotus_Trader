#!/usr/bin/env python3
"""
GeckoTerminal OHLCV backfill job

- Uses canonical pool (pair_address,dex_id) from lowcap_positions.features if present
- Otherwise searches pools by mint+chain, prefers native-quoted highest-liquidity, persists canonical pool
- Supports two granularities:
  - 1m → writes to lowcap_price_data_1m (minute closes)
  - 15m → writes to lowcap_price_data_ohlc with timeframe='15m'
- Upserts only missing timestamps (idempotent gap-fill)
"""

import os
import sys
import time
import math
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple, Set

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
    url = f"{GT_BASE}/networks/{network}/tokens/{token_mint}/pools?include=dex,base_token,quote_token&per_page=50"
    resp = requests.get(url, headers=GT_HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _fetch_gt_ohlcv_by_pool(network: str, pool_address: str, aggregate_min: int, limit: int = 1000, to_ts: Optional[int] = None) -> Dict[str, Any]:
    params = [f"aggregate={aggregate_min}", f"limit={limit}"]
    if to_ts is not None:
        params.append(f"to={to_ts}")
    url = f"{GT_BASE}/networks/{network}/pools/{pool_address}/ohlcv/minute?" + "&".join(params)
    resp = requests.get(url, headers=GT_HEADERS, timeout=30)
    if resp.status_code == 404:
        return {"data": None}
    resp.raise_for_status()
    return resp.json()


def _select_canonical_pool_from_gt(chain: str, token_mint: str) -> Optional[Tuple[str, str, str]]:
    """
    Return (pool_address, dex_id, quote_symbol) with smart pool selection logic.
    
    For native tokens (SOL, ETH, etc.): Prefer NATIVE/USD pairs
    For other tokens: Prefer TOKEN/NATIVE pairs
    """
    network = NETWORK_MAP.get(chain, chain)
    data = _fetch_gt_pools_by_token(network, token_mint)
    pools = data.get('data', []) or []
    if not pools:
        return None

    native_symbol = NATIVE_SYMBOL_BY_CHAIN.get(chain)
    native_address = NATIVE_ADDRESS_BY_CHAIN.get(chain)
    
    def liquidity_usd(p):
        try:
            return float(p.get('attributes', {}).get('reserve_in_usd') or 0)
        except Exception:
            return 0.0

    # Check if this is the native token
    is_native_token = (token_mint == native_address)
    
    if is_native_token:
        # For native tokens (SOL, ETH, etc.): Look for NATIVE/USD pairs
        usd_pairs: List[Dict[str, Any]] = []
        others: List[Dict[str, Any]] = []
        
        for p in pools:
            name = p.get('attributes', {}).get('name', '')
            base_symbol = name.split('/')[0].strip().upper()
            quote_symbol = name.split('/')[-1].strip().upper()
            
            # Look for NATIVE/USD pairs (SOL/USDC, ETH/USDC, etc.)
            if base_symbol == native_symbol and quote_symbol in ['USDC', 'USDT', 'USD']:
                usd_pairs.append(p)
            else:
                others.append(p)
        
        # Prefer USD pairs, fallback to others
        if usd_pairs:
            chosen = max(usd_pairs, key=liquidity_usd)
        else:
            chosen = max(others, key=liquidity_usd)
    else:
        # For non-native tokens: Look for TOKEN/NATIVE pairs
        native_quoted: List[Dict[str, Any]] = []
        others: List[Dict[str, Any]] = []
        
        for p in pools:
            name = p.get('attributes', {}).get('name', '')
            quote_symbol = name.split('/')[-1].strip().upper()
            
            if quote_symbol == native_symbol:
                native_quoted.append(p)
            else:
                others.append(p)
        
        # Prefer native-quoted, fallback to others
        if native_quoted:
            chosen = max(native_quoted, key=liquidity_usd)
        else:
            chosen = max(others, key=liquidity_usd)

    attr = chosen.get('attributes', {})
    pool_address = attr.get('address')
    quote_symbol = (attr.get('name') or '').split('/')[-1].strip().upper()
    dex_id = (chosen.get('relationships', {}).get('dex', {}) or {}).get('data', {}).get('id', '')
    return (pool_address, dex_id, quote_symbol)


def _get_canonical_pool_from_features(features: Optional[Dict[str, Any]]) -> Optional[Tuple[str, str]]:
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
    try:
        # Prefer latest ACTIVE row for this token/chain
        res_active = (
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
        rows = res_active.data or []
        if not rows:
            # Fallback: latest row regardless of status
            res_any = (
                supabase.client
                .table('lowcap_positions')
                .select('id,features,created_at')
                .eq('token_contract', token_contract)
                .eq('token_chain', chain)
                .order('created_at', desc=True)
                .limit(1)
                .execute()
            )
            rows = res_any.data or []
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


def _update_backfill_watermark(supabase: SupabaseManager, token_contract: str, chain: str, last_filled_ts: datetime):
    try:
        res = supabase.client.table('lowcap_positions').select('id,features').eq('token_contract', token_contract).eq('token_chain', chain).limit(1).execute()
        rows = res.data or []
        if not rows:
            return
        row = rows[0]
        features = row.get('features') or {}
        if not isinstance(features, dict):
            features = {}
        backfill_meta = features.get('backfill') or {}
        if not isinstance(backfill_meta, dict):
            backfill_meta = {}
        backfill_meta['last_attempt_ts'] = _now_utc().isoformat()
        backfill_meta['last_filled_ts'] = last_filled_ts.isoformat()
        features['backfill'] = backfill_meta
        supabase.client.table('lowcap_positions').update({'features': features}).eq('id', row['id']).execute()
    except Exception as e:
        logger.warning(f"Failed to persist backfill watermark for {token_contract} on {chain}: {e}")


def _get_existing_timestamps_1m(supabase: SupabaseManager, token_contract: str, chain: str, start_ts: datetime, end_ts: datetime) -> Set[str]:
    try:
        result = (
            supabase.client
            .table('lowcap_price_data_ohlc')
            .select('timestamp')
            .eq('token_contract', token_contract)
            .eq('chain', chain)
            .eq('timeframe', '1m')
            .gte('timestamp', start_ts.isoformat())
            .lte('timestamp', end_ts.isoformat())
            .limit(100000)
            .execute()
        )
        data = result.data or []
        return set([row['timestamp'] for row in data])
    except Exception as e:
        logger.warning(f"Failed to load existing 1m timestamps: {e}")
        return set()


def _get_existing_timestamps_15m(supabase: SupabaseManager, token_contract: str, chain: str, start_ts: datetime, end_ts: datetime) -> Set[str]:
    try:
        result = supabase.client.table('lowcap_price_data_ohlc').select('timestamp').eq('token_contract', token_contract).eq('chain', chain).eq('timeframe', '15m').gte('timestamp', start_ts.isoformat()).lte('timestamp', end_ts.isoformat()).limit(100000).execute()
        data = result.data or []
        return set([row['timestamp'] for row in data])
    except Exception as e:
        logger.warning(f"Failed to load existing 15m timestamps: {e}")
        return set()


def _get_native_usd_at(supabase: SupabaseManager, chain: str, at_ts: datetime) -> Optional[float]:
    try:
        native_address = NATIVE_ADDRESS_BY_CHAIN.get(chain)
        if not native_address:
            return None
        res = supabase.client.table('lowcap_price_data_1m').select('price_usd').eq('token_contract', native_address).eq('chain', chain).lte('timestamp', at_ts.isoformat()).order('timestamp', desc=True).limit(1).execute()
        rows = res.data or []
        if rows:
            return float(rows[0]['price_usd'])
        return None
    except Exception as e:
        logger.warning(f"Failed to get native USD at {at_ts}: {e}")
        return None


def _build_rows_for_insert_15m(token_contract: str, chain: str, pool_addr: str, dex_id: str, quote_symbol: str, ohlcv_list: List[List[Any]], supabase: SupabaseManager) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for entry in ohlcv_list:
        try:
            # [ts, o, h, l, c, v] - GeckoTerminal returns [timestamp, open, high, low, close, volume]
            ts_sec = int(entry[0])
            open_usd = float(entry[1])
            high_usd = float(entry[2])
            low_usd = float(entry[3])
            close_usd = float(entry[4])
            volume_tokens = float(entry[5])  # Volume in token amount
            ts_dt = datetime.fromtimestamp(ts_sec, tz=timezone.utc)

            # Convert volume to USD: volume_tokens * close_price_usd
            volume_usd = volume_tokens * close_usd

            # Get native price conversion
            native_usd = _get_native_usd_at(supabase, chain, ts_dt) or 0.0
            if native_usd > 0:
                open_native = open_usd / native_usd
                high_native = high_usd / native_usd
                low_native = low_usd / native_usd
                close_native = close_usd / native_usd
            else:
                open_native = high_native = low_native = close_native = 0.0

            rows.append({
                'token_contract': token_contract,
                'chain': chain,
                'timeframe': '15m',  # 15-minute timeframe
                'timestamp': ts_dt.isoformat(),
                'open_native': open_native,
                'high_native': high_native,
                'low_native': low_native,
                'close_native': close_native,
                'open_usd': open_usd,
                'high_usd': high_usd,
                'low_usd': low_usd,
                'close_usd': close_usd,
                'volume': volume_usd,  # Now stored as USD volume
                'source': 'geckoterminal'
            })
        except Exception as e:
            logger.debug(f"Skip malformed OHLCV entry: {e}")
    return rows


def backfill_token_15m(token_contract: str, chain: str, lookback_minutes: int = 10080) -> Dict[str, Any]:
    """
    Backfill last N minutes for a token from GeckoTerminal by canonical pool (15m aggregation).
    """
    supabase = SupabaseManager()
    chain = (chain or '').lower()
    network = NETWORK_MAP.get(chain, chain)
    if network not in NETWORK_MAP.values():
        raise ValueError(f"Unsupported chain/network: {chain}")

    # Load features to find canonical pool
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
        # We still want quote_symbol for storage; fetch from pools listing if needed
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

    # Determine time window
    end_dt = _minute_floor(_now_utc() - timedelta(minutes=2))
    start_dt = end_dt - timedelta(minutes=lookback_minutes)

    # Load existing timestamps to avoid overwrite
    existing = _get_existing_timestamps_15m(supabase, token_contract, chain, start_dt, end_dt)

    # Fetch OHLCV in chunks (max 1000 per call)
    rows_to_insert: List[Dict[str, Any]] = []
    remaining = lookback_minutes
    window_end = end_dt
    newest_inserted_ts: Optional[datetime] = None
    while remaining > 0:
        this_window = min(remaining, 1000)
        to_ts = _unix(window_end)
        data = _fetch_gt_ohlcv_by_pool(network, pool_addr, aggregate_min=15, limit=this_window, to_ts=to_ts)
        if not data or not data.get('data'):
            # 404 or empty; fallback once: re-select canonical by search
            if not canonical:
                picked = _select_canonical_pool_from_gt(chain, token_contract)
                if picked:
                    pool_addr, dex_id, quote_symbol = picked
                    _update_canonical_pool_features(supabase, token_contract, chain, pool_addr, dex_id)
                    continue
            break

        ohlcv_list = (data.get('data', {}) or {}).get('attributes', {}).get('ohlcv_list', []) or []
        if not ohlcv_list:
            break

        batch_rows = _build_rows_for_insert_15m(token_contract, chain, pool_addr, dex_id, quote_symbol, ohlcv_list, supabase)
        # Filter out existing timestamps
        filtered = [r for r in batch_rows if r['timestamp'] not in existing]
        rows_to_insert.extend(filtered)
        if filtered:
            # Track newest timestamp among filtered rows
            for r in filtered:
                ts_dt = datetime.fromisoformat(r['timestamp'])
                if newest_inserted_ts is None or ts_dt > newest_inserted_ts:
                    newest_inserted_ts = ts_dt

        # Prepare next window
        oldest_ts = datetime.fromtimestamp(int(ohlcv_list[-1][0]), tz=timezone.utc)
        window_end = oldest_ts - timedelta(minutes=1)
        remaining = int((_unix(window_end) - _unix(start_dt)) / 60) + 1
        if remaining <= 0:
            break

        # polite pacing
        time.sleep(0.2)

    # Batch insert in chunks to supabase
    inserted = 0
    if rows_to_insert:
        BATCH = 500
        for i in range(0, len(rows_to_insert), BATCH):
            chunk = rows_to_insert[i:i+BATCH]
            try:
                supabase.client.table('lowcap_price_data_ohlc').insert(chunk).execute()
                inserted += len(chunk)
            except Exception as e:
                logger.error(f"Insert chunk failed: {e}")

    # Update watermark if we inserted anything
    if inserted > 0 and newest_inserted_ts is not None:
        _update_backfill_watermark(supabase, token_contract, chain, newest_inserted_ts)

    return {
        'token_contract': token_contract,
        'chain': chain,
        'pool_address': pool_addr,
        'dex_id': dex_id,
        'inserted_rows': inserted,
        'window_start': start_dt.isoformat(),
        'window_end': end_dt.isoformat(),
    }


def _build_rows_for_insert_1m(token_contract: str, chain: str, ohlcv_list: List[List[Any]], supabase: SupabaseManager) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for entry in ohlcv_list:
        try:
            ts_sec = int(entry[0])
            open_usd = float(entry[1])
            high_usd = float(entry[2])
            low_usd = float(entry[3])
            close_usd = float(entry[4])
            volume_tokens = float(entry[5])
            ts_dt = datetime.fromtimestamp(ts_sec, tz=timezone.utc)
            volume_usd = volume_tokens * close_usd
            native_usd = _get_native_usd_at(supabase, chain, ts_dt) or 0.0
            if native_usd > 0:
                open_native = open_usd / native_usd
                high_native = high_usd / native_usd
                low_native = low_usd / native_usd
                close_native = close_usd / native_usd
            else:
                open_native = high_native = low_native = close_native = 0.0
            rows.append({
                'token_contract': token_contract,
                'chain': chain,
                'timeframe': '1m',
                'timestamp': ts_dt.isoformat(),
                'open_native': open_native,
                'high_native': high_native,
                'low_native': low_native,
                'close_native': close_native,
                'open_usd': open_usd,
                'high_usd': high_usd,
                'low_usd': low_usd,
                'close_usd': close_usd,
                'volume': volume_usd,
                'source': 'geckoterminal'
            })
        except Exception as e:
            logger.debug(f"Skip malformed 1m OHLCV entry: {e}")
    return rows


def backfill_token_1m(token_contract: str, chain: str, lookback_minutes: int = 72 * 60) -> Dict[str, Any]:
    supabase = SupabaseManager()
    chain = (chain or '').lower()
    network = NETWORK_MAP.get(chain, chain)
    if network not in NETWORK_MAP.values():
        raise ValueError(f"Unsupported chain/network: {chain}")

    # Determine canonical pool just as for 15m (for consistency)
    try:
        pos = supabase.client.table('lowcap_positions').select('features').eq('token_contract', token_contract).eq('token_chain', chain).limit(1).execute()
        features = (pos.data[0].get('features') if pos.data else None) or {}
    except Exception:
        features = {}

    canonical = _get_canonical_pool_from_features(features)
    if not canonical:
        picked = _select_canonical_pool_from_gt(chain, token_contract)
        if not picked:
            raise RuntimeError("No pools found on GeckoTerminal for token")
        pool_addr, dex_id, _ = picked
        _update_canonical_pool_features(supabase, token_contract, chain, pool_addr, dex_id)
    else:
        pool_addr, dex_id = canonical

    end_dt = _minute_floor(_now_utc() - timedelta(minutes=2))
    start_dt = end_dt - timedelta(minutes=lookback_minutes)
    existing = _get_existing_timestamps_1m(supabase, token_contract, chain, start_dt, end_dt)

    rows_to_insert: List[Dict[str, Any]] = []
    remaining = lookback_minutes
    window_end = end_dt
    while remaining > 0:
        this_window = min(remaining, 1000)
        to_ts = _unix(window_end)
        data = _fetch_gt_ohlcv_by_pool(network, pool_addr, aggregate_min=1, limit=this_window, to_ts=to_ts)
        if not data or not data.get('data'):
            break
        ohlcv_list = (data.get('data', {}) or {}).get('attributes', {}).get('ohlcv_list', []) or []
        if not ohlcv_list:
            break
        batch_rows = _build_rows_for_insert_1m(token_contract, chain, ohlcv_list, supabase)
        filtered = [r for r in batch_rows if r['timestamp'] not in existing]
        rows_to_insert.extend(filtered)
        if not filtered:
            break
        oldest_ts = datetime.fromtimestamp(int(ohlcv_list[-1][0]), tz=timezone.utc)
        window_end = oldest_ts - timedelta(minutes=1)
        remaining = int((_unix(window_end) - _unix(start_dt)) / 60) + 1
        if remaining <= 0:
            break
        time.sleep(0.2)

    inserted = 0
    if rows_to_insert:
        BATCH = 1000
        for i in range(0, len(rows_to_insert), BATCH):
            chunk = rows_to_insert[i:i+BATCH]
            try:
                supabase.client.table('lowcap_price_data_ohlc').insert(chunk).execute()
                inserted += len(chunk)
            except Exception as e:
                logger.error(f"Insert 1m chunk failed: {e}")

    return {
        'token_contract': token_contract,
        'chain': chain,
        'inserted_rows': inserted,
        'window_start': start_dt.isoformat(),
        'window_end': end_dt.isoformat(),
    }


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    if len(sys.argv) < 4:
        print("Usage: geckoterminal_backfill.py <chain> <token_contract> <granularity:1m|15m> [lookback_minutes]")
        sys.exit(1)
    chain = sys.argv[1]
    token = sys.argv[2]
    gran = sys.argv[3].lower()
    lookback = int(sys.argv[4]) if len(sys.argv) > 4 else (72 * 60 if gran == '1m' else 2880)
    if gran == '1m':
        res = backfill_token_1m(token, chain, lookback)
    elif gran == '15m':
        res = backfill_token_15m(token, chain, lookback)
    else:
        print("granularity must be 1m or 15m")
        sys.exit(1)
    print(res)


if __name__ == "__main__":
    main()


