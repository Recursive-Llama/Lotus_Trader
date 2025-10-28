"""
Intent Metrics Updater Job

Periodically updates intent_metrics in position features by aggregating from AD_strands.
"""

import os
import logging
from datetime import datetime, timezone
from supabase import create_client, Client

from src.intelligence.lowcap_portfolio_manager.utils.intent_aggregator import IntentAggregator

logger = logging.getLogger(__name__)


class IntentMetricsUpdater:
    """Updates intent metrics for all active positions."""
    
    def __init__(self) -> None:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_KEY", "")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
        self.sb: Client = create_client(url, key)
        self.aggregator = IntentAggregator(self.sb)
    
    def get_active_positions(self) -> list[dict]:
        """Get all active positions."""
        try:
            result = self.sb.table("lowcap_positions").select(
                "id,token_contract,token_chain,token_ticker"
            ).eq("status", "active").limit(1000).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error fetching active positions: {e}")
            return []
    
    def update_all_intents(self, window_hours: int = 24) -> int:
        """
        Update intent metrics for all active positions.
        
        Args:
            window_hours: Time window for intent aggregation
            
        Returns:
            Number of positions updated
        """
        positions = self.get_active_positions()
        updated = 0
        
        logger.info(f"Updating intent metrics for {len(positions)} active positions")
        
        for position in positions:
            try:
                position_id = position["id"]
                token_contract = position["token_contract"]
                token_chain = position["token_chain"]
                
                success = self.aggregator.update_position_intents(
                    token_contract, token_chain, position_id
                )
                
                if success:
                    updated += 1
                    
            except Exception as e:
                logger.error(f"Error updating intents for position {position.get('id', 'unknown')}: {e}")
        
        logger.info(f"Updated intent metrics for {updated}/{len(positions)} positions")
        return updated
    
    def run(self) -> int:
        """Run the intent metrics update job."""
        return self.update_all_intents()


def main() -> None:
    """Main entry point."""
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    
    updater = IntentMetricsUpdater()
    updated = updater.run()
    
    print(f"Intent metrics update completed: {updated} positions updated")


if __name__ == "__main__":
    main()
