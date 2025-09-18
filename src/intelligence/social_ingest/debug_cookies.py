#!/usr/bin/env python3
"""
Debug script to test cookie loading and page content
"""

import asyncio
import json
import time
from playwright.async_api import async_playwright

async def debug_cookies():
    """Debug cookie loading and page content"""
    
    # Load cookies
    cookies_file = "src/config/gem_bot_cookies.json"
    try:
        with open(cookies_file, 'r') as f:
            cookies = json.load(f)
        print(f"🍪 Loaded {len(cookies)} cookies from {cookies_file}")
        
        # Show cookie details
        for i, cookie in enumerate(cookies):
            print(f"   Cookie {i+1}: {cookie.get('name')}")
            print(f"      Domain: {cookie.get('domain')}")
            print(f"      Expires: {cookie.get('expires')}")
            print(f"      Value: {cookie.get('value', '')[:50]}...")
            print()
            
    except Exception as e:
        print(f"❌ Error loading cookies: {e}")
        return
    
    # Test with browser
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    page = await browser.new_page()
    
    try:
        # Apply cookies
        print("🍪 Applying cookies to browser...")
        await page.context.add_cookies(cookies)
        print("✅ Cookies applied")
        
        # Navigate to page
        url = "https://gembot.io/feed"
        print(f"🌐 Navigating to {url}...")
        await page.goto(url, timeout=60000)
        print("✅ Page loaded")
        
        # Wait for content
        await page.wait_for_timeout(5000)
        
        # Check current URL
        current_url = page.url
        print(f"🌐 Current URL: {current_url}")
        
        # Get page content
        page_content = await page.text_content('body')
        print(f"📄 Page content length: {len(page_content) if page_content else 0}")
        
        if page_content:
            print(f"📄 First 1000 characters:")
            print(page_content[:1000])
            print("...")
            
            # Check for specific content
            if 'Risky' in page_content:
                print("✅ Found 'Risky' in content")
            else:
                print("❌ 'Risky' not found in content")
                
            if 'Conservative' in page_content:
                print("✅ Found 'Conservative' in content")
            else:
                print("❌ 'Conservative' not found in content")
                
            if 'login' in page_content.lower():
                print("❌ Found 'login' in content - may be on login page")
            else:
                print("✅ No 'login' found in content")
                
            if 'sign in' in page_content.lower():
                print("❌ Found 'sign in' in content - may be on login page")
            else:
                print("✅ No 'sign in' found in content")
        else:
            print("❌ No page content found")
        
        # Wait for user to see the page
        print("\n👀 Browser is open - check if you're logged in...")
        print("Press Enter to continue...")
        input()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await browser.close()
        await playwright.stop()

if __name__ == "__main__":
    asyncio.run(debug_cookies())
