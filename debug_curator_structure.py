#!/usr/bin/env python3
"""
Debug Curator Structure - Compare different sources
"""

import sys
sys.path.append('src')

from intelligence.social_ingest.social_ingest_basic import SocialIngestModule

# Mock dependencies
class MockSupabase:
    def create_strand(self, strand): 
        return strand
    
    def update_curator_last_seen(self, curator_id): 
        pass

class MockLLM:
    async def generate_async(self, prompt, **kwargs): 
        return '{}'

def debug_curator_structures():
    """Compare curator structures from different sources"""
    print("🔍 Debugging Curator Structures...")
    
    # Initialize social ingest module
    social_ingest = SocialIngestModule(MockSupabase(), MockLLM())
    
    print("\n📊 From social_ingest.get_enabled_curators():")
    curators = social_ingest.get_enabled_curators()
    twitter_curators = [c for c in curators if c.get('platform') == 'twitter']
    
    print(f"Found {len(twitter_curators)} Twitter curators")
    
    for i, curator in enumerate(twitter_curators[:3]):
        print(f"  Curator {i+1}: {curator}")
        print(f"    Keys: {list(curator.keys())}")
        if 'platform_data' in curator:
            print(f"    Platform data: {curator['platform_data']}")
    
    print("\n📊 From twitter_scanner.twitter_curators:")
    from intelligence.social_ingest.twitter_scanner import TwitterScanner
    twitter_scanner = TwitterScanner(social_ingest)
    
    for i, curator in enumerate(twitter_scanner.twitter_curators[:3]):
        print(f"  Curator {i+1}: {curator}")
        print(f"    Keys: {list(curator.keys())}")

if __name__ == "__main__":
    debug_curator_structures()
