#!/usr/bin/env python3
"""
Debug script to see what elements are on the Discord page
"""

import asyncio
import json
import time
from playwright.async_api import async_playwright

async def debug_discord_elements():
    """Debug Discord page elements"""
    
    # Load cookies
    cookies_file = "src/config/discord_gem_bot_cookies.json"
    try:
        with open(cookies_file, 'r') as f:
            cookies = json.load(f)
        print(f"🍪 Loaded {len(cookies)} cookies from {cookies_file}")
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
        
        # Navigate to Discord channel
        server_id = "1393627491352055968"
        channel_id = "1405408713505771652"  # Risky channel
        url = f"https://discord.com/channels/{server_id}/{channel_id}"
        print(f"🌐 Navigating to {url}...")
        await page.goto(url, timeout=90000)
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
            if 'risky' in page_content.lower():
                print("✅ Found 'risky' in content")
            else:
                print("❌ 'risky' not found in content")
                
            if 'gembot' in page_content.lower():
                print("✅ Found 'gembot' in content")
            else:
                print("❌ 'gembot' not found in content")
        else:
            print("❌ No page content found")
        
        # Try different selectors to find messages
        print("\n🔍 Trying different selectors for messages...")
        
        selectors_to_try = [
            '[data-list-item-id*="chat-messages"]',
            '[data-list-item-id]',
            '[class*="message"]',
            '[class*="chat"]',
            'div[role="listitem"]',
            'div[data-id]',
            'article',
            'div[class*="message"]',
            'div[class*="Message"]',
            'div[class*="container"]'
        ]
        
        for selector in selectors_to_try:
            try:
                elements = await page.query_selector_all(selector)
                print(f"   Selector '{selector}': {len(elements)} elements")
                if len(elements) > 0:
                    # Show first few element details
                    for i, elem in enumerate(elements[:3]):
                        try:
                            text = await elem.text_content()
                            attrs = await elem.get_attribute('data-list-item-id')
                            print(f"      Element {i+1}: text='{text[:50] if text else 'None'}...', id='{attrs}'")
                        except:
                            pass
            except Exception as e:
                print(f"   Selector '{selector}': Error - {e}")
        
        # Wait for user to see the page
        print("\n👀 Browser is open - check if you can see messages...")
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
    asyncio.run(debug_discord_elements())
