"""
Telegram Authentication Setup

Sets up Telegram authentication using user session for monitoring public groups.
Uses Telethon library for Telegram API access.
"""

import asyncio
import logging
import os
from telethon import TelegramClient
from telethon.sessions import StringSession

logger = logging.getLogger(__name__)

class TelegramAuthSetup:
    """Setup Telegram authentication and save session"""
    
    def __init__(self, api_id: int, api_hash: str, phone: str, session_file: str = None):
        """
        Initialize Telegram authentication
        
        Args:
            api_id: Telegram API ID
            api_hash: Telegram API Hash
            phone: Phone number in international format
            session_file: Path to save session file
        """
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.session_file = session_file or "src/config/telegram_session.txt"
        self.client = None
        
    async def setup_authentication(self):
        """Setup Telegram authentication and save session"""
        try:
            # Create client with string session
            self.client = TelegramClient(StringSession(), self.api_id, self.api_hash)
            
            # Connect and authenticate
            await self.client.start(phone=self.phone)
            
            # Get session string
            session_string = self.client.session.save()
            
            # Save session to file
            os.makedirs(os.path.dirname(self.session_file), exist_ok=True)
            with open(self.session_file, 'w') as f:
                f.write(session_string)
            
            logger.info(f"✅ Telegram authentication successful! Session saved to {self.session_file}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Telegram authentication failed: {e}")
            return False
        finally:
            if self.client:
                await self.client.disconnect()
    
    async def test_connection(self):
        """Test Telegram connection with saved session"""
        try:
            # Load session from file
            if not os.path.exists(self.session_file):
                logger.error(f"Session file not found: {self.session_file}")
                return False
            
            with open(self.session_file, 'r') as f:
                session_string = f.read().strip()
            
            # Create client with saved session
            self.client = TelegramClient(StringSession(session_string), self.api_id, self.api_hash)
            await self.client.start()
            
            # Get user info
            me = await self.client.get_me()
            logger.info(f"✅ Connected as: {me.first_name} (@{me.username})")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Telegram connection test failed: {e}")
            return False
        finally:
            if self.client:
                await self.client.disconnect()
    
    async def test_groups_access(self, group_handles: list):
        """Test access to specific Telegram groups"""
        try:
            # Load session
            if not os.path.exists(self.session_file):
                logger.error(f"Session file not found: {self.session_file}")
                return False
            
            with open(self.session_file, 'r') as f:
                session_string = f.read().strip()
            
            self.client = TelegramClient(StringSession(session_string), self.api_id, self.api_hash)
            await self.client.start()
            
            logger.info("🔍 Testing access to configured groups...")
            
            for handle in group_handles:
                try:
                    # Try to get group info
                    group = await self.client.get_entity(handle)
                    logger.info(f"✅ Access to {handle}: {group.title} ({group.participants_count} members)")
                except Exception as e:
                    logger.warning(f"❌ No access to {handle}: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Group access test failed: {e}")
            return False
        finally:
            if self.client:
                await self.client.disconnect()

async def main():
    """Main function for Telegram authentication setup"""
    # Telegram API credentials
    API_ID = 21826741
    API_HASH = "4643cce207a1a9d56d56a5389a4f1f52"
    PHONE = "+447449700491"
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize auth setup
    auth = TelegramAuthSetup(API_ID, API_HASH, PHONE)
    
    print("🚀 Starting Telegram authentication setup...")
    print(f"Phone: {PHONE}")
    print(f"API ID: {API_ID}")
    print()
    
    # Setup authentication
    success = await auth.setup_authentication()
    if not success:
        print("❌ Authentication failed!")
        return
    
    print("✅ Authentication successful!")
    print()
    
    # Test connection
    print("🔍 Testing connection...")
    success = await auth.test_connection()
    if not success:
        print("❌ Connection test failed!")
        return
    
    print("✅ Connection test successful!")
    print()
    
    # Test group access
    group_handles = [
        -1002691312655,  # ducksinnerpond (now private)
        -1002252103258,  # slaying charts with jones rida
        -1002263903412,  # cryptic's den
        "cryptolyxecalls", 
        "crypto_popseye_calls",
        "zincalpha",
        "PredictTheMarkets",  # Sachs
        "eleetmoramblings"  # Eleetmo
    ]
    
    print("🔍 Testing group access...")
    await auth.test_groups_access(group_handles)
    
    print("\n🎉 Telegram setup complete!")
    print("You can now use the Telegram scanner to monitor these groups.")

if __name__ == "__main__":
    asyncio.run(main())

