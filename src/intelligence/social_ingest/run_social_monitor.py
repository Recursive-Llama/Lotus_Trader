"""
Social Media Monitor - Combined Twitter and Telegram

Main script to run both Twitter and Telegram monitoring simultaneously.
"""

import asyncio
import logging
import signal
import sys
from typing import Dict, Any

# Add src to path
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from intelligence.social_ingest.social_ingest_basic import SocialIngestModule
from intelligence.social_ingest.twitter_scanner import TwitterScanner
from intelligence.social_ingest.telegram_scanner import TelegramScanner

# Import real components
from utils.supabase_manager import SupabaseManager
from llm_integration.openrouter_client import OpenRouterClient

class SocialMediaMonitor:
    """Combined Twitter and Telegram monitoring"""
    
    def __init__(self):
        self.running = False
        self.tasks = []
        
        # Initialize real components
        self.supabase_manager = SupabaseManager()
        self.llm_client = OpenRouterClient()
        
        # Initialize social ingest module with real components
        self.social_ingest = SocialIngestModule(self.supabase_manager, self.llm_client)
        
        # Initialize scanners
        self.twitter_scanner = TwitterScanner(self.social_ingest)
        self.telegram_scanner = TelegramScanner(
            api_id=21826741,
            api_hash="4643cce207a1a9d56d56a5389a4f1f52"
        )
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\n🛑 Received signal {signum}, shutting down...")
        self.running = False
    
    async def start_monitoring(self):
        """Start monitoring both Twitter and Telegram"""
        try:
            self.running = True
            print("🚀 Starting Social Media Monitor...")
            print("📱 Monitoring Twitter and Telegram for crypto signals")
            print("Press Ctrl+C to stop")
            print()
            
            # Start Twitter monitoring with clean output
            twitter_task = asyncio.create_task(
                self._monitor_twitter_clean()
            )
            self.tasks.append(twitter_task)
            
            # Start Telegram monitoring
            telegram_task = asyncio.create_task(
                self.telegram_scanner.start_monitoring(self.social_ingest, check_interval=60)
            )
            self.tasks.append(telegram_task)
            
            # Wait for tasks to complete
            await asyncio.gather(*self.tasks, return_exceptions=True)
            
        except Exception as e:
            logging.error(f"Error in monitoring: {e}")
        finally:
            await self.stop_monitoring()
    
    async def _monitor_twitter_clean(self):
        """Clean Twitter monitoring with sequential checking - 30 seconds per curator"""
        try:
            # Get enabled curators
            curators = self.social_ingest.get_enabled_curators()
            twitter_curators = [c for c in curators if c.get('platform') == 'twitter']
            
            if not twitter_curators:
                print("❌ No Twitter curators found")
                return
            
            print(f"🔍 Found {len(twitter_curators)} Twitter curators")
            print("📱 Starting sequential monitoring (30 seconds per curator)...")
            
            # Initialize Twitter scanner browser context (without starting its loop)
            print("🔧 Initializing Twitter scanner browser...")
            await self._initialize_twitter_scanner()
            
            current_index = 0
            
            while self.running:
                curator = twitter_curators[current_index]
                handle = curator.get('platform_data', {}).get('handle', curator.get('name', 'unknown'))
                
                print(f"\n📱 Checking {handle}...")
                
                try:
                    # Transform curator data to match Twitter scanner's expected format
                    twitter_curator = {
                        'id': curator['id'],
                        'name': curator['name'],
                        'handle': curator.get('platform_data', {}).get('handle', curator.get('name', 'unknown')),
                        'weight': curator.get('platform_data', {}).get('weight', 0.5),
                        'priority': curator.get('platform_data', {}).get('priority', 'medium'),
                        'tags': curator.get('tags', [])
                    }
                    
                    # Call the Twitter scanner's check method directly
                    await self.twitter_scanner._check_curator(twitter_curator)
                    print(f"   ✅ Checked {handle}")
                    
                except Exception as e:
                    print(f"   ❌ Error checking {handle}: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Wait 30 seconds before checking next curator
                print(f"⏳ Waiting 30 seconds before next curator...")
                await asyncio.sleep(30)
                
                # Move to next curator
                current_index = (current_index + 1) % len(twitter_curators)
            
        except asyncio.CancelledError:
            print("Twitter monitoring cancelled")
        except Exception as e:
            print(f"Error in Twitter monitoring: {e}")
        finally:
            # Clean up browser resources
            await self._cleanup_twitter_scanner()
    
    async def _initialize_twitter_scanner(self):
        """Initialize Twitter scanner browser context without starting the monitoring loop"""
        try:
            from playwright.async_api import async_playwright
            
            # Initialize Playwright
            playwright = await async_playwright().start()
            self.twitter_scanner.browser = await playwright.chromium.launch(headless=True)
            
            # Create new context and add cookies
            self.twitter_scanner.context = await self.twitter_scanner.browser.new_context()
            await self.twitter_scanner._load_cookies()
            
            # Create page from the context with cookies
            self.twitter_scanner.page = await self.twitter_scanner.context.new_page()
            
            print("✅ Twitter scanner browser initialized")
            
        except Exception as e:
            print(f"❌ Failed to initialize Twitter scanner: {e}")
            raise
    
    async def _cleanup_twitter_scanner(self):
        """Clean up Twitter scanner browser resources"""
        try:
            if self.twitter_scanner.page:
                await self.twitter_scanner.page.close()
            if self.twitter_scanner.browser:
                await self.twitter_scanner.browser.close()
            print("🧹 Twitter scanner cleaned up")
        except Exception as e:
            print(f"Warning: Error cleaning up Twitter scanner: {e}")
    
    async def stop_monitoring(self):
        """Stop all monitoring tasks"""
        print("🛑 Stopping monitoring...")
        
        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        print("✅ Monitoring stopped")
    
    async def test_connections(self):
        """Test both Twitter and Telegram connections"""
        print("🔍 Testing connections...")
        
        # Test Telegram (has test_connection method)
        print("📱 Testing Telegram connection...")
        telegram_success = await self.telegram_scanner.test_connection()
        if telegram_success:
            print("✅ Telegram connection successful")
        else:
            print("❌ Telegram connection failed")
        
        # Twitter will be tested when monitoring starts
        print("📱 Twitter connection will be tested when monitoring starts...")
        
        return telegram_success  # Only require Telegram to work for now

async def main():
    """Main function"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize monitor
    monitor = SocialMediaMonitor()
    
    # Test connections first
    print("🧪 Testing connections before starting monitoring...")
    success = await monitor.test_connections()
    
    if not success:
        print("❌ Connection test failed, exiting")
        return
    
    print("\n✅ All connections successful!")
    print("🚀 Starting monitoring...")
    print()
    
    # Start monitoring
    try:
        await monitor.start_monitoring()
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
