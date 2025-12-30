#!/usr/bin/env python3
"""
Deep investigation into EMA staleness issue.
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

def investigate_position(contract: str, chain: str, timeframe: str):
    print("=" * 80)
    print(f"EMA STALENESS INVESTIGATION - {contract[:12]}... {timeframe}")
    print("=" * 80)

    # 1. Get the position with full features
    result = sb.table("lowcap_positions").select("*").eq("token_contract", contract).eq("token_chain", chain).eq("timeframe", timeframe).execute()
    if not result.data:
        print("Position not found!")
        return
    
    pos = result.data[0]
    features = pos.get('features', {}) or {}
    ticker = pos.get('token_ticker', contract[:8])

    # 2. Check when TA was last updated
    ta = features.get('ta', {}) or {}
    ta_updated = ta.get('updated_at') or ta.get('timestamp') or 'NOT FOUND IN TA'
    print(f"\n1. TA METADATA:")
    print(f"   ta.updated_at: {ta_updated}")
    
    # Check all keys in ta
    print(f"   ta keys: {list(ta.keys())}")

    # 3. Check uptrend_engine_v4 timestamps
    uptrend = features.get('uptrend_engine_v4', {}) or {}
    uptrend_updated = uptrend.get('updated_at') or uptrend.get('timestamp') or 'NOT FOUND'
    print(f"\n2. UPTREND ENGINE METADATA:")
    print(f"   uptrend_engine_v4.updated_at: {uptrend_updated}")
    print(f"   state: {uptrend.get('state')}")
    print(f"   price: {uptrend.get('price')}")

    # 4. Check position updated_at
    pos_updated = pos.get('updated_at')
    print(f"\n3. POSITION UPDATED_AT: {pos_updated}")

    # 5. Get recent OHLC data
    print(f"\n4. RECENT OHLC DATA (last 10 bars):")
    ohlc = sb.table("lowcap_price_data_ohlc").select("timestamp, close_usd").eq("token_contract", contract).eq("chain", chain).eq("timeframe", timeframe).order("timestamp", desc=True).limit(400).execute().data

    for row in ohlc[:10]:
        print(f"   {row['timestamp']}: ${float(row['close_usd']):.10f}")

    # 6. Check stored EMAs vs current price
    print(f"\n5. EMA vs CURRENT PRICE COMPARISON:")
    ema = ta.get('ema', {}) or {}
    current_price = float(ohlc[0]['close_usd']) if ohlc else 0
    
    # Get the correct suffix for this timeframe
    ema_suffix = f"_{timeframe}" if timeframe != "1h" else ""
    
    stored_ema20 = float(ema.get(f'ema20{ema_suffix}', 0))
    stored_ema333 = float(ema.get(f'ema333{ema_suffix}', 0))
    
    print(f"   Current Price: ${current_price:.10f}")
    print(f"   Stored EMA20{ema_suffix}: ${stored_ema20:.10f}")
    print(f"   Stored EMA333{ema_suffix}: ${stored_ema333:.10f}")

    # Calculate ratio
    if current_price > 0 and stored_ema20 > 0:
        ema20_ratio = stored_ema20 / current_price
        ema333_ratio = stored_ema333 / current_price if stored_ema333 > 0 else 0
        print(f"   EMA20/Price Ratio: {ema20_ratio:.2f}x (should be close to 1.0)")
        print(f"   EMA333/Price Ratio: {ema333_ratio:.2f}x (should be close to 1.0)")
        
        if ema20_ratio > 2 or ema20_ratio < 0.5:
            print(f"   ⚠️  EMA20 is STALE - {ema20_ratio:.1f}x away from current price!")

    # 7. Compute what EMAs SHOULD be from OHLC
    print(f"\n6. COMPUTED EMAs FROM OHLC DATA:")
    prices = [float(r['close_usd']) for r in reversed(ohlc) if float(r['close_usd']) > 0]
    
    if len(prices) >= 20:
        from src.intelligence.lowcap_portfolio_manager.jobs.ta_utils import ema_series
        
        computed_ema20 = ema_series(prices, 20)[-1] if len(prices) >= 20 else 0
        computed_ema333 = ema_series(prices, 333)[-1] if len(prices) >= 333 else 0
        
        print(f"   Computed EMA20: ${computed_ema20:.10f}")
        print(f"   Computed EMA333: ${computed_ema333:.10f}")
        
        if stored_ema20 > 0 and computed_ema20 > 0:
            diff_pct = abs(stored_ema20 - computed_ema20) / computed_ema20 * 100
            print(f"   EMA20 Difference: {diff_pct:.1f}%")
            if diff_pct > 10:
                print(f"   ⚠️  STORED EMA20 IS STALE BY {diff_pct:.1f}%!")

    # 8. Check price history to understand when EMAs were valid
    print(f"\n7. PRICE HISTORY ANALYSIS:")
    if prices:
        max_price = max(prices)
        min_price = min(prices)
        oldest = prices[0]
        newest = prices[-1]
        print(f"   Data range: {len(prices)} bars")
        print(f"   Oldest price: ${oldest:.10f}")
        print(f"   Newest price: ${newest:.10f}")
        print(f"   Max price: ${max_price:.10f}")
        print(f"   Min price: ${min_price:.10f}")
        
        # Check if stored EMA matches any historical price
        if stored_ema20 > 0:
            for i, p in enumerate(prices):
                if abs(p - stored_ema20) / stored_ema20 < 0.1:  # Within 10%
                    bar_idx = len(prices) - i - 1
                    print(f"\n   Stored EMA20 matches price from {bar_idx} bars ago: ${p:.10f}")
                    if bar_idx > 50:
                        print(f"   ⚠️  This suggests EMAs haven't been updated for ~{bar_idx} bars!")
                    break

    # 9. Check logs for TA computation errors
    print(f"\n8. CHECKING FOR TA COMPUTATION ISSUES:")
    print(f"   (Check logs for errors related to {ticker})")
    
    print("\n" + "=" * 80)
    
    return pos, features

def check_all_positions_for_staleness():
    """Check all active positions for stale EMAs"""
    print("\n" + "=" * 80)
    print("CHECKING ALL ACTIVE POSITIONS FOR STALE EMAs")
    print("=" * 80)
    
    positions = sb.table("lowcap_positions").select("id, token_contract, token_chain, token_ticker, timeframe, features, status").in_("status", ["active", "watchlist"]).execute().data
    
    stale_positions = []
    
    for pos in positions:
        features = pos.get('features', {}) or {}
        ta = features.get('ta', {}) or {}
        ema = ta.get('ema', {}) or {}
        uptrend = features.get('uptrend_engine_v4', {}) or {}
        
        timeframe = pos.get('timeframe', '1h')
        ema_suffix = f"_{timeframe}" if timeframe != "1h" else ""
        
        stored_ema20 = float(ema.get(f'ema20{ema_suffix}', 0))
        current_price = float(uptrend.get('price', 0))
        
        if stored_ema20 > 0 and current_price > 0:
            ratio = stored_ema20 / current_price
            if ratio > 2 or ratio < 0.5:
                stale_positions.append({
                    'ticker': pos.get('token_ticker', pos.get('token_contract', '')[:8]),
                    'timeframe': timeframe,
                    'status': pos.get('status'),
                    'stored_ema20': stored_ema20,
                    'current_price': current_price,
                    'ratio': ratio
                })
    
    if stale_positions:
        print(f"\nFound {len(stale_positions)} positions with potentially stale EMAs:")
        for sp in stale_positions:
            print(f"   {sp['ticker']}/{sp['timeframe']} ({sp['status']}): EMA20/Price = {sp['ratio']:.2f}x")
    else:
        print("\nNo stale EMAs detected in active positions!")
    
    return stale_positions

if __name__ == "__main__":
    # Investigate the specific position
    investigate_position("GWeGoN9sYmZPUjLMS316HF8eppxVzr36Rp8Hmnwhpump", "solana", "1m")
    
    # Check all positions
    check_all_positions_for_staleness()

