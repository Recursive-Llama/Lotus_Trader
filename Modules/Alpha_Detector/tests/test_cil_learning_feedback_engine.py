"""
Test CIL Learning & Feedback Engine
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.intelligence.system_control.central_intelligence_layer.engines.learning_feedback_engine import (
    LearningFeedbackEngine, LessonType, DoctrineStatus, Lesson, Braid, DoctrineUpdate
)


class TestLearningFeedbackEngine:
    """Test CIL Learning & Feedback Engine"""
    
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
    def learning_engine(self, mock_supabase_manager, mock_llm_client):
        """Create LearningFeedbackEngine instance"""
        return LearningFeedbackEngine(mock_supabase_manager, mock_llm_client)
    
    @pytest.fixture
    def mock_orchestration_results(self):
        """Mock orchestration results"""
        return {
            'completed_experiments': [
                Mock(
                    experiment_id='EXP_123',
                    agent_id='raw_data_intelligence',
                    outcome='success',
                    metrics={'accuracy': 0.8, 'precision': 0.7},
                    lessons_learned=['lesson_1', 'lesson_2'],
                    recommendations=['recommendation_1'],
                    confidence_score=0.8,
                    completion_time=datetime.now(timezone.utc)
                ),
                Mock(
                    experiment_id='EXP_456',
                    agent_id='indicator_intelligence',
                    outcome='failure',
                    metrics={'accuracy': 0.3, 'precision': 0.2},
                    lessons_learned=['lesson_3'],
                    recommendations=['recommendation_2'],
                    confidence_score=0.4,
                    completion_time=datetime.now(timezone.utc)
                )
            ],
            'active_experiments': [
                {
                    'experiment_id': 'EXP_789',
                    'target_agent': 'pattern_intelligence',
                    'created_at': datetime.now(timezone.utc) - timedelta(hours=2),
                    'deadline': datetime.now(timezone.utc) + timedelta(hours=1)
                }
            ],
            'experiment_ideas': [],
            'experiment_designs': [],
            'experiment_assignments': []
        }
    
    def test_learning_engine_initialization(self, learning_engine):
        """Test LearningFeedbackEngine initialization"""
        assert learning_engine.supabase_manager is not None
        assert learning_engine.llm_client is not None
        assert learning_engine.lesson_clustering_threshold == 0.7
        assert learning_engine.doctrine_promotion_threshold == 0.8
        assert learning_engine.doctrine_retirement_threshold == 0.3
        assert learning_engine.surprise_threshold == 0.6
        assert learning_engine.novelty_threshold == 0.5
        assert learning_engine.min_lessons_per_braid == 3
        assert learning_engine.max_lessons_per_braid == 20
        assert learning_engine.braid_consolidation_threshold == 0.8
    
    @pytest.mark.asyncio
    async def test_process_learning_feedback_success(self, learning_engine, mock_orchestration_results):
        """Test successful learning feedback processing"""
        # Mock the individual learning methods
        with patch.object(learning_engine, 'capture_all_outcomes') as mock_capture, \
             patch.object(learning_engine, 'structure_results_into_lessons') as mock_structure, \
             patch.object(learning_engine, 'update_strand_braid_memory') as mock_update, \
             patch.object(learning_engine, 'generate_doctrine_feedback') as mock_doctrine, \
             patch.object(learning_engine, 'distribute_doctrine_updates') as mock_distribute, \
             patch.object(learning_engine, 'assess_continuous_improvement') as mock_assess:
            
            # Set up mock returns
            mock_capture.return_value = [{'outcome_id': 'OUTCOME_1'}]
            mock_structure.return_value = []
            mock_update.return_value = []
            mock_doctrine.return_value = []
            mock_distribute.return_value = []
            mock_assess.return_value = {}
            
            # Process learning feedback
            result = await learning_engine.process_learning_feedback(mock_orchestration_results)
            
            # Verify structure
            assert 'captured_outcomes' in result
            assert 'structured_lessons' in result
            assert 'updated_braids' in result
            assert 'doctrine_updates' in result
            assert 'distributed_updates' in result
            assert 'improvement_assessment' in result
            assert 'learning_timestamp' in result
            assert 'learning_errors' in result
            
            # Verify processing timestamp
            assert isinstance(result['learning_timestamp'], datetime)
    
    @pytest.mark.asyncio
    async def test_capture_all_outcomes(self, learning_engine, mock_orchestration_results):
        """Test outcome capture"""
        # Capture outcomes
        outcomes = await learning_engine.capture_all_outcomes(mock_orchestration_results)
        
        # Verify results
        assert isinstance(outcomes, list)
        assert len(outcomes) == 3  # 2 completed + 1 active
        
        # Check completed experiment outcomes
        completed_outcomes = [o for o in outcomes if o['outcome_type'] != 'progress']
        assert len(completed_outcomes) == 2
        
        # Check progress outcomes
        progress_outcomes = [o for o in outcomes if o['outcome_type'] == 'progress']
        assert len(progress_outcomes) == 1
        
        # Verify outcome structure
        for outcome in outcomes:
            assert 'outcome_id' in outcome
            assert 'experiment_id' in outcome
            assert 'agent_id' in outcome
            assert 'outcome_type' in outcome
            assert 'captured_at' in outcome
            assert isinstance(outcome['captured_at'], datetime)
    
    @pytest.mark.asyncio
    async def test_structure_results_into_lessons(self, learning_engine, mock_orchestration_results):
        """Test lesson structuring"""
        # Mock capture_all_outcomes
        with patch.object(learning_engine, 'capture_all_outcomes') as mock_capture:
            mock_capture.return_value = [
                {
                    'outcome_id': 'OUTCOME_1',
                    'experiment_id': 'EXP_123',
                    'agent_id': 'raw_data_intelligence',
                    'outcome_type': 'success',
                    'metrics': {'accuracy': 0.8, 'precision': 0.7},
                    'lessons_learned': ['lesson_1', 'lesson_2'],
                    'recommendations': ['recommendation_1'],
                    'confidence_score': 0.8,
                    'completion_time': datetime.now(timezone.utc)
                }
            ]
            
            # Structure lessons
            lessons = await learning_engine.structure_results_into_lessons(mock_orchestration_results)
            
            # Verify results
            assert isinstance(lessons, list)
            assert len(lessons) == 1
            
            lesson = lessons[0]
            assert isinstance(lesson, Lesson)
            assert lesson.lesson_id.startswith('LESSON_')
            assert lesson.lesson_type == LessonType.SUCCESS
            assert lesson.pattern_family in ['divergence', 'volume_analysis', 'correlation_analysis', 'pattern_recognition', 'general']
            assert isinstance(lesson.context, dict)
            assert lesson.outcome == 'success'
            assert 0.0 <= lesson.persistence_score <= 1.0
            assert 0.0 <= lesson.novelty_score <= 1.0
            assert 0.0 <= lesson.surprise_rating <= 1.0
            assert lesson.evidence_count > 0
            assert 0.0 <= lesson.confidence_level <= 1.0
            assert isinstance(lesson.fails_when, list)
            assert isinstance(lesson.created_at, datetime)
    
    @pytest.mark.asyncio
    async def test_update_strand_braid_memory(self, learning_engine, mock_orchestration_results):
        """Test strand-braid memory update"""
        # Mock structure_results_into_lessons and _get_existing_braids
        with patch.object(learning_engine, 'structure_results_into_lessons') as mock_structure, \
             patch.object(learning_engine, '_get_existing_braids') as mock_braids, \
             patch.object(learning_engine, '_save_braids_to_database') as mock_save:
            
            # Create mock lesson
            mock_lesson = Lesson(
                lesson_id='LESSON_123',
                lesson_type=LessonType.SUCCESS,
                pattern_family='divergence',
                context={'experiment_id': 'EXP_123'},
                outcome='success',
                persistence_score=0.8,
                novelty_score=0.7,
                surprise_rating=0.6,
                evidence_count=3,
                confidence_level=0.8,
                mechanism_hypothesis='Test hypothesis',
                fails_when=['condition_1'],
                created_at=datetime.now(timezone.utc)
            )
            
            mock_structure.return_value = [mock_lesson]
            mock_braids.return_value = []
            mock_save.return_value = None
            
            # Update strand-braid memory
            braids = await learning_engine.update_strand_braid_memory(mock_orchestration_results)
            
            # Verify results
            assert isinstance(braids, list)
            assert len(braids) == 1
            
            braid = braids[0]
            assert isinstance(braid, Braid)
            assert braid.braid_id.startswith('BRAID_')
            assert braid.braid_name == 'divergence_braid'
            assert braid.pattern_family == 'divergence'
            assert len(braid.lessons) == 1
            assert isinstance(braid.aggregate_metrics, dict)
            assert braid.doctrine_status == DoctrineStatus.PROVISIONAL
            assert isinstance(braid.lineage, dict)
            assert isinstance(braid.created_at, datetime)
            assert isinstance(braid.updated_at, datetime)
    
    @pytest.mark.asyncio
    async def test_generate_doctrine_feedback(self, learning_engine, mock_orchestration_results):
        """Test doctrine feedback generation"""
        # Mock update_strand_braid_memory
        with patch.object(learning_engine, 'update_strand_braid_memory') as mock_update:
            # Create mock braid
            mock_lesson = Lesson(
                lesson_id='LESSON_123',
                lesson_type=LessonType.SUCCESS,
                pattern_family='divergence',
                context={'agent_id': 'raw_data_intelligence'},
                outcome='success',
                persistence_score=0.9,
                novelty_score=0.8,
                surprise_rating=0.7,
                evidence_count=5,
                confidence_level=0.9,
                mechanism_hypothesis='Test hypothesis',
                fails_when=['condition_1'],
                created_at=datetime.now(timezone.utc)
            )
            
            mock_braid = Braid(
                braid_id='BRAID_123',
                braid_name='divergence_braid',
                pattern_family='divergence',
                lessons=[mock_lesson],
                aggregate_metrics={'avg_confidence': 0.9, 'lesson_count': 1},
                doctrine_status=DoctrineStatus.PROVISIONAL,
                lineage={'created_from': 'LESSON_123'},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            mock_update.return_value = [mock_braid]
            
            # Generate doctrine feedback
            updates = await learning_engine.generate_doctrine_feedback(mock_orchestration_results)
            
            # Verify results
            assert isinstance(updates, list)
            if updates:  # Only check if updates were generated
                update = updates[0]
                assert isinstance(update, DoctrineUpdate)
                assert update.update_id.startswith('PROMOTE_')
                assert update.update_type == 'promote'
                assert update.pattern_family == 'divergence'
                assert isinstance(update.rationale, str)
                assert isinstance(update.evidence, list)
                assert 0.0 <= update.confidence_level <= 1.0
                assert isinstance(update.affected_agents, list)
                assert isinstance(update.created_at, datetime)
    
    @pytest.mark.asyncio
    async def test_distribute_doctrine_updates(self, learning_engine, mock_orchestration_results, mock_supabase_manager):
        """Test doctrine update distribution"""
        # Mock generate_doctrine_feedback
        with patch.object(learning_engine, 'generate_doctrine_feedback') as mock_doctrine:
            # Create mock doctrine update
            mock_update = DoctrineUpdate(
                update_id='PROMOTE_123',
                update_type='promote',
                pattern_family='divergence',
                rationale='Test rationale',
                evidence=['LESSON_123'],
                confidence_level=0.9,
                affected_agents=['raw_data_intelligence', 'indicator_intelligence'],
                created_at=datetime.now(timezone.utc)
            )
            
            mock_doctrine.return_value = [mock_update]
            
            # Distribute doctrine updates
            distributions = await learning_engine.distribute_doctrine_updates(mock_orchestration_results)
            
            # Verify results
            assert isinstance(distributions, list)
            assert len(distributions) == 2  # One for each affected agent
            
            for distribution in distributions:
                assert 'update_id' in distribution
                assert 'target_agent' in distribution
                assert 'distribution_status' in distribution
                assert 'distributed_at' in distribution
                assert distribution['distribution_status'] == 'sent'
                assert isinstance(distribution['distributed_at'], datetime)
            
            # Verify strands were inserted
            assert mock_supabase_manager.insert_strand.call_count == 2
    
    @pytest.mark.asyncio
    async def test_assess_continuous_improvement(self, learning_engine, mock_orchestration_results):
        """Test continuous improvement assessment"""
        # Mock all the learning methods
        with patch.object(learning_engine, 'capture_all_outcomes') as mock_capture, \
             patch.object(learning_engine, 'structure_results_into_lessons') as mock_structure, \
             patch.object(learning_engine, 'update_strand_braid_memory') as mock_update, \
             patch.object(learning_engine, 'generate_doctrine_feedback') as mock_doctrine:
            
            # Set up mock returns
            mock_capture.return_value = [{'outcome_id': 'OUTCOME_1'}]
            mock_structure.return_value = []
            mock_update.return_value = []
            mock_doctrine.return_value = []
            
            # Assess continuous improvement
            assessment = await learning_engine.assess_continuous_improvement(mock_orchestration_results)
            
            # Verify results
            assert isinstance(assessment, dict)
            assert 'improvement_metrics' in assessment
            assert 'system_sharpening' in assessment
            assert 'improvement_recommendations' in assessment
            assert 'assessment_timestamp' in assessment
            
            # Verify improvement metrics
            metrics = assessment['improvement_metrics']
            assert 'outcomes_processed' in metrics
            assert 'lessons_structured' in metrics
            assert 'braids_updated' in metrics
            assert 'doctrine_updates_generated' in metrics
            assert 'system_learning_rate' in metrics
            assert 'doctrine_evolution_rate' in metrics
            assert 'pattern_discovery_rate' in metrics
            assert 'knowledge_retention_rate' in metrics
            
            # Verify system sharpening
            sharpening = assessment['system_sharpening']
            assert 'accuracy_improvement' in sharpening
            assert 'efficiency_improvement' in sharpening
            assert 'novelty_improvement' in sharpening
            assert 'resilience_improvement' in sharpening
            
            # Verify recommendations
            recommendations = assessment['improvement_recommendations']
            assert isinstance(recommendations, list)
    
    def test_determine_lesson_type(self, learning_engine):
        """Test lesson type determination"""
        # Test success
        outcome = {'outcome_type': 'success'}
        lesson_type = learning_engine._determine_lesson_type(outcome)
        assert lesson_type == LessonType.SUCCESS
        
        # Test failure
        outcome = {'outcome_type': 'failure'}
        lesson_type = learning_engine._determine_lesson_type(outcome)
        assert lesson_type == LessonType.FAILURE
        
        # Test anomaly
        outcome = {'outcome_type': 'anomaly'}
        lesson_type = learning_engine._determine_lesson_type(outcome)
        assert lesson_type == LessonType.ANOMALY
        
        # Test partial
        outcome = {'outcome_type': 'partial'}
        lesson_type = learning_engine._determine_lesson_type(outcome)
        assert lesson_type == LessonType.PARTIAL
        
        # Test progress
        outcome = {'outcome_type': 'progress'}
        lesson_type = learning_engine._determine_lesson_type(outcome)
        assert lesson_type == LessonType.INSIGHT
        
        # Test default
        outcome = {'outcome_type': 'unknown'}
        lesson_type = learning_engine._determine_lesson_type(outcome)
        assert lesson_type == LessonType.INSIGHT
    
    def test_extract_pattern_family(self, learning_engine):
        """Test pattern family extraction"""
        # Test divergence
        outcome = {'experiment_id': 'EXP_divergence_123'}
        family = learning_engine._extract_pattern_family(outcome)
        assert family == 'divergence'
        
        # Test volume
        outcome = {'experiment_id': 'EXP_volume_456'}
        family = learning_engine._extract_pattern_family(outcome)
        assert family == 'volume_analysis'
        
        # Test correlation
        outcome = {'experiment_id': 'EXP_correlation_789'}
        family = learning_engine._extract_pattern_family(outcome)
        assert family == 'correlation_analysis'
        
        # Test pattern
        outcome = {'experiment_id': 'EXP_pattern_012'}
        family = learning_engine._extract_pattern_family(outcome)
        assert family == 'pattern_recognition'
        
        # Test default
        outcome = {'experiment_id': 'EXP_unknown_345'}
        family = learning_engine._extract_pattern_family(outcome)
        assert family == 'general'
    
    def test_extract_lesson_context(self, learning_engine):
        """Test lesson context extraction"""
        completion_time = datetime.now(timezone.utc)
        outcome = {
            'experiment_id': 'EXP_123',
            'agent_id': 'raw_data_intelligence',
            'outcome_type': 'success',
            'completion_time': completion_time,
            'metrics': {'accuracy': 0.8},
            'confidence_score': 0.9
        }
        
        context = learning_engine._extract_lesson_context(outcome)
        
        assert isinstance(context, dict)
        assert context['experiment_id'] == 'EXP_123'
        assert context['agent_id'] == 'raw_data_intelligence'
        assert context['outcome_type'] == 'success'
        assert context['completion_time'] == completion_time
        assert context['metrics'] == {'accuracy': 0.8}
        assert context['confidence_score'] == 0.9
    
    def test_calculate_persistence_score(self, learning_engine):
        """Test persistence score calculation"""
        # Test with accuracy and precision
        outcome = {
            'confidence_score': 0.8,
            'metrics': {'accuracy': 0.9, 'precision': 0.8}
        }
        score = learning_engine._calculate_persistence_score(outcome)
        assert 0.0 <= score <= 1.0
        assert abs(score - 0.85) < 0.001  # (0.9 + 0.8) / 2
        
        # Test with only confidence
        outcome = {
            'confidence_score': 0.7,
            'metrics': {}
        }
        score = learning_engine._calculate_persistence_score(outcome)
        assert 0.0 <= score <= 1.0
        assert score == 0.7
    
    def test_calculate_novelty_score(self, learning_engine):
        """Test novelty score calculation"""
        # Test with high metrics
        outcome = {
            'metrics': {'accuracy': 0.9, 'precision': 0.9, 'recall': 0.9}
        }
        score = learning_engine._calculate_novelty_score(outcome)
        assert 0.0 <= score <= 1.0
        assert score == 1.0  # 3/3 indicators
        
        # Test with low metrics
        outcome = {
            'metrics': {'accuracy': 0.5, 'precision': 0.4, 'recall': 0.3}
        }
        score = learning_engine._calculate_novelty_score(outcome)
        assert 0.0 <= score <= 1.0
        assert score == 0.0  # 0/3 indicators
    
    def test_calculate_surprise_rating(self, learning_engine):
        """Test surprise rating calculation"""
        # Test anomaly
        outcome = {'outcome_type': 'anomaly', 'confidence_score': 0.8}
        rating = learning_engine._calculate_surprise_rating(outcome)
        assert rating == 0.9
        
        # Test confident failure
        outcome = {'outcome_type': 'failure', 'confidence_score': 0.8}
        rating = learning_engine._calculate_surprise_rating(outcome)
        assert rating == 0.8
        
        # Test low-confidence success
        outcome = {'outcome_type': 'success', 'confidence_score': 0.4}
        rating = learning_engine._calculate_surprise_rating(outcome)
        assert rating == 0.7
        
        # Test expected outcome
        outcome = {'outcome_type': 'success', 'confidence_score': 0.8}
        rating = learning_engine._calculate_surprise_rating(outcome)
        assert rating == 0.3
    
    def test_count_evidence(self, learning_engine):
        """Test evidence counting"""
        # Test with all evidence types
        outcome = {
            'metrics': {'accuracy': 0.8, 'precision': 0.7},
            'lessons_learned': ['lesson_1', 'lesson_2'],
            'recommendations': ['recommendation_1']
        }
        count = learning_engine._count_evidence(outcome)
        assert count == 5  # 2 metrics + 2 lessons + 1 recommendation
        
        # Test with minimal evidence
        outcome = {'metrics': {}}
        count = learning_engine._count_evidence(outcome)
        assert count == 1  # Minimum evidence count
    
    def test_calculate_confidence_level(self, learning_engine):
        """Test confidence level calculation"""
        outcome = {'confidence_score': 0.8}
        confidence = learning_engine._calculate_confidence_level(outcome)
        assert confidence == 0.8
        
        outcome = {}
        confidence = learning_engine._calculate_confidence_level(outcome)
        assert confidence == 0.5  # Default
    
    @pytest.mark.asyncio
    async def test_generate_mechanism_hypothesis(self, learning_engine):
        """Test mechanism hypothesis generation"""
        outcome = {
            'outcome_type': 'success',
            'experiment_id': 'EXP_divergence_123'
        }
        
        hypothesis = await learning_engine._generate_mechanism_hypothesis(outcome)
        
        assert isinstance(hypothesis, str)
        assert 'divergence' in hypothesis
        assert 'success' in hypothesis
        assert 'Placeholder hypothesis' in hypothesis
    
    @pytest.mark.asyncio
    async def test_determine_failure_conditions(self, learning_engine):
        """Test failure conditions determination"""
        outcome = {'outcome_type': 'failure'}
        
        conditions = await learning_engine._determine_failure_conditions(outcome)
        
        assert isinstance(conditions, list)
        assert len(conditions) == 3
        assert 'Low confidence threshold' in conditions
        assert 'Insufficient evidence' in conditions
        assert 'Contradictory results' in conditions
    
    @pytest.mark.asyncio
    async def test_get_existing_braids(self, learning_engine):
        """Test getting existing braids"""
        braids = await learning_engine._get_existing_braids()
        
        assert isinstance(braids, list)
        assert len(braids) == 0  # Mock returns empty list
    
    def test_find_matching_braid(self, learning_engine):
        """Test finding matching braid"""
        # Create mock lesson
        lesson = Lesson(
            lesson_id='LESSON_123',
            lesson_type=LessonType.SUCCESS,
            pattern_family='divergence',
            context={},
            outcome='success',
            persistence_score=0.8,
            novelty_score=0.7,
            surprise_rating=0.6,
            evidence_count=3,
            confidence_level=0.8,
            mechanism_hypothesis='Test',
            fails_when=['condition_1'],
            created_at=datetime.now(timezone.utc)
        )
        
        # Create mock braids
        matching_braid = Braid(
            braid_id='BRAID_123',
            braid_name='divergence_braid',
            pattern_family='divergence',
            lessons=[],
            aggregate_metrics={},
            doctrine_status=DoctrineStatus.PROVISIONAL,
            lineage={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        non_matching_braid = Braid(
            braid_id='BRAID_456',
            braid_name='volume_braid',
            pattern_family='volume_analysis',
            lessons=[],
            aggregate_metrics={},
            doctrine_status=DoctrineStatus.PROVISIONAL,
            lineage={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        existing_braids = [matching_braid, non_matching_braid]
        
        # Test finding matching braid
        found_braid = learning_engine._find_matching_braid(lesson, existing_braids)
        assert found_braid == matching_braid
        
        # Test finding no matching braid
        lesson.pattern_family = 'correlation_analysis'
        found_braid = learning_engine._find_matching_braid(lesson, existing_braids)
        assert found_braid is None
    
    def test_calculate_braid_metrics(self, learning_engine):
        """Test braid metrics calculation"""
        # Create mock lessons
        lesson1 = Lesson(
            lesson_id='LESSON_1',
            lesson_type=LessonType.SUCCESS,
            pattern_family='divergence',
            context={},
            outcome='success',
            persistence_score=0.8,
            novelty_score=0.7,
            surprise_rating=0.6,
            evidence_count=3,
            confidence_level=0.8,
            mechanism_hypothesis='Test',
            fails_when=['condition_1'],
            created_at=datetime.now(timezone.utc)
        )
        
        lesson2 = Lesson(
            lesson_id='LESSON_2',
            lesson_type=LessonType.SUCCESS,
            pattern_family='divergence',
            context={},
            outcome='success',
            persistence_score=0.9,
            novelty_score=0.8,
            surprise_rating=0.7,
            evidence_count=4,
            confidence_level=0.9,
            mechanism_hypothesis='Test',
            fails_when=['condition_2'],
            created_at=datetime.now(timezone.utc)
        )
        
        lessons = [lesson1, lesson2]
        metrics = learning_engine._calculate_braid_metrics(lessons)
        
        assert isinstance(metrics, dict)
        assert 'avg_persistence' in metrics
        assert 'avg_novelty' in metrics
        assert 'avg_surprise' in metrics
        assert 'avg_confidence' in metrics
        assert 'total_evidence' in metrics
        assert 'lesson_count' in metrics
        
        assert abs(metrics['avg_persistence'] - 0.85) < 0.001  # (0.8 + 0.9) / 2
        assert abs(metrics['avg_novelty'] - 0.75) < 0.001  # (0.7 + 0.8) / 2
        assert abs(metrics['avg_surprise'] - 0.65) < 0.001  # (0.6 + 0.7) / 2
        assert abs(metrics['avg_confidence'] - 0.85) < 0.001  # (0.8 + 0.9) / 2
        assert metrics['total_evidence'] == 7  # 3 + 4
        assert metrics['lesson_count'] == 2
    
    def test_update_doctrine_status(self, learning_engine):
        """Test doctrine status update"""
        # Test promotion
        braid = Mock()
        braid.aggregate_metrics = {'avg_confidence': 0.9}
        status = learning_engine._update_doctrine_status(braid)
        assert status == DoctrineStatus.AFFIRMED
        
        # Test retirement
        braid.aggregate_metrics = {'avg_confidence': 0.2}
        status = learning_engine._update_doctrine_status(braid)
        assert status == DoctrineStatus.RETIRED
        
        # Test provisional
        braid.aggregate_metrics = {'avg_confidence': 0.5}
        status = learning_engine._update_doctrine_status(braid)
        assert status == DoctrineStatus.PROVISIONAL
    
    def test_should_promote_braid(self, learning_engine):
        """Test braid promotion criteria"""
        # Test should promote
        braid = Mock()
        braid.aggregate_metrics = {'avg_confidence': 0.9, 'lesson_count': 5}
        should_promote = learning_engine._should_promote_braid(braid)
        assert should_promote is True
        
        # Test should not promote (low confidence)
        braid.aggregate_metrics = {'avg_confidence': 0.7, 'lesson_count': 5}
        should_promote = learning_engine._should_promote_braid(braid)
        assert should_promote is False
        
        # Test should not promote (insufficient lessons)
        braid.aggregate_metrics = {'avg_confidence': 0.9, 'lesson_count': 2}
        should_promote = learning_engine._should_promote_braid(braid)
        assert should_promote is False
    
    def test_should_retire_braid(self, learning_engine):
        """Test braid retirement criteria"""
        # Test should retire
        braid = Mock()
        braid.aggregate_metrics = {'avg_confidence': 0.2, 'lesson_count': 5}
        should_retire = learning_engine._should_retire_braid(braid)
        assert should_retire is True
        
        # Test should not retire (high confidence)
        braid.aggregate_metrics = {'avg_confidence': 0.5, 'lesson_count': 5}
        should_retire = learning_engine._should_retire_braid(braid)
        assert should_retire is False
        
        # Test should not retire (insufficient lessons)
        braid.aggregate_metrics = {'avg_confidence': 0.2, 'lesson_count': 2}
        should_retire = learning_engine._should_retire_braid(braid)
        assert should_retire is False
    
    def test_should_refine_braid(self, learning_engine):
        """Test braid refinement criteria"""
        # Test should refine
        braid = Mock()
        braid.aggregate_metrics = {'avg_confidence': 0.5, 'lesson_count': 5}
        should_refine = learning_engine._should_refine_braid(braid)
        assert should_refine is True
        
        # Test should not refine (high confidence)
        braid.aggregate_metrics = {'avg_confidence': 0.9, 'lesson_count': 5}
        should_refine = learning_engine._should_refine_braid(braid)
        assert should_refine is False
        
        # Test should not refine (low confidence)
        braid.aggregate_metrics = {'avg_confidence': 0.2, 'lesson_count': 5}
        should_refine = learning_engine._should_refine_braid(braid)
        assert should_refine is False
    
    def test_should_contraindicate_braid(self, learning_engine):
        """Test braid contraindication criteria"""
        # Test should contraindicate (high failure rate)
        braid = Mock()
        braid.lessons = [
            Mock(lesson_type=LessonType.FAILURE),
            Mock(lesson_type=LessonType.FAILURE),
            Mock(lesson_type=LessonType.FAILURE),
            Mock(lesson_type=LessonType.SUCCESS)
        ]
        should_contraindicate = learning_engine._should_contraindicate_braid(braid)
        assert should_contraindicate is True
        
        # Test should not contraindicate (low failure rate)
        braid.lessons = [
            Mock(lesson_type=LessonType.SUCCESS),
            Mock(lesson_type=LessonType.SUCCESS),
            Mock(lesson_type=LessonType.FAILURE)
        ]
        should_contraindicate = learning_engine._should_contraindicate_braid(braid)
        assert should_contraindicate is False
    
    def test_get_affected_agents(self, learning_engine):
        """Test getting affected agents"""
        # Create mock braid with lessons
        lesson1 = Mock()
        lesson1.context = {'agent_id': 'raw_data_intelligence'}
        
        lesson2 = Mock()
        lesson2.context = {'agent_id': 'indicator_intelligence'}
        
        braid = Mock()
        braid.lessons = [lesson1, lesson2]
        
        agents = learning_engine._get_affected_agents(braid)
        
        assert isinstance(agents, list)
        assert len(agents) == 2
        assert 'raw_data_intelligence' in agents
        assert 'indicator_intelligence' in agents
        
        # Test with no agent context
        lesson1.context = {}
        lesson2.context = {}
        agents = learning_engine._get_affected_agents(braid)
        
        assert isinstance(agents, list)
        assert len(agents) == 2
        assert 'raw_data_intelligence' in agents
        assert 'indicator_intelligence' in agents
    
    def test_calculate_learning_rate(self, learning_engine):
        """Test learning rate calculation"""
        # Create mock lessons
        lesson1 = Mock(novelty_score=0.8, surprise_rating=0.7)
        lesson2 = Mock(novelty_score=0.6, surprise_rating=0.9)
        
        lessons = [lesson1, lesson2]
        rate = learning_engine._calculate_learning_rate(lessons)
        
        assert 0.0 <= rate <= 1.0
        assert rate == 0.75  # (0.8 + 0.7 + 0.6 + 0.9) / 4
        
        # Test with empty lessons
        rate = learning_engine._calculate_learning_rate([])
        assert rate == 0.0
    
    def test_calculate_doctrine_evolution_rate(self, learning_engine):
        """Test doctrine evolution rate calculation"""
        # Create mock doctrine updates
        update1 = Mock(update_type='promote')
        update2 = Mock(update_type='retire')
        update3 = Mock(update_type='refine')
        
        updates = [update1, update2, update3]
        rate = learning_engine._calculate_doctrine_evolution_rate(updates)
        
        assert 0.0 <= rate <= 1.0
        assert rate == 0.75  # 3/4 possible update types
        
        # Test with empty updates
        rate = learning_engine._calculate_doctrine_evolution_rate([])
        assert rate == 0.0
    
    def test_calculate_pattern_discovery_rate(self, learning_engine):
        """Test pattern discovery rate calculation"""
        # Create mock braids
        braid1 = Mock(doctrine_status=DoctrineStatus.PROVISIONAL)
        braid2 = Mock(doctrine_status=DoctrineStatus.AFFIRMED)
        braid3 = Mock(doctrine_status=DoctrineStatus.PROVISIONAL)
        
        braids = [braid1, braid2, braid3]
        rate = learning_engine._calculate_pattern_discovery_rate(braids)
        
        assert 0.0 <= rate <= 1.0
        assert rate == 2/3  # 2 provisional out of 3 braids
        
        # Test with empty braids
        rate = learning_engine._calculate_pattern_discovery_rate([])
        assert rate == 0.0
    
    def test_calculate_knowledge_retention_rate(self, learning_engine):
        """Test knowledge retention rate calculation"""
        # Create mock braids
        braid1 = Mock(doctrine_status=DoctrineStatus.AFFIRMED)
        braid2 = Mock(doctrine_status=DoctrineStatus.PROVISIONAL)
        braid3 = Mock(doctrine_status=DoctrineStatus.AFFIRMED)
        
        braids = [braid1, braid2, braid3]
        rate = learning_engine._calculate_knowledge_retention_rate(braids)
        
        assert 0.0 <= rate <= 1.0
        assert rate == 2/3  # 2 affirmed out of 3 braids
        
        # Test with empty braids
        rate = learning_engine._calculate_knowledge_retention_rate([])
        assert rate == 0.0
    
    def test_assess_accuracy_improvement(self, learning_engine):
        """Test accuracy improvement assessment"""
        # Create mock lessons
        lesson1 = Mock(lesson_type=LessonType.SUCCESS)
        lesson2 = Mock(lesson_type=LessonType.FAILURE)
        lesson3 = Mock(lesson_type=LessonType.SUCCESS)
        
        lessons = [lesson1, lesson2, lesson3]
        improvement = learning_engine._assess_accuracy_improvement(lessons)
        
        assert 0.0 <= improvement <= 1.0
        assert improvement == 2/3  # 2 success out of 3 lessons
        
        # Test with empty lessons
        improvement = learning_engine._assess_accuracy_improvement([])
        assert improvement == 0.0
    
    def test_assess_efficiency_improvement(self, learning_engine):
        """Test efficiency improvement assessment"""
        # Create mock lessons
        lesson1 = Mock(persistence_score=0.8)
        lesson2 = Mock(persistence_score=0.6)
        lesson3 = Mock(persistence_score=0.9)
        
        lessons = [lesson1, lesson2, lesson3]
        improvement = learning_engine._assess_efficiency_improvement(lessons)
        
        assert 0.0 <= improvement <= 1.0
        assert abs(improvement - 0.7666666666666667) < 0.001  # (0.8 + 0.6 + 0.9) / 3
        
        # Test with empty lessons
        improvement = learning_engine._assess_efficiency_improvement([])
        assert improvement == 0.0
    
    def test_assess_novelty_improvement(self, learning_engine):
        """Test novelty improvement assessment"""
        # Create mock lessons
        lesson1 = Mock(novelty_score=0.8)
        lesson2 = Mock(novelty_score=0.6)
        lesson3 = Mock(novelty_score=0.9)
        
        lessons = [lesson1, lesson2, lesson3]
        improvement = learning_engine._assess_novelty_improvement(lessons)
        
        assert 0.0 <= improvement <= 1.0
        assert abs(improvement - 0.7666666666666667) < 0.001  # (0.8 + 0.6 + 0.9) / 3
        
        # Test with empty lessons
        improvement = learning_engine._assess_novelty_improvement([])
        assert improvement == 0.0
    
    def test_assess_resilience_improvement(self, learning_engine):
        """Test resilience improvement assessment"""
        # Create mock braids
        braid1 = Mock(doctrine_status=DoctrineStatus.AFFIRMED)
        braid2 = Mock(doctrine_status=DoctrineStatus.PROVISIONAL)
        braid3 = Mock(doctrine_status=DoctrineStatus.AFFIRMED)
        
        braids = [braid1, braid2, braid3]
        improvement = learning_engine._assess_resilience_improvement(braids)
        
        assert 0.0 <= improvement <= 1.0
        assert improvement == 2/3  # 2 affirmed out of 3 braids
        
        # Test with empty braids
        improvement = learning_engine._assess_resilience_improvement([])
        assert improvement == 0.0
    
    @pytest.mark.asyncio
    async def test_generate_improvement_recommendations(self, learning_engine):
        """Test improvement recommendations generation"""
        improvement_metrics = {
            'system_learning_rate': 0.3,
            'doctrine_evolution_rate': 0.2,
            'pattern_discovery_rate': 0.8,
            'knowledge_retention_rate': 0.9
        }
        
        system_sharpening = {
            'accuracy_improvement': 0.6,
            'efficiency_improvement': 0.5,
            'novelty_improvement': 0.7,
            'resilience_improvement': 0.8
        }
        
        recommendations = await learning_engine._generate_improvement_recommendations(
            improvement_metrics, system_sharpening
        )
        
        assert isinstance(recommendations, list)
        assert len(recommendations) >= 2  # Should have at least 2 recommendations
        assert any('learning rate' in rec for rec in recommendations)
        assert any('doctrine evolution' in rec for rec in recommendations)
        assert any('accuracy' in rec for rec in recommendations)
        assert any('efficiency' in rec for rec in recommendations)
    
    @pytest.mark.asyncio
    async def test_publish_learning_results(self, learning_engine, mock_supabase_manager):
        """Test publishing learning results"""
        learning_results = {
            'captured_outcomes': [{'outcome_id': 'OUTCOME_1'}],
            'structured_lessons': [{'lesson_id': 'LESSON_1'}],
            'updated_braids': [{'braid_id': 'BRAID_1'}],
            'doctrine_updates': [{'update_id': 'UPDATE_1'}],
            'improvement_assessment': {
                'improvement_metrics': {'system_learning_rate': 0.8},
                'system_sharpening': {'accuracy_improvement': 0.7}
            },
            'learning_errors': []
        }
        
        await learning_engine._publish_learning_results(learning_results)
        
        # Verify strand was inserted
        mock_supabase_manager.insert_strand.assert_called_once()
        call_args = mock_supabase_manager.insert_strand.call_args[0][0]
        assert call_args['kind'] == 'cil_learning_feedback'
        assert call_args['agent_id'] == 'central_intelligence_layer'
        assert call_args['cil_team_member'] == 'learning_feedback_engine'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
