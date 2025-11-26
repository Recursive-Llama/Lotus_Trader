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

# Tuning Configs
TUNING_MR_THRESHOLD = 0.6 # Miss Rate threshold to loosen
TUNING_FPR_THRESHOLD = 0.5 # FPR threshold to tighten
TUNING_TS_MIN_LOOSEN = 0.9
TUNING_TS_MIN_TIGHTEN = 1.1
TUNING_HALO_LOOSEN = 1.2
TUNING_HALO_TIGHTEN = 0.8

def materialize_pm_strength_overrides(sb_client: Client) -> int:
    """Materialize PM Strength lessons (Sizing) to pm_overrides."""
    try:
        # Fetch active pm_strength lessons
        res = sb_client.table('learning_lessons')\
            .select('*')\
            .eq('module', 'pm')\
            .eq('status', 'active')\
            .eq('lesson_type', 'pm_strength')\
            .execute()
        lessons = res.data or []
        
        if not lessons:
            return 0
        
        now = datetime.now(timezone.utc)
        overrides_written = 0
    
        for lesson in lessons:
            try:
                stats = lesson.get('stats', {})
                edge_raw = float(stats.get('edge_raw', 0.0))
        
                # Judge: Is edge significant?
                if abs(edge_raw) < EDGE_SIGNIFICANCE_THRESHOLD:
                    continue
        
                # Map to Multiplier [0.3, 3.0]
                multiplier = max(0.3, min(3.0, 1.0 + edge_raw))
                
                # Confidence score
                confidence = float(stats.get('support_score', 0.0)) * float(stats.get('reliability_score', 0.0))
                if confidence < MIN_CONFIDENCE_SCORE:
                    continue
        
                pattern_key = lesson.get('pattern_key')
                action_category = lesson.get('action_category') or 'entry'
                scope_subset = lesson.get('scope_subset') or lesson.get('scope_values') or {}
                decay_meta = stats.get('decay_meta', {})
                
                if not isinstance(scope_subset, dict):
                    scope_subset = {}
                
                # Upsert
                sb_client.table('pm_overrides').upsert({
                    'pattern_key': pattern_key,
                    'action_category': action_category,
                    'scope_subset': scope_subset,
                    'multiplier': multiplier,
                    'confidence_score': confidence,
                    'decay_state': decay_meta.get('state'),
                    'last_updated_at': now.isoformat()
                }, on_conflict='pattern_key,action_category,scope_subset').execute()
                
                overrides_written += 1
            except Exception as e:
                 logger.warning(f"Failed to write strength override for lesson {lesson.get('id')}: {e}")
                
        logger.info(f"Materialized {overrides_written} Strength overrides.")
        return overrides_written
    except Exception as e:
        logger.error(f"Strength Materializer failed: {e}")
        return 0

def materialize_tuning_overrides(sb_client: Client) -> int:
    """Materialize Tuning Rate lessons (Gates) to pm_overrides using Drift Logic."""
    try:
        # Fetch active tuning_rates lessons
        res = sb_client.table('learning_lessons')\
            .select('*')\
            .eq('module', 'pm')\
            .eq('status', 'active')\
            .eq('lesson_type', 'tuning_rates')\
            .execute()
        lessons = res.data or []
        
        if not lessons:
            return 0
        
        now = datetime.now(timezone.utc)
        overrides_written = 0
        
        # Drift Parameters
        ETA = 0.005 # Learning rate
        
        for lesson in lessons:
            try:
                stats = lesson.get('stats', {})
                n_misses = float(stats.get('n_misses', 0))
                n_fps = float(stats.get('n_fps', 0))
                
                # Pressure: Positive = Needs Loosening (Too many misses)
                #           Negative = Needs Tightening (Too many FPs)
                pressure = n_misses - n_fps
                
                if pressure == 0:
                    continue
                    
                # Calculate Multipliers
                # Lower is Looser for TS/DX (Thresholds) -> exp(-eta * p)
                # Higher is Looser for Halo (Distance) -> exp(+eta * p)
                
                mult_threshold = math.exp(-ETA * pressure)
                mult_halo = math.exp(ETA * pressure)
                
                # Clamp for safety [0.5, 2.0]
                mult_threshold = max(0.5, min(2.0, mult_threshold))
                mult_halo = max(0.5, min(2.0, mult_halo))
                
                pattern_key = lesson.get('pattern_key', '')
                scope_subset = lesson.get('scope_subset') or {}
                
                overrides_to_write = []
                
                if "S1" in pattern_key:
                    overrides_to_write.append(('tuning_ts_min', mult_threshold))
                    overrides_to_write.append(('tuning_halo', mult_halo))
                elif "S3" in pattern_key:
                    # S3 uses TS and DX
                    overrides_to_write.append(('tuning_ts_min', mult_threshold))
                    overrides_to_write.append(('tuning_dx_min', mult_threshold))

                for cat, mult in overrides_to_write:
                    # Skip tiny changes (drift noise)
                    if abs(mult - 1.0) < 0.01:
                        continue
                        
                    sb_client.table('pm_overrides').upsert({
                        'pattern_key': pattern_key,
                        'action_category': cat,
                        'scope_subset': scope_subset,
                        'multiplier': mult,
                        'confidence_score': 1.0, # Drift is cumulative confidence
                        'decay_state': None,
                        'last_updated_at': now.isoformat()
                    }, on_conflict='pattern_key,action_category,scope_subset').execute()
                    overrides_written += 1
            
            except Exception as e:
                logger.warning(f"Failed to write tuning override for lesson {lesson.get('id')}: {e}")

        logger.info(f"Materialized {overrides_written} Tuning overrides.")
        return overrides_written
        
    except Exception as e:
        logger.error(f"Tuning Materializer failed: {e}")
        return 0

def run_override_materializer(sb_client: Optional[Client] = None) -> Dict[str, int]:
    if sb_client is None:
        sb_client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    
    n_strength = materialize_pm_strength_overrides(sb_client)
    n_tuning = materialize_tuning_overrides(sb_client)
    
    return {'strength_overrides': n_strength, 'tuning_overrides': n_tuning}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from dotenv import load_dotenv
    load_dotenv()
    res = run_override_materializer()
    print(res)
