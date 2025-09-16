"""
Telegram Scanner

Monitors Telegram groups for curator messages and extracts token information.
Uses Telethon library for Telegram API access.
"""

import asyncio
import logging
import os
import yaml
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import Message

logger = logging.getLogger(__name__)

class TelegramScanner:
    """Scanner for monitoring Telegram groups"""
    
    def __init__(self, api_id: int, api_hash: str, session_file: str = None, config_path: str = None):
        """
        Initialize Telegram Scanner
        
        Args:
            api_id: Telegram API ID
            api_hash: Telegram API Hash
            session_file: Path to session file
            config_path: Path to curator configuration file
        """
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_file = session_file or "src/config/telegram_session.txt"
        self.config_path = config_path or "src/config/twitter_curators.yaml"
        self.client = None
        
        # Load curator configuration
        self.curators_config = self._load_curators_config()
        self.telegram_curators = self._get_telegram_curators()
        
        # Track processed messages
        self.processed_messages = set()
        self.curator_last_seen = {}
        
        logger.info(f"Telegram Scanner initialized with {len(self.telegram_curators)} Telegram curators")
    
    def _load_curators_config(self) -> Dict[str, Any]:
        """Load curator configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load curators config: {e}")
            return {'curators': []}
    
    def _get_telegram_curators(self) -> Dict[str, Dict[str, Any]]:
        """Get curators with Telegram platforms"""
        telegram_curators = {}
        
        for curator in self.curators_config.get('curators', []):
            platforms = curator.get('platforms', {})
            if 'telegram' in platforms and platforms['telegram'].get('active', False):
                tg_data = platforms['telegram']
                curator_id = f"telegram:{tg_data['handle']}"
                
                telegram_curators[curator_id] = {
                    **curator,
                    'platform': 'telegram',
                    'platform_data': tg_data,
                    'channel_id': tg_data.get('channel_id', ''),
                    'handle': tg_data['handle']
                }
        
        return telegram_curators
    
    async def start_monitoring(self, social_ingest_module, check_interval: int = 60):
        """
        Start monitoring Telegram groups
        
        Args:
            social_ingest_module: Social ingest module for processing messages
            check_interval: Check interval in seconds
        """
        try:
            # Load session and connect
            if not os.path.exists(self.session_file):
                logger.error(f"Session file not found: {self.session_file}")
                logger.error("Please run telegram_auth_setup.py first")
                return
            
            with open(self.session_file, 'r') as f:
                session_string = f.read().strip()
            
            self.client = TelegramClient(StringSession(session_string), self.api_id, self.api_hash)
            await self.client.start()
            
            logger.info("🚀 Telegram monitoring started")
            
            # Main monitoring loop
            while True:
                try:
                    await self._check_all_curators(social_ingest_module)
                    await asyncio.sleep(check_interval)
                except KeyboardInterrupt:
                    logger.info("🛑 Monitoring stopped by user")
                    break
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                    await asyncio.sleep(check_interval)
                    
        except Exception as e:
            logger.error(f"Failed to start Telegram monitoring: {e}")
        finally:
            if self.client:
                await self.client.disconnect()
    
    async def _check_all_curators(self, social_ingest_module):
        """Check all Telegram curators for new messages"""
        for curator_id, curator in self.telegram_curators.items():
            try:
                await self._check_curator(curator_id, curator, social_ingest_module)
            except Exception as e:
                logger.error(f"Error checking curator {curator_id}: {e}")
    
    async def _check_curator(self, curator_id: str, curator: Dict[str, Any], social_ingest_module):
        """Check a specific curator's Telegram group for new messages"""
        try:
            channel_id = curator.get('channel_id', '')
            if not channel_id:
                logger.debug(f"No channel_id for curator {curator_id}")
                return
            
            # Get group entity
            try:
                group = await self.client.get_entity(channel_id)
            except Exception as e:
                logger.warning(f"Could not access group {channel_id}: {e}")
                return
            
            # Get recent messages (limit to 5 for efficiency)
            messages = await self.client.get_messages(group, limit=5)
            
            # Process messages
            new_messages = 0
            for message in messages:
                if not isinstance(message, Message) or not message.text:
                    continue
                
                # Create unique message ID
                message_id = f"{group.id}_{message.id}"
                
                # Skip if already processed
                if message_id in self.processed_messages:
                    continue
                
                # Skip if this is the last seen message or older
                last_seen = self.curator_last_seen.get(curator_id)
                if last_seen and message.id <= last_seen:
                    continue
                
                # Only process messages from the last 2 hours to avoid old messages
                message_time = message.date
                current_time = datetime.now(timezone.utc)
                if (current_time - message_time).total_seconds() > 7200:  # 2 hours
                    logger.debug(f"Skipping old message from {message_time}")
                    continue
                
                # Process message
                await self._process_message(curator_id, curator, message, social_ingest_module)
                
                # Mark as processed
                self.processed_messages.add(message_id)
                new_messages += 1
                
                # Update last seen
                if not last_seen or message.id > last_seen:
                    self.curator_last_seen[curator_id] = message.id
            
            if new_messages > 0:
                logger.info(f"📱 Processed {new_messages} new messages from {curator_id}")
            
        except Exception as e:
            logger.error(f"Error checking curator {curator_id}: {e}")
    
    async def _process_message(self, curator_id: str, curator: Dict[str, Any], message: Message, social_ingest_module):
        """Process a Telegram message"""
        try:
            # Create message data
            message_data = {
                'text': message.text,
                'timestamp': message.date.isoformat(),
                'url': f"https://t.me/{curator.get('channel_id', '')}/{message.id}",
                'message_id': message.id,
                'platform': 'telegram'
            }
            
            # Add image data if present
            if message.photo:
                try:
                    # Download image
                    image_path = await self.client.download_media(message.photo)
                    if image_path and os.path.exists(image_path):
                        with open(image_path, 'rb') as f:
                            message_data['image_data'] = f.read()
                        # Clean up temp file
                        os.remove(image_path)
                except Exception as e:
                    logger.debug(f"Could not download image from message: {e}")
            
            # Process through social ingest module
            strand = await social_ingest_module.process_social_signal(curator_id, message_data)
            if strand:
                logger.info(f"✅ Created strand from Telegram message: {curator_id}")
            else:
                logger.debug(f"No strand created from Telegram message: {curator_id}")
                
        except Exception as e:
            logger.error(f"Error processing Telegram message: {e}")
    
    async def test_connection(self):
        """Test Telegram connection"""
        try:
            if not os.path.exists(self.session_file):
                logger.error(f"Session file not found: {self.session_file}")
                return False
            
            with open(self.session_file, 'r') as f:
                session_string = f.read().strip()
            
            self.client = TelegramClient(StringSession(session_string), self.api_id, self.api_hash)
            await self.client.start()
            
            # Get user info
            me = await self.client.get_me()
            logger.info(f"✅ Connected as: {me.first_name} (@{me.username})")
            
            # Test group access
            logger.info("🔍 Testing group access...")
            for curator_id, curator in self.telegram_curators.items():
                channel_id = curator.get('channel_id', '')
                if channel_id:
                    try:
                        group = await self.client.get_entity(channel_id)
                        logger.info(f"✅ Access to {channel_id}: {group.title}")
                    except Exception as e:
                        logger.warning(f"❌ No access to {channel_id}: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Telegram connection test failed: {e}")
            return False
        finally:
            if self.client:
                await self.client.disconnect()
    
    def get_telegram_curators(self) -> List[Dict[str, Any]]:
        """Get list of Telegram curators"""
        return list(self.telegram_curators.values())

async def main():
    """Main function for testing Telegram scanner"""
    # Telegram API credentials
    API_ID = 21826741
    API_HASH = "4643cce207a1a9d56d56a5389a4f1f52"
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize scanner
    scanner = TelegramScanner(API_ID, API_HASH)
    
    print("🔍 Testing Telegram scanner...")
    
    # Test connection
    success = await scanner.test_connection()
    if success:
        print("✅ Telegram scanner test successful!")
    else:
        print("❌ Telegram scanner test failed!")

if __name__ == "__main__":
    asyncio.run(main())