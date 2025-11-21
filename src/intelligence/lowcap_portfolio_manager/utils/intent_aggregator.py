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
                         decay_half_life_hours: float = 72.0) -> Dict[str, float]:
        """
        Aggregate intent signals for a token with exponential decay (no hard cutoff).
        All curator mentions are additive with decay applied.
        
        Args:
            token_contract: Token contract address
            token_chain: Token chain (solana, ethereum, etc.)
            decay_half_life_hours: Half-life for exponential decay (default 72h)
                                  After 72h, weight is 0.5, after 144h it's 0.25, after 7 days (168h) it's ~0.125
            
        Returns:
            Dict with intent metrics: {"hi_buy": 0.3, "med_buy": 0.2, "profit": 0.1, "sell": 0.05, "mock": 0.02}
        """
        try:
            # Query ALL AD_strands for this token (no time cutoff - decay handles it)
            # Extract curator from signal_pack.curator.id (not team_member)
            query = """
                SELECT 
                    s.symbol,
                    s.tags,
                    s.signal_pack,
                    s.created_at,
                    COALESCE(
                        (SELECT c.final_weight 
                         FROM curators c 
                         WHERE c.curator_id = s.signal_pack->'curator'->>'id'),
                        0.5
                    ) as curator_weight
                FROM AD_strands s
                WHERE s.symbol = %s
                AND s.kind IN ('social_lowcap', 'signal', 'trading_plan', 'intelligence')
                AND s.tags IS NOT NULL
                ORDER BY s.created_at DESC
            """
            
            result = self.sb.rpc('execute_query', {
                'query': query,
                'params': [token_contract]
            }).execute()
            
            strands = result.data or []
            
            # Aggregate intents with frequency and curator weighting (additive across all curators)
            intent_counts = {"hi_buy": 0, "med_buy": 0, "profit": 0, "sell": 0, "mock": 0}
            intent_weights = {"hi_buy": 0.0, "med_buy": 0.0, "profit": 0.0, "sell": 0.0, "mock": 0.0}
            
            now = datetime.now(timezone.utc)
            
            for strand in strands:
                tags = strand.get("tags", [])
                # Get curator weight from query result (already joined)
                curator_weight = float(strand.get("curator_weight", 0.5))
                created_at = datetime.fromisoformat(strand["created_at"].replace('Z', '+00:00'))
                
                # Calculate recency weight using exponential decay (no hard cutoff)
                # Decay formula: weight = exp(-ln(2) * hours_ago / half_life)
                # This gives 0.5 at half_life, 0.25 at 2*half_life, etc.
                hours_ago = (now - created_at).total_seconds() / 3600
                if hours_ago < 0:
                    hours_ago = 0  # Handle future timestamps
                
                # Exponential decay: weight decays to near-zero over time
                # Using half-life: after decay_half_life_hours, weight is 0.5
                recency_weight = math.exp(-math.log(2) * hours_ago / decay_half_life_hours)
                
                # Only process if decay weight is significant (above 0.01 to avoid noise)
                if recency_weight < 0.01:
                    continue
                
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
            # Scores are additive: all curator mentions contribute, weighted by curator score and decay
            intent_metrics = {}
            for intent_type in intent_counts.keys():
                count = intent_counts[intent_type]
                weight = intent_weights[intent_type]
                
                if count > 0 and weight > 0:
                    # Frequency multiplier: 1 + log(count) to boost frequently mentioned intents
                    freq_multiplier = 1 + math.log(count)
                    # Normalize: weight is sum of (curator_weight * decay) for all mentions
                    # Divide by count to get average, then apply frequency multiplier
                    # Scale by 2.0 to keep scores in 0-1 range
                    normalized_score = min(1.0, (weight / count) * freq_multiplier / 2.0)
                else:
                    normalized_score = 0.0
                
                intent_metrics[intent_type] = normalized_score
            
            logger.debug(f"Intent aggregation for {token_contract}: {intent_metrics} (from {len(strands)} strands)")
            return intent_metrics
            
        except Exception as e:
            logger.error(f"Error aggregating intents for {token_contract}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
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
