"""
Integration Tests for Module-Specific Resonance Scoring

Comprehensive test suite for the module-specific resonance scoring system,
including mathematical resonance engine, module-specific scoring, and
historical data retrieval functions.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone, timedelta
import json

# Import the modules to test
from mathematical_resonance_engine import MathematicalResonanceEngine
from module_specific_scoring import ModuleSpecificScoring
from historical_data_functions import HistoricalDataRetriever
from centralized_learning_system import CentralizedLearningSystem


class TestMathematicalResonanceEngine:
    """Test the mathematical resonance engine with module-specific calculations"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.engine = MathematicalResonanceEngine()
        
        # Sample strand data for each module type
        self.sample_strands = {
            'rdi': {
                'id': 'test_rdi_001',
                'kind': 'pattern',
                'module_intelligence': {
                    'pattern_type': 'diagonal_breakout',
                    'success_rate': 0.75
                },
                'sig_confidence': 0.8,
                'sig_sigma': 0.7,
                'motif_family': 'trend_following'
            },
            'cil': {
                'id': 'test_cil_001',
                'kind': 'prediction_review',
                'content': {
                    'success': True,
                    'confidence': 0.85,
                    'return_pct': 0.12,
                    'method': 'ensemble'
                },
                'strategic_meta_type': 'meta_learning'
            },
            'ctp': {
                'id': 'test_ctp_001',
                'kind': 'conditional_trading_plan',
                'content': {
                    'profitability': 0.6,
                    'risk_adjusted_return': 0.8,
                    'plan_type': 'breakout_strategy',
                    'strategy': 'momentum'
                },
                'quality_score': 0.75
            },
            'dm': {
                'id': 'test_dm_001',
                'kind': 'trading_decision',
                'content': {
                    'outcome_quality': 0.7,
                    'risk_management_effectiveness': 0.8,
                    'decision_type': 'position_sizing',
                    'decision_factors': ['risk', 'volatility', 'correlation']
                }
            },
            'td': {
                'id': 'test_td_001',
                'kind': 'execution_outcome',
                'content': {
                    'execution_success': 0.9,
                    'slippage_minimization': 0.85,
                    'execution_method': 'twap',
                    'execution_strategy': 'adaptive'
                }
            }
        }
    
    def test_module_resonance_calculation(self):
        """Test module-specific resonance calculation"""
        for module_type, strand in self.sample_strands.items():
            result = self.engine.calculate_module_resonance(strand, module_type)
            
            # Check that all resonance values are present
            assert 'phi' in result
            assert 'rho' in result
            assert 'theta' in result
            assert 'omega' in result
            assert 'module_type' in result
            assert 'calculated_at' in result
            
            # Check that values are in expected ranges
            assert 0.0 <= result['phi'] <= 2.0
            assert 0.0 <= result['rho'] <= 2.0
            assert 0.0 <= result['theta'] <= 1.0
            assert 0.0 <= result['omega'] <= 2.0
            
            # Check module type is correct
            assert result['module_type'] == module_type
    
    def test_rdi_resonance_calculation(self):
        """Test RDI-specific resonance calculations"""
        strand = self.sample_strands['rdi']
        result = self.engine.calculate_module_resonance(strand, 'rdi')
        
        # RDI should have high phi (fractal consistency) due to high confidence
        assert result['phi'] > 0.5
        
        # RDI should have moderate rho (recursive feedback) based on success rate
        assert 0.0 <= result['rho'] <= 1.0
        
        # RDI should have moderate theta (collective intelligence) based on diversity
        assert 0.0 <= result['theta'] <= 1.0
    
    def test_cil_resonance_calculation(self):
        """Test CIL-specific resonance calculations"""
        strand = self.sample_strands['cil']
        result = self.engine.calculate_module_resonance(strand, 'cil')
        
        # CIL should have high phi due to successful prediction
        assert result['phi'] > 0.5
        
        # CIL should have high rho due to successful prediction with return
        assert result['rho'] > 0.5
        
        # CIL should have moderate theta based on method diversity
        assert 0.0 <= result['theta'] <= 1.0
    
    def test_ctp_resonance_calculation(self):
        """Test CTP-specific resonance calculations"""
        strand = self.sample_strands['ctp']
        result = self.engine.calculate_module_resonance(strand, 'ctp')
        
        # CTP should have moderate phi based on profitability and risk
        assert 0.0 <= result['phi'] <= 1.0
        
        # CTP should have moderate rho based on profitability
        assert 0.0 <= result['rho'] <= 1.0
        
        # CTP should have moderate theta based on strategy diversity
        assert 0.0 <= result['theta'] <= 1.0
    
    def test_dm_resonance_calculation(self):
        """Test DM-specific resonance calculations"""
        strand = self.sample_strands['dm']
        result = self.engine.calculate_module_resonance(strand, 'dm')
        
        # DM should have moderate phi based on outcome quality and risk management
        assert 0.0 <= result['phi'] <= 1.0
        
        # DM should have moderate rho based on outcome quality
        assert 0.0 <= result['rho'] <= 1.0
        
        # DM should have moderate theta based on factor diversity
        assert 0.0 <= result['theta'] <= 1.0
    
    def test_td_resonance_calculation(self):
        """Test TD-specific resonance calculations"""
        strand = self.sample_strands['td']
        result = self.engine.calculate_module_resonance(strand, 'td')
        
        # TD should have high phi due to high execution success
        assert result['phi'] > 0.5
        
        # TD should have high rho due to high execution success and slippage control
        assert result['rho'] > 0.5
        
        # TD should have moderate theta based on strategy diversity
        assert 0.0 <= result['theta'] <= 1.0
    
    def test_unknown_module_type(self):
        """Test handling of unknown module type"""
        strand = self.sample_strands['rdi']
        result = self.engine.calculate_module_resonance(strand, 'unknown')
        
        # Should return error values
        assert result['phi'] == 0.0
        assert result['rho'] == 0.0
        assert result['theta'] == 0.0
        assert result['omega'] == 0.0
        assert 'error' in result


class TestModuleSpecificScoring:
    """Test the module-specific scoring functions"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.scoring = ModuleSpecificScoring()
        
        # Sample strand data for each module type
        self.sample_strands = {
            'rdi': {
                'id': 'test_rdi_001',
                'kind': 'pattern',
                'module_intelligence': {
                    'pattern_type': 'diagonal_breakout',
                    'success_rate': 0.75
                },
                'sig_confidence': 0.8,
                'sig_sigma': 0.7,
                'motif_family': 'trend_following'
            },
            'cil': {
                'id': 'test_cil_001',
                'kind': 'prediction_review',
                'content': {
                    'success': True,
                    'confidence': 0.85,
                    'return_pct': 0.12,
                    'method': 'ensemble'
                },
                'strategic_meta_type': 'meta_learning'
            },
            'ctp': {
                'id': 'test_ctp_001',
                'kind': 'conditional_trading_plan',
                'content': {
                    'profitability': 0.6,
                    'risk_adjusted_return': 0.8,
                    'plan_type': 'breakout_strategy',
                    'strategy': 'momentum'
                },
                'quality_score': 0.75
            },
            'dm': {
                'id': 'test_dm_001',
                'kind': 'trading_decision',
                'content': {
                    'outcome_quality': 0.7,
                    'risk_management_effectiveness': 0.8,
                    'decision_type': 'position_sizing',
                    'decision_factors': ['risk', 'volatility', 'correlation']
                }
            },
            'td': {
                'id': 'test_td_001',
                'kind': 'execution_outcome',
                'content': {
                    'execution_success': 0.9,
                    'slippage_minimization': 0.85,
                    'execution_method': 'twap',
                    'execution_strategy': 'adaptive'
                }
            }
        }
    
    def test_module_scores_calculation(self):
        """Test module-specific scores calculation"""
        for module_type, strand in self.sample_strands.items():
            result = self.scoring.calculate_module_scores(strand, module_type)
            
            # Check that all score values are present
            assert 'persistence_score' in result
            assert 'novelty_score' in result
            assert 'surprise_rating' in result
            assert 'module_type' in result
            assert 'calculated_at' in result
            
            # Check that values are in expected ranges
            assert 0.0 <= result['persistence_score'] <= 1.0
            assert 0.0 <= result['novelty_score'] <= 1.0
            assert 0.0 <= result['surprise_rating'] <= 1.0
            
            # Check module type is correct
            assert result['module_type'] == module_type
    
    def test_rdi_scores_calculation(self):
        """Test RDI-specific scores calculation"""
        strand = self.sample_strands['rdi']
        result = self.scoring.calculate_module_scores(strand, 'rdi')
        
        # RDI should have high persistence due to high confidence and sigma
        assert result['persistence_score'] > 0.5
        
        # RDI should have moderate novelty due to pattern type
        assert 0.0 <= result['novelty_score'] <= 1.0
        
        # RDI should have moderate surprise based on confidence vs strength
        assert 0.0 <= result['surprise_rating'] <= 1.0
    
    def test_cil_scores_calculation(self):
        """Test CIL-specific scores calculation"""
        strand = self.sample_strands['cil']
        result = self.scoring.calculate_module_scores(strand, 'cil')
        
        # CIL should have high persistence due to successful prediction
        assert result['persistence_score'] > 0.5
        
        # CIL should have moderate novelty due to method diversity
        assert 0.0 <= result['novelty_score'] <= 1.0
        
        # CIL should have moderate surprise based on return vs confidence
        assert 0.0 <= result['surprise_rating'] <= 1.0
    
    def test_ctp_scores_calculation(self):
        """Test CTP-specific scores calculation"""
        strand = self.sample_strands['ctp']
        result = self.scoring.calculate_module_scores(strand, 'ctp')
        
        # CTP should have moderate persistence based on profitability and risk
        assert 0.0 <= result['persistence_score'] <= 1.0
        
        # CTP should have moderate novelty based on plan type
        assert 0.0 <= result['novelty_score'] <= 1.0
        
        # CTP should have moderate surprise based on profitability vs risk
        assert 0.0 <= result['surprise_rating'] <= 1.0
    
    def test_dm_scores_calculation(self):
        """Test DM-specific scores calculation"""
        strand = self.sample_strands['dm']
        result = self.scoring.calculate_module_scores(strand, 'dm')
        
        # DM should have moderate persistence based on outcome quality
        assert 0.0 <= result['persistence_score'] <= 1.0
        
        # DM should have moderate novelty based on decision factors
        assert 0.0 <= result['novelty_score'] <= 1.0
        
        # DM should have moderate surprise based on outcome vs risk management
        assert 0.0 <= result['surprise_rating'] <= 1.0
    
    def test_td_scores_calculation(self):
        """Test TD-specific scores calculation"""
        strand = self.sample_strands['td']
        result = self.scoring.calculate_module_scores(strand, 'td')
        
        # TD should have high persistence due to high execution success
        assert result['persistence_score'] > 0.5
        
        # TD should have moderate novelty based on execution method
        assert 0.0 <= result['novelty_score'] <= 1.0
        
        # TD should have moderate surprise based on success vs slippage
        assert 0.0 <= result['surprise_rating'] <= 1.0
    
    def test_unknown_module_type(self):
        """Test handling of unknown module type"""
        strand = self.sample_strands['rdi']
        result = self.scoring.calculate_module_scores(strand, 'unknown')
        
        # Should return default values
        assert result['persistence_score'] == 0.5
        assert result['novelty_score'] == 0.5
        assert result['surprise_rating'] == 0.5
        assert 'error' in result


class TestHistoricalDataRetriever:
    """Test the historical data retrieval functions"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.retriever = HistoricalDataRetriever()
    
    @pytest.mark.asyncio
    async def test_get_historical_performance(self):
        """Test getting historical performance data"""
        for module_type in ['rdi', 'cil', 'ctp', 'dm', 'td']:
            result = await self.retriever.get_historical_performance(module_type)
            
            # Check that all expected fields are present
            assert 'accuracy' in result
            assert 'consistency' in result
            assert 'novelty' in result
            assert 'sample_size' in result
            assert 'improvement_rate' in result
            
            # Check that values are in expected ranges
            assert 0.0 <= result['accuracy'] <= 1.0
            assert 0.0 <= result['consistency'] <= 1.0
            assert 0.0 <= result['novelty'] <= 1.0
            assert result['sample_size'] > 0
            assert -1.0 <= result['improvement_rate'] <= 1.0
    
    @pytest.mark.asyncio
    async def test_get_cross_module_performance(self):
        """Test getting cross-module performance analysis"""
        result = await self.retriever.get_cross_module_performance()
        
        # Check that all expected fields are present
        assert 'module_performance' in result
        assert 'overall_accuracy' in result
        assert 'overall_consistency' in result
        assert 'overall_improvement_rate' in result
        assert 'analysis_period_days' in result
        
        # Check that module performance data is present for all modules
        assert len(result['module_performance']) == 5
        for module_type in ['rdi', 'cil', 'ctp', 'dm', 'td']:
            assert module_type in result['module_performance']
        
        # Check that overall metrics are reasonable
        assert 0.0 <= result['overall_accuracy'] <= 1.0
        assert 0.0 <= result['overall_consistency'] <= 1.0
        assert -1.0 <= result['overall_improvement_rate'] <= 1.0
    
    @pytest.mark.asyncio
    async def test_get_improvement_trends(self):
        """Test getting improvement trends for a module"""
        for module_type in ['rdi', 'cil', 'ctp', 'dm', 'td']:
            result = await self.retriever.get_improvement_trends(module_type)
            
            # Check that all expected fields are present
            assert 'module_type' in result
            assert 'trend_period_days' in result
            assert 'accuracy_trend' in result
            assert 'consistency_trend' in result
            assert 'novelty_trend' in result
            assert 'overall_trend' in result
            assert 'confidence_level' in result
            
            # Check that module type is correct
            assert result['module_type'] == module_type
            
            # Check that trend values are valid
            assert result['accuracy_trend'] in ['improving', 'stable', 'declining', 'unknown']
            assert result['consistency_trend'] in ['improving', 'stable', 'declining', 'unknown']
            assert result['novelty_trend'] in ['increasing', 'stable', 'decreasing', 'unknown']
            assert result['overall_trend'] in ['positive', 'neutral', 'negative', 'unknown']
            assert 0.0 <= result['confidence_level'] <= 1.0


class TestCentralizedLearningSystemIntegration:
    """Test the integrated centralized learning system"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Mock dependencies
        self.mock_supabase = Mock()
        self.mock_llm_client = Mock()
        self.mock_prompt_manager = Mock()
        
        # Create learning system
        self.learning_system = CentralizedLearningSystem(
            self.mock_supabase,
            self.mock_llm_client,
            self.mock_prompt_manager
        )
        
        # Sample strand data
        self.sample_strand = {
            'id': 'test_strand_001',
            'kind': 'pattern',
            'module_intelligence': {
                'pattern_type': 'diagonal_breakout',
                'success_rate': 0.75
            },
            'sig_confidence': 0.8,
            'sig_sigma': 0.7,
            'motif_family': 'trend_following'
        }
    
    def test_get_module_type_from_kind(self):
        """Test getting module type from strand kind"""
        # Test valid kinds
        assert self.learning_system._get_module_type_from_kind('pattern') == 'rdi'
        assert self.learning_system._get_module_type_from_kind('prediction_review') == 'cil'
        assert self.learning_system._get_module_type_from_kind('conditional_trading_plan') == 'ctp'
        assert self.learning_system._get_module_type_from_kind('trading_decision') == 'dm'
        assert self.learning_system._get_module_type_from_kind('execution_outcome') == 'td'
        
        # Test invalid kind
        assert self.learning_system._get_module_type_from_kind('unknown') is None
    
    @pytest.mark.asyncio
    async def test_calculate_module_scores(self):
        """Test calculating module scores for a strand"""
        # Mock the update method
        self.learning_system._update_strand_scores = AsyncMock()
        
        # Test with RDI strand
        await self.learning_system._calculate_module_scores(self.sample_strand)
        
        # Verify that update was called
        self.learning_system._update_strand_scores.assert_called_once()
        
        # Check that the call was made with correct parameters
        call_args = self.learning_system._update_strand_scores.call_args
        assert call_args[0][0] == 'test_strand_001'  # strand_id
        assert 'persistence_score' in call_args[0][1]  # scores
        assert 'resonance_scores' in call_args[0][2]  # resonance_scores
    
    @pytest.mark.asyncio
    async def test_update_strand_scores(self):
        """Test updating strand with calculated scores"""
        # Mock the database update
        mock_update = AsyncMock()
        self.mock_supabase.client.table.return_value.update.return_value.eq.return_value.execute = mock_update
        
        # Test data
        scores = {
            'persistence_score': 0.8,
            'novelty_score': 0.6,
            'surprise_rating': 0.4
        }
        resonance_scores = {
            'phi': 0.9,
            'rho': 0.7,
            'theta': 0.6,
            'omega': 1.1
        }
        
        # Call the method
        await self.learning_system._update_strand_scores('test_strand_001', scores, resonance_scores)
        
        # Verify that database update was called
        mock_update.assert_called_once()
        
        # Check that the update data contains expected fields
        call_args = self.mock_supabase.client.table.return_value.update.call_args
        update_data = call_args[0][0]
        
        assert update_data['persistence_score'] == 0.8
        assert update_data['novelty_score'] == 0.6
        assert update_data['surprise_rating'] == 0.4
        assert update_data['resonance_scores'] == resonance_scores
        assert 'updated_at' in update_data


class TestEndToEndIntegration:
    """Test end-to-end integration of the module-specific resonance system"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Mock dependencies
        self.mock_supabase = Mock()
        self.mock_llm_client = Mock()
        self.mock_prompt_manager = Mock()
        
        # Create learning system
        self.learning_system = CentralizedLearningSystem(
            self.mock_supabase,
            self.mock_llm_client,
            self.mock_prompt_manager
        )
        
        # Sample strands for each module type
        self.test_strands = {
            'rdi': {
                'id': 'test_rdi_001',
                'kind': 'pattern',
                'module_intelligence': {
                    'pattern_type': 'diagonal_breakout',
                    'success_rate': 0.75
                },
                'sig_confidence': 0.8,
                'sig_sigma': 0.7,
                'motif_family': 'trend_following'
            },
            'cil': {
                'id': 'test_cil_001',
                'kind': 'prediction_review',
                'content': {
                    'success': True,
                    'confidence': 0.85,
                    'return_pct': 0.12,
                    'method': 'ensemble'
                },
                'strategic_meta_type': 'meta_learning'
            },
            'ctp': {
                'id': 'test_ctp_001',
                'kind': 'conditional_trading_plan',
                'content': {
                    'profitability': 0.6,
                    'risk_adjusted_return': 0.8,
                    'plan_type': 'breakout_strategy',
                    'strategy': 'momentum'
                },
                'quality_score': 0.75
            },
            'dm': {
                'id': 'test_dm_001',
                'kind': 'trading_decision',
                'content': {
                    'outcome_quality': 0.7,
                    'risk_management_effectiveness': 0.8,
                    'decision_type': 'position_sizing',
                    'decision_factors': ['risk', 'volatility', 'correlation']
                }
            },
            'td': {
                'id': 'test_td_001',
                'kind': 'execution_outcome',
                'content': {
                    'execution_success': 0.9,
                    'slippage_minimization': 0.85,
                    'execution_method': 'twap',
                    'execution_strategy': 'adaptive'
                }
            }
        }
    
    def test_module_specific_resonance_integration(self):
        """Test that module-specific resonance calculations work correctly"""
        for module_type, strand in self.test_strands.items():
            # Test resonance engine
            resonance_result = self.learning_system.resonance_engine.calculate_module_resonance(
                strand, module_type
            )
            
            # Test module scoring
            scoring_result = self.learning_system.module_scoring.calculate_module_scores(
                strand, module_type
            )
            
            # Verify both results are valid
            assert 'phi' in resonance_result
            assert 'rho' in resonance_result
            assert 'theta' in resonance_result
            assert 'omega' in resonance_result
            
            assert 'persistence_score' in scoring_result
            assert 'novelty_score' in scoring_result
            assert 'surprise_rating' in scoring_result
            
            # Verify values are in expected ranges
            assert 0.0 <= resonance_result['phi'] <= 2.0
            assert 0.0 <= resonance_result['rho'] <= 2.0
            assert 0.0 <= resonance_result['theta'] <= 1.0
            assert 0.0 <= resonance_result['omega'] <= 2.0
            
            assert 0.0 <= scoring_result['persistence_score'] <= 1.0
            assert 0.0 <= scoring_result['novelty_score'] <= 1.0
            assert 0.0 <= scoring_result['surprise_rating'] <= 1.0
    
    @pytest.mark.asyncio
    async def test_historical_data_integration(self):
        """Test that historical data retrieval works correctly"""
        for module_type in ['rdi', 'cil', 'ctp', 'dm', 'td']:
            # Test historical performance
            historical_result = await self.learning_system.module_scoring.get_historical_module_performance(
                module_type
            )
            
            # Verify result is valid
            assert 'accuracy' in historical_result
            assert 'consistency' in historical_result
            assert 'novelty' in historical_result
            assert 'sample_size' in historical_result
            assert 'improvement_rate' in historical_result
            
            # Verify values are in expected ranges
            assert 0.0 <= historical_result['accuracy'] <= 1.0
            assert 0.0 <= historical_result['consistency'] <= 1.0
            assert 0.0 <= historical_result['novelty'] <= 1.0
            assert historical_result['sample_size'] > 0
            assert -1.0 <= historical_result['improvement_rate'] <= 1.0


if __name__ == '__main__':
    # Run the tests
    pytest.main([__file__, '-v'])
