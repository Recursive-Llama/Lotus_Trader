#!/usr/bin/env python3
"""
Scheduled Price Collection System

Collects price data every minute for active position tokens and stores in database.
Uses parallel async requests for scalability.

Tiered Collection Strategy:
- 0-250 tokens: Every 1 min, 60% coverage threshold
- 250-500 tokens: Every 2 min, 45% coverage threshold
- 500-750 tokens: Every 3 min, 33% coverage threshold
- etc.

Active/Watchlist 1m positions always collected every 1 minute (priority).
"""

import asyncio
import logging
import math
import os
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timezone, timedelta

import aiohttp

logger = logging.getLogger(__name__)

# Rate limits
MAX_CALLS_PER_MINUTE = 250  # DexScreener limit is 300, we use 250 for safety
MAX_CONCURRENT_REQUESTS = 50  # Max concurrent HTTP requests


class ScheduledPriceCollector:
    """
    Scheduled price collection system for active position tokens
    
    Collects price data every minute from DexScreener API and stores in database.
    Uses parallel async requests for scalability with tiered collection.
    """
    
    def __init__(self, supabase_manager, price_oracle):
        """
        Initialize scheduled price collector
        
        Args:
            supabase_manager: Database manager for position queries and price storage
            price_oracle: Price Oracle instance for price fetching
        """
        self.supabase_manager = supabase_manager
        self.price_oracle = price_oracle
        self.collecting = False
        self.collect_task = None
        
        # Track collection cycles for tiered collection
        self.current_cycle = 0  # Increments each minute
        self.last_collection_time: Dict[Tuple[str, str], datetime] = {}  # (token, chain) -> last collected
        
        logger.info("Scheduled price collector initialized (parallel mode)")
    
    async def start_collection(self, interval_minutes: int = 1):
        """
        Start scheduled price collection
        
        Args:
            interval_minutes: Minutes between price collection cycles
        """
        if self.collecting:
            logger.warning("Price collection already running")
            return
        
        self.collecting = True
        self.collect_task = asyncio.create_task(self._collection_loop(interval_minutes))
        # Elevated to WARNING to ensure visibility in logs during incident debugging
        logger.warning(f"Price collection started (interval: {interval_minutes} minutes)")
    
    async def stop_collection(self):
        """Stop scheduled price collection"""
        if not self.collecting:
            return
        
        self.collecting = False
        if self.collect_task:
            self.collect_task.cancel()
            try:
                await self.collect_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Price collection stopped")
    
    async def _collection_loop(self, interval_minutes: int):
        """Main collection loop"""
        last_heartbeat = datetime.now(timezone.utc)
        while self.collecting:
            # Log tick at debug level - heartbeat is logged every 5 minutes at INFO level
            logger.debug("Price collection tick")
            try:
                start_time = datetime.now(timezone.utc)
                await self._collect_prices_parallel()
                elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                logger.info(f"Price collection completed in {elapsed:.2f}s")
                
                # Increment cycle counter
                self.current_cycle += 1
                
                # Lightweight heartbeat approximately every 5 minutes
                now = datetime.now(timezone.utc)
                if (now - last_heartbeat) >= timedelta(minutes=5):
                    await self._log_heartbeat()
                    last_heartbeat = now
                await asyncio.sleep(interval_minutes * 60)  # Convert to seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in price collection loop: {e}")
                await asyncio.sleep(interval_minutes * 60)
    
    def _get_collection_interval(self, total_tokens: int) -> int:
        """
        Calculate collection interval based on total token count.
        
        Returns interval in minutes (1, 2, 3, etc.)
        - 0-250 tokens: Every 1 min
        - 250-500 tokens: Every 2 min
        - 500-750 tokens: Every 3 min
        - etc.
        """
        if total_tokens <= 0:
            return 1
        return max(1, math.ceil(total_tokens / MAX_CALLS_PER_MINUTE))
    
    def _get_coverage_threshold(self, interval: int) -> float:
        """
        Calculate coverage threshold based on collection interval.
        
        Returns threshold as decimal (0.60, 0.45, 0.33, etc.)
        Formula: threshold = 1 / interval (with buffer)
        """
        if interval <= 1:
            return 0.60  # 60% for every-minute collection
        elif interval == 2:
            return 0.45  # 45% for every-2-minute collection
        else:
            # Dynamic: (60 / interval) / 60 = 1/interval, with small buffer
            return max(0.20, (60 / interval - 2) / 60)  # Small buffer below theoretical max
    
    async def _get_priority_1m_positions(self) -> Set[Tuple[str, str]]:
        """
        Get active and watchlist 1m positions that need every-minute collection.
        
        Returns set of (token_contract, chain) tuples.
        """
        try:
            result = (
                self.supabase_manager.client.table('lowcap_positions')
                .select('token_contract', 'token_chain')
                .eq('timeframe', '1m')
                .in_('status', ['active', 'watchlist'])
                .execute()
            )
            
            priority_tokens = set()
            for row in (result.data or []):
                token = row.get('token_contract')
                chain = (row.get('token_chain') or '').lower()
                if token and chain:
                    priority_tokens.add((token, chain))
            
            return priority_tokens
        except Exception as e:
            logger.error(f"Error getting priority 1m positions: {e}")
            return set()
    
    def _should_collect_this_cycle(self, token: str, chain: str, interval: int, priority_1m: Set[Tuple[str, str]]) -> bool:
        """
        Determine if a token should be collected this cycle.
        
        Priority 1m tokens: Always collect
        Other tokens: Collect based on interval (cycle % interval == 0)
        """
        # Priority 1m tokens always collected
        if (token, chain) in priority_1m:
            return True
        
        # For interval-based collection, use hash to distribute tokens across cycles
        # This ensures even distribution and consistent collection
        token_hash = hash((token, chain)) % interval
        return (self.current_cycle % interval) == token_hash
    
    async def _collect_prices_parallel(self):
        """Collect prices using parallel async requests with tiered collection"""
        try:
            # Get all positions
            all_positions = await self._get_active_positions()
            
            if not all_positions:
                logger.info("No positions to collect prices for")
                return
            
            total_tokens = len(all_positions)
            
            # Calculate interval and threshold
            interval = self._get_collection_interval(total_tokens)
            threshold = self._get_coverage_threshold(interval)
            
            # Get priority 1m positions
            priority_1m = await self._get_priority_1m_positions()
            
            # Filter tokens to collect this cycle
            tokens_to_collect = []
            for pos in all_positions:
                token = pos.get('token_contract')
                chain = pos.get('token_chain', '').lower()
                
                # Hyperliquid prices are collected via WebSocket, not DexScreener
                if chain == 'hyperliquid':
                    continue
                    
                if token and chain and self._should_collect_this_cycle(token, chain, interval, priority_1m):
                    tokens_to_collect.append({'token_contract': token, 'token_chain': chain})
            
            # Log collection stats
            priority_count = sum(1 for pos in tokens_to_collect 
                               if (pos['token_contract'], pos['token_chain']) in priority_1m)
            logger.info(
                f"Collecting {len(tokens_to_collect)}/{total_tokens} tokens "
                f"(interval={interval}min, threshold={threshold:.0%}, priority_1m={priority_count}, cycle={self.current_cycle})"
            )
            
            if not tokens_to_collect:
                return
            
            # Collect prices in parallel
            await self._collect_prices_batch_parallel(tokens_to_collect)
            
            # Update P&L for all positions after price collection
            await self._update_all_positions_pnl()
            
            # Update wallet balances for all active chains
            await self._update_all_wallet_balances()
                
        except Exception as e:
            logger.error(f"Error in parallel price collection: {e}")
    
    async def _collect_prices_batch_parallel(self, positions: List[Dict[str, Any]]):
        """Collect prices for a batch of positions in parallel using aiohttp"""
        try:
            async with aiohttp.ClientSession() as session:
                # Create tasks for all tokens
                tasks = []
                for pos in positions:
                    token = pos['token_contract']
                    chain = pos['token_chain']
                    tasks.append(self._fetch_and_store_price(session, token, chain))
                
                # Run with concurrency limit
                results = []
                for i in range(0, len(tasks), MAX_CONCURRENT_REQUESTS):
                    batch = tasks[i:i + MAX_CONCURRENT_REQUESTS]
                    batch_results = await asyncio.gather(*batch, return_exceptions=True)
                    results.extend(batch_results)
                
                # Count successes and failures
                success_count = sum(1 for r in results if r is True)
                error_count = sum(1 for r in results if isinstance(r, Exception) or r is False)
                
                if error_count > 0:
                    logger.warning(f"Price collection: {success_count} success, {error_count} errors")
                else:
                    logger.debug(f"Price collection: {success_count} success")
                    
        except Exception as e:
            logger.error(f"Error in batch parallel collection: {e}")
    
    async def _fetch_and_store_price(self, session: aiohttp.ClientSession, token_contract: str, chain: str) -> bool:
        """Fetch price from DexScreener and store in database"""
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token_contract}"
            
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    pairs = data.get('pairs') or []
                    
                    # Process and store price data
                    await self._process_token_price_data(token_contract, chain, pairs)
                    
                    # Update last collection time
                    self.last_collection_time[(token_contract, chain)] = datetime.now(timezone.utc)
                    return True
                elif response.status == 429:
                    logger.warning(f"Rate limited for {token_contract[:8]}...")
                    return False
                else:
                    logger.debug(f"DexScreener API error for {token_contract[:8]}...: {response.status}")
                    return False
                    
        except asyncio.TimeoutError:
            logger.debug(f"Timeout fetching price for {token_contract[:8]}...")
            return False
        except Exception as e:
            logger.debug(f"Error fetching price for {token_contract[:8]}...: {e}")
            return False
    
    async def _collect_prices_for_active_positions(self):
        """Legacy method - redirects to parallel collection"""
        await self._collect_prices_parallel()
    
    async def _get_active_positions(self) -> List[Dict[str, Any]]:
        """Get active positions from database"""
        try:
            result = (
                self.supabase_manager.client.table('lowcap_positions')
                .select('token_contract', 'token_chain')
                .in_('status', ['active', 'watchlist', 'dormant'])
                .execute()
            )
            
            positions = result.data if result.data else []
            # Deduplicate by (token_contract, chain)
            unique = {}
            for pos in positions:
                token = (pos.get('token_contract'), (pos.get('token_chain') or '').lower())
                if token[0] and token[1] and token not in unique:
                    unique[token] = {
                        'token_contract': token[0],
                        'token_chain': token[1]
                    }
            
            unique_positions = list(unique.values())
            if unique_positions:
                logger.info(f"Found {len(unique_positions)} unique tokens across tracked positions")
            else:
                logger.info("No tracked positions found")
            return unique_positions
                
        except Exception as e:
            logger.error(f"Error getting active positions: {e}")
            return []
    
    def _group_tokens_by_chain(self, positions: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Group token contracts by chain"""
        tokens_by_chain = {}
        
        for position in positions:
            chain = position.get('token_chain', '').lower()
            token_contract = position.get('token_contract')
            
            if chain and token_contract:
                if chain not in tokens_by_chain:
                    tokens_by_chain[chain] = []
                tokens_by_chain[chain].append(token_contract)
        
        return tokens_by_chain
    
    async def _collect_prices_for_chain(self, chain: str, tokens: List[str]):
        """Collect prices for tokens on a specific chain using DexScreener API"""
        try:
            # Batch up to 30 tokens per API call (DexScreener limit)
            batch_size = 30
            for i in range(0, len(tokens), batch_size):
                batch = tokens[i:i + batch_size]
                await self._collect_batch_prices(chain, batch)
                
                # Add delay between batches to respect rate limits
                if i + batch_size < len(tokens):
                    await asyncio.sleep(1)
                    
        except Exception as e:
            logger.error(f"Error collecting prices for chain {chain}: {e}")
    
    async def _collect_batch_prices(self, chain: str, tokens: List[str]):
        """Collect prices for a batch of tokens using DexScreener API"""
        try:
            # Process each token individually using the same logic as Price Oracle
            for token in tokens:
                try:
                    # Call DexScreener API for single token (same as Price Oracle)
                    url = f"https://api.dexscreener.com/latest/dex/tokens/{token}"
                    response = requests.get(url, timeout=10)
                    
                    if response.ok:
                        data = response.json()
                        pairs = data.get('pairs') or []  # Handle None case
                        
                        # Process this token's price data
                        await self._process_token_price_data(token, chain, pairs)
                    else:
                        logger.error(f"DexScreener API error for {token}: {response.status_code}")
                        
                except Exception as e:
                    logger.error(f"Error collecting price for {token}: {e}")
                
        except Exception as e:
            logger.error(f"Error collecting batch prices: {e}")
    
    async def _process_token_price_data(self, token_contract: str, chain: str, pairs: List[Dict]):
        """Process and store price data for a single token"""
        try:
            # Ensure pairs is a list (handle None case)
            if pairs is None:
                pairs = []
            
            # Find pairs for this token on this chain
            token_pairs = [
                p for p in pairs 
                if p.get('chainId') == chain and 
                (p.get('baseToken', {}).get('address', '').lower() == token_contract.lower() or
                 p.get('quoteToken', {}).get('address', '').lower() == token_contract.lower())
            ]
            
            if not token_pairs:
                logger.debug(f"No pairs found for token {token_contract} on {chain}")
                return
            
            # Get the best pair - prioritize native token pairs (WETH, SOL, BNB)
            best_pair = self._get_best_pair_with_native_preference(token_pairs, chain, token_contract)
            
            # Extract price data
            price_data = self._extract_price_data(best_pair, token_contract, chain)
            
            if price_data:
                # Store in database
                await self._store_price_data(price_data)
                
        except Exception as e:
            logger.error(f"Error processing price data for {token_contract}: {e}")
    
    def _get_best_pair_with_native_preference(self, pairs: List[Dict], chain: str, token_contract: str) -> Dict:
        """Get the best pair, prioritizing native token pairs (WETH, SOL, BNB) for position tokens, USDC/USDT for native tokens"""
        # Check if this is a native token we're collecting
        native_addresses = {
            'ethereum': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',  # WETH
            'bsc': '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c',       # WBNB
            'solana': 'So11111111111111111111111111111111111111112',    # SOL
        }
        
        is_native_token = token_contract.lower() == native_addresses.get(chain, '').lower()
        
        if is_native_token:
            # For native tokens, prioritize USDC/USDT pairs
            stable_pairs = [
                p for p in pairs 
                if p.get('quoteToken', {}).get('symbol', '').upper() in ['USDC', 'USDT']
            ]
            
            if stable_pairs:
                best_pair = max(stable_pairs, key=lambda p: p.get('liquidity', {}).get('usd', 0))
                logger.info(f"Using stable pair for native token {chain}: {best_pair.get('quoteToken', {}).get('symbol', 'UNKNOWN')}")
                return best_pair
            else:
                # Fallback to highest liquidity
                fallback_pair = max(pairs, key=lambda p: p.get('liquidity', {}).get('usd', 0))
                # Informational only; downgrade to info to avoid noisy terminal warnings
                logger.info(f"No stable pairs found for native token {chain}, using fallback: {fallback_pair.get('quoteToken', {}).get('symbol', 'UNKNOWN')}")
                return fallback_pair
        else:
            # For position tokens, prioritize native token pairs (WETH, SOL, BNB)
            native_tokens = {
                'base': '0x4200000000000000000000000000000000000006',      # WETH
                'ethereum': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',  # WETH
                'bsc': '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c',       # WBNB
                'solana': 'So11111111111111111111111111111111111111112',    # SOL
            }
            
            native_address = native_tokens.get(chain)
            if not native_address:
                return max(pairs, key=lambda p: p.get('liquidity', {}).get('usd', 0))
            
            # Filter for native token pairs first (quote token only, like Price Oracle)
            native_pairs = [
                p for p in pairs 
                if p.get('quoteToken', {}).get('address', '').lower() == native_address.lower()
            ]
            
            if native_pairs:
                # Get the native pair with highest liquidity
                best_pair = max(native_pairs, key=lambda p: p.get('liquidity', {}).get('usd', 0))
                logger.info(f"Using native token pair for {chain}: {best_pair.get('quoteToken', {}).get('symbol', 'UNKNOWN')}")
                return best_pair
            else:
                # Fallback to any pair with highest liquidity
                fallback_pair = max(pairs, key=lambda p: p.get('liquidity', {}).get('usd', 0))
                # Informational only; downgrade to info to avoid noisy terminal warnings
                logger.info(f"No native token pairs found for {chain}, using fallback: {fallback_pair.get('quoteToken', {}).get('symbol', 'UNKNOWN')}")
                return fallback_pair
    
    def _get_native_usd_rate(self, chain: str) -> float:
        """Get current native token USD rate from database"""
        try:
            # Native token addresses (WETH stored separately for each chain)
            native_addresses = {
                'ethereum': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',  # WETH
                'base': '0x4200000000000000000000000000000000000006',      # WETH (Base)
                'bsc': '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c',       # WBNB
                'solana': 'So11111111111111111111111111111111111111112',    # SOL
            }
            
            native_address = native_addresses.get(chain)
            if not native_address:
                return 0.0
            
            # Use the actual chain for lookup - store native prices separately for each chain
            lookup_chain = chain
            
            # Get latest native token price from database
            result = self.supabase_manager.client.table('lowcap_price_data_1m').select(
                'price_usd'
            ).eq('token_contract', native_address).eq('chain', lookup_chain).order(
                'timestamp', desc=True
            ).limit(1).execute()
            
            if result.data and len(result.data) > 0:
                return float(result.data[0]['price_usd'])
            else:
                logger.warning(f"No native token price found in database for {chain} (lookup: {lookup_chain})")
                return 0.0
                
        except Exception as e:
            logger.error(f"Error getting native USD rate for {chain}: {e}")
            return 0.0
    
    def _extract_price_data(self, pair: Dict, token_contract: str, chain: str) -> Optional[Dict[str, Any]]:
        """Extract price data from DexScreener pair data"""
        try:
            # Check if this is a native token
            native_addresses = {
                'ethereum': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
                'base': '0x4200000000000000000000000000000000000006',
                'bsc': '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c',
                'solana': 'So11111111111111111111111111111111111111112',
            }
            
            is_native_token = token_contract.lower() == native_addresses.get(chain, '').lower()
            
            # Determine if token is base or quote
            base_token = pair.get('baseToken', {})
            quote_token = pair.get('quoteToken', {})
            
            is_base_token = base_token.get('address', '').lower() == token_contract.lower()
            
            if is_base_token:
                price_native = float(pair.get('priceNative', 0))
                price_usd = float(pair.get('priceUsd', 0))
                quote_symbol = quote_token.get('symbol', 'UNKNOWN')
            else:
                # Token is quote token, need to invert price
                price_native = 1.0 / float(pair.get('priceNative', 1)) if pair.get('priceNative') else 0
                price_usd = 1.0 / float(pair.get('priceUsd', 1)) if pair.get('priceUsd') else 0
                quote_symbol = base_token.get('symbol', 'UNKNOWN')
            
            # For native tokens, price_native should be 1.0 (1 native token = 1 native token)
            # but we still need to store the USD price correctly
            if is_native_token:
                price_native = 1.0
                # Keep the USD price as is - this is the actual price we want to store
            else:
                # For non-native tokens, price_native is calculated from priceNative field
                # (already set above from pair data, no conversion needed since we use USD prices)
                pass
            
            # Get volume data from Dexscreener (multi-timeframe volumes)
            volume_data = pair.get('volume', {})
            volume_24h = float(volume_data.get('h24', 0))
            volume_6h = float(volume_data.get('h6', 0))
            volume_1h = float(volume_data.get('h1', 0))
            volume_5m = float(volume_data.get('m5', 0))  # 5-minute rolling volume
            
            # Calculate 1m volume as m5 / 5 (simple average)
            volume_1m = volume_5m / 5.0 if volume_5m > 0 else 0
            
            liquidity_usd = float(pair.get('liquidity', {}).get('usd', 0))
            
            return {
                'token_contract': token_contract,
                'chain': chain,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'price_usd': price_usd,
                'price_native': price_native,
                'quote_token': quote_symbol,
                'liquidity_usd': liquidity_usd,
                'liquidity_change_1m': 0,  # Will be calculated on next run
                'volume_5m': volume_5m,  # Store 5-minute volume
                'volume_1m': volume_1m,  # Calculated 1-minute volume (m5/5)
                'volume_1h': volume_1h,  # 1-hour volume for 1h rollups
                'volume_6h': volume_6h,  # 6-hour volume for 4h rollups
                'volume_24h': volume_24h,  # 24-hour volume for 1d rollups
                'price_change_24h': float(pair.get('priceChange', {}).get('h24', 0)),
                'market_cap': float(pair.get('marketCap', 0)),
                'fdv': float(pair.get('fdv', 0)),
                'dex_id': pair.get('dexId', ''),
                'pair_address': pair.get('pairAddress', ''),
                'source': 'dexscreener'
            }
            
        except Exception as e:
            logger.error(f"Error extracting price data: {e}")
            return None
    
    async def _store_price_data(self, price_data: Dict[str, Any]):
        """Store price data in database"""
        try:
            # Calculate volume and liquidity changes from previous entry
            await self._calculate_changes(price_data)
            
            # Insert into database
            result = self.supabase_manager.client.table('lowcap_price_data_1m').insert(price_data).execute()
            
            if result.data:
                logger.debug(f"Stored price data for {price_data['token_contract']} on {price_data['chain']}")
            else:
                logger.error(f"Failed to store price data for {price_data['token_contract']}")
                
        except Exception as e:
            logger.error(f"Error storing price data: {e}")
    
    async def _calculate_changes(self, price_data: Dict[str, Any]):
        """Calculate volume and liquidity changes from previous entry"""
        try:
            token_contract = price_data['token_contract']
            chain = price_data['chain']
            
            # Get previous entry
            result = self.supabase_manager.client.table('lowcap_price_data_1m').select(
                'liquidity_usd'
            ).eq('token_contract', token_contract).eq('chain', chain).order(
                'timestamp', desc=True
            ).limit(1).execute()
            
            if result.data:
                prev_data = result.data[0]
                prev_liquidity = float(prev_data.get('liquidity_usd', 0))
                
                price_data['liquidity_change_1m'] = price_data['liquidity_usd'] - prev_liquidity
            else:
                # First entry - no changes
                price_data['liquidity_change_1m'] = 0
                
        except Exception as e:
            logger.error(f"Error calculating changes: {e}")
            price_data['liquidity_change_1m'] = 0

    async def _log_heartbeat(self):
        """Log a lightweight heartbeat with heart glyph and HL WS status."""
        try:
            client = self.supabase_manager.client
            cutoff = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
            
            # Check lowcap price data (simplified - check for new 1m rows in last 5 mins)
            try:
                result = client.table('lowcap_price_data_ohlc').select('token_contract').eq('timeframe', '1m').gte('timestamp', cutoff).limit(1).execute()
                has_lowcap_data = len(result.data or []) > 0
            except Exception:
                has_lowcap_data = False
            
            # Check Hyperliquid WS status (majors data)
            hl_status = "?"
            try:
                hl_result = client.table('majors_price_data_ohlc').select('timestamp').eq('source', 'hyperliquid').order('timestamp', desc=True).limit(1).execute()
                if hl_result.data:
                    latest_ts = datetime.fromisoformat(hl_result.data[0]['timestamp'].replace('Z', '+00:00'))
                    age_minutes = (datetime.now(timezone.utc) - latest_ts).total_seconds() / 60
                    if age_minutes < 5:
                        hl_status = "✓"
                    elif age_minutes < 30:
                        hl_status = "⚠"
                    else:
                        hl_status = "✗"
                else:
                    hl_status = "✗"
            except Exception:
                hl_status = "?"
            
            # Simple heartbeat: ❦ glyph + status indicators
            status_parts = []
            if has_lowcap_data:
                status_parts.append("lowcap")
            status_parts.append(f"HL:{hl_status}")
            
            logger.info(f"❦ {' '.join(status_parts)}")
        except Exception as e:
            logger.debug(f"Heartbeat check error: {e}")

    async def _update_all_positions_pnl(self):
        """Update P&L for all active positions using current database prices"""
        try:
            # Get all active positions
            result = self.supabase_manager.client.table('lowcap_positions').select('*').eq('status', 'active').execute()
            active_positions = result.data if result.data else []
            
            if not active_positions:
                logger.info("No active positions to update P&L for")
                return
            
            # Update P&L for each position
            updated_count = 0
            for position in active_positions:
                try:
                    await self._update_position_pnl(position['id'])
                    updated_count += 1
                except Exception as e:
                    logger.error(f"Error updating P&L for position {position.get('id', 'unknown')}: {e}")
            
            logger.info(f"Updated P&L for {updated_count}/{len(active_positions)} active positions")
            
        except Exception as e:
            logger.error(f"Error updating all positions P&L: {e}")

    async def _update_position_pnl(self, position_id: str) -> bool:
        """Update position P&L using current market prices"""
        try:
            # Get position data
            result = self.supabase_manager.client.table('lowcap_positions').select('*').eq('id', position_id).execute()
            if not result.data:
                return False
            
            position = result.data[0]
            
            # Get current price from database
            token_contract = position.get('token_contract')
            token_chain = position.get('token_chain', '').lower()
            if not token_contract or not token_chain:
                return False
                
            current_price_usd = await self._get_current_price_usd_from_db(token_contract, token_chain)
            if current_price_usd is None:
                logger.warning(f"Could not get current USD price for {token_contract} on {token_chain}")
                return False
            
            # Calculate P&L (USD)
            total_quantity = float(position.get('total_quantity', 0.0) or 0.0)
            total_investment_usd = float(position.get('total_allocation_usd', 0.0) or 0.0)
            total_extracted_usd = float(position.get('total_extracted_usd', 0.0) or 0.0)
            
            # Reconcile total_quantity = total_tokens_bought - total_tokens_sold
            total_tokens_bought = float(position.get('total_tokens_bought', 0.0) or 0.0)
            total_tokens_sold = float(position.get('total_tokens_sold', 0.0) or 0.0)
            expected_quantity = total_tokens_bought - total_tokens_sold
            
            # Update total_quantity if it's wrong
            if abs(total_quantity - expected_quantity) > 0.0001:
                logger.info(f"Reconciling {position_id} quantity: {total_quantity:.8f} -> {expected_quantity:.8f}")
                total_quantity = expected_quantity
            
            current_position_value_usd = total_quantity * current_price_usd
            total_pnl_usd = (total_extracted_usd + current_position_value_usd) - total_investment_usd
            total_pnl_pct = (total_pnl_usd / total_investment_usd * 100.0) if total_investment_usd > 0 else 0.0
            
            # Update position
            update_data = {
                'total_quantity': total_quantity,
                'current_usd_value': current_position_value_usd,
                'total_pnl_usd': total_pnl_usd,
                'total_pnl_pct': total_pnl_pct,
                'pnl_last_calculated_at': datetime.now(timezone.utc).isoformat()
            }
            
            result = self.supabase_manager.client.table('lowcap_positions').update(update_data).eq('id', position_id).execute()
            if result.data:
                logger.info(f"Updated P&L for {position_id}: {total_pnl_pct:.2f}% (${total_pnl_usd:.2f})")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error updating P&L for position {position_id}: {e}")
            return False

    async def _get_current_price_usd_from_db(self, token_contract: str, chain: str) -> Optional[float]:
        """Get current USD price from database (supporting both Lowcap and Hyperliquid tables)"""
        try:
            if chain == 'hyperliquid':
                # Hyperliquid data is in a separate table (ingested via WS)
                # Note: Hyperliquid table uses 'token' instead of 'token_contract', and 'close' instead of 'price_usd'
                # We use the most recent 1m candle as "current price"
                result = self.supabase_manager.client.table('hyperliquid_price_data_ohlc').select(
                    'close'
                ).eq('token', token_contract).eq('timeframe', '1m').order(
                    'ts', desc=True
                ).limit(1).execute()
                
                if result.data and len(result.data) > 0:
                    return float(result.data[0]['close'])
            else:
                # Standard lowcap tokens (DexScreener)
                result = self.supabase_manager.client.table('lowcap_price_data_1m').select(
                    'price_usd'
                ).eq('token_contract', token_contract).eq('chain', chain).order(
                    'timestamp', desc=True
                ).limit(1).execute()
                
                if result.data and len(result.data) > 0:
                    return float(result.data[0]['price_usd'])
                    
            return None
            
        except Exception as e:
            logger.error(f"Error getting current USD price from database for {token_contract} ({chain}): {e}")
            return None

    async def _get_native_usd_rate_async(self, chain: str) -> float:
        """Get current native token USD rate from database"""
        try:
            # Native token addresses
            native_addresses = {
                'ethereum': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',  # WETH
                'base': '0x4200000000000000000000000000000000000006',      # WETH (Base)
                'bsc': '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c',       # WBNB
                'solana': 'So11111111111111111111111111111111111111112',    # SOL
            }
            
            native_address = native_addresses.get(chain)
            if not native_address:
                return 0.0
            
            # Get latest native token price from database
            result = self.supabase_manager.client.table('lowcap_price_data_1m').select(
                'price_usd'
            ).eq('token_contract', native_address).eq('chain', chain).order(
                'timestamp', desc=True
            ).limit(1).execute()
            
            if result.data and len(result.data) > 0:
                return float(result.data[0]['price_usd'])
            else:
                logger.warning(f"No native token price found in database for {chain}")
                return 0.0
                
        except Exception as e:
            logger.error(f"Error getting native USD rate for {chain}: {e}")
            return 0.0

    async def _update_all_wallet_balances(self):
        """
        Update wallet balances for home chain (Solana) and Hyperliquid.
        
        - Solana: USDC balance (home chain capital)
        - Hyperliquid: Margin balance (collateral for perpetuals)
        """
        try:
            home_chain = os.getenv("HOME_CHAIN", "solana").lower()
            
            # Update home chain (Solana) - this is where all USDC capital is
            await self._update_wallet_balance_for_chain(home_chain)
            
            # Update Hyperliquid margin balance
            await self._update_hyperliquid_balance()
                
        except Exception as e:
            logger.error(f"Error updating wallet balances: {e}")
    
    async def _update_wallet_balance_for_chain(self, chain: str):
        """
        Update wallet balance for Solana (home chain) only.
        
        Tracks:
        - SOL balance: For gas tracking only (not trading capital)
        - USDC balance: This is the trading capital (all capital is on Solana USDC)
        
        Note: Other chains (Base, Ethereum, BSC) are not tracked - we trade via Li.Fi
        from Solana USDC, so their balances are irrelevant.
        """
        try:
            # Get wallet balance from the wallet manager
            if hasattr(self.supabase_manager, 'wallet_manager'):
                wallet_manager = self.supabase_manager.wallet_manager
            else:
                # Fallback: try to get wallet manager from price oracle
                if hasattr(self.price_oracle, 'wallet_manager'):
                    wallet_manager = self.price_oracle.wallet_manager
                else:
                    logger.warning(f"No wallet manager available for {chain} balance update")
                    return
            
            updates = {
                'chain': chain,
                'wallet_address': wallet_manager.get_wallet_address(chain),
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
            # Fetch native token balance (SOL) - for gas tracking only
            # Note: Native tokens (SOL/ETH/BNB) are NOT trading capital, just gas
            native_balance = await wallet_manager.get_balance(chain, None)  # None for native token
            if native_balance is not None:
                updates['balance'] = float(native_balance)
                # Don't convert to USD - native tokens are just for gas, not trading capital
                # balance_usd field is not meaningful for native tokens in this context
            else:
                logger.warning(f"Could not get {chain} native token balance")
                updates['balance'] = 0.0
            
            # Fetch USDC balance - THIS is the trading capital
            # All capital is centralized on Solana USDC (home chain)
            usdc_address = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'  # Solana USDC
            try:
                usdc_balance = await wallet_manager.get_balance(chain, usdc_address)
                if usdc_balance is not None:
                    # USDC balance IS the trading capital (already in USD terms)
                    updates['usdc_balance'] = float(usdc_balance)
                    logger.debug(f"Updated {chain} USDC balance: {usdc_balance:.2f}")
                else:
                    logger.warning(f"Could not get {chain} USDC balance")
                    updates['usdc_balance'] = 0.0
            except Exception as e:
                logger.warning(f"Error fetching USDC balance for {chain}: {e}")
                updates['usdc_balance'] = 0.0
            
            # Update wallet balance in database
            self.supabase_manager.client.table('wallet_balances').upsert(updates).execute()
            
            balance_display = f"{updates.get('balance', 0):.6f} SOL"
            if 'usdc_balance' in updates:
                balance_display += f", ${updates.get('usdc_balance', 0):.2f} USDC"
            logger.debug(f"Updated {chain} wallet balance: {balance_display}")
            
        except Exception as e:
            logger.error(f"Error updating {chain} wallet balance: {e}")
    
    async def _update_hyperliquid_balance(self):
        """
        Update Hyperliquid margin balance (USDC collateral).
        
        Hyperliquid uses margin/collateral separate from Solana USDC.
        This balance is used for allocation calculations for Hyperliquid positions.
        """
        try:
            # Use specific logger for Hyperliquid operations to route to correct log file
            hl_logger = logging.getLogger("hyperliquid_balance")
            
            # Check if Hyperliquid is enabled
            hl_enabled = os.getenv("HL_INGEST_ENABLED", "0")
            if hl_enabled != "1":
                hl_logger.debug(f"Skipping Hyperliquid balance update: HL_INGEST_ENABLED={hl_enabled}")
                return
            
            # Import here to avoid circular dependencies
            from src.intelligence.lowcap_portfolio_manager.pm.hyperliquid_executor import HyperliquidExecutor
            
            executor = HyperliquidExecutor()
            hl_logger.debug("Fetching Hyperliquid margin balance...")
            margin_balance = executor.get_margin_balance()
            
            if margin_balance is None:
                hl_logger.warning("Could not get Hyperliquid margin balance (returned None)")
                return
            
            # Get account address for wallet_address field
            account_address = os.getenv("HL_ACCOUNT_ADDRESS", "")
            
            # Update wallet_balances table
            updates = {
                'chain': 'hyperliquid',
                'balance': float(margin_balance),  # Required field: map margin to balance
                'usdc_balance': float(margin_balance),
                'balance_usd': float(margin_balance),
                'wallet_address': account_address,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
            self.supabase_manager.client.table('wallet_balances').upsert(updates).execute()
            logger.debug(f"Updated Hyperliquid margin balance: ${margin_balance:.2f}")
            
        except ImportError:
            logger.debug("HyperliquidExecutor not available, skipping Hyperliquid balance update")
        except Exception as e:
            logger.warning(f"Error updating Hyperliquid balance: {e}")


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def test_price_collector():
        """Test price collector functionality"""
        try:
            print("📊 Price Collector Test")
            print("=" * 40)
            
            # This would require actual database and price oracle setup
            print("Price collector test requires database and price oracle setup")
            print("Run this as part of the main trading system")
            
        except Exception as e:
            print(f"❌ Error testing price collector: {e}")
    
    # Run test
    asyncio.run(test_price_collector())
