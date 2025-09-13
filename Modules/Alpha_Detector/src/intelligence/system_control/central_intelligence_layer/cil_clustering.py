"""
CIL Specialized Clustering System

This module provides CIL-specific clustering capabilities that build on the universal foundation.
It implements trading-specific two-tier clustering with enhanced features for trading patterns.

Features:
1. Trading-specific column clustering (symbol, timeframe, regime, strength_range, rr_profile, etc.)
2. Enhanced PatternClusterer with trading-specific features
3. Strength range classification
4. R/R profile clustering
5. Market conditions clustering
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone

# Import universal clustering as base
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'Modules', 'Alpha_Detector', 'src'))
from intelligence.universal_learning.universal_clustering import UniversalClustering, Cluster
from llm_integration.pattern_clusterer import PatternClusterer

logger = logging.getLogger(__name__)


class CILPatternClusterer(PatternClusterer):
    """
    Enhanced PatternClusterer for CIL trading-specific clustering
    
    Extends the base PatternClusterer with trading-specific features and clustering logic.
    """
    
    def __init__(self):
        """Initialize CIL PatternClusterer with trading-specific features"""
        super().__init__()
        
        # Trading-specific numeric features
        self.trading_features = [
            'rr_ratio', 'max_drawdown', 'outcome_score', 'prediction_accuracy',
            'volume_ratio', 'volatility', 'regime_strength', 'session_quality',
            'slippage', 'execution_quality', 'risk_score'
        ]
        
        # Trading-specific categorical features (extend the base feature extractor)
        self.feature_extractor.categorical_columns.extend([
            'strength_range', 'rr_profile', 'market_conditions', 'trading_session',
            'venue', 'order_type', 'risk_level', 'strategy_type'
        ])
    
    def _extract_trading_features(self, strand: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract trading-specific features from strand
        
        Args:
            strand: Strand dictionary
            
        Returns:
            Dictionary of trading features
        """
        features = {}
        
        # Extract numeric trading features
        for feature in self.trading_features:
            features[feature] = strand.get(feature, 0.0)
        
        # Extract categorical trading features
        for feature in self.categorical_features:
            features[feature] = strand.get(feature, 'unknown')
        
        return features


class CILClustering(UniversalClustering):
    """
    CIL Specialized Clustering System
    
    Builds on universal clustering with trading-specific enhancements.
    """
    
    def __init__(self):
        """Initialize CIL clustering system"""
        super().__init__()
        
        # Trading-specific structural columns for Tier 1 clustering
        self.trading_structural_columns = [
            'symbol', 'timeframe', 'regime', 'session_bucket',
            'pattern_type', 'strength_range', 'rr_profile', 'market_conditions'
        ]
        
        # Initialize CIL PatternClusterer
        self.cil_pattern_clusterer = CILPatternClusterer()
        
        # Trading-specific clustering configuration
        self.strength_ranges = {
            'weak': (1.2, 1.5),
            'moderate': (1.5, 2.0),
            'strong': (2.0, 3.0),
            'extreme': (3.0, 5.0),
            'anomalous': (5.0, float('inf'))
        }
        
        self.rr_profiles = {
            'conservative': {'min_rr': 1.5, 'max_rr': 2.0, 'max_dd': 0.05},
            'moderate': {'min_rr': 2.0, 'max_rr': 3.0, 'max_dd': 0.10},
            'aggressive': {'min_rr': 3.0, 'max_rr': 5.0, 'max_dd': 0.20}
        }
    
    def cluster_trading_strands_by_columns(self, strands: List[Dict[str, Any]], braid_level: int) -> List[Cluster]:
        """
        Tier 1: Trading-Specific Column Clustering
        
        Groups trading strands by trading-specific structural columns.
        
        Args:
            strands: List of strand dictionaries
            braid_level: Braid level to cluster
            
        Returns:
            List of ColumnCluster objects
        """
        try:
            clusters = []
            
            for strand in strands:
                # Only cluster same braid level
                if strand.get('braid_level', 0) != braid_level:
                    continue
                
                # Find similar cluster based on trading-specific columns
                similar_cluster = self._find_similar_trading_cluster(strand, clusters)
                
                if similar_cluster:
                    similar_cluster.add_strand(strand)
                else:
                    # Create new cluster
                    cluster_key = self._generate_trading_cluster_key(strand)
                    new_cluster = Cluster(
                        strands=[strand],
                        cluster_key=cluster_key,
                        braid_level=braid_level,
                        created_at=datetime.now(timezone.utc)
                    )
                    clusters.append(new_cluster)
            
            self.logger.info(f"CIL column clustering: {len(strands)} strands -> {len(clusters)} clusters")
            return clusters
            
        except Exception as e:
            self.logger.error(f"Error in CIL column clustering: {e}")
            return []
    
    def cluster_trading_strands_by_patterns(self, column_clusters: List[Cluster]) -> List[Cluster]:
        """
        Tier 2: CIL Pattern Clustering (Enhanced PatternClusterer)
        
        Uses enhanced PatternClusterer for trading-specific pattern clustering.
        
        Args:
            column_clusters: List of ColumnCluster objects from tier 1
            
        Returns:
            List of PatternCluster objects
        """
        try:
            pattern_clusters = []
            
            for column_cluster in column_clusters:
                if column_cluster.size >= self.min_strands_for_ml_clustering:
                    # Use CIL PatternClusterer for trading-specific clustering
                    ml_clusters = self.cil_pattern_clusterer.cluster_situations(column_cluster.strands)
                    
                    # Convert ML clusters to our Cluster format
                    for i, ml_cluster in enumerate(ml_clusters):
                        cluster_key = f"{column_cluster.cluster_key}_cil_ml_{i}"
                        pattern_cluster = Cluster(
                            strands=ml_cluster.get('situations', []),
                            cluster_key=cluster_key,
                            braid_level=column_cluster.braid_level,
                            created_at=datetime.now(timezone.utc)
                        )
                        pattern_clusters.append(pattern_cluster)
                else:
                    # Too few strands, keep as single cluster
                    pattern_clusters.append(column_cluster)
            
            self.logger.info(f"CIL pattern clustering: {len(column_clusters)} column clusters -> {len(pattern_clusters)} pattern clusters")
            return pattern_clusters
            
        except Exception as e:
            self.logger.error(f"Error in CIL pattern clustering: {e}")
            return column_clusters
    
    def cluster_trading_strands(self, strands: List[Dict[str, Any]], braid_level: int) -> List[Cluster]:
        """
        Complete CIL two-tier clustering process
        
        Args:
            strands: List of strand dictionaries
            braid_level: Braid level to cluster
            
        Returns:
            List of final clusters after CIL two-tier clustering
        """
        try:
            # Step 1: Trading-specific column clustering
            column_clusters = self.cluster_trading_strands_by_columns(strands, braid_level)
            
            # Step 2: CIL pattern clustering (enhanced PatternClusterer)
            pattern_clusters = self.cluster_trading_strands_by_patterns(column_clusters)
            
            self.logger.info(f"CIL two-tier clustering complete: {len(strands)} strands -> {len(pattern_clusters)} final clusters")
            return pattern_clusters
            
        except Exception as e:
            self.logger.error(f"Error in CIL two-tier clustering: {e}")
            return []
    
    def classify_strength_range(self, strand: Dict[str, Any]) -> str:
        """
        Classify pattern strength range based on strand data
        
        Args:
            strand: Strand dictionary
            
        Returns:
            Strength range classification
        """
        try:
            # Get relevant metrics based on pattern type
            pattern_type = strand.get('pattern_type', 'unknown')
            
            if pattern_type == 'volume_spike':
                volume_ratio = strand.get('volume_ratio', 1.0)
                for range_name, (min_val, max_val) in self.strength_ranges.items():
                    if min_val <= volume_ratio < max_val:
                        return range_name
                return 'anomalous'
            
            elif pattern_type == 'divergence':
                divergence_strength = strand.get('divergence_strength', 0.0)
                if divergence_strength < 0.5:
                    return 'weak'
                elif divergence_strength < 0.7:
                    return 'moderate'
                elif divergence_strength < 0.9:
                    return 'strong'
                else:
                    return 'extreme'
            
            else:
                # Default classification based on confidence
                confidence = strand.get('sig_confidence', strand.get('confidence', 0.0))
                if confidence < 0.5:
                    return 'weak'
                elif confidence < 0.7:
                    return 'moderate'
                elif confidence < 0.9:
                    return 'strong'
                else:
                    return 'extreme'
                    
        except Exception as e:
            self.logger.error(f"Error classifying strength range: {e}")
            return 'moderate'
    
    def classify_rr_profile(self, strand: Dict[str, Any]) -> str:
        """
        Classify risk/reward profile based on strand data
        
        Args:
            strand: Strand dictionary
            
        Returns:
            R/R profile classification
        """
        try:
            rr_ratio = strand.get('rr_ratio', 0.0)
            max_drawdown = strand.get('max_drawdown', 0.0)
            
            for profile_name, profile_config in self.rr_profiles.items():
                if (profile_config['min_rr'] <= rr_ratio <= profile_config['max_rr'] and
                    max_drawdown <= profile_config['max_dd']):
                    return profile_name
            
            # Default to moderate if no match
            return 'moderate'
            
        except Exception as e:
            self.logger.error(f"Error classifying R/R profile: {e}")
            return 'moderate'
    
    def classify_market_conditions(self, strand: Dict[str, Any]) -> str:
        """
        Classify market conditions based on strand data
        
        Args:
            strand: Strand dictionary
            
        Returns:
            Market conditions classification
        """
        try:
            regime = strand.get('regime', 'unknown')
            volatility = strand.get('volatility', 0.0)
            
            if regime in ['bull', 'bear']:
                if volatility > 0.8:
                    return 'high_volatility'
                elif volatility > 0.5:
                    return 'moderate_volatility'
                else:
                    return 'low_volatility'
            elif regime == 'sideways':
                return 'sideways'
            elif regime in ['transition', 'anomaly']:
                return 'transitional'
            else:
                return 'unknown'
                
        except Exception as e:
            self.logger.error(f"Error classifying market conditions: {e}")
            return 'unknown'
    
    def _find_similar_trading_cluster(self, strand: Dict[str, Any], clusters: List[Cluster]) -> Optional[Cluster]:
        """
        Find a similar cluster based on trading-specific columns
        
        Args:
            strand: Strand to find similar cluster for
            clusters: Existing clusters to search
            
        Returns:
            Similar cluster if found, None otherwise
        """
        for cluster in clusters:
            if self._strands_are_trading_similar(strand, cluster.get_representative()):
                return cluster
        return None
    
    def _strands_are_trading_similar(self, strand1: Dict[str, Any], strand2: Dict[str, Any]) -> bool:
        """
        Check if two strands are trading-similar based on trading columns
        
        Args:
            strand1: First strand
            strand2: Second strand
            
        Returns:
            True if trading-similar, False otherwise
        """
        for column in self.trading_structural_columns:
            value1 = strand1.get(column)
            value2 = strand2.get(column)
            
            # Both must have the same value (or both be None/empty)
            if value1 != value2:
                return False
        
        return True
    
    def _generate_trading_cluster_key(self, strand: Dict[str, Any]) -> str:
        """
        Generate a cluster key for a strand based on trading columns
        
        Args:
            strand: Strand to generate key for
            
        Returns:
            Trading cluster key string
        """
        key_parts = []
        for column in self.trading_structural_columns:
            value = strand.get(column, 'unknown')
            key_parts.append(str(value))
        
        return '_'.join(key_parts)


# Example usage and testing
if __name__ == "__main__":
    # Test the CIL clustering system
    clustering = CILClustering()
    
    # Test trading strands
    test_strands = [
        {
            'id': 'trading_1',
            'symbol': 'BTC',
            'timeframe': '1h',
            'regime': 'bull',
            'pattern_type': 'volume_spike',
            'strength_range': 'strong',
            'rr_profile': 'moderate',
            'market_conditions': 'moderate_volatility',
            'braid_level': 0,
            'volume_ratio': 2.5,
            'rr_ratio': 2.5,
            'max_drawdown': 0.08
        },
        {
            'id': 'trading_2',
            'symbol': 'BTC',
            'timeframe': '1h',
            'regime': 'bull',
            'pattern_type': 'volume_spike',
            'strength_range': 'strong',
            'rr_profile': 'moderate',
            'market_conditions': 'moderate_volatility',
            'braid_level': 0,
            'volume_ratio': 2.3,
            'rr_ratio': 2.2,
            'max_drawdown': 0.09
        }
    ]
    
    # Test clustering
    clusters = clustering.cluster_trading_strands(test_strands, braid_level=0)
    
    print(f"CIL clustered {len(test_strands)} strands into {len(clusters)} clusters")
    for i, cluster in enumerate(clusters):
        print(f"Cluster {i+1}: {cluster.size} strands, key={cluster.cluster_key}")
        print(f"  Meets threshold: {clustering.cluster_meets_threshold(cluster)}")
