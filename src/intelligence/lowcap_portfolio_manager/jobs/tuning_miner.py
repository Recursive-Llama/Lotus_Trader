import os
import logging
import json
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from supabase import create_client, Client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TuningMiner:
    """
    Phase 2 of Tuning System: The Miner.
    
    Reads raw 'pattern_episode_events'.
    Mines frequent scope slices using recursive Apriori-like search.
    Calculates Tuning Rates (Win Rate, Miss Rate, False Positive Rate, Dodge Rate).
    Writes to 'learning_lessons' with lesson_type='tuning_rates'.
    
    Phase 7 Update: Now handles S2 and DX pattern keys for ladder tuning.
    - pm.uptrend.S1.* - S1 entry tuning
    - pm.uptrend.S2.* - S2 dip buy tuning (halo, ts_min, slope guards)
    - pm.uptrend.S3.dx - DX ladder tuning (dx_atr_mult adjustment)
    - pm.uptrend.S3.* - S3 retest tuning
    """

    def __init__(self):
        self.supabase_url = os.environ.get("SUPABASE_URL")
        self.supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
            
        self.sb: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Miner Config
        self.N_MIN = 33  # Minimum samples to form a lesson
        self.LOOKBACK_DAYS = 90
        
        # Pattern key categories for different tuning behaviors
        self.DX_PATTERN_KEYS = {"pm.uptrend.S3.dx"}
        self.S2_PATTERN_KEYS = {"pm.uptrend.S2.buy_flag", "pm.uptrend.S2.entry"}

    def run(self):
        """Main execution entry point."""
        logger.info("Starting Tuning Miner...")
        
        # 1. Fetch Raw Events
        events = self._fetch_raw_events()
        logger.info(f"Fetched {len(events)} raw episode events.")
        
        if not events:
            return

        # 2. Mine Lessons (Calculate Rates for Slices)
        lessons = self._mine_lessons(events)
        logger.info(f"Mined {len(lessons)} tuning lessons.")
        
        # 3. Upsert to DB
        if lessons:
            self._write_lessons(lessons)
            
        logger.info("Tuning Miner Complete.")

    def _fetch_raw_events(self) -> List[Dict[str, Any]]:
        """Fetch events from pattern_episode_events."""
        cutoff = (datetime.utcnow() - timedelta(days=self.LOOKBACK_DAYS)).isoformat()
        
        try:
            # We need outcomes to calculate rates.
            res = self.sb.table("pattern_episode_events")\
                .select("*")\
                .neq("outcome", "null")\
                .gte("timestamp", cutoff)\
                .execute()
            return res.data
        except Exception as e:
            logger.error(f"Failed to fetch events: {e}")
            return []

    def _mine_lessons(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Mines frequent itemsets using recursive DFS with pruning.
        """
        if not events:
            return []
            
        df = pd.DataFrame(events)
        
        # Flatten scope for easier grouping
        scope_keys = set()
        for scope in df['scope']:
            if isinstance(scope, dict):
                scope_keys.update(scope.keys())
        
        sorted_dims = sorted(list(scope_keys))
        
        for key in sorted_dims:
            df[f"scope_{key}"] = df['scope'].apply(lambda x: x.get(key) if isinstance(x, dict) else None)
            
        lessons = []
        
        def mine_recursive(df_slice: pd.DataFrame, current_mask: Dict[str, Any], start_dim_idx: int):
            # Base case: Prune if too small
            if len(df_slice) < self.N_MIN:
                return

            # Process current node (Create lesson for this slice)
            self._process_slice(df_slice, current_mask, lessons)
            
            # Recursive step: Try adding one more dimension
            for i in range(start_dim_idx, len(sorted_dims)):
                dim = sorted_dims[i]
                col = f"scope_{dim}"
                
                if col not in df_slice.columns:
                    continue
                
                # Get frequent values for this dimension in the current slice
                # This is the Apriori step: only branch on values that exist frequently
                counts = df_slice[col].value_counts()
                valid_values = counts[counts >= self.N_MIN].index.tolist()
                
                for val in valid_values:
                    # Create new mask
                    new_mask = current_mask.copy()
                    new_mask[dim] = val
                    
                    # Filter slice
                    new_slice = df_slice[df_slice[col] == val]
                    
                    # Recurse deeper
                    mine_recursive(new_slice, new_mask, i + 1)

        # Start recursion with global slice
        mine_recursive(df, {}, 0)
        
        return lessons

    def _process_slice(self, df_slice: pd.DataFrame, scope_subset: Dict[str, Any], lessons: List[Dict[str, Any]]):
        """Calculates stats for a specific slice and appends to lessons."""
        # Note: N_MIN check is already done by caller, but good for safety
        if len(df_slice) < self.N_MIN:
            return

        # Group by pattern_key within this slice
        grouped = df_slice.groupby('pattern_key')
        for pattern_key, group in grouped:
            if len(group) < self.N_MIN:
                continue
            
            # Phase 7: Special handling for DX ladder tuning
            if pattern_key in self.DX_PATTERN_KEYS:
                lesson = self._process_dx_slice(pattern_key, group, scope_subset)
                if lesson:
                    lessons.append(lesson)
                continue
                
            p_acted = group[group['decision'] == 'acted']
            p_skipped = group[group['decision'] == 'skipped']
            p_n_acted = len(p_acted)
            p_n_skipped = len(p_skipped)
            
            p_wr = len(p_acted[p_acted['outcome'] == 'success']) / p_n_acted if p_n_acted > 0 else 0.0
            p_fpr = len(p_acted[p_acted['outcome'] == 'failure']) / p_n_acted if p_n_acted > 0 else 0.0
            p_mr = len(p_skipped[p_skipped['outcome'] == 'success']) / p_n_skipped if p_n_skipped > 0 else 0.0
            p_dr = len(p_skipped[p_skipped['outcome'] == 'failure']) / p_n_skipped if p_n_skipped > 0 else 0.0
            
            p_n_misses = len(p_skipped[p_skipped['outcome'] == 'success'])
            p_n_fps = len(p_acted[p_acted['outcome'] == 'failure'])

            # Construct Lesson
            stats = {
                "wr": round(p_wr, 3),
                "fpr": round(p_fpr, 3),
                "mr": round(p_mr, 3),
                "dr": round(p_dr, 3),
                "n_acted": p_n_acted,
                "n_skipped": p_n_skipped,
                "n_misses": p_n_misses,
                "n_fps": p_n_fps,
                "n_total": len(group)
            }
            
            lesson = {
                "module": "pm",
                "pattern_key": pattern_key,
                "action_category": "tuning", 
                "scope_subset": scope_subset,
                "n": len(group),
                "stats": stats,
                "lesson_type": "tuning_rates",
                "status": "active",
                "updated_at": datetime.utcnow().isoformat()
            }
            lessons.append(lesson)
    
    def _process_dx_slice(self, pattern_key: str, group: pd.DataFrame, scope_subset: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Phase 7: Special processing for DX ladder tuning.
        
        DX ladder tuning is different from standard win/loss rates:
        - Only runs on successful recoveries (failures handled by dx_min decision tuning)
        - Uses dx_count (ladder fill level) to determine if arms are too tight/wide
        - dx_count=3 frequently on success → arms too tight, spread out
        - dx_count=1 frequently on success → arms too wide, tighten
        """
        # Only consider successful DX episodes for ladder tuning
        successful = group[group['outcome'] == 'success']
        
        if len(successful) < self.N_MIN:
            return None
        
        # Extract dx_count from factors
        dx_counts = []
        for _, row in successful.iterrows():
            factors = row.get('factors', {})
            if isinstance(factors, dict):
                dx_count = factors.get('dx_count')
                if dx_count is not None:
                    dx_counts.append(int(dx_count))
        
        if not dx_counts:
            return None
        
        # Calculate distribution of dx_count on success
        dx_arr = np.array(dx_counts)
        avg_dx_count = float(np.mean(dx_arr))
        count_1 = int(np.sum(dx_arr == 1))
        count_2 = int(np.sum(dx_arr == 2))
        count_3 = int(np.sum(dx_arr == 3))
        
        # Calculate ladder pressure
        # Positive = arms too tight (too many 3s) → need to spread out (increase dx_atr_mult)
        # Negative = arms too wide (too many 1s) → need to tighten (decrease dx_atr_mult)
        # Neutral when distribution is balanced around 2
        ladder_pressure = (count_3 - count_1) / len(dx_counts)
        
        stats = {
            "avg_dx_count": round(avg_dx_count, 2),
            "count_1": count_1,
            "count_2": count_2,
            "count_3": count_3,
            "n_success": len(successful),
            "n_total": len(group),
            "ladder_pressure": round(ladder_pressure, 3),
        }
        
        # Also calculate standard failure rate for DX decision tuning
        failed = group[group['outcome'] == 'failure']
        stats["n_failure"] = len(failed)
        stats["failure_rate"] = round(len(failed) / len(group), 3) if len(group) > 0 else 0.0
        
        lesson = {
            "module": "pm",
            "pattern_key": pattern_key,
            "action_category": "tuning_dx_ladder",  # Distinct category for materializer
            "scope_subset": scope_subset,
            "n": len(group),
            "stats": stats,
            "lesson_type": "tuning_rates",
            "status": "active",
            "updated_at": datetime.utcnow().isoformat()
        }
        
        return lesson

    def _write_lessons(self, lessons: List[Dict[str, Any]]):
        """Upserts lessons to DB."""
        try:
            # Upsert in batches
            BATCH_SIZE = 100
            for i in range(0, len(lessons), BATCH_SIZE):
                batch = lessons[i:i+BATCH_SIZE]
                # On conflict: Update stats and n
                self.sb.table("learning_lessons").upsert(
                    batch, 
                    on_conflict="module,pattern_key,action_category,scope_subset"
                ).execute()
        except Exception as e:
            logger.error(f"Failed to write lessons: {e}")

if __name__ == "__main__":
    # Load env if running directly
    from dotenv import load_dotenv
    load_dotenv()
    
    miner = TuningMiner()
    miner.run()
