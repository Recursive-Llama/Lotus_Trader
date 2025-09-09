"""
Motif Cards as Specialized Strands

Key Insight: Motif Cards are specialized strands with pattern metadata, not separate objects.
- All patterns flow through same strand system
- Vector search integration for motifs
- LLM lesson generation for pattern evolution
- Resonance integration with φ, ρ, θ calculations
- Lineage tracking through strand hierarchy
- Meta-signal generation from motifs
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
class MotifStrand:
    """Motif Card as Specialized Strand data structure"""
    # Standard strand fields
    id: str
    symbol: str
    timeframe: str
    session_bucket: str
    regime: str
    tags: List[str]
    created_at: datetime
    
    # Pattern-specific fields
    motif_name: str
    motif_family: str
    invariants: List[str]
    fails_when: List[str]
    contexts: Dict[str, Any]
    evidence_refs: List[str]
    why_map: Dict[str, Any]
    lineage: Dict[str, Any]
    
    # Resonance state (from database-native resonance system)
    phi: float = 0.0  # Motif field resonance
    rho: float = 1.0  # Recursive depth/feedback factor
    phi_updated_at: Optional[datetime] = None
    rho_updated_at: Optional[datetime] = None
    telemetry: Optional[Dict[str, Any]] = None
    
    # Standard strand scoring
    sig_sigma: float = 0.0
    sig_confidence: float = 0.0
    sig_direction: str = 'neutral'
    outcome_score: float = 0.0
    
    # Default fields
    kind: str = 'motif'
    module: str = 'alpha'


class MotifStrandManager:
    """
    Motif Strand Manager
    
    Responsibilities:
    - Create motif cards as specialized strands
    - Manage motif lineage and evolution
    - Integrate with resonance system
    - Generate meta-signals from motifs
    - Handle motif clustering and learning
    """
    
    def __init__(self, supabase_manager: SupabaseManager, llm_client: OpenRouterClient):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.prompt_manager = PromptManager()
        self.context_system = DatabaseDrivenContextSystem(supabase_manager)
        
        # Motif Management
        self.active_motifs: Dict[str, MotifStrand] = {}
        self.motif_lineage: Dict[str, List[str]] = {}  # parent -> children
        
        # Resonance Integration
        self.resonance_threshold = 0.6
        self.telemetry_window_hours = 24
        
    async def initialize(self):
        """Initialize the motif strand manager"""
        try:
            # Load existing motifs
            await self._load_existing_motifs()
            
            # Start motif monitoring loop
            asyncio.create_task(self._motif_monitoring_loop())
            
            print("✅ MotifStrandManager initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ MotifStrandManager initialization failed: {e}")
            return False
    
    async def _motif_monitoring_loop(self):
        """Main motif monitoring loop"""
        while True:
            try:
                # Update motif telemetry
                await self._update_motif_telemetry()
                
                # Check for motif evolution
                await self._check_motif_evolution()
                
                # Generate motif meta-signals
                await self._generate_motif_meta_signals()
                
                # Wait before next iteration
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                print(f"Error in motif monitoring loop: {e}")
                await asyncio.sleep(600)  # Wait 10 minutes on error
    
    async def create_motif_from_confluence(self, confluence_data: Dict[str, Any]) -> Optional[MotifStrand]:
        """Create motif strand from confluence data"""
        try:
            # Generate motif using LLM
            motif_data = await self._generate_motif_data(confluence_data)
            
            if not motif_data:
                return None
            
            # Create motif strand
            motif_id = f"motif_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            motif = MotifStrand(
                id=motif_id,
                symbol=confluence_data.get('symbol', 'BTC'),
                timeframe=confluence_data.get('timeframe', '1h'),
                session_bucket=confluence_data.get('session', 'US'),
                regime=confluence_data.get('regime', 'high_vol'),
                tags=[f"agent:central_intelligence:motif_miner:pattern_discovered"],
                created_at=datetime.now(timezone.utc),
                
                # Pattern-specific fields
                motif_name=motif_data.get('name', ''),
                motif_family=motif_data.get('family', 'confluence'),
                invariants=motif_data.get('invariants', []),
                fails_when=motif_data.get('fails_when', []),
                contexts=motif_data.get('contexts', {}),
                evidence_refs=[confluence_data.get('confluence_id', '')],
                why_map=motif_data.get('why_map', {}),
                lineage=motif_data.get('lineage', {'parents': [], 'mutation_note': 'Generated from confluence'}),
                
                # Resonance state
                phi=0.0,
                rho=1.0,
                phi_updated_at=datetime.now(timezone.utc),
                rho_updated_at=datetime.now(timezone.utc),
                telemetry={'sr': 0.0, 'cr': 0.0, 'xr': 0.0, 'surprise': 0.0},
                
                # Standard scoring
                sig_sigma=confluence_data.get('lift', 0.0),
                sig_confidence=confluence_data.get('confidence', 0.0),
                sig_direction='positive' if confluence_data.get('lift', 0.0) > 0 else 'negative',
                outcome_score=0.0
            )
            
            # Store motif
            self.active_motifs[motif_id] = motif
            
            # Publish motif strand
            await self._publish_motif_strand(motif)
            
            print(f"✅ Created motif strand {motif_id}: {motif.motif_name}")
            return motif
            
        except Exception as e:
            print(f"Error creating motif from confluence: {e}")
            return None
    
    async def _generate_motif_data(self, confluence_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate motif data using LLM"""
        try:
            # Create prompt for motif generation
            prompt = f"""
            Create a motif card for this confluence pattern:
            
            Confluence Data: {json.dumps(confluence_data, indent=2)}
            
            Generate:
            1. Motif name (descriptive, memorable)
            2. Motif family (category like 'divergence_volume', 'momentum_reversal', etc.)
            3. Invariants (what must be present for the pattern to work)
            4. Fails when (what breaks the pattern)
            5. Contexts (regime, session, timeframe requirements)
            6. Why map (mechanism hypothesis, supports, fails_when)
            7. Lineage (parent patterns, mutation note)
            
            Return as JSON:
            {{
                "name": "descriptive motif name",
                "family": "motif_family_category",
                "invariants": ["invariant1", "invariant2", ...],
                "fails_when": ["failure_condition1", "failure_condition2", ...],
                "contexts": {{
                    "regime": ["high_vol", "sideways"],
                    "session": ["US", "EU"],
                    "timeframe": ["1h", "4h"]
                }},
                "why_map": {{
                    "mechanism_hypothesis": "explanation of why this works",
                    "supports": ["supporting_evidence1", "supporting_evidence2", ...],
                    "fails_when": ["failure_condition1", "failure_condition2", ...]
                }},
                "lineage": {{
                    "parents": ["parent_motif_id1", "parent_motif_id2"],
                    "mutation_note": "how this evolved from parents"
                }}
            }}
            """
            
            response = await self.llm_client.generate_response(
                prompt=prompt,
                model="anthropic/claude-3.5-sonnet",
                max_tokens=800,
                temperature=0.3
            )
            
            # Parse response
            try:
                motif_data = json.loads(response)
                return motif_data
                
            except json.JSONDecodeError:
                print(f"Failed to parse LLM response for motif: {response}")
                return None
                
        except Exception as e:
            print(f"Error generating motif data: {e}")
            return None
    
    async def _publish_motif_strand(self, motif: MotifStrand):
        """Publish motif strand to database"""
        try:
            strand_data = {
                'kind': motif.kind,
                'module': motif.module,
                'symbol': motif.symbol,
                'timeframe': motif.timeframe,
                'session_bucket': motif.session_bucket,
                'regime': motif.regime,
                'tags': motif.tags,
                'created_at': motif.created_at.isoformat(),
                
                # Pattern-specific fields
                'motif_name': motif.motif_name,
                'motif_family': motif.motif_family,
                'invariants': motif.invariants,
                'fails_when': motif.fails_when,
                'contexts': motif.contexts,
                'evidence_refs': motif.evidence_refs,
                'why_map': motif.why_map,
                'lineage': motif.lineage,
                
                # Resonance state
                'phi': motif.phi,
                'rho': motif.rho,
                'phi_updated_at': motif.phi_updated_at.isoformat() if motif.phi_updated_at else None,
                'rho_updated_at': motif.rho_updated_at.isoformat() if motif.rho_updated_at else None,
                'telemetry': motif.telemetry,
                
                # Standard scoring
                'sig_sigma': motif.sig_sigma,
                'sig_confidence': motif.sig_confidence,
                'sig_direction': motif.sig_direction,
                'outcome_score': motif.outcome_score,
                
                'team_member': 'motif_strand_manager'
            }
            
            await self.supabase_manager.insert_strand(strand_data)
            
        except Exception as e:
            print(f"Error publishing motif strand: {e}")
    
    async def _update_motif_telemetry(self):
        """Update motif telemetry (sr, cr, xr, surprise)"""
        try:
            for motif_id, motif in self.active_motifs.items():
                # Calculate telemetry metrics
                telemetry = await self._calculate_motif_telemetry(motif)
                
                if telemetry:
                    motif.telemetry = telemetry
                    
                    # Update in database
                    await self._update_motif_in_database(motif)
                    
        except Exception as e:
            print(f"Error updating motif telemetry: {e}")
    
    async def _calculate_motif_telemetry(self, motif: MotifStrand) -> Optional[Dict[str, Any]]:
        """Calculate telemetry metrics for a motif"""
        try:
            # Query for motif performance over time window
            query = """
                SELECT 
                    COUNT(*) as total_occurrences,
                    AVG(CASE WHEN outcome_score > 0 THEN 1.0 ELSE 0.0 END) as success_rate,
                    AVG(CASE WHEN sig_confidence > 0.7 THEN 1.0 ELSE 0.0 END) as confirmation_rate,
                    AVC(CASE WHEN outcome_score < -0.5 THEN 1.0 ELSE 0.0 END) as contradiction_rate
                FROM AD_strands
                WHERE motif_name = %s
                    AND created_at > NOW() - INTERVAL '%s hours'
            """
            
            result = await self.supabase_manager.execute_query(query, [motif.motif_name, self.telemetry_window_hours])
            
            if result and result[0]['total_occurrences'] > 0:
                row = result[0]
                
                # Calculate surprise rating (how unexpected the pattern is)
                surprise = await self._calculate_surprise_rating(motif)
                
                telemetry = {
                    'sr': float(row['success_rate'] or 0.0),  # Success rate
                    'cr': float(row['confirmation_rate'] or 0.0),  # Confirmation rate
                    'xr': float(row['contradiction_rate'] or 0.0),  # Contradiction rate
                    'surprise': surprise,
                    'total_occurrences': int(row['total_occurrences']),
                    'last_updated': datetime.now(timezone.utc).isoformat()
                }
                
                return telemetry
            
            return None
            
        except Exception as e:
            print(f"Error calculating motif telemetry: {e}")
            return None
    
    async def _calculate_surprise_rating(self, motif: MotifStrand) -> float:
        """Calculate surprise rating for a motif"""
        try:
            # Simple surprise calculation based on novelty and unexpectedness
            # This could be enhanced with more sophisticated algorithms
            
            # Check how often this motif appears vs similar motifs
            query = """
                SELECT COUNT(*) as similar_count
                FROM AD_strands
                WHERE motif_family = %s
                    AND created_at > NOW() - INTERVAL '24 hours'
            """
            
            result = await self.supabase_manager.execute_query(query, [motif.motif_family])
            similar_count = result[0]['count'] if result else 0
            
            # Calculate surprise based on rarity and unexpectedness
            if similar_count == 0:
                surprise = 1.0  # Very surprising if no similar patterns
            elif similar_count < 5:
                surprise = 0.8  # High surprise for rare patterns
            elif similar_count < 20:
                surprise = 0.5  # Medium surprise
            else:
                surprise = 0.2  # Low surprise for common patterns
            
            return surprise
            
        except Exception as e:
            print(f"Error calculating surprise rating: {e}")
            return 0.0
    
    async def _check_motif_evolution(self):
        """Check for motif evolution and create new variants"""
        try:
            for motif_id, motif in self.active_motifs.items():
                # Check if motif has evolved significantly
                if await self._should_evolve_motif(motif):
                    # Create evolved motif
                    evolved_motif = await self._evolve_motif(motif)
                    
                    if evolved_motif:
                        # Store evolved motif
                        self.active_motifs[evolved_motif.id] = evolved_motif
                        
                        # Update lineage
                        if motif_id not in self.motif_lineage:
                            self.motif_lineage[motif_id] = []
                        self.motif_lineage[motif_id].append(evolved_motif.id)
                        
                        # Publish evolved motif
                        await self._publish_motif_strand(evolved_motif)
                        
                        print(f"✅ Evolved motif {motif_id} -> {evolved_motif.id}")
                        
        except Exception as e:
            print(f"Error checking motif evolution: {e}")
    
    async def _should_evolve_motif(self, motif: MotifStrand) -> bool:
        """Determine if a motif should evolve"""
        try:
            # Check if motif has high resonance and good performance
            if motif.phi > 0.8 and motif.telemetry and motif.telemetry.get('sr', 0.0) > 0.7:
                # Check if enough time has passed since creation
                time_since_creation = datetime.now(timezone.utc) - motif.created_at
                if time_since_creation.total_seconds() > 3600:  # 1 hour
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error checking if motif should evolve: {e}")
            return False
    
    async def _evolve_motif(self, parent_motif: MotifStrand) -> Optional[MotifStrand]:
        """Evolve a motif into a new variant"""
        try:
            # Generate evolved motif using LLM
            prompt = f"""
            Evolve this motif into a new variant:
            
            Parent Motif: {json.dumps({
                'name': parent_motif.motif_name,
                'family': parent_motif.motif_family,
                'invariants': parent_motif.invariants,
                'fails_when': parent_motif.fails_when,
                'contexts': parent_motif.contexts,
                'why_map': parent_motif.why_map
            }, indent=2)}
            
            Performance: {json.dumps(parent_motif.telemetry, indent=2)}
            
            Create an evolved variant that:
            1. Builds on the parent's strengths
            2. Addresses any weaknesses
            3. Maintains the core mechanism
            4. Adds new insights or refinements
            
            Return as JSON with the same structure as the parent.
            """
            
            response = await self.llm_client.generate_response(
                prompt=prompt,
                model="anthropic/claude-3.5-sonnet",
                max_tokens=800,
                temperature=0.4
            )
            
            # Parse response
            try:
                evolved_data = json.loads(response)
                
                # Create evolved motif
                evolved_id = f"motif_{parent_motif.id}_evolved_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                evolved_motif = MotifStrand(
                    id=evolved_id,
                    symbol=parent_motif.symbol,
                    timeframe=parent_motif.timeframe,
                    session_bucket=parent_motif.session_bucket,
                    regime=parent_motif.regime,
                    tags=[f"agent:central_intelligence:motif_miner:pattern_evolved"],
                    created_at=datetime.now(timezone.utc),
                    
                    # Evolved pattern fields
                    motif_name=evolved_data.get('name', f"{parent_motif.motif_name} (Evolved)"),
                    motif_family=evolved_data.get('family', parent_motif.motif_family),
                    invariants=evolved_data.get('invariants', parent_motif.invariants),
                    fails_when=evolved_data.get('fails_when', parent_motif.fails_when),
                    contexts=evolved_data.get('contexts', parent_motif.contexts),
                    evidence_refs=[parent_motif.id],
                    why_map=evolved_data.get('why_map', parent_motif.why_map),
                    lineage={
                        'parents': [parent_motif.id],
                        'mutation_note': 'Evolved from parent motif'
                    },
                    
                    # Reset resonance state for new motif
                    phi=0.0,
                    rho=1.0,
                    phi_updated_at=datetime.now(timezone.utc),
                    rho_updated_at=datetime.now(timezone.utc),
                    telemetry={'sr': 0.0, 'cr': 0.0, 'xr': 0.0, 'surprise': 0.0},
                    
                    # Standard scoring
                    sig_sigma=parent_motif.sig_sigma,
                    sig_confidence=parent_motif.sig_confidence,
                    sig_direction=parent_motif.sig_direction,
                    outcome_score=0.0
                )
                
                return evolved_motif
                
            except json.JSONDecodeError:
                print(f"Failed to parse LLM response for evolved motif: {response}")
                return None
                
        except Exception as e:
            print(f"Error evolving motif: {e}")
            return None
    
    async def _generate_motif_meta_signals(self):
        """Generate meta-signals from high-resonance motifs"""
        try:
            for motif_id, motif in self.active_motifs.items():
                # Check if motif has high resonance
                if motif.phi > self.resonance_threshold:
                    # Generate meta-signal
                    await self._publish_motif_meta_signal(motif)
                    
        except Exception as e:
            print(f"Error generating motif meta-signals: {e}")
    
    async def _publish_motif_meta_signal(self, motif: MotifStrand):
        """Publish meta-signal for high-resonance motif"""
        try:
            strand_data = {
                'kind': 'meta_signal',
                'module': 'alpha',
                'tags': [f"agent:central_intelligence:motif_strand_manager:high_resonance_motif"],
                'meta_signal_type': 'high_resonance_motif',
                'meta_signal_data': {
                    'motif_id': motif.id,
                    'motif_name': motif.motif_name,
                    'motif_family': motif.motif_family,
                    'phi': motif.phi,
                    'rho': motif.rho,
                    'telemetry': motif.telemetry,
                    'resonance_threshold': self.resonance_threshold
                },
                'team_member': 'motif_strand_manager'
            }
            
            await self.supabase_manager.insert_strand(strand_data)
            
        except Exception as e:
            print(f"Error publishing motif meta-signal: {e}")
    
    async def _update_motif_in_database(self, motif: MotifStrand):
        """Update motif in database"""
        try:
            update_data = {
                'phi': motif.phi,
                'rho': motif.rho,
                'phi_updated_at': motif.phi_updated_at.isoformat() if motif.phi_updated_at else None,
                'rho_updated_at': motif.rho_updated_at.isoformat() if motif.rho_updated_at else None,
                'telemetry': motif.telemetry,
                'sig_sigma': motif.sig_sigma,
                'sig_confidence': motif.sig_confidence,
                'sig_direction': motif.sig_direction,
                'outcome_score': motif.outcome_score
            }
            
            await self.supabase_manager.update_strand(
                strand_id=motif.id,
                update_data=update_data
            )
            
        except Exception as e:
            print(f"Error updating motif in database: {e}")
    
    async def _load_existing_motifs(self):
        """Load existing motifs from database"""
        try:
            query = """
                SELECT * FROM AD_strands 
                WHERE kind = 'motif' 
                ORDER BY created_at DESC
            """
            
            result = await self.supabase_manager.execute_query(query)
            
            for row in result:
                motif = MotifStrand(
                    id=row['id'],
                    symbol=row.get('symbol', 'BTC'),
                    timeframe=row.get('timeframe', '1h'),
                    session_bucket=row.get('session_bucket', 'US'),
                    regime=row.get('regime', 'high_vol'),
                    tags=row.get('tags', []),
                    created_at=row['created_at'],
                    
                    # Pattern-specific fields
                    motif_name=row.get('motif_name', ''),
                    motif_family=row.get('motif_family', ''),
                    invariants=row.get('invariants', []),
                    fails_when=row.get('fails_when', []),
                    contexts=row.get('contexts', {}),
                    evidence_refs=row.get('evidence_refs', []),
                    why_map=row.get('why_map', {}),
                    lineage=row.get('lineage', {}),
                    
                    # Resonance state
                    phi=row.get('phi', 0.0),
                    rho=row.get('rho', 1.0),
                    phi_updated_at=row.get('phi_updated_at'),
                    rho_updated_at=row.get('rho_updated_at'),
                    telemetry=row.get('telemetry', {}),
                    
                    # Standard scoring
                    sig_sigma=row.get('sig_sigma', 0.0),
                    sig_confidence=row.get('sig_confidence', 0.0),
                    sig_direction=row.get('sig_direction', 'neutral'),
                    outcome_score=row.get('outcome_score', 0.0)
                )
                
                self.active_motifs[motif.id] = motif
                
        except Exception as e:
            print(f"Warning: Could not load existing motifs: {e}")
    
    async def get_motif_status(self) -> Dict[str, Any]:
        """Get current motif status"""
        return {
            'active_motifs_count': len(self.active_motifs),
            'motif_lineage_count': len(self.motif_lineage),
            'resonance_threshold': self.resonance_threshold,
            'telemetry_window_hours': self.telemetry_window_hours
        }
    
    async def get_high_resonance_motifs(self) -> List[MotifStrand]:
        """Get motifs with high resonance"""
        return [motif for motif in self.active_motifs.values() if motif.phi > self.resonance_threshold]
