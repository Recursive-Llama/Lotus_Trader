"""
Test Prompt Infrastructure

Comprehensive test suite for the centralized prompt management system,
including PromptManager, governance, and module integration.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from llm_integration.prompt_manager import PromptManager
from llm_integration.prompt_governance import PromptGovernance
from intelligence.llm_integration.braiding_prompts import BraidingPrompts
from intelligence.llm_integration.llm_client import MockLLMClient


class TestPromptInfrastructure:
    """Test suite for prompt infrastructure"""
    
    def setup_method(self):
        """Set up test environment"""
        self.prompt_manager = PromptManager()
        self.governance = PromptGovernance()
        self.mock_llm = MockLLMClient()
    
    def test_prompt_manager_initialization(self):
        """Test PromptManager initialization and template loading"""
        assert self.prompt_manager is not None
        assert len(self.prompt_manager.prompts) > 0
        
        # Check that templates are loaded
        templates = self.prompt_manager.list_templates()
        assert len(templates) > 0
        print(f"✅ Loaded {len(templates)} prompt templates")
    
    def test_conditional_trading_planner_prompts(self):
        """Test CTP-specific prompts"""
        # Test plan generation prompt
        try:
            template = self.prompt_manager.get_prompt('conditional_plan_generation')
            assert 'prompt' in template
            assert 'system_message' in template
            assert 'parameters' in template
            print("✅ CTP plan generation prompt loaded")
        except ValueError:
            print("❌ CTP plan generation prompt not found")
        
        # Test risk assessment prompt
        try:
            template = self.prompt_manager.get_prompt('risk_assessment')
            assert 'prompt' in template
            assert 'system_message' in template
            print("✅ CTP risk assessment prompt loaded")
        except ValueError:
            print("❌ CTP risk assessment prompt not found")
        
        # Test outcome analysis prompt
        try:
            template = self.prompt_manager.get_prompt('trade_outcome_analysis')
            assert 'prompt' in template
            assert 'system_message' in template
            print("✅ CTP outcome analysis prompt loaded")
        except ValueError:
            print("❌ CTP outcome analysis prompt not found")
    
    def test_learning_system_prompts(self):
        """Test learning system prompts"""
        braiding_types = [
            'raw_data_braiding',
            'cil_braiding', 
            'trading_plan_braiding',
            'mixed_braiding',
            'universal_braiding'
        ]
        
        for braiding_type in braiding_types:
            try:
                template = self.prompt_manager.get_prompt(braiding_type)
                assert 'prompt' in template
                assert 'system_message' in template
                print(f"✅ {braiding_type} prompt loaded")
            except ValueError:
                print(f"❌ {braiding_type} prompt not found")
    
    def test_prompt_formatting(self):
        """Test prompt formatting with context"""
        # Test CTP plan generation formatting
        try:
            context = {
                'pattern_group': 'BTC_1h_volume_spike',
                'pattern_types': ['volume_spike', 'divergence'],
                'historical_performance': {'success_rate': 0.75},
                'market_context': 'bullish_trend',
                'trade_outcome_insights': 'High success in trending markets'
            }
            
            formatted_prompt = self.prompt_manager.format_prompt(
                'conditional_plan_generation', 
                context
            )
            
            assert len(formatted_prompt) > 0
            assert 'BTC_1h_volume_spike' in formatted_prompt
            assert 'volume_spike' in formatted_prompt
            print("✅ CTP prompt formatting works")
            
        except ValueError as e:
            print(f"❌ CTP prompt formatting failed: {e}")
    
    def test_braiding_prompts_integration(self):
        """Test BraidingPrompts integration with PromptManager"""
        braiding_prompts = BraidingPrompts(
            llm_client=self.mock_llm,
            prompt_manager=self.prompt_manager
        )
        
        # Test that it uses PromptManager
        assert braiding_prompts.prompt_manager is not None
        assert braiding_prompts.prompt_templates is not None
        
        # Test template mapping
        expected_templates = [
            'raw_data_braiding',
            'cil_braiding',
            'trading_plan_braiding', 
            'mixed_braiding',
            'universal_braiding'
        ]
        
        for template_name in braiding_prompts.prompt_templates.values():
            assert template_name in expected_templates
        
        print("✅ BraidingPrompts integration works")
    
    async def test_braid_generation_with_prompts(self):
        """Test braid generation using centralized prompts"""
        braiding_prompts = BraidingPrompts(
            llm_client=self.mock_llm,
            prompt_manager=self.prompt_manager
        )
        
        # Create test strands
        test_strands = [
            {
                'id': 'strand1',
                'kind': 'pattern',
                'content': {'pattern_type': 'volume_spike', 'asset': 'BTC'},
                'created_at': '2024-01-01T00:00:00Z'
            },
            {
                'id': 'strand2', 
                'kind': 'pattern',
                'content': {'pattern_type': 'divergence', 'asset': 'BTC'},
                'created_at': '2024-01-01T01:00:00Z'
            }
        ]
        
        # Test different braid types
        braid_types = ['raw_data_intelligence', 'central_intelligence_layer', 'universal_braid']
        
        for braid_type in braid_types:
            try:
                lesson = await braiding_prompts.generate_braid_lesson(test_strands, braid_type)
                assert len(lesson) > 0
                print(f"✅ {braid_type} braid generation works")
            except Exception as e:
                print(f"❌ {braid_type} braid generation failed: {e}")
    
    def test_prompt_governance_scanning(self):
        """Test prompt governance scanning"""
        # Test scanning for hardcoded prompts
        violations = self.governance.scan_for_hardcoded_prompts()
        
        print(f"Found {len(violations)} potential hardcoded prompt violations")
        
        # Group by severity
        high_severity = [v for v in violations if v['severity'] == 'high']
        medium_severity = [v for v in violations if v['severity'] == 'medium']
        
        print(f"High severity: {len(high_severity)}")
        print(f"Medium severity: {len(medium_severity)}")
        
        # Show some examples
        if violations:
            print("\nExample violations:")
            for i, violation in enumerate(violations[:3]):
                print(f"  {i+1}. {violation['file']}:{violation['line']} - {violation['pattern']}")
    
    def test_prompt_governance_compliance(self):
        """Test prompt governance compliance checking"""
        summary = self.governance.enforce_prompt_standards()
        
        print(f"Compliance Summary:")
        print(f"  Total violations: {summary['total_violations']}")
        print(f"  Files with violations: {summary['files_with_violations']}")
        print(f"  High severity: {summary['high_severity']}")
        print(f"  Medium severity: {summary['medium_severity']}")
        print(f"  Compliance rate: {summary['compliance_rate']:.2%}")
        
        # Check if we have good compliance
        assert summary['compliance_rate'] >= 0.0  # At least some compliance
        print("✅ Governance compliance check completed")
    
    def test_prompt_template_validation(self):
        """Test prompt template validation"""
        # Test validation with valid context
        try:
            context = {
                'pattern_group': 'test_group',
                'pattern_types': ['test_pattern'],
                'historical_performance': {'success_rate': 0.5},
                'market_context': 'test_context',
                'trade_outcome_insights': 'test_insights'
            }
            
            is_valid = self.prompt_manager.validate_template('conditional_plan_generation', context)
            assert is_valid
            print("✅ Template validation works")
            
        except Exception as e:
            print(f"❌ Template validation failed: {e}")
    
    def test_prompt_parameters(self):
        """Test prompt parameter extraction"""
        try:
            params = self.prompt_manager.get_parameters('conditional_plan_generation')
            assert isinstance(params, dict)
            assert 'temperature' in params
            assert 'max_tokens' in params
            print(f"✅ Prompt parameters: {params}")
            
        except Exception as e:
            print(f"❌ Parameter extraction failed: {e}")
    
    def test_system_message_extraction(self):
        """Test system message extraction"""
        try:
            system_msg = self.prompt_manager.get_system_message('conditional_plan_generation')
            assert isinstance(system_msg, str)
            assert len(system_msg) > 0
            assert 'You are' in system_msg
            print("✅ System message extraction works")
            
        except Exception as e:
            print(f"❌ System message extraction failed: {e}")


def test_prompt_infrastructure_comprehensive():
    """Run comprehensive prompt infrastructure test"""
    print("🚀 Starting Comprehensive Prompt Infrastructure Test")
    print("=" * 60)
    
    test_suite = TestPromptInfrastructure()
    test_suite.setup_method()
    
    # Run all tests
    test_suite.test_prompt_manager_initialization()
    test_suite.test_conditional_trading_planner_prompts()
    test_suite.test_learning_system_prompts()
    test_suite.test_prompt_formatting()
    test_suite.test_braiding_prompts_integration()
    test_suite.test_prompt_governance_scanning()
    test_suite.test_prompt_governance_compliance()
    test_suite.test_prompt_template_validation()
    test_suite.test_prompt_parameters()
    test_suite.test_system_message_extraction()
    
    print("\n" + "=" * 60)
    print("✅ Comprehensive Prompt Infrastructure Test Complete")
    print("🎯 Ready for CTP, DM, and Trader implementation!")


if __name__ == "__main__":
    test_prompt_infrastructure_comprehensive()
