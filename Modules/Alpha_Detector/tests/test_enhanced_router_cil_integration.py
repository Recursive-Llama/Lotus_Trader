"""
Test Enhanced Router CIL Integration

Tests the enhanced Central Intelligence Router configuration for CIL management capabilities.
"""

import pytest
import yaml
import os
from pathlib import Path

class TestEnhancedRouterCILIntegration:
    """Test enhanced router configuration for CIL management"""
    
    def test_router_config_loading(self):
        """Test that the enhanced router configuration loads correctly"""
        config_path = Path(__file__).parent.parent / "config" / "central_intelligence_router.yaml"
        
        assert config_path.exists(), "Router configuration file should exist"
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        assert config is not None, "Configuration should load successfully"
        assert 'router' in config, "Should have router section"
        assert 'agent_registration' in config, "Should have agent registration section"
        assert 'content_type_mappings' in config, "Should have content type mappings"
        assert 'cil_management' in config, "Should have CIL management section"
    
    def test_cil_management_configuration(self):
        """Test CIL management configuration is properly structured"""
        config_path = Path(__file__).parent.parent / "config" / "central_intelligence_router.yaml"
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        cil_management = config['cil_management']
        
        # Test directive tracking
        assert 'directive_tracking' in cil_management
        assert cil_management['directive_tracking']['enabled'] is True
        assert cil_management['directive_tracking']['track_responses'] is True
        assert cil_management['directive_tracking']['track_compliance'] is True
        assert cil_management['directive_tracking']['track_performance'] is True
        
        # Test experiment registry
        assert 'experiment_registry' in cil_management
        assert cil_management['experiment_registry']['enabled'] is True
        assert cil_management['experiment_registry']['track_active_experiments'] is True
        assert cil_management['experiment_registry']['track_completed_experiments'] is True
        assert cil_management['experiment_registry']['track_experiment_outcomes'] is True
        
        # Test directive routing
        assert 'directive_routing' in cil_management
        assert cil_management['directive_routing']['enabled'] is True
        assert 'directive_types' in cil_management['directive_routing']
        assert 'target_team_mapping' in cil_management['directive_routing']
        
        # Test meta-signal routing
        assert 'meta_signal_routing' in cil_management
        assert cil_management['meta_signal_routing']['enabled'] is True
        assert 'meta_signal_types' in cil_management['meta_signal_routing']
        assert 'subscription_mapping' in cil_management['meta_signal_routing']
        
        # Test team coordination
        assert 'team_coordination' in cil_management
        assert cil_management['team_coordination']['enabled'] is True
        assert 'coordination_types' in cil_management['team_coordination']
        assert cil_management['team_coordination']['conflict_resolution'] == "cil_arbitration"
        assert cil_management['team_coordination']['resource_allocation'] == "cil_managed"
        assert cil_management['team_coordination']['priority_override'] == "cil_authority"
    
    def test_cil_team_capabilities(self):
        """Test CIL team capabilities are properly registered"""
        config_path = Path(__file__).parent.parent / "config" / "central_intelligence_router.yaml"
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        agent_registration = config['agent_registration']
        cil_capabilities = agent_registration['default_capabilities']['central_intelligence_layer']
        
        # Test core capabilities
        assert 'strategic_analysis' in cil_capabilities['capabilities']
        assert 'experiment_orchestration' in cil_capabilities['capabilities']
        assert 'doctrine_management' in cil_capabilities['capabilities']
        assert 'plan_composition' in cil_capabilities['capabilities']
        assert 'resonance_management' in cil_capabilities['capabilities']
        
        # Test specializations
        assert 'cross_team_patterns' in cil_capabilities['specializations']
        assert 'strategic_experiments' in cil_capabilities['specializations']
        assert 'doctrine_curation' in cil_capabilities['specializations']
        assert 'strategic_plans' in cil_capabilities['specializations']
        assert 'resonance_calculation' in cil_capabilities['specializations']
        
        # Test management capabilities
        assert 'experiment_assignment' in cil_capabilities['management_capabilities']
        assert 'directive_issuance' in cil_capabilities['management_capabilities']
        assert 'team_coordination' in cil_capabilities['management_capabilities']
        assert 'resource_allocation' in cil_capabilities['management_capabilities']
    
    def test_cil_content_type_mappings(self):
        """Test CIL content type mappings are properly configured"""
        config_path = Path(__file__).parent.parent / "config" / "central_intelligence_router.yaml"
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        content_mappings = config['content_type_mappings']
        
        # Test CIL management mapping
        assert 'cil_management' in content_mappings
        cil_management_mapping = content_mappings['cil_management']
        assert 'strategic_analysis' in cil_management_mapping['required_capabilities']
        assert 'experiment_orchestration' in cil_management_mapping['required_capabilities']
        assert 'central_intelligence_layer' in cil_management_mapping['priority_agents']
        
        # Test CIL directives mapping
        assert 'cil_directives' in content_mappings
        cil_directives_mapping = content_mappings['cil_directives']
        assert 'experiment_assignment' in cil_directives_mapping['required_capabilities']
        assert 'directive_issuance' in cil_directives_mapping['required_capabilities']
        assert 'central_intelligence_layer' in cil_directives_mapping['priority_agents']
        
        # Test CIL meta-signals mapping
        assert 'cil_meta_signals' in content_mappings
        cil_meta_signals_mapping = content_mappings['cil_meta_signals']
        assert 'strategic_analysis' in cil_meta_signals_mapping['required_capabilities']
        assert 'cross_team_patterns' in cil_meta_signals_mapping['required_capabilities']
        assert 'central_intelligence_layer' in cil_meta_signals_mapping['priority_agents']
    
    def test_directive_types_and_mappings(self):
        """Test directive types and target team mappings"""
        config_path = Path(__file__).parent.parent / "config" / "central_intelligence_router.yaml"
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        directive_routing = config['cil_management']['directive_routing']
        
        # Test directive types
        expected_directive_types = [
            "experiment_assignment", 
            "focus_directive", 
            "coordination_request", 
            "resource_allocation"
        ]
        for directive_type in expected_directive_types:
            assert directive_type in directive_routing['directive_types']
        
        # Test target team mappings
        target_mappings = directive_routing['target_team_mapping']
        expected_mappings = [
            "agent:central_intelligence:experiment_orchestrator:experiment_assigned",
            "agent:central_intelligence:strategic_pattern_miner:focus_directive",
            "agent:central_intelligence:doctrine_keeper:coordination_request",
            "agent:central_intelligence:plan_composer:resource_allocation"
        ]
        for mapping in expected_mappings:
            assert mapping in target_mappings
    
    def test_meta_signal_types_and_subscriptions(self):
        """Test meta-signal types and subscription mappings"""
        config_path = Path(__file__).parent.parent / "config" / "central_intelligence_router.yaml"
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        meta_signal_routing = config['cil_management']['meta_signal_routing']
        
        # Test meta-signal types
        expected_meta_signal_types = [
            "confluence_event",
            "experiment_directive", 
            "doctrine_update",
            "strategic_plan",
            "resonance_cluster"
        ]
        for signal_type in expected_meta_signal_types:
            assert signal_type in meta_signal_routing['meta_signal_types']
        
        # Test subscription mappings
        subscription_mappings = meta_signal_routing['subscription_mapping']
        expected_subscriptions = [
            "agent:central_intelligence:meta:confluence_event",
            "agent:central_intelligence:meta:experiment_directive",
            "agent:central_intelligence:meta:doctrine_update",
            "agent:central_intelligence:meta:strategic_plan",
            "agent:central_intelligence:meta:resonance_cluster"
        ]
        for subscription in expected_subscriptions:
            assert subscription in subscription_mappings

