#!/usr/bin/env python3
"""
Hyperliquid Token Discovery

Discovers all available tokens on Hyperliquid, categorizes them,
and analyzes capacity limits.

Run: python tests/hyperliquid/test_token_discovery.py
"""

import json
import logging
import os
import sys
from typing import Dict, Any, List, Set
from collections import defaultdict

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

import requests  # type: ignore

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Hyperliquid API
REST_BASE_URL = "https://api.hyperliquid.xyz"


class HyperliquidTokenDiscovery:
    """Discover and categorize Hyperliquid tokens"""
    
    def __init__(self):
        self.base_url = REST_BASE_URL
        self.tokens = []
        self.token_metadata = {}
    
    def get_all_tokens(self) -> List[Dict[str, Any]]:
        """Get all available tokens from Hyperliquid"""
        logger.info("=" * 80)
        logger.info("Step 1: Discovering All Available Tokens")
        logger.info("=" * 80)
        
        try:
            # Try info endpoint
            url = f"{self.base_url}/info"
            
            # Hyperliquid uses POST for info endpoint
            response = requests.post(url, json={"type": "meta"}, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'list'}")
                
                # Extract tokens from response
                tokens = self._extract_tokens(data)
                logger.info(f"Found {len(tokens)} tokens")
                return tokens
            else:
                logger.error(f"Error: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching tokens: {e}")
            return []
    
    def _extract_tokens(self, data: Any) -> List[Dict[str, Any]]:
        """Extract token list from API response"""
        tokens = []
        
        # Try different response structures
        if isinstance(data, dict):
            # Check common keys
            if "universe" in data:
                universe = data["universe"]
                for item in universe:
                    if isinstance(item, dict):
                        tokens.append({
                            "name": item.get("name"),
                            "symbol": item.get("name"),  # Usually same as name
                            "maxLeverage": item.get("maxLeverage"),
                            "onlyIsolated": item.get("onlyIsolated"),
                            "szDecimals": item.get("szDecimals"),
                        })
                    elif isinstance(item, str):
                        tokens.append({"name": item, "symbol": item})
            
            elif "meta" in data:
                meta = data["meta"]
                if "universe" in meta:
                    return self._extract_tokens({"universe": meta["universe"]})
            
            elif "tokens" in data:
                return self._extract_tokens({"universe": data["tokens"]})
        
        elif isinstance(data, list):
            # Direct list of tokens
            for item in data:
                if isinstance(item, dict):
                    tokens.append({
                        "name": item.get("name") or item.get("symbol"),
                        "symbol": item.get("symbol") or item.get("name"),
                        **{k: v for k, v in item.items() if k not in ["name", "symbol"]}
                    })
                elif isinstance(item, str):
                    tokens.append({"name": item, "symbol": item})
        
        return tokens
    
    def categorize_tokens(self, tokens: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Categorize tokens by type"""
        logger.info("\n" + "=" * 80)
        logger.info("Step 2: Categorizing Tokens")
        logger.info("=" * 80)
        
        categories = {
            "crypto": [],
            "stocks": [],
            "commodities": [],
            "forex": [],
            "indices": [],
            "other": [],
            "unknown": [],
        }
        
        # Common crypto patterns
        crypto_patterns = [
            "BTC", "ETH", "SOL", "BNB", "ADA", "DOT", "LINK", "MATIC", "AVAX",
            "UNI", "ATOM", "ALGO", "FIL", "AAVE", "MKR", "COMP", "SNX", "SUSHI",
            "CRV", "YFI", "1INCH", "BAL", "BAND", "BAT", "CEL", "CHZ", "ENJ",
            "EOS", "ETC", "GRT", "ICP", "KNC", "LRC", "MANA", "NEAR", "OMG",
            "ONT", "QTUM", "REN", "SKL", "STORJ", "SXP", "THETA", "UMA", "VET",
            "WAVES", "XLM", "XRP", "XTZ", "ZEC", "ZRX", "DOGE", "SHIB", "PEPE",
            "FLOKI", "BONK", "WIF", "HYPE",
        ]
        
        # Stock patterns (usually have $ or specific naming)
        stock_patterns = ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN", "META", "NVDA"]
        
        # Commodity patterns
        commodity_patterns = ["GOLD", "SILVER", "OIL", "GAS", "WHEAT", "CORN"]
        
        # Forex patterns
        forex_patterns = ["EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD"]
        
        for token in tokens:
            symbol = token.get("symbol") or token.get("name", "").upper()
            name = token.get("name", "").upper()
            
            # Check patterns
            categorized = False
            
            # Crypto
            if any(pattern in symbol or pattern in name for pattern in crypto_patterns):
                categories["crypto"].append(token)
                categorized = True
            
            # Stocks
            elif any(pattern in symbol or pattern in name for pattern in stock_patterns):
                categories["stocks"].append(token)
                categorized = True
            
            # Commodities
            elif any(pattern in symbol or pattern in name for pattern in commodity_patterns):
                categories["commodities"].append(token)
                categorized = True
            
            # Forex
            elif any(pattern in symbol or pattern in name for pattern in forex_patterns):
                categories["forex"].append(token)
                categorized = True
            
            # Indices (usually contain "INDEX" or numbers)
            elif "INDEX" in symbol or "INDEX" in name or symbol.startswith("SPX") or symbol.startswith("DJI"):
                categories["indices"].append(token)
                categorized = True
            
            # Other (check for $ which might indicate stocks)
            elif "$" in symbol or "$" in name:
                categories["stocks"].append(token)
                categorized = True
            
            if not categorized:
                # Try to infer from name
                if any(word in name.lower() for word in ["coin", "token", "crypto", "btc", "eth"]):
                    categories["crypto"].append(token)
                else:
                    categories["unknown"].append(token)
        
        # Log results
        logger.info("\nToken Categories:")
        for category, tokens_list in categories.items():
            if tokens_list:
                logger.info(f"  {category.upper()}: {len(tokens_list)} tokens")
                if len(tokens_list) <= 10:
                    symbols = [t.get("symbol") or t.get("name", "?") for t in tokens_list]
                    logger.info(f"    Examples: {', '.join(symbols)}")
                else:
                    symbols = [t.get("symbol") or t.get("name", "?") for t in tokens_list[:10]]
                    logger.info(f"    Examples: {', '.join(symbols)}... (+{len(tokens_list) - 10} more)")
        
        return categories
    
    def analyze_capacity(self, tokens: List[Dict[str, Any]], timeframes: List[str] = ["15m", "1h", "4h"]) -> Dict[str, Any]:
        """Analyze subscription capacity"""
        logger.info("\n" + "=" * 80)
        logger.info("Step 3: Analyzing Subscription Capacity")
        logger.info("=" * 80)
        
        total_tokens = len(tokens)
        subscriptions_per_token = len(timeframes)
        total_subscriptions = total_tokens * subscriptions_per_token
        
        # Hyperliquid limits
        max_subscriptions = 1000
        max_connections = 100
        
        analysis = {
            "total_tokens": total_tokens,
            "timeframes": timeframes,
            "subscriptions_per_token": subscriptions_per_token,
            "total_subscriptions_needed": total_subscriptions,
            "max_subscriptions_allowed": max_subscriptions,
            "max_connections_allowed": max_connections,
            "can_handle_all_tokens": total_subscriptions <= max_subscriptions,
            "max_tokens_supported": max_subscriptions // subscriptions_per_token,
            "recommendation": None,
        }
        
        logger.info(f"\nCapacity Analysis:")
        logger.info(f"  Total tokens: {total_tokens}")
        logger.info(f"  Timeframes: {', '.join(timeframes)}")
        logger.info(f"  Subscriptions per token: {subscriptions_per_token}")
        logger.info(f"  Total subscriptions needed: {total_subscriptions}")
        logger.info(f"  Max subscriptions allowed: {max_subscriptions}")
        logger.info(f"  Max tokens supported: {analysis['max_tokens_supported']}")
        
        if analysis["can_handle_all_tokens"]:
            logger.info(f"\n✅ Can handle ALL tokens ({total_tokens} tokens)")
            analysis["recommendation"] = "handle_all"
        else:
            logger.warning(f"\n⚠️  Cannot handle all tokens")
            logger.warning(f"   Need: {total_subscriptions} subscriptions")
            logger.warning(f"   Have: {max_subscriptions} subscriptions")
            logger.warning(f"   Can handle: {analysis['max_tokens_supported']} tokens max")
            analysis["recommendation"] = "filter_tokens"
        
        return analysis
    
    def get_token_metadata(self, tokens: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get additional metadata for tokens (volume, liquidity, etc.)"""
        logger.info("\n" + "=" * 80)
        logger.info("Step 4: Fetching Token Metadata")
        logger.info("=" * 80)
        
        # Try to get market data
        try:
            url = f"{self.base_url}/info"
            response = requests.post(url, json={"type": "metaAndAssetCtxs"}, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                logger.info("✅ Retrieved metadata")
                return data
            else:
                logger.warning(f"Could not fetch metadata: {response.status_code}")
                return {}
        except Exception as e:
            logger.warning(f"Error fetching metadata: {e}")
            return {}
    
    def generate_recommendations(self, tokens: List[Dict[str, Any]], categories: Dict[str, Any], capacity: Dict[str, Any]) -> Dict[str, Any]:
        """Generate recommendations for token management"""
        logger.info("\n" + "=" * 80)
        logger.info("Step 5: Generating Recommendations")
        logger.info("=" * 80)
        
        crypto_count = len(categories.get("crypto", []))
        other_count = sum(len(categories.get(cat, [])) for cat in ["stocks", "commodities", "forex", "indices", "other", "unknown"])
        
        recommendations = {
            "strategy": None,
            "filtering_approach": None,
            "max_tokens": capacity["max_tokens_supported"],
            "crypto_only": crypto_count <= capacity["max_tokens_supported"],
            "all_tokens": capacity["can_handle_all_tokens"],
        }
        
        logger.info(f"\nRecommendations:")
        
        if capacity["can_handle_all_tokens"]:
            recommendations["strategy"] = "handle_all"
            recommendations["filtering_approach"] = "no_filtering"
            logger.info("  ✅ Handle ALL tokens (within limits)")
        elif crypto_count <= capacity["max_tokens_supported"]:
            recommendations["strategy"] = "crypto_only"
            recommendations["filtering_approach"] = "filter_by_asset_type"
            logger.info(f"  ✅ Handle CRYPTO tokens only ({crypto_count} tokens)")
            logger.info(f"     Within limit of {capacity['max_tokens_supported']} tokens")
        else:
            recommendations["strategy"] = "filtered"
            recommendations["filtering_approach"] = "filter_by_volume_liquidity"
            logger.info(f"  ⚠️  Need to filter tokens")
            logger.info(f"     Crypto tokens: {crypto_count}")
            logger.info(f"     Max supported: {capacity['max_tokens_supported']}")
            logger.info(f"     Filter by: Volume, liquidity, or manual selection")
        
        return recommendations
    
    def run_full_discovery(self) -> Dict[str, Any]:
        """Run full token discovery and analysis"""
        # Step 1: Get all tokens
        tokens = self.get_all_tokens()
        
        if not tokens:
            logger.error("No tokens found. Check API endpoint.")
            return {}
        
        # Step 2: Categorize
        categories = self.categorize_tokens(tokens)
        
        # Step 3: Analyze capacity
        capacity = self.analyze_capacity(tokens, timeframes=["15m", "1h", "4h"])
        
        # Step 4: Get metadata
        metadata = self.get_token_metadata(tokens)
        
        # Step 5: Generate recommendations
        recommendations = self.generate_recommendations(tokens, categories, capacity)
        
        # Compile results
        results = {
            "tokens": tokens,
            "total_count": len(tokens),
            "categories": {
                cat: [t.get("symbol") or t.get("name", "?") for t in tokens_list]
                for cat, tokens_list in categories.items()
            },
            "category_counts": {
                cat: len(tokens_list) for cat, tokens_list in categories.items()
            },
            "capacity": capacity,
            "metadata": metadata,
            "recommendations": recommendations,
        }
        
        return results


def main():
    """Main entry point"""
    discovery = HyperliquidTokenDiscovery()
    results = discovery.run_full_discovery()
    
    # Save results
    output_file = "tests/hyperliquid/token_discovery_results.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info(f"\nResults saved to: {output_file}")
    
    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total tokens: {results.get('total_count', 0)}")
    logger.info(f"Strategy: {results.get('recommendations', {}).get('strategy', 'unknown')}")
    logger.info(f"Max tokens supported: {results.get('capacity', {}).get('max_tokens_supported', 0)}")
    
    return results


if __name__ == "__main__":
    main()

