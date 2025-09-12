"""
CIL-PatternMiner: Tool-Using Data Searcher

Role: Actively searches market_data + strands using tools to mine patterns; builds the Pattern Atlas.
- Runs canned scans (confluence, lead-lag, regime/session lattice)
- Uses LLM passes to name motifs and draft mechanism hypotheses (Why-Map)
- Emits meta-signals (CIL-origin events) back to strands for everyone to subscribe to

Think: the layer that actively searches for patterns in data.
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
class MotifCard:
    """Motif Card data structure"""
    motif_id: str
    name: str
    family: str
    invariants: List[str]
    fails_when: List[str]
    contexts: Dict[str, Any]
    evidence_refs: List[str]
    why_map: Dict[str, Any]
    lineage: Dict[str, Any]
    confidence: float
    created_at: datetime


@dataclass
class ConfluenceEvent:
    """Confluence event data structure"""
    confluence_id: str
    family_a: str
    family_b: str
    regime: str
    session: str
    delta_t: int
    lift: float
    confidence: float
    created_at: datetime


class CILPatternMiner:
    """
    CIL-PatternMiner: Tool-Using Data Searcher
    
    Responsibilities:
    - Actively searches market_data + strands using tools
    - Builds Pattern Atlas with Motif Cards
    - Runs confluence, lead-lag, regime/session scans
    - Uses LLM to name motifs and draft mechanism hypotheses
    - Emits meta-signals back to strands
    """
    
    def __init__(self, supabase_manager: SupabaseManager, llm_client: OpenRouterClient):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.prompt_manager = PromptManager()
        self.context_system = DatabaseDrivenContextSystem(supabase_manager)
        
        # Pattern Atlas
        self.motif_cards: Dict[str, MotifCard] = {}
        self.confluence_events: Dict[str, ConfluenceEvent] = {}
        
        # Mining Configuration
        self.scan_interval_minutes = 15
        self.confluence_threshold = 0.7
        self.lead_lag_threshold = 0.6
        self.min_samples_for_pattern = 50
        
    async def initialize(self):
        """Initialize the pattern miner"""
        try:
            # Load existing motif cards
            await self._load_motif_cards()
            
            # Start mining loop
            asyncio.create_task(self._mining_loop())
            
            print("✅ CIL-PatternMiner initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ CIL-PatternMiner initialization failed: {e}")
            return False
    
    async def _mining_loop(self):
        """Main mining loop"""
        while True:
            try:
                # Run confluence scan
                await self._scan_confluence_patterns()
                
                # Run lead-lag scan
                await self._scan_lead_lag_patterns()
                
                # Run regime/session lattice scan
                await self._scan_regime_session_patterns()
                
                # Generate motif cards from patterns
                await self._generate_motif_cards()
                
                # Emit meta-signals
                await self._emit_meta_signals()
                
                # Wait before next iteration
                await asyncio.sleep(self.scan_interval_minutes * 60)
                
            except Exception as e:
                print(f"Error in pattern mining loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _scan_confluence_patterns(self):
        """Scan for confluence patterns (A∧B within Δt)"""
        try:
            # Query for recent signals from different families
            query = """
                SELECT 
                    s1.family as family_a,
                    s2.family as family_b,
                    s1.regime,
                    s1.session_bucket,
                    EXTRACT(EPOCH FROM (s2.created_at - s1.created_at)) as delta_t,
                    COUNT(*) as co_occurrences
                FROM AD_strands s1
                JOIN AD_strands s2 ON s1.symbol = s2.symbol 
                    AND s1.timeframe = s2.timeframe
                    AND s2.created_at BETWEEN s1.created_at AND s1.created_at + INTERVAL '1 hour'
                WHERE s1.kind = 'signal' 
                    AND s2.kind = 'signal'
                    AND s1.family != s2.family
                    AND s1.created_at > NOW() - INTERVAL '24 hours'
                GROUP BY s1.family, s2.family, s1.regime, s1.session_bucket, delta_t
                HAVING COUNT(*) >= %s
                ORDER BY co_occurrences DESC
            """
            
            result = await self.supabase_manager.execute_query(query, [self.min_samples_for_pattern])
            
            for row in result:
                # Calculate lift
                lift = await self._calculate_lift(row['family_a'], row['family_b'], row['regime'], row['session_bucket'])
                
                if lift > self.confluence_threshold:
                    # Create confluence event
                    confluence_id = f"conf_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    confluence = ConfluenceEvent(
                        confluence_id=confluence_id,
                        family_a=row['family_a'],
                        family_b=row['family_b'],
                        regime=row['regime'],
                        session=row['session_bucket'],
                        delta_t=int(row['delta_t']),
                        lift=lift,
                        confidence=min(lift, 1.0),
                        created_at=datetime.now(timezone.utc)
                    )
                    
                    self.confluence_events[confluence_id] = confluence
                    
                    print(f"✅ Found confluence: {row['family_a']} ∧ {row['family_b']} (lift: {lift:.3f})")
                    
        except Exception as e:
            print(f"Error scanning confluence patterns: {e}")
    
    async def _scan_lead_lag_patterns(self):
        """Scan for lead-lag patterns (A→B)"""
        try:
            # Query for lead-lag patterns
            query = """
                SELECT 
                    s1.family as lead_family,
                    s2.family as lag_family,
                    s1.regime,
                    s1.session_bucket,
                    AVG(EXTRACT(EPOCH FROM (s2.created_at - s1.created_at))) as avg_lag,
                    COUNT(*) as occurrences
                FROM AD_strands s1
                JOIN AD_strands s2 ON s1.symbol = s2.symbol 
                    AND s1.timeframe = s2.timeframe
                    AND s2.created_at BETWEEN s1.created_at + INTERVAL '1 minute' AND s1.created_at + INTERVAL '1 hour'
                WHERE s1.kind = 'signal' 
                    AND s2.kind = 'signal'
                    AND s1.family != s2.family
                    AND s1.created_at > NOW() - INTERVAL '24 hours'
                GROUP BY s1.family, s2.family, s1.regime, s1.session_bucket
                HAVING COUNT(*) >= %s
                ORDER BY occurrences DESC
            """
            
            result = await self.supabase_manager.execute_query(query, [self.min_samples_for_pattern])
            
            for row in result:
                # Calculate lead-lag strength
                strength = await self._calculate_lead_lag_strength(row['lead_family'], row['lag_family'], row['regime'])
                
                if strength > self.lead_lag_threshold:
                    print(f"✅ Found lead-lag: {row['lead_family']} → {row['lag_family']} (strength: {strength:.3f})")
                    
        except Exception as e:
            print(f"Error scanning lead-lag patterns: {e}")
    
    async def _scan_regime_session_patterns(self):
        """Scan for regime/session lattice patterns"""
        try:
            # Query for regime/session patterns
            query = """
                SELECT 
                    regime,
                    session_bucket,
                    family,
                    COUNT(*) as occurrences,
                    AVG(sig_confidence) as avg_confidence
                FROM AD_strands
                WHERE kind = 'signal'
                    AND created_at > NOW() - INTERVAL '24 hours'
                GROUP BY regime, session_bucket, family
                HAVING COUNT(*) >= %s
                ORDER BY occurrences DESC
            """
            
            result = await self.supabase_manager.execute_query(query, [self.min_samples_for_pattern])
            
            for row in result:
                if row['avg_confidence'] > 0.6:
                    print(f"✅ Found regime/session pattern: {row['family']} in {row['regime']}/{row['session_bucket']} (confidence: {row['avg_confidence']:.3f})")
                    
        except Exception as e:
            print(f"Error scanning regime/session patterns: {e}")
    
    async def _calculate_lift(self, family_a: str, family_b: str, regime: str, session: str) -> float:
        """Calculate lift for confluence pattern"""
        try:
            # Get individual frequencies
            query_a = """
                SELECT COUNT(*) as count_a
                FROM AD_strands
                WHERE family = %s AND regime = %s AND session_bucket = %s
                    AND created_at > NOW() - INTERVAL '24 hours'
            """
            
            query_b = """
                SELECT COUNT(*) as count_b
                FROM AD_strands
                WHERE family = %s AND regime = %s AND session_bucket = %s
                    AND created_at > NOW() - INTERVAL '24 hours'
            """
            
            query_ab = """
                SELECT COUNT(*) as count_ab
                FROM AD_strands s1
                JOIN AD_strands s2 ON s1.symbol = s2.symbol 
                    AND s1.timeframe = s2.timeframe
                    AND s2.created_at BETWEEN s1.created_at AND s1.created_at + INTERVAL '1 hour'
                WHERE s1.family = %s AND s2.family = %s 
                    AND s1.regime = %s AND s1.session_bucket = %s
                    AND s1.created_at > NOW() - INTERVAL '24 hours'
            """
            
            result_a = await self.supabase_manager.execute_query(query_a, [family_a, regime, session])
            result_b = await self.supabase_manager.execute_query(query_b, [family_b, regime, session])
            result_ab = await self.supabase_manager.execute_query(query_ab, [family_a, family_b, regime, session])
            
            count_a = result_a[0]['count_a'] if result_a else 0
            count_b = result_b[0]['count_b'] if result_b else 0
            count_ab = result_ab[0]['count_ab'] if result_ab else 0
            
            # Calculate lift
            if count_a > 0 and count_b > 0:
                expected = (count_a * count_b) / (count_a + count_b)
                if expected > 0:
                    return count_ab / expected
            
            return 0.0
            
        except Exception as e:
            print(f"Error calculating lift: {e}")
            return 0.0
    
    async def _calculate_lead_lag_strength(self, lead_family: str, lag_family: str, regime: str) -> float:
        """Calculate lead-lag strength"""
        try:
            # Simple implementation - could be enhanced
            query = """
                SELECT COUNT(*) as count
                FROM AD_strands s1
                JOIN AD_strands s2 ON s1.symbol = s2.symbol 
                    AND s1.timeframe = s2.timeframe
                    AND s2.created_at BETWEEN s1.created_at + INTERVAL '1 minute' AND s1.created_at + INTERVAL '1 hour'
                WHERE s1.family = %s AND s2.family = %s 
                    AND s1.regime = %s
                    AND s1.created_at > NOW() - INTERVAL '24 hours'
            """
            
            result = await self.supabase_manager.execute_query(query, [lead_family, lag_family, regime])
            count = result[0]['count'] if result else 0
            
            # Normalize to 0-1 range
            return min(count / 100.0, 1.0)
            
        except Exception as e:
            print(f"Error calculating lead-lag strength: {e}")
            return 0.0
    
    async def _generate_motif_cards(self):
        """Generate motif cards from discovered patterns"""
        try:
            # Process confluence events
            for confluence_id, confluence in self.confluence_events.items():
                if confluence_id not in self.motif_cards:
                    # Generate motif card using LLM
                    motif_card = await self._create_motif_card_from_confluence(confluence)
                    if motif_card:
                        self.motif_cards[motif_card.motif_id] = motif_card
                        
        except Exception as e:
            print(f"Error generating motif cards: {e}")
    
    async def _create_motif_card_from_confluence(self, confluence: ConfluenceEvent) -> Optional[MotifCard]:
        """Create motif card from confluence event using LLM"""
        try:
            # Generate motif name and details using LLM
            prompt = f"""
            Create a motif card for this confluence pattern:
            
            Family A: {confluence.family_a}
            Family B: {confluence.family_b}
            Regime: {confluence.regime}
            Session: {confluence.session}
            Delta T: {confluence.delta_t} seconds
            Lift: {confluence.lift}
            
            Generate:
            1. Motif name (descriptive)
            2. Motif family (category)
            3. Invariants (what must be present)
            4. Fails when (what breaks the pattern)
            5. Why map (mechanism hypothesis)
            
            Return as JSON format.
            """
            
            response = await self.llm_client.generate_response(
                prompt=prompt,
                model="anthropic/claude-3.5-sonnet",
                max_tokens=500,
                temperature=0.3
            )
            
            # Parse response and create motif card
            try:
                motif_data = json.loads(response)
                
                motif_id = f"motif_{confluence.confluence_id}"
                motif_card = MotifCard(
                    motif_id=motif_id,
                    name=motif_data.get('name', f"{confluence.family_a} + {confluence.family_b}"),
                    family=motif_data.get('family', 'confluence'),
                    invariants=motif_data.get('invariants', []),
                    fails_when=motif_data.get('fails_when', []),
                    contexts={
                        'regime': confluence.regime,
                        'session': confluence.session,
                        'delta_t': confluence.delta_t
                    },
                    evidence_refs=[confluence.confluence_id],
                    why_map=motif_data.get('why_map', {}),
                    lineage={'parents': [], 'mutation_note': 'Generated from confluence'},
                    confidence=confluence.confidence,
                    created_at=datetime.now(timezone.utc)
                )
                
                return motif_card
                
            except json.JSONDecodeError:
                print(f"Failed to parse LLM response for motif card: {response}")
                return None
                
        except Exception as e:
            print(f"Error creating motif card from confluence: {e}")
            return None
    
    async def _emit_meta_signals(self):
        """Emit meta-signals back to strands"""
        try:
            # Emit confluence meta-signals
            for confluence_id, confluence in self.confluence_events.items():
                if confluence.lift > self.confluence_threshold:
                    await self._publish_meta_signal('confluence_event', {
                        'confluence_id': confluence_id,
                        'family_a': confluence.family_a,
                        'family_b': confluence.family_b,
                        'regime': confluence.regime,
                        'session': confluence.session,
                        'delta_t': confluence.delta_t,
                        'lift': confluence.lift,
                        'confidence': confluence.confidence
                    })
            
            # Emit motif meta-signals
            for motif_id, motif in self.motif_cards.items():
                if motif.confidence > 0.7:
                    await self._publish_meta_signal('motif_discovered', {
                        'motif_id': motif_id,
                        'name': motif.name,
                        'family': motif.family,
                        'invariants': motif.invariants,
                        'confidence': motif.confidence
                    })
                    
        except Exception as e:
            print(f"Error emitting meta-signals: {e}")
    
    async def _publish_meta_signal(self, signal_type: str, signal_data: Dict[str, Any]):
        """Publish meta-signal to database"""
        try:
            strand_data = {
                'kind': 'meta_signal',
                'module': 'alpha',
                'tags': [f"agent:central_intelligence:pattern_miner:{signal_type}"],
                'meta_signal_type': signal_type,
                'meta_signal_data': signal_data,
                'team_member': 'pattern_miner'
            }
            
            await self.supabase_manager.insert_strand(strand_data)
            
        except Exception as e:
            print(f"Error publishing meta-signal: {e}")
    
    async def _load_motif_cards(self):
        """Load existing motif cards from database"""
        try:
            query = """
                SELECT * FROM AD_strands 
                WHERE kind = 'motif' 
                ORDER BY created_at DESC
            """
            
            result = await self.supabase_manager.execute_query(query)
            
            for row in result:
                motif_card = MotifCard(
                    motif_id=row['motif_id'],
                    name=row.get('motif_name', ''),
                    family=row.get('motif_family', ''),
                    invariants=row.get('invariants', []),
                    fails_when=row.get('fails_when', []),
                    contexts=row.get('contexts', {}),
                    evidence_refs=row.get('evidence_refs', []),
                    why_map=row.get('why_map', {}),
                    lineage=row.get('lineage', {}),
                    confidence=row.get('confidence', 0.0),
                    created_at=row['created_at']
                )
                self.motif_cards[motif_card.motif_id] = motif_card
                
        except Exception as e:
            print(f"Warning: Could not load motif cards: {e}")
    
    async def get_pattern_atlas_status(self) -> Dict[str, Any]:
        """Get current pattern atlas status"""
        return {
            'motif_cards_count': len(self.motif_cards),
            'confluence_events_count': len(self.confluence_events),
            'scan_interval_minutes': self.scan_interval_minutes,
            'confluence_threshold': self.confluence_threshold,
            'lead_lag_threshold': self.lead_lag_threshold,
            'min_samples_for_pattern': self.min_samples_for_pattern
        }

