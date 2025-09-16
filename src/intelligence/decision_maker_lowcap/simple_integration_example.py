"""
Simple Integration Example

Shows how to integrate the simplified Decision Maker Lowcap with social monitoring.
"""

import asyncio
import logging
from typing import Dict, Any

# Import the simplified components
from decision_maker_lowcap_simple import DecisionMakerLowcapSimple
from src.intelligence.social_ingest.social_ingest_basic import SocialIngestModule

logger = logging.getLogger(__name__)


class SimpleSocialTradingSystem:
    """
    Simple Social Trading System
    
    Integrates social monitoring with simplified decision making.
    """
    
    def __init__(self, supabase_manager, llm_client, config: Dict[str, Any] = None):
        """
        Initialize Simple Social Trading System
        
        Args:
            supabase_manager: Database manager
            llm_client: LLM client for token extraction
            config: Configuration dictionary
        """
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.config = config or {}
        
        # Initialize components
        self.social_ingest = SocialIngestModule(
            supabase_manager=supabase_manager,
            llm_client=llm_client,
            config_path="src/config/twitter_curators.yaml"
        )
        
        self.decision_maker = DecisionMakerLowcapSimple(
            supabase_manager=supabase_manager,
            config=self.config.get('decision_maker', {})
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("Simple Social Trading System initialized")
    
    async def process_social_signal(self, platform: str, handle: str, message_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a social signal through the complete pipeline
        
        Args:
            platform: Platform name ("twitter", "telegram")
            handle: Platform handle ("@0xdetweiler")
            message_data: Message data including content, tokens, etc.
            
        Returns:
            Decision result or None
        """
        try:
            self.logger.info(f"Processing signal from {platform}:{handle}")
            
            # Step 1: Process social signal (extract tokens, verify with DexScreener)
            social_signal = await self.social_ingest.process_social_signal(
                curator_id=self._get_curator_id_from_handle(handle),
                message_data=message_data
            )
            
            if not social_signal:
                self.logger.info(f"No valid signal extracted from {handle}")
                return None
            
            # Step 2: Make decision using simplified 4-step process
            decision = self.decision_maker.make_decision(social_signal)
            
            if decision:
                self.logger.info(f"Decision made: {decision['content']['action']} - {decision['content']['reasoning']}")
                
                # Step 3: If approved, create position record (optional)
                if decision['content']['action'] == 'approve':
                    await self._create_position_record(decision)
            
            return decision
            
        except Exception as e:
            self.logger.error(f"Error processing social signal: {e}")
            return None
    
    def _get_curator_id_from_handle(self, handle: str) -> str:
        """Convert handle to curator ID"""
        return handle.replace('@', '').lower()
    
    async def _create_position_record(self, decision: Dict[str, Any]) -> bool:
        """
        Create position record for approved decisions
        
        Args:
            decision: Approved decision strand
            
        Returns:
            True if position record created successfully
        """
        try:
            content = decision['content']
            token_data = content['token']
            
            # Generate position ID
            position_id = f"pos_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{token_data['ticker']}"
            
            # Create position record
            position = {
                'id': position_id,
                'curator_id': content['curator_id'],
                'social_signal_id': content.get('source_strand_id'),
                'decision_strand_id': decision.get('id'),
                'token_chain': token_data['chain'],
                'token_contract': token_data['contract'],
                'token_ticker': token_data['ticker'],
                'token_name': token_data.get('name'),
                'allocation_pct': content['allocation_pct'],
                'allocation_usd': content['allocation_usd'],
                'entry_venue': content['venue']['dex'],
                'status': 'pending',  # Will be updated when actually executed
                'book_id': 'social',
                'curator_performance_at_entry': content['curator_confidence'],
                'notes': f"Created from {content['source_kind']} signal"
            }
            
            # Insert into database
            result = self.supabase_manager.table('lowcap_positions').insert(position).execute()
            
            if result.data:
                self.logger.info(f"Created position record: {position_id}")
                return True
            else:
                self.logger.error(f"Failed to create position record: {position_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error creating position record: {e}")
            return False
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get system status and portfolio summary"""
        try:
            portfolio_summary = self.decision_maker.get_portfolio_summary()
            
            return {
                "system": "Simple Social Trading System",
                "status": "running",
                "portfolio": portfolio_summary,
                "config": self.config
            }
            
        except Exception as e:
            self.logger.error(f"Error getting system status: {e}")
            return {"error": str(e)}


# Example usage and testing
async def main():
    """Example of how to use the simple social trading system"""
    
    # Mock dependencies
    class MockSupabaseManager:
        def rpc(self, function_name, params):
            print(f"RPC call: {function_name} with params: {params}")
            if function_name == 'get_portfolio_summary':
                return {'data': [{'total_positions': 0, 'active_positions': 0, 'current_exposure_pct': 0.0, 'total_pnl_usd': 0.0, 'avg_pnl_pct': 0.0}]}
            return {'data': []}
        
        def table(self, table_name):
            class MockTable:
                def select(self, columns):
                    return self
                def eq(self, column, value):
                    return self
                def insert(self, data):
                    return self
                def execute(self):
                    return {'data': [{'id': 'test_123'}]}
            return MockTable()
        
        def create_strand(self, strand):
            print(f"Created strand: {strand['kind']} - {strand['content']['action']}")
            return strand
    
    class MockLLMClient:
        pass
    
    # Initialize system
    config = {
        'decision_maker': {
            'book_id': 'social',
            'book_nav': 100000.0,
            'min_curator_score': 0.6,
            'max_exposure_pct': 20.0
        }
    }
    
    system = SimpleSocialTradingSystem(
        supabase_manager=MockSupabaseManager(),
        llm_client=MockLLMClient(),
        config=config
    )
    
    # Test with sample signal
    sample_signal = {
        'text': 'Check out this new token $PEPE on Solana!',
        'url': 'https://twitter.com/test/status/123',
        'timestamp': '2024-12-15T10:30:00Z',
        'platform_id': '1234567890'
    }
    
    # Process signal
    result = await system.process_social_signal(
        platform='twitter',
        handle='@0xdetweiler',
        message_data=sample_signal
    )
    
    print(f"Processing result: {result}")
    
    # Get system status
    status = system.get_system_status()
    print(f"System status: {status}")


if __name__ == "__main__":
    asyncio.run(main())
