#!/usr/bin/env python3
"""
Discord Monitor Script for Gem Bot Token Detection

This script connects to Discord using a user token and monitors the conservative
channel for new token calls. It compares recent messages with previous state
and returns new token data as JSON when changes are detected.

Usage:
    python discord_monitor.py

Returns:
    - JSON with new token data if changes detected
    - Empty output if no changes
"""

import os
import json
import asyncio
import logging
import aiohttp
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DiscordTokenMonitor:
    """Monitor Discord channel for new token calls using user token"""
    
    def __init__(self):
        self.token = os.getenv('DISCORD_TOKEN')
        self.channel_id = os.getenv('DISCORD_CHANNEL_ID', '1405408713505771652')
        self.state_file = 'src/config/discord_monitor_state.json'
        self.seen_messages = set()
        self.base_url = "https://discord.com/api/v10"
        
        if not self.token:
            raise ValueError("DISCORD_TOKEN environment variable is required")
    
    def load_previous_state(self) -> Dict[str, Any]:
        """Load previous message state from file"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    self.seen_messages = set(state.get('seen_messages', []))
                    return state
        except Exception as e:
            logger.warning(f"Could not load previous state: {e}")
        
        return {'seen_messages': [], 'last_check': None}
    
    def save_state(self, state: Dict[str, Any]):
        """Save current state to file"""
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save state: {e}")
    
    def extract_token_data(self, message_content: str) -> Optional[Dict[str, Any]]:
        """Extract token information from Discord message content"""
        try:
            # Look for common patterns in token call messages
            content_lower = message_content.lower()
            
            # Check if this looks like a token call
            token_indicators = [
                'mint address', 'mc:', 'liquidity', 'txns:', 'holders:', 
                'creator:', 'bundle:', 'sniped:', 'fresh:', 'platform:'
            ]
            
            if not any(indicator in content_lower for indicator in token_indicators):
                return None
            
            # Extract contract address (look for Solana address pattern)
            import re
            solana_address_pattern = r'[1-9A-HJ-NP-Za-km-z]{32,44}'
            addresses = re.findall(solana_address_pattern, message_content)
            
            if not addresses:
                return None
            
            # Use the first valid-looking address
            contract_address = addresses[0]
            
            # Extract token name/ticker from title (look for emoji + text pattern)
            ticker_match = re.search(r'[💎🚀🔥💫⭐🌟]+\s*([A-Za-z0-9]+)', message_content)
            ticker = ticker_match.group(1) if ticker_match else "UNKNOWN"
            
            # Extract metrics using more specific patterns for Discord embeds
            
            mc_match = re.search(r'mc:\s*\$?([0-9,\.]+[kmb]?)', content_lower)
            liq_match = re.search(r'liquidity:\s*\$?([0-9,\.]+[kmb]?)', content_lower)
            txns_match = re.search(r'txns:\s*([0-9,]+)', content_lower)
            holders_match = re.search(r'holders:\s*([0-9,]+)', content_lower)
            creator_match = re.search(r'creator:\s*([0-9,\.]+%)', content_lower)
            bundle_match = re.search(r'bundle:\s*([0-9,\.]+%)', content_lower)
            sniped_match = re.search(r'sniped:\s*([0-9,\.]+%)', content_lower)
            fresh_match = re.search(r'fresh:\s*([0-9,]+)', content_lower)
            platform_match = re.search(r'platform:\s*([0-9,]+)', content_lower)
            
            # Convert K/M/B suffixes to numbers
            def parse_number(value_str):
                if not value_str:
                    return None
                value_str = value_str.replace(',', '').upper()  # Convert to uppercase for consistency
                if value_str.endswith('K'):
                    return int(float(value_str[:-1]) * 1000)
                elif value_str.endswith('M'):
                    return int(float(value_str[:-1]) * 1000000)
                elif value_str.endswith('B'):
                    return int(float(value_str[:-1]) * 1000000000)
                else:
                    return int(float(value_str))
            
            token_data = {
                'ticker': ticker,
                'contract': contract_address,
                'market_cap': parse_number(mc_match.group(1)) if mc_match else None,
                'liquidity': parse_number(liq_match.group(1)) if liq_match else None,
                'transactions': int(txns_match.group(1).replace(',', '')) if txns_match else None,
                'holders': int(holders_match.group(1).replace(',', '')) if holders_match else None,
                'creator_pct': creator_match.group(1) if creator_match else None,
                'bundle_pct': bundle_match.group(1) if bundle_match else None,
                'sniped_pct': sniped_match.group(1) if sniped_match else None,
                'fresh': int(fresh_match.group(1).replace(',', '')) if fresh_match else None,
                'platform': int(platform_match.group(1).replace(',', '')) if platform_match else None,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'raw_content': message_content[:500]  # First 500 chars for context
            }
            
            return token_data
            
        except Exception as e:
            logger.error(f"Error extracting token data: {e}")
            return None
    
    async def check_for_new_tokens(self) -> List[Dict[str, Any]]:
        """Check Discord channel for new token calls using API - simplified approach"""
        try:
            # Use aiohttp to make API calls
            headers = {
                'Authorization': self.token,
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                # Get only the most recent message
                url = f"{self.base_url}/channels/{self.channel_id}/messages"
                params = {'limit': 1}  # Only get the latest message
                
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status != 200:
                        logger.error(f"Failed to fetch messages: {response.status}")
                        return []
                    
                    messages = await response.json()
                    
                    if not messages:
                        return []
                    
                    # Get the latest message
                    latest_message = messages[0]
                    content = latest_message.get('content', '')
                    author = latest_message.get('author', {}).get('username', 'Unknown')
                    timestamp = latest_message.get('timestamp', '')
                    embeds = latest_message.get('embeds', [])
                    
                    # Show the latest message for verification
                    print(f"📺 #gembot-conservative-calls:")
                    print(f"   👤 From: {author}")
                    print(f"   ⏰ Time: {timestamp}")
                    
                    if content:
                        print(f"   📝 Content: {content[:100]}{'...' if len(content) > 100 else ''}")
                    
                    # Check for embeds (where the token data likely is)
                    if embeds:
                        embed = embeds[0]  # Just the first embed
                        if embed.get('title'):
                            print(f"   💎 Token: {embed['title']}")
                        if embed.get('description'):
                            print(f"   📝 Description: {embed['description']}")
                        if embed.get('fields'):
                            print(f"   📊 Token Data:")
                            for field in embed['fields']:
                                print(f"      {field.get('name', '')}: {field.get('value', '')}")
                    
                    # Extract token data from the latest message
                    embed_text = ""
                    if embeds:
                        embed = embeds[0]
                        if embed.get('title'):
                            embed_text += embed['title'] + " "
                        if embed.get('description'):
                            embed_text += embed['description'] + " "
                        if embed.get('fields'):
                            for field in embed['fields']:
                                embed_text += f"{field.get('name', '')}: {field.get('value', '')} "
                    
                    # Try to extract token data
                    token_data = self.extract_token_data(embed_text)
                    
                    if token_data:
                        print(f"   ✅ Extracted: {token_data['ticker']} - {token_data['contract']}")
                        return [token_data]
                    else:
                        print(f"   ❌ No token data found")
                        return []
            
        except Exception as e:
            logger.error(f"Error in check_for_new_tokens: {e}")
            return []

async def main():
    """Main function to run the Discord monitor"""
    try:
        monitor = DiscordTokenMonitor()
        new_tokens = await monitor.check_for_new_tokens()
        
        if new_tokens:
            # Return JSON with new token data
            output = {
                'status': 'new_tokens_found',
                'count': len(new_tokens),
                'tokens': new_tokens,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            print(json.dumps(output, indent=2))
        else:
            # Return empty output for no changes
            print("")
            
    except Exception as e:
        logger.error(f"Error in main: {e}")
        print(json.dumps({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }))

if __name__ == "__main__":
    asyncio.run(main())
