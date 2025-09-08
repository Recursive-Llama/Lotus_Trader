"""
CIL Lineage & Provenance System - Additional Missing Piece 2
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple, Set
from dataclasses import dataclass
from enum import Enum

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient


class LineageType(Enum):
    """Types of lineage relationships"""
    PARENT_CHILD = "parent_child"
    SIBLING = "sibling"
    DESCENDANT = "descendant"
    ANCESTOR = "ancestor"
    MUTATION = "mutation"
    MERGE = "merge"
    SPLIT = "split"


class ProvenanceType(Enum):
    """Types of provenance information"""
    CREATION = "creation"
    MODIFICATION = "modification"
    DERIVATION = "derivation"
    INFLUENCE = "influence"
    REFERENCE = "reference"
    VALIDATION = "validation"


class MutationType(Enum):
    """Types of mutations in lineage"""
    PARAMETER_ADJUSTMENT = "parameter_adjustment"
    CONDITION_REFINEMENT = "condition_refinement"
    SCOPE_EXPANSION = "scope_expansion"
    SCOPE_REDUCTION = "scope_reduction"
    COMBINATION = "combination"
    SPLIT = "split"
    MERGE = "merge"


@dataclass
class LineageNode:
    """A node in the lineage tree"""
    node_id: str
    node_type: str  # 'experiment', 'lesson', 'pattern', 'doctrine'
    content: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    status: str  # 'active', 'retired', 'superseded'


@dataclass
class LineageEdge:
    """An edge in the lineage tree"""
    edge_id: str
    source_node_id: str
    target_node_id: str
    relationship_type: LineageType
    mutation_note: str
    confidence: float
    created_at: datetime
    metadata: Dict[str, Any]


@dataclass
class ProvenanceRecord:
    """A provenance record for tracking lineage"""
    record_id: str
    entity_id: str
    entity_type: str
    provenance_type: ProvenanceType
    source_entity_id: Optional[str]
    source_entity_type: Optional[str]
    mutation_details: Dict[str, Any]
    confidence: float
    created_at: datetime
    metadata: Dict[str, Any]


@dataclass
class FamilyTree:
    """A family tree for a signal family"""
    family_name: str
    root_nodes: List[str]
    nodes: Dict[str, LineageNode]
    edges: Dict[str, LineageEdge]
    provenance_records: List[ProvenanceRecord]
    tree_depth: int
    branch_count: int
    created_at: datetime
    updated_at: datetime


class LineageProvenanceSystem:
    """CIL Lineage & Provenance System - Family tree construction and circular rediscovery prevention"""
    
    def __init__(self, supabase_manager: SupabaseManager, llm_client: OpenRouterClient):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        
        # Configuration
        self.max_tree_depth = 10
        self.max_branches_per_node = 5
        self.similarity_threshold = 0.8
        self.circular_detection_threshold = 0.9
        
        # System state
        self.family_trees: Dict[str, FamilyTree] = {}
        self.lineage_nodes: Dict[str, LineageNode] = {}
        self.lineage_edges: Dict[str, LineageEdge] = {}
        self.provenance_records: List[ProvenanceRecord] = []
        self.circular_patterns: Set[str] = set()
        
        # LLM prompt templates
        self.lineage_analysis_prompt = self._load_lineage_analysis_prompt()
        self.circular_detection_prompt = self._load_circular_detection_prompt()
        self.family_tree_prompt = self._load_family_tree_prompt()
        
        # Initialize family trees
        self._initialize_family_trees()
    
    def _load_lineage_analysis_prompt(self) -> str:
        """Load lineage analysis prompt template"""
        return """
        Analyze the lineage and provenance of this entity.
        
        Entity Details:
        - ID: {entity_id}
        - Type: {entity_type}
        - Content: {content}
        - Metadata: {metadata}
        - Created At: {created_at}
        
        Existing Lineage Context:
        - Family: {family}
        - Existing Nodes: {existing_nodes}
        - Existing Edges: {existing_edges}
        - Recent Additions: {recent_additions}
        
        Analyze lineage relationships:
        1. Parent-child relationships (direct derivation)
        2. Sibling relationships (parallel development)
        3. Mutation patterns (parameter adjustments, refinements)
        4. Merge/split patterns (combination or division)
        5. Influence relationships (indirect connections)
        
        Respond in JSON format:
        {{
            "lineage_analysis": {{
                "parent_candidates": [
                    {{
                        "node_id": "node_id",
                        "relationship_type": "parent_child|sibling|mutation|merge|split",
                        "confidence": 0.0-1.0,
                        "mutation_note": "description of relationship"
                    }}
                ],
                "sibling_candidates": [
                    {{
                        "node_id": "node_id",
                        "relationship_type": "sibling",
                        "confidence": 0.0-1.0,
                        "similarity_score": 0.0-1.0
                    }}
                ],
                "influence_candidates": [
                    {{
                        "node_id": "node_id",
                        "relationship_type": "influence",
                        "confidence": 0.0-1.0,
                        "influence_type": "parameter|condition|scope|approach"
                    }}
                ]
            }},
            "provenance_insights": ["list of insights"],
            "circular_risk_assessment": {{
                "risk_level": "low|medium|high",
                "risk_factors": ["list of risk factors"],
                "prevention_suggestions": ["list of suggestions"]
            }},
            "uncertainty_flags": ["any uncertainties"]
        }}
        """
    
    def _load_circular_detection_prompt(self) -> str:
        """Load circular detection prompt template"""
        return """
        Detect potential circular rediscovery patterns in the lineage.
        
        New Entity:
        - ID: {entity_id}
        - Type: {entity_type}
        - Content: {content}
        - Family: {family}
        
        Existing Lineage:
        - Family Tree: {family_tree}
        - Recent Patterns: {recent_patterns}
        - Historical Patterns: {historical_patterns}
        
        Analyze for circular rediscovery:
        1. Direct duplicates (identical content)
        2. Near-duplicates (high similarity)
        3. Cyclical patterns (A→B→C→A)
        4. Redundant variations (same approach, different parameters)
        5. Historical repetition (same pattern, different time)
        
        Respond in JSON format:
        {{
            "circular_detection": {{
                "duplicate_candidates": [
                    {{
                        "node_id": "node_id",
                        "similarity_score": 0.0-1.0,
                        "duplicate_type": "exact|near|parameter_variant|temporal_variant",
                        "confidence": 0.0-1.0
                    }}
                ],
                "cyclical_patterns": [
                    {{
                        "cycle_nodes": ["node1", "node2", "node3"],
                        "cycle_type": "direct|indirect|parameter_cycle",
                        "confidence": 0.0-1.0
                    }}
                ],
                "redundant_variations": [
                    {{
                        "base_node": "node_id",
                        "variation_type": "parameter|condition|scope",
                        "redundancy_score": 0.0-1.0,
                        "confidence": 0.0-1.0
                    }}
                ]
            }},
            "circular_risk": {{
                "overall_risk": "low|medium|high",
                "risk_score": 0.0-1.0,
                "primary_risks": ["list of primary risks"],
                "prevention_actions": ["list of prevention actions"]
            }},
            "lineage_recommendations": ["list of recommendations"]
        }}
        """
    
    def _load_family_tree_prompt(self) -> str:
        """Load family tree prompt template"""
        return """
        Construct and analyze the family tree for this signal family.
        
        Family Details:
        - Name: {family_name}
        - Root Nodes: {root_nodes}
        - Total Nodes: {total_nodes}
        - Total Edges: {total_edges}
        - Tree Depth: {tree_depth}
        - Branch Count: {branch_count}
        
        Node Analysis:
        - Active Nodes: {active_nodes}
        - Retired Nodes: {retired_nodes}
        - Superseded Nodes: {superseded_nodes}
        
        Edge Analysis:
        - Parent-Child Edges: {parent_child_edges}
        - Sibling Edges: {sibling_edges}
        - Mutation Edges: {mutation_edges}
        - Merge/Split Edges: {merge_split_edges}
        
        Analyze family tree structure:
        1. Tree topology and branching patterns
        2. Node lifecycle and evolution
        3. Edge relationship distribution
        4. Family growth patterns
        5. Optimization opportunities
        
        Respond in JSON format:
        {{
            "family_tree_analysis": {{
                "topology_insights": ["list of topology insights"],
                "growth_patterns": ["list of growth patterns"],
                "evolution_trends": ["list of evolution trends"],
                "optimization_opportunities": ["list of optimization opportunities"]
            }},
            "tree_metrics": {{
                "branching_factor": 0.0-1.0,
                "depth_efficiency": 0.0-1.0,
                "node_utilization": 0.0-1.0,
                "edge_efficiency": 0.0-1.0
            }},
            "recommendations": ["list of recommendations"],
            "uncertainty_flags": ["any uncertainties"]
        }}
        """
    
    def _initialize_family_trees(self):
        """Initialize family trees for known signal families"""
        families = [
            'divergence', 'volume', 'correlation', 'session', 'cross_asset',
            'pattern', 'indicator', 'microstructure', 'regime', 'volatility'
        ]
        
        for family in families:
            self.family_trees[family] = FamilyTree(
                family_name=family,
                root_nodes=[],
                nodes={},
                edges={},
                provenance_records=[],
                tree_depth=0,
                branch_count=0,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
    
    async def process_lineage_provenance(self, new_entities: List[Dict[str, Any]],
                                       existing_lineage: Dict[str, Any]) -> Dict[str, Any]:
        """Process lineage and provenance for new entities"""
        try:
            # Analyze lineage for new entities
            lineage_analyses = await self._analyze_lineage(new_entities, existing_lineage)
            
            # Detect circular patterns
            circular_detections = await self._detect_circular_patterns(new_entities, existing_lineage)
            
            # Update family trees
            tree_updates = await self._update_family_trees(lineage_analyses, circular_detections)
            
            # Generate provenance records
            provenance_generation = await self._generate_provenance_records(new_entities, lineage_analyses)
            
            # Compile results
            results = {
                'lineage_analyses': lineage_analyses,
                'circular_detections': circular_detections,
                'tree_updates': tree_updates,
                'provenance_generation': provenance_generation,
                'lineage_timestamp': datetime.now(timezone.utc),
                'lineage_errors': []
            }
            
            # Publish results
            await self._publish_lineage_results(results)
            
            return results
            
        except Exception as e:
            print(f"Error processing lineage provenance: {e}")
            return {
                'lineage_analyses': [],
                'circular_detections': [],
                'tree_updates': {},
                'provenance_generation': [],
                'lineage_timestamp': datetime.now(timezone.utc),
                'lineage_errors': [str(e)]
            }
    
    async def _analyze_lineage(self, new_entities: List[Dict[str, Any]],
                             existing_lineage: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze lineage relationships for new entities"""
        lineage_analyses = []
        
        for entity in new_entities:
            # Prepare analysis data
            analysis_data = {
                'entity_id': entity.get('entity_id', f"ENTITY_{int(datetime.now().timestamp())}"),
                'entity_type': entity.get('entity_type', 'unknown'),
                'content': entity.get('content', {}),
                'metadata': entity.get('metadata', {}),
                'created_at': entity.get('created_at', datetime.now(timezone.utc).isoformat()),
                'family': entity.get('family', 'unknown'),
                'existing_nodes': existing_lineage.get('nodes', {}),
                'existing_edges': existing_lineage.get('edges', {}),
                'recent_additions': existing_lineage.get('recent_additions', [])
            }
            
            # Generate lineage analysis using LLM
            analysis = await self._generate_lineage_analysis(analysis_data)
            
            if analysis:
                lineage_analyses.append({
                    'entity_id': analysis_data['entity_id'],
                    'lineage_analysis': analysis['lineage_analysis'],
                    'provenance_insights': analysis.get('provenance_insights', []),
                    'circular_risk_assessment': analysis.get('circular_risk_assessment', {}),
                    'uncertainty_flags': analysis.get('uncertainty_flags', [])
                })
        
        return lineage_analyses
    
    async def _generate_lineage_analysis(self, analysis_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate lineage analysis using LLM"""
        try:
            # Generate analysis using LLM
            analysis = await self._generate_llm_analysis(
                self.lineage_analysis_prompt, analysis_data
            )
            
            return analysis
            
        except Exception as e:
            print(f"Error generating lineage analysis: {e}")
            return None
    
    async def _detect_circular_patterns(self, new_entities: List[Dict[str, Any]],
                                      existing_lineage: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect circular rediscovery patterns"""
        circular_detections = []
        
        for entity in new_entities:
            # Prepare detection data
            detection_data = {
                'entity_id': entity.get('entity_id', f"ENTITY_{int(datetime.now().timestamp())}"),
                'entity_type': entity.get('entity_type', 'unknown'),
                'content': entity.get('content', {}),
                'family': entity.get('family', 'unknown'),
                'family_tree': existing_lineage.get('family_trees', {}).get(entity.get('family', 'unknown'), {}),
                'recent_patterns': existing_lineage.get('recent_patterns', []),
                'historical_patterns': existing_lineage.get('historical_patterns', [])
            }
            
            # Generate circular detection using LLM
            detection = await self._generate_circular_detection(detection_data)
            
            if detection:
                circular_detections.append({
                    'entity_id': detection_data['entity_id'],
                    'circular_detection': detection['circular_detection'],
                    'circular_risk': detection.get('circular_risk', {}),
                    'lineage_recommendations': detection.get('lineage_recommendations', [])
                })
        
        return circular_detections
    
    async def _generate_circular_detection(self, detection_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate circular detection using LLM"""
        try:
            # Generate detection using LLM
            detection = await self._generate_llm_analysis(
                self.circular_detection_prompt, detection_data
            )
            
            return detection
            
        except Exception as e:
            print(f"Error generating circular detection: {e}")
            return None
    
    async def _update_family_trees(self, lineage_analyses: List[Dict[str, Any]],
                                 circular_detections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Update family trees based on lineage analyses"""
        tree_updates = {}
        
        for analysis in lineage_analyses:
            entity_id = analysis['entity_id']
            lineage_analysis = analysis['lineage_analysis']
            
            # Determine family from entity (simplified)
            family = 'divergence'  # Default family
            
            if family in self.family_trees:
                family_tree = self.family_trees[family]
                
                # Create lineage node
                node = LineageNode(
                    node_id=entity_id,
                    node_type='experiment',
                    content={'hypothesis': 'Test hypothesis'},
                    metadata={'family': family},
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    status='active'
                )
                
                # Add node to family tree
                family_tree.nodes[entity_id] = node
                
                # Create lineage edges based on analysis
                edges_created = []
                for parent_candidate in lineage_analysis.get('parent_candidates', []):
                    edge = LineageEdge(
                        edge_id=f"EDGE_{entity_id}_{parent_candidate['node_id']}",
                        source_node_id=parent_candidate['node_id'],
                        target_node_id=entity_id,
                        relationship_type=LineageType(parent_candidate['relationship_type']),
                        mutation_note=parent_candidate.get('mutation_note', ''),
                        confidence=parent_candidate['confidence'],
                        created_at=datetime.now(timezone.utc),
                        metadata={}
                    )
                    
                    family_tree.edges[edge.edge_id] = edge
                    edges_created.append(edge.edge_id)
                
                # Update tree metrics
                family_tree.tree_depth = max(family_tree.tree_depth, 1)
                family_tree.branch_count = len(family_tree.edges)
                family_tree.updated_at = datetime.now(timezone.utc)
                
                tree_updates[family] = {
                    'nodes_added': 1,
                    'edges_added': len(edges_created),
                    'tree_depth': family_tree.tree_depth,
                    'branch_count': family_tree.branch_count,
                    'updated_at': family_tree.updated_at.isoformat()
                }
        
        return tree_updates
    
    async def _generate_provenance_records(self, new_entities: List[Dict[str, Any]],
                                         lineage_analyses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate provenance records for new entities"""
        provenance_generation = []
        
        for entity, analysis in zip(new_entities, lineage_analyses):
            entity_id = analysis['entity_id']
            lineage_analysis = analysis['lineage_analysis']
            
            # Create provenance record
            provenance_record = ProvenanceRecord(
                record_id=f"PROV_{entity_id}",
                entity_id=entity_id,
                entity_type=entity.get('entity_type', 'unknown'),
                provenance_type=ProvenanceType.CREATION,
                source_entity_id=lineage_analysis.get('parent_candidates', [{}])[0].get('node_id') if lineage_analysis.get('parent_candidates') else None,
                source_entity_type='experiment',
                mutation_details=lineage_analysis.get('parent_candidates', [{}])[0].get('mutation_note', '') if lineage_analysis.get('parent_candidates') else '',
                confidence=lineage_analysis.get('parent_candidates', [{}])[0].get('confidence', 0.5) if lineage_analysis.get('parent_candidates') else 0.5,
                created_at=datetime.now(timezone.utc),
                metadata={'family': entity.get('family', 'unknown')}
            )
            
            # Add to provenance records
            self.provenance_records.append(provenance_record)
            
            provenance_generation.append({
                'record_id': provenance_record.record_id,
                'entity_id': entity_id,
                'provenance_type': provenance_record.provenance_type.value,
                'source_entity_id': provenance_record.source_entity_id,
                'mutation_details': provenance_record.mutation_details,
                'confidence': provenance_record.confidence,
                'created_at': provenance_record.created_at.isoformat()
            })
        
        return provenance_generation
    
    async def _generate_llm_analysis(self, prompt_template: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate LLM analysis using prompt template"""
        try:
            # Format prompt with data
            formatted_prompt = prompt_template.format(**data)
            
            # Call LLM (mock implementation)
            # In real implementation, use self.llm_client
            if 'lineage_analysis' in formatted_prompt:
                response = {
                    "lineage_analysis": {
                        "parent_candidates": [
                            {
                                "node_id": "PARENT_1",
                                "relationship_type": "parent_child",
                                "confidence": 0.85,
                                "mutation_note": "Parameter adjustment for volatility threshold"
                            }
                        ],
                        "sibling_candidates": [
                            {
                                "node_id": "SIBLING_1",
                                "relationship_type": "sibling",
                                "confidence": 0.72,
                                "similarity_score": 0.78
                            }
                        ],
                        "influence_candidates": [
                            {
                                "node_id": "INFLUENCE_1",
                                "relationship_type": "influence",
                                "confidence": 0.68,
                                "influence_type": "parameter"
                            }
                        ]
                    },
                    "provenance_insights": [
                        "Strong parent-child relationship with parameter mutation",
                        "Moderate sibling relationship with similar approach",
                        "Weak influence from related experiment"
                    ],
                    "circular_risk_assessment": {
                        "risk_level": "low",
                        "risk_factors": ["Parameter variation", "Condition refinement"],
                        "prevention_suggestions": ["Monitor parameter ranges", "Track condition evolution"]
                    },
                    "uncertainty_flags": ["Limited historical context"]
                }
            elif 'circular_detection' in formatted_prompt:
                response = {
                    "circular_detection": {
                        "duplicate_candidates": [
                            {
                                "node_id": "DUPLICATE_1",
                                "similarity_score": 0.92,
                                "duplicate_type": "near",
                                "confidence": 0.88
                            }
                        ],
                        "cyclical_patterns": [],
                        "redundant_variations": [
                            {
                                "base_node": "BASE_1",
                                "variation_type": "parameter",
                                "redundancy_score": 0.75,
                                "confidence": 0.82
                            }
                        ]
                    },
                    "circular_risk": {
                        "overall_risk": "medium",
                        "risk_score": 0.65,
                        "primary_risks": ["Near-duplicate pattern", "Parameter redundancy"],
                        "prevention_actions": ["Increase parameter diversity", "Expand condition scope"]
                    },
                    "lineage_recommendations": [
                        "Consider different parameter ranges",
                        "Explore alternative conditions",
                        "Monitor for cyclical patterns"
                    ]
                }
            else:
                response = {
                    "family_tree_analysis": {
                        "topology_insights": [
                            "Balanced branching structure",
                            "Good depth distribution",
                            "Efficient node utilization"
                        ],
                        "growth_patterns": [
                            "Steady growth in divergence family",
                            "Recent focus on parameter refinement",
                            "Increasing cross-family connections"
                        ],
                        "evolution_trends": [
                            "Progressive parameter optimization",
                            "Condition scope expansion",
                            "Approach diversification"
                        ],
                        "optimization_opportunities": [
                            "Reduce redundant branches",
                            "Optimize edge relationships",
                            "Improve node utilization"
                        ]
                    },
                    "tree_metrics": {
                        "branching_factor": 0.75,
                        "depth_efficiency": 0.82,
                        "node_utilization": 0.68,
                        "edge_efficiency": 0.71
                    },
                    "recommendations": [
                        "Optimize tree structure",
                        "Improve node utilization",
                        "Enhance edge efficiency"
                    ],
                    "uncertainty_flags": ["Limited tree depth data"]
                }
            
            return response
            
        except Exception as e:
            print(f"Error generating LLM analysis: {e}")
            return None
    
    async def _publish_lineage_results(self, results: Dict[str, Any]):
        """Publish lineage results as CIL strand"""
        try:
            # Create CIL lineage strand
            cil_strand = {
                'id': f"cil_lineage_provenance_{int(datetime.now().timestamp())}",
                'kind': 'cil_lineage_provenance',
                'module': 'alpha',
                'symbol': 'ALL',
                'timeframe': '1h',
                'session_bucket': 'ALL',
                'regime': 'all',
                'tags': ['agent:central_intelligence:lineage_provenance_system:lineage_processed'],
                'content': json.dumps(results, default=str),
                'sig_sigma': 0.9,
                'sig_confidence': 0.95,
                'outcome_score': 0.0,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'agent_id': 'central_intelligence_layer',
                'cil_team_member': 'lineage_provenance_system',
                'strategic_meta_type': 'lineage_provenance',
                'resonance_score': 0.9
            }
            
            # Insert into database
            await self.supabase_manager.insert_strand(cil_strand)
            
        except Exception as e:
            print(f"Error publishing lineage results: {e}")


# Example usage and testing
async def main():
    """Example usage of LineageProvenanceSystem"""
    from src.utils.supabase_manager import SupabaseManager
    from src.llm_integration.openrouter_client import OpenRouterClient
    
    # Initialize components
    supabase_manager = SupabaseManager()
    llm_client = OpenRouterClient()
    
    # Create lineage provenance system
    lineage_system = LineageProvenanceSystem(supabase_manager, llm_client)
    
    # Mock new entities
    new_entities = [
        {
            'entity_id': 'ENTITY_1',
            'entity_type': 'experiment',
            'content': {'hypothesis': 'Divergence patterns in high volatility'},
            'metadata': {'family': 'divergence', 'parameters': {'threshold': 0.8}},
            'family': 'divergence'
        },
        {
            'entity_id': 'ENTITY_2',
            'entity_type': 'lesson',
            'content': {'insight': 'Volume confirmation improves accuracy'},
            'metadata': {'family': 'volume', 'success_rate': 0.85},
            'family': 'volume'
        }
    ]
    
    existing_lineage = {
        'nodes': {'PARENT_1': {'type': 'experiment', 'content': {}}},
        'edges': {'EDGE_1': {'source': 'PARENT_1', 'target': 'CHILD_1'}},
        'recent_additions': ['ENTITY_0'],
        'family_trees': {'divergence': {'nodes': 5, 'edges': 4}},
        'recent_patterns': ['divergence_high_vol'],
        'historical_patterns': ['divergence_low_vol', 'divergence_sideways']
    }
    
    # Process lineage provenance
    results = await lineage_system.process_lineage_provenance(new_entities, existing_lineage)
    
    print("Lineage Provenance Results:")
    print(f"Lineage Analyses: {len(results['lineage_analyses'])}")
    print(f"Circular Detections: {len(results['circular_detections'])}")
    print(f"Tree Updates: {results['tree_updates']}")
    print(f"Provenance Generation: {len(results['provenance_generation'])}")


if __name__ == "__main__":
    asyncio.run(main())
