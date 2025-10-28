"""Lowcap Portfolio Manager package.

This namespace contains ingest, SPIRAL phase detection, core lever computation,
action mapping, bands/rotation selection, event bus, strands logging, and jobs.
"""

import os

try:
    if os.getenv("TREND_REDEPLOY_ENABLED", "0") == "1":
        from .pm.actions.trend_redeploy import register_trend_redeploy_handler

        register_trend_redeploy_handler()
    if os.getenv("ACTIONS_ENABLED", "0") == "1":
        # Register PM executor bridge if trader and client get injected by runtime,
        # this import is a no-op here; actual registration should be done in run_social_trading
        pass
except Exception:
    # Optional hook; ignore failures at import time
    pass
