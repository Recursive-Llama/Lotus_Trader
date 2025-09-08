"""
PatternClusterer: Clusters similar situations into patterns using machine learning
Groups database records by similarity for lesson generation
"""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime, timezone
import json

logger = logging.getLogger(__name__)

class PatternClusterer:
    """
    Clusters similar situations into patterns using machine learning
    Groups database records by similarity for lesson generation
    """
    
    def __init__(self, min_cluster_size: int = 3, max_clusters: int = 10):
        """
        Initialize the pattern clusterer
        
        Args:
            min_cluster_size: Minimum number of records in a cluster
            max_clusters: Maximum number of clusters to create
        """
        self.min_cluster_size = min_cluster_size
        self.max_clusters = max_clusters
        self.scaler = StandardScaler()
        self.clustering_model = None
        self.feature_extractor = FeatureExtractor()
    
    def cluster_situations(self, similar_situations: List[Dict]) -> List[Dict]:
        """
        Cluster similar situations into patterns
        
        Args:
            similar_situations: List of similar database records
            
        Returns:
            List of clusters with metadata
        """
        if len(similar_situations) < self.min_cluster_size:
            logger.warning(f"Not enough situations for clustering: {len(similar_situations)} < {self.min_cluster_size}")
            return []
        
        try:
            # Extract features for clustering
            features = self._extract_clustering_features(similar_situations)
            
            if features is None or len(features) == 0:
                logger.warning("No features extracted for clustering")
                return []
            
            # Perform clustering
            clusters = self._perform_clustering(features, similar_situations)
            
            # Filter clusters by minimum size
            valid_clusters = [cluster for cluster in clusters if cluster['size'] >= self.min_cluster_size]
            
            logger.info(f"Created {len(valid_clusters)} valid clusters from {len(similar_situations)} situations")
            return valid_clusters
            
        except Exception as e:
            logger.error(f"Failed to cluster situations: {e}")
            return []
    
    def _extract_clustering_features(self, situations: List[Dict]) -> Optional[np.ndarray]:
        """
        Extract features for clustering
        
        Args:
            situations: List of database records
            
        Returns:
            Feature matrix for clustering
        """
        try:
            features = []
            
            for situation in situations:
                feature_vector = self.feature_extractor.extract_features(situation)
                if feature_vector is not None:
                    features.append(feature_vector)
            
            if len(features) == 0:
                return None
            
            return np.array(features)
            
        except Exception as e:
            logger.error(f"Failed to extract clustering features: {e}")
            return None
    
    def _perform_clustering(self, features: np.ndarray, situations: List[Dict]) -> List[Dict]:
        """
        Perform clustering using KMeans or DBSCAN algorithm
        
        Args:
            features: Feature matrix
            situations: Original database records
            
        Returns:
            List of clusters with metadata
        """
        try:
            # Standardize features
            features_scaled = self.scaler.fit_transform(features)
            
            # Determine optimal number of clusters
            n_clusters = self._determine_optimal_clusters(features_scaled)
            
            if n_clusters < 2:
                logger.warning("Not enough clusters determined, using single cluster")
                return self._create_single_cluster(situations, features)
            
            # Perform KMeans clustering
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(features_scaled)
            
            # Group situations by cluster
            clusters = []
            for cluster_id in range(n_clusters):
                cluster_indices = [i for i, label in enumerate(cluster_labels) if label == cluster_id]
                cluster_situations = [situations[i] for i in cluster_indices]
                cluster_features = features[cluster_indices]
                
                if len(cluster_situations) >= self.min_cluster_size:
                    cluster = {
                        'cluster_id': cluster_id,
                        'situations': cluster_situations,
                        'size': len(cluster_situations),
                        'centroid': kmeans.cluster_centers_[cluster_id].tolist(),
                        'features': cluster_features.tolist(),
                        'silhouette_score': self._calculate_cluster_silhouette(features_scaled, cluster_labels, cluster_id),
                        'cluster_metadata': self._extract_cluster_metadata(cluster_situations)
                    }
                    clusters.append(cluster)
            
            return clusters
            
        except Exception as e:
            logger.error(f"Failed to perform clustering: {e}")
            return []
    
    def _determine_optimal_clusters(self, features: np.ndarray) -> int:
        """
        Determine optimal number of clusters using silhouette score
        
        Args:
            features: Scaled feature matrix
            
        Returns:
            Optimal number of clusters
        """
        try:
            if len(features) < 4:
                return 1
            
            max_clusters = min(self.max_clusters, len(features) // 2)
            if max_clusters < 2:
                return 1
            
            best_score = -1
            best_n_clusters = 2
            
            for n_clusters in range(2, max_clusters + 1):
                try:
                    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
                    cluster_labels = kmeans.fit_predict(features)
                    
                    if len(set(cluster_labels)) > 1:  # Ensure we have multiple clusters
                        score = silhouette_score(features, cluster_labels)
                        if score > best_score:
                            best_score = score
                            best_n_clusters = n_clusters
                            
                except Exception as e:
                    logger.warning(f"Failed to calculate silhouette score for {n_clusters} clusters: {e}")
                    continue
            
            logger.info(f"Optimal number of clusters: {best_n_clusters} (silhouette score: {best_score:.3f})")
            return best_n_clusters
            
        except Exception as e:
            logger.error(f"Failed to determine optimal clusters: {e}")
            return 2
    
    def _calculate_cluster_silhouette(self, features: np.ndarray, cluster_labels: np.ndarray, cluster_id: int) -> float:
        """
        Calculate silhouette score for a specific cluster
        
        Args:
            features: Scaled feature matrix
            cluster_labels: Cluster labels
            cluster_id: ID of the cluster
            
        Returns:
            Silhouette score for the cluster
        """
        try:
            cluster_mask = cluster_labels == cluster_id
            if np.sum(cluster_mask) < 2:
                return 0.0
            
            cluster_features = features[cluster_mask]
            cluster_labels_subset = cluster_labels[cluster_mask]
            
            if len(set(cluster_labels_subset)) > 1:
                return silhouette_score(cluster_features, cluster_labels_subset)
            else:
                return 0.0
                
        except Exception as e:
            logger.warning(f"Failed to calculate cluster silhouette: {e}")
            return 0.0
    
    def _extract_cluster_metadata(self, cluster_situations: List[Dict]) -> Dict[str, Any]:
        """
        Extract metadata about a cluster
        
        Args:
            cluster_situations: Situations in the cluster
            
        Returns:
            Cluster metadata
        """
        try:
            metadata = {
                'symbols': list(set(s.get('symbol', 'unknown') for s in cluster_situations)),
                'timeframes': list(set(s.get('timeframe', 'unknown') for s in cluster_situations)),
                'regimes': list(set(s.get('regime', 'unknown') for s in cluster_situations)),
                'directions': list(set(s.get('sig_direction', 'unknown') for s in cluster_situations)),
                'avg_confidence': np.mean([s.get('sig_confidence', 0) for s in cluster_situations]),
                'avg_strength': np.mean([s.get('sig_sigma', 0) for s in cluster_situations]),
                'date_range': self._get_date_range(cluster_situations),
                'common_patterns': self._find_common_patterns(cluster_situations)
            }
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to extract cluster metadata: {e}")
            return {}
    
    def _get_date_range(self, situations: List[Dict]) -> Dict[str, str]:
        """
        Get date range for cluster situations
        
        Args:
            situations: List of situations
            
        Returns:
            Date range dictionary
        """
        try:
            dates = []
            for situation in situations:
                if 'created_at' in situation:
                    dates.append(situation['created_at'])
            
            if dates:
                return {
                    'earliest': min(dates),
                    'latest': max(dates)
                }
            else:
                return {'earliest': None, 'latest': None}
                
        except Exception as e:
            logger.warning(f"Failed to get date range: {e}")
            return {'earliest': None, 'latest': None}
    
    def _find_common_patterns(self, situations: List[Dict]) -> List[str]:
        """
        Find common patterns in cluster situations
        
        Args:
            situations: List of situations
            
        Returns:
            List of common patterns
        """
        try:
            pattern_counts = {}
            
            for situation in situations:
                if 'patterns' in situation:
                    patterns = situation['patterns']
                    if isinstance(patterns, dict):
                        for pattern, value in patterns.items():
                            if value:
                                pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
                    elif isinstance(patterns, list):
                        for pattern in patterns:
                            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
            
            # Return patterns that appear in at least 50% of situations
            threshold = len(situations) * 0.5
            common_patterns = [pattern for pattern, count in pattern_counts.items() if count >= threshold]
            
            return common_patterns
            
        except Exception as e:
            logger.warning(f"Failed to find common patterns: {e}")
            return []
    
    def _create_single_cluster(self, situations: List[Dict], features: np.ndarray) -> List[Dict]:
        """
        Create a single cluster when clustering fails
        
        Args:
            situations: List of situations
            features: Feature matrix
            
        Returns:
            List with single cluster
        """
        try:
            cluster = {
                'cluster_id': 0,
                'situations': situations,
                'size': len(situations),
                'centroid': np.mean(features, axis=0).tolist(),
                'features': features.tolist(),
                'silhouette_score': 0.0,
                'cluster_metadata': self._extract_cluster_metadata(situations)
            }
            
            return [cluster]
            
        except Exception as e:
            logger.error(f"Failed to create single cluster: {e}")
            return []


class FeatureExtractor:
    """
    Extracts features from database records for clustering
    """
    
    def __init__(self):
        self.numeric_columns = [
            'sig_confidence', 'sig_sigma', 'accumulated_score',
            'rsi', 'macd', 'bb_position', 'volume_ratio', 'volatility'
        ]
        self.categorical_columns = [
            'symbol', 'timeframe', 'regime', 'sig_direction', 'kind'
        ]
    
    def extract_features(self, record: Dict) -> Optional[np.ndarray]:
        """
        Extract features from a database record
        
        Args:
            record: Database record
            
        Returns:
            Feature vector or None if extraction fails
        """
        try:
            features = []
            
            # Extract numeric features
            for column in self.numeric_columns:
                value = record.get(column, 0)
                if isinstance(value, (int, float)):
                    features.append(float(value))
                else:
                    features.append(0.0)
            
            # Extract categorical features (one-hot encoding)
            for column in self.categorical_columns:
                value = str(record.get(column, 'unknown')).lower()
                
                # Simple categorical encoding
                if column == 'symbol':
                    symbol_encoding = {'btc': 1, 'eth': 2, 'sol': 3}.get(value, 0)
                    features.append(symbol_encoding)
                elif column == 'timeframe':
                    timeframe_encoding = {'1m': 1, '5m': 2, '15m': 3, '1h': 4}.get(value, 0)
                    features.append(timeframe_encoding)
                elif column == 'regime':
                    regime_encoding = {'trending_up': 1, 'trending_down': -1, 'ranging': 0}.get(value, 0)
                    features.append(regime_encoding)
                elif column == 'sig_direction':
                    direction_encoding = {'long': 1, 'short': -1}.get(value, 0)
                    features.append(direction_encoding)
                else:
                    features.append(0.0)
            
            # Extract pattern features
            pattern_features = self._extract_pattern_features(record)
            features.extend(pattern_features)
            
            return np.array(features)
            
        except Exception as e:
            logger.error(f"Failed to extract features from record: {e}")
            return None
    
    def _extract_pattern_features(self, record: Dict) -> List[float]:
        """
        Extract pattern-related features
        
        Args:
            record: Database record
            
        Returns:
            List of pattern features
        """
        try:
            pattern_features = []
            
            # Check for common patterns
            common_patterns = [
                'breakout_up', 'breakout_down', 'support_level', 'resistance_level',
                'bullish_divergence', 'bearish_divergence', 'volume_spike'
            ]
            
            for pattern in common_patterns:
                if 'patterns' in record:
                    patterns = record['patterns']
                    if isinstance(patterns, dict):
                        pattern_features.append(1.0 if patterns.get(pattern, False) else 0.0)
                    else:
                        pattern_features.append(0.0)
                else:
                    pattern_features.append(0.0)
            
            return pattern_features
            
        except Exception as e:
            logger.warning(f"Failed to extract pattern features: {e}")
            return [0.0] * 7  # Return zeros for all pattern features
