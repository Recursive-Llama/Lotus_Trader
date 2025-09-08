"""
Database-Native Resonance System

Mathematical Resonance Equations:
- φ_i = φ_(i-1) × ρ_i (fractal self-similarity)
- θ_i = θ_(i-1) + ℏ × ∑(φ_j × ρ_j) (non-local connections)
- ρ_i(t+1) = ρ_i(t) + α × ∆φ(t) (recursive feedback)

Event-driven workers that react to strand events and update resonance state.
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient
from src.llm_integration.prompt_manager import PromptManager
from src.llm_integration.database_driven_context_system import DatabaseDrivenContextSystem


@dataclass
class ResonanceState:
    """Resonance state data structure"""
    motif_id: str
    phi: float  # Motif field resonance
    rho: float  # Recursive depth/feedback factor
    theta: float  # Global context field
    phi_updated_at: datetime
    rho_updated_at: datetime
    theta_updated_at: datetime
    telemetry: Dict[str, Any]


@dataclass
class GlobalResonanceField:
    """Global resonance field state"""
    theta: float  # Global context field
    updated_at: datetime
    window: int  # Time window in hours
    delta: float  # Decay factor
    alpha: float  # Learning rate
    gamma: float  # Momentum factor
    rho_min: float  # Minimum rho value
    rho_max: float  # Maximum rho value


class TelemetryUpdater:
    """
    Worker A: Telemetry Updater
    
    Recomputes sr, cr, xr, surprise for (motif_id, context) over window W
    Trigger: lesson.created | signal.detected | experiment.result
    Action: recompute rates from strands and update MotifCard.telemetry
    """
    
    def __init__(self, supabase_manager: SupabaseManager):
        self.supabase_manager = supabase_manager
        self.window_hours = 24
        self.min_samples = 10
        
    async def update_telemetry(self, strand_event: Dict[str, Any]):
        """Update telemetry for motif based on strand event"""
        try:
            # Extract motif information from event
            motif_id = strand_event.get('motif_id')
            if not motif_id:
                return
            
            # Calculate telemetry metrics
            telemetry = await self._calculate_telemetry_metrics(motif_id)
            
            if telemetry:
                # Update motif telemetry in database
                await self._update_motif_telemetry(motif_id, telemetry)
                
                # Trigger resonance update
                await self._trigger_resonance_update(motif_id, telemetry)
                
        except Exception as e:
            print(f"Error updating telemetry: {e}")
    
    async def _calculate_telemetry_metrics(self, motif_id: str) -> Optional[Dict[str, Any]]:
        """Calculate telemetry metrics for a motif"""
        try:
            # Query for motif performance over time window
            query = """
                SELECT 
                    COUNT(*) as total_occurrences,
                    AVG(CASE WHEN outcome_score > 0 THEN 1.0 ELSE 0.0 END) as success_rate,
                    AVG(CASE WHEN sig_confidence > 0.7 THEN 1.0 ELSE 0.0 END) as confirmation_rate,
                    AVG(CASE WHEN outcome_score < -0.5 THEN 1.0 ELSE 0.0 END) as contradiction_rate,
                    AVG(sig_sigma) as avg_sigma,
                    AVG(sig_confidence) as avg_confidence
                FROM AD_strands
                WHERE motif_id = %s
                    AND created_at > NOW() - INTERVAL '%s hours'
            """
            
            result = await self.supabase_manager.execute_query(query, [motif_id, self.window_hours])
            
            if result and result[0]['total_occurrences'] >= self.min_samples:
                row = result[0]
                
                # Calculate surprise rating
                surprise = await self._calculate_surprise_rating(motif_id)
                
                telemetry = {
                    'sr': float(row['success_rate'] or 0.0),  # Success rate
                    'cr': float(row['confirmation_rate'] or 0.0),  # Confirmation rate
                    'xr': float(row['contradiction_rate'] or 0.0),  # Contradiction rate
                    'surprise': surprise,
                    'total_occurrences': int(row['total_occurrences']),
                    'avg_sigma': float(row['avg_sigma'] or 0.0),
                    'avg_confidence': float(row['avg_confidence'] or 0.0),
                    'last_updated': datetime.now(timezone.utc).isoformat()
                }
                
                return telemetry
            
            return None
            
        except Exception as e:
            print(f"Error calculating telemetry metrics: {e}")
            return None
    
    async def _calculate_surprise_rating(self, motif_id: str) -> float:
        """Calculate surprise rating for a motif"""
        try:
            # Get motif family
            query = "SELECT motif_family FROM AD_strands WHERE id = %s"
            result = await self.supabase_manager.execute_query(query, [motif_id])
            
            if not result:
                return 0.0
            
            motif_family = result[0]['motif_family']
            
            # Count similar motifs
            query = """
                SELECT COUNT(*) as similar_count
                FROM AD_strands
                WHERE motif_family = %s
                    AND created_at > NOW() - INTERVAL '24 hours'
            """
            
            result = await self.supabase_manager.execute_query(query, [motif_family])
            similar_count = result[0]['count'] if result else 0
            
            # Calculate surprise based on rarity
            if similar_count == 0:
                return 1.0
            elif similar_count < 5:
                return 0.8
            elif similar_count < 20:
                return 0.5
            else:
                return 0.2
                
        except Exception as e:
            print(f"Error calculating surprise rating: {e}")
            return 0.0
    
    async def _update_motif_telemetry(self, motif_id: str, telemetry: Dict[str, Any]):
        """Update motif telemetry in database"""
        try:
            update_data = {
                'telemetry': telemetry
            }
            
            await self.supabase_manager.update_strand(
                strand_id=motif_id,
                update_data=update_data
            )
            
        except Exception as e:
            print(f"Error updating motif telemetry: {e}")
    
    async def _trigger_resonance_update(self, motif_id: str, telemetry: Dict[str, Any]):
        """Trigger resonance update for motif"""
        try:
            # Create resonance update event
            event_data = {
                'event_type': 'telemetry_updated',
                'motif_id': motif_id,
                'telemetry': telemetry,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Store event for resonance update worker
            await self.supabase_manager.insert_strand({
                'kind': 'resonance_event',
                'module': 'alpha',
                'tags': ['resonance:telemetry_updated'],
                'event_data': event_data
            })
            
        except Exception as e:
            print(f"Error triggering resonance update: {e}")


class ResonanceUpdate:
    """
    Worker B: Resonance Update
    
    Updates φ, ρ using mathematical resonance equations
    Δφ = (sr + λ1·cr − λ2·xr) − φ_prev
    ρ = clip(ρ_prev + α·Δφ, ρ_min, ρ_max)
    φ = (1−γ)·(φ_prev · ρ) + γ·φ_prev
    """
    
    def __init__(self, supabase_manager: SupabaseManager):
        self.supabase_manager = supabase_manager
        
        # Resonance parameters
        self.lambda1 = 0.3  # Weight for confirmation rate
        self.lambda2 = 0.5  # Weight for contradiction rate
        self.alpha = 0.1    # Learning rate
        self.gamma = 0.1    # Momentum factor
        self.rho_min = 0.1  # Minimum rho value
        self.rho_max = 2.0  # Maximum rho value
        
    async def update_resonance(self, telemetry_change: Dict[str, Any]):
        """Update resonance for motif based on telemetry change"""
        try:
            motif_id = telemetry_change.get('motif_id')
            telemetry = telemetry_change.get('telemetry', {})
            
            if not motif_id or not telemetry:
                return
            
            # Get current resonance state
            current_state = await self._get_current_resonance_state(motif_id)
            
            if not current_state:
                # Initialize new resonance state
                current_state = {
                    'phi': 0.0,
                    'rho': 1.0,
                    'phi_updated_at': datetime.now(timezone.utc),
                    'rho_updated_at': datetime.now(timezone.utc)
                }
            
            # Calculate new resonance values
            new_phi, new_rho = await self._calculate_resonance_values(current_state, telemetry)
            
            # Update resonance state in database
            await self._update_resonance_state(motif_id, new_phi, new_rho)
            
            # Trigger context field update
            await self._trigger_context_field_update(motif_id, new_phi, new_rho)
            
        except Exception as e:
            print(f"Error updating resonance: {e}")
    
    async def _get_current_resonance_state(self, motif_id: str) -> Optional[Dict[str, Any]]:
        """Get current resonance state for motif"""
        try:
            query = """
                SELECT phi, rho, phi_updated_at, rho_updated_at
                FROM AD_strands
                WHERE id = %s
            """
            
            result = await self.supabase_manager.execute_query(query, [motif_id])
            
            if result:
                return {
                    'phi': result[0]['phi'] or 0.0,
                    'rho': result[0]['rho'] or 1.0,
                    'phi_updated_at': result[0]['phi_updated_at'],
                    'rho_updated_at': result[0]['rho_updated_at']
                }
            
            return None
            
        except Exception as e:
            print(f"Error getting current resonance state: {e}")
            return None
    
    async def _calculate_resonance_values(self, current_state: Dict[str, Any], telemetry: Dict[str, Any]) -> tuple[float, float]:
        """Calculate new resonance values using mathematical equations"""
        try:
            # Extract telemetry values
            sr = telemetry.get('sr', 0.0)  # Success rate
            cr = telemetry.get('cr', 0.0)  # Confirmation rate
            xr = telemetry.get('xr', 0.0)  # Contradiction rate
            surprise = telemetry.get('surprise', 0.0)
            
            # Current values
            phi_prev = current_state['phi']
            rho_prev = current_state['rho']
            
            # Calculate Δφ (change in phi)
            delta_phi = (sr + self.lambda1 * cr - self.lambda2 * xr) - phi_prev
            
            # Update ρ (recursive feedback factor)
            new_rho = rho_prev + self.alpha * delta_phi
            new_rho = max(self.rho_min, min(self.rho_max, new_rho))  # Clip to bounds
            
            # Update φ (fractal self-similarity)
            new_phi = (1 - self.gamma) * (phi_prev * new_rho) + self.gamma * phi_prev
            
            # Apply surprise boost
            new_phi = new_phi * (1 + surprise * 0.2)
            
            # Ensure phi stays in reasonable bounds
            new_phi = max(0.0, min(2.0, new_phi))
            
            return new_phi, new_rho
            
        except Exception as e:
            print(f"Error calculating resonance values: {e}")
            return current_state['phi'], current_state['rho']
    
    async def _update_resonance_state(self, motif_id: str, new_phi: float, new_rho: float):
        """Update resonance state in database"""
        try:
            now = datetime.now(timezone.utc)
            
            update_data = {
                'phi': new_phi,
                'rho': new_rho,
                'phi_updated_at': now.isoformat(),
                'rho_updated_at': now.isoformat()
            }
            
            await self.supabase_manager.update_strand(
                strand_id=motif_id,
                update_data=update_data
            )
            
            print(f"✅ Updated resonance for {motif_id}: φ={new_phi:.3f}, ρ={new_rho:.3f}")
            
        except Exception as e:
            print(f"Error updating resonance state: {e}")
    
    async def _trigger_context_field_update(self, motif_id: str, new_phi: float, new_rho: float):
        """Trigger context field update"""
        try:
            # Create context field update event
            event_data = {
                'event_type': 'resonance_updated',
                'motif_id': motif_id,
                'phi': new_phi,
                'rho': new_rho,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Store event for context field worker
            await self.supabase_manager.insert_strand({
                'kind': 'resonance_event',
                'module': 'alpha',
                'tags': ['resonance:resonance_updated'],
                'event_data': event_data
            })
            
        except Exception as e:
            print(f"Error triggering context field update: {e}")


class ContextFieldTick:
    """
    Worker C: Context Field Tick
    
    Updates global θ field
    S = Σ_active(φ · ρ)
    ħ = mean_active(surprise)
    θ = (1−δ)·θ_prev + ħ·S
    """
    
    def __init__(self, supabase_manager: SupabaseManager):
        self.supabase_manager = supabase_manager
        
        # Context field parameters
        self.delta = 0.05  # Decay factor
        self.update_interval_minutes = 10
        
    async def update_context_field(self, tick_event: Dict[str, Any]):
        """Update global context field"""
        try:
            # Get current global resonance state
            current_theta = await self._get_current_theta()
            
            # Calculate new theta
            new_theta = await self._calculate_new_theta(current_theta)
            
            # Update global theta
            await self._update_global_theta(new_theta)
            
        except Exception as e:
            print(f"Error updating context field: {e}")
    
    async def _get_current_theta(self) -> float:
        """Get current global theta value"""
        try:
            query = "SELECT theta FROM CIL_Resonance_State ORDER BY updated_at DESC LIMIT 1"
            result = await self.supabase_manager.execute_query(query)
            
            if result:
                return result[0]['theta'] or 0.0
            
            return 0.0
            
        except Exception as e:
            print(f"Error getting current theta: {e}")
            return 0.0
    
    async def _calculate_new_theta(self, current_theta: float) -> float:
        """Calculate new theta using mathematical equation"""
        try:
            # Get active motifs with their resonance values
            query = """
                SELECT phi, rho, telemetry
                FROM AD_strands
                WHERE kind = 'motif'
                    AND phi > 0.1
                    AND created_at > NOW() - INTERVAL '24 hours'
            """
            
            result = await self.supabase_manager.execute_query(query)
            
            if not result:
                return current_theta * (1 - self.delta)  # Decay if no active motifs
            
            # Calculate S = Σ_active(φ · ρ)
            S = sum(row['phi'] * row['rho'] for row in result if row['phi'] and row['rho'])
            
            # Calculate ħ = mean_active(surprise)
            surprises = []
            for row in result:
                telemetry = row.get('telemetry', {})
                if isinstance(telemetry, dict):
                    surprise = telemetry.get('surprise', 0.0)
                    surprises.append(surprise)
            
            hbar = sum(surprises) / len(surprises) if surprises else 0.0
            
            # Calculate new theta: θ = (1−δ)·θ_prev + ħ·S
            new_theta = (1 - self.delta) * current_theta + hbar * S
            
            return new_theta
            
        except Exception as e:
            print(f"Error calculating new theta: {e}")
            return current_theta
    
    async def _update_global_theta(self, new_theta: float):
        """Update global theta in database"""
        try:
            now = datetime.now(timezone.utc)
            
            # Update or insert global resonance state
            query = """
                INSERT INTO CIL_Resonance_State (theta, updated_at, window, delta, alpha, gamma, rho_min, rho_max)
                VALUES (%s, %s, 24, 0.05, 0.1, 0.1, 0.1, 2.0)
                ON CONFLICT (id) DO UPDATE SET
                    theta = EXCLUDED.theta,
                    updated_at = EXCLUDED.updated_at
            """
            
            await self.supabase_manager.execute_query(query, [new_theta, now])
            
            print(f"✅ Updated global theta: {new_theta:.3f}")
            
        except Exception as e:
            print(f"Error updating global theta: {e}")


class QueueOrdering:
    """
    Worker D: Queue Ordering
    
    Maintains resonance-prioritized experiment queue
    resonance_score = φ · ρ · surprise
    Sort candidates with family caps
    """
    
    def __init__(self, supabase_manager: SupabaseManager):
        self.supabase_manager = supabase_manager
        self.max_experiments_per_family = 3
        
    async def update_experiment_queue(self, resonance_update: Dict[str, Any]):
        """Update experiment queue based on resonance"""
        try:
            # Get all candidate experiments
            candidates = await self._get_experiment_candidates()
            
            # Calculate resonance scores
            scored_candidates = []
            for candidate in candidates:
                resonance_score = await self._calculate_resonance_score(candidate)
                scored_candidates.append({
                    'candidate': candidate,
                    'resonance_score': resonance_score
                })
            
            # Sort by resonance score
            scored_candidates.sort(key=lambda x: x['resonance_score'], reverse=True)
            
            # Apply family caps
            capped_candidates = await self._apply_family_caps(scored_candidates)
            
            # Update experiment queue
            await self._update_experiment_queue_table(capped_candidates)
            
        except Exception as e:
            print(f"Error updating experiment queue: {e}")
    
    async def _get_experiment_candidates(self) -> List[Dict[str, Any]]:
        """Get all candidate experiments"""
        try:
            query = """
                SELECT 
                    h.hypothesis_id,
                    h.hypothesis_text,
                    h.experiment_shape,
                    h.confidence,
                    m.motif_family,
                    m.phi,
                    m.rho,
                    m.telemetry
                FROM AD_strands h
                LEFT JOIN AD_strands m ON h.hypothesis_id = m.motif_id
                WHERE h.kind = 'hypothesis'
                    AND h.status = 'pending'
                ORDER BY h.created_at DESC
            """
            
            result = await self.supabase_manager.execute_query(query)
            return result
            
        except Exception as e:
            print(f"Error getting experiment candidates: {e}")
            return []
    
    async def _calculate_resonance_score(self, candidate: Dict[str, Any]) -> float:
        """Calculate resonance score for candidate"""
        try:
            phi = candidate.get('phi', 0.0) or 0.0
            rho = candidate.get('rho', 1.0) or 1.0
            telemetry = candidate.get('telemetry', {})
            
            if isinstance(telemetry, dict):
                surprise = telemetry.get('surprise', 0.0)
            else:
                surprise = 0.0
            
            # resonance_score = φ · ρ · surprise
            resonance_score = phi * rho * surprise
            
            return resonance_score
            
        except Exception as e:
            print(f"Error calculating resonance score: {e}")
            return 0.0
    
    async def _apply_family_caps(self, scored_candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply family caps to prevent over-exploration"""
        try:
            family_counts = {}
            capped_candidates = []
            
            for item in scored_candidates:
                candidate = item['candidate']
                family = candidate.get('motif_family', 'unknown')
                
                if family not in family_counts:
                    family_counts[family] = 0
                
                if family_counts[family] < self.max_experiments_per_family:
                    capped_candidates.append(item)
                    family_counts[family] += 1
            
            return capped_candidates
            
        except Exception as e:
            print(f"Error applying family caps: {e}")
            return scored_candidates
    
    async def _update_experiment_queue_table(self, capped_candidates: List[Dict[str, Any]]):
        """Update experiment queue table"""
        try:
            # Clear existing queue
            await self.supabase_manager.execute_query("DELETE FROM experiment_queue")
            
            # Insert new queue items
            for i, item in enumerate(capped_candidates):
                candidate = item['candidate']
                resonance_score = item['resonance_score']
                
                query = """
                    INSERT INTO experiment_queue (candidate_id, motif_id, context, resonance_score, created_at, family, cap_rank)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                
                await self.supabase_manager.execute_query(query, [
                    candidate['hypothesis_id'],
                    candidate.get('motif_id', ''),
                    json.dumps(candidate),
                    resonance_score,
                    datetime.now(timezone.utc),
                    candidate.get('motif_family', 'unknown'),
                    i + 1
                ])
            
            print(f"✅ Updated experiment queue with {len(capped_candidates)} candidates")
            
        except Exception as e:
            print(f"Error updating experiment queue table: {e}")


class ResonanceSystem:
    """
    Main Resonance System Coordinator
    
    Coordinates all resonance workers and manages the overall system
    """
    
    def __init__(self, supabase_manager: SupabaseManager, llm_client: OpenRouterClient):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        
        # Initialize workers
        self.telemetry_updater = TelemetryUpdater(supabase_manager)
        self.resonance_update = ResonanceUpdate(supabase_manager)
        self.context_field_tick = ContextFieldTick(supabase_manager)
        self.queue_ordering = QueueOrdering(supabase_manager)
        
        # System state
        self.is_running = False
        
    async def initialize(self):
        """Initialize the resonance system"""
        try:
            # Start main resonance loop
            asyncio.create_task(self._resonance_loop())
            
            self.is_running = True
            print("✅ ResonanceSystem initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ ResonanceSystem initialization failed: {e}")
            return False
    
    async def _resonance_loop(self):
        """Main resonance system loop"""
        while self.is_running:
            try:
                # Process resonance events
                await self._process_resonance_events()
                
                # Periodic context field update
                await self._periodic_context_field_update()
                
                # Periodic queue ordering update
                await self._periodic_queue_ordering_update()
                
                # Wait before next iteration
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                print(f"Error in resonance loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _process_resonance_events(self):
        """Process resonance events from database"""
        try:
            # Query for recent resonance events
            query = """
                SELECT * FROM AD_strands 
                WHERE kind = 'resonance_event'
                    AND created_at > NOW() - INTERVAL '5 minutes'
                ORDER BY created_at DESC
            """
            
            result = await self.supabase_manager.execute_query(query)
            
            for row in result:
                event_data = row.get('event_data', {})
                event_type = event_data.get('event_type', '')
                
                if event_type == 'telemetry_updated':
                    await self.resonance_update.update_resonance(event_data)
                elif event_type == 'resonance_updated':
                    await self.context_field_tick.update_context_field(event_data)
                    
        except Exception as e:
            print(f"Error processing resonance events: {e}")
    
    async def _periodic_context_field_update(self):
        """Periodic context field update"""
        try:
            # Check if enough time has passed
            query = "SELECT updated_at FROM CIL_Resonance_State ORDER BY updated_at DESC LIMIT 1"
            result = await self.supabase_manager.execute_query(query)
            
            if result:
                last_update = result[0]['updated_at']
                time_since_update = datetime.now(timezone.utc) - last_update
                
                if time_since_update.total_seconds() > 600:  # 10 minutes
                    await self.context_field_tick.update_context_field({})
                    
        except Exception as e:
            print(f"Error in periodic context field update: {e}")
    
    async def _periodic_queue_ordering_update(self):
        """Periodic queue ordering update"""
        try:
            # Check if enough time has passed
            query = "SELECT created_at FROM experiment_queue ORDER BY created_at DESC LIMIT 1"
            result = await self.supabase_manager.execute_query(query)
            
            if result:
                last_update = result[0]['created_at']
                time_since_update = datetime.now(timezone.utc) - last_update
                
                if time_since_update.total_seconds() > 1800:  # 30 minutes
                    await self.queue_ordering.update_experiment_queue({})
                    
        except Exception as e:
            print(f"Error in periodic queue ordering update: {e}")
    
    async def get_resonance_status(self) -> Dict[str, Any]:
        """Get current resonance system status"""
        try:
            # Get global theta
            theta_query = "SELECT theta, updated_at FROM CIL_Resonance_State ORDER BY updated_at DESC LIMIT 1"
            theta_result = await self.supabase_manager.execute_query(theta_query)
            
            # Get active motifs count
            motifs_query = "SELECT COUNT(*) as count FROM AD_strands WHERE kind = 'motif' AND phi > 0.1"
            motifs_result = await self.supabase_manager.execute_query(motifs_query)
            
            # Get experiment queue count
            queue_query = "SELECT COUNT(*) as count FROM experiment_queue"
            queue_result = await self.supabase_manager.execute_query(queue_query)
            
            return {
                'is_running': self.is_running,
                'global_theta': theta_result[0]['theta'] if theta_result else 0.0,
                'theta_updated_at': theta_result[0]['updated_at'] if theta_result else None,
                'active_motifs_count': motifs_result[0]['count'] if motifs_result else 0,
                'experiment_queue_count': queue_result[0]['count'] if queue_result else 0
            }
            
        except Exception as e:
            print(f"Error getting resonance status: {e}")
            return {'is_running': self.is_running, 'error': str(e)}
    
    async def stop(self):
        """Stop the resonance system"""
        self.is_running = False
        print("🛑 ResonanceSystem stopped")
