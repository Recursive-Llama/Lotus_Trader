"""
Simple test for resonance system functionality
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock

from src.intelligence.system_control.central_intelligence_layer.resonance_workers import (
    TelemetryUpdater, ResonanceUpdate, ContextFieldTick, QueueOrdering, ResonanceSystem
)
from src.intelligence.system_control.central_intelligence_layer.motif_strands import (
    MotifStrandManager, MotifStrand
)


class TestResonanceSimple:
    """Simple tests for resonance system"""
    
    @pytest_asyncio.fixture
    async def supabase_manager(self):
        """Mock SupabaseManager for testing"""
        manager = Mock()
        manager.execute_query = AsyncMock()
        manager.insert_strand = AsyncMock()
        manager.update_strand = AsyncMock()
        return manager
    
    @pytest_asyncio.fixture
    async def llm_client(self):
        """Mock OpenRouterClient for testing"""
        client = Mock()
        client.generate_response = AsyncMock()
        return client
    
    @pytest.mark.asyncio
    async def test_telemetry_updater_initialization(self, supabase_manager):
        """Test TelemetryUpdater initialization"""
        updater = TelemetryUpdater(supabase_manager)
        assert updater.window_hours == 24
        assert updater.min_samples == 10
        assert updater.supabase_manager is not None
    
    @pytest.mark.asyncio
    async def test_resonance_update_initialization(self, supabase_manager):
        """Test ResonanceUpdate initialization"""
        updater = ResonanceUpdate(supabase_manager)
        assert updater.lambda1 == 0.3
        assert updater.lambda2 == 0.5
        assert updater.alpha == 0.1
        assert updater.gamma == 0.1
        assert updater.rho_min == 0.1
        assert updater.rho_max == 2.0
    
    @pytest.mark.asyncio
    async def test_context_field_tick_initialization(self, supabase_manager):
        """Test ContextFieldTick initialization"""
        tick = ContextFieldTick(supabase_manager)
        assert tick.delta == 0.05
        assert tick.update_interval_minutes == 10
    
    @pytest.mark.asyncio
    async def test_queue_ordering_initialization(self, supabase_manager):
        """Test QueueOrdering initialization"""
        ordering = QueueOrdering(supabase_manager)
        assert ordering.max_experiments_per_family == 3
    
    @pytest.mark.asyncio
    async def test_resonance_system_initialization(self, supabase_manager, llm_client):
        """Test ResonanceSystem initialization"""
        system = ResonanceSystem(supabase_manager, llm_client)
        assert system.telemetry_updater is not None
        assert system.resonance_update is not None
        assert system.context_field_tick is not None
        assert system.queue_ordering is not None
        assert system.is_running == False
    
    @pytest.mark.asyncio
    async def test_motif_strand_manager_initialization(self, supabase_manager, llm_client):
        """Test MotifStrandManager initialization"""
        manager = MotifStrandManager(supabase_manager, llm_client)
        assert manager.supabase_manager is not None
        assert manager.llm_client is not None
        assert manager.resonance_threshold == 0.6
        assert manager.telemetry_window_hours == 24
    
    @pytest.mark.asyncio
    async def test_resonance_calculation(self, supabase_manager):
        """Test resonance calculation using mathematical equations"""
        updater = ResonanceUpdate(supabase_manager)
        
        # Test data
        current_state = {
            'phi': 0.5,
            'rho': 1.0,
            'phi_updated_at': None,
            'rho_updated_at': None
        }
        
        telemetry = {
            'sr': 0.7,  # Success rate
            'cr': 0.8,  # Confirmation rate
            'xr': 0.1,  # Contradiction rate
            'surprise': 0.6
        }
        
        # Calculate new resonance values
        new_phi, new_rho = await updater._calculate_resonance_values(current_state, telemetry)
        
        # Verify calculations
        assert new_phi > 0.0
        assert new_rho > 0.0
        assert new_rho >= updater.rho_min
        assert new_rho <= updater.rho_max
        assert new_phi <= 2.0  # Upper bound
    
    @pytest.mark.asyncio
    async def test_resonance_score_calculation(self, supabase_manager):
        """Test resonance score calculation"""
        ordering = QueueOrdering(supabase_manager)
        
        candidate = {
            'phi': 0.8,
            'rho': 1.2,
            'telemetry': {'surprise': 0.6}
        }
        
        # Calculate resonance score
        score = await ordering._calculate_resonance_score(candidate)
        
        # Verify calculation: φ · ρ · surprise
        expected_score = 0.8 * 1.2 * 0.6
        assert score == expected_score
    
    @pytest.mark.asyncio
    async def test_family_caps_application(self, supabase_manager):
        """Test family caps application"""
        ordering = QueueOrdering(supabase_manager)
        
        scored_candidates = [
            {'candidate': {'motif_family': 'divergence'}, 'resonance_score': 0.9},
            {'candidate': {'motif_family': 'divergence'}, 'resonance_score': 0.8},
            {'candidate': {'motif_family': 'divergence'}, 'resonance_score': 0.7},
            {'candidate': {'motif_family': 'divergence'}, 'resonance_score': 0.6},
            {'candidate': {'motif_family': 'volume'}, 'resonance_score': 0.5}
        ]
        
        # Apply family caps
        capped = await ordering._apply_family_caps(scored_candidates)
        
        # Verify family caps (max 3 per family)
        divergence_count = sum(1 for item in capped if item['candidate']['motif_family'] == 'divergence')
        assert divergence_count <= 3
        
        # Verify volume family is included
        volume_count = sum(1 for item in capped if item['candidate']['motif_family'] == 'volume')
        assert volume_count == 1
    
    @pytest.mark.asyncio
    async def test_mathematical_equations_bounds(self, supabase_manager):
        """Test mathematical equations stay within bounds"""
        updater = ResonanceUpdate(supabase_manager)
        
        # Test extreme values
        current_state = {
            'phi': 0.0,
            'rho': 0.1,
            'phi_updated_at': None,
            'rho_updated_at': None
        }
        
        telemetry = {
            'sr': 1.0,  # Maximum success rate
            'cr': 1.0,  # Maximum confirmation rate
            'xr': 0.0,  # No contradictions
            'surprise': 1.0  # Maximum surprise
        }
        
        # Calculate new resonance values
        new_phi, new_rho = await updater._calculate_resonance_values(current_state, telemetry)
        
        # Verify bounds
        assert new_phi >= 0.0
        assert new_phi <= 2.0  # Upper bound
        assert new_rho >= updater.rho_min
        assert new_rho <= updater.rho_max
    
    @pytest.mark.asyncio
    async def test_guardrail_effectiveness(self, supabase_manager):
        """Test guardrail effectiveness against resonance explosions"""
        updater = ResonanceUpdate(supabase_manager)
        
        # Test with values that could cause explosion
        current_state = {
            'phi': 1.9,  # Near upper bound
            'rho': 1.9,  # Near upper bound
            'phi_updated_at': None,
            'rho_updated_at': None
        }
        
        telemetry = {
            'sr': 1.0,
            'cr': 1.0,
            'xr': 0.0,
            'surprise': 1.0
        }
        
        # Calculate new resonance values
        new_phi, new_rho = await updater._calculate_resonance_values(current_state, telemetry)
        
        # Verify guardrails prevent explosion
        assert new_phi <= 2.0  # Upper bound enforced
        assert new_rho <= updater.rho_max  # Upper bound enforced
        assert new_phi >= 0.0  # Lower bound enforced
        assert new_rho >= updater.rho_min  # Lower bound enforced

