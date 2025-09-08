"""
Test uncertainty handling in Advanced LLM Components
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timezone

from src.intelligence.system_control.central_intelligence_layer.llm_components.motif_miner import MotifMiner
from src.intelligence.system_control.central_intelligence_layer.llm_components.analogy_engine import AnalogyEngine
from src.intelligence.system_control.central_intelligence_layer.llm_components.counterfactual_critic import CounterfactualCritic


class TestUncertaintyHandling:
    """Test that LLM components properly handle uncertainty and don't hallucinate"""
    
    @pytest.fixture
    def mock_supabase_manager(self):
        return Mock()
    
    @pytest.fixture
    def mock_llm_client(self):
        return Mock()
    
    @pytest.fixture
    def motif_miner(self, mock_supabase_manager, mock_llm_client):
        return MotifMiner(mock_supabase_manager, mock_llm_client)
    
    @pytest.fixture
    def analogy_engine(self, mock_supabase_manager, mock_llm_client):
        return AnalogyEngine(mock_supabase_manager, mock_llm_client)
    
    @pytest.fixture
    def counterfactual_critic(self, mock_supabase_manager, mock_llm_client):
        return CounterfactualCritic(mock_supabase_manager, mock_llm_client)
    
    def test_motif_miner_rejects_low_confidence_patterns(self, motif_miner):
        """Test that Motif Miner rejects patterns with low confidence"""
        
        # Mock LLM response with low confidence
        low_confidence_response = json.dumps({
            "motif_name": "Weak Pattern",
            "motif_family": "uncertain",
            "invariants": ["unclear_condition"],
            "fails_when": ["many_conditions"],
            "confidence_score": 0.2,
            "uncertainty_flags": {
                "pattern_clarity": "low",
                "data_sufficiency": "insufficient",
                "invariant_confidence": "low",
                "context_confidence": "low",
                "uncertainty_notes": "Pattern is too unclear to be reliable"
            }
        })
        
        # Test parsing
        cluster_data = {
            'braid_level': 2,
            'strands': [{'id': 'strand_1', 'regime': 'unknown', 'session_bucket': 'unknown', 'timeframe': 'unknown'}]
        }
        
        result = motif_miner._parse_motif_response(low_confidence_response, cluster_data)
        
        # Should return None due to low confidence
        assert result is None
    
    def test_motif_miner_accepts_high_confidence_patterns(self, motif_miner):
        """Test that Motif Miner accepts patterns with high confidence"""
        
        # Mock LLM response with high confidence
        high_confidence_response = json.dumps({
            "motif_name": "Strong Pattern",
            "motif_family": "divergence_volume",
            "invariants": ["rsi_divergence", "volume_spike"],
            "fails_when": ["low_volume", "no_divergence"],
            "confidence_score": 0.85,
            "uncertainty_flags": {
                "pattern_clarity": "high",
                "data_sufficiency": "sufficient",
                "invariant_confidence": "high",
                "context_confidence": "high",
                "uncertainty_notes": "Pattern is clear and well-defined"
            }
        })
        
        # Test parsing
        cluster_data = {
            'braid_level': 2,
            'strands': [{'id': 'strand_1', 'regime': 'high_vol', 'session_bucket': 'US', 'timeframe': '1h'}]
        }
        
        result = motif_miner._parse_motif_response(high_confidence_response, cluster_data)
        
        # Should return valid motif data
        assert result is not None
        assert result['motif_name'] == "Strong Pattern"
        assert result['confidence_score'] == 0.85
    
    def test_analogy_engine_rejects_weak_analogies(self, analogy_engine):
        """Test that Analogy Engine rejects weak analogies"""
        
        # Mock LLM response with weak analogy
        weak_analogy_response = json.dumps({
            "similarity_score": 0.2,
            "transformation_functions": {
                "time_shift": "uncertain",
                "scale_adjustment": "unclear"
            },
            "rhyme_quality": "low",
            "uncertainty_flags": {
                "analogy_confidence": "low",
                "transformation_confidence": "low",
                "transfer_confidence": "low",
                "uncertainty_notes": "Motifs are too different to form meaningful analogy"
            }
        })
        
        # Test parsing
        motif_a = {'id': 'motif_a', 'motif_family': 'divergence'}
        motif_b = {'id': 'motif_b', 'motif_family': 'volume'}
        
        result = analogy_engine._parse_analogy_response(weak_analogy_response, motif_a, motif_b)
        
        # Should return None due to weak analogy
        assert result is None
    
    def test_analogy_engine_accepts_strong_analogies(self, analogy_engine):
        """Test that Analogy Engine accepts strong analogies"""
        
        # Mock LLM response with strong analogy
        strong_analogy_response = json.dumps({
            "similarity_score": 0.8,
            "transformation_functions": {
                "time_shift": "Apply 2-hour delay",
                "scale_adjustment": "Normalize by volatility"
            },
            "rhyme_quality": "high",
            "uncertainty_flags": {
                "analogy_confidence": "high",
                "transformation_confidence": "high",
                "transfer_confidence": "high",
                "uncertainty_notes": "Strong structural similarity between motifs"
            }
        })
        
        # Test parsing
        motif_a = {'id': 'motif_a', 'motif_family': 'divergence'}
        motif_b = {'id': 'motif_b', 'motif_family': 'volume'}
        
        result = analogy_engine._parse_analogy_response(strong_analogy_response, motif_a, motif_b)
        
        # Should return valid analogy data
        assert result is not None
        assert result['similarity_score'] == 0.8
        assert result['rhyme_quality'] == "high"
    
    def test_counterfactual_critic_rejects_unclear_causality(self, counterfactual_critic):
        """Test that Counterfactual Critic rejects unclear causal relationships"""
        
        # Mock LLM response with unclear causality
        unclear_causality_response = json.dumps({
            "necessary_components": ["unclear_component"],
            "optional_components": ["unknown_component"],
            "causal_chain": ["unclear_step_1", "unclear_step_2"],
            "causal_confidence": 0.2,
            "uncertainty_flags": {
                "causal_clarity": "low",
                "component_confidence": "low",
                "chain_confidence": "low",
                "failure_confidence": "low",
                "uncertainty_notes": "Causal relationships are too unclear"
            }
        })
        
        # Test parsing
        motif = {'id': 'motif_1', 'motif_name': 'Unclear Pattern'}
        
        result = counterfactual_critic._parse_causal_skeleton_response(unclear_causality_response, motif)
        
        # Should return None due to unclear causality
        assert result is None
    
    def test_counterfactual_critic_accepts_clear_causality(self, counterfactual_critic):
        """Test that Counterfactual Critic accepts clear causal relationships"""
        
        # Mock LLM response with clear causality
        clear_causality_response = json.dumps({
            "necessary_components": ["rsi_divergence", "volume_confirmation"],
            "optional_components": ["timeframe_variation"],
            "causal_chain": [
                "RSI shows divergence",
                "Volume confirms the signal",
                "Price reacts to the pattern"
            ],
            "causal_confidence": 0.9,
            "uncertainty_flags": {
                "causal_clarity": "high",
                "component_confidence": "high",
                "chain_confidence": "high",
                "failure_confidence": "high",
                "uncertainty_notes": "Clear causal relationships identified"
            }
        })
        
        # Test parsing
        motif = {'id': 'motif_1', 'motif_name': 'Clear Pattern'}
        
        result = counterfactual_critic._parse_causal_skeleton_response(clear_causality_response, motif)
        
        # Should return valid causal skeleton data
        assert result is not None
        assert result['causal_confidence'] == 0.9
        assert len(result['necessary_components']) == 2
    
    def test_uncertainty_flags_preserved_in_output(self, motif_miner):
        """Test that uncertainty flags are preserved in the output"""
        
        # Mock LLM response with uncertainty flags
        response_with_uncertainty = json.dumps({
            "motif_name": "Partially Clear Pattern",
            "motif_family": "divergence_volume",
            "invariants": ["rsi_divergence"],
            "fails_when": ["low_volume"],
            "confidence_score": 0.6,
            "uncertainty_flags": {
                "pattern_clarity": "medium",
                "data_sufficiency": "sufficient",
                "invariant_confidence": "medium",
                "context_confidence": "low",
                "uncertainty_notes": "Pattern is partially clear but context confidence is low"
            }
        })
        
        # Test parsing
        cluster_data = {
            'braid_level': 2,
            'strands': [{'id': 'strand_1', 'regime': 'high_vol', 'session_bucket': 'US', 'timeframe': '1h'}]
        }
        
        result = motif_miner._parse_motif_response(response_with_uncertainty, cluster_data)
        
        # Should return motif data with uncertainty flags preserved
        assert result is not None
        assert 'uncertainty_flags' in result
        assert result['uncertainty_flags']['pattern_clarity'] == "medium"
        assert result['uncertainty_flags']['context_confidence'] == "low"
        assert result['uncertainty_flags']['uncertainty_notes'] == "Pattern is partially clear but context confidence is low"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

