"""
Simple Prompt Infrastructure Test

Basic test for the centralized prompt management system without heavy dependencies.
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_prompt_manager_basic():
    """Test basic PromptManager functionality"""
    try:
        from llm_integration.prompt_manager import PromptManager
        
        # Initialize prompt manager
        prompt_manager = PromptManager()
        print(f"✅ PromptManager initialized with {len(prompt_manager.prompts)} templates")
        
        # List templates
        templates = prompt_manager.list_templates()
        print(f"✅ Found {len(templates)} prompt templates")
        
        # Test specific CTP templates
        ctp_templates = [
            'conditional_plan_generation',
            'risk_assessment', 
            'trade_outcome_analysis'
        ]
        
        for template_name in ctp_templates:
            try:
                template = prompt_manager.get_prompt(template_name)
                assert 'prompt' in template
                assert 'system_message' in template
                print(f"✅ {template_name} template loaded")
            except ValueError:
                print(f"❌ {template_name} template not found")
        
        # Test braiding templates
        braiding_templates = [
            'raw_data_braiding',
            'cil_braiding',
            'trading_plan_braiding',
            'mixed_braiding',
            'universal_braiding'
        ]
        
        for template_name in braiding_templates:
            try:
                template = prompt_manager.get_prompt(template_name)
                assert 'prompt' in template
                print(f"✅ {template_name} template loaded")
            except ValueError:
                print(f"❌ {template_name} template not found")
        
        return True
        
    except Exception as e:
        print(f"❌ PromptManager test failed: {e}")
        return False

def test_prompt_formatting():
    """Test prompt formatting with context"""
    try:
        from llm_integration.prompt_manager import PromptManager
        
        prompt_manager = PromptManager()
        
        # Test CTP plan generation formatting
        context = {
            'pattern_group': 'BTC_1h_volume_spike',
            'pattern_types': ['volume_spike', 'divergence'],
            'historical_performance': {'success_rate': 0.75},
            'market_context': 'bullish_trend',
            'trade_outcome_insights': 'High success in trending markets'
        }
        
        formatted_prompt = prompt_manager.format_prompt('conditional_plan_generation', context)
        
        assert len(formatted_prompt) > 0
        assert 'BTC_1h_volume_spike' in formatted_prompt
        assert 'volume_spike' in formatted_prompt
        print("✅ Prompt formatting works")
        
        return True
        
    except Exception as e:
        print(f"❌ Prompt formatting test failed: {e}")
        return False

def test_prompt_governance():
    """Test prompt governance scanning"""
    try:
        from llm_integration.prompt_governance import PromptGovernance
        
        governance = PromptGovernance()
        
        # Test scanning for hardcoded prompts
        violations = governance.scan_for_hardcoded_prompts()
        
        print(f"✅ Found {len(violations)} potential hardcoded prompt violations")
        
        # Group by severity
        high_severity = [v for v in violations if v['severity'] == 'high']
        medium_severity = [v for v in violations if v['severity'] == 'medium']
        
        print(f"  High severity: {len(high_severity)}")
        print(f"  Medium severity: {len(medium_severity)}")
        
        # Show some examples
        if violations:
            print("\nExample violations:")
            for i, violation in enumerate(violations[:3]):
                print(f"  {i+1}. {violation['file']}:{violation['line']} - {violation['pattern']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Prompt governance test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Simple Prompt Infrastructure Test")
    print("=" * 50)
    
    tests = [
        test_prompt_manager_basic,
        test_prompt_formatting,
        test_prompt_governance
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        print(f"\n🧪 Running {test.__name__}...")
        if test():
            passed += 1
            print(f"✅ {test.__name__} passed")
        else:
            print(f"❌ {test.__name__} failed")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎯 All tests passed! Prompt infrastructure is ready.")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
