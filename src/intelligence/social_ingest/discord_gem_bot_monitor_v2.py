"""
Discord Gem Bot Monitor - Subprocess Version

Monitors Discord channels for new token calls using an external Discord bot script.
Creates strands and sends them to the Universal Learning System for processing.
"""

import asyncio
import json
import logging
import subprocess
import sys
import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.intelligence.universal_learning.universal_learning_system import UniversalLearningSystem
from src.intelligence.supabase_manager import SupabaseManager

logger = logging.getLogger(__name__)

class DiscordGemBotMonitor:
    """
    Monitor Discord channels for new token calls using subprocess approach
    """
    
    def __init__(self, test_mode: bool = True, check_interval: int = 15):
        """
        Initialize Discord Gem Bot Monitor
        
        Args:
            test_mode: If True, uses test allocation (1.2%) and test strand kinds
            check_interval: Seconds between checks (default 15)
        """
        self.test_mode = test_mode
        self.check_interval = check_interval
        self.running = False
        
        # Initialize dependencies
        self.supabase_manager = SupabaseManager()
        self.universal_learning_system = UniversalLearningSystem()
        
        # Channel configuration (only conservative for now)
        self.channel_config = {
            'channel_name': '#gembot-conservative-calls',
            'allocation_pct': 1.2 if test_mode else 12.0,
            'strand_kind': 'gem_bot_conservative_test' if test_mode else 'gem_bot_conservative',
            'risk_level': 'low'
        }
        
        # Path to the Discord monitor script (using mock for now)
        self.discord_script_path = "src/intelligence/social_ingest/discord_monitor_mock.py"
        
        print(f"🤖 Discord Gem Bot Monitor initialized")
        print(f"   - Channel: {self.channel_config['channel_name']}")
        print(f"   - Allocation: {self.channel_config['allocation_pct']}% ({'test' if test_mode else 'live'} mode)")
        print(f"   - Check interval: {check_interval} seconds")
        print(f"   - Discord script: {self.discord_script_path}")
    
    async def start_monitoring(self):
        """Start monitoring Discord for new token calls"""
        print(f"🚀 Starting Discord Gem Bot monitoring...")
        print(f"📊 Monitoring channel: {self.channel_config['channel_name']}")
        print(f"💰 Test mode: {'ON' if self.test_mode else 'OFF'}")
        print(f"⏱️  Check interval: {self.check_interval} seconds")
        print(f"🌐 Discord script: {self.discord_script_path}")
        print("=" * 60)
        
        self.running = True
        
        try:
            while self.running:
                await self._check_for_new_tokens()
                await asyncio.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            print("\n👋 Stopping Discord monitoring...")
        except Exception as e:
            print(f"❌ Error in Discord monitoring: {e}")
        finally:
            self.running = False
    
    async def _check_for_new_tokens(self):
        """Check for new tokens using Discord monitor script"""
        try:
            print(f"🔍 Checking for new tokens - {datetime.now().strftime('%H:%M:%S')}")
            
            # Run the Discord monitor script
            result = subprocess.run([
                sys.executable, self.discord_script_path
            ], capture_output=True, text=True, cwd='/Users/bruce/Documents/Lotus_Trader⚘⟁')
            
            if result.stderr:
                print(f"⚠️  Discord script stderr: {result.stderr}")
                return
            
            # Parse output
            output = result.stdout.strip()
            
            if not output:
                print("   (No new tokens)")
                return
            
            try:
                data = json.loads(output)
                
                if data.get('status') == 'new_tokens_found':
                    tokens = data.get('tokens', [])
                    print(f"🆕 Found {len(tokens)} new tokens!")
                    
                    for token_data in tokens:
                        await self._create_gem_bot_strand(token_data)
                        
                elif data.get('status') == 'error':
                    print(f"❌ Discord script error: {data.get('error')}")
                    
            except json.JSONDecodeError:
                print(f"❌ Failed to parse Discord script output: {output}")
                
        except Exception as e:
            print(f"❌ Error checking for new tokens: {e}")
    
    async def _create_gem_bot_strand(self, token_data: Dict[str, Any]):
        """
        Create a gem_bot strand for the trader
        
        Args:
            token_data: Token information extracted from Discord message
        """
        try:
            print(f"📝 Creating strand for token: {token_data.get('ticker', 'UNKNOWN')}")
            print(f"   Contract: {token_data.get('contract', 'N/A')}")
            print(f"   Market Cap: {token_data.get('market_cap', 'N/A')}")
            print(f"   Liquidity: {token_data.get('liquidity', 'N/A')}")
            
            # Create trading signals
            trading_signals = {
                'action': 'buy',
                'symbol': token_data.get('ticker', 'UNKNOWN'),
                'contract_address': token_data.get('contract'),
                'allocation_pct': self.channel_config['allocation_pct'],
                'source': 'discord_gem_bot',
                'channel': self.channel_config['channel_name'],
                'risk_level': self.channel_config['risk_level'],
                'auto_approve': True,
                'market_cap': token_data.get('market_cap'),
                'liquidity': token_data.get('liquidity'),
                'holders': token_data.get('holders'),
                'raw_content': token_data.get('raw_content', ''),
                'timestamp': token_data.get('timestamp', datetime.now(timezone.utc).isoformat())
            }
            
            # Create strand data
            strand_data = {
                'kind': self.channel_config['strand_kind'],
                'source': 'discord_gem_bot',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'data': {
                    'trading_signals': trading_signals,
                    'token_info': token_data,
                    'channel_info': {
                        'name': self.channel_config['channel_name'],
                        'risk_level': self.channel_config['risk_level']
                    }
                },
                'metadata': {
                    'test_mode': self.test_mode,
                    'monitor_type': 'discord_subprocess',
                    'check_interval': self.check_interval
                }
            }
            
            # Create the strand
            strand = await self.supabase_manager.create_strand(strand_data)
            
            if strand:
                print(f"✅ Created strand: {strand['id']}")
                print(f"   Kind: {strand['kind']}")
                print(f"   Allocation: {trading_signals['allocation_pct']}%")
                print(f"   Auto-approve: {trading_signals['auto_approve']}")
                
                # Trigger Universal Learning System
                await self.universal_learning_system.process_strand(strand)
                print(f"🎯 Strand sent to Universal Learning System")
            else:
                print(f"❌ Failed to create strand")
                
        except Exception as e:
            print(f"❌ Error creating strand: {e}")
    
    def stop(self):
        """Stop monitoring"""
        self.running = False
        print("🛑 Discord monitoring stopped")

# Test function
async def test_discord_monitor():
    """Test the Discord monitor"""
    print("🧪 Testing Discord Gem Bot Monitor...")
    
    monitor = DiscordGemBotMonitor(test_mode=True, check_interval=5)
    
    try:
        # Run for 30 seconds to test
        print("Running for 30 seconds...")
        await asyncio.wait_for(monitor.start_monitoring(), timeout=30)
    except asyncio.TimeoutError:
        print("✅ Test completed (30 seconds)")
    except KeyboardInterrupt:
        print("👋 Test stopped by user")
    finally:
        monitor.stop()

if __name__ == "__main__":
    asyncio.run(test_discord_monitor())
