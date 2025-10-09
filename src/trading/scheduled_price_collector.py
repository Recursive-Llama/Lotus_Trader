#!/usr/bin/env python3
"""
Scheduled Price Collection System

Collects price data every minute for active position tokens and stores in database.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import requests

logger = logging.getLogger(__name__)


class ScheduledPriceCollector:
    """
    Scheduled price collection system for active position tokens
    
    Collects price data every minute from DexScreener API and stores in database.
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
        
        logger.info("Scheduled price collector initialized")
    
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
            # Elevated to WARNING for initial visibility that the loop is alive
            logger.warning("Price collection tick")
            try:
                await self._collect_prices_for_active_positions()
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
    
    async def _collect_prices_for_active_positions(self):
        """Collect prices for all active position tokens"""
        try:
            # Get active positions from database
            active_positions = await self._get_active_positions()
            
            if not active_positions:
                logger.info("No active positions found")
                return
            
            logger.info(f"Collecting prices for {len(active_positions)} active positions")
            
            # Group tokens by chain for batch API calls
            tokens_by_chain = self._group_tokens_by_chain(active_positions)
            
            # Collect prices for each chain
            for chain, tokens in tokens_by_chain.items():
                await self._collect_prices_for_chain(chain, tokens)
                
        except Exception as e:
            logger.error(f"Error collecting prices for active positions: {e}")
    
    async def _get_active_positions(self) -> List[Dict[str, Any]]:
        """Get active positions from database and add native tokens"""
        try:
            result = self.supabase_manager.client.table('lowcap_positions').select(
                'token_contract', 'token_chain'
            ).eq('status', 'active').execute()
            
            positions = result.data if result.data else []
            
            # Add native tokens for price collection (store WETH separately for each chain)
            native_tokens = [
                {'token_contract': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', 'token_chain': 'ethereum'},  # WETH on Ethereum
                {'token_contract': '0x4200000000000000000000000000000000000006', 'token_chain': 'base'},      # WETH on Base
                {'token_contract': '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c', 'token_chain': 'bsc'},       # WBNB
                {'token_contract': 'So11111111111111111111111111111111111111112', 'token_chain': 'solana'},    # SOL
            ]
            
            # Combine positions with native tokens
            all_tokens = positions + native_tokens
            
            if all_tokens:
                logger.info(f"Found {len(positions)} active positions + {len(native_tokens)} native tokens")
                return all_tokens
            else:
                return []
                
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
                        pairs = data.get('pairs', [])
                        
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
            # Find pairs for this token on this chain
            token_pairs = [
                p for p in pairs 
                if p.get('chainId') == chain and 
                (p.get('baseToken', {}).get('address', '').lower() == token_contract.lower() or
                 p.get('quoteToken', {}).get('address', '').lower() == token_contract.lower())
            ]
            
            if not token_pairs:
                logger.warning(f"No pairs found for token {token_contract} on {chain}")
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
                logger.warning(f"No stable pairs found for native token {chain}, using fallback: {fallback_pair.get('quoteToken', {}).get('symbol', 'UNKNOWN')}")
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
                logger.warning(f"No native token pairs found for {chain}, using fallback: {fallback_pair.get('quoteToken', {}).get('symbol', 'UNKNOWN')}")
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
            
            # If we got USDT pair for non-native tokens, convert to native price using current native/USD rate
            if quote_symbol == 'USDT' and price_usd > 0 and not is_native_token:
                native_usd_rate = self._get_native_usd_rate(chain)
                if native_usd_rate > 0:
                    price_native = price_usd / native_usd_rate
                    logger.info(f"Converted USDT price to native for {chain}: ${price_usd:.6f} USD -> {price_native:.6f} native")
            
            # Calculate volume and liquidity changes (will be 0 for first entry)
            volume_24h = float(pair.get('volume', {}).get('h24', 0))
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
                'volume_24h': volume_24h,
                'volume_change_1m': 0,  # Will be calculated on next run
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
                'volume_24h', 'liquidity_usd'
            ).eq('token_contract', token_contract).eq('chain', chain).order(
                'timestamp', desc=True
            ).limit(1).execute()
            
            if result.data:
                prev_data = result.data[0]
                prev_volume = float(prev_data.get('volume_24h', 0))
                prev_liquidity = float(prev_data.get('liquidity_usd', 0))
                
                # Calculate changes
                price_data['volume_change_1m'] = price_data['volume_24h'] - prev_volume
                price_data['liquidity_change_1m'] = price_data['liquidity_usd'] - prev_liquidity
            else:
                # First entry - no changes
                price_data['volume_change_1m'] = 0
                price_data['liquidity_change_1m'] = 0
                
        except Exception as e:
            logger.error(f"Error calculating changes: {e}")
            price_data['volume_change_1m'] = 0
            price_data['liquidity_change_1m'] = 0

    async def _log_heartbeat(self):
        """Log a lightweight heartbeat with recent insert counts per chain."""
        try:
            client = self.supabase_manager.client
            cutoff = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
            counts: Dict[str, int] = {}
            for chain in ['solana', 'ethereum', 'base', 'bsc']:
                try:
                    # Try to use exact count if supported
                    result = client.table('lowcap_price_data_1m').select('token_contract', count='exact').eq('chain', chain).gte('timestamp', cutoff).execute()
                    count_val = getattr(result, 'count', None)
                    if count_val is None:
                        count_val = len(result.data or [])
                    counts[chain] = int(count_val)
                except Exception:
                    # Best effort: fallback without breaking heartbeat
                    try:
                        data = client.table('lowcap_price_data_1m').select('token_contract').eq('chain', chain).gte('timestamp', cutoff).limit(1000).execute().data or []
                        counts[chain] = len(data)
                    except Exception:
                        counts[chain] = -1
            logger.warning(f"Price collector heartbeat: last_5m rows -> {counts}")
        except Exception as e:
            logger.warning(f"Price collector heartbeat error: {e}")


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
