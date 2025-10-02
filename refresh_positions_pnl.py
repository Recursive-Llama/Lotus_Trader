#!/usr/bin/env python3
"""
Refresh Positions P&L Script

Recalculates P&L for all active positions using current database prices.
This is useful when you want to refresh the portfolio data.
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
from src.intelligence.trader_lowcap.trader_lowcap_simple_v2 import TraderLowcapSimpleV2

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def refresh_all_positions_pnl():
    """Refresh P&L for all active positions"""
    try:
        # Initialize components
        logger.info("🚀 Starting position P&L refresh...")
        
        supabase_manager = SupabaseManager()
        trader = TraderLowcapSimpleV2(supabase_manager)
        
        # Get all active positions first
        logger.info("📊 Getting active positions...")
        active_positions = await trader._get_all_active_positions()
        
        if not active_positions:
            logger.info("ℹ️  No active positions found")
            return
        
        logger.info(f"📈 Found {len(active_positions)} active positions")
        
        # Update P&L for all positions
        logger.info("🔄 Updating P&L for all positions...")
        await trader._update_all_positions_pnl()
        
        # Get updated positions to show summary
        logger.info("📊 Getting updated position summary...")
        updated_positions = await trader._get_all_active_positions()
        
        # Calculate portfolio summary
        total_allocation_usd = sum(p.get('total_allocation_usd', 0) for p in updated_positions)
        total_pnl_usd = sum(p.get('total_pnl_usd', 0) for p in updated_positions)
        total_pnl_pct = (total_pnl_usd / total_allocation_usd * 100) if total_allocation_usd > 0 else 0
        
        logger.info("✅ P&L refresh completed!")
        logger.info(f"📊 Portfolio Summary:")
        logger.info(f"   Total Positions: {len(updated_positions)}")
        logger.info(f"   Total Allocation: ${total_allocation_usd:.2f}")
        logger.info(f"   Total P&L: ${total_pnl_usd:.2f} ({total_pnl_pct:+.2f}%)")
        
        # Show individual position details
        logger.info("📋 Position Details:")
        for position in updated_positions:
            ticker = position.get('token_ticker', 'Unknown')
            pnl_usd = position.get('total_pnl_usd', 0)
            pnl_pct = position.get('total_pnl_pct', 0)
            allocation_usd = position.get('total_allocation_usd', 0)
            current_price = position.get('current_price', 0)
            
            emoji = "📈" if pnl_pct > 0 else "📉" if pnl_pct < 0 else "➡️"
            logger.info(f"   {emoji} {ticker}: ${allocation_usd:.2f} → ${pnl_usd:+.2f} ({pnl_pct:+.1f}%) @ ${current_price:.6f}")
        
        logger.info("🎉 All done!")
        
    except Exception as e:
        logger.error(f"❌ Error refreshing positions: {e}")
        raise


async def refresh_single_position_pnl(position_id: str):
    """Refresh P&L for a single position"""
    try:
        logger.info(f"🔄 Refreshing P&L for position: {position_id}")
        
        supabase_manager = SupabaseManager()
        trader = TraderLowcapSimpleV2(supabase_manager)
        
        # Update single position P&L
        await trader._update_position_pnl(position_id)
        
        # Get updated position
        position = trader.repo.get_position(position_id)
        if position:
            ticker = position.get('token_ticker', 'Unknown')
            pnl_usd = position.get('total_pnl_usd', 0)
            pnl_pct = position.get('total_pnl_pct', 0)
            current_price = position.get('current_price', 0)
            
            emoji = "📈" if pnl_pct > 0 else "📉" if pnl_pct < 0 else "➡️"
            logger.info(f"✅ {emoji} {ticker}: ${pnl_usd:+.2f} ({pnl_pct:+.1f}%) @ ${current_price:.6f}")
        else:
            logger.error(f"❌ Position {position_id} not found")
        
    except Exception as e:
        logger.error(f"❌ Error refreshing position {position_id}: {e}")
        raise


async def main():
    """Main function"""
    if len(sys.argv) > 1:
        # Refresh specific position
        position_id = sys.argv[1]
        await refresh_single_position_pnl(position_id)
    else:
        # Refresh all positions
        await refresh_all_positions_pnl()


if __name__ == "__main__":
    print("🔄 Lotus Trader - Position P&L Refresh")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        print(f"Target: Single position ({sys.argv[1]})")
    else:
        print("Target: All active positions")
    
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    asyncio.run(main())
