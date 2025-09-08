"""
DatabaseDrivenContextSystem: Orchestrates context retrieval using vector search and pattern matching
Leverages database structure for intelligent context injection
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime, timezone, timedelta
import json
import uuid

from .context_indexer import ContextIndexer
from .pattern_clusterer import PatternClusterer
from src.utils.supabase_manager import SupabaseManager

logger = logging.getLogger(__name__)

class DatabaseDrivenContextSystem:
    """
    Orchestrates context retrieval using vector search and pattern matching
    Leverages database structure for intelligent context injection
    """
    
    def __init__(self, db_manager: SupabaseManager, embedding_model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the database-driven context system
        
        Args:
            db_manager: Database manager for accessing data
            embedding_model_name: Name of the embedding model to use
        """
        self.db_manager = db_manager
        self.context_indexer = ContextIndexer(embedding_model_name)
        self.pattern_clusterer = PatternClusterer()
        self.vector_cache = {}  # Cache for frequently accessed vectors
        self.cache_ttl = timedelta(hours=1)  # Cache time-to-live
    
    def get_relevant_context(self, current_analysis: Dict, top_k: int = 10, 
                           similarity_threshold: float = 0.7) -> Dict:
        """
        Get relevant context using vector search and pattern clustering
        
        Args:
            current_analysis: Current analysis data
            top_k: Number of similar situations to retrieve
            similarity_threshold: Minimum similarity score for inclusion
            
        Returns:
            Enhanced context with relevant lessons and patterns
        """
        try:
            logger.info("Starting context retrieval process")
            
            # 1. Create context vector for current analysis
            current_vector = self.context_indexer.create_context_vector(current_analysis)
            
            # 2. Find similar historical situations using vector search
            similar_situations = self._find_similar_situations(
                current_vector, top_k, similarity_threshold
            )
            
            if not similar_situations:
                logger.warning("No similar situations found")
                return self._create_empty_context(current_analysis)
            
            # 3. Cluster similar situations into patterns
            clusters = self.pattern_clusterer.cluster_situations(similar_situations)
            
            # 4. Generate lessons from clusters using LLM
            lessons = []
            for cluster in clusters:
                if cluster['size'] >= 3:  # Only clusters with enough data
                    lesson = self._generate_cluster_lesson(cluster)
                    if lesson:
                        lessons.append(lesson)
            
            # 5. Inject most relevant lessons into context
            relevant_lessons = self._select_most_relevant_lessons(lessons, current_analysis)
            
            context = {
                'current_analysis': current_analysis,
                'similar_situations': similar_situations,
                'pattern_clusters': clusters,
                'generated_lessons': relevant_lessons,
                'context_metadata': {
                    'similarity_scores': [s.get('similarity', 0) for s in similar_situations],
                    'cluster_sizes': [c['size'] for c in clusters],
                    'lesson_count': len(relevant_lessons),
                    'retrieval_timestamp': datetime.now(timezone.utc).isoformat()
                }
            }
            
            logger.info(f"Context retrieval complete: {len(similar_situations)} similar situations, "
                       f"{len(clusters)} clusters, {len(relevant_lessons)} lessons")
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to get relevant context: {e}")
            return self._create_empty_context(current_analysis)
    
    def _find_similar_situations(self, current_vector: np.ndarray, top_k: int, 
                               similarity_threshold: float) -> List[Dict]:
        """
        Find similar historical situations using vector search
        
        Args:
            current_vector: Vector representation of current analysis
            top_k: Number of similar situations to retrieve
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of similar situations with similarity scores
        """
        try:
            # Get recent database records
            recent_records = self._get_recent_database_records()
            
            if not recent_records:
                logger.warning("No recent database records found")
                return []
            
            # Calculate similarities
            similarities = []
            for record in recent_records:
                if 'context_vector' in record and record['context_vector']:
                    try:
                        record_vector = np.array(record['context_vector'])
                        similarity = self.context_indexer.get_similarity_score(current_vector, record_vector)
                        
                        if similarity >= similarity_threshold:
                            record['similarity'] = similarity
                            similarities.append(record)
                    except Exception as e:
                        logger.warning(f"Failed to calculate similarity for record {record.get('id', 'unknown')}: {e}")
                        continue
            
            # Sort by similarity and return top_k
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            return similarities[:top_k]
            
        except Exception as e:
            logger.error(f"Failed to find similar situations: {e}")
            return []
    
    def _get_recent_database_records(self, days_back: int = 30) -> List[Dict]:
        """
        Get recent database records for context retrieval
        
        Args:
            days_back: Number of days to look back
            
        Returns:
            List of recent database records
        """
        try:
            # Calculate date threshold
            threshold_date = datetime.now(timezone.utc) - timedelta(days=days_back)
            
            # Query recent records from AD_strands table
            query = """
                SELECT * FROM AD_strands 
                WHERE created_at >= %s 
                AND context_vector IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 1000
            """
            
            result = self.db_manager.execute_query(query, (threshold_date,))
            
            if result:
                records = []
                for row in result:
                    record = dict(row)
                    # Parse JSON fields if they exist
                    for field in ['trading_plan', 'signal_pack', 'dsi_evidence', 'regime_context', 'event_context', 'module_intelligence', 'curator_feedback']:
                        if field in record and record[field]:
                            try:
                                record[field] = json.loads(record[field]) if isinstance(record[field], str) else record[field]
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse JSON field {field}")
                                record[field] = {}
                    
                    records.append(record)
                
                logger.info(f"Retrieved {len(records)} recent database records")
                return records
            else:
                logger.warning("No recent database records found")
                return []
                
        except Exception as e:
            logger.error(f"Failed to get recent database records: {e}")
            return []
    
    def _generate_cluster_lesson(self, cluster: Dict) -> Optional[Dict]:
        """
        Generate lesson from clustered situations
        
        Args:
            cluster: Cluster of similar situations
            
        Returns:
            Generated lesson or None if generation fails
        """
        try:
            # For now, create a basic lesson structure
            # This will be enhanced with LLM integration in Day 3
            lesson = {
                'lesson_id': f"lesson_{uuid.uuid4().hex[:8]}",
                'cluster_id': cluster['cluster_id'],
                'situation_count': cluster['size'],
                'lesson_content': self._create_basic_lesson_content(cluster),
                'key_insights': self._extract_key_insights(cluster),
                'actionable_recommendations': self._extract_recommendations(cluster),
                'confidence_score': self._calculate_lesson_confidence(cluster),
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
            
            return lesson
            
        except Exception as e:
            logger.error(f"Failed to generate cluster lesson: {e}")
            return None
    
    def _create_basic_lesson_content(self, cluster: Dict) -> str:
        """
        Create basic lesson content from cluster
        
        Args:
            cluster: Cluster of similar situations
            
        Returns:
            Basic lesson content
        """
        try:
            metadata = cluster.get('cluster_metadata', {})
            situations = cluster.get('situations', [])
            
            # Extract key information
            symbols = metadata.get('symbols', ['unknown'])
            timeframes = metadata.get('timeframes', ['unknown'])
            regimes = metadata.get('regimes', ['unknown'])
            directions = metadata.get('directions', ['unknown'])
            avg_confidence = metadata.get('avg_confidence', 0)
            avg_strength = metadata.get('avg_strength', 0)
            common_patterns = metadata.get('common_patterns', [])
            
            lesson_parts = [
                f"Pattern Analysis: {len(situations)} similar situations found",
                f"Symbols: {', '.join(symbols)}",
                f"Timeframes: {', '.join(timeframes)}",
                f"Regimes: {', '.join(regimes)}",
                f"Directions: {', '.join(directions)}",
                f"Average Confidence: {avg_confidence:.2f}",
                f"Average Strength: {avg_strength:.2f}"
            ]
            
            if common_patterns:
                lesson_parts.append(f"Common Patterns: {', '.join(common_patterns)}")
            
            return " | ".join(lesson_parts)
            
        except Exception as e:
            logger.error(f"Failed to create basic lesson content: {e}")
            return "Basic lesson content generation failed"
    
    def _extract_key_insights(self, cluster: Dict) -> List[str]:
        """
        Extract key insights from cluster
        
        Args:
            cluster: Cluster of similar situations
            
        Returns:
            List of key insights
        """
        try:
            insights = []
            metadata = cluster.get('cluster_metadata', {})
            
            # Analyze confidence and strength
            avg_confidence = metadata.get('avg_confidence', 0)
            avg_strength = metadata.get('avg_strength', 0)
            
            if avg_confidence > 0.7:
                insights.append("High confidence pattern detected")
            elif avg_confidence < 0.4:
                insights.append("Low confidence pattern detected")
            
            if avg_strength > 0.6:
                insights.append("Strong signal pattern")
            elif avg_strength < 0.3:
                insights.append("Weak signal pattern")
            
            # Analyze common patterns
            common_patterns = metadata.get('common_patterns', [])
            if common_patterns:
                insights.append(f"Consistent patterns: {', '.join(common_patterns)}")
            
            # Analyze regime consistency
            regimes = metadata.get('regimes', [])
            if len(regimes) == 1:
                insights.append(f"Consistent regime: {regimes[0]}")
            elif len(regimes) > 1:
                insights.append(f"Mixed regimes: {', '.join(regimes)}")
            
            return insights
            
        except Exception as e:
            logger.error(f"Failed to extract key insights: {e}")
            return []
    
    def _extract_recommendations(self, cluster: Dict) -> List[str]:
        """
        Extract actionable recommendations from cluster
        
        Args:
            cluster: Cluster of similar situations
            
        Returns:
            List of actionable recommendations
        """
        try:
            recommendations = []
            metadata = cluster.get('cluster_metadata', {})
            
            # Analyze confidence and strength for recommendations
            avg_confidence = metadata.get('avg_confidence', 0)
            avg_strength = metadata.get('avg_strength', 0)
            
            if avg_confidence > 0.7 and avg_strength > 0.6:
                recommendations.append("Consider high-confidence trade execution")
            elif avg_confidence < 0.4 or avg_strength < 0.3:
                recommendations.append("Exercise caution - low confidence/strength pattern")
            
            # Analyze common patterns for recommendations
            common_patterns = metadata.get('common_patterns', [])
            if 'breakout_up' in common_patterns:
                recommendations.append("Monitor for upward breakout confirmation")
            elif 'breakout_down' in common_patterns:
                recommendations.append("Monitor for downward breakout confirmation")
            
            if 'volume_spike' in common_patterns:
                recommendations.append("Volume confirmation is important for this pattern")
            
            # Analyze regime for recommendations
            regimes = metadata.get('regimes', [])
            if 'trending_up' in regimes:
                recommendations.append("Consider trend-following strategies")
            elif 'trending_down' in regimes:
                recommendations.append("Consider trend-following or reversal strategies")
            elif 'ranging' in regimes:
                recommendations.append("Consider range-bound trading strategies")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to extract recommendations: {e}")
            return []
    
    def _calculate_lesson_confidence(self, cluster: Dict) -> float:
        """
        Calculate confidence score for lesson
        
        Args:
            cluster: Cluster of similar situations
            
        Returns:
            Confidence score between 0 and 1
        """
        try:
            # Base confidence on cluster size and silhouette score
            cluster_size = cluster.get('size', 0)
            silhouette_score = cluster.get('silhouette_score', 0)
            
            # Size factor (more situations = higher confidence)
            size_factor = min(1.0, cluster_size / 10.0)  # Normalize to 10 situations
            
            # Silhouette factor (better clustering = higher confidence)
            silhouette_factor = max(0.0, silhouette_score)
            
            # Combine factors
            confidence = (size_factor * 0.6) + (silhouette_factor * 0.4)
            
            return min(1.0, max(0.0, confidence))
            
        except Exception as e:
            logger.error(f"Failed to calculate lesson confidence: {e}")
            return 0.0
    
    def _select_most_relevant_lessons(self, lessons: List[Dict], current_analysis: Dict) -> List[Dict]:
        """
        Select most relevant lessons for current analysis
        
        Args:
            lessons: List of generated lessons
            current_analysis: Current analysis data
            
        Returns:
            List of most relevant lessons
        """
        try:
            if not lessons:
                return []
            
            # Score lessons based on relevance to current analysis
            scored_lessons = []
            for lesson in lessons:
                relevance_score = self._calculate_lesson_relevance(lesson, current_analysis)
                lesson['relevance_score'] = relevance_score
                scored_lessons.append(lesson)
            
            # Sort by relevance score and return top 3
            scored_lessons.sort(key=lambda x: x['relevance_score'], reverse=True)
            return scored_lessons[:3]
            
        except Exception as e:
            logger.error(f"Failed to select relevant lessons: {e}")
            return lessons[:3]  # Return first 3 if scoring fails
    
    def _calculate_lesson_relevance(self, lesson: Dict, current_analysis: Dict) -> float:
        """
        Calculate relevance score for a lesson
        
        Args:
            lesson: Lesson to score
            current_analysis: Current analysis data
            
        Returns:
            Relevance score between 0 and 1
        """
        try:
            score = 0.0
            
            # Match on symbol
            if 'symbol' in current_analysis:
                lesson_content = lesson.get('lesson_content', '')
                if current_analysis['symbol'].lower() in lesson_content.lower():
                    score += 0.3
            
            # Match on timeframe
            if 'timeframe' in current_analysis:
                lesson_content = lesson.get('lesson_content', '')
                if current_analysis['timeframe'] in lesson_content:
                    score += 0.2
            
            # Match on regime
            if 'regime' in current_analysis:
                lesson_content = lesson.get('lesson_content', '')
                if current_analysis['regime'] in lesson_content:
                    score += 0.2
            
            # Match on direction
            if 'sig_direction' in current_analysis:
                lesson_content = lesson.get('lesson_content', '')
                if current_analysis['sig_direction'] in lesson_content:
                    score += 0.2
            
            # Add confidence factor
            confidence = lesson.get('confidence_score', 0)
            score += confidence * 0.1
            
            return min(1.0, score)
            
        except Exception as e:
            logger.error(f"Failed to calculate lesson relevance: {e}")
            return 0.0
    
    def _create_empty_context(self, current_analysis: Dict) -> Dict:
        """
        Create empty context when no similar situations are found
        
        Args:
            current_analysis: Current analysis data
            
        Returns:
            Empty context structure
        """
        return {
            'current_analysis': current_analysis,
            'similar_situations': [],
            'pattern_clusters': [],
            'generated_lessons': [],
            'context_metadata': {
                'similarity_scores': [],
                'cluster_sizes': [],
                'lesson_count': 0,
                'retrieval_timestamp': datetime.now(timezone.utc).isoformat(),
                'status': 'no_similar_situations_found'
            }
        }
    
    def index_database_records(self, records: List[Dict]) -> List[Dict]:
        """
        Index database records with context vectors
        
        Args:
            records: List of database records to index
            
        Returns:
            List of records with added context vectors
        """
        try:
            logger.info(f"Indexing {len(records)} database records")
            
            # Create context vectors for records
            enhanced_records = self.context_indexer.batch_create_vectors(records)
            
            # Store vectors in database
            self._store_context_vectors(enhanced_records)
            
            logger.info(f"Successfully indexed {len(enhanced_records)} records")
            return enhanced_records
            
        except Exception as e:
            logger.error(f"Failed to index database records: {e}")
            return records
    
    def _store_context_vectors(self, enhanced_records: List[Dict]) -> None:
        """
        Store context vectors in database
        
        Args:
            enhanced_records: Records with context vectors
        """
        try:
            for record in enhanced_records:
                if 'context_vector' in record and record['context_vector']:
                    # Update record with context vector
                    update_query = """
                        UPDATE AD_strands 
                        SET context_vector = %s, context_string = %s, vector_created_at = %s
                        WHERE id = %s
                    """
                    
                    self.db_manager.execute_query(update_query, (
                        json.dumps(record['context_vector']),
                        record.get('context_string', ''),
                        record.get('vector_created_at', datetime.now(timezone.utc).isoformat()),
                        record['id']
                    ))
            
            logger.info(f"Stored context vectors for {len(enhanced_records)} records")
            
        except Exception as e:
            logger.error(f"Failed to store context vectors: {e}")
            raise
