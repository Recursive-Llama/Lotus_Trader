import os
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

try:
    # Insert a dummy row with minimal columns to see what works
    # We use a pattern_key that will be easy to delete
    res = sb.table("pm_overrides").insert({
        "pattern_key": "debug_schema_test",
        "action_category": "debug",
        "scope_subset": {},
        "confidence_score": 0.0
    }).execute()
    
    print("Insert succeeded!")
    if res.data:
        print("Columns returned:", list(res.data[0].keys()))
        
    # Build update payload with questionable columns
    payload = {}
    try:
        payload["dirA"] = 0.5
        sb.table("pm_overrides").update(payload).eq("pattern_key", "debug_schema_test").execute()
        print("Update dirA succeeded!")
    except Exception as e:
        print(f"Update dirA failed: {e}")
        
    try:
        payload = {"n": 10}
        sb.table("pm_overrides").update(payload).eq("pattern_key", "debug_schema_test").execute()
        print("Update n succeeded!")
    except Exception as e:
        print(f"Update n failed: {e}")

    # Cleanup
    sb.table("pm_overrides").delete().eq("pattern_key", "debug_schema_test").execute()
    
except Exception as e:
    print(f"Insert failed: {e}")
