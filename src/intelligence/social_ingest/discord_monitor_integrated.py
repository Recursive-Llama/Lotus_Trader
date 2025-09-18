#!/usr/bin/env python3
"""
Discord Monitor - Integrated Version

This module provides Discord monitoring that integrates cleanly with the main
social trading system. It monitors Discord channels for new token calls and
creates strands that are processed by the Universal Learning System.

Features:
- Clean, non-overwhelming output
- Integrates with existing Universal Learning System
- Creates strands for new tokens
- Shows status every minute when no new tokens
- Shows ticker + contract for new tokens
"""

import asyncio
import json
import subprocess
import sys
import os
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from intelligence.universal_learning.universal_learning_system import UniversalLearningSystem
from utils.supabase_manager import SupabaseManager
from llm_integration.openrouter_client import OpenRouterClient

logger = logging.getLogger(__name__)


class DiscordMonitorIntegrated:
    """
    Integrated Discord Monitor for Social Trading System
    
    Monitors Discord channels for new token calls and creates strands
    that are processed by the Universal Learning System.
    """
    
    def __init__(self, learning_system: UniversalLearningSystem, check_interval: int = 60):
        """
        Initialize Discord Monitor
        
        Args:
            learning_system: Universal Learning System instance
            check_interval: Seconds between checks (default: 60)
        """
        self.learning_system = learning_system
        self.check_interval = check_interval
        self.discord_script = "src/intelligence/social_ingest/discord_monitor.py"
        self.running = False
        self.seen_contracts = set()
        self.last_status_time = datetime.now()
        
        print(f"🔍 Discord: Initialized monitoring (check every {check_interval}s)")
    
    async def create_strand_from_token_data(self, token_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a gem_bot_conservative strand from token data"""
        try:
            import uuid
            strand_id = str(uuid.uuid4())
            
            # Create strand using the correct structure
            strand = {
                "id": strand_id,
                "module": "discord_gem_bot",
                "kind": "gem_bot_conservative",
                "symbol": token_data['ticker'],
                "timeframe": None,
                "session_bucket": f"discord_{datetime.now(timezone.utc).strftime('%Y%m%d_%H')}",
                "regime": None,
                "tags": ["discord", "gem_bot", "conservative", "auto_approved"],
                "target_agent": "trader_lowcap",
                "sig_sigma": None,
                "sig_confidence": 0.9,
                "confidence": 0.9,
                "sig_direction": "buy",
                "trading_plan": None,
                "signal_pack": {
                    "token": {
                        "ticker": token_data['ticker'],
                        "contract": token_data['contract'],
                        "chain": "solana",
                        "price": None,
                        "volume_24h": None,
                        "market_cap": token_data['market_cap'],
                        "liquidity": token_data['liquidity'],
                        "dex": "pump.fun",
                        "verified": False
                    },
                    "venue": {
                        "dex": "pump.fun",
                        "chain": "solana",
                        "liq_usd": token_data['liquidity'],
                        "vol24h_usd": None
                    },
                    "curator": {
                        "id": "gem_bot_conservative",
                        "name": "Gem Bot Conservative",
                        "platform": "discord",
                        "handle": "#gembot-conservative-calls",
                        "weight": 1.0,
                        "priority": "high",
                        "tags": ["conservative", "auto_approved"]
                    },
                    "trading_signals": {
                        "action": "buy",
                        "timing": "immediate",
                        "confidence": 0.9,
                        "allocation_pct": 12.0,
                        "auto_approve": True,
                        "source": "discord_gem_bot",
                        "channel": "#gembot-conservative-calls",
                        "risk_level": "low"
                    }
                },
                "module_intelligence": {
                    "discord_signal": {
                        "message": {
                            "text": token_data['raw_content'],
                            "timestamp": token_data['timestamp'],
                            "url": f"https://discord.com/channels/1393627491352055968/1405408713505771652",
                            "has_image": False,
                            "has_chart": False,
                            "chart_type": None
                        },
                        "context_slices": {
                            "liquidity_bucket": self._get_liquidity_bucket(token_data.get('liquidity', 0)),
                            "volume_bucket": "unknown",
                            "time_bucket_utc": self._get_time_bucket(),
                            "sentiment": "positive"
                        }
                    }
                },
                "status": "active"
            }
            
            return strand
            
        except Exception as e:
            logger.error(f"Error creating strand from token data: {e}")
            return None
    
    def _get_liquidity_bucket(self, liquidity):
        """Get liquidity bucket for context"""
        if liquidity < 10000:
            return "micro"
        elif liquidity < 50000:
            return "small"
        elif liquidity < 200000:
            return "medium"
        elif liquidity < 1000000:
            return "large"
        else:
            return "mega"
    
    def _get_time_bucket(self):
        """Get time bucket for context"""
        hour = datetime.now(timezone.utc).hour
        if 0 <= hour < 6:
            return "night"
        elif 6 <= hour < 12:
            return "morning"
        elif 12 <= hour < 18:
            return "afternoon"
        else:
            return "evening"
    
    async def run_discord_monitor(self) -> Optional[str]:
        """Run the Discord monitor script and return output"""
        try:
            result = subprocess.run(
                [sys.executable, self.discord_script],
                capture_output=True,
                text=True,
                cwd=os.getcwd(),
                env=os.environ.copy()
            )
            if result.stderr:
                logger.warning(f"Discord script stderr: {result.stderr}")
            return result.stdout
        except Exception as e:
            logger.error(f"Error running Discord script: {e}")
            return None
    
    async def process_new_token_data(self, output: str) -> List[Dict[str, Any]]:
        """Process new token data when changes are detected"""
        try:
            if not output:
                return []
            
            # Extract JSON from output
            json_start = output.find('{')
            if json_start == -1:
                return []
            
            json_part = output[json_start:]
            data = json.loads(json_part)
            
            if data.get('status') == 'new_tokens_found':
                tokens = data.get('tokens', [])
                
                # Check for new unique contract addresses
                new_tokens = []
                for token in tokens:
                    contract = token.get('contract')
                    if contract and contract not in self.seen_contracts:
                        new_tokens.append(token)
                        self.seen_contracts.add(contract)
                
                return new_tokens
            
            return []
            
        except Exception as e:
            logger.error(f"Error processing token data: {e}")
            return []
    
    async def start_monitoring(self):
        """Start Discord monitoring with clean output"""
        print(f"🔍 Discord: Starting monitoring of #gembot-conservative-calls")
        print(f"🔍 Discord: Check interval: {self.check_interval} seconds")
        
        self.running = True
        
        # Get initial reference
        print(f"🔍 Discord: Getting initial reference...")
        initial_output = await self.run_discord_monitor()
        if initial_output:
            initial_tokens = await self.process_new_token_data(initial_output)
            print(f"🔍 Discord: Initial reference captured ({len(initial_tokens)} tokens)")
        else:
            print(f"⚠️ Discord: Could not get initial reference")
        
        try:
            check_num = 0
            while self.running:
                check_num += 1
                current_time = datetime.now()
                
                # Run Discord monitor
                current_output = await self.run_discord_monitor()
                
                if current_output:
                    # Process for new tokens
                    new_tokens = await self.process_new_token_data(current_output)
                    
                    if new_tokens:
                        # New tokens found - show details
                        for token in new_tokens:
                            print(f"🆕 Discord: NEW TOKEN! {token.get('ticker')} - {token.get('contract')}")
                            
                            # Create strand
                            strand = await self.create_strand_from_token_data(token)
                            if strand:
                                # Send to Universal Learning System
                                await self.learning_system.process_strand_event(strand)
                                print(f"   🎯 Strand created and sent to trader")
                            else:
                                print(f"   ❌ Failed to create strand")
                    else:
                        # No new tokens - show status every minute
                        time_since_last_status = (current_time - self.last_status_time).total_seconds()
                        if time_since_last_status >= 60:  # Show status every minute
                            print(f"🔍 Discord: Monitoring... (no new tokens)")
                            self.last_status_time = current_time
                else:
                    print(f"⚠️ Discord: Connection issue, retrying...")
                
                # Wait for next check
                await asyncio.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            print(f"\n🔍 Discord: Stopping monitoring...")
        except Exception as e:
            logger.error(f"Discord monitoring error: {e}")
        finally:
            self.running = False
            print(f"🔍 Discord: Monitoring stopped")
    
    def stop_monitoring(self):
        """Stop Discord monitoring"""
        self.running = False
