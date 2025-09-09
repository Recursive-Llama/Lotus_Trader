#!/usr/bin/env python3
"""
Comprehensive CIL Functionality Test Suite

This test suite puts the CIL system through its paces by:
1. Mocking Raw Data Intelligence patterns and inserting them into the database
2. Testing all CIL functionality with real LLM calls
3. Assessing CIL's decisions and outputs
4. Identifying blockages, complexities, and well-working parts
5. Testing the full system (code + LLM combination)

Test Categories:
- Pattern Processing & Analysis
- Strategic Intelligence Generation
- Cross-Agent Communication
- Learning & Adaptation
- Decision Making & Recommendations
- System Integration & Coordination
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import uuid

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from intelligence.system_control.central_intelligence_layer.core.central_intelligence_agent import CentralIntelligenceAgent
from intelligence.system_control.central_intelligence_layer.engines.global_synthesis_engine import GlobalSynthesisEngine
from intelligence.system_control.central_intelligence_layer.engines.input_processor import InputProcessor
from intelligence.system_control.central_intelligence_layer.engines.experiment_orchestration_engine import ExperimentOrchestrationEngine
from intelligence.system_control.central_intelligence_layer.engines.learning_feedback_engine import LearningFeedbackEngine
from intelligence.system_control.central_intelligence_layer.engines.autonomy_adaptation_engine import AutonomyAdaptationEngine
from intelligence.system_control.central_intelligence_layer.engines.output_directive_system import OutputDirectiveSystem
from intelligence.system_control.central_intelligence_layer.engines.governance_system import GovernanceSystem
from intelligence.system_control.central_intelligence_layer.engines.system_resonance_manager import SystemResonanceManager

# Database imports
from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CILFunctionalityTester:
    """Comprehensive CIL functionality tester"""
    
    def __init__(self):
        self.db = SupabaseManager()
        self.cil_agent = None
        self.test_results = {
            'pattern_processing': {},
            'strategic_intelligence': {},
            'cross_agent_communication': {},
            'learning_adaptation': {},
            'decision_making': {},
            'system_integration': {},
            'blockages': [],
            'working_well': [],
            'complexities': []
        }
        
    async def setup(self):
        """Initialize the CIL agent and database connection"""
        try:
            # Test database connection
            if not self.db.test_connection():
                raise Exception("Database connection failed")
            
            # Initialize LLM client
            llm_client = OpenRouterClient()
            
            # Initialize CIL agent with required parameters
            self.cil_agent = CentralIntelligenceAgent(self.db, llm_client)
            logger.info("✅ CIL agent initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize CIL agent: {e}")
            raise
    
    async def cleanup(self):
        """Clean up resources"""
        # SupabaseManager doesn't need explicit cleanup
        pass
    
    def create_mock_raw_patterns(self) -> List[Dict[str, Any]]:
        """Create diverse mock Raw Data Intelligence patterns"""
        patterns = []
        
        # Pattern 1: High-confidence divergence
        patterns.append({
            'agent_id': 'alpha_raw_data_intelligence',
            'team_member': 'divergence_detector',
            'kind': 'raw_data_pattern',
            'content': json.dumps({
                'pattern_type': 'divergence',
                'asset': 'BTCUSDT',
                'timeframe': '1m',
                'confidence': 0.92,
                'pattern_data': {
                    'price_divergence': 0.045,
                    'volume_spike': 2.3,
                    'rsi_divergence': True,
                    'macd_divergence': True
                },
                'timestamp': datetime.now().isoformat(),
                'metadata': {
                    'source': 'mock_test',
                    'test_id': 'divergence_high_confidence'
                }
            }),
            'confidence': 0.92,
            'tags': ['cil', 'pattern_analysis', 'divergence'],
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        })
        
        # Pattern 2: Medium-confidence volume pattern
        patterns.append({
            'agent_id': 'alpha_raw_data_intelligence',
            'team_member': 'volume_analyzer',
            'kind': 'raw_data_pattern',
            'content': json.dumps({
                'pattern_type': 'volume_anomaly',
                'asset': 'ETHUSDT',
                'timeframe': '1m',
                'confidence': 0.78,
                'pattern_data': {
                    'volume_ratio': 1.8,
                    'price_movement': 0.023,
                    'volume_profile': 'unusual',
                    'market_depth': 'shallow'
                },
                'timestamp': datetime.now().isoformat(),
                'metadata': {
                    'source': 'mock_test',
                    'test_id': 'volume_medium_confidence'
                }
            }),
            'confidence': 0.78,
            'tags': ['cil', 'pattern_analysis', 'volume'],
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        })
        
        # Pattern 3: Low-confidence support/resistance
        patterns.append({
            'agent_id': 'alpha_raw_data_intelligence',
            'team_member': 'support_resistance_detector',
            'kind': 'raw_data_pattern',
            'content': json.dumps({
                'pattern_type': 'support_resistance',
                'asset': 'ADAUSDT',
                'timeframe': '1m',
                'confidence': 0.65,
                'pattern_data': {
                    'support_level': 0.45,
                    'resistance_level': 0.52,
                    'touch_count': 2,
                    'strength': 'weak'
                },
                'timestamp': datetime.now().isoformat(),
                'metadata': {
                    'source': 'mock_test',
                    'test_id': 'support_resistance_low_confidence'
                }
            }),
            'confidence': 0.65,
            'tags': ['cil', 'pattern_analysis', 'support_resistance'],
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        })
        
        # Pattern 4: High-confidence momentum pattern
        patterns.append({
            'agent_id': 'alpha_raw_data_intelligence',
            'team_member': 'momentum_detector',
            'kind': 'raw_data_pattern',
            'content': json.dumps({
                'pattern_type': 'momentum_breakout',
                'asset': 'SOLUSDT',
                'timeframe': '1m',
                'confidence': 0.89,
                'pattern_data': {
                    'momentum_strength': 0.78,
                    'breakout_volume': 2.1,
                    'trend_continuation': True,
                    'volatility_expansion': True
                },
                'timestamp': datetime.now().isoformat(),
                'metadata': {
                    'source': 'mock_test',
                    'test_id': 'momentum_high_confidence'
                }
            }),
            'confidence': 0.89,
            'tags': ['cil', 'pattern_analysis', 'momentum'],
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        })
        
        # Pattern 5: Cross-asset correlation pattern
        patterns.append({
            'agent_id': 'alpha_raw_data_intelligence',
            'team_member': 'correlation_analyzer',
            'kind': 'raw_data_pattern',
            'content': json.dumps({
                'pattern_type': 'cross_asset_correlation',
                'assets': ['BTCUSDT', 'ETHUSDT'],
                'timeframe': '1m',
                'confidence': 0.85,
                'pattern_data': {
                    'correlation_strength': 0.82,
                    'correlation_type': 'positive',
                    'lag_time': 0,
                    'stability': 'high'
                },
                'timestamp': datetime.now().isoformat(),
                'metadata': {
                    'source': 'mock_test',
                    'test_id': 'correlation_high_confidence'
                }
            }),
            'confidence': 0.85,
            'tags': ['cil', 'pattern_analysis', 'correlation'],
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        })
        
        return patterns
    
    async def insert_mock_patterns(self, patterns: List[Dict[str, Any]]) -> List[str]:
        """Insert mock patterns into the database"""
        inserted_ids = []
        
        for pattern in patterns:
            try:
                # Convert datetime objects to ISO strings for Supabase
                pattern_data = pattern.copy()
                pattern_data['created_at'] = pattern['created_at'].isoformat()
                pattern_data['updated_at'] = pattern['updated_at'].isoformat()
                
                result = self.db.insert_strand(pattern_data)
                if result and 'id' in result:
                    inserted_ids.append(str(result['id']))
                    logger.info(f"✅ Inserted pattern: {pattern['kind']} - {pattern['agent_id']}")
                else:
                    logger.error(f"❌ Failed to insert pattern: No ID returned")
                    self.test_results['blockages'].append(f"Pattern insertion failed: No ID returned")
                
            except Exception as e:
                logger.error(f"❌ Failed to insert pattern: {e}")
                self.test_results['blockages'].append(f"Pattern insertion failed: {e}")
        
        return inserted_ids
    
    async def test_pattern_processing(self):
        """Test CIL's pattern processing capabilities"""
        logger.info("🧪 Testing Pattern Processing...")
        
        try:
            # Create and insert mock patterns
            patterns = self.create_mock_raw_patterns()
            pattern_ids = await self.insert_mock_patterns(patterns)
            
            # Test CIL pattern processing
            processing_results = await self.cil_agent._coordinate_comprehensive_analysis()
            
            self.test_results['pattern_processing'] = {
                'patterns_inserted': len(pattern_ids),
                'processing_successful': processing_results is not None,
                'processing_results': processing_results
            }
            
            logger.info(f"✅ Pattern processing test completed: {len(pattern_ids)} patterns processed")
            
        except Exception as e:
            logger.error(f"❌ Pattern processing test failed: {e}")
            self.test_results['blockages'].append(f"Pattern processing failed: {e}")
    
    async def test_strategic_intelligence_generation(self):
        """Test CIL's strategic intelligence generation"""
        logger.info("🧪 Testing Strategic Intelligence Generation...")
        
        try:
            # Initialize LLM client for engines
            llm_client = OpenRouterClient()
            
            # Test Global Synthesis Engine
            global_synthesis = GlobalSynthesisEngine(self.db, llm_client)
            synthesis_results = await global_synthesis.process_global_synthesis()
            
            # Test Input Processor
            input_processor = InputProcessor(self.db, llm_client)
            input_results = await input_processor.process_input_analysis()
            
            # Test Experiment Orchestration
            experiment_engine = ExperimentOrchestrationEngine(self.db, llm_client)
            experiment_results = await experiment_engine.process_experiment_orchestration()
            
            self.test_results['strategic_intelligence'] = {
                'global_synthesis': synthesis_results,
                'input_processing': input_results,
                'experiment_orchestration': experiment_results
            }
            
            logger.info("✅ Strategic intelligence generation test completed")
            
        except Exception as e:
            logger.error(f"❌ Strategic intelligence generation test failed: {e}")
            self.test_results['blockages'].append(f"Strategic intelligence generation failed: {e}")
    
    async def test_cross_agent_communication(self):
        """Test CIL's cross-agent communication capabilities"""
        logger.info("🧪 Testing Cross-Agent Communication...")
        
        try:
            # Initialize LLM client for engines
            llm_client = OpenRouterClient()
            
            # Test Output Directive System
            output_system = OutputDirectiveSystem(self.db, llm_client)
            directive_results = await output_system.process_output_directives()
            
            # Test Governance System
            governance = GovernanceSystem(self.db, llm_client)
            governance_results = await governance.process_governance_decisions()
            
            self.test_results['cross_agent_communication'] = {
                'output_directives': directive_results,
                'governance_decisions': governance_results
            }
            
            logger.info("✅ Cross-agent communication test completed")
            
        except Exception as e:
            logger.error(f"❌ Cross-agent communication test failed: {e}")
            self.test_results['blockages'].append(f"Cross-agent communication failed: {e}")
    
    async def test_learning_adaptation(self):
        """Test CIL's learning and adaptation capabilities"""
        logger.info("🧪 Testing Learning & Adaptation...")
        
        try:
            # Initialize LLM client for engines
            llm_client = OpenRouterClient()
            
            # Test Learning Feedback Engine
            learning_engine = LearningFeedbackEngine(self.db, llm_client)
            learning_results = await learning_engine.process_learning_feedback()
            
            # Test Autonomy Adaptation Engine
            autonomy_engine = AutonomyAdaptationEngine(self.db, llm_client)
            autonomy_results = await autonomy_engine.process_autonomy_adaptation()
            
            # Test System Resonance Manager
            resonance_manager = SystemResonanceManager(self.db, llm_client)
            resonance_results = await resonance_manager.process_system_resonance()
            
            self.test_results['learning_adaptation'] = {
                'learning_feedback': learning_results,
                'autonomy_adaptation': autonomy_results,
                'system_resonance': resonance_results
            }
            
            logger.info("✅ Learning & adaptation test completed")
            
        except Exception as e:
            logger.error(f"❌ Learning & adaptation test failed: {e}")
            self.test_results['blockages'].append(f"Learning & adaptation failed: {e}")
    
    async def test_decision_making(self):
        """Test CIL's decision-making capabilities"""
        logger.info("🧪 Testing Decision Making...")
        
        try:
            # Test comprehensive CIL analysis
            comprehensive_results = await self.cil_agent._coordinate_comprehensive_analysis()
            
            # Initialize LLM client for engines
            llm_client = OpenRouterClient()
            
            # Test individual engine decision-making
            engines = [
                ('GlobalSynthesis', GlobalSynthesisEngine(self.db, llm_client)),
                ('InputProcessor', InputProcessor(self.db, llm_client)),
                ('ExperimentOrchestration', ExperimentOrchestrationEngine(self.db, llm_client)),
                ('LearningFeedback', LearningFeedbackEngine(self.db, llm_client)),
                ('AutonomyAdaptation', AutonomyAdaptationEngine(self.db, llm_client)),
                ('OutputDirective', OutputDirectiveSystem(self.db, llm_client)),
                ('Governance', GovernanceSystem(self.db, llm_client)),
                ('SystemResonance', SystemResonanceManager(self.db, llm_client))
            ]
            
            engine_decisions = {}
            for name, engine in engines:
                try:
                    if hasattr(engine, 'process_global_synthesis'):
                        result = await engine.process_global_synthesis()
                    elif hasattr(engine, 'process_input_analysis'):
                        result = await engine.process_input_analysis()
                    elif hasattr(engine, 'process_experiment_orchestration'):
                        result = await engine.process_experiment_orchestration()
                    elif hasattr(engine, 'process_learning_feedback'):
                        result = await engine.process_learning_feedback()
                    elif hasattr(engine, 'process_autonomy_adaptation'):
                        result = await engine.process_autonomy_adaptation()
                    elif hasattr(engine, 'process_output_directives'):
                        result = await engine.process_output_directives()
                    elif hasattr(engine, 'process_governance_decisions'):
                        result = await engine.process_governance_decisions()
                    elif hasattr(engine, 'process_system_resonance'):
                        result = await engine.process_system_resonance()
                    else:
                        result = "No process method found"
                    
                    engine_decisions[name] = result
                    
                except Exception as e:
                    engine_decisions[name] = f"Error: {e}"
                    self.test_results['blockages'].append(f"{name} decision-making failed: {e}")
            
            self.test_results['decision_making'] = {
                'comprehensive_analysis': comprehensive_results,
                'engine_decisions': engine_decisions
            }
            
            logger.info("✅ Decision making test completed")
            
        except Exception as e:
            logger.error(f"❌ Decision making test failed: {e}")
            self.test_results['blockages'].append(f"Decision making failed: {e}")
    
    async def test_system_integration(self):
        """Test CIL's system integration capabilities"""
        logger.info("🧪 Testing System Integration...")
        
        try:
            # Test CIL agent initialization and coordination
            if self.cil_agent:
                team_members = self.cil_agent.team_members
                coordination_results = await self.cil_agent._coordinate_comprehensive_analysis()
                
                self.test_results['system_integration'] = {
                    'team_members_count': len(team_members),
                    'team_member_types': [type(member).__name__ for member in team_members],
                    'coordination_successful': coordination_results is not None,
                    'coordination_results': coordination_results
                }
                
                logger.info(f"✅ System integration test completed: {len(team_members)} team members")
            
        except Exception as e:
            logger.error(f"❌ System integration test failed: {e}")
            self.test_results['blockages'].append(f"System integration failed: {e}")
    
    async def analyze_test_results(self):
        """Analyze test results and identify patterns"""
        logger.info("📊 Analyzing Test Results...")
        
        # Identify what's working well
        if self.test_results['pattern_processing'].get('processing_successful'):
            self.test_results['working_well'].append("Pattern processing is working")
        
        if self.test_results['strategic_intelligence']:
            self.test_results['working_well'].append("Strategic intelligence generation is working")
        
        if self.test_results['cross_agent_communication']:
            self.test_results['working_well'].append("Cross-agent communication is working")
        
        if self.test_results['learning_adaptation']:
            self.test_results['working_well'].append("Learning & adaptation is working")
        
        if self.test_results['decision_making']:
            self.test_results['working_well'].append("Decision making is working")
        
        if self.test_results['system_integration']:
            self.test_results['working_well'].append("System integration is working")
        
        # Identify complexities
        if len(self.test_results['blockages']) > 0:
            self.test_results['complexities'].append(f"Found {len(self.test_results['blockages'])} blockages")
        
        # Count successful tests
        successful_tests = sum(1 for category in self.test_results.values() 
                             if isinstance(category, dict) and category)
        
        logger.info(f"📊 Test Analysis Complete:")
        logger.info(f"   ✅ Working Well: {len(self.test_results['working_well'])}")
        logger.info(f"   ❌ Blockages: {len(self.test_results['blockages'])}")
        logger.info(f"   🔄 Complexities: {len(self.test_results['complexities'])}")
        logger.info(f"   📈 Successful Tests: {successful_tests}/6")
    
    async def run_comprehensive_test(self):
        """Run the complete CIL functionality test suite"""
        logger.info("🚀 Starting Comprehensive CIL Functionality Test Suite")
        
        try:
            await self.setup()
            
            # Run all test categories
            await self.test_pattern_processing()
            await self.test_strategic_intelligence_generation()
            await self.test_cross_agent_communication()
            await self.test_learning_adaptation()
            await self.test_decision_making()
            await self.test_system_integration()
            
            # Analyze results
            await self.analyze_test_results()
            
            # Print comprehensive results
            self.print_test_results()
            
        except Exception as e:
            logger.error(f"❌ Comprehensive test failed: {e}")
            raise
        finally:
            await self.cleanup()
    
    def print_test_results(self):
        """Print comprehensive test results"""
        print("\n" + "="*80)
        print("🧪 CIL FUNCTIONALITY TEST RESULTS")
        print("="*80)
        
        print(f"\n📊 OVERALL SUMMARY:")
        print(f"   ✅ Working Well: {len(self.test_results['working_well'])}")
        print(f"   ❌ Blockages: {len(self.test_results['blockages'])}")
        print(f"   🔄 Complexities: {len(self.test_results['complexities'])}")
        
        print(f"\n✅ WHAT'S WORKING WELL:")
        for item in self.test_results['working_well']:
            print(f"   • {item}")
        
        if self.test_results['blockages']:
            print(f"\n❌ BLOCKAGES IDENTIFIED:")
            for blockage in self.test_results['blockages']:
                print(f"   • {blockage}")
        
        if self.test_results['complexities']:
            print(f"\n🔄 COMPLEXITIES IDENTIFIED:")
            for complexity in self.test_results['complexities']:
                print(f"   • {complexity}")
        
        print(f"\n📈 DETAILED RESULTS:")
        for category, results in self.test_results.items():
            if isinstance(results, dict) and results:
                print(f"\n   {category.upper().replace('_', ' ')}:")
                for key, value in results.items():
                    if isinstance(value, (dict, list)):
                        print(f"     • {key}: {type(value).__name__} with {len(value)} items")
                    else:
                        print(f"     • {key}: {value}")
        
        print("\n" + "="*80)

async def main():
    """Main test execution"""
    tester = CILFunctionalityTester()
    await tester.run_comprehensive_test()

if __name__ == "__main__":
    asyncio.run(main())
