#!/usr/bin/env python3
"""
Check Position Entry Proximity Script

Analyzes which positions are closest to their entry prices by querying
the lowcap_price_data_1m table directly for current prices.
"""

import asyncio
import logging
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.append('src')

from src.utils.supabase_manager import SupabaseManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def check_position_entry_proximity():
    """Check which positions are closest to their entry prices"""
    try:
        # Initialize Supabase
        logger.info("🚀 Starting position entry proximity analysis...")
        supabase_manager = SupabaseManager()
        
        # Get all active positions
        logger.info("📊 Getting active positions...")
        result = supabase_manager.client.table('lowcap_positions').select('*').eq('status', 'active').execute()
        
        if not result.data:
            logger.info("ℹ️  No active positions found")
            return
        
        positions = result.data
        logger.info(f"📈 Found {len(positions)} active positions")
        
        # Calculate proximity to entry for each position
        position_proximity = []
        
        for position in positions:
            ticker = position.get('token_ticker', 'Unknown')
            chain = position.get('token_chain', 'Unknown')
            position_id = position.get('id', 'Unknown')
            token_contract = position.get('token_contract', '')
            
            # Get entry price (average entry price)
            avg_entry_price = position.get('avg_entry_price', 0)
            
            if avg_entry_price > 0 and token_contract:
                # Get current price from price data table
                price_result = supabase_manager.client.table('lowcap_price_data_1m').select('price_usd, price_native, timestamp').eq('token_contract', token_contract).eq('chain', chain).order('timestamp', desc=True).limit(1).execute()
                
                if price_result.data:
                    current_price_usd = float(price_result.data[0]['price_usd'])
                    current_price_native = float(price_result.data[0]['price_native'])
                    price_timestamp = price_result.data[0]['timestamp']
                    
                    # Use native price for comparison (SOL, ETH, BNB, etc.)
                    current_price = current_price_native
                    
                    # Calculate proximity as percentage difference from entry
                    proximity_pct = abs((current_price - avg_entry_price) / avg_entry_price * 100)
                    
                    # Determine if above or below entry
                    direction = "above" if current_price > avg_entry_price else "below"
                    
                    position_proximity.append({
                        'position_id': position_id,
                        'ticker': ticker,
                        'chain': chain,
                        'avg_entry_price': avg_entry_price,
                        'current_price': current_price,
                        'current_price_usd': current_price_usd,
                        'proximity_pct': proximity_pct,
                        'direction': direction,
                        'total_allocation_usd': position.get('total_allocation_usd', 0),
                        'total_pnl_usd': position.get('total_pnl_usd', 0),
                        'total_pnl_pct': position.get('total_pnl_pct', 0),
                        'total_quantity': position.get('total_quantity', 0),
                        'price_timestamp': price_timestamp
                    })
                else:
                    logger.warning(f"⚠️  No price data found for {ticker} ({chain}) - {token_contract}")
            else:
                logger.warning(f"⚠️  Skipping {ticker} - missing entry price ({avg_entry_price}) or contract ({token_contract})")
        
        # Sort by proximity (closest to entry first)
        position_proximity.sort(key=lambda x: x['proximity_pct'])
        
        logger.info("✅ Analysis completed!")
        logger.info("=" * 80)
        logger.info("📊 POSITIONS CLOSEST TO ENTRY PRICES")
        logger.info("=" * 80)
        
        # Show top 15 closest to entry
        top_n = min(15, len(position_proximity))
        logger.info(f"🎯 Top {top_n} positions closest to entry:")
        logger.info("")
        
        for i, pos in enumerate(position_proximity[:top_n]):
            emoji = "📈" if pos['direction'] == "above" else "📉"
            direction_arrow = "↗️" if pos['direction'] == "above" else "↘️"
            
            # Get native token symbol for display
            native_symbol = "SOL" if pos['chain'] == "solana" else "ETH" if pos['chain'] in ["ethereum", "base"] else "BNB" if pos['chain'] == "bsc" else pos['chain'].upper()
            
            logger.info(f"{i+1:2d}. {emoji} {pos['ticker']} ({pos['chain']})")
            logger.info(f"     {direction_arrow} {pos['proximity_pct']:.2f}% {pos['direction']} entry")
            logger.info(f"     💰 Entry: {pos['avg_entry_price']:.8f} {native_symbol} | Current: {pos['current_price']:.8f} {native_symbol}")
            logger.info(f"     💵 USD: ${pos['current_price_usd']:.8f}")
            logger.info(f"     📊 Allocation: ${pos['total_allocation_usd']:.2f} | P&L: ${pos['total_pnl_usd']:+.2f} ({pos['total_pnl_pct']:+.1f}%)")
            logger.info(f"     🪙 Quantity: {pos['total_quantity']:,.0f} tokens")
            logger.info(f"     🕐 Price data: {pos['price_timestamp'][:19]}Z")
            logger.info(f"     🆔 ID: {pos['position_id'][:30]}...")
            logger.info("")
        
        # Show summary statistics
        if position_proximity:
            avg_proximity = sum(p['proximity_pct'] for p in position_proximity) / len(position_proximity)
            min_proximity = min(p['proximity_pct'] for p in position_proximity)
            max_proximity = max(p['proximity_pct'] for p in position_proximity)
            
            above_entry = len([p for p in position_proximity if p['direction'] == "above"])
            below_entry = len([p for p in position_proximity if p['direction'] == "below"])
            
            logger.info("📈 SUMMARY STATISTICS:")
            logger.info(f"   Total positions analyzed: {len(position_proximity)}")
            logger.info(f"   Average distance from entry: {avg_proximity:.2f}%")
            logger.info(f"   Closest to entry: {min_proximity:.2f}%")
            logger.info(f"   Furthest from entry: {max_proximity:.2f}%")
            logger.info(f"   Above entry: {above_entry} positions")
            logger.info(f"   Below entry: {below_entry} positions")
        
        logger.info("🎉 Analysis complete!")
        
    except Exception as e:
        logger.error(f"❌ Error analyzing position proximity: {e}")
        raise


async def main():
    """Main function"""
    await check_position_entry_proximity()


if __name__ == "__main__":
    print("🎯 Lotus Trader - Position Entry Proximity Analysis")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    asyncio.run(main())