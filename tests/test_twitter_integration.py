#!/usr/bin/env python3
"""
Test Twitter Integration - Debug the new approach
"""

import asyncio
import sys
import os

# Add src to path
sys.path.append('src')

from intelligence.social_ingest.social_ingest_basic import SocialIngestModule
from intelligence.social_ingest.twitter_scanner import TwitterScanner

# Mock dependencies for testing
class MockSupabase:
    def create_strand(self, strand): 
        print(f"📝 Created strand: {strand.get('kind', 'unknown')} from {strand.get('content', {}).get('curator_id', 'unknown')}")
        return strand
    
    def update_curator_last_seen(self, curator_id): 
        print(f"🔄 Updated last seen for: {curator_id}")

class MockLLM:
    async def generate_async(self, prompt, **kwargs): 
        # Mock response for testing
        if "token_extraction" in prompt or "Extract token information" in prompt:
            return '{"tokens": [{"token_name": "TEST", "network": "solana", "sentiment": "positive", "confidence": 0.8, "has_chart": false, "chart_type": null, "handle_mentioned": null, "needs_verification": false, "additional_info": "Test token from social media"}]}'
        return '{}'

async def test_twitter_integration():
    """Test the new Twitter integration approach"""
    print("🧪 Testing Twitter Integration...")
    
    # Initialize social ingest module
    social_ingest = SocialIngestModule(MockSupabase(), MockLLM())
    
    # Initialize Twitter scanner
    twitter_scanner = TwitterScanner(social_ingest)
    
    print(f"📊 Twitter scanner initialized with {len(twitter_scanner.twitter_curators)} curators")
    
    # Print curator structure to debug
    print("\n🔍 Curator structure:")
    for i, curator in enumerate(twitter_scanner.twitter_curators[:3]):  # Show first 3
        print(f"  Curator {i+1}: {curator}")
    
    # Test browser initialization
    print("\n🔧 Testing browser initialization...")
    try:
        from playwright.async_api import async_playwright
        
        # Initialize Playwright
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        
        # Create new context and add cookies
        context = await browser.new_context()
        await twitter_scanner._load_cookies()
        
        # Create page from the context with cookies
        page = await context.new_page()
        
        # Set the page on the scanner
        twitter_scanner.page = page
        
        print("✅ Browser initialized successfully")
        
        # Test checking a single curator
        print("\n📱 Testing single curator check...")
        if twitter_scanner.twitter_curators:
            test_curator = twitter_scanner.twitter_curators[0]
            print(f"Testing curator: {test_curator}")
            
            try:
                await twitter_scanner._check_curator(test_curator)
                print("✅ Curator check successful")
            except Exception as e:
                print(f"❌ Curator check failed: {e}")
                import traceback
                traceback.print_exc()
        
        # Clean up
        await page.close()
        await browser.close()
        print("🧹 Cleanup complete")
        
    except Exception as e:
        print(f"❌ Browser initialization failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_twitter_integration())
