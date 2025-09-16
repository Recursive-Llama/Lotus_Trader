"""
Curator Registry System

Automatically registers curators in the database when first detected.
Manages curator performance tracking and multi-platform support.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import json

logger = logging.getLogger(__name__)


class CuratorRegistry:
    """
    Curator Registry System
    
    Handles:
    - Automatic curator registration when first detected
    - Multi-platform curator management
    - Performance tracking and weight calculation
    - Database integration for curator data
    """
    
    def __init__(self, supabase_manager, config_path: str = None):
        """
        Initialize Curator Registry
        
        Args:
            supabase_manager: Database manager for curator operations
            config_path: Path to curator configuration file
        """
        self.supabase_manager = supabase_manager
        self.config_path = config_path or "src/config/twitter_curators.yaml"
        self.logger = logging.getLogger(__name__)
        
        # Load curator configuration
        self.curators_config = self._load_curators_config()
        
        # Cache for registered curators (to avoid repeated DB calls)
        self.registered_curators = {}
        self.curator_platforms = {}
        
        self.logger.info("Curator Registry initialized")
    
    def _load_curators_config(self) -> Dict[str, Any]:
        """Load curator configuration from YAML file"""
        try:
            import yaml
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Failed to load curators config: {e}")
            return {'curators': []}
    
    async def register_curator_from_config(self, curator_data: Dict[str, Any]) -> str:
        """
        Register a curator from configuration data
        
        Args:
            curator_data: Curator data from YAML config
            
        Returns:
            curator_id: Registered curator ID
        """
        try:
            curator_id = curator_data['id']
            name = curator_data['name']
            platforms = curator_data.get('platforms', {})
            
            # Register curator in database
            await self._register_curator_in_db(curator_id, name, curator_data)
            
            # Register each platform
            for platform, platform_data in platforms.items():
                if platform_data.get('active', True):
                    await self._register_curator_platform(
                        curator_id=curator_id,
                        platform=platform,
                        handle=platform_data['handle'],
                        platform_id=platform_data.get('channel_id'),
                        weight=platform_data.get('weight', 0.5),
                        priority=platform_data.get('priority', 'medium')
                    )
            
            self.logger.info(f"Registered curator {curator_id} with {len(platforms)} platforms")
            return curator_id
            
        except Exception as e:
            self.logger.error(f"Error registering curator from config: {e}")
            return None
    
    async def register_curator_from_signal(self, platform: str, handle: str, 
                                         platform_id: str = None, 
                                         signal_content: str = None) -> Optional[str]:
        """
        Register a new curator when first detected from a signal
        
        Args:
            platform: Platform name ("twitter", "telegram")
            handle: Platform handle ("@0xdetweiler")
            platform_id: Platform-specific ID (channel_id, user_id)
            signal_content: Content of the signal for analysis
            
        Returns:
            curator_id: Registered curator ID or None if failed
        """
        try:
            # Generate curator ID from handle
            curator_id = self._generate_curator_id(handle)
            
            # Check if already registered
            if await self._is_curator_registered(curator_id):
                return curator_id
            
            # Extract name from handle
            name = self._extract_name_from_handle(handle)
            
            # Register curator in database
            await self._register_curator_in_db(
                curator_id=curator_id,
                name=name,
                metadata={
                    'discovered_from': platform,
                    'discovery_signal': signal_content,
                    'auto_registered': True
                }
            )
            
            # Register platform
            await self._register_curator_platform(
                curator_id=curator_id,
                platform=platform,
                handle=handle,
                platform_id=platform_id,
                weight=0.5,  # Default weight for new curators
                priority='medium'
            )
            
            self.logger.info(f"Auto-registered new curator {curator_id} from {platform}:{handle}")
            return curator_id
            
        except Exception as e:
            self.logger.error(f"Error auto-registering curator: {e}")
            return None
    
    async def _register_curator_in_db(self, curator_id: str, name: str, 
                                    metadata: Dict[str, Any] = None) -> bool:
        """Register curator in database"""
        try:
            # Use the register_curator function from the database
            result = await self.supabase_manager.rpc(
                'register_curator',
                {
                    'curator_id_param': curator_id,
                    'name_param': name,
                    'platform_param': 'unknown',  # Will be updated by platform registration
                    'handle_param': 'unknown',
                    'tier_param': metadata.get('tier', 'standard') if metadata else 'standard'
                }
            )
            
            # Cache the curator
            self.registered_curators[curator_id] = {
                'id': curator_id,
                'name': name,
                'registered_at': datetime.now(timezone.utc).isoformat()
            }
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error registering curator in DB: {e}")
            return False
    
    async def _register_curator_platform(self, curator_id: str, platform: str, 
                                       handle: str, platform_id: str = None,
                                       weight: float = 0.5, priority: str = 'medium') -> bool:
        """Register curator platform in database"""
        try:
            # Insert into curator_platforms table
            result = await self.supabase_manager.table('curator_platforms').insert({
                'curator_id': curator_id,
                'platform': platform,
                'handle': handle,
                'platform_id': platform_id,
                'weight': weight,
                'priority': priority,
                'is_active': True,
                'is_primary': False  # Will be updated if this is the only platform
            }).execute()
            
            # Cache the platform
            if curator_id not in self.curator_platforms:
                self.curator_platforms[curator_id] = {}
            
            self.curator_platforms[curator_id][platform] = {
                'handle': handle,
                'platform_id': platform_id,
                'weight': weight,
                'priority': priority
            }
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error registering curator platform: {e}")
            return False
    
    async def _is_curator_registered(self, curator_id: str) -> bool:
        """Check if curator is already registered"""
        try:
            result = await self.supabase_manager.table('curators').select('curator_id').eq('curator_id', curator_id).execute()
            return len(result.data) > 0
        except Exception as e:
            self.logger.error(f"Error checking curator registration: {e}")
            return False
    
    def _generate_curator_id(self, handle: str) -> str:
        """Generate curator ID from handle"""
        # Remove @ symbol and convert to lowercase
        clean_handle = handle.replace('@', '').lower()
        return clean_handle
    
    def _extract_name_from_handle(self, handle: str) -> str:
        """Extract display name from handle"""
        # Remove @ symbol and capitalize
        clean_handle = handle.replace('@', '')
        return clean_handle.replace('_', ' ').title()
    
    async def get_curator_info(self, curator_id: str) -> Optional[Dict[str, Any]]:
        """Get curator information from database"""
        try:
            result = await self.supabase_manager.table('curators').select('*').eq('curator_id', curator_id).execute()
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            self.logger.error(f"Error getting curator info: {e}")
            return None
    
    async def get_curator_platforms(self, curator_id: str) -> List[Dict[str, Any]]:
        """Get all platforms for a curator"""
        try:
            result = await self.supabase_manager.table('curator_platforms').select('*').eq('curator_id', curator_id).execute()
            return result.data
        except Exception as e:
            self.logger.error(f"Error getting curator platforms: {e}")
            return []
    
    async def update_curator_performance(self, curator_id: str) -> bool:
        """Update curator performance metrics"""
        try:
            result = await self.supabase_manager.rpc('update_curator_performance', {
                'curator_id_param': curator_id
            })
            return True
        except Exception as e:
            self.logger.error(f"Error updating curator performance: {e}")
            return False
    
    async def record_curator_signal(self, curator_id: str, platform: str, 
                                  handle: str, signal_data: Dict[str, Any]) -> Optional[str]:
        """
        Record a signal from a curator
        
        Args:
            curator_id: Curator ID
            platform: Platform name
            handle: Platform handle
            signal_data: Signal data including content, tokens, etc.
            
        Returns:
            signal_id: Created signal ID
        """
        try:
            signal_id = f"{curator_id}_{platform}_{int(datetime.now().timestamp())}"
            
            # Extract primary token info if available
            primary_token = signal_data.get('primary_token', {})
            if not primary_token and signal_data.get('tokens'):
                # Use first token as primary if no primary specified
                tokens = signal_data.get('tokens', [])
                if tokens:
                    primary_token = tokens[0]
            
            signal_record = {
                'curator_id': curator_id,
                'platform': platform,
                'handle': handle,
                'signal_id': signal_id,
                'message_id': signal_data.get('message_id'),
                'message_url': signal_data.get('url'),
                'content': signal_data.get('text', ''),
                'extracted_tokens': json.dumps(signal_data.get('tokens', [])),
                'sentiment': signal_data.get('sentiment'),
                'confidence': signal_data.get('confidence', 0.5),
                'primary_token_chain': primary_token.get('chain'),
                'primary_token_contract': primary_token.get('contract'),
                'primary_token_ticker': primary_token.get('ticker'),
                'primary_token_name': primary_token.get('name'),
                'signal_type': signal_data.get('type', 'call'),
                'urgency': signal_data.get('urgency', 'medium'),
                'tags': signal_data.get('tags', [])
            }
            
            result = await self.supabase_manager.table('curator_signals').insert(signal_record).execute()
            
            # Update curator last seen
            await self.supabase_manager.table('curators').update({
                'last_seen_at': datetime.now(timezone.utc).isoformat(),
                'last_signal_at': datetime.now(timezone.utc).isoformat()
            }).eq('curator_id', curator_id).execute()
            
            self.logger.info(f"Recorded signal {signal_id} from {curator_id}")
            return signal_id
            
        except Exception as e:
            self.logger.error(f"Error recording curator signal: {e}")
            return None
    
    async def update_signal_outcome(self, signal_id: str, outcome: str, 
                                  pnl_pct: float = None, pnl_usd: float = None) -> bool:
        """Update signal outcome after position is closed"""
        try:
            update_data = {
                'signal_outcome': outcome,
                'outcome_updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            if pnl_pct is not None:
                update_data['signal_pnl_pct'] = pnl_pct
            if pnl_usd is not None:
                update_data['signal_pnl_usd'] = pnl_usd
            
            result = await self.supabase_manager.table('curator_signals').update(update_data).eq('signal_id', signal_id).execute()
            
            # Update curator performance
            signal_data = await self.supabase_manager.table('curator_signals').select('curator_id').eq('signal_id', signal_id).execute()
            if signal_data.data:
                curator_id = signal_data.data[0]['curator_id']
                await self.update_curator_performance(curator_id)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating signal outcome: {e}")
            return False
    
    async def get_top_curators(self, limit: int = 10, platform: str = None) -> List[Dict[str, Any]]:
        """Get top performing curators"""
        try:
            query = self.supabase_manager.table('curator_performance_summary').select('*').order('win_rate', desc=True).limit(limit)
            
            if platform:
                # Join with curator_platforms to filter by platform
                query = query.eq('platform', platform)
            
            result = await query.execute()
            return result.data
            
        except Exception as e:
            self.logger.error(f"Error getting top curators: {e}")
            return []
    
    async def initialize_from_config(self) -> bool:
        """Initialize curator registry from configuration file"""
        try:
            self.logger.info("Initializing curator registry from configuration...")
            
            for curator_data in self.curators_config.get('curators', []):
                if curator_data.get('enabled', True):
                    await self.register_curator_from_config(curator_data)
            
            self.logger.info(f"Initialized {len(self.curators_config.get('curators', []))} curators from config")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing curator registry: {e}")
            return False


# Example usage and testing
async def main():
    """Test the curator registry system"""
    # Mock supabase manager for testing
    class MockSupabaseManager:
        async def rpc(self, function_name, params):
            print(f"RPC call: {function_name} with params: {params}")
            return {'data': [{'curator_id': params.get('curator_id_param')}]}
        
        async def table(self, table_name):
            class MockTable:
                def __init__(self, table_name):
                    self.table_name = table_name
                
                def select(self, columns):
                    return self
                
                def insert(self, data):
                    return self
                
                def update(self, data):
                    return self
                
                def eq(self, column, value):
                    return self
                
                def order(self, column, desc=False):
                    return self
                
                def limit(self, count):
                    return self
                
                async def execute(self):
                    return {'data': []}
            
            return MockTable(table_name)
    
    # Test the registry
    registry = CuratorRegistry(MockSupabaseManager())
    
    # Test auto-registration
    curator_id = await registry.register_curator_from_signal(
        platform="twitter",
        handle="@testcurator",
        signal_content="Check out this new token $TEST"
    )
    
    print(f"Registered curator: {curator_id}")


if __name__ == "__main__":
    asyncio.run(main())
