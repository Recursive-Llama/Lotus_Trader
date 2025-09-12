"""
Test Prompt Files Directly

Test the YAML prompt files directly without importing heavy dependencies.
"""

import os
import yaml
from pathlib import Path

def test_yaml_files_exist():
    """Test that all expected YAML prompt files exist"""
    base_path = Path(__file__).parent.parent / "src" / "llm_integration" / "prompt_templates"
    
    expected_files = [
        "conditional_trading_planner/plan_generation.yaml",
        "conditional_trading_planner/risk_assessment.yaml", 
        "conditional_trading_planner/outcome_analysis.yaml",
        "learning_system/braiding_prompts.yaml",
        "prediction_engine/prediction_generation.yaml",
        "central_intelligence_layer/learning_analysis.yaml"
    ]
    
    missing_files = []
    
    for file_path in expected_files:
        full_path = base_path / file_path
        if not full_path.exists():
            missing_files.append(file_path)
        else:
            print(f"✅ {file_path} exists")
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All expected YAML files exist")
        return True

def test_yaml_structure():
    """Test that YAML files have correct structure"""
    base_path = Path(__file__).parent.parent / "src" / "llm_integration" / "prompt_templates"
    
    # Test CTP plan generation
    ctp_file = base_path / "conditional_trading_planner" / "plan_generation.yaml"
    
    try:
        with open(ctp_file, 'r') as f:
            data = yaml.safe_load(f)
        
        # Check structure
        assert 'conditional_plan_generation' in data
        template = data['conditional_plan_generation']
        
        assert 'description' in template
        assert 'category' in template
        assert 'latest_version' in template
        assert 'versions' in template
        
        version = template['versions']['v2.0']
        assert 'system_message' in version
        assert 'prompt' in version
        assert 'parameters' in version
        assert 'context_variables' in version
        
        print("✅ CTP plan generation YAML structure is correct")
        
    except Exception as e:
        print(f"❌ CTP plan generation YAML structure error: {e}")
        return False
    
    # Test braiding prompts
    braiding_file = base_path / "learning_system" / "braiding_prompts.yaml"
    
    try:
        with open(braiding_file, 'r') as f:
            data = yaml.safe_load(f)
        
        # Check that all braiding types exist
        expected_braiding_types = [
            'raw_data_braiding',
            'cil_braiding',
            'conditional_trading_plan_braiding',
            'trade_outcome_braiding',
            'mixed_braiding',
            'universal_braiding'
        ]
        
        for braiding_type in expected_braiding_types:
            assert braiding_type in data
            template = data[braiding_type]
            assert 'versions' in template
            version = template['versions']['v2.0']
            assert 'system_message' in version
            assert 'prompt' in version
            assert 'parameters' in version
        
        print("✅ Braiding prompts YAML structure is correct")
        
    except Exception as e:
        print(f"❌ Braiding prompts YAML structure error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def test_prompt_content():
    """Test that prompts contain expected content"""
    base_path = Path(__file__).parent.parent / "src" / "llm_integration" / "prompt_templates"
    
    # Test CTP plan generation content
    ctp_file = base_path / "conditional_trading_planner" / "plan_generation.yaml"
    
    try:
        with open(ctp_file, 'r') as f:
            data = yaml.safe_load(f)
        
        template = data['conditional_plan_generation']['versions']['v2.0']
        
        # Check system message
        system_msg = template['system_message']
        assert 'You are an expert quantitative trading strategist' in system_msg
        assert 'conditional logic' in system_msg
        assert 'relative positioning' in system_msg
        
        # Check prompt
        prompt = template['prompt']
        assert 'pattern_group' in prompt
        assert 'pattern_types' in prompt
        assert 'JSON' in prompt
        assert 'conditional_entry' in prompt
        
        print("✅ CTP plan generation content is correct")
        
    except Exception as e:
        print(f"❌ CTP plan generation content error: {e}")
        return False
    
    return True

def test_context_variables():
    """Test that context variables are properly defined"""
    base_path = Path(__file__).parent.parent / "src" / "llm_integration" / "prompt_templates"
    
    # Test CTP plan generation context variables
    ctp_file = base_path / "conditional_trading_planner" / "plan_generation.yaml"
    
    try:
        with open(ctp_file, 'r') as f:
            data = yaml.safe_load(f)
        
        template = data['conditional_plan_generation']['versions']['v2.0']
        context_vars = template['context_variables']
        
        expected_vars = [
            'pattern_group',
            'pattern_types', 
            'historical_performance',
            'market_context',
            'trade_outcome_insights'
        ]
        
        for var in expected_vars:
            assert var in context_vars
        
        print("✅ CTP context variables are correct")
        
    except Exception as e:
        print(f"❌ CTP context variables error: {e}")
        return False
    
    return True

def main():
    """Run all tests"""
    print("🚀 Starting Prompt Files Test")
    print("=" * 40)
    
    tests = [
        test_yaml_files_exist,
        test_yaml_structure,
        test_prompt_content,
        test_context_variables
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
    
    print("\n" + "=" * 40)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎯 All prompt file tests passed!")
        print("✅ Prompt infrastructure is ready for CTP, DM, and Trader implementation!")
        return True
    else:
        print("⚠️  Some prompt file tests failed. Check the output above.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
