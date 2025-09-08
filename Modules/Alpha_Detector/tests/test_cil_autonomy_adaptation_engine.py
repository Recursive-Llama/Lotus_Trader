"""
Test CIL Autonomy & Adaptation Engine
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.intelligence.system_control.central_intelligence_layer.engines.autonomy_adaptation_engine import (
    AutonomyAdaptationEngine, AutonomyLevel, AdaptationType, SelfReflection, 
    AdaptiveFocus, AgentCalibration
)


class TestAutonomyAdaptationEngine:
    """Test CIL Autonomy & Adaptation Engine"""
    
    @pytest.fixture
    def mock_supabase_manager(self):
        """Mock SupabaseManager"""
        manager = Mock()
        manager.execute_query = AsyncMock()
        manager.insert_strand = AsyncMock()
        return manager
    
    @pytest.fixture
    def mock_llm_client(self):
        """Mock OpenRouterClient"""
        return Mock()
    
    @pytest.fixture
    def adaptation_engine(self, mock_supabase_manager, mock_llm_client):
        """Create AutonomyAdaptationEngine instance"""
        return AutonomyAdaptationEngine(mock_supabase_manager, mock_llm_client)
    
    @pytest.fixture
    def mock_learning_results(self):
        """Mock learning results"""
        return {
            'improvement_assessment': {
                'improvement_metrics': {
                    'system_learning_rate': 0.8,
                    'doctrine_evolution_rate': 0.6,
                    'pattern_discovery_rate': 0.7,
                    'knowledge_retention_rate': 0.9
                },
                'system_sharpening': {
                    'accuracy_improvement': 0.8,
                    'efficiency_improvement': 0.7,
                    'novelty_improvement': 0.6,
                    'resilience_improvement': 0.75
                }
            },
            'doctrine_updates': [
                Mock(
                    update_type='promote',
                    pattern_family='divergence',
                    rationale='Test rationale',
                    evidence=['LESSON_123'],
                    confidence_level=0.9
                )
            ],
            'experiment_ideas': [{'trigger': 'test_trigger'}],
            'experiment_designs': [{'experiment_id': 'EXP_123'}],
            'experiment_assignments': [{'assignment_id': 'ASSIGN_123'}]
        }
    
    def test_adaptation_engine_initialization(self, adaptation_engine):
        """Test AutonomyAdaptationEngine initialization"""
        assert adaptation_engine.supabase_manager is not None
        assert adaptation_engine.llm_client is not None
        assert adaptation_engine.reflection_interval_hours == 6
        assert adaptation_engine.adaptation_threshold == 0.7
        assert adaptation_engine.autonomy_adjustment_rate == 0.1
        assert adaptation_engine.focus_shift_threshold == 0.8
        assert adaptation_engine.doctrine_evolution_rate == 0.05
        assert 'raw_data_intelligence' in adaptation_engine.agent_capabilities
        assert 'indicator_intelligence' in adaptation_engine.agent_capabilities
        assert 'pattern_intelligence' in adaptation_engine.agent_capabilities
        assert 'system_control' in adaptation_engine.agent_capabilities
    
    @pytest.mark.asyncio
    async def test_process_autonomy_adaptation_success(self, adaptation_engine, mock_learning_results):
        """Test successful autonomy adaptation processing"""
        # Mock the individual adaptation methods
        with patch.object(adaptation_engine, 'perform_self_reflection') as mock_reflection, \
             patch.object(adaptation_engine, 'adapt_focus_dynamically') as mock_focus, \
             patch.object(adaptation_engine, 'evolve_doctrine') as mock_doctrine, \
             patch.object(adaptation_engine, 'calibrate_agents') as mock_calibrate, \
             patch.object(adaptation_engine, 'assess_resilience_to_change') as mock_resilience:
            
            # Set up mock returns
            mock_reflection.return_value = [{'reflection_id': 'REFLECTION_1'}]
            mock_focus.return_value = [{'focus_id': 'FOCUS_1'}]
            mock_doctrine.return_value = [{'evolution_id': 'EVOL_1'}]
            mock_calibrate.return_value = [{'agent_id': 'raw_data_intelligence'}]
            mock_resilience.return_value = {'resilience_score': 0.8}
            
            # Process autonomy adaptation
            result = await adaptation_engine.process_autonomy_adaptation(mock_learning_results)
            
            # Verify structure
            assert 'self_reflections' in result
            assert 'adaptive_focus' in result
            assert 'doctrine_evolution' in result
            assert 'agent_calibrations' in result
            assert 'resilience_assessment' in result
            assert 'adaptation_timestamp' in result
            assert 'adaptation_errors' in result
            
            # Verify processing timestamp
            assert isinstance(result['adaptation_timestamp'], datetime)
    
    @pytest.mark.asyncio
    async def test_perform_self_reflection(self, adaptation_engine, mock_learning_results):
        """Test self-reflection performance"""
        # Perform self-reflection
        reflections = await adaptation_engine.perform_self_reflection(mock_learning_results)
        
        # Verify results
        assert isinstance(reflections, list)
        assert len(reflections) == 1
        
        reflection = reflections[0]
        assert isinstance(reflection, SelfReflection)
        assert reflection.reflection_id.startswith('REFLECTION_')
        assert reflection.reflection_type == 'orchestration_review'
        assert isinstance(reflection.orchestration_choices, dict)
        assert isinstance(reflection.performance_metrics, dict)
        assert isinstance(reflection.improvement_areas, list)
        assert isinstance(reflection.adaptation_recommendations, list)
        assert 0.0 <= reflection.confidence_level <= 1.0
        assert isinstance(reflection.created_at, datetime)
        
        # Verify orchestration choices
        assert 'experiment_ideas_generated' in reflection.orchestration_choices
        assert 'experiment_designs_created' in reflection.orchestration_choices
        assert 'experiment_assignments_made' in reflection.orchestration_choices
        assert 'doctrine_updates_generated' in reflection.orchestration_choices
        
        # Verify performance metrics
        assert 'learning_rate' in reflection.performance_metrics
        assert 'doctrine_evolution_rate' in reflection.performance_metrics
        assert 'pattern_discovery_rate' in reflection.performance_metrics
        assert 'knowledge_retention_rate' in reflection.performance_metrics
        assert 'accuracy_improvement' in reflection.performance_metrics
        assert 'efficiency_improvement' in reflection.performance_metrics
        assert 'novelty_improvement' in reflection.performance_metrics
        assert 'resilience_improvement' in reflection.performance_metrics
    
    @pytest.mark.asyncio
    async def test_adapt_focus_dynamically(self, adaptation_engine, mock_learning_results):
        """Test dynamic focus adaptation"""
        # Mock _analyze_pattern_families
        with patch.object(adaptation_engine, '_analyze_pattern_families') as mock_analyze:
            mock_analyze.return_value = {
                'divergence': {'performance': 0.9, 'novelty': 0.8, 'persistence': 0.9},
                'volume_analysis': {'performance': 0.6, 'novelty': 0.7, 'persistence': 0.6}
            }
            
            # Adapt focus dynamically
            adaptive_focuses = await adaptation_engine.adapt_focus_dynamically(mock_learning_results)
            
            # Verify results
            assert isinstance(adaptive_focuses, list)
            assert len(adaptive_focuses) >= 1  # Should have at least one focus adaptation
            
            focus = adaptive_focuses[0]
            assert isinstance(focus, AdaptiveFocus)
            assert focus.focus_id.startswith('FOCUS_')
            assert focus.pattern_family in ['divergence', 'volume_analysis', 'correlation_analysis', 'pattern_recognition']
            assert 0.0 <= focus.exploration_budget <= 1.0
            assert 0.0 <= focus.priority_score <= 1.0
            assert isinstance(focus.adaptation_rationale, str)
            assert focus.time_horizon == '24_hours'
            assert isinstance(focus.success_metrics, dict)
            assert isinstance(focus.created_at, datetime)
    
    @pytest.mark.asyncio
    async def test_evolve_doctrine(self, adaptation_engine, mock_learning_results):
        """Test doctrine evolution"""
        # Evolve doctrine
        evolutions = await adaptation_engine.evolve_doctrine(mock_learning_results)
        
        # Verify results
        assert isinstance(evolutions, list)
        assert len(evolutions) == 1  # One doctrine update should generate one evolution
        
        evolution = evolutions[0]
        assert isinstance(evolution, dict)
        assert evolution['evolution_id'].startswith('DOCTRINE_EVOL_')
        assert evolution['evolution_type'] == 'doctrine_affirmation'
        assert evolution['pattern_family'] == 'divergence'
        assert evolution['rationale'] == 'Test rationale'
        assert evolution['evidence'] == ['LESSON_123']
        assert evolution['confidence_level'] == 0.9
        assert evolution['evolution_rate'] == 0.05
        assert isinstance(evolution['created_at'], datetime)
    
    @pytest.mark.asyncio
    async def test_calibrate_agents(self, adaptation_engine, mock_learning_results):
        """Test agent calibration"""
        # Mock _calculate_agent_metrics and _needs_calibration
        with patch.object(adaptation_engine, '_calculate_agent_metrics') as mock_metrics, \
             patch.object(adaptation_engine, '_needs_calibration') as mock_needs:
            
            # Set up mock returns
            mock_metrics.return_value = {
                'performance_score': 0.6,  # Below threshold
                'accuracy': 0.7,
                'efficiency': 0.6,
                'novelty': 0.7,
                'resilience': 0.75
            }
            mock_needs.return_value = True  # Needs calibration
            
            # Calibrate agents
            calibrations = await adaptation_engine.calibrate_agents(mock_learning_results)
            
            # Verify results
            assert isinstance(calibrations, list)
            assert len(calibrations) == 4  # One for each agent
            
            calibration = calibrations[0]
            assert isinstance(calibration, AgentCalibration)
            assert calibration.agent_id in ['raw_data_intelligence', 'indicator_intelligence', 'pattern_intelligence', 'system_control']
            assert calibration.autonomy_level in [AutonomyLevel.STRICT, AutonomyLevel.BOUNDED, AutonomyLevel.EXPLORATORY]
            assert isinstance(calibration.threshold_settings, dict)
            assert 0.0 <= calibration.exploration_budget <= 1.0
            assert isinstance(calibration.performance_targets, dict)
            assert isinstance(calibration.calibration_rationale, str)
            assert isinstance(calibration.created_at, datetime)
            
            # Verify threshold settings
            assert 'confidence_threshold' in calibration.threshold_settings
            assert 'similarity_threshold' in calibration.threshold_settings
            assert 'success_threshold' in calibration.threshold_settings
            
            # Verify performance targets
            assert 'accuracy_target' in calibration.performance_targets
            assert 'efficiency_target' in calibration.performance_targets
            assert 'novelty_target' in calibration.performance_targets
            assert 'resilience_target' in calibration.performance_targets
    
    @pytest.mark.asyncio
    async def test_assess_resilience_to_change(self, adaptation_engine, mock_learning_results):
        """Test resilience to change assessment"""
        # Mock _assess_regime_shift_resilience and _generate_resilience_recommendations
        with patch.object(adaptation_engine, '_assess_regime_shift_resilience') as mock_assess, \
             patch.object(adaptation_engine, '_generate_resilience_recommendations') as mock_recommendations:
            
            # Set up mock returns
            mock_assess.return_value = {
                'resilience_score': 0.8,
                'adaptation_capability': 0.7,
                'learning_persistence': 0.8,
                'pattern_stability': 0.9,
                'system_flexibility': 0.75
            }
            mock_recommendations.return_value = ['Improve system resilience', 'Increase adaptation rate']
            
            # Assess resilience to change
            assessment = await adaptation_engine.assess_resilience_to_change(mock_learning_results)
            
            # Verify results
            assert isinstance(assessment, dict)
            assert 'resilience_metrics' in assessment
            assert 'regime_resilience' in assessment
            assert 'resilience_recommendations' in assessment
            assert 'assessment_timestamp' in assessment
            
            # Verify resilience metrics
            metrics = assessment['resilience_metrics']
            assert 'adaptation_rate' in metrics
            assert 'learning_persistence' in metrics
            assert 'pattern_stability' in metrics
            assert 'system_flexibility' in metrics
            
            # Verify regime resilience
            regime_resilience = assessment['regime_resilience']
            assert 'resilience_score' in regime_resilience
            assert 'adaptation_capability' in regime_resilience
            assert 'learning_persistence' in regime_resilience
            assert 'pattern_stability' in regime_resilience
            assert 'system_flexibility' in regime_resilience
            
            # Verify recommendations
            recommendations = assessment['resilience_recommendations']
            assert isinstance(recommendations, list)
            assert len(recommendations) == 2
    
    def test_identify_improvement_areas(self, adaptation_engine):
        """Test improvement area identification"""
        # Test with low performance metrics
        performance_metrics = {
            'learning_rate': 0.3,
            'doctrine_evolution_rate': 0.2,
            'pattern_discovery_rate': 0.3,
            'accuracy_improvement': 0.5,
            'efficiency_improvement': 0.4
        }
        
        areas = adaptation_engine._identify_improvement_areas(performance_metrics)
        
        assert isinstance(areas, list)
        assert len(areas) == 5  # All areas should be identified
        assert 'learning_rate' in areas
        assert 'doctrine_evolution' in areas
        assert 'pattern_discovery' in areas
        assert 'accuracy' in areas
        assert 'efficiency' in areas
        
        # Test with high performance metrics
        performance_metrics = {
            'learning_rate': 0.8,
            'doctrine_evolution_rate': 0.7,
            'pattern_discovery_rate': 0.8,
            'accuracy_improvement': 0.9,
            'efficiency_improvement': 0.8
        }
        
        areas = adaptation_engine._identify_improvement_areas(performance_metrics)
        
        assert isinstance(areas, list)
        assert len(areas) == 0  # No areas should be identified
    
    @pytest.mark.asyncio
    async def test_generate_adaptation_recommendations(self, adaptation_engine):
        """Test adaptation recommendations generation"""
        performance_metrics = {
            'learning_rate': 0.3,
            'doctrine_evolution_rate': 0.2,
            'pattern_discovery_rate': 0.3,
            'accuracy_improvement': 0.5,
            'efficiency_improvement': 0.4
        }
        
        improvement_areas = ['learning_rate', 'doctrine_evolution', 'pattern_discovery', 'accuracy', 'efficiency']
        
        recommendations = await adaptation_engine._generate_adaptation_recommendations(
            performance_metrics, improvement_areas
        )
        
        assert isinstance(recommendations, list)
        assert len(recommendations) == 5
        
        # Check specific recommendations
        assert any('learning rate' in rec for rec in recommendations)
        assert any('doctrine evolution' in rec for rec in recommendations)
        assert any('pattern discovery' in rec for rec in recommendations)
        assert any('accuracy' in rec for rec in recommendations)
        assert any('efficiency' in rec for rec in recommendations)
    
    def test_calculate_reflection_confidence(self, adaptation_engine):
        """Test reflection confidence calculation"""
        # Test with high performance metrics
        performance_metrics = {
            'learning_rate': 0.8,
            'doctrine_evolution_rate': 0.7,
            'pattern_discovery_rate': 0.8,
            'accuracy_improvement': 0.9,
            'efficiency_improvement': 0.8
        }
        
        confidence = adaptation_engine._calculate_reflection_confidence(performance_metrics)
        
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.7  # Should be high confidence
        
        # Test with low performance metrics
        performance_metrics = {
            'learning_rate': 0.3,
            'doctrine_evolution_rate': 0.2,
            'pattern_discovery_rate': 0.3,
            'accuracy_improvement': 0.5,
            'efficiency_improvement': 0.4
        }
        
        confidence = adaptation_engine._calculate_reflection_confidence(performance_metrics)
        
        assert 0.0 <= confidence <= 1.0
        assert confidence < 0.5  # Should be low confidence
    
    def test_analyze_pattern_families(self, adaptation_engine):
        """Test pattern family analysis"""
        learning_results = {'test': 'data'}
        
        families = adaptation_engine._analyze_pattern_families(learning_results)
        
        assert isinstance(families, dict)
        assert 'divergence' in families
        assert 'volume_analysis' in families
        assert 'correlation_analysis' in families
        assert 'pattern_recognition' in families
        
        # Verify family structure
        for family, metrics in families.items():
            assert isinstance(metrics, dict)
            assert 'performance' in metrics
            assert 'novelty' in metrics
            assert 'persistence' in metrics
            assert 0.0 <= metrics['performance'] <= 1.0
            assert 0.0 <= metrics['novelty'] <= 1.0
            assert 0.0 <= metrics['persistence'] <= 1.0
    
    def test_calculate_family_priority(self, adaptation_engine):
        """Test family priority calculation"""
        metrics = {
            'performance': 0.8,
            'novelty': 0.7,
            'persistence': 0.9
        }
        
        system_sharpening = {
            'accuracy_improvement': 0.8,
            'novelty_improvement': 0.6
        }
        
        priority = adaptation_engine._calculate_family_priority(metrics, system_sharpening)
        
        assert 0.0 <= priority <= 1.0
        assert priority > 0.7  # Should be high priority
        
        # Test with low metrics
        metrics = {
            'performance': 0.3,
            'novelty': 0.2,
            'persistence': 0.4
        }
        
        priority = adaptation_engine._calculate_family_priority(metrics, system_sharpening)
        
        assert 0.0 <= priority <= 1.0
        assert priority < 0.5  # Should be low priority
    
    def test_calculate_adaptive_budget(self, adaptation_engine):
        """Test adaptive budget calculation"""
        # Test with high priority
        current_budget = 0.3
        priority_score = 0.9
        
        new_budget = adaptation_engine._calculate_adaptive_budget(current_budget, priority_score)
        
        assert 0.1 <= new_budget <= 0.5
        assert new_budget > current_budget  # Should increase
        
        # Test with low priority
        priority_score = 0.2
        
        new_budget = adaptation_engine._calculate_adaptive_budget(current_budget, priority_score)
        
        assert 0.1 <= new_budget <= 0.5
        assert new_budget < current_budget  # Should decrease
        
        # Test boundary conditions
        current_budget = 0.1
        priority_score = 0.2
        
        new_budget = adaptation_engine._calculate_adaptive_budget(current_budget, priority_score)
        
        assert new_budget >= 0.1  # Should not go below minimum
        
        current_budget = 0.5
        priority_score = 0.9
        
        new_budget = adaptation_engine._calculate_adaptive_budget(current_budget, priority_score)
        
        assert new_budget <= 0.5  # Should not go above maximum
    
    def test_generate_focus_rationale(self, adaptation_engine):
        """Test focus rationale generation"""
        family = 'divergence'
        metrics = {
            'performance': 0.8,
            'novelty': 0.7,
            'persistence': 0.9
        }
        priority_score = 0.85
        
        rationale = adaptation_engine._generate_focus_rationale(family, metrics, priority_score)
        
        assert isinstance(rationale, str)
        assert family in rationale
        assert str(priority_score) in rationale
        assert str(metrics['performance']) in rationale
        assert str(metrics['novelty']) in rationale
        assert str(metrics['persistence']) in rationale
    
    def test_determine_doctrine_evolution_type(self, adaptation_engine):
        """Test doctrine evolution type determination"""
        # Test promote
        update = Mock(update_type='promote')
        evolution_type = adaptation_engine._determine_doctrine_evolution_type(update)
        assert evolution_type == 'doctrine_affirmation'
        
        # Test retire
        update = Mock(update_type='retire')
        evolution_type = adaptation_engine._determine_doctrine_evolution_type(update)
        assert evolution_type == 'doctrine_retirement'
        
        # Test refine
        update = Mock(update_type='refine')
        evolution_type = adaptation_engine._determine_doctrine_evolution_type(update)
        assert evolution_type == 'doctrine_refinement'
        
        # Test contraindicate
        update = Mock(update_type='contraindicate')
        evolution_type = adaptation_engine._determine_doctrine_evolution_type(update)
        assert evolution_type == 'doctrine_contraindication'
        
        # Test unknown
        update = Mock(update_type='unknown')
        evolution_type = adaptation_engine._determine_doctrine_evolution_type(update)
        assert evolution_type is None
    
    def test_calculate_agent_metrics(self, adaptation_engine):
        """Test agent metrics calculation"""
        agent_id = 'raw_data_intelligence'
        learning_results = {'test': 'data'}
        
        metrics = adaptation_engine._calculate_agent_metrics(agent_id, learning_results)
        
        assert isinstance(metrics, dict)
        assert 'performance_score' in metrics
        assert 'accuracy' in metrics
        assert 'efficiency' in metrics
        assert 'novelty' in metrics
        assert 'resilience' in metrics
        
        # Verify metric ranges
        for metric, value in metrics.items():
            assert 0.0 <= value <= 1.0
    
    def test_needs_calibration(self, adaptation_engine):
        """Test calibration need assessment"""
        # Test needs calibration
        agent_metrics = {'performance_score': 0.6}
        system_sharpening = {}
        
        needs = adaptation_engine._needs_calibration(agent_metrics, system_sharpening)
        assert needs is True
        
        # Test doesn't need calibration
        agent_metrics = {'performance_score': 0.8}
        
        needs = adaptation_engine._needs_calibration(agent_metrics, system_sharpening)
        assert needs is False
    
    def test_calculate_adaptive_autonomy(self, adaptation_engine):
        """Test adaptive autonomy calculation"""
        agent_id = 'raw_data_intelligence'
        
        # Test high performance
        agent_metrics = {'performance_score': 0.9}
        autonomy = adaptation_engine._calculate_adaptive_autonomy(agent_id, agent_metrics)
        assert autonomy == AutonomyLevel.EXPLORATORY
        
        # Test medium performance
        agent_metrics = {'performance_score': 0.7}
        autonomy = adaptation_engine._calculate_adaptive_autonomy(agent_id, agent_metrics)
        assert autonomy == AutonomyLevel.BOUNDED
        
        # Test low performance
        agent_metrics = {'performance_score': 0.5}
        autonomy = adaptation_engine._calculate_adaptive_autonomy(agent_id, agent_metrics)
        assert autonomy == AutonomyLevel.STRICT
    
    def test_calculate_adaptive_thresholds(self, adaptation_engine):
        """Test adaptive threshold calculation"""
        agent_id = 'raw_data_intelligence'
        
        # Test high performance
        agent_metrics = {'performance_score': 0.9}
        thresholds = adaptation_engine._calculate_adaptive_thresholds(agent_id, agent_metrics)
        
        assert isinstance(thresholds, dict)
        assert 'confidence_threshold' in thresholds
        assert 'similarity_threshold' in thresholds
        assert 'success_threshold' in thresholds
        
        # Verify threshold ranges
        for threshold, value in thresholds.items():
            assert 0.0 <= value <= 1.0
        
        # Test low performance
        agent_metrics = {'performance_score': 0.3}
        thresholds = adaptation_engine._calculate_adaptive_thresholds(agent_id, agent_metrics)
        
        # Low performance should result in lower thresholds
        assert thresholds['confidence_threshold'] < 0.7
    
    def test_generate_calibration_rationale(self, adaptation_engine):
        """Test calibration rationale generation"""
        agent_id = 'raw_data_intelligence'
        agent_metrics = {'performance_score': 0.7}
        autonomy_level = AutonomyLevel.BOUNDED
        thresholds = {'confidence_threshold': 0.8, 'similarity_threshold': 0.7, 'success_threshold': 0.8}
        
        rationale = adaptation_engine._generate_calibration_rationale(
            agent_id, agent_metrics, autonomy_level, thresholds
        )
        
        assert isinstance(rationale, str)
        assert agent_id in rationale
        assert autonomy_level.value in rationale
        assert str(agent_metrics['performance_score']) in rationale
    
    def test_assess_regime_shift_resilience(self, adaptation_engine):
        """Test regime shift resilience assessment"""
        resilience_metrics = {
            'adaptation_rate': 0.8,
            'learning_persistence': 0.7,
            'pattern_stability': 0.9,
            'system_flexibility': 0.75
        }
        
        assessment = adaptation_engine._assess_regime_shift_resilience(resilience_metrics)
        
        assert isinstance(assessment, dict)
        assert 'resilience_score' in assessment
        assert 'adaptation_capability' in assessment
        assert 'learning_persistence' in assessment
        assert 'pattern_stability' in assessment
        assert 'system_flexibility' in assessment
        
        # Verify resilience score calculation
        expected_score = (0.8 + 0.7 + 0.9 + 0.75) / 4
        assert abs(assessment['resilience_score'] - expected_score) < 0.001
        
        # Verify individual metrics
        assert assessment['adaptation_capability'] == 0.8
        assert assessment['learning_persistence'] == 0.7
        assert assessment['pattern_stability'] == 0.9
        assert assessment['system_flexibility'] == 0.75
    
    @pytest.mark.asyncio
    async def test_generate_resilience_recommendations(self, adaptation_engine):
        """Test resilience recommendations generation"""
        resilience_metrics = {
            'adaptation_rate': 0.3,
            'learning_persistence': 0.6,
            'pattern_stability': 0.8,
            'system_flexibility': 0.7
        }
        
        regime_resilience = {
            'resilience_score': 0.6,
            'adaptation_capability': 0.3,
            'learning_persistence': 0.6,
            'pattern_stability': 0.8,
            'system_flexibility': 0.7
        }
        
        recommendations = await adaptation_engine._generate_resilience_recommendations(
            resilience_metrics, regime_resilience
        )
        
        assert isinstance(recommendations, list)
        assert len(recommendations) >= 1  # Should have at least one recommendation
        
        # Check for specific recommendations
        assert any('adaptation' in rec.lower() for rec in recommendations)
        assert any('learning persistence' in rec.lower() for rec in recommendations)
    
    @pytest.mark.asyncio
    async def test_publish_adaptation_results(self, adaptation_engine, mock_supabase_manager):
        """Test publishing adaptation results"""
        adaptation_results = {
            'self_reflections': [{'reflection_id': 'REFLECTION_1'}],
            'adaptive_focus': [{'focus_id': 'FOCUS_1'}],
            'doctrine_evolution': [{'evolution_id': 'EVOL_1'}],
            'agent_calibrations': [{'agent_id': 'raw_data_intelligence'}],
            'resilience_assessment': {'resilience_score': 0.8},
            'adaptation_errors': []
        }
        
        await adaptation_engine._publish_adaptation_results(adaptation_results)
        
        # Verify strand was inserted
        mock_supabase_manager.insert_strand.assert_called_once()
        call_args = mock_supabase_manager.insert_strand.call_args[0][0]
        assert call_args['kind'] == 'cil_autonomy_adaptation'
        assert call_args['agent_id'] == 'central_intelligence_layer'
        assert call_args['cil_team_member'] == 'autonomy_adaptation_engine'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
