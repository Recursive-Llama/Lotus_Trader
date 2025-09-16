"""
Test Telegram Connection

Simple test script to verify Telegram connection and group access.
"""

import asyncio
import logging
import sys
import os

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from intelligence.social_ingest.telegram_scanner import TelegramScanner

async def main():
    """Test Telegram connection"""
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    print("🔍 Testing Telegram Connection...")
    print()
    
    # Initialize scanner
    scanner = TelegramScanner(
        api_id=21826741,
        api_hash="4643cce207a1a9d56d56a5389a4f1f52"
    )
    
    # Test connection
    success = await scanner.test_connection()
    
    if success:
        print("\n✅ Telegram connection test successful!")
        print("📱 Ready to monitor Telegram groups")
    else:
        print("\n❌ Telegram connection test failed!")
        print("Please check your session file and group access")

if __name__ == "__main__":
    asyncio.run(main())

