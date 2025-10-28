from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any, Dict


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


