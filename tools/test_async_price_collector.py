#!/usr/bin/env python3
"""
Test script to compare sync vs async price collection performance.

Tests:
1. Sync approach (current - requests)
2. Async approach (proposed - aiohttp)
3. Timing comparison
4. Rate limiting verification
5. Data collection accuracy
"""

import os
import sys
import time
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import requests
import aiohttp
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

def get_supabase() -> Client:
    """Get Supabase client"""
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
    return create_client(url, key)

def get_test_tokens(sb: Client, limit: int = 20) -> List[Tuple[str, str]]:
    """Get test tokens (active/watchlist/dormant)"""
    result = (
        sb.table('lowcap_positions')
        .select('token_contract', 'token_chain')
        .in_('status', ['active', 'watchlist', 'dormant'])
        .limit(limit)
        .execute()
    )
    
    tokens = []
    seen = set()
    for row in (result.data or []):
        token = (row['token_contract'], (row.get('token_chain') or '').lower())
        if token[0] and token[1] and token not in seen:
            tokens.append(token)
            seen.add(token)
    
    return tokens

def sync_collect_token(token_contract: str, chain: str) -> Dict[str, Any]:
    """Sync version - current approach"""
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{token_contract}"
        response = requests.get(url, timeout=10)
        
        if response.ok:
            data = response.json()
            pairs = data.get('pairs') or []
            
            # Find pairs for this chain
            token_pairs = [
                p for p in pairs 
                if p.get('chainId') == chain
            ]
            
            return {
                'token': f"{token_contract[:8]}.../{chain}",
                'success': True,
                'pairs_found': len(token_pairs),
                'status_code': response.status_code
            }
        else:
            return {
                'token': f"{token_contract[:8]}.../{chain}",
                'success': False,
                'pairs_found': 0,
                'status_code': response.status_code,
                'error': f"HTTP {response.status_code}"
            }
    except Exception as e:
        return {
            'token': f"{token_contract[:8]}.../{chain}",
            'success': False,
            'pairs_found': 0,
            'status_code': None,
            'error': str(e)
        }

async def async_collect_token(session: aiohttp.ClientSession, token_contract: str, chain: str) -> Dict[str, Any]:
    """Async version - proposed approach"""
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{token_contract}"
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
            if response.status == 200:
                data = await response.json()
                pairs = data.get('pairs') or []
                
                # Find pairs for this chain
                token_pairs = [
                    p for p in pairs 
                    if p.get('chainId') == chain
                ]
                
                return {
                    'token': f"{token_contract[:8]}.../{chain}",
                    'success': True,
                    'pairs_found': len(token_pairs),
                    'status_code': response.status
                }
            else:
                return {
                    'token': f"{token_contract[:8]}.../{chain}",
                    'success': False,
                    'pairs_found': 0,
                    'status_code': response.status,
                    'error': f"HTTP {response.status}"
                }
    except Exception as e:
        return {
            'token': f"{token_contract[:8]}.../{chain}",
            'success': False,
            'pairs_found': 0,
            'status_code': None,
            'error': str(e)
        }

def test_sync_approach(tokens: List[Tuple[str, str]]) -> Tuple[float, List[Dict[str, Any]]]:
    """Test sync approach (current)"""
    print("Testing SYNC approach (current)...")
    start_time = time.time()
    
    results = []
    for token_contract, chain in tokens:
        result = sync_collect_token(token_contract, chain)
        results.append(result)
    
    elapsed = time.time() - start_time
    return elapsed, results

async def test_async_approach(tokens: List[Tuple[str, str]], max_concurrent: int = 50) -> Tuple[float, List[Dict[str, Any]]]:
    """Test async approach (proposed)"""
    print(f"Testing ASYNC approach (max_concurrent={max_concurrent})...")
    start_time = time.time()
    
    async with aiohttp.ClientSession() as session:
        # Create tasks for all tokens
        tasks = [
            async_collect_token(session, token_contract, chain)
            for token_contract, chain in tokens
        ]
        
        # Run with concurrency limit
        results = []
        for i in range(0, len(tasks), max_concurrent):
            batch = tasks[i:i + max_concurrent]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            
            # Handle exceptions
            for result in batch_results:
                if isinstance(result, Exception):
                    results.append({
                        'token': 'unknown',
                        'success': False,
                        'pairs_found': 0,
                        'status_code': None,
                        'error': str(result)
                    })
                else:
                    results.append(result)
    
    elapsed = time.time() - start_time
    return elapsed, results

def print_results(elapsed: float, results: List[Dict[str, Any]], approach: str):
    """Print test results"""
    success_count = sum(1 for r in results if r.get('success', False))
    total_pairs = sum(r.get('pairs_found', 0) for r in results)
    
    print(f"\n{approach} Results:")
    print(f"  Total tokens: {len(results)}")
    print(f"  Successful: {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)")
    print(f"  Total pairs found: {total_pairs}")
    print(f"  Time elapsed: {elapsed:.2f} seconds")
    print(f"  Average per token: {elapsed/len(results):.3f} seconds")
    print(f"  Tokens per minute: {len(results)/(elapsed/60):.1f}")
    
    # Show errors
    errors = [r for r in results if not r.get('success', False)]
    if errors:
        print(f"\n  Errors ({len(errors)}):")
        for err in errors[:5]:  # Show first 5 errors
            print(f"    - {err.get('token', 'unknown')}: {err.get('error', 'unknown error')}")
        if len(errors) > 5:
            print(f"    ... and {len(errors) - 5} more errors")
    
    # Check for rate limiting
    rate_limited = [r for r in results if r.get('status_code') == 429]
    if rate_limited:
        print(f"\n  ⚠️  Rate limited: {len(rate_limited)} tokens")
    
    return {
        'elapsed': elapsed,
        'success_count': success_count,
        'total_pairs': total_pairs,
        'errors': len(errors),
        'rate_limited': len(rate_limited)
    }

async def main():
    print("=" * 80)
    print("Price Collector Performance Test")
    print("=" * 80)
    print()
    
    sb = get_supabase()
    
    # Get test tokens
    print("Getting test tokens...")
    tokens = get_test_tokens(sb, limit=30)  # Test with 30 tokens
    print(f"Found {len(tokens)} tokens to test")
    print()
    
    if not tokens:
        print("No tokens found. Exiting.")
        return
    
    # Test 1: Sync approach
    print("-" * 80)
    sync_elapsed, sync_results = test_sync_approach(tokens)
    sync_stats = print_results(sync_elapsed, sync_results, "SYNC")
    
    # Wait a bit between tests to avoid rate limiting
    print("\nWaiting 5 seconds before async test...")
    await asyncio.sleep(5)
    
    # Test 2: Async approach (with concurrency limit)
    print("-" * 80)
    async_elapsed, async_results = await test_async_approach(tokens, max_concurrent=50)
    async_stats = print_results(async_elapsed, async_results, "ASYNC")
    
    # Comparison
    print("\n" + "=" * 80)
    print("COMPARISON")
    print("=" * 80)
    speedup = sync_elapsed / async_elapsed if async_elapsed > 0 else 0
    print(f"Speedup: {speedup:.2f}x faster with async")
    print(f"Time saved: {sync_elapsed - async_elapsed:.2f} seconds ({((sync_elapsed - async_elapsed)/sync_elapsed*100):.1f}%)")
    print()
    
    # Success rate comparison
    sync_success_rate = sync_stats['success_count'] / len(tokens) * 100
    async_success_rate = async_stats['success_count'] / len(tokens) * 100
    print(f"Success rate: Sync {sync_success_rate:.1f}% vs Async {async_success_rate:.1f}%")
    
    # Rate limiting check
    if sync_stats['rate_limited'] > 0 or async_stats['rate_limited'] > 0:
        print(f"\n⚠️  Rate limiting detected:")
        print(f"   Sync: {sync_stats['rate_limited']} tokens")
        print(f"   Async: {async_stats['rate_limited']} tokens")
    
    # Throughput
    print(f"\nThroughput:")
    print(f"   Sync: {len(tokens)/(sync_elapsed/60):.1f} tokens/minute")
    print(f"   Async: {len(tokens)/(async_elapsed/60):.1f} tokens/minute")
    print(f"   DexScreener limit: 300 tokens/minute")
    
    # Recommendation
    print("\n" + "=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)
    if speedup > 2 and async_stats['success_count'] >= sync_stats['success_count']:
        print("✅ Async approach is significantly faster and equally reliable")
        print("   → Proceed with async implementation")
    elif speedup > 1.5:
        print("✅ Async approach is faster")
        print("   → Proceed with async implementation")
    else:
        print("⚠️  Async approach shows minimal improvement")
        print("   → Investigate further before implementing")
    
    if async_elapsed < 60:
        print(f"✅ Async completes in {async_elapsed:.1f}s (under 60s target)")
    else:
        print(f"⚠️  Async takes {async_elapsed:.1f}s (over 60s target)")
        print("   → Consider reducing concurrency or optimizing further")
    
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())

