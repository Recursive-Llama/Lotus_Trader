"""
Curator Integration Example

Shows how to integrate the curator registry with the social monitoring system.
This replaces the static YAML-based curator management with dynamic database tracking.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from curator_registry import CuratorRegistry
from social_ingest_basic import SocialIngestModule

logger = logging.getLogger(__name__)


class CuratorIntegratedSocialIngest(SocialIngestModule):
    """
    Enhanced Social Ingest Module with Curator Registry Integration
    
    Features:
    - Automatic curator registration when first detected
    - Dynamic curator performance tracking
    - Multi-platform curator support
    - Real-time weight adjustment based on performance
    """
    
    def __init__(self, supabase_manager, llm_client, config_path: str = None):
        """Initialize with curator registry integration"""
        super().__init__(supabase_manager, llm_client, config_path)
        
        # Initialize curator registry
        self.curator_registry = CuratorRegistry(supabase_manager, config_path)
        
        # Initialize curators from config
        asyncio.create_task(self.curator_registry.initialize_from_config())
        
        self.logger.info("Curator-integrated social ingest module initialized")
    
    async def process_social_signal(self, platform: str, handle: str, 
                                  message_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process social signal with curator registry integration
        
        Args:
            platform: Platform name ("twitter", "telegram")
            handle: Platform handle ("@0xdetweiler")
            message_data: Message data including content, tokens, etc.
            
        Returns:
            Processed signal data or None
        """
        try:
            # Generate curator ID from handle
            curator_id = self.curator_registry._generate_curator_id(handle)
            
            # Check if curator is registered, auto-register if not
            if not await self.curator_registry._is_curator_registered(curator_id):
                self.logger.info(f"Auto-registering new curator: {curator_id}")
                await self.curator_registry.register_curator_from_signal(
                    platform=platform,
                    handle=handle,
                    platform_id=message_data.get('platform_id'),
                    signal_content=message_data.get('text', '')
                )
            
            # Get curator info
            curator_info = await self.curator_registry.get_curator_info(curator_id)
            if not curator_info:
                self.logger.warning(f"Could not get curator info for {curator_id}")
                return None
            
            # Record the signal
            signal_id = await self.curator_registry.record_curator_signal(
                curator_id=curator_id,
                platform=platform,
                handle=handle,
                signal_data=message_data
            )
            
            if not signal_id:
                self.logger.warning(f"Failed to record signal from {curator_id}")
                return None
            
            # Process the signal (extract tokens, etc.)
            processed_signal = await self._process_signal_content(message_data)
            if not processed_signal:
                return None
            
            # Add curator metadata to processed signal
            processed_signal.update({
                'curator_id': curator_id,
                'curator_name': curator_info.get('name'),
                'curator_tier': curator_info.get('tier'),
                'curator_weight': curator_info.get('final_weight', 0.5),
                'signal_id': signal_id,
                'platform': platform,
                'handle': handle
            })
            
            # Update curator performance
            await self.curator_registry.update_curator_performance(curator_id)
            
            self.logger.info(f"Processed signal {signal_id} from {curator_id} (weight: {curator_info.get('final_weight', 0.5)})")
            return processed_signal
            
        except Exception as e:
            self.logger.error(f"Error processing social signal: {e}")
            return None
    
    async def _process_signal_content(self, message_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process signal content to extract tokens and metadata"""
        try:
            content = message_data.get('text', '')
            
            # Use LLM to extract token information
            if self.llm_client:
                # This would call your existing LLM integration
                # For now, return mock data
                return {
                    'tokens': [
                        {
                            'ticker': 'TEST',
                            'chain': 'solana',
                            'contract': 'mock_contract_address',
                            'confidence': 0.8
                        }
                    ],
                    'sentiment': 'bullish',
                    'confidence': 0.7,
                    'type': 'call',
                    'urgency': 'medium',
                    'tags': ['alpha', 'new']
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error processing signal content: {e}")
            return None
    
    async def get_curator_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for all curators"""
        try:
            # Get top curators
            top_curators = await self.curator_registry.get_top_curators(limit=10)
            
            # Get performance summary
            result = await self.supabase_manager.table('curator_performance_summary').select('*').execute()
            
            return {
                'top_curators': top_curators,
                'performance_summary': result.data,
                'total_curators': len(result.data) if result.data else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error getting curator performance summary: {e}")
            return {'top_curators': [], 'performance_summary': [], 'total_curators': 0}
    
    async def update_curator_weights(self) -> bool:
        """Update all curator weights based on performance"""
        try:
            # Get all active curators
            result = await self.supabase_manager.table('curators').select('curator_id').eq('status', 'active').execute()
            
            if not result.data:
                return True
            
            # Update performance for each curator
            for curator in result.data:
                curator_id = curator['curator_id']
                await self.curator_registry.update_curator_performance(curator_id)
            
            self.logger.info(f"Updated weights for {len(result.data)} curators")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating curator weights: {e}")
            return False


# Example usage
async def main():
    """Example of how to use the curator-integrated social ingest"""
    
    # Mock dependencies
    class MockSupabaseManager:
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
    
    class MockLLMClient:
        pass
    
    # Initialize the integrated system
    social_ingest = CuratorIntegratedSocialIngest(
        supabase_manager=MockSupabaseManager(),
        llm_client=MockLLMClient(),
        config_path="src/config/twitter_curators.yaml"
    )
    
    # Process a sample signal
    sample_signal = {
        'text': 'Check out this new token $TEST on Solana!',
        'url': 'https://twitter.com/test/status/123',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'platform_id': '1234567890'
    }
    
    result = await social_ingest.process_social_signal(
        platform='twitter',
        handle='@testcurator',
        message_data=sample_signal
    )
    
    print(f"Processed signal: {result}")
    
    # Get performance summary
    summary = await social_ingest.get_curator_performance_summary()
    print(f"Performance summary: {summary}")


if __name__ == "__main__":
    asyncio.run(main())
