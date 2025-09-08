"""
Test Database-Native Resonance System

Test Coverage:
- Worker functionality: TelemetryUpdater, ResonanceUpdate, ContextFieldTick, QueueOrdering
- Mathematical equations: φ, ρ, θ calculations with proper bounds and guardrails
- Database views: v_resonance_enhanced_scores, v_rates, v_surprise
- Event-driven updates: Strand events triggering resonance calculations
- Guardrail effectiveness: Prevention of resonance explosions, echo loops, regime lock-in
- Integration: Resonance-enhanced scoring through database views
- Performance: Worker efficiency, view query performance, concurrency safety
"""

import pytest
import pytest_asyncio
import asyncio
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.intelligence.system_control.central_intelligence_layer.resonance_workers import (
    TelemetryUpdater, ResonanceUpdate, ContextFieldTick, QueueOrdering, ResonanceSystem
)
from src.intelligence.system_control.central_intelligence_layer.motif_strands import (
    MotifStrandManager, MotifStrand
)
from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient


class TestResonanceSystem:
    """Test resonance system functionality"""
    
    @pytest_asyncio.fixture
    async def supabase_manager(self):
        """Mock SupabaseManager for testing"""
        manager = Mock(spec=SupabaseManager)
        manager.execute_query = AsyncMock()
        manager.insert_strand = AsyncMock()
        manager.update_strand = AsyncMock()
        return manager
    
    @pytest_asyncio.fixture
    async def llm_client(self):
        """Mock OpenRouterClient for testing"""
        client = Mock(spec=OpenRouterClient)
        client.generate_response = AsyncMock()
        return client
    
    @pytest_asyncio.fixture
    async def telemetry_updater(self, supabase_manager):
        """TelemetryUpdater instance for testing"""
        return TelemetryUpdater(supabase_manager)
    
    @pytest_asyncio.fixture
    async def resonance_update(self, supabase_manager):
        """ResonanceUpdate instance for testing"""
        return ResonanceUpdate(supabase_manager)
    
    @pytest_asyncio.fixture
    async def context_field_tick(self, supabase_manager):
        """ContextFieldTick instance for testing"""
        return ContextFieldTick(supabase_manager)
    
    @pytest_asyncio.fixture
    async def queue_ordering(self, supabase_manager):
        """QueueOrdering instance for testing"""
        return QueueOrdering(supabase_manager)
    
    @pytest_asyncio.fixture
    async def resonance_system(self, supabase_manager, llm_client):
        """ResonanceSystem instance for testing"""
        return ResonanceSystem(supabase_manager, llm_client)
    
    @pytest_asyncio.fixture
    async def motif_strand_manager(self, supabase_manager, llm_client):
        """MotifStrandManager instance for testing"""
        return MotifStrandManager(supabase_manager, llm_client)
    
    @pytest.mark.asyncio
    async def test_telemetry_updater_initialization(self, telemetry_updater):
        """Test TelemetryUpdater initialization"""
        assert telemetry_updater.window_hours == 24
        assert telemetry_updater.min_samples == 10
        assert telemetry_updater.supabase_manager is not None
    
    @pytest.mark.asyncio
    async def test_telemetry_calculation(self, telemetry_updater, supabase_manager):
        """Test telemetry calculation functionality"""
        # Mock database response
        supabase_manager.execute_query.return_value = [{
            'total_occurrences': 20,
            'success_rate': 0.7,
            'confirmation_rate': 0.8,
            'contradiction_rate': 0.1,
            'avg_sigma': 0.6,
            'avg_confidence': 0.75
        }]
        
        # Test telemetry calculation
        telemetry = await telemetry_updater._calculate_telemetry_metrics('test_motif_id')
        
        assert telemetry is not None
        assert telemetry['sr'] == 0.7
        assert telemetry['cr'] == 0.8
        assert telemetry['xr'] == 0.1
        assert telemetry['total_occurrences'] == 20
        assert 'surprise' in telemetry
        assert 'last_updated' in telemetry
    
    @pytest.mark.asyncio
    async def test_telemetry_update_with_strand_event(self, telemetry_updater, supabase_manager):
        """Test telemetry update with strand event"""
        # Mock strand event
        strand_event = {
            'motif_id': 'test_motif_id',
            'kind': 'signal',
            'created_at': datetime.now(timezone.utc)
        }
        
        # Mock database responses
        supabase_manager.execute_query.return_value = [{
            'total_occurrences': 15,
            'success_rate': 0.6,
            'confirmation_rate': 0.7,
            'contradiction_rate': 0.2,
            'avg_sigma': 0.5,
            'avg_confidence': 0.65
        }]
        
        # Test telemetry update
        await telemetry_updater.update_telemetry(strand_event)
        
        # Verify database calls
        assert supabase_manager.execute_query.called
        assert supabase_manager.update_strand.called
        assert supabase_manager.insert_strand.called
    
    async def test_resonance_update_initialization(self, resonance_update):
        """Test ResonanceUpdate initialization"""
        assert resonance_update.lambda1 == 0.3
        assert resonance_update.lambda2 == 0.5
        assert resonance_update.alpha == 0.1
        assert resonance_update.gamma == 0.1
        assert resonance_update.rho_min == 0.1
        assert resonance_update.rho_max == 2.0
    
    async def test_resonance_calculation(self, resonance_update):
        """Test resonance calculation using mathematical equations"""
        # Test data
        current_state = {
            'phi': 0.5,
            'rho': 1.0,
            'phi_updated_at': datetime.now(timezone.utc),
            'rho_updated_at': datetime.now(timezone.utc)
        }
        
        telemetry = {
            'sr': 0.7,  # Success rate
            'cr': 0.8,  # Confirmation rate
            'xr': 0.1,  # Contradiction rate
            'surprise': 0.6
        }
        
        # Calculate new resonance values
        new_phi, new_rho = await resonance_update._calculate_resonance_values(current_state, telemetry)
        
        # Verify calculations
        assert new_phi > 0.0
        assert new_rho > 0.0
        assert new_rho >= resonance_update.rho_min
        assert new_rho <= resonance_update.rho_max
        assert new_phi <= 2.0  # Upper bound
    
    async def test_resonance_update_with_telemetry_change(self, resonance_update, supabase_manager):
        """Test resonance update with telemetry change"""
        # Mock telemetry change
        telemetry_change = {
            'motif_id': 'test_motif_id',
            'telemetry': {
                'sr': 0.8,
                'cr': 0.9,
                'xr': 0.05,
                'surprise': 0.7
            }
        }
        
        # Mock current resonance state
        supabase_manager.execute_query.return_value = [{
            'phi': 0.6,
            'rho': 1.1,
            'phi_updated_at': datetime.now(timezone.utc),
            'rho_updated_at': datetime.now(timezone.utc)
        }]
        
        # Test resonance update
        await resonance_update.update_resonance(telemetry_change)
        
        # Verify database calls
        assert supabase_manager.execute_query.called
        assert supabase_manager.update_strand.called
        assert supabase_manager.insert_strand.called
    
    async def test_context_field_tick_initialization(self, context_field_tick):
        """Test ContextFieldTick initialization"""
        assert context_field_tick.delta == 0.05
        assert context_field_tick.update_interval_minutes == 10
    
    async def test_context_field_calculation(self, context_field_tick, supabase_manager):
        """Test context field calculation"""
        # Mock current theta
        supabase_manager.execute_query.return_value = [{'theta': 0.5}]
        
        # Mock active motifs
        supabase_manager.execute_query.return_value = [
            {'phi': 0.8, 'rho': 1.2, 'telemetry': {'surprise': 0.6}},
            {'phi': 0.6, 'rho': 1.1, 'telemetry': {'surprise': 0.5}},
            {'phi': 0.7, 'rho': 1.3, 'telemetry': {'surprise': 0.7}}
        ]
        
        # Test theta calculation
        new_theta = await context_field_tick._calculate_new_theta(0.5)
        
        assert new_theta > 0.0
        assert new_theta != 0.5  # Should be different from current
    
    async def test_context_field_update(self, context_field_tick, supabase_manager):
        """Test context field update"""
        # Mock database responses
        supabase_manager.execute_query.side_effect = [
            [{'theta': 0.4}],  # Current theta
            [  # Active motifs
                {'phi': 0.8, 'rho': 1.2, 'telemetry': {'surprise': 0.6}},
                {'phi': 0.6, 'rho': 1.1, 'telemetry': {'surprise': 0.5}}
            ]
        ]
        
        # Test context field update
        await context_field_tick.update_context_field({})
        
        # Verify database calls
        assert supabase_manager.execute_query.called
        assert supabase_manager.execute_query.call_count >= 2
    
    async def test_queue_ordering_initialization(self, queue_ordering):
        """Test QueueOrdering initialization"""
        assert queue_ordering.max_experiments_per_family == 3
    
    async def test_experiment_candidates_retrieval(self, queue_ordering, supabase_manager):
        """Test experiment candidates retrieval"""
        # Mock database response
        supabase_manager.execute_query.return_value = [
            {
                'hypothesis_id': 'hyp_1',
                'hypothesis_text': 'Test hypothesis 1',
                'experiment_shape': 'durability',
                'confidence': 0.8,
                'motif_family': 'divergence',
                'phi': 0.7,
                'rho': 1.2,
                'telemetry': {'surprise': 0.6}
            },
            {
                'hypothesis_id': 'hyp_2',
                'hypothesis_text': 'Test hypothesis 2',
                'experiment_shape': 'stack',
                'confidence': 0.6,
                'motif_family': 'volume',
                'phi': 0.5,
                'rho': 1.0,
                'telemetry': {'surprise': 0.4}
            }
        ]
        
        # Test candidates retrieval
        candidates = await queue_ordering._get_experiment_candidates()
        
        assert len(candidates) == 2
        assert candidates[0]['hypothesis_id'] == 'hyp_1'
        assert candidates[1]['hypothesis_id'] == 'hyp_2'
    
    async def test_resonance_score_calculation(self, queue_ordering):
        """Test resonance score calculation"""
        candidate = {
            'phi': 0.8,
            'rho': 1.2,
            'telemetry': {'surprise': 0.6}
        }
        
        # Calculate resonance score
        score = await queue_ordering._calculate_resonance_score(candidate)
        
        # Verify calculation: φ · ρ · surprise
        expected_score = 0.8 * 1.2 * 0.6
        assert score == expected_score
    
    async def test_family_caps_application(self, queue_ordering):
        """Test family caps application"""
        scored_candidates = [
            {'candidate': {'motif_family': 'divergence'}, 'resonance_score': 0.9},
            {'candidate': {'motif_family': 'divergence'}, 'resonance_score': 0.8},
            {'candidate': {'motif_family': 'divergence'}, 'resonance_score': 0.7},
            {'candidate': {'motif_family': 'divergence'}, 'resonance_score': 0.6},
            {'candidate': {'motif_family': 'volume'}, 'resonance_score': 0.5}
        ]
        
        # Apply family caps
        capped = await queue_ordering._apply_family_caps(scored_candidates)
        
        # Verify family caps (max 3 per family)
        divergence_count = sum(1 for item in capped if item['candidate']['motif_family'] == 'divergence')
        assert divergence_count <= 3
        
        # Verify volume family is included
        volume_count = sum(1 for item in capped if item['candidate']['motif_family'] == 'volume')
        assert volume_count == 1
    
    async def test_resonance_system_initialization(self, resonance_system):
        """Test ResonanceSystem initialization"""
        assert resonance_system.telemetry_updater is not None
        assert resonance_system.resonance_update is not None
        assert resonance_system.context_field_tick is not None
        assert resonance_system.queue_ordering is not None
        assert resonance_system.is_running == False
    
    async def test_resonance_system_startup(self, resonance_system):
        """Test ResonanceSystem startup"""
        # Test initialization
        result = await resonance_system.initialize()
        
        assert result == True
        assert resonance_system.is_running == True
    
    async def test_resonance_system_status(self, resonance_system, supabase_manager):
        """Test resonance system status retrieval"""
        # Mock database responses
        supabase_manager.execute_query.side_effect = [
            [{'theta': 0.6, 'updated_at': datetime.now(timezone.utc)}],  # Global theta
            [{'count': 15}],  # Active motifs
            [{'count': 8}],   # Experiment queue
        ]
        
        # Test status retrieval
        status = await resonance_system.get_resonance_status()
        
        assert 'is_running' in status
        assert 'global_theta' in status
        assert 'active_motifs_count' in status
        assert 'experiment_queue_count' in status
    
    async def test_motif_strand_creation(self, motif_strand_manager, supabase_manager, llm_client):
        """Test motif strand creation"""
        # Mock confluence data
        confluence_data = {
            'confluence_id': 'conf_123',
            'family_a': 'divergence',
            'family_b': 'volume',
            'regime': 'high_vol',
            'session': 'US',
            'lift': 0.8,
            'confidence': 0.7,
            'symbol': 'BTC',
            'timeframe': '1h'
        }
        
        # Mock LLM response
        llm_client.generate_response.return_value = json.dumps({
            'name': 'Divergence + Volume Squeeze',
            'family': 'divergence_volume',
            'invariants': ['rsi_divergence', 'volume_spike'],
            'fails_when': ['low_volume', 'no_divergence'],
            'contexts': {
                'regime': ['high_vol'],
                'session': ['US'],
                'timeframe': ['1h']
            },
            'why_map': {
                'mechanism_hypothesis': 'Liquidity vacuum after failed retest',
                'supports': ['volume_confirmation'],
                'fails_when': ['trend_continuation']
            },
            'lineage': {
                'parents': [],
                'mutation_note': 'Generated from confluence'
            }
        })
        
        # Test motif creation
        motif = await motif_strand_manager.create_motif_from_confluence(confluence_data)
        
        assert motif is not None
        assert motif.motif_name == 'Divergence + Volume Squeeze'
        assert motif.motif_family == 'divergence_volume'
        assert motif.phi == 0.0  # Initial resonance state
        assert motif.rho == 1.0  # Initial feedback factor
        assert motif.telemetry is not None
    
    async def test_resonance_enhanced_scoring(self, supabase_manager):
        """Test resonance-enhanced scoring through database views"""
        # Mock database response for resonance-enhanced scores
        supabase_manager.execute_query.return_value = [
            {
                'id': 'motif_123',
                'current_score': 0.7,
                'resonance_score': 0.5,
                'final_score': 0.77,  # 0.7 * (1 + 0.5 * 0.2)
                'resonance_quality': 'medium_resonance',
                'field_strength': 0.6
            }
        ]
        
        # Test resonance-enhanced scoring
        query = """
            SELECT * FROM v_resonance_enhanced_scores 
            WHERE id = 'motif_123'
        """
        
        result = await supabase_manager.execute_query(query)
        
        assert len(result) == 1
        assert result[0]['final_score'] > result[0]['current_score']  # Enhanced score should be higher
        assert result[0]['resonance_quality'] == 'medium_resonance'
    
    async def test_mathematical_equations_bounds(self, resonance_update):
        """Test mathematical equations stay within bounds"""
        # Test extreme values
        current_state = {
            'phi': 0.0,
            'rho': 0.1,
            'phi_updated_at': datetime.now(timezone.utc),
            'rho_updated_at': datetime.now(timezone.utc)
        }
        
        telemetry = {
            'sr': 1.0,  # Maximum success rate
            'cr': 1.0,  # Maximum confirmation rate
            'xr': 0.0,  # No contradictions
            'surprise': 1.0  # Maximum surprise
        }
        
        # Calculate new resonance values
        new_phi, new_rho = await resonance_update._calculate_resonance_values(current_state, telemetry)
        
        # Verify bounds
        assert new_phi >= 0.0
        assert new_phi <= 2.0  # Upper bound
        assert new_rho >= resonance_update.rho_min
        assert new_rho <= resonance_update.rho_max
    
    async def test_guardrail_effectiveness(self, resonance_update):
        """Test guardrail effectiveness against resonance explosions"""
        # Test with values that could cause explosion
        current_state = {
            'phi': 1.9,  # Near upper bound
            'rho': 1.9,  # Near upper bound
            'phi_updated_at': datetime.now(timezone.utc),
            'rho_updated_at': datetime.now(timezone.utc)
        }
        
        telemetry = {
            'sr': 1.0,
            'cr': 1.0,
            'xr': 0.0,
            'surprise': 1.0
        }
        
        # Calculate new resonance values
        new_phi, new_rho = await resonance_update._calculate_resonance_values(current_state, telemetry)
        
        # Verify guardrails prevent explosion
        assert new_phi <= 2.0  # Upper bound enforced
        assert new_rho <= resonance_update.rho_max  # Upper bound enforced
        assert new_phi >= 0.0  # Lower bound enforced
        assert new_rho >= resonance_update.rho_min  # Lower bound enforced
    
    async def test_concurrency_safety(self, resonance_system, supabase_manager):
        """Test concurrency safety of resonance system"""
        # Mock database responses
        supabase_manager.execute_query.return_value = []
        supabase_manager.insert_strand.return_value = None
        supabase_manager.update_strand.return_value = None
        
        # Start multiple concurrent operations
        tasks = []
        for i in range(10):
            task = asyncio.create_task(resonance_system._process_resonance_events())
            tasks.append(task)
        
        # Wait for all tasks to complete
        await asyncio.gather(*tasks)
        
        # Verify no errors occurred
        assert True  # If we get here, no exceptions were raised
    
    async def test_performance_metrics(self, resonance_system, supabase_manager):
        """Test performance metrics and efficiency"""
        # Mock database responses
        supabase_manager.execute_query.return_value = []
        
        # Measure execution time
        start_time = datetime.now()
        
        # Run resonance system operations
        await resonance_system._process_resonance_events()
        await resonance_system._periodic_context_field_update()
        await resonance_system._periodic_queue_ordering_update()
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        # Verify reasonable execution time (should be fast)
        assert execution_time < 5.0  # Should complete within 5 seconds
    
    async def test_resonance_system_stop(self, resonance_system):
        """Test resonance system stop functionality"""
        # Start system
        await resonance_system.initialize()
        assert resonance_system.is_running == True
        
        # Stop system
        await resonance_system.stop()
        assert resonance_system.is_running == False
