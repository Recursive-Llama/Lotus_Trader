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
