"""
Override Materializer Job (V5 Simplified)

Reads lessons from learning_lessons and materializes actionable ones into pm_overrides table.
Replaces the legacy JSON-blob config writes.

Logic:
1. Read active lessons.
2. Apply Decay (if enabled).
3. Filter: Is Edge significant? (Judge).
4. Upsert into pm_overrides table.
"""

import logging
import os
import math
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from supabase import create_client, Client

logger = logging.getLogger(__name__)

# Configuration
EDGE_SIGNIFICANCE_THRESHOLD = 0.05  # |Edge - 1.0| > 0.05 to be an override
MIN_CONFIDENCE_SCORE = 0.2          # Lower bound for override confidence

def apply_decay(
    lever_value: float,
    lesson_strength: float,
    decay_halflife_hours: Optional[float],
    lesson_age_hours: float
) -> float:
    """Decay lever toward 1.0."""
    if not decay_halflife_hours or decay_halflife_hours <= 0:
        return lever_value
    if lesson_age_hours <= 0:
        return lever_value
        
    decay_rate = math.log(2) / decay_halflife_hours
    decay_factor = math.exp(-decay_rate * lesson_age_hours)
    
    neutral = 1.0
    decayed = neutral + (lever_value - neutral) * decay_factor * lesson_strength
    return decayed

def materialize_overrides(sb_client: Client, module: str = 'pm') -> Dict[str, int]:
    """
    Materialize lessons to pm_overrides table.
    Only supports PM module for now (DM allocation learning removed).
    """
    if module != 'pm':
        return {'overrides_written': 0}
        
    try:
        # Fetch active lessons
        res = sb_client.table('learning_lessons').select('*').eq('module', 'pm').eq('status', 'active').execute()
        lessons = res.data or []
        
        if not lessons:
            return {'overrides_written': 0}
            
        now = datetime.now(timezone.utc)
        overrides_written = 0
        
        for lesson in lessons:
            stats = lesson.get('stats', {})
            # Judge: Is edge significant?
            edge_raw = float(stats.get('edge_raw', 0.0))
            # edge_raw is centered at 0 in V5 simplified calc? 
            # Wait, in lesson_builder_v5 I wrote: edge_raw = (avg_rr - 1.0) * ...
            # So edge_raw=0 is neutral.
            
            # Check absolute magnitude
            if abs(edge_raw) < EDGE_SIGNIFICANCE_THRESHOLD:
                continue
                
            # Map to Multiplier
            # e.g. edge +0.1 -> 1.1x size?
            # Simple mapping: 1.0 + edge_raw
            # Clamp to safety bounds [0.3, 3.0]
            multiplier = max(0.3, min(3.0, 1.0 + edge_raw))
            
            # Apply Decay (if metadata exists)
            decay_meta = stats.get('decay_meta', {})
            # Actually lesson_builder_v5 puts decay_meta in stats, and lesson has `decay_halflife_hours`.
            # Let's use the pre-calculated decay_multiplier from stats if available (miner computed it).
            # Miner set edge_raw = (avg_rr - 1.0) * ... * decay_multiplier
            # So edge_raw ALREADY includes decay!
            # We don't need to decay again here unless we want to decay based on "time since lesson update".
            
            # Confidence score
            confidence = float(stats.get('support_score', 0.0)) * float(stats.get('reliability_score', 0.0))
            if confidence < MIN_CONFIDENCE_SCORE:
                continue
                
            # Write to pm_overrides
            pattern_key = lesson.get('pattern_key')
            # action_category is inside payload or top level?
            # In miner I put action_category in top level.
            action_category = lesson.get('action_category') or 'entry'
            
            # scope_subset is in `scope_subset` or `scope_values`?
            # Miner used `scope_subset` for V5, or `scope_values` for compat.
            # Let's check standard. Miner V5 wrote `scope_subset` into payload but `scope_values` into compat_payload.
            # I'll check both.
            scope_subset = lesson.get('scope_subset') or lesson.get('scope_values') or {}
            # Ensure it's a dict
            if not isinstance(scope_subset, dict):
                scope_subset = {}
                
            # We need to sanitize scope_subset (remove 'pattern_key' hack if present)
            scope_subset.pop('pattern_key', None)
            
            try:
                payload = {
                    'pattern_key': pattern_key,
                    'action_category': action_category,
                    'scope_subset': scope_subset,
                    'multiplier': multiplier,
                    'confidence_score': confidence,
                    'decay_state': decay_meta.get('state'),
                    'last_updated_at': now.isoformat()
                }
                
                # Upsert based on unique constraint
                sb_client.table('pm_overrides').upsert(
                    payload, 
                    on_conflict='pattern_key,action_category,scope_subset'
                ).execute()
                
                overrides_written += 1
            except Exception as e:
                logger.warning(f"Failed to write override for {pattern_key}: {e}")
                
        logger.info(f"Materialized {overrides_written} overrides from {len(lessons)} lessons.")
        return {'overrides_written': overrides_written}
        
    except Exception as e:
        logger.error(f"Materializer failed: {e}")
        return {'overrides_written': 0}

def run_override_materializer(sb_client: Optional[Client] = None) -> Dict[str, int]:
    if sb_client is None:
        sb_client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    return materialize_overrides(sb_client)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    res = run_override_materializer()
    print(res)
