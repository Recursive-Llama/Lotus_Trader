"""
Test suite for CIL Lineage & Provenance System
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, List, Any

from src.intelligence.system_control.central_intelligence_layer.missing_pieces.lineage_provenance_system import (
    LineageProvenanceSystem,
    LineageType,
    ProvenanceType,
    MutationType,
    LineageNode,
    LineageEdge,
    ProvenanceRecord,
    FamilyTree
)


class TestLineageProvenanceSystem:
    """Test suite for LineageProvenanceSystem"""
    
    @pytest.fixture
    def mock_supabase_manager(self):
        """Mock SupabaseManager"""
        manager = Mock()
        manager.insert_strand = AsyncMock()
        return manager
    
    @pytest.fixture
    def mock_llm_client(self):
        """Mock OpenRouterClient"""
        client = Mock()
        return client
    
    @pytest.fixture
    def lineage_system(self, mock_supabase_manager, mock_llm_client):
        """Create LineageProvenanceSystem instance"""
        return LineageProvenanceSystem(mock_supabase_manager, mock_llm_client)
    
    def test_lineage_provenance_system_initialization(self, lineage_system):
        """Test system initialization"""
        assert lineage_system.supabase_manager is not None
        assert lineage_system.llm_client is not None
        assert lineage_system.max_tree_depth == 10
        assert lineage_system.max_branches_per_node == 5
        assert lineage_system.similarity_threshold == 0.8
        assert lineage_system.circular_detection_threshold == 0.9
        assert len(lineage_system.family_trees) == 10
        assert len(lineage_system.lineage_nodes) == 0
        assert len(lineage_system.lineage_edges) == 0
        assert len(lineage_system.provenance_records) == 0
        assert len(lineage_system.circular_patterns) == 0
    
    def test_initialize_family_trees(self, lineage_system):
        """Test family trees initialization"""
        expected_families = [
            'divergence', 'volume', 'correlation', 'session', 'cross_asset',
            'pattern', 'indicator', 'microstructure', 'regime', 'volatility'
        ]
        
        for family in expected_families:
            assert family in lineage_system.family_trees
            family_tree = lineage_system.family_trees[family]
            assert family_tree.family_name == family
            assert family_tree.root_nodes == []
            assert len(family_tree.nodes) == 0
            assert len(family_tree.edges) == 0
            assert len(family_tree.provenance_records) == 0
            assert family_tree.tree_depth == 0
            assert family_tree.branch_count == 0
    
    @pytest.mark.asyncio
    async def test_process_lineage_provenance(self, lineage_system):
        """Test processing lineage provenance"""
        new_entities = [
            {
                'entity_id': 'ENTITY_1',
                'entity_type': 'experiment',
                'content': {'hypothesis': 'Test hypothesis 1'},
                'metadata': {'family': 'divergence'},
                'family': 'divergence'
            }
        ]
        
        existing_lineage = {
            'nodes': {'PARENT_1': {'type': 'experiment'}},
            'edges': {'EDGE_1': {'source': 'PARENT_1'}},
            'recent_additions': ['ENTITY_0'],
            'family_trees': {'divergence': {'nodes': 5}},
            'recent_patterns': ['pattern1'],
            'historical_patterns': ['pattern2']
        }
        
        results = await lineage_system.process_lineage_provenance(new_entities, existing_lineage)
        
        assert 'lineage_analyses' in results
        assert 'circular_detections' in results
        assert 'tree_updates' in results
        assert 'provenance_generation' in results
        assert 'lineage_timestamp' in results
        assert 'lineage_errors' in results
        assert isinstance(results['lineage_analyses'], list)
        assert isinstance(results['circular_detections'], list)
        assert isinstance(results['tree_updates'], dict)
        assert isinstance(results['provenance_generation'], list)
        assert isinstance(results['lineage_errors'], list)
    
    @pytest.mark.asyncio
    async def test_analyze_lineage(self, lineage_system):
        """Test analyzing lineage relationships"""
        new_entities = [
            {
                'entity_id': 'ENTITY_1',
                'entity_type': 'experiment',
                'content': {'hypothesis': 'Test hypothesis'},
                'metadata': {'family': 'divergence'},
                'family': 'divergence'
            }
        ]
        
        existing_lineage = {
            'nodes': {'PARENT_1': {'type': 'experiment'}},
            'edges': {'EDGE_1': {'source': 'PARENT_1'}},
            'recent_additions': ['ENTITY_0']
        }
        
        lineage_analyses = await lineage_system._analyze_lineage(new_entities, existing_lineage)
        
        assert len(lineage_analyses) == 1
        analysis = lineage_analyses[0]
        assert 'entity_id' in analysis
        assert 'lineage_analysis' in analysis
        assert 'provenance_insights' in analysis
        assert 'circular_risk_assessment' in analysis
        assert 'uncertainty_flags' in analysis
        assert analysis['entity_id'] == 'ENTITY_1'
    
    @pytest.mark.asyncio
    async def test_generate_lineage_analysis(self, lineage_system):
        """Test generating lineage analysis"""
        analysis_data = {
            'entity_id': 'ENTITY_1',
            'entity_type': 'experiment',
            'content': {'hypothesis': 'Test hypothesis'},
            'metadata': {'family': 'divergence'},
            'created_at': datetime.now(timezone.utc).isoformat(),
            'family': 'divergence',
            'existing_nodes': {'PARENT_1': {'type': 'experiment'}},
            'existing_edges': {'EDGE_1': {'source': 'PARENT_1'}},
            'recent_additions': ['ENTITY_0']
        }
        
        analysis = await lineage_system._generate_lineage_analysis(analysis_data)
        
        assert analysis is not None
        assert 'lineage_analysis' in analysis
        assert 'provenance_insights' in analysis
        assert 'circular_risk_assessment' in analysis
        assert 'uncertainty_flags' in analysis
        
        lineage_analysis = analysis['lineage_analysis']
        assert 'parent_candidates' in lineage_analysis
        assert 'sibling_candidates' in lineage_analysis
        assert 'influence_candidates' in lineage_analysis
        
        # Verify parent candidates structure
        for parent in lineage_analysis['parent_candidates']:
            assert 'node_id' in parent
            assert 'relationship_type' in parent
            assert 'confidence' in parent
            assert 'mutation_note' in parent
            assert 0.0 <= parent['confidence'] <= 1.0
    
    @pytest.mark.asyncio
    async def test_detect_circular_patterns(self, lineage_system):
        """Test detecting circular patterns"""
        new_entities = [
            {
                'entity_id': 'ENTITY_1',
                'entity_type': 'experiment',
                'content': {'hypothesis': 'Test hypothesis'},
                'family': 'divergence'
            }
        ]
        
        existing_lineage = {
            'family_trees': {'divergence': {'nodes': 5}},
            'recent_patterns': ['pattern1'],
            'historical_patterns': ['pattern2']
        }
        
        circular_detections = await lineage_system._detect_circular_patterns(new_entities, existing_lineage)
        
        assert len(circular_detections) == 1
        detection = circular_detections[0]
        assert 'entity_id' in detection
        assert 'circular_detection' in detection
        assert 'circular_risk' in detection
        assert 'lineage_recommendations' in detection
        assert detection['entity_id'] == 'ENTITY_1'
    
    @pytest.mark.asyncio
    async def test_generate_circular_detection(self, lineage_system):
        """Test generating circular detection"""
        detection_data = {
            'entity_id': 'ENTITY_1',
            'entity_type': 'experiment',
            'content': {'hypothesis': 'Test hypothesis'},
            'family': 'divergence',
            'family_tree': {'nodes': 5, 'edges': 4},
            'recent_patterns': ['pattern1'],
            'historical_patterns': ['pattern2']
        }
        
        detection = await lineage_system._generate_circular_detection(detection_data)
        
        assert detection is not None
        assert 'circular_detection' in detection
        assert 'circular_risk' in detection
        assert 'lineage_recommendations' in detection
        
        circular_detection = detection['circular_detection']
        assert 'duplicate_candidates' in circular_detection
        assert 'cyclical_patterns' in circular_detection
        assert 'redundant_variations' in circular_detection
        
        # Verify duplicate candidates structure
        for duplicate in circular_detection['duplicate_candidates']:
            assert 'node_id' in duplicate
            assert 'similarity_score' in duplicate
            assert 'duplicate_type' in duplicate
            assert 'confidence' in duplicate
            assert 0.0 <= duplicate['similarity_score'] <= 1.0
            assert 0.0 <= duplicate['confidence'] <= 1.0
    
    @pytest.mark.asyncio
    async def test_update_family_trees(self, lineage_system):
        """Test updating family trees"""
        lineage_analyses = [
            {
                'entity_id': 'ENTITY_1',
                'lineage_analysis': {
                    'parent_candidates': [
                        {
                            'node_id': 'PARENT_1',
                            'relationship_type': 'parent_child',
                            'confidence': 0.85,
                            'mutation_note': 'Parameter adjustment'
                        }
                    ]
                }
            }
        ]
        
        circular_detections = [
            {
                'entity_id': 'ENTITY_1',
                'circular_detection': {
                    'duplicate_candidates': [],
                    'cyclical_patterns': [],
                    'redundant_variations': []
                }
            }
        ]
        
        tree_updates = await lineage_system._update_family_trees(lineage_analyses, circular_detections)
        
        assert isinstance(tree_updates, dict)
        if tree_updates:
            for family, update in tree_updates.items():
                assert 'nodes_added' in update
                assert 'edges_added' in update
                assert 'tree_depth' in update
                assert 'branch_count' in update
                assert 'updated_at' in update
                assert isinstance(update['nodes_added'], int)
                assert isinstance(update['edges_added'], int)
                assert isinstance(update['tree_depth'], int)
                assert isinstance(update['branch_count'], int)
    
    @pytest.mark.asyncio
    async def test_generate_provenance_records(self, lineage_system):
        """Test generating provenance records"""
        new_entities = [
            {
                'entity_id': 'ENTITY_1',
                'entity_type': 'experiment',
                'content': {'hypothesis': 'Test hypothesis'},
                'family': 'divergence'
            }
        ]
        
        lineage_analyses = [
            {
                'entity_id': 'ENTITY_1',
                'lineage_analysis': {
                    'parent_candidates': [
                        {
                            'node_id': 'PARENT_1',
                            'relationship_type': 'parent_child',
                            'confidence': 0.85,
                            'mutation_note': 'Parameter adjustment'
                        }
                    ]
                }
            }
        ]
        
        provenance_generation = await lineage_system._generate_provenance_records(new_entities, lineage_analyses)
        
        assert len(provenance_generation) == 1
        record = provenance_generation[0]
        assert 'record_id' in record
        assert 'entity_id' in record
        assert 'provenance_type' in record
        assert 'source_entity_id' in record
        assert 'mutation_details' in record
        assert 'confidence' in record
        assert 'created_at' in record
        assert record['entity_id'] == 'ENTITY_1'
        assert 0.0 <= record['confidence'] <= 1.0
    
    @pytest.mark.asyncio
    async def test_generate_llm_analysis(self, lineage_system):
        """Test generating LLM analysis"""
        prompt_template = "Test prompt with {test_field}"
        data = {'test_field': 'test_value'}
        
        result = await lineage_system._generate_llm_analysis(prompt_template, data)
        
        assert result is not None
        assert isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_publish_lineage_results(self, lineage_system):
        """Test publishing lineage results"""
        results = {
            'lineage_analyses': [{'entity_id': 'ENTITY_1'}],
            'circular_detections': [{'entity_id': 'ENTITY_1'}],
            'tree_updates': {'divergence': {'nodes_added': 1}},
            'provenance_generation': [{'record_id': 'PROV_1'}],
            'lineage_timestamp': datetime.now(timezone.utc),
            'lineage_errors': []
        }
        
        await lineage_system._publish_lineage_results(results)
        
        # Verify supabase_manager.insert_strand was called
        lineage_system.supabase_manager.insert_strand.assert_called_once()
        
        # Verify the strand structure
        call_args = lineage_system.supabase_manager.insert_strand.call_args[0][0]
        assert 'id' in call_args
        assert 'kind' in call_args
        assert 'content' in call_args
        assert call_args['kind'] == 'cil_lineage_provenance'
        assert call_args['agent_id'] == 'central_intelligence_layer'
        assert call_args['team_member'] == 'lineage_provenance_system'
    
    def test_lineage_type_enum(self):
        """Test LineageType enum values"""
        assert LineageType.PARENT_CHILD.value == "parent_child"
        assert LineageType.SIBLING.value == "sibling"
        assert LineageType.DESCENDANT.value == "descendant"
        assert LineageType.ANCESTOR.value == "ancestor"
        assert LineageType.MUTATION.value == "mutation"
        assert LineageType.MERGE.value == "merge"
        assert LineageType.SPLIT.value == "split"
    
    def test_provenance_type_enum(self):
        """Test ProvenanceType enum values"""
        assert ProvenanceType.CREATION.value == "creation"
        assert ProvenanceType.MODIFICATION.value == "modification"
        assert ProvenanceType.DERIVATION.value == "derivation"
        assert ProvenanceType.INFLUENCE.value == "influence"
        assert ProvenanceType.REFERENCE.value == "reference"
        assert ProvenanceType.VALIDATION.value == "validation"
    
    def test_mutation_type_enum(self):
        """Test MutationType enum values"""
        assert MutationType.PARAMETER_ADJUSTMENT.value == "parameter_adjustment"
        assert MutationType.CONDITION_REFINEMENT.value == "condition_refinement"
        assert MutationType.SCOPE_EXPANSION.value == "scope_expansion"
        assert MutationType.SCOPE_REDUCTION.value == "scope_reduction"
        assert MutationType.COMBINATION.value == "combination"
        assert MutationType.SPLIT.value == "split"
        assert MutationType.MERGE.value == "merge"
    
    def test_lineage_node_dataclass(self):
        """Test LineageNode dataclass"""
        node = LineageNode(
            node_id='TEST_NODE',
            node_type='experiment',
            content={'hypothesis': 'Test hypothesis'},
            metadata={'family': 'divergence'},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            status='active'
        )
        
        assert node.node_id == 'TEST_NODE'
        assert node.node_type == 'experiment'
        assert node.content == {'hypothesis': 'Test hypothesis'}
        assert node.metadata == {'family': 'divergence'}
        assert node.status == 'active'
    
    def test_lineage_edge_dataclass(self):
        """Test LineageEdge dataclass"""
        edge = LineageEdge(
            edge_id='TEST_EDGE',
            source_node_id='SOURCE_NODE',
            target_node_id='TARGET_NODE',
            relationship_type=LineageType.PARENT_CHILD,
            mutation_note='Parameter adjustment',
            confidence=0.85,
            created_at=datetime.now(timezone.utc),
            metadata={'family': 'divergence'}
        )
        
        assert edge.edge_id == 'TEST_EDGE'
        assert edge.source_node_id == 'SOURCE_NODE'
        assert edge.target_node_id == 'TARGET_NODE'
        assert edge.relationship_type == LineageType.PARENT_CHILD
        assert edge.mutation_note == 'Parameter adjustment'
        assert edge.confidence == 0.85
        assert edge.metadata == {'family': 'divergence'}
    
    def test_provenance_record_dataclass(self):
        """Test ProvenanceRecord dataclass"""
        record = ProvenanceRecord(
            record_id='TEST_RECORD',
            entity_id='ENTITY_1',
            entity_type='experiment',
            provenance_type=ProvenanceType.CREATION,
            source_entity_id='SOURCE_ENTITY',
            source_entity_type='experiment',
            mutation_details='Parameter adjustment',
            confidence=0.85,
            created_at=datetime.now(timezone.utc),
            metadata={'family': 'divergence'}
        )
        
        assert record.record_id == 'TEST_RECORD'
        assert record.entity_id == 'ENTITY_1'
        assert record.entity_type == 'experiment'
        assert record.provenance_type == ProvenanceType.CREATION
        assert record.source_entity_id == 'SOURCE_ENTITY'
        assert record.source_entity_type == 'experiment'
        assert record.mutation_details == 'Parameter adjustment'
        assert record.confidence == 0.85
        assert record.metadata == {'family': 'divergence'}
    
    def test_family_tree_dataclass(self):
        """Test FamilyTree dataclass"""
        nodes = {
            'NODE_1': LineageNode(
                node_id='NODE_1',
                node_type='experiment',
                content={},
                metadata={},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                status='active'
            )
        }
        
        edges = {
            'EDGE_1': LineageEdge(
                edge_id='EDGE_1',
                source_node_id='SOURCE',
                target_node_id='TARGET',
                relationship_type=LineageType.PARENT_CHILD,
                mutation_note='',
                confidence=0.8,
                created_at=datetime.now(timezone.utc),
                metadata={}
            )
        }
        
        tree = FamilyTree(
            family_name='divergence',
            root_nodes=['ROOT_1'],
            nodes=nodes,
            edges=edges,
            provenance_records=[],
            tree_depth=2,
            branch_count=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        assert tree.family_name == 'divergence'
        assert tree.root_nodes == ['ROOT_1']
        assert len(tree.nodes) == 1
        assert len(tree.edges) == 1
        assert tree.tree_depth == 2
        assert tree.branch_count == 1


if __name__ == "__main__":
    pytest.main([__file__])
