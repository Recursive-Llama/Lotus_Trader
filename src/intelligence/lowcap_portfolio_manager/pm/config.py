from __future__ import annotations

import json
import os
import logging
from functools import lru_cache
from typing import Any, Dict, Optional
from supabase import Client

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def load_pm_config() -> Dict[str, Any]:
    # Allow override via PM_CONFIG_PATH or default to src/config/pm_config.jsonc
    path = os.getenv("PM_CONFIG_PATH", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "pm_config.jsonc"))
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # Minimal sane defaults
        return {
            "e2_retrace_window": [0.68, 1.00],
            "mode_sizes": {
                "patient": {"immediate": 0.00, "e1": 0.05, "e2": 0.05},
                "normal": {"immediate": 0.10, "e1": 0.15, "e2": 0.15},
                "aggressive": {"immediate": 0.15, "e1": 0.35, "e2": 0.50},
            },
        }


def fetch_and_merge_db_config(file_config: Dict[str, Any], sb_client: Optional[Client]) -> Dict[str, Any]:
    """
    Fetch module_id='pm' config from learning_configs and merge it over the file config.
    
    Args:
        file_config: The base config loaded from file
        sb_client: Supabase client
    
    Returns:
        Merged config dict
    """
    if not sb_client:
        return file_config

    try:
        res = (
            sb_client.table("learning_configs")
            .select("config_data")
            .eq("module_id", "pm")
            .execute()
        )
        if res.data and len(res.data) > 0:
            db_config = res.data[0].get("config_data", {})
            if db_config:
                # Shallow merge is usually enough for top-level keys like "exposure_skew"
                # If we need deep merge, we can add it, but for now top-level replacement is safer/simpler
                merged = dict(file_config)
                merged.update(db_config)
                return merged
    except Exception as e:
        logger.warning(f"Error loading PM config from DB: {e}")
    
    return file_config
