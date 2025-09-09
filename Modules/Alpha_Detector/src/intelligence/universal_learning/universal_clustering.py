"""
Universal Clustering System for All Strands

This module provides universal clustering capabilities for all strand types in the system.
It implements the two-tier clustering approach:
1. Column Clustering (Structural Grouping) - Groups by high-level columns
2. Pattern Clustering (ML-based Similarity) - Uses existing PatternClusterer

The clustering system is designed to work with the unified learning system where:
- Everything is strands (signals, intelligence, trading_plans, braids, etc.)
- Clustering groups similar strands for promotion to braids
- Two-tier approach provides both structural and ML-based similarity
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone

# Import existing PatternClusterer
from src.llm_integration.pattern_clusterer import PatternClusterer

logger = logging.getLogger(__name__)


@dataclass
class Cluster:
    """Represents a cluster of similar strands"""
    strands: List[Dict[str, Any]]
    cluster_key: str
    braid_level: int
    created_at: datetime
    
    @property
    def size(self) -> int:
        """Number of strands in this cluster"""
        return len(self.strands)
    
    @property
    def avg_persistence(self) -> float:
        """Average persistence score of strands in this cluster"""
        if not self.strands:
            return 0.0
        return sum(s.get('persistence_score', 0.0) for s in self.strands) / len(self.strands)
    
    @property
    def avg_novelty(self) -> float:
        """Average novelty score of strands in this cluster"""
        if not self.strands:
            return 0.0
        return sum(s.get('novelty_score', 0.0) for s in self.strands) / len(self.strands)
    
    @property
    def avg_surprise(self) -> float:
        """Average surprise rating of strands in this cluster"""
        if not self.strands:
            return 0.0
        return sum(s.get('surprise_rating', 0.0) for s in self.strands) / len(self.strands)
    
    def add_strand(self, strand: Dict[str, Any]) -> None:
        """Add a strand to this cluster"""
        self.strands.append(strand)
    
    def get_representative(self) -> Dict[str, Any]:
        """Get a representative strand from this cluster"""
        if not self.strands:
            return {}
        return self.strands[0]


class UniversalClustering:
    """
    Universal clustering system for all strand types
    
    Implements two-tier clustering:
    1. Column Clustering (Structural Grouping)
    2. Pattern Clustering (ML-based Similarity)
    """
    
    def __init__(self):
        """Initialize universal clustering system"""
        self.logger = logging.getLogger(__name__)
        
        # Initialize PatternClusterer for ML-based clustering
        self.pattern_clusterer = PatternClusterer()
        
        # Structural columns for initial grouping
        self.structural_columns = [
            'agent_id', 'timeframe', 'regime', 'session_bucket',
            'pattern_type', 'motif_family', 'strategic_meta_type'
        ]
        
        # Clustering configuration
        self.min_strands_for_ml_clustering = 3
        self.similarity_threshold = 0.7
    
    def cluster_strands_by_columns(self, strands: List[Dict[str, Any]], braid_level: int) -> List[Cluster]:
        """
        Tier 1: Column Clustering (Structural Grouping)
        
        Groups strands by structural similarity using high-level columns.
        Only clusters strands of the same braid_level.
        
        Args:
            strands: List of strand dictionaries
            braid_level: Braid level to cluster (0=strand, 1=braid, 2=metabraid, etc.)
            
        Returns:
            List of ColumnCluster objects
        """
        try:
            clusters = []
            
            for strand in strands:
                # Only cluster same braid level
                if strand.get('braid_level', 0) != braid_level:
                    continue
                
                # Find similar cluster based on structural columns
                similar_cluster = self._find_similar_column_cluster(strand, clusters)
                
                if similar_cluster:
                    similar_cluster.add_strand(strand)
                else:
                    # Create new cluster
                    cluster_key = self._generate_cluster_key(strand)
                    new_cluster = Cluster(
                        strands=[strand],
                        cluster_key=cluster_key,
                        braid_level=braid_level,
                        created_at=datetime.now(timezone.utc)
                    )
                    clusters.append(new_cluster)
            
            self.logger.info(f"Column clustering: {len(strands)} strands -> {len(clusters)} clusters")
            return clusters
            
        except Exception as e:
            self.logger.error(f"Error in column clustering: {e}")
            return []
    
    def cluster_strands_by_patterns(self, column_clusters: List[Cluster]) -> List[Cluster]:
        """
        Tier 2: Pattern Clustering (ML-based Similarity)
        
        Uses existing PatternClusterer for sophisticated pattern clustering.
        Only applies ML clustering to clusters with enough strands.
        
        Args:
            column_clusters: List of ColumnCluster objects from tier 1
            
        Returns:
            List of PatternCluster objects
        """
        try:
            pattern_clusters = []
            
            for column_cluster in column_clusters:
                if column_cluster.size >= self.min_strands_for_ml_clustering:
                    # Use PatternClusterer for ML-based clustering
                    ml_clusters = self.pattern_clusterer.cluster_situations(column_cluster.strands)
                    
                    # Convert ML clusters to our Cluster format
                    for i, ml_cluster in enumerate(ml_clusters):
                        cluster_key = f"{column_cluster.cluster_key}_ml_{i}"
                        pattern_cluster = Cluster(
                            strands=ml_cluster.get('situations', []),  # Extract situations from ML cluster
                            cluster_key=cluster_key,
                            braid_level=column_cluster.braid_level,
                            created_at=datetime.now(timezone.utc)
                        )
                        pattern_clusters.append(pattern_cluster)
                else:
                    # Too few strands, keep as single cluster
                    pattern_clusters.append(column_cluster)
            
            self.logger.info(f"Pattern clustering: {len(column_clusters)} column clusters -> {len(pattern_clusters)} pattern clusters")
            return pattern_clusters
            
        except Exception as e:
            self.logger.error(f"Error in pattern clustering: {e}")
            return column_clusters  # Fallback to column clusters
    
    def cluster_strands(self, strands: List[Dict[str, Any]], braid_level: int) -> List[Cluster]:
        """
        Complete two-tier clustering process
        
        Args:
            strands: List of strand dictionaries
            braid_level: Braid level to cluster
            
        Returns:
            List of final clusters after two-tier clustering
        """
        try:
            # Step 1: Column clustering (structural grouping)
            column_clusters = self.cluster_strands_by_columns(strands, braid_level)
            
            # Step 2: Pattern clustering (ML-based similarity)
            pattern_clusters = self.cluster_strands_by_patterns(column_clusters)
            
            self.logger.info(f"Two-tier clustering complete: {len(strands)} strands -> {len(pattern_clusters)} final clusters")
            return pattern_clusters
            
        except Exception as e:
            self.logger.error(f"Error in two-tier clustering: {e}")
            return []
    
    def _find_similar_column_cluster(self, strand: Dict[str, Any], clusters: List[Cluster]) -> Optional[Cluster]:
        """
        Find a similar cluster based on structural columns
        
        Args:
            strand: Strand to find similar cluster for
            clusters: Existing clusters to search
            
        Returns:
            Similar cluster if found, None otherwise
        """
        for cluster in clusters:
            if self._strands_are_structurally_similar(strand, cluster.get_representative()):
                return cluster
        return None
    
    def _strands_are_structurally_similar(self, strand1: Dict[str, Any], strand2: Dict[str, Any]) -> bool:
        """
        Check if two strands are structurally similar based on columns
        
        Args:
            strand1: First strand
            strand2: Second strand
            
        Returns:
            True if structurally similar, False otherwise
        """
        for column in self.structural_columns:
            value1 = strand1.get(column)
            value2 = strand2.get(column)
            
            # Both must have the same value (or both be None/empty)
            if value1 != value2:
                return False
        
        return True
    
    def _generate_cluster_key(self, strand: Dict[str, Any]) -> str:
        """
        Generate a cluster key for a strand based on structural columns
        
        Args:
            strand: Strand to generate key for
            
        Returns:
            Cluster key string
        """
        key_parts = []
        for column in self.structural_columns:
            value = strand.get(column, 'unknown')
            key_parts.append(str(value))
        
        return '_'.join(key_parts)
    
    def cluster_meets_threshold(self, cluster: Cluster, thresholds: Optional[Dict[str, Any]] = None) -> bool:
        """
        Check if cluster meets threshold for promotion to braid
        
        Args:
            cluster: Cluster to check
            thresholds: Custom thresholds (optional)
            
        Returns:
            True if cluster meets threshold, False otherwise
        """
        if thresholds is None:
            thresholds = {
                'min_strands': 5,
                'min_avg_persistence': 0.6,
                'min_avg_novelty': 0.5,
                'min_avg_surprise': 0.4
            }
        
        return (cluster.size >= thresholds['min_strands'] and
                cluster.avg_persistence >= thresholds['min_avg_persistence'] and
                cluster.avg_novelty >= thresholds['min_avg_novelty'] and
                cluster.avg_surprise >= thresholds['min_avg_surprise'])


# Example usage and testing
if __name__ == "__main__":
    # Test the universal clustering system
    clustering = UniversalClustering()
    
    # Test strands
    test_strands = [
        {
            'id': 'strand_1',
            'agent_id': 'raw_data_intelligence',
            'timeframe': '1h',
            'regime': 'bull',
            'pattern_type': 'divergence',
            'braid_level': 0,
            'persistence_score': 0.8,
            'novelty_score': 0.6,
            'surprise_rating': 0.4
        },
        {
            'id': 'strand_2',
            'agent_id': 'raw_data_intelligence',
            'timeframe': '1h',
            'regime': 'bull',
            'pattern_type': 'divergence',
            'braid_level': 0,
            'persistence_score': 0.7,
            'novelty_score': 0.5,
            'surprise_rating': 0.3
        },
        {
            'id': 'strand_3',
            'agent_id': 'central_intelligence_layer',
            'timeframe': '4h',
            'regime': 'bear',
            'pattern_type': 'confluence',
            'braid_level': 0,
            'persistence_score': 0.9,
            'novelty_score': 0.8,
            'surprise_rating': 0.6
        }
    ]
    
    # Test clustering
    clusters = clustering.cluster_strands(test_strands, braid_level=0)
    
    print(f"Clustered {len(test_strands)} strands into {len(clusters)} clusters")
    for i, cluster in enumerate(clusters):
        print(f"Cluster {i+1}: {cluster.size} strands, persistence={cluster.avg_persistence:.2f}, novelty={cluster.avg_novelty:.2f}")
        print(f"  Meets threshold: {clustering.cluster_meets_threshold(cluster)}")
