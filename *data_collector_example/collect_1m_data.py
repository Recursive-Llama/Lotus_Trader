#!/usr/bin/env python3
"""
1-Minute Data Collector for Dexscreener

Collects price data from Dexscreener API and stores raw 1-minute price points
in the database. This is the first step in the OHLCV data pipeline.

Usage:
    python collect_1m_data.py          # Run once
    python collect_1m_data.py --loop   # Run continuously every minute
"""

import asyncio
import logging
import sys
import argparse
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import requests
from supabase import create_client, Client

# Import configuration
import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DexscreenerCollector:
    """Collects 1-minute price data from Dexscreener API"""
    
    def __init__(self):
        """Initialize the collector with database connection"""
        # Validate config
        errors = config.validate_config()
        if errors:
            logger.error("Configuration errors found:")
            for error in errors:
                logger.error(f"  - {error}")
            raise ValueError("Invalid configuration. Fix errors above.")
        
        # Initialize Supabase client
        self.sb: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        logger.info("Initialized Dexscreener collector")
    
    def collect_prices(self) -> Dict[str, int]:
        """
        Collect prices for all configured tokens
        
        Returns:
            Dictionary with counts: {"collected": N, "errors": M}
        """
        logger.info(f"Starting price collection for {len(config.TOKENS_TO_TRACK)} tokens on {config.DEFAULT_CHAIN}")
        
        collected = 0
        errors = 0
        
        for token_contract in config.TOKENS_TO_TRACK:
            chain = config.DEFAULT_CHAIN
            
            try:
                success = self._collect_token_price(token_contract, chain)
                if success:
                    collected += 1
                else:
                    errors += 1
            except Exception as e:
                logger.error(f"Error collecting price for {token_contract} on {chain}: {e}")
                errors += 1
        
        logger.info(f"Price collection complete: {collected} collected, {errors} errors")
        return {"collected": collected, "errors": errors}
    
    def _collect_token_price(self, token_contract: str, chain: str) -> bool:
        """
        Collect price for a single token
        
        Args:
            token_contract: Token contract address
            chain: Chain name (ethereum, base, bsc, solana)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Call Dexscreener API
            url = f"{config.DEXSCREENER_API_BASE}/{token_contract}"
            response = requests.get(url, timeout=config.DEXSCREENER_TIMEOUT)
            
            if not response.ok:
                logger.error(f"Dexscreener API error for {token_contract}: {response.status_code}")
                return False
            
            data = response.json()
            pairs = data.get('pairs', [])
            
            if not pairs:
                logger.warning(f"No pairs found for token {token_contract}")
                return False
            
            # Find the best pair for this chain
            best_pair = self._get_best_pair(pairs, chain, token_contract)
            
            if not best_pair:
                logger.warning(f"No suitable pair found for {token_contract} on {chain}")
                return False
            
            # Extract price data
            price_data = self._extract_price_data(best_pair, token_contract, chain)
            
            if not price_data:
                logger.warning(f"Could not extract price data for {token_contract}")
                return False
            
            # Store in database
            self._store_price_data(price_data)
            
            logger.debug(f"Collected price for {token_contract} on {chain}: ${price_data['price_usd']:.6f}")
            return True
            
        except Exception as e:
            logger.error(f"Error collecting price for {token_contract} on {chain}: {e}")
            return False
    
    def _get_best_pair(self, pairs: List[Dict], chain: str, token_contract: str) -> Optional[Dict]:
        """
        Get the best pair for a token, prioritizing native token pairs
        
        Args:
            pairs: List of pairs from Dexscreener
            chain: Chain name
            token_contract: Token contract address
            
        Returns:
            Best pair dictionary or None
        """
        # Filter pairs for this chain
        chain_pairs = [
            p for p in pairs 
            if p.get('chainId', '').lower() == chain.lower()
        ]
        
        if not chain_pairs:
            return None
        
        # Native token addresses for each chain
        native_addresses = {
            'ethereum': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',  # WETH
            'base': '0x4200000000000000000000000000000000000006',      # WETH
            'bsc': '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c',       # WBNB
            'solana': 'So11111111111111111111111111111111111111112',    # SOL
        }
        
        native_address = native_addresses.get(chain.lower())
        
        # Prioritize native token pairs (quote token)
        if native_address:
            native_pairs = [
                p for p in chain_pairs 
                if p.get('quoteToken', {}).get('address', '').lower() == native_address.lower()
            ]
            
            if native_pairs:
                # Return pair with highest liquidity
                return max(native_pairs, key=lambda p: p.get('liquidity', {}).get('usd', 0))
        
        # Fallback: return pair with highest liquidity
        return max(chain_pairs, key=lambda p: p.get('liquidity', {}).get('usd', 0))
    
    def _extract_price_data(self, pair: Dict, token_contract: str, chain: str) -> Optional[Dict[str, Any]]:
        """
        Extract price data from Dexscreener pair data
        
        Args:
            pair: Pair data from Dexscreener
            token_contract: Token contract address
            chain: Chain name
            
        Returns:
            Price data dictionary or None
        """
        try:
            base_token = pair.get('baseToken', {})
            quote_token = pair.get('quoteToken', {})
            
            # Determine if token is base or quote
            is_base_token = base_token.get('address', '').lower() == token_contract.lower()
            
            if is_base_token:
                # Token is base token
                price_native = float(pair.get('priceNative', 0))
                price_usd = float(pair.get('priceUsd', 0))
            else:
                # Token is quote token, need to invert price
                price_native_raw = float(pair.get('priceNative', 1))
                price_usd_raw = float(pair.get('priceUsd', 1))
                price_native = 1.0 / price_native_raw if price_native_raw > 0 else 0
                price_usd = 1.0 / price_usd_raw if price_usd_raw > 0 else 0
            
            # Get volume data from Dexscreener
            volume_data = pair.get('volume', {})
            volume_24h = float(volume_data.get('h24', 0))
            volume_6h = float(volume_data.get('h6', 0))
            volume_1h = float(volume_data.get('h1', 0))
            volume_5m = float(volume_data.get('m5', 0))  # 5-minute rolling volume
            
            # Calculate 1m volume as m5 / 5 (simple average)
            volume_1m = volume_5m / 5.0 if volume_5m > 0 else 0
            
            return {
                'token_contract': token_contract,
                'chain': chain.lower(),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'price_usd': price_usd,
                'price_native': price_native,
                'volume': volume_5m,  # Store 5-minute volume
                'volume_1m': volume_1m,  # Calculated 1-minute volume (m5/5)
                'volume_1h': volume_1h,  # 1-hour volume for 1h rollups
                'volume_6h': volume_6h,  # 6-hour volume for 4h rollups
                'volume_24h': volume_24h,  # 24-hour volume for 1d rollups
                'source': 'dexscreener'
            }
            
        except Exception as e:
            logger.error(f"Error extracting price data: {e}")
            return None
    
    def _store_price_data(self, price_data: Dict[str, Any]):
        """
        Store price data in database
        
        Args:
            price_data: Price data dictionary
        """
        try:
            # Calculate volume change from previous entry
            self._calculate_volume_change(price_data)
            
            # Insert into database
            result = self.sb.table(config.TABLE_1M_PRICE_DATA).insert(price_data).execute()
            
            if result.data:
                logger.debug(f"Stored price data for {price_data['token_contract']} on {price_data['chain']}")
            else:
                logger.warning(f"Failed to store price data for {price_data['token_contract']}")
                
        except Exception as e:
            logger.error(f"Error storing price data: {e}")
    
    def _calculate_volume_change(self, price_data: Dict[str, Any]):
        """
        Volume is already calculated in _extract_price_data (m5/5 for 1m)
        This method is kept for compatibility but doesn't need to do anything
        """
        # Volume calculation is done in _extract_price_data
        pass


async def run_loop(collector: DexscreenerCollector, interval_minutes: int):
    """Run collection in a loop"""
    logger.info(f"Starting collection loop (interval: {interval_minutes} minutes)")
    
    while True:
        try:
            collector.collect_prices()
            await asyncio.sleep(interval_minutes * 60)
        except KeyboardInterrupt:
            logger.info("Stopping collection loop")
            break
        except Exception as e:
            logger.error(f"Error in collection loop: {e}")
            await asyncio.sleep(interval_minutes * 60)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Collect 1-minute price data from Dexscreener")
    parser.add_argument(
        '--loop',
        action='store_true',
        help='Run continuously every minute'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=config.COLLECTION_INTERVAL_MINUTES,
        help=f'Collection interval in minutes (default: {config.COLLECTION_INTERVAL_MINUTES})'
    )
    
    args = parser.parse_args()
    
    try:
        collector = DexscreenerCollector()
        
        if args.loop:
            # Run in loop
            asyncio.run(run_loop(collector, args.interval))
        else:
            # Run once
            results = collector.collect_prices()
            logger.info(f"Collection complete: {results['collected']} collected, {results['errors']} errors")
            
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

