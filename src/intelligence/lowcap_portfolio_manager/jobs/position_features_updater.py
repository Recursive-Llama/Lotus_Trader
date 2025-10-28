#!/usr/bin/env python3
"""
Position Features Updater

Updates lowcap_positions.features with pair_created_at and market_cap data
from DexScreener and price data sources.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import requests
import asyncio
import aiohttp

from supabase import create_client, Client

logger = logging.getLogger(__name__)


class PositionFeaturesUpdater:
    """Updates position features with DexScreener and price data"""
    
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL", "")
        self.supabase_key = os.getenv("SUPABASE_ANON_KEY", "")
        self.sb: Client = create_client(self.supabase_url, self.supabase_key)
        
    async def run(self) -> int:
        """Update features for all active positions"""
        updated = 0
        
        try:
            # Get all active positions
            result = self.sb.table("lowcap_positions").select(
                "id,token_contract,token_chain,token_ticker,features"
            ).eq("status", "active").execute()
            
            positions = result.data or []
            logger.info(f"Found {len(positions)} active positions to update")
            
            for position in positions:
                try:
                    updated_features = await self._update_position_features(position)
                    if updated_features:
                        # Update the position with new features
                        self.sb.table("lowcap_positions").update({
                            "features": updated_features
                        }).eq("id", position["id"]).execute()
                        
                        updated += 1
                        logger.info(f"Updated features for {position['token_ticker']} ({position['id']})")
                        
                except Exception as e:
                    logger.error(f"Error updating position {position['id']}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in position features updater: {e}")
            
        logger.info(f"Position features updater completed: {updated} positions updated")
        return updated
    
    async def _update_position_features(self, position: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update features for a single position"""
        try:
            token_contract = position["token_contract"]
            token_chain = position["token_chain"]
            features = position.get("features", {})
            
            # Check if we already have the data
            has_pair_created_at = "pair_created_at" in features
            has_market_cap = "market_cap" in features
            
            if has_pair_created_at and has_market_cap:
                logger.debug(f"Position {position['id']} already has required features")
                return None
            
            updated_features = dict(features)
            
            # Get DexScreener data if missing pair_created_at
            if not has_pair_created_at:
                dexscreener_data = await self._get_dexscreener_data(token_contract, token_chain)
                if dexscreener_data:
                    updated_features["pair_created_at"] = dexscreener_data.get("pair_created_at", "")
                    updated_features["market_cap"] = dexscreener_data.get("market_cap", 0.0)
                else:
                    logger.warning(f"Could not get DexScreener data for {token_contract}")
            
            # Get market cap from price data if missing
            elif not has_market_cap:
                market_cap = await self._get_market_cap_from_price_data(token_contract, token_chain)
                if market_cap is not None:
                    updated_features["market_cap"] = market_cap
                else:
                    logger.warning(f"Could not get market cap for {token_contract}")
            
            # Add update timestamp
            updated_features["features_updated_at"] = datetime.now(timezone.utc).isoformat()
            
            return updated_features
            
        except Exception as e:
            logger.error(f"Error updating features for position {position.get('id', 'unknown')}: {e}")
            return None
    
    async def _get_dexscreener_data(self, token_contract: str, token_chain: str) -> Optional[Dict[str, Any]]:
        """Get DexScreener data for a token"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://api.dexscreener.com/latest/dex/tokens/{token_contract}",
                    timeout=10
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        pairs = data.get('pairs', [])
                        
                        if pairs:
                            # Find best match for the chain
                            chain_pairs = [p for p in pairs if p.get('chainId', '').lower() == token_chain.lower()]
                            if not chain_pairs:
                                # Fallback to any pair
                                chain_pairs = pairs
                            
                            best_pair = max(chain_pairs, key=lambda p: p.get('liquidity', {}).get('usd', 0))
                            
                            # Extract pair creation date
                            pair_created_at = best_pair.get('pairCreatedAt', '')
                            if pair_created_at:
                                try:
                                    # Ensure it's in ISO8601 format
                                    dt = datetime.fromisoformat(pair_created_at.replace('Z', '+00:00'))
                                    pair_created_at = dt.isoformat()
                                except:
                                    pair_created_at = ''
                            
                            return {
                                "pair_created_at": pair_created_at,
                                "market_cap": float(best_pair.get('marketCap', 0))
                            }
                        
        except Exception as e:
            logger.error(f"Error getting DexScreener data for {token_contract}: {e}")
            
        return None
    
    async def _get_market_cap_from_price_data(self, token_contract: str, token_chain: str) -> Optional[float]:
        """Get market cap from price data table"""
        try:
            # Get latest market cap from price data
            result = self.sb.table("lowcap_price_data_1m").select("market_cap").eq(
                "token_contract", token_contract
            ).eq("token_chain", token_chain).order("timestamp", desc=True).limit(1).execute()
            
            if result.data:
                market_cap = result.data[0].get("market_cap")
                if market_cap is not None:
                    return float(market_cap)
                    
        except Exception as e:
            logger.error(f"Error getting market cap from price data for {token_contract}: {e}")
            
        return None


async def main():
    """Main function"""
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    
    updater = PositionFeaturesUpdater()
    updated_count = await updater.run()
    
    print(f"Updated {updated_count} positions with features data")


if __name__ == "__main__":
    asyncio.run(main())
