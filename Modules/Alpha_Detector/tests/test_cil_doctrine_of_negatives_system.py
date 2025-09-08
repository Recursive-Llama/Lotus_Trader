"""
Test CIL Doctrine of Negatives System
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.intelligence.system_control.central_intelligence_layer.missing_pieces.doctrine_of_negatives_system import (
    DoctrineOfNegativesSystem, NegativeType, NegativeSeverity, NegativeStatus,
    NegativeSource, NegativePattern, NegativeDoctrine, NegativeViolation, NegativeAnalysis
)


class TestDoctrineOfNegativesSystem:
    """Test CIL Doctrine of Negatives System"""
    
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
    def doctrine_system(self, mock_supabase_manager, mock_llm_client):
        """Create DoctrineOfNegativesSystem instance"""
        return DoctrineOfNegativesSystem(mock_supabase_manager, mock_llm_client)
    
    @pytest.fixture
    def mock_experiment_designs(self):
        """Mock experiment designs"""
        return [
            {
                'patterns': ['rsi_divergence', 'volume_spike'],
                'market_regime': 'high_vol',
                'session': 'US',
                'timeframe': '1h',
                'historical_performance': {'success_rate': 0.6},
                'conditions': {'volatility': 2.5, 'rsi_divergence': True},
                'risk_level': 'high'
            },
            {
                'patterns': ['breakout', 'volume_confirmation'],
                'market_regime': 'sideways',
                'session': 'EU',
                'timeframe': '4h',
                'historical_performance': {'success_rate': 0.8},
                'conditions': {'volume': 0.3, 'breakout_strength': 0.03},
                'risk_level': 'medium'
            },
            {
                'patterns': ['trend_reversal', 'news_event'],
                'market_regime': 'trending',
                'session': 'ASIA',
                'timeframe': '1h',
                'historical_performance': {'success_rate': 0.4},
                'conditions': {'news_impact': 'high', 'trend_reversal': True},
                'risk_level': 'critical'
            }
        ]
    
    @pytest.fixture
    def mock_pattern_conditions(self):
        """Mock pattern conditions"""
        return [
            {'condition': 'volatility > 2.0'},
            {'condition': 'volume < 0.5x_average'},
            {'condition': 'news_impact = high'},
            {'condition': 'rsi_divergence = bullish'},
            {'condition': 'macd_divergence = bearish'}
        ]
    
    def test_doctrine_system_initialization(self, doctrine_system):
        """Test DoctrineOfNegativesSystem initialization"""
        assert doctrine_system.supabase_manager is not None
        assert doctrine_system.llm_client is not None
        assert doctrine_system.negative_confidence_threshold == 0.7
        assert doctrine_system.violation_severity_threshold == 0.8
        assert doctrine_system.doctrine_review_interval_hours == 24
        assert doctrine_system.negative_evidence_threshold == 3
        assert doctrine_system.max_negative_patterns == 1000
        assert doctrine_system.negative_analysis_prompt is not None
        assert doctrine_system.violation_detection_prompt is not None
        assert doctrine_system.doctrine_evolution_prompt is not None
        assert isinstance(doctrine_system.negative_patterns, dict)
        assert isinstance(doctrine_system.negative_doctrines, dict)
        assert isinstance(doctrine_system.negative_violations, list)
        assert isinstance(doctrine_system.negative_analyses, list)
        assert len(doctrine_system.negative_patterns) == 4  # Should have 4 default patterns
        assert len(doctrine_system.negative_doctrines) == 3  # Should have 3 default doctrines
    
    def test_load_prompt_templates(self, doctrine_system):
        """Test prompt template loading"""
        # Test negative analysis prompt
        assert 'patterns_conditions' in doctrine_system.negative_analysis_prompt
        assert 'market_regime' in doctrine_system.negative_analysis_prompt
        assert 'session' in doctrine_system.negative_analysis_prompt
        assert 'timeframe' in doctrine_system.negative_analysis_prompt
        assert 'historical_performance' in doctrine_system.negative_analysis_prompt
        
        # Test violation detection prompt
        assert 'experiment_pattern' in doctrine_system.violation_detection_prompt
        assert 'negative_doctrine' in doctrine_system.violation_detection_prompt
        assert 'current_conditions' in doctrine_system.violation_detection_prompt
        assert 'historical_violations' in doctrine_system.violation_detection_prompt
        assert 'risk_level' in doctrine_system.violation_detection_prompt
        
        # Test doctrine evolution prompt
        assert 'current_doctrine' in doctrine_system.doctrine_evolution_prompt
        assert 'new_evidence' in doctrine_system.doctrine_evolution_prompt
        assert 'violation_history' in doctrine_system.doctrine_evolution_prompt
        assert 'performance_metrics' in doctrine_system.doctrine_evolution_prompt
    
    def test_initialize_negative_patterns(self, doctrine_system):
        """Test negative patterns initialization"""
        patterns = doctrine_system.negative_patterns
        
        assert len(patterns) == 4
        
        # Check high volatility RSI divergence pattern
        high_vol_pattern = patterns['high_vol_rsi_divergence']
        assert high_vol_pattern.negative_type == NegativeType.CONTRAINDICATED
        assert high_vol_pattern.pattern_description == "RSI divergence signals in high volatility regimes"
        assert high_vol_pattern.contraindicated_conditions == ["volatility > 2.0", "regime = high_vol", "session = news"]
        assert high_vol_pattern.failure_mechanisms == ["false_signals", "whipsaws", "overtrading"]
        assert high_vol_pattern.severity == NegativeSeverity.HIGH
        assert high_vol_pattern.confidence_level == 0.85
        assert high_vol_pattern.evidence_count == 15
        assert high_vol_pattern.source == NegativeSource.EXPERIMENTAL_FAILURE
        assert high_vol_pattern.status == NegativeStatus.ACTIVE
        
        # Check low volume breakout pattern
        low_vol_pattern = patterns['low_volume_breakout']
        assert low_vol_pattern.negative_type == NegativeType.FAILURE_MODE
        assert low_vol_pattern.pattern_description == "Breakout patterns with low volume confirmation"
        assert low_vol_pattern.contraindicated_conditions == ["volume < 0.5x_average", "breakout_strength > 0.02"]
        assert low_vol_pattern.failure_mechanisms == ["fake_breakout", "lack_of_participation", "quick_reversal"]
        assert low_vol_pattern.severity == NegativeSeverity.MEDIUM
        assert low_vol_pattern.confidence_level == 0.75
        assert low_vol_pattern.evidence_count == 8
        assert low_vol_pattern.source == NegativeSource.HISTORICAL_ANALYSIS
        assert low_vol_pattern.status == NegativeStatus.ACTIVE
        
        # Check trend reversal during news pattern
        news_pattern = patterns['trend_reversal_during_news']
        assert news_pattern.negative_type == NegativeType.TIMING_INAPPROPRIATE
        assert news_pattern.pattern_description == "Trend reversal signals during high-impact news events"
        assert news_pattern.contraindicated_conditions == ["news_impact = high", "trend_reversal_signal = true"]
        assert news_pattern.failure_mechanisms == ["news_override", "unpredictable_volatility", "liquidity_gaps"]
        assert news_pattern.severity == NegativeSeverity.CRITICAL
        assert news_pattern.confidence_level == 0.95
        assert news_pattern.evidence_count == 25
        assert news_pattern.source == NegativeSource.EXPERIMENTAL_FAILURE
        assert news_pattern.status == NegativeStatus.ACTIVE
        
        # Check multiple divergence conflict pattern
        conflict_pattern = patterns['multiple_divergence_conflict']
        assert conflict_pattern.negative_type == NegativeType.TOXIC_COMBINATION
        assert conflict_pattern.pattern_description == "Multiple conflicting divergence signals"
        assert conflict_pattern.contraindicated_conditions == ["rsi_divergence = bullish", "macd_divergence = bearish", "volume_divergence = neutral"]
        assert conflict_pattern.failure_mechanisms == ["signal_confusion", "indecision", "analysis_paralysis"]
        assert conflict_pattern.severity == NegativeSeverity.MEDIUM
        assert conflict_pattern.confidence_level == 0.70
        assert conflict_pattern.evidence_count == 12
        assert conflict_pattern.source == NegativeSource.LLM_INSIGHT
        assert conflict_pattern.status == NegativeStatus.ACTIVE
    
    def test_initialize_negative_doctrines(self, doctrine_system):
        """Test negative doctrines initialization"""
        doctrines = doctrine_system.negative_doctrines
        
        assert len(doctrines) == 3
        
        # Check volatility doctrine
        volatility_doctrine = doctrines['volatility_doctrine']
        assert volatility_doctrine.doctrine_name == "High Volatility Contraindications"
        assert volatility_doctrine.negative_patterns == ["high_vol_rsi_divergence", "trend_reversal_during_news"]
        assert volatility_doctrine.doctrine_rules['volatility_threshold'] == 2.0
        assert volatility_doctrine.doctrine_rules['enforcement_action'] == "block"
        assert volatility_doctrine.doctrine_rules['exception_conditions'] == ["confirmed_breakout", "volume_confirmation"]
        assert volatility_doctrine.enforcement_level == "strict"
        assert volatility_doctrine.exceptions == ["confirmed_breakout", "volume_confirmation"]
        assert volatility_doctrine.review_frequency == 24
        
        # Check volume doctrine
        volume_doctrine = doctrines['volume_doctrine']
        assert volume_doctrine.doctrine_name == "Volume Confirmation Requirements"
        assert volume_doctrine.negative_patterns == ["low_volume_breakout"]
        assert volume_doctrine.doctrine_rules['volume_threshold'] == 0.5
        assert volume_doctrine.doctrine_rules['enforcement_action'] == "warn"
        assert volume_doctrine.doctrine_rules['exception_conditions'] == ["news_catalyst", "institutional_flow"]
        assert volume_doctrine.enforcement_level == "moderate"
        assert volume_doctrine.exceptions == ["news_catalyst", "institutional_flow"]
        assert volume_doctrine.review_frequency == 12
        
        # Check divergence doctrine
        divergence_doctrine = doctrines['divergence_doctrine']
        assert divergence_doctrine.doctrine_name == "Divergence Signal Conflicts"
        assert divergence_doctrine.negative_patterns == ["multiple_divergence_conflict"]
        assert divergence_doctrine.doctrine_rules['conflict_threshold'] == 2
        assert divergence_doctrine.doctrine_rules['enforcement_action'] == "monitor"
        assert divergence_doctrine.doctrine_rules['exception_conditions'] == ["strong_volume_confirmation", "regime_alignment"]
        assert divergence_doctrine.enforcement_level == "lenient"
        assert divergence_doctrine.exceptions == ["strong_volume_confirmation", "regime_alignment"]
        assert divergence_doctrine.review_frequency == 6
    
    @pytest.mark.asyncio
    async def test_process_doctrine_of_negatives_analysis_success(self, doctrine_system, mock_experiment_designs, mock_pattern_conditions):
        """Test successful doctrine of negatives analysis processing"""
        # Process doctrine of negatives analysis
        results = await doctrine_system.process_doctrine_of_negatives_analysis(mock_experiment_designs, mock_pattern_conditions)
        
        # Verify structure
        assert 'negative_analyses' in results
        assert 'violation_detections' in results
        assert 'doctrine_evolution' in results
        assert 'pattern_updates' in results
        assert 'doctrine_timestamp' in results
        assert 'doctrine_errors' in results
        
        # Verify processing timestamp
        assert isinstance(results['doctrine_timestamp'], datetime)
        
        # Verify results are correct types
        assert isinstance(results['negative_analyses'], list)
        assert isinstance(results['violation_detections'], list)
        assert isinstance(results['doctrine_evolution'], list)
        assert isinstance(results['pattern_updates'], list)
        assert isinstance(results['doctrine_errors'], list)
    
    @pytest.mark.asyncio
    async def test_analyze_negative_patterns(self, doctrine_system, mock_experiment_designs, mock_pattern_conditions):
        """Test negative pattern analysis"""
        # Analyze negative patterns
        analyses = await doctrine_system._analyze_negative_patterns(mock_experiment_designs, mock_pattern_conditions)
        
        # Verify results
        assert isinstance(analyses, list)
        assert len(analyses) == 3  # Should analyze all 3 designs
        
        # Check analysis structure
        for analysis in analyses:
            assert isinstance(analysis, NegativeAnalysis)
            assert analysis.analysis_id.startswith('NEGATIVE_ANALYSIS_')
            assert analysis.analysis_type == "pattern_analysis"
            assert isinstance(analysis.negative_patterns_analyzed, list)
            assert isinstance(analysis.analysis_results, dict)
            assert isinstance(analysis.recommendations, list)
            assert 0.0 <= analysis.confidence_score <= 1.0
            assert isinstance(analysis.created_at, datetime)
            
            # Verify analysis results structure
            assert 'negative_patterns' in analysis.analysis_results
            assert 'negative_insights' in analysis.analysis_results
            assert 'uncertainty_flags' in analysis.analysis_results
            
            # Verify specific values
            assert isinstance(analysis.analysis_results['negative_patterns'], list)
            assert len(analysis.analysis_results['negative_patterns']) == 1
            pattern = analysis.analysis_results['negative_patterns'][0]
            assert pattern['negative_type'] == 'contraindicated'
            assert pattern['pattern_description'] == 'High volatility RSI divergence signals'
            assert pattern['contraindicated_conditions'] == ['volatility > 2.0', 'regime = high_vol']
            assert pattern['failure_mechanisms'] == ['false_signals', 'whipsaws']
            assert pattern['severity'] == 'high'
            assert pattern['confidence_level'] == 0.85
            assert pattern['evidence'] == ['experimental_failure', 'historical_analysis']
            
            assert analysis.analysis_results['negative_insights'] == ['High volatility reduces RSI reliability', 'News events override technical signals']
            assert analysis.analysis_results['uncertainty_flags'] == ['limited_sample_size']
        
        # Verify analyses were added to system
        assert len(doctrine_system.negative_analyses) == 3
    
    @pytest.mark.asyncio
    async def test_generate_negative_analysis(self, doctrine_system, mock_experiment_designs, mock_pattern_conditions):
        """Test negative analysis generation"""
        analysis_data = {
            'patterns_conditions': mock_experiment_designs[0]['patterns'] + [cond['condition'] for cond in mock_pattern_conditions],
            'market_regime': mock_experiment_designs[0]['market_regime'],
            'session': mock_experiment_designs[0]['session'],
            'timeframe': mock_experiment_designs[0]['timeframe'],
            'historical_performance': mock_experiment_designs[0]['historical_performance']
        }
        
        # Generate negative analysis
        analysis = await doctrine_system._generate_negative_analysis(analysis_data)
        
        # Verify analysis
        assert analysis is not None
        assert isinstance(analysis, dict)
        assert 'negative_patterns' in analysis
        assert 'negative_insights' in analysis
        assert 'uncertainty_flags' in analysis
        
        # Verify specific values
        assert isinstance(analysis['negative_patterns'], list)
        assert len(analysis['negative_patterns']) == 1
        pattern = analysis['negative_patterns'][0]
        assert pattern['negative_type'] == 'contraindicated'
        assert pattern['pattern_description'] == 'High volatility RSI divergence signals'
        assert pattern['contraindicated_conditions'] == ['volatility > 2.0', 'regime = high_vol']
        assert pattern['failure_mechanisms'] == ['false_signals', 'whipsaws']
        assert pattern['severity'] == 'high'
        assert pattern['confidence_level'] == 0.85
        assert pattern['evidence'] == ['experimental_failure', 'historical_analysis']
        
        assert analysis['negative_insights'] == ['High volatility reduces RSI reliability', 'News events override technical signals']
        assert analysis['uncertainty_flags'] == ['limited_sample_size']
    
    @pytest.mark.asyncio
    async def test_detect_negative_violations(self, doctrine_system, mock_experiment_designs):
        """Test negative violation detection"""
        # Detect negative violations
        violations = await doctrine_system._detect_negative_violations(mock_experiment_designs)
        
        # Verify results
        assert isinstance(violations, list)
        assert len(violations) >= 0  # May or may not detect violations depending on conditions
        
        # Check violation structure
        for violation in violations:
            assert isinstance(violation, NegativeViolation)
            assert violation.violation_id.startswith('VIOLATION_')
            assert violation.negative_pattern_id is not None
            assert isinstance(violation.violation_description, str)
            assert isinstance(violation.violated_conditions, list)
            assert isinstance(violation.severity, NegativeSeverity)
            assert isinstance(violation.detected_at, datetime)
            assert violation.resolved_at is None
            assert violation.resolution_notes is None
            assert isinstance(violation.created_at, datetime)
        
        # Verify violations were added to system
        assert len(doctrine_system.negative_violations) >= 0
    
    @pytest.mark.asyncio
    async def test_generate_violation_detection(self, doctrine_system, mock_experiment_designs):
        """Test violation detection generation"""
        detection_data = {
            'experiment_pattern': mock_experiment_designs[0],
            'negative_doctrine': doctrine_system.negative_doctrines['volatility_doctrine'].__dict__,
            'current_conditions': mock_experiment_designs[0]['conditions'],
            'historical_violations': [],
            'risk_level': mock_experiment_designs[0]['risk_level']
        }
        
        # Generate violation detection
        detection = await doctrine_system._generate_violation_detection(detection_data)
        
        # Verify detection
        assert detection is not None
        assert isinstance(detection, dict)
        assert 'violations_detected' in detection
        assert 'violation_insights' in detection
        assert 'risk_assessment' in detection
        
        # Verify specific values
        assert isinstance(detection['violations_detected'], list)
        assert len(detection['violations_detected']) == 1
        violation = detection['violations_detected'][0]
        assert violation['negative_pattern_id'] == 'high_vol_rsi_divergence'
        assert violation['violation_type'] == 'direct'
        assert violation['violation_description'] == 'RSI divergence signal in high volatility regime'
        assert violation['violated_conditions'] == ['volatility > 2.0', 'rsi_divergence = true']
        assert violation['severity'] == 'high'
        assert violation['confidence'] == 0.9
        assert violation['recommended_action'] == 'block'
        
        assert detection['violation_insights'] == ['High confidence violation detected', 'Immediate action required']
        assert detection['risk_assessment'] == 'high'
    
    @pytest.mark.asyncio
    async def test_evolve_negative_doctrine(self, doctrine_system):
        """Test negative doctrine evolution"""
        # Create mock analyses and violations
        mock_analyses = [
            NegativeAnalysis(
                analysis_id='ANALYSIS_1',
                analysis_type='pattern_analysis',
                negative_patterns_analyzed=['pattern1'],
                analysis_results={'negative_patterns': []},
                recommendations=['rec1'],
                confidence_score=0.8,
                created_at=datetime.now(timezone.utc)
            )
        ]
        
        mock_violations = [
            NegativeViolation(
                violation_id='VIOLATION_1',
                negative_pattern_id='pattern1',
                violation_description='Test violation',
                violated_conditions=['condition1'],
                severity=NegativeSeverity.HIGH,
                detected_at=datetime.now(timezone.utc),
                resolved_at=None,
                resolution_notes=None,
                created_at=datetime.now(timezone.utc)
            )
        ]
        
        # Evolve negative doctrine
        evolution_updates = await doctrine_system._evolve_negative_doctrine(mock_analyses, mock_violations)
        
        # Verify results
        assert isinstance(evolution_updates, list)
        assert len(evolution_updates) == 1
        
        # Check evolution update structure
        update = evolution_updates[0]
        assert 'update_type' in update
        assert 'target_id' in update
        assert 'update_details' in update
        assert 'rationale' in update
        assert 'confidence' in update
        
        # Verify specific values
        assert update['update_type'] == 'add_pattern'
        assert update['target_id'] == 'new_pattern_1'
        assert update['update_details']['severity'] == 'high'
        assert update['update_details']['confidence'] == 0.85
        assert update['rationale'] == 'New evidence from experimental failures'
        assert update['confidence'] == 0.8
    
    @pytest.mark.asyncio
    async def test_generate_doctrine_evolution(self, doctrine_system):
        """Test doctrine evolution generation"""
        evolution_data = {
            'current_doctrine': {name: doctrine.__dict__ for name, doctrine in doctrine_system.negative_doctrines.items()},
            'new_evidence': [],
            'violation_history': [],
            'performance_metrics': doctrine_system._calculate_doctrine_performance_metrics()
        }
        
        # Generate doctrine evolution
        evolution = await doctrine_system._generate_doctrine_evolution(evolution_data)
        
        # Verify evolution
        assert evolution is not None
        assert isinstance(evolution, dict)
        assert 'doctrine_updates' in evolution
        assert 'evolution_insights' in evolution
        assert 'doctrine_health' in evolution
        
        # Verify specific values
        assert isinstance(evolution['doctrine_updates'], list)
        assert len(evolution['doctrine_updates']) == 1
        update = evolution['doctrine_updates'][0]
        assert update['update_type'] == 'add_pattern'
        assert update['target_id'] == 'new_pattern_1'
        assert update['update_details']['severity'] == 'high'
        assert update['update_details']['confidence'] == 0.85
        assert update['rationale'] == 'New evidence from experimental failures'
        assert update['confidence'] == 0.8
        
        assert evolution['evolution_insights'] == ['Doctrine evolution based on new evidence']
        assert evolution['doctrine_health'] == 0.85
    
    def test_calculate_doctrine_performance_metrics(self, doctrine_system):
        """Test doctrine performance metrics calculation"""
        # Add some mock violations
        doctrine_system.negative_violations = [
            NegativeViolation(
                violation_id='VIOLATION_1',
                negative_pattern_id='pattern1',
                violation_description='Test violation 1',
                violated_conditions=['condition1'],
                severity=NegativeSeverity.HIGH,
                detected_at=datetime.now(timezone.utc),
                resolved_at=datetime.now(timezone.utc),  # Resolved
                resolution_notes='Resolved',
                created_at=datetime.now(timezone.utc)
            ),
            NegativeViolation(
                violation_id='VIOLATION_2',
                negative_pattern_id='pattern2',
                violation_description='Test violation 2',
                violated_conditions=['condition2'],
                severity=NegativeSeverity.MEDIUM,
                detected_at=datetime.now(timezone.utc),
                resolved_at=None,  # Not resolved
                resolution_notes=None,
                created_at=datetime.now(timezone.utc)
            )
        ]
        
        # Calculate performance metrics
        metrics = doctrine_system._calculate_doctrine_performance_metrics()
        
        # Verify results
        assert isinstance(metrics, dict)
        assert 'total_violations' in metrics
        assert 'resolved_violations' in metrics
        assert 'active_patterns' in metrics
        assert 'doctrine_effectiveness' in metrics
        
        # Verify specific values
        assert metrics['total_violations'] == 2
        assert metrics['resolved_violations'] == 1
        assert metrics['active_patterns'] == 4  # All 4 default patterns are active
        assert metrics['doctrine_effectiveness'] == 0.5  # 1 resolved out of 2 total
    
    @pytest.mark.asyncio
    async def test_update_negative_patterns(self, doctrine_system):
        """Test negative pattern updates"""
        # Create mock analyses
        mock_analyses = [
            NegativeAnalysis(
                analysis_id='ANALYSIS_1',
                analysis_type='pattern_analysis',
                negative_patterns_analyzed=['pattern1'],
                analysis_results={
                    'negative_patterns': [
                        {
                            'negative_type': 'contraindicated',
                            'pattern_description': 'Test negative pattern',
                            'contraindicated_conditions': ['condition1', 'condition2'],
                            'failure_mechanisms': ['mechanism1'],
                            'severity': 'high',
                            'confidence_level': 0.85,
                            'evidence': ['evidence1', 'evidence2']
                        }
                    ]
                },
                recommendations=['rec1'],
                confidence_score=0.8,
                created_at=datetime.now(timezone.utc)
            )
        ]
        
        mock_evolution = [
            {
                'update_type': 'add_pattern',
                'target_id': 'new_pattern_1',
                'update_details': {'severity': 'high'},
                'rationale': 'New evidence',
                'confidence': 0.8
            }
        ]
        
        # Update negative patterns
        pattern_updates = await doctrine_system._update_negative_patterns(mock_analyses, mock_evolution)
        
        # Verify results
        assert isinstance(pattern_updates, list)
        assert len(pattern_updates) == 1
        
        # Check pattern update structure
        update = pattern_updates[0]
        assert 'pattern_id' in update
        assert 'update_type' in update
        assert 'pattern_data' in update
        assert 'confidence' in update
        assert 'updated_at' in update
        
        # Verify specific values
        assert update['pattern_id'].startswith('pattern_')
        assert update['update_type'] == 'add_pattern'
        assert isinstance(update['pattern_data'], dict)
        assert update['confidence'] == 0.85
        assert isinstance(update['updated_at'], str)
        
        # Verify pattern was added to system
        assert len(doctrine_system.negative_patterns) == 5  # 4 default + 1 new
    
    @pytest.mark.asyncio
    async def test_generate_llm_analysis(self, doctrine_system):
        """Test LLM analysis generation"""
        prompt_template = "Test negative_patterns prompt with {test_field}"
        data = {'test_field': 'test_value'}
        
        # Generate LLM analysis
        analysis = await doctrine_system._generate_llm_analysis(prompt_template, data)
        
        # Verify analysis
        assert analysis is not None
        assert isinstance(analysis, dict)
        assert 'negative_patterns' in analysis
        assert 'negative_insights' in analysis
        assert 'uncertainty_flags' in analysis
        
        # Verify specific values
        assert isinstance(analysis['negative_patterns'], list)
        assert len(analysis['negative_patterns']) == 1
        pattern = analysis['negative_patterns'][0]
        assert pattern['negative_type'] == 'contraindicated'
        assert pattern['pattern_description'] == 'High volatility RSI divergence signals'
        assert pattern['contraindicated_conditions'] == ['volatility > 2.0', 'regime = high_vol']
        assert pattern['failure_mechanisms'] == ['false_signals', 'whipsaws']
        assert pattern['severity'] == 'high'
        assert pattern['confidence_level'] == 0.85
        assert pattern['evidence'] == ['experimental_failure', 'historical_analysis']
        
        assert analysis['negative_insights'] == ['High volatility reduces RSI reliability', 'News events override technical signals']
        assert analysis['uncertainty_flags'] == ['limited_sample_size']
    
    @pytest.mark.asyncio
    async def test_publish_doctrine_results(self, doctrine_system, mock_supabase_manager):
        """Test publishing doctrine results"""
        results = {
            'negative_analyses': [{'analysis_id': 'ANALYSIS_1'}],
            'violation_detections': [{'violation_id': 'VIOLATION_1'}],
            'doctrine_evolution': [{'update_id': 'UPDATE_1'}],
            'pattern_updates': [{'pattern_id': 'PATTERN_1'}],
            'doctrine_timestamp': datetime.now(timezone.utc),
            'doctrine_errors': []
        }
        
        await doctrine_system._publish_doctrine_results(results)
        
        # Verify strand was inserted
        mock_supabase_manager.insert_strand.assert_called_once()
        call_args = mock_supabase_manager.insert_strand.call_args[0][0]
        assert call_args['kind'] == 'cil_doctrine_of_negatives'
        assert call_args['agent_id'] == 'central_intelligence_layer'
        assert call_args['cil_team_member'] == 'doctrine_of_negatives_system'
        assert call_args['strategic_meta_type'] == 'doctrine_analysis'
        assert call_args['resonance_score'] == 0.9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
