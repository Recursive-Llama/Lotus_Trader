"""
Test Uncertainty-Driven Review System
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timezone

from src.intelligence.system_control.central_intelligence_layer.llm_components.motif_miner import MotifMiner


class TestUncertaintyReviewSystem:
    """Test that uncertainty triggers review and resolution actions"""
    
    @pytest.fixture
    def mock_supabase_manager(self):
        return Mock()
    
    @pytest.fixture
    def mock_llm_client(self):
        return Mock()
    
    @pytest.fixture
    def motif_miner(self, mock_supabase_manager, mock_llm_client):
        return MotifMiner(mock_supabase_manager, mock_llm_client)
    
    def test_uncertainty_type_determination(self, motif_miner):
        """Test that uncertainty types are correctly determined from flags"""
        
        # Test pattern clarity uncertainty
        flags = {'pattern_clarity': 'low', 'data_sufficiency': 'sufficient'}
        uncertainty_type = motif_miner._determine_uncertainty_type(flags)
        assert uncertainty_type == 'pattern_clarity'
        
        # Test data sufficiency uncertainty
        flags = {'pattern_clarity': 'high', 'data_sufficiency': 'insufficient'}
        uncertainty_type = motif_miner._determine_uncertainty_type(flags)
        assert uncertainty_type == 'data_sufficiency'
        
        # Test invariant confidence uncertainty
        flags = {'invariant_confidence': 'low', 'context_confidence': 'high'}
        uncertainty_type = motif_miner._determine_uncertainty_type(flags)
        assert uncertainty_type == 'pattern_clarity'
        
        # Test context confidence uncertainty
        flags = {'context_confidence': 'low', 'pattern_clarity': 'high'}
        uncertainty_type = motif_miner._determine_uncertainty_type(flags)
        assert uncertainty_type == 'data_sufficiency'
    
    def test_uncertainty_priority_calculation(self, motif_miner):
        """Test that uncertainty priority is correctly calculated"""
        
        # Test single uncertainty flag
        flags = {'pattern_clarity': 'low'}
        priority = motif_miner._determine_uncertainty_priority(flags)
        assert priority == 0.8  # 0.5 + 0.2 + 0.1 (uncertainty count)
        
        # Test multiple uncertainty flags
        flags = {'pattern_clarity': 'low', 'data_sufficiency': 'insufficient'}
        priority = motif_miner._determine_uncertainty_priority(flags)
        assert priority == 1.0  # 0.5 + 0.2 + 0.3 + 0.2 (capped at 1.0)
        
        # Test no uncertainty flags
        flags = {'pattern_clarity': 'high', 'data_sufficiency': 'sufficient'}
        priority = motif_miner._determine_uncertainty_priority(flags)
        assert priority == 0.5  # Default
        
        # Test medium uncertainty
        flags = {'invariant_confidence': 'low', 'context_confidence': 'low'}
        priority = motif_miner._determine_uncertainty_priority(flags)
        assert priority == 0.7  # 0.5 + 0.2 (uncertainty count)
    
    def test_resolution_actions_mapping(self, motif_miner):
        """Test that appropriate resolution actions are mapped to uncertainty types"""
        
        # Test pattern clarity actions
        actions = motif_miner._get_resolution_actions('pattern_clarity')
        expected_actions = ['data_collection', 'experiment_design', 'human_review', 'pattern_validation']
        assert actions == expected_actions
        
        # Test data sufficiency actions
        actions = motif_miner._get_resolution_actions('data_sufficiency')
        expected_actions = ['data_collection', 'sample_expansion', 'context_broadening', 'data_validation']
        assert actions == expected_actions
        
        # Test causal clarity actions
        actions = motif_miner._get_resolution_actions('causal_clarity')
        expected_actions = ['causal_analysis', 'counterfactual_testing', 'mechanism_research']
        assert actions == expected_actions
        
        # Test analogy confidence actions
        actions = motif_miner._get_resolution_actions('analogy_confidence')
        expected_actions = ['analogy_validation', 'transfer_testing', 'cross_context_analysis']
        assert actions == expected_actions
        
        # Test transfer feasibility actions
        actions = motif_miner._get_resolution_actions('transfer_feasibility')
        expected_actions = ['transfer_validation', 'context_mapping', 'transformation_testing']
        assert actions == expected_actions
        
        # Test unknown uncertainty type (default actions)
        actions = motif_miner._get_resolution_actions('unknown_type')
        expected_actions = ['data_collection', 'human_review']
        assert actions == expected_actions
    
    @pytest.mark.asyncio
    async def test_uncertainty_strand_publishing(self, motif_miner):
        """Test that uncertainty strands are published with correct structure"""
        
        # Mock supabase manager
        motif_miner.supabase_manager.insert_strand = AsyncMock(return_value=True)
        
        # Test data
        cluster = {
            'braid_level': 2,
            'cluster_size': 5,
            'strands': [{'id': 'strand_1'}, {'id': 'strand_2'}]
        }
        
        uncertainty_flags = {
            'pattern_clarity': 'low',
            'data_sufficiency': 'insufficient',
            'uncertainty_notes': 'Pattern is too unclear to be reliable'
        }
        
        motif_data = {
            'motif_name': 'Unclear Pattern',
            'motif_family': 'uncertain',
            'confidence_score': 0.2
        }
        
        # Test uncertainty strand publishing
        result = await motif_miner._publish_uncertainty_strand(cluster, uncertainty_flags, motif_data)
        
        # Verify result
        assert result is True
        
        # Verify supabase manager was called
        motif_miner.supabase_manager.insert_strand.assert_called_once()
        
        # Get the call arguments
        call_args = motif_miner.supabase_manager.insert_strand.call_args[0][0]
        
        # Verify strand structure
        assert call_args['kind'] == 'uncertainty'
        assert call_args['tags'] == ['agent:central_intelligence:motif_miner:uncertainty_detected']
        assert call_args['strategic_meta_type'] == 'uncertainty_detection'
        assert call_args['doctrine_status'] == 'needs_resolution'
        
        # Verify uncertainty data
        module_intel = call_args['module_intelligence']
        assert module_intel['uncertainty_type'] == 'pattern_clarity'  # Should be pattern_clarity due to low flag
        assert module_intel['uncertainty_flags'] == uncertainty_flags
        assert module_intel['partial_motif_data'] == motif_data
        assert module_intel['resolution_priority'] > 0.5  # Should be high priority
        assert 'resolution_actions' in module_intel
        
        # Verify negative scoring (indicates uncertainty)
        assert call_args['sig_sigma'] < 0
        assert call_args['accumulated_score'] < 0
    
    @pytest.mark.asyncio
    async def test_uncertainty_triggers_strand_publishing(self, motif_miner):
        """Test that uncertainty in motif analysis triggers uncertainty strand publishing"""
        
        # Mock supabase manager
        motif_miner.supabase_manager.insert_strand = AsyncMock(return_value=True)
        
        # Test cluster data
        cluster_data = {
            'braid_level': 2,
            'cluster_size': 5,
            'strands': [{'id': 'strand_1', 'regime': 'unknown', 'session_bucket': 'unknown', 'timeframe': 'unknown'}]
        }
        
        # Test uncertainty flags
        uncertainty_flags = {
            'pattern_clarity': 'low',
            'data_sufficiency': 'insufficient',
            'uncertainty_notes': 'Pattern is too unclear to be reliable'
        }
        
        # Test motif data
        motif_data = {
            'motif_name': 'Unclear Pattern',
            'motif_family': 'uncertain',
            'confidence_score': 0.2
        }
        
        # Test uncertainty strand publishing directly
        result = await motif_miner._publish_uncertainty_strand(cluster_data, uncertainty_flags, motif_data)
        
        # Should return True (successful publishing)
        assert result is True
        
        # Should have published uncertainty strand
        motif_miner.supabase_manager.insert_strand.assert_called_once()
        
        # Verify uncertainty strand was published
        call_args = motif_miner.supabase_manager.insert_strand.call_args[0][0]
        assert call_args['kind'] == 'uncertainty'
        assert call_args['strategic_meta_type'] == 'uncertainty_detection'
    
    def test_uncertainty_flow_integration(self, motif_miner):
        """Test that uncertainty flows through the system correctly"""
        
        # Test uncertainty type determination
        flags = {'pattern_clarity': 'low', 'data_sufficiency': 'insufficient'}
        uncertainty_type = motif_miner._determine_uncertainty_type(flags)
        assert uncertainty_type == 'pattern_clarity'  # pattern_clarity takes precedence
        
        # Test priority calculation
        priority = motif_miner._determine_uncertainty_priority(flags)
        assert priority > 0.7  # Should be high priority
        
        # Test resolution actions
        actions = motif_miner._get_resolution_actions(uncertainty_type)
        assert 'data_collection' in actions
        assert 'experiment_design' in actions
        assert 'human_review' in actions
        assert 'pattern_validation' in actions
        
        # Test that uncertainty type maps to correct actions
        assert len(actions) == 4  # Should have 4 specific actions for pattern_clarity


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
