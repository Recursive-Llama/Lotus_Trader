"""
Unified Social Media Monitor

Combines Twitter and Telegram monitoring into a single system.
Handles both platforms and links curators who have both.
"""

import logging
import asyncio
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import yaml

from twitter_scanner import TwitterScanner
from telegram_scanner import TelegramScanner
from social_ingest_basic import SocialIngestModule

logger = logging.getLogger(__name__)


class UnifiedSocialMonitor:
    """
    Unified Social Media Monitor
    
    This module:
    - Monitors both Twitter and Telegram curators
    - Links curators who have both platforms
    - Processes social signals through the same pipeline
    - Manages curator performance across platforms
    """
    
    def __init__(self, supabase_manager, llm_client, config_path: str = None):
        """
        Initialize Unified Social Monitor
        
        Args:
            supabase_manager: Database manager for strand creation
            llm_client: LLM client for information extraction
            config_path: Path to curator configuration file
        """
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
        
        # Load curator configuration
        if config_path and os.path.exists(config_path):
            self.curators_config = self._load_curators_config(config_path)
        else:
            # Default to src/config/twitter_curators.yaml
            default_config_path = "src/config/twitter_curators.yaml"
            if os.path.exists(default_config_path):
                self.curators_config = self._load_curators_config(default_config_path)
            else:
                self.curators_config = self._get_default_curators_config()
        
        # Initialize platform scanners
        self.twitter_scanner = TwitterScanner(llm_client, config_path)
        self.telegram_scanner = TelegramScanner(llm_client, config_path)
        
        # Initialize social ingest module
        self.social_ingest = SocialIngestModule(supabase_manager, llm_client, config_path)
        
        # Build unified curator mapping
        self.unified_curators = self._build_unified_curator_mapping()
        
        self.logger.info(f"Unified Social Monitor initialized with {len(self.unified_curators)} curators")
    
    def _load_curators_config(self, config_path: str) -> Dict[str, Any]:
        """Load curator configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Failed to load curators config: {e}")
            return self._get_default_curators_config()
    
    def _get_default_curators_config(self) -> Dict[str, Any]:
        """Get default curator configuration"""
        return {
            'curators': [
                {
                    'id': '0xdetweiler',
                    'name': '0xDetweiler',
                    'platforms': {
                        'twitter': {
                            'handle': '@0xdetweiler',
                            'active': True,
                            'weight': 0.8,
                            'priority': 'high'
                        }
                    },
                    'tags': ['defi', 'alpha', 'technical'],
                    'enabled': True
                }
            ]
        }
    
    def _build_unified_curator_mapping(self) -> Dict[str, Dict[str, Any]]:
        """Build unified curator mapping that links platforms"""
        unified_curators = {}
        
        for curator in self.curators_config['curators']:
            if not curator.get('enabled', True):
                continue
            
            curator_id = curator['id']
            platforms = curator.get('platforms', {})
            
            # Create unified curator entry
            unified_curator = {
                'id': curator_id,
                'name': curator.get('name', 'Unknown'),
                'tags': curator.get('tags', []),
                'notes': curator.get('notes', ''),
                'platforms': {},
                'active_platforms': [],
                'total_weight': 0.0,
                'max_priority': 'low'
            }
            
            # Process each platform
            for platform, platform_data in platforms.items():
                if platform_data.get('active', True):
                    unified_curator['platforms'][platform] = platform_data
                    unified_curator['active_platforms'].append(platform)
                    unified_curator['total_weight'] += platform_data.get('weight', 0.0)
                    
                    # Track highest priority
                    priority = platform_data.get('priority', 'low')
                    if priority == 'high':
                        unified_curator['max_priority'] = 'high'
                    elif priority == 'medium' and unified_curator['max_priority'] != 'high':
                        unified_curator['max_priority'] = 'medium'
            
            # Calculate average weight
            if unified_curator['active_platforms']:
                unified_curator['avg_weight'] = unified_curator['total_weight'] / len(unified_curator['active_platforms'])
            else:
                unified_curator['avg_weight'] = 0.0
            
            unified_curators[curator_id] = unified_curator
        
        return unified_curators
    
    async def start_monitoring(self, twitter_interval: int = 30, telegram_interval: int = 60):
        """
        Start monitoring both Twitter and Telegram
        
        Args:
            twitter_interval: Seconds between Twitter checks
            telegram_interval: Seconds between Telegram checks
        """
        self.logger.info("🚀 Starting Unified Social Media Monitoring...")
        
        # Create tasks for both platforms
        twitter_task = asyncio.create_task(
            self._monitor_twitter(twitter_interval)
        )
        telegram_task = asyncio.create_task(
            self._monitor_telegram(telegram_interval)
        )
        
        try:
            # Run both monitoring tasks concurrently
            await asyncio.gather(twitter_task, telegram_task)
        except KeyboardInterrupt:
            self.logger.info("🛑 Unified monitoring stopped by user")
        except Exception as e:
            self.logger.error(f"❌ Error in unified monitoring: {e}")
        finally:
            # Cancel tasks
            twitter_task.cancel()
            telegram_task.cancel()
    
    async def _monitor_twitter(self, interval: int):
        """Monitor Twitter curators"""
        try:
            while True:
                self.logger.info("🐦 Checking Twitter curators...")
                await self.twitter_scanner._check_all_curators()
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            self.logger.info("Twitter monitoring cancelled")
        except Exception as e:
            self.logger.error(f"Error in Twitter monitoring: {e}")
    
    async def _monitor_telegram(self, interval: int):
        """Monitor Telegram curators"""
        try:
            while True:
                self.logger.info("📱 Checking Telegram curators...")
                await self.telegram_scanner._check_all_curators()
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            self.logger.info("Telegram monitoring cancelled")
        except Exception as e:
            self.logger.error(f"Error in Telegram monitoring: {e}")
    
    def get_curator_summary(self) -> Dict[str, Any]:
        """Get summary of all curators and their platforms"""
        summary = {
            'total_curators': len(self.unified_curators),
            'platform_breakdown': {
                'twitter_only': 0,
                'telegram_only': 0,
                'multi_platform': 0
            },
            'curators': []
        }
        
        for curator_id, curator in self.unified_curators.items():
            platforms = curator['active_platforms']
            
            if 'twitter' in platforms and 'telegram' in platforms:
                summary['platform_breakdown']['multi_platform'] += 1
            elif 'twitter' in platforms:
                summary['platform_breakdown']['twitter_only'] += 1
            elif 'telegram' in platforms:
                summary['platform_breakdown']['telegram_only'] += 1
            
            summary['curators'].append({
                'id': curator_id,
                'name': curator['name'],
                'platforms': platforms,
                'avg_weight': curator['avg_weight'],
                'priority': curator['max_priority'],
                'tags': curator['tags']
            })
        
        return summary
    
    def get_curator_by_platform(self, platform: str) -> List[Dict[str, Any]]:
        """Get curators that have a specific platform"""
        curators = []
        
        for curator_id, curator in self.unified_curators.items():
            if platform in curator['active_platforms']:
                curators.append({
                    'id': curator_id,
                    'name': curator['name'],
                    'platform_data': curator['platforms'][platform],
                    'all_platforms': curator['active_platforms']
                })
        
        return curators
    
    def get_linked_curators(self) -> List[Dict[str, Any]]:
        """Get curators that have both Twitter and Telegram"""
        linked_curators = []
        
        for curator_id, curator in self.unified_curators.items():
            if 'twitter' in curator['active_platforms'] and 'telegram' in curator['active_platforms']:
                linked_curators.append({
                    'id': curator_id,
                    'name': curator['name'],
                    'twitter': curator['platforms']['twitter'],
                    'telegram': curator['platforms']['telegram'],
                    'total_weight': curator['total_weight'],
                    'avg_weight': curator['avg_weight']
                })
        
        return linked_curators


async def main():
    """Test the unified social monitor"""
    from test_token_detection import MockLLMClient
    
    # Mock clients for testing
    llm_client = MockLLMClient()
    supabase_manager = None  # Mock for testing
    
    # Initialize monitor
    monitor = UnifiedSocialMonitor(supabase_manager, llm_client)
    
    # Show curator summary
    summary = monitor.get_curator_summary()
    print("📊 Curator Summary:")
    print(f"  Total curators: {summary['total_curators']}")
    print(f"  Twitter only: {summary['platform_breakdown']['twitter_only']}")
    print(f"  Telegram only: {summary['platform_breakdown']['telegram_only']}")
    print(f"  Multi-platform: {summary['platform_breakdown']['multi_platform']}")
    
    print("\n🔗 Linked Curators (Twitter + Telegram):")
    linked = monitor.get_linked_curators()
    for curator in linked:
        print(f"  - {curator['name']} (@{curator['twitter']['handle']} + @{curator['telegram']['handle']})")
    
    print("\n🐦 Twitter Curators:")
    twitter_curators = monitor.get_curator_by_platform('twitter')
    for curator in twitter_curators:
        print(f"  - {curator['name']} (@{curator['platform_data']['handle']})")
    
    print("\n📱 Telegram Curators:")
    telegram_curators = monitor.get_curator_by_platform('telegram')
    for curator in telegram_curators:
        print(f"  - {curator['name']} (@{curator['platform_data']['handle']})")


if __name__ == "__main__":
    asyncio.run(main())

