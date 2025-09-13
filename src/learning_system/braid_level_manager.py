"""
Braid Level Manager

Manages braid creation and level promotion based on quality thresholds and learning criteria.
This manager handles the creation of braids at appropriate levels based on strand quality.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
import uuid

logger = logging.getLogger(__name__)


class BraidLevelManager:
    """
    Braid Level Manager
    
    Manages braid creation and level promotion based on quality thresholds and learning criteria.
    This manager handles the creation of braids at appropriate levels based on strand quality.
    """
    
    def __init__(self, supabase_manager):
        """
        Initialize braid level manager
        
        Args:
            supabase_manager: Database manager for strand operations
        """
        self.supabase_manager = supabase_manager
        self.logger = logging.getLogger(__name__)
        
        # Quality thresholds for braid creation - SAME THRESHOLD FOR ALL LEVELS
        # Braids cluster with other braids of the same level, not higher individual scores
        self.quality_thresholds = {
            'level_2': {
                'min_resonance': 0.6,
                'min_strands': 3,
                'min_persistence': 0.5,
                'min_novelty': 0.4,
                'min_surprise': 0.4
            },
            'level_3': {
                'min_resonance': 0.6,  # SAME as level 2
                'min_strands': 3,      # SAME as level 2
                'min_persistence': 0.5, # SAME as level 2
                'min_novelty': 0.4,    # SAME as level 2
                'min_surprise': 0.4    # SAME as level 2
            },
            'level_4': {
                'min_resonance': 0.6,  # SAME as level 2
                'min_strands': 3,      # SAME as level 2
                'min_persistence': 0.5, # SAME as level 2
                'min_novelty': 0.4,    # SAME as level 2
                'min_surprise': 0.4    # SAME as level 2
            }
        }
    
    async def create_braid(
        self, 
        source_strands: List[Dict[str, Any]], 
        strand_type: str,
        target_level: int = 2
    ) -> Optional[str]:
        """
        Create a braid from source strands
        
        Args:
            source_strands: List of source strands
            strand_type: Type of strands
            target_level: Target braid level (2, 3, or 4)
            
        Returns:
            Braid ID if successful, None otherwise
        """
        try:
            if not source_strands:
                self.logger.warning("No source strands provided for braid creation")
                return None
            
            # Check if strands meet quality thresholds
            if not self._meets_quality_thresholds(source_strands, target_level):
                self.logger.warning(f"Source strands do not meet quality thresholds for level {target_level}")
                return None
            
            # Calculate braid scores
            braid_scores = self._calculate_braid_scores(source_strands)
            
            # Create braid data
            braid_data = self._create_braid_data(
                source_strands, 
                strand_type, 
                target_level, 
                braid_scores
            )
            
            # Save braid to database
            braid_id = await self._save_braid(braid_data)
            
            if braid_id:
                self.logger.info(f"Created level {target_level} braid {braid_id} from {len(source_strands)} {strand_type} strands")
                return braid_id
            else:
                self.logger.error("Failed to save braid to database")
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating braid: {e}")
            return None
    
    def _meets_quality_thresholds(self, source_strands: List[Dict[str, Any]], target_level: int) -> bool:
        """Check if source strands meet quality thresholds for target level"""
        try:
            level_key = f'level_{target_level}'
            if level_key not in self.quality_thresholds:
                self.logger.warning(f"Unknown target level: {target_level}")
                return False
            
            thresholds = self.quality_thresholds[level_key]
            
            # Check minimum strand count
            if len(source_strands) < thresholds['min_strands']:
                return False
            
            # Calculate average scores
            avg_resonance = sum(s.get('resonance_score', 0) for s in source_strands) / len(source_strands)
            avg_persistence = sum(s.get('persistence_score', 0) for s in source_strands) / len(source_strands)
            avg_novelty = sum(s.get('novelty_score', 0) for s in source_strands) / len(source_strands)
            avg_surprise = sum(s.get('surprise_rating', 0) for s in source_strands) / len(source_strands)
            
            # Check all thresholds
            meets_resonance = avg_resonance >= thresholds['min_resonance']
            meets_persistence = avg_persistence >= thresholds['min_persistence']
            meets_novelty = avg_novelty >= thresholds['min_novelty']
            meets_surprise = avg_surprise >= thresholds['min_surprise']
            
            return meets_resonance and meets_persistence and meets_novelty and meets_surprise
            
        except Exception as e:
            self.logger.error(f"Error checking quality thresholds: {e}")
            return False
    
    def _calculate_braid_scores(self, source_strands: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate braid scores from source strands"""
        try:
            # Calculate average scores
            avg_persistence = sum(s.get('persistence_score', 0.5) for s in source_strands) / len(source_strands)
            avg_novelty = sum(s.get('novelty_score', 0.5) for s in source_strands) / len(source_strands)
            avg_surprise = sum(s.get('surprise_rating', 0.5) for s in source_strands) / len(source_strands)
            
            # Calculate overall resonance
            avg_resonance = (avg_persistence + avg_novelty + avg_surprise) / 3
            
            # Calculate quality metrics
            quality_metrics = {
                'persistence': avg_persistence,
                'novelty': avg_novelty,
                'surprise': avg_surprise,
                'resonance': avg_resonance,
                'strand_count': len(source_strands),
                'quality_score': avg_resonance * (1 + (len(source_strands) - 3) * 0.1)  # Bonus for more strands
            }
            
            return quality_metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating braid scores: {e}")
            return {
                'persistence': 0.5,
                'novelty': 0.5,
                'surprise': 0.5,
                'resonance': 0.5,
                'strand_count': len(source_strands),
                'quality_score': 0.5
            }
    
    def _create_braid_data(
        self, 
        source_strands: List[Dict[str, Any]], 
        strand_type: str, 
        target_level: int, 
        braid_scores: Dict[str, float]
    ) -> Dict[str, Any]:
        """Create braid data dictionary"""
        try:
            braid_id = str(uuid.uuid4())
            created_at = datetime.now(timezone.utc).isoformat()
            
            # Extract source strand IDs
            source_strand_ids = [s.get('id') for s in source_strands if s.get('id')]
            
            # Extract clustering metadata from source strands for re-clustering
            clustering_metadata = self._extract_clustering_metadata(source_strands)
            
            # Create braid content with preserved metadata
            braid_content = {
                'braid_analysis': f"Level {target_level} braid created from {len(source_strands)} {strand_type} strands",
                'source_strands': source_strand_ids,
                'creation_metadata': {
                    'target_level': target_level,
                    'strand_type': strand_type,
                    'creation_timestamp': created_at,
                    'quality_scores': braid_scores
                },
                'clustering_metadata': clustering_metadata,  # For re-clustering
                'learning_insights': self._generate_learning_insights(source_strands, braid_scores)
            }
            
            # Create braid data
            braid_data = {
                'id': braid_id,
                'kind': f'{strand_type}_braid',
                'agent_id': 'learning_system',
                'braid_level': target_level,
                'created_at': created_at,
                'persistence_score': braid_scores['persistence'],
                'novelty_score': braid_scores['novelty'],
                'surprise_rating': braid_scores['surprise'],
                'resonance_score': braid_scores['resonance'],
                'quality_score': braid_scores['quality_score'],
                'source_strand_count': len(source_strands),
                'source_strands': source_strand_ids,
                'cluster_key': clustering_metadata['cluster_key'],  # For re-clustering
                'content': braid_content,
                'status': 'active'
            }
            
            return braid_data
            
        except Exception as e:
            self.logger.error(f"Error creating braid data: {e}")
            return {}
    
    def _generate_learning_insights(
        self, 
        source_strands: List[Dict[str, Any]], 
        braid_scores: Dict[str, float]
    ) -> Dict[str, Any]:
        """Generate learning insights for the braid"""
        try:
            # Analyze score distributions
            persistence_scores = [s.get('persistence_score', 0.5) for s in source_strands]
            novelty_scores = [s.get('novelty_score', 0.5) for s in source_strands]
            surprise_scores = [s.get('surprise_rating', 0.5) for s in source_strands]
            
            insights = {
                'score_analysis': {
                    'persistence_range': [min(persistence_scores), max(persistence_scores)],
                    'novelty_range': [min(novelty_scores), max(novelty_scores)],
                    'surprise_range': [min(surprise_scores), max(surprise_scores)],
                    'score_consistency': self._calculate_score_consistency(persistence_scores, novelty_scores, surprise_scores)
                },
                'quality_assessment': {
                    'overall_quality': 'high' if braid_scores['resonance'] > 0.7 else 'medium' if braid_scores['resonance'] > 0.5 else 'low',
                    'learning_potential': 'excellent' if braid_scores['quality_score'] > 0.8 else 'good' if braid_scores['quality_score'] > 0.6 else 'fair',
                    'strand_diversity': 'high' if len(set(persistence_scores)) > len(persistence_scores) * 0.7 else 'medium'
                },
                'recommendations': self._generate_recommendations(braid_scores, len(source_strands))
            }
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error generating learning insights: {e}")
            return {'error': str(e)}
    
    def _calculate_score_consistency(self, persistence_scores: List[float], novelty_scores: List[float], surprise_scores: List[float]) -> str:
        """Calculate score consistency across strands"""
        try:
            # Calculate coefficient of variation for each score type
            def cv(scores):
                if not scores or len(scores) < 2:
                    return 0
                mean_score = sum(scores) / len(scores)
                if mean_score == 0:
                    return 0
                variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
                std_dev = variance ** 0.5
                return std_dev / mean_score
            
            persistence_cv = cv(persistence_scores)
            novelty_cv = cv(novelty_scores)
            surprise_cv = cv(surprise_scores)
            
            avg_cv = (persistence_cv + novelty_cv + surprise_cv) / 3
            
            if avg_cv < 0.1:
                return 'very_consistent'
            elif avg_cv < 0.2:
                return 'consistent'
            elif avg_cv < 0.3:
                return 'moderately_consistent'
            else:
                return 'inconsistent'
                
        except Exception as e:
            self.logger.error(f"Error calculating score consistency: {e}")
            return 'unknown'
    
    def _extract_clustering_metadata(self, source_strands: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract clustering metadata from source strands for re-clustering"""
        try:
            # Extract common clustering attributes
            symbols = set()
            timeframes = set()
            pattern_types = set()
            group_signatures = set()
            
            for strand in source_strands:
                # Extract symbol
                if 'symbol' in strand:
                    symbols.add(strand['symbol'])
                
                # Extract timeframe
                if 'timeframe' in strand:
                    timeframes.add(strand['timeframe'])
                
                # Extract pattern type from module_intelligence
                module_intel = strand.get('module_intelligence', {})
                if 'pattern_type' in module_intel:
                    pattern_types.add(module_intel['pattern_type'])
                
                # Extract group signature
                if 'group_signature' in strand:
                    group_signatures.add(strand['group_signature'])
            
            # Generate cluster key for re-clustering
            cluster_key = self._generate_cluster_key(source_strands)
            
            return {
                'symbols': list(symbols),
                'timeframes': list(timeframes),
                'pattern_types': list(pattern_types),
                'group_signatures': list(group_signatures),
                'cluster_key': cluster_key,
                'original_cluster_keys': [s.get('cluster_key', 'unknown') for s in source_strands if s.get('cluster_key')]
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting clustering metadata: {e}")
            return {
                'symbols': [],
                'timeframes': [],
                'pattern_types': [],
                'group_signatures': [],
                'cluster_key': 'unknown',
                'original_cluster_keys': []
            }
    
    def _generate_cluster_key(self, source_strands: List[Dict[str, Any]]) -> str:
        """Generate a cluster key for the braid based on source strands"""
        try:
            if not source_strands:
                return 'unknown'
            
            # Get the most common attributes from source strands
            symbols = set()
            timeframes = set()
            pattern_types = set()
            
            for strand in source_strands:
                if 'symbol' in strand:
                    symbols.add(strand['symbol'])
                if 'timeframe' in strand:
                    timeframes.add(strand['timeframe'])
                
                module_intel = strand.get('module_intelligence', {})
                if 'pattern_type' in module_intel:
                    pattern_types.add(module_intel['pattern_type'])
            
            # Use the most common values or first available
            symbol = list(symbols)[0] if symbols else 'unknown'
            timeframe = list(timeframes)[0] if timeframes else 'unknown'
            pattern_type = list(pattern_types)[0] if pattern_types else 'unknown'
            
            # Generate cluster key for re-clustering
            return f"{symbol}_{timeframe}_{pattern_type}"
            
        except Exception as e:
            self.logger.error(f"Error generating cluster key: {e}")
            return 'unknown'

    def _generate_recommendations(self, braid_scores: Dict[str, float], strand_count: int) -> List[str]:
        """Generate recommendations based on braid scores"""
        try:
            recommendations = []
            
            # Resonance-based recommendations
            if braid_scores['resonance'] > 0.8:
                recommendations.append("Excellent braid quality - consider promoting to higher level")
            elif braid_scores['resonance'] > 0.6:
                recommendations.append("Good braid quality - monitor for improvement opportunities")
            else:
                recommendations.append("Braid quality needs improvement - focus on source strand quality")
            
            # Strand count recommendations
            if strand_count > 10:
                recommendations.append("Large braid - consider splitting into smaller, more focused braids")
            elif strand_count < 5:
                recommendations.append("Small braid - consider adding more high-quality strands")
            
            # Individual score recommendations
            if braid_scores['persistence'] < 0.6:
                recommendations.append("Low persistence - focus on more reliable patterns")
            if braid_scores['novelty'] < 0.6:
                recommendations.append("Low novelty - seek more diverse approaches")
            if braid_scores['surprise'] < 0.6:
                recommendations.append("Low surprise - look for more unexpected insights")
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
            return ["Error generating recommendations"]
    
    async def _save_braid(self, braid_data: Dict[str, Any]) -> Optional[str]:
        """Save braid to database"""
        try:
            result = self.supabase_manager.supabase.table('AD_strands').insert(braid_data).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]['id']
            else:
                self.logger.error("Failed to save braid to database")
                return None
                
        except Exception as e:
            self.logger.error(f"Error saving braid to database: {e}")
            return None
    
    async def promote_braid(self, braid_id: str, target_level: int) -> bool:
        """
        Promote a braid to a higher level
        
        Args:
            braid_id: ID of the braid to promote
            target_level: Target level for promotion
            
        Returns:
            True if promotion succeeded, False otherwise
        """
        try:
            # Get current braid data
            result = self.supabase_manager.supabase.table('AD_strands').select('*').eq('id', braid_id).execute()
            
            if not result.data or len(result.data) == 0:
                self.logger.error(f"Braid {braid_id} not found")
                return False
            
            braid_data = result.data[0]
            current_level = braid_data.get('braid_level', 1)
            
            if target_level <= current_level:
                self.logger.warning(f"Cannot promote braid {braid_id} from level {current_level} to {target_level}")
                return False
            
            # Update braid level
            update_data = {
                'braid_level': target_level,
                'promoted_at': datetime.now(timezone.utc).isoformat()
            }
            
            update_result = self.supabase_manager.supabase.table('AD_strands').update(update_data).eq('id', braid_id).execute()
            
            if update_result.data:
                self.logger.info(f"Promoted braid {braid_id} to level {target_level}")
                return True
            else:
                self.logger.error(f"Failed to promote braid {braid_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error promoting braid {braid_id}: {e}")
            return False
    
    async def get_braid_statistics(self, strand_type: str = None) -> Dict[str, Any]:
        """Get statistics about braids"""
        try:
            query = self.supabase_manager.supabase.table('AD_strands').select('*').like('kind', '%_braid')
            
            if strand_type:
                query = query.like('kind', f'{strand_type}_braid')
            
            result = query.execute()
            braids = result.data if result.data else []
            
            # Calculate statistics
            level_counts = {}
            total_braids = len(braids)
            avg_resonance = 0
            avg_quality = 0
            
            if braids:
                for braid in braids:
                    level = braid.get('braid_level', 1)
                    level_counts[level] = level_counts.get(level, 0) + 1
                
                avg_resonance = sum(b.get('resonance_score', 0) for b in braids) / len(braids)
                avg_quality = sum(b.get('quality_score', 0) for b in braids) / len(braids)
            
            stats = {
                'total_braids': total_braids,
                'level_distribution': level_counts,
                'average_resonance': avg_resonance,
                'average_quality': avg_quality,
                'strand_type': strand_type or 'all'
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting braid statistics: {e}")
            return {'total_braids': 0, 'level_distribution': {}, 'average_resonance': 0, 'average_quality': 0, 'strand_type': strand_type or 'all'}
