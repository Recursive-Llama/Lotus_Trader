"""
Intent Aggregation Utility

Aggregates intent signals from AD_strands table with frequency weighting and curator scoring.
"""

import math
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from supabase import Client

logger = logging.getLogger(__name__)


class IntentAggregator:
    """Aggregates intent signals from AD_strands with frequency and curator weighting."""
    
    def __init__(self, supabase_client: Client):
        self.sb = supabase_client
    
    def aggregate_intents(self, token_contract: str, token_chain: str, 
                         window_hours: int = 24) -> Dict[str, float]:
        """
        Aggregate intent signals for a token over the specified window.
        
        Args:
            token_contract: Token contract address
            token_chain: Token chain (solana, ethereum, etc.)
            window_hours: Time window in hours (default 24h)
            
        Returns:
            Dict with intent metrics: {"hi_buy": 0.3, "med_buy": 0.2, "profit": 0.1, "sell": 0.05, "mock": 0.02}
        """
        try:
            # Calculate window start time
            window_start = datetime.now(timezone.utc) - timedelta(hours=window_hours)
            
            # Query AD_strands for intent signals
            query = """
                SELECT 
                    s.symbol,
                    s.tags,
                    s.module_intelligence,
                    s.curator_feedback,
                    s.created_at,
                    c.final_weight as curator_weight
                FROM AD_strands s
                LEFT JOIN curators c ON c.curator_id = s.team_member
                WHERE s.symbol = %s
                AND s.created_at >= %s
                AND s.kind IN ('signal', 'trading_plan', 'intelligence')
                AND s.tags IS NOT NULL
                ORDER BY s.created_at DESC
            """
            
            result = self.sb.rpc('execute_query', {
                'query': query,
                'params': [token_contract, window_start.isoformat()]
            }).execute()
            
            strands = result.data or []
            
            # Aggregate intents with frequency and curator weighting
            intent_counts = {"hi_buy": 0, "med_buy": 0, "profit": 0, "sell": 0, "mock": 0}
            intent_weights = {"hi_buy": 0.0, "med_buy": 0.0, "profit": 0.0, "sell": 0.0, "mock": 0.0}
            
            for strand in strands:
                tags = strand.get("tags", [])
                curator_weight = float(strand.get("curator_weight", 0.5))
                created_at = datetime.fromisoformat(strand["created_at"].replace('Z', '+00:00'))
                
                # Calculate recency weight (exponential decay)
                hours_ago = (datetime.now(timezone.utc) - created_at).total_seconds() / 3600
                recency_weight = math.exp(-hours_ago / (window_hours / 3))  # Decay over 1/3 of window
                
                # Extract intent signals from tags
                for tag in tags:
                    if isinstance(tag, str):
                        tag_lower = tag.lower()
                        if "buy" in tag_lower and "high" in tag_lower:
                            intent_counts["hi_buy"] += 1
                            intent_weights["hi_buy"] += curator_weight * recency_weight
                        elif "buy" in tag_lower and "med" in tag_lower:
                            intent_counts["med_buy"] += 1
                            intent_weights["med_buy"] += curator_weight * recency_weight
                        elif "profit" in tag_lower or "take_profit" in tag_lower:
                            intent_counts["profit"] += 1
                            intent_weights["profit"] += curator_weight * recency_weight
                        elif "sell" in tag_lower and "signal" in tag_lower:
                            intent_counts["sell"] += 1
                            intent_weights["sell"] += curator_weight * recency_weight
                        elif "mock" in tag_lower or "laugh" in tag_lower or "joke" in tag_lower:
                            intent_counts["mock"] += 1
                            intent_weights["mock"] += curator_weight * recency_weight
            
            # Convert to normalized scores (0-1)
            intent_metrics = {}
            for intent_type in intent_counts.keys():
                count = intent_counts[intent_type]
                weight = intent_weights[intent_type]
                
                if count > 0:
                    # Frequency multiplier: 1 + log(count)
                    freq_multiplier = 1 + math.log(count)
                    # Normalize weight by count and apply frequency multiplier
                    normalized_score = min(1.0, (weight / count) * freq_multiplier / 2.0)
                else:
                    normalized_score = 0.0
                
                intent_metrics[intent_type] = normalized_score
            
            logger.debug(f"Intent aggregation for {token_contract}: {intent_metrics}")
            return intent_metrics
            
        except Exception as e:
            logger.error(f"Error aggregating intents for {token_contract}: {e}")
            return {"hi_buy": 0.0, "med_buy": 0.0, "profit": 0.0, "sell": 0.0, "mock": 0.0}
    
    def update_position_intents(self, token_contract: str, token_chain: str, 
                               position_id: str) -> bool:
        """
        Update intent_metrics in position features.
        
        Args:
            token_contract: Token contract address
            token_chain: Token chain
            position_id: Position ID to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Aggregate intents
            intent_metrics = self.aggregate_intents(token_contract, token_chain)
            
            # Update position features
            result = self.sb.table("lowcap_positions").select("features").eq("id", position_id).execute()
            
            if not result.data:
                logger.warning(f"Position {position_id} not found")
                return False
            
            position = result.data[0]
            features = position.get("features", {})
            features["intent_metrics"] = intent_metrics
            features["intent_updated_at"] = datetime.now(timezone.utc).isoformat()
            
            # Update the position
            self.sb.table("lowcap_positions").update({
                "features": features
            }).eq("id", position_id).execute()
            
            logger.info(f"Updated intent metrics for {position_id}: {intent_metrics}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating intent metrics for {position_id}: {e}")
            return False


def main():
    """Test the intent aggregator."""
    import os
    from supabase import create_client
    
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")
    
    if not url or not key:
        print("SUPABASE_URL and SUPABASE_KEY are required")
        return
    
    sb = create_client(url, key)
    aggregator = IntentAggregator(sb)
    
    # Test with a sample token
    test_token = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC on Solana
    intents = aggregator.aggregate_intents(test_token, "solana")
    print(f"Intent metrics for {test_token}: {intents}")


if __name__ == "__main__":
    main()
