#!/usr/bin/env python3
"""
GeckoTerminal OHLCV backfill job - Clean, Simple Version

- Uses canonical pool from lowcap_positions.features if present
- Otherwise searches pools by mint+chain, prefers native-quoted highest-liquidity
- Supports timeframes (15m, 1h, 4h) - writes to lowcap_price_data_ohlc
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


# GeckoTerminal network slugs
NETWORK_MAP = {
    'solana': 'solana',
    'ethereum': 'eth',  # GT expects 'eth' not 'ethereum'
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
    """Fetch pools for a token from GeckoTerminal with retry logic"""
    url = f"{GT_BASE}/networks/{network}/tokens/{token_mint}/pools?include=dex,base_token,quote_token&per_page=50"
    
    # Retry with exponential backoff
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=GT_HEADERS, timeout=15)
            if resp.status_code == 404:
                # Token not found on GeckoTerminal - return empty result
                return {"data": None}
            if resp.status_code == 429:
                # Rate limited - wait longer
                wait_time = (2 ** attempt) * 2  # 2, 4, 8 seconds
                logger.warning(f"Rate limited on pool discovery, waiting {wait_time}s (attempt {attempt + 1})")
                time.sleep(wait_time)
                continue
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt == 2:  # Last attempt
                raise e
            wait_time = (2 ** attempt) * 1  # 1, 2, 4 seconds
            logger.warning(f"Pool discovery request failed, retrying in {wait_time}s: {e}")
            time.sleep(wait_time)
    
    raise Exception("All retry attempts failed")


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


def _get_canonical_pool_from_features(features: Optional[Dict[str, Any]]) -> Optional[Tuple[str, str, Optional[str], Optional[str]]]:
    """
    Extract canonical pool from position features.
    Returns (pair_address, dex_id, quote_symbol, last_pool_check) or None
    """
    if not features:
        return None
    cp = features.get('canonical_pool') if isinstance(features, dict) else None
    if isinstance(cp, dict):
        pair = cp.get('pair_address')
        dex_id = cp.get('dex_id')
        if pair and dex_id:
            quote_symbol = cp.get('quote_symbol')
            last_pool_check = cp.get('last_pool_check')  # ISO timestamp string
            return (pair, dex_id, quote_symbol, last_pool_check)
    return None


def _update_canonical_pool_features(supabase: SupabaseManager, token_contract: str, chain: str, pool_addr: str, dex_id: str, quote_symbol: Optional[str] = None):
    """
    Update position features with canonical pool info for ALL timeframes.
    
    Since we have 3 positions per Solana token (one per timeframe: 15m, 1h, 4h),
    we need to update all of them so they share the same canonical pool.
    
    Args:
        supabase: Supabase manager
        token_contract: Token contract address
        chain: Chain name
        pool_addr: Pool address
        dex_id: DEX ID
        quote_symbol: Quote symbol (e.g., 'SOL', 'USDC') - optional, will be stored if provided
    """
    try:
        # Build canonical_pool dict
        canonical_pool = {
            'pair_address': pool_addr,
            'dex_id': dex_id
        }
        
        # Add quote_symbol if provided
        if quote_symbol:
            canonical_pool['quote_symbol'] = quote_symbol
        
        # Update last_pool_check timestamp (when we last fetched/verified pool info)
        canonical_pool['last_pool_check'] = _now_utc().isoformat()
        
        # Get ALL positions for this token/chain (all timeframes)
        res = (
            supabase.client
            .table('lowcap_positions')
            .select('id,features')
            .eq('token_contract', token_contract)
            .eq('token_chain', chain)
            .execute()
        )
        rows = res.data or []
        
        if not rows:
            logger.debug(f"No positions found for {token_contract} on {chain} to update canonical pool")
            return
        
        # Update each position's features with canonical pool
        for row in rows:
            try:
                features = row.get('features') or {}
                if not isinstance(features, dict):
                    features = {}
                
                features['canonical_pool'] = canonical_pool
                supabase.client.table('lowcap_positions').update({'features': features}).eq('id', row['id']).execute()
            except Exception as e:
                logger.warning(f"Failed to update canonical_pool for position {row.get('id')}: {e}")
        
        logger.debug(f"Updated canonical_pool for {len(rows)} positions ({token_contract[:8]}.../{chain})")
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
    
    Interpolates missing candles when < 3 consecutive bad candles are found
    between valid candles (linear interpolation).
    """
    # First pass: Process all entries and mark as valid/invalid
    processed_entries = []
    
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
            
            is_valid = True
            skip_reason = None

            # Safeguards: reject invalid prices
            if open_usd <= 0 or high_usd <= 0 or low_usd <= 0 or close_usd <= 0:
                is_valid = False
                skip_reason = "non-positive USD prices"
            
            # Check OHLC logic: high >= max(open,close) and low <= min(open,close)
            elif high_usd < max(open_usd, close_usd) or low_usd > min(open_usd, close_usd):
                is_valid = False
                skip_reason = f"invalid OHLC relationship (high={high_usd}, low={low_usd}, open={open_usd}, close={close_usd})"

            # Check for extreme jumps (>100x change) - likely bad data
            elif close_usd > 0 and open_usd > 0:
                price_change_ratio = max(close_usd / open_usd, open_usd / close_usd)
                if price_change_ratio > 100.0:
                    is_valid = False
                    skip_reason = f"extreme price jump (ratio={price_change_ratio:.2f})"
            
            processed_entries.append({
                'ts_sec': ts_sec,
                'ts_dt': ts_dt,
                'ts_iso': ts_iso,
                'open_usd': open_usd,
                'high_usd': high_usd,
                'low_usd': low_usd,
                'close_usd': close_usd,
                'volume_usd': volume_usd,
                'is_valid': is_valid,
                'skip_reason': skip_reason
            })
        except Exception as e:
            # Malformed entry - mark as invalid
            try:
                ts_sec = int(entry[0])
                ts_dt = datetime.fromtimestamp(ts_sec, tz=timezone.utc)
                ts_iso = ts_dt.isoformat()
            except:
                ts_sec = 0
                ts_dt = datetime.now(timezone.utc)
                ts_iso = ts_dt.isoformat()
            
            processed_entries.append({
                'ts_sec': ts_sec,
                'ts_dt': ts_dt,
                'ts_iso': ts_iso,
                'open_usd': 0.0,
                'high_usd': 0.0,
                'low_usd': 0.0,
                'close_usd': 0.0,
                'volume_usd': 0.0,
                'is_valid': False,
                'skip_reason': f"malformed entry: {e}"
            })
    
    # Second pass: Build rows with interpolation for < 3 consecutive bad candles
    rows = []
    skipped_count = 0
    interpolated_count = 0
    i = 0
    
    while i < len(processed_entries):
        entry = processed_entries[i]
        
        if entry['is_valid']:
            # Valid entry - add directly
            rows.append(_build_row_dict(
                token_contract, chain, timeframe,
                entry['ts_iso'],
                entry['open_usd'], entry['high_usd'], entry['low_usd'], entry['close_usd'],
                entry['volume_usd']
            ))
            i += 1
        else:
            # Invalid entry - check if we can interpolate
            # Count consecutive invalid entries
            invalid_start = i
            invalid_count = 0
            while i < len(processed_entries) and not processed_entries[i]['is_valid']:
                invalid_count += 1
                i += 1
            
            # Find next valid entry (look ahead from current position)
            next_valid = None
            next_valid_idx = i
            while next_valid_idx < len(processed_entries) and not processed_entries[next_valid_idx]['is_valid']:
                next_valid_idx += 1
            if next_valid_idx < len(processed_entries):
                next_valid = processed_entries[next_valid_idx]
            
            # Find previous valid entry (last row we added)
            prev_valid = None
            if rows:
                # Get the last valid entry's close price
                last_row = rows[-1]
                prev_valid = {
                    'ts_dt': datetime.fromisoformat(last_row['timestamp'].replace('Z', '+00:00')),
                    'close_usd': last_row['close_usd']
                }
            
            # Can we interpolate? Need valid before AND after, and < 3 consecutive bad
            if prev_valid and next_valid and invalid_count < 3:
                # Interpolate the missing candles
                prev_ts = prev_valid['ts_dt'].timestamp()
                next_ts = next_valid['ts_dt'].timestamp()
                prev_close = prev_valid['close_usd']
                next_open = next_valid['open_usd']
                
                # Interpolate each invalid entry
                for j in range(invalid_start, invalid_start + invalid_count):
                    invalid_entry = processed_entries[j]
                    invalid_ts = invalid_entry['ts_dt'].timestamp()
                    
                    # Linear interpolation factor (0.0 at prev, 1.0 at next)
                    if next_ts > prev_ts:
                        t = (invalid_ts - prev_ts) / (next_ts - prev_ts)
                    else:
                        t = 0.5  # Fallback if timestamps are equal
                    
                    # Interpolate prices (linear between prev_close and next_open)
                    interpolated_price = prev_close + (next_open - prev_close) * t
                    
                    # For OHLC, use interpolated price for open/close
                    # High/Low should span the range between prev and next to maintain realistic OHLC logic
                    price_range = abs(next_open - prev_close)
                    price_spread = max(price_range * 0.01, interpolated_price * 0.001)  # 1% of range or 0.1% of price
                    interpolated_open = interpolated_price
                    interpolated_close = interpolated_price
                    interpolated_high = interpolated_price + price_spread
                    interpolated_low = max(0.0, interpolated_price - price_spread)
                    
                    # Ensure OHLC logic: high >= max(open,close) and low <= min(open,close)
                    interpolated_high = max(interpolated_high, max(interpolated_open, interpolated_close))
                    interpolated_low = min(interpolated_low, min(interpolated_open, interpolated_close))
                    
                    # Use average volume from prev/next (or 0 if not available)
                    interpolated_volume = 0.0
                    
                    rows.append(_build_row_dict(
                        token_contract, chain, timeframe,
                        invalid_entry['ts_iso'],
                        interpolated_open, interpolated_high, interpolated_low, interpolated_close,
                        interpolated_volume
                    ))
                    interpolated_count += 1
                
                logger.info(
                    f"Interpolated {invalid_count} missing candles between {prev_valid['ts_dt'].isoformat()} "
                    f"and {next_valid['ts_dt'].isoformat()} (prev_close=${prev_close:.6f}, next_open=${next_open:.6f})"
                )
            else:
                # Can't interpolate - skip these entries
                for j in range(invalid_start, invalid_start + invalid_count):
                    invalid_entry = processed_entries[j]
                    skipped_count += 1
                    if invalid_entry['skip_reason']:
                        logger.debug(f"Skip entry {invalid_entry['ts_iso']}: {invalid_entry['skip_reason']}")
    
    if skipped_count > 0:
        logger.info(f"Skipped {skipped_count} invalid entries during row building")
    if interpolated_count > 0:
        logger.info(f"Interpolated {interpolated_count} missing candles")
    
    return rows


def _build_row_dict(
    token_contract: str,
    chain: str,
    timeframe: str,
    ts_iso: str,
    open_usd: float,
    high_usd: float,
    low_usd: float,
    close_usd: float,
    volume_usd: float
) -> Dict[str, Any]:
    """Build a single row dictionary for database insertion."""
    # Native prices: Set to 0.0 (convert on-demand when needed for display/reporting)
    return {
        'token_contract': token_contract,
        'chain': chain,
        'timeframe': timeframe,
        'timestamp': ts_iso,
        'open_native': 0.0,
        'high_native': 0.0,
        'low_native': 0.0,
        'close_native': 0.0,
        'open_usd': open_usd,
        'high_usd': high_usd,
        'low_usd': low_usd,
        'close_usd': close_usd,
        'volume': max(0.0, volume_usd),  # Ensure non-negative volume
        'source': 'geckoterminal'
    }


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
    
    # Pool refresh interval: 7 days (604800 seconds)
    POOL_REFRESH_INTERVAL_SECONDS = 7 * 24 * 60 * 60
    
    if canonical:
        pool_addr, dex_id, stored_quote_symbol, last_pool_check = canonical
        
        # Check if we need to refresh pool info
        needs_refresh = False
        if not stored_quote_symbol:
            # Missing quote_symbol - need to fetch
            needs_refresh = True
            logger.debug(f"Missing quote_symbol for {token_contract[:8]}..., fetching pools")
        elif last_pool_check:
            # Check if last_pool_check is older than refresh interval
            try:
                last_check_dt = datetime.fromisoformat(last_pool_check.replace('Z', '+00:00'))
                age_seconds = (_now_utc() - last_check_dt).total_seconds()
                if age_seconds > POOL_REFRESH_INTERVAL_SECONDS:
                    needs_refresh = True
                    logger.debug(f"Pool info for {token_contract[:8]}... is {age_seconds/86400:.1f} days old, refreshing")
            except (ValueError, TypeError):
                # Invalid timestamp, refresh to fix it
                needs_refresh = True
        else:
            # No last_pool_check timestamp, refresh to add it
            needs_refresh = True
        
        if needs_refresh:
            # Defer pool refresh to avoid extra API calls during backfill.
            # If we have pool_addr (which we should if canonical exists), we can use it for OHLCV fetching.
            # The quote_symbol refresh is nice to have but not critical - we can refresh it later.
            quote_symbol = stored_quote_symbol or NATIVE_SYMBOL_BY_CHAIN.get(chain, '')
            logger.debug(f"Deferring pool refresh for {token_contract[:8]}... (quote_symbol={quote_symbol}, will refresh later)")
        else:
            # Use stored quote_symbol - no API call needed!
            quote_symbol = stored_quote_symbol or NATIVE_SYMBOL_BY_CHAIN.get(chain, '')
            logger.debug(f"Using cached pool info for {token_contract[:8]}... (quote_symbol={quote_symbol})")
    else:
        # No canonical pool - need to fetch and select one
        picked = _select_canonical_pool_from_gt(chain, token_contract)
        if not picked:
            # Token not found on GeckoTerminal - return gracefully
            logger.warning(f"GeckoTerminal: Token not found ({chain}) - skipping backfill")
            return {
                'token_contract': token_contract,
                'chain': chain,
                'timeframe': timeframe,
                'pool_address': None,
                'dex_id': '',
                'inserted_rows': 0,
                'error': 'token_not_found'
            }
        pool_addr, dex_id, quote_symbol = picked
        # Store canonical pool with quote_symbol
        _update_canonical_pool_features(supabase, token_contract, chain, pool_addr, dex_id, quote_symbol)
    
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
        # Log at debug level - individual warnings are consolidated at decision_maker level
        logger.debug(f"Backfill {token_contract[:8]}.../{chain}/{timeframe}: Got {len(rows_to_insert)} bars (minimum: {bars_min})")
        # Still proceed, but log at debug level

    # Deduplicate rows by (token_contract, chain, timeframe, timestamp) before inserting
    seen = set()
    unique_rows = []
    for r in rows_to_insert:
        key = (r['token_contract'], r['chain'], r['timeframe'], r['timestamp'])
        if key not in seen:
            seen.add(key)
            unique_rows.append(r)
    
    if len(unique_rows) < len(rows_to_insert):
        logger.debug(f"Deduplicated {len(rows_to_insert)} rows to {len(unique_rows)} unique rows")
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