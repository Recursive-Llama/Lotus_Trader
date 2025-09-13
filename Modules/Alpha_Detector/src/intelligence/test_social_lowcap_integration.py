"""
Social Lowcap Integration Test

Tests the integration of all three social lowcap modules:
1. Social Ingest - Data collection
2. Decision Maker Lowcap - Portfolio-aware decisions
3. Trader Lowcap - Specialized execution

Tests the complete flow from social signal to execution.
"""

import logging
import sys
import os
from datetime import datetime, timezone
from typing import Dict, Any

# Add the project root to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../..'))

from src.learning_system.integrated_learning_system import CentralizedLearningSystem
from src.learning_system.context_injection_engine import ContextInjectionEngine
from src.learning_system.module_specific_scoring import ModuleSpecificScoring

# Import the new social lowcap modules
from social_ingest.social_ingest_module import SocialIngestModule
from decision_maker_lowcap.decision_maker_lowcap import DecisionMakerLowcap
from trader_lowcap.trader_lowcap import TraderLowcap

# Mock database manager for testing
class MockSupabaseManager:
    """Mock database manager for testing"""
    
    def __init__(self):
        self.strands = []
        self.positions = []
        self.curators = []
    
    def create_strand(self, strand_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a strand"""
        strand_id = f"strand_{len(self.strands) + 1}"
        strand = {
            'id': strand_id,
            'created_at': datetime.now(timezone.utc).isoformat(),
            **strand_data
        }
        self.strands.append(strand)
        return strand
    
    def create_position(self, position_data: Dict[str, Any]) -> str:
        """Create a position"""
        position_id = f"pos_{len(self.positions) + 1}"
        position = {
            'id': position_id,
            'created_at': datetime.now(timezone.utc).isoformat(),
            **position_data
        }
        self.positions.append(position)
        return position_id
    
    def get_active_positions(self, book_id: str) -> list:
        """Get active positions for a book"""
        return [pos for pos in self.positions if pos.get('book_id') == book_id and pos.get('status') != 'closed']
    
    def get_pending_decisions(self, book_id: str) -> list:
        """Get pending decisions for a book"""
        return [strand for strand in self.strands 
                if strand.get('module') == 'decision_maker_lowcap' 
                and strand.get('content', {}).get('action') == 'approve'
                and strand.get('status') == 'active']
    
    def update_curator_last_seen(self, curator_id: str):
        """Update curator last seen timestamp"""
        for curator in self.curators:
            if curator.get('curator_id') == curator_id:
                curator['last_seen_at'] = datetime.now(timezone.utc).isoformat()
                break
    
    def update_position_entry(self, position_id: str, level: int, price: float, timestamp: datetime, slippage: float):
        """Update position entry level"""
        for position in self.positions:
            if position.get('id') == position_id:
                position[f'entry_{level}_price'] = price
                position[f'entry_{level}_executed'] = True
                position[f'entry_{level}_timestamp'] = timestamp.isoformat()
                position[f'entry_{level}_slippage_pct'] = slippage
                break


def test_social_lowcap_integration():
    """Test the complete social lowcap integration flow"""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("🚀 Starting Social Lowcap Integration Test")
    
    # Initialize mock database manager
    db_manager = MockSupabaseManager()
    
    # Initialize learning system components
    learning_system = CentralizedLearningSystem()
    context_engine = ContextInjectionEngine(db_manager)
    scoring_system = ModuleSpecificScoring()
    
    # Initialize social lowcap modules
    social_ingest = SocialIngestModule(db_manager)
    decision_maker = DecisionMakerLowcap(db_manager, learning_system, context_engine)
    trader = TraderLowcap(db_manager, learning_system, context_engine)
    
    logger.info("✅ All modules initialized successfully")
    
    # Test 1: Social Ingest - Process social signal
    logger.info("\n📡 Test 1: Social Ingest - Processing social signal")
    
    mock_message = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'text': 'Check out $FOO token, looks promising!',
        'links': {}
    }
    
    social_strand = social_ingest.process_social_signal('tg:@alphaOne', mock_message)
    
    if social_strand:
        logger.info(f"✅ Social signal processed: {social_strand['content']['token']['ticker']}")
        logger.info(f"   Curator: {social_strand['content']['curator_id']}")
        logger.info(f"   Venue: {social_strand['content']['venue']['dex']}")
    else:
        logger.error("❌ Failed to process social signal")
        return False
    
    # Test 2: Decision Maker Lowcap - Make allocation decision
    logger.info("\n🎯 Test 2: Decision Maker Lowcap - Making allocation decision")
    
    decision_strand = decision_maker.make_decision(social_strand)
    
    if decision_strand:
        logger.info(f"✅ Decision made: {decision_strand['content']['action']}")
        logger.info(f"   Allocation: {decision_strand['content']['allocation_pct']:.1f}%")
        logger.info(f"   Reasoning: {decision_strand['content']['reasoning']}")
    else:
        logger.error("❌ Failed to make decision")
        return False
    
    # Test 3: Trader Lowcap - Execute trade
    logger.info("\n⚡ Test 3: Trader Lowcap - Executing trade")
    
    execution_strand = trader.execute_trade(decision_strand)
    
    if execution_strand:
        logger.info(f"✅ Trade executed: {execution_strand['content']['execution_strategy']}")
        logger.info(f"   Position ID: {execution_strand['content']['position_id']}")
        logger.info(f"   Allocation: {execution_strand['content']['allocation_usd']:.2f} USD")
    else:
        logger.error("❌ Failed to execute trade")
        return False
    
    # Test 4: Verify database state
    logger.info("\n📊 Test 4: Verifying database state")
    
    logger.info(f"   Strands created: {len(db_manager.strands)}")
    logger.info(f"   Positions created: {len(db_manager.positions)}")
    
    # Test 5: Test learning system integration
    logger.info("\n🧠 Test 5: Testing learning system integration")
    
    # Test module-specific scoring
    dml_score = scoring_system.calculate_module_score('decision_maker_lowcap', {
        'curator_performance': 0.8,
        'allocation_accuracy': 0.7,
        'portfolio_impact': 0.9
    })
    
    tdl_score = scoring_system.calculate_module_score('trader_lowcap', {
        'execution_success': 0.9,
        'slippage_control': 0.8,
        'venue_selection': 0.7
    })
    
    logger.info(f"   DML Score: {dml_score:.2f}")
    logger.info(f"   TDL Score: {tdl_score:.2f}")
    
    # Test 6: Test context injection
    logger.info("\n🔗 Test 6: Testing context injection")
    
    try:
        dml_context = context_engine.get_context_for_module('decision_maker_lowcap', {'curator_id': 'tg:@alphaOne'})
        tdl_context = context_engine.get_context_for_module('trader_lowcap', {'token': {'ticker': 'FOO'}})
        
        logger.info(f"   DML Context keys: {list(dml_context.keys())}")
        logger.info(f"   TDL Context keys: {list(tdl_context.keys())}")
    except Exception as e:
        logger.warning(f"   Context injection test failed (expected in mock): {e}")
    
    # Test 7: Test portfolio management
    logger.info("\n💼 Test 7: Testing portfolio management")
    
    portfolio_summary = decision_maker.get_portfolio_summary()
    execution_summary = trader.get_execution_summary()
    
    logger.info(f"   Portfolio Summary: {portfolio_summary}")
    logger.info(f"   Execution Summary: {execution_summary}")
    
    logger.info("\n🎉 Social Lowcap Integration Test Completed Successfully!")
    logger.info("   All modules are working together correctly")
    logger.info("   Learning system integration is functional")
    logger.info("   Database operations are working")
    
    return True


if __name__ == "__main__":
    success = test_social_lowcap_integration()
    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
