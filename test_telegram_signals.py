#!/usr/bin/env python3
"""
Test script for Telegram signal notifications

This script tests the Telegram signal notification system with sample data.
Run this to verify the integration works before using in production.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from communication.telegram_signal_notifier import TelegramSignalNotifier


async def test_telegram_notifications():
    """Test the Telegram signal notification system"""
    
    print("🧪 Testing Telegram Signal Notifications")
    print("=" * 50)
    
    # Check environment variables
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    channel_id = os.getenv('TELEGRAM_CHANNEL_ID')
    
    if not bot_token or not channel_id:
        print("❌ Missing required environment variables:")
        print("   - TELEGRAM_BOT_TOKEN")
        print("   - TELEGRAM_CHANNEL_ID")
        print("\nPlease set these in your .env file or environment.")
        return False
    
    print(f"✅ Bot token configured: {bot_token[:10]}...")
    print(f"✅ Channel ID configured: {channel_id}")
    print()
    
    # Initialize notifier
    notifier = TelegramSignalNotifier(
        bot_token=bot_token,
        channel_id=channel_id,
        api_id=21826741,
        api_hash="4643cce207a1a9d56d56a5389a4f1f52",
        session_file="src/config/telegram_session.txt"
    )
    
    # Test connection
    print("🔍 Testing connection to Telegram channel...")
    connection_ok = await notifier.test_connection()
    
    if not connection_ok:
        print("❌ Failed to connect to Telegram channel")
        print("   Please check your bot token and channel ID")
        return False
    
    print("✅ Connection successful!")
    print()
    
    # Test buy signal
    print("📈 Testing BUY signal notification...")
    buy_success = await notifier.send_buy_signal(
        token_ticker="TEST",
        token_contract="0x1234567890123456789012345678901234567890",
        chain="base",
        amount_native=0.1,
        price=0.00000123,
        tx_hash="0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        source_tweet_url="https://twitter.com/example/status/1234567890",
        allocation_pct=2.5
    )
    
    if buy_success:
        print("✅ Buy signal sent successfully!")
    else:
        print("❌ Failed to send buy signal")
    
    print()
    
    # Wait a moment between messages
    await asyncio.sleep(2)
    
    # Test sell signal
    print("📉 Testing SELL signal notification...")
    sell_success = await notifier.send_sell_signal(
        token_ticker="TEST",
        token_contract="0x1234567890123456789012345678901234567890",
        chain="base",
        tokens_sold=1000000,
        sell_price=0.00000246,
        tx_hash="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        profit_pct=100.0,
        profit_usd=123.45,
        total_profit_usd=123.45,
        source_tweet_url="https://twitter.com/example/status/1234567890"
    )
    
    if sell_success:
        print("✅ Sell signal sent successfully!")
    else:
        print("❌ Failed to send sell signal")
    
    print()
    
    # Close connection
    await notifier.close()
    
    # Summary
    if buy_success and sell_success:
        print("🎉 All tests passed! Telegram signal notifications are working correctly.")
        print("\nYour trading system will now send notifications to your Telegram group for:")
        print("  • Buy signals with token info, amounts, and transaction links")
        print("  • Sell signals with profit tracking and P&L information")
        print("  • Source tweet links when available")
        return True
    else:
        print("❌ Some tests failed. Please check the configuration and try again.")
        return False


async def test_message_formatting():
    """Test message formatting without sending"""
    print("\n🎨 Testing message formatting...")
    print("=" * 30)
    
    notifier = TelegramSignalNotifier(
        bot_token="dummy",
        channel_id="dummy",
        api_id=21826741,
        api_hash="4643cce207a1a9d56d56a5389a4f1f52"
    )
    
    # Test buy message formatting
    buy_message = notifier._format_buy_message(
        token_ticker="PEPE",
        token_link="https://basescan.org/token/0x1234567890123456789012345678901234567890",
        amount_native=0.1,
        native_symbol="ETH",
        price=0.00000123,
        tx_link="https://basescan.org/tx/0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        source_tweet_url="https://twitter.com/example/status/1234567890",
        allocation_pct=2.5
    )
    
    print("📈 BUY MESSAGE FORMAT:")
    print(buy_message)
    print()
    
    # Test sell message formatting
    sell_message = notifier._format_sell_message(
        token_ticker="PEPE",
        token_link="https://basescan.org/token/0x1234567890123456789012345678901234567890",
        tokens_sold=1000000,
        sell_price=0.00000246,
        native_symbol="ETH",
        tx_link="https://basescan.org/tx/0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        profit_pct=100.0,
        profit_usd=123.45,
        total_profit_usd=123.45,
        source_tweet_url="https://twitter.com/example/status/1234567890"
    )
    
    print("📉 SELL MESSAGE FORMAT:")
    print(sell_message)
    print()


async def main():
    """Main test function"""
    print("🚀 Telegram Signal Notification Test Suite")
    print("=" * 50)
    print()
    
    # Test message formatting first
    await test_message_formatting()
    
    # Ask user if they want to send actual test messages
    print("⚠️  The next test will send actual messages to your Telegram channel.")
    response = input("Do you want to proceed? (y/N): ").strip().lower()
    
    if response in ['y', 'yes']:
        success = await test_telegram_notifications()
        if success:
            print("\n🎯 Setup complete! Your trading system is ready to send Telegram notifications.")
        else:
            print("\n🔧 Please fix the configuration issues and try again.")
    else:
        print("\n✅ Message formatting test completed. Run again with 'y' to test actual sending.")


if __name__ == "__main__":
    asyncio.run(main())
