"""
Braid Level Manager - Phase 4

Manages braid level progression system where 3+ strands of level N create braids of level N+1.
Braid levels have no cap and provide unlimited compression and learning depth.
"""

import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


class BraidLevelManager:
    """
    Manages braid level progression system
    
    Braid Level Progression:
    - Level 1: 3+ prediction_review strands → create braid_level=1
    - Level 2: 3+ braid_level=1 strands → create braid_level=2
    - Level 3: 3+ braid_level=2 strands → create braid_level=3
    - Level 4+: 3+ braid_level=N strands → create braid_level=N+1 (no cap)
    
    Each braid remembers its original cluster for proper clustering.
    """
    
    def __init__(self, supabase_manager):
        self.supabase_manager = supabase_manager
        self.logger = logging.getLogger(f"{__name__}.braid_level_manager")
        
        # Braid creation thresholds
        self.braid_threshold = 3  # 3+ strands needed for next level
        self.max_braid_level = None  # No cap on braid levels
    
    async def process_braid_creation(self, cluster_type: str, cluster_key: str) -> List[str]:
        """
        Process braid creation for a specific cluster
        
        Args:
            cluster_type: Type of cluster (pattern_timeframe, asset, etc.)
            cluster_key: Specific cluster key (BTC, success, etc.)
            
        Returns:
            List of newly created braid IDs
        """
        try:
            self.logger.info(f"Processing braid creation for {cluster_type}:{cluster_key}")
            
            # Get all strands in this cluster
            cluster_strands = await self.get_cluster_strands(cluster_type, cluster_key)
            
            if len(cluster_strands) < self.braid_threshold:
                self.logger.info(f"Not enough strands for braid creation: {len(cluster_strands)} < {self.braid_threshold}")
                return []
            
            # Group by braid level
            level_groups = self.group_by_braid_level(cluster_strands)
            
            # Process each level for braid creation
            created_braids = []
            for level, strands in level_groups.items():
                if len(strands) >= self.braid_threshold:
                    braid_id = await self.create_next_level_braid(
                        level, strands, cluster_type, cluster_key
                    )
                    if braid_id:
                        created_braids.append(braid_id)
            
            self.logger.info(f"Created {len(created_braids)} braids for {cluster_type}:{cluster_key}")
            return created_braids
            
        except Exception as e:
            self.logger.error(f"Error processing braid creation for {cluster_type}:{cluster_key}: {e}")
            return []
    
    async def get_cluster_strands(self, cluster_type: str, cluster_key: str) -> List[Dict[str, Any]]:
        """Get all strands in a specific cluster using Direct Supabase Client"""
        
        try:
            # Use Direct Supabase Client instead of RPC
            if cluster_type == 'pattern_timeframe':
                # Split cluster_key into asset and group_signature
                parts = cluster_key.split('_', 1)
                if len(parts) == 2:
                    asset, group_signature = parts
                    result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction_review').eq('content->>asset', asset).eq('content->>group_signature', group_signature).execute()
                else:
                    result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction_review').eq('content->>group_signature', cluster_key).execute()
            elif cluster_type == 'asset':
                result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction_review').eq('content->>asset', cluster_key).execute()
            elif cluster_type == 'timeframe':
                result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction_review').eq('content->>timeframe', cluster_key).execute()
            elif cluster_type == 'outcome':
                success_value = cluster_key == 'success'
                result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction_review').eq('content->>success', success_value).execute()
            elif cluster_type == 'pattern':
                result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction_review').eq('content->>group_type', cluster_key).execute()
            elif cluster_type == 'group_type':
                result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction_review').eq('content->>group_type', cluster_key).execute()
            elif cluster_type == 'method':
                result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction_review').eq('content->>method', cluster_key).execute()
            else:
                self.logger.error(f"Unknown cluster type: {cluster_type}")
                return []
            
            return result.data if result.data else []
            
        except Exception as e:
            self.logger.error(f"Error getting cluster strands for {cluster_type}:{cluster_key}: {e}")
            return []
    
    
    def group_by_braid_level(self, strands: List[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
        """Group strands by their braid level"""
        
        level_groups = {}
        
        for strand in strands:
            # Get braid level from strand
            braid_level = self.get_strand_braid_level(strand)
            
            if braid_level not in level_groups:
                level_groups[braid_level] = []
            level_groups[braid_level].append(strand)
        
        return level_groups
    
    def get_strand_braid_level(self, strand: Dict[str, Any]) -> int:
        """Get braid level from strand"""
        
        # Get braid level from the strand's braid_level field
        return strand.get('braid_level', 1)  # Default to level 1
    
    async def create_next_level_braid(self, current_level: int, strands: List[Dict[str, Any]], 
                                    cluster_type: str, cluster_key: str) -> Optional[str]:
        """
        Create braid at next level from 3+ strands of current level
        
        Args:
            current_level: Current braid level of the strands
            strands: List of strands to combine into braid
            cluster_type: Type of cluster
            cluster_key: Specific cluster key
            
        Returns:
            ID of created braid, or None if creation failed
        """
        try:
            next_level = current_level + 1
            
            # Check if we should cap braid levels (if max_braid_level is set)
            if self.max_braid_level and next_level > self.max_braid_level:
                self.logger.info(f"Braid level {next_level} exceeds max level {self.max_braid_level}")
                return None
            
            # Create new prediction_review strand with higher braid level
            braid_strand = {
                'id': f"pred_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}",
                'kind': 'prediction_review',  # Keep same kind!
                'created_at': datetime.now(timezone.utc).isoformat(),
                'tags': ['cil', 'braid', f'level_{next_level}', f'cluster_{cluster_type}'],
                'braid_level': next_level,
                'content': {
                    'cluster_type': cluster_type,
                    'cluster_key': cluster_key,
                    'source_strands': [s['id'] for s in strands],
                    'source_level': current_level,
                    'strand_count': len(strands),
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'braid_level': next_level
                },
                'module_intelligence': {
                    'cluster_type': cluster_type,
                    'cluster_key': cluster_key,
                    'braid_level': next_level,
                    'source_count': len(strands),
                    'source_level': current_level
                }
            }
            
            # Store braid strand in database
            braid_id = await self.store_braid_strand(braid_strand)
            
            if braid_id:
                # Update source strands to reference this braid
                await self.update_source_strands(strands, braid_id)
                
                self.logger.info(f"Created braid level {next_level} with {len(strands)} source strands")
            
            return braid_id
            
        except Exception as e:
            self.logger.error(f"Error creating braid level {next_level}: {e}")
            return None
    
    async def store_braid_strand(self, braid_strand: Dict[str, Any]) -> Optional[str]:
        """Store braid strand in database using proper Supabase client method"""
        
        try:
            # Prepare strand data for Supabase client
            strand_data = {
                'id': braid_strand['id'],
                'module': 'alpha',
                'kind': braid_strand['kind'],
                'symbol': braid_strand['content'].get('cluster_key', 'UNKNOWN'),
                'timeframe': '1h',  # Default timeframe
                'tags': braid_strand['tags'],
                'created_at': braid_strand['created_at'],
                'updated_at': braid_strand['created_at'],
                'braid_level': braid_strand['braid_level'],
                'lesson': '',  # No lesson for general braids
                'content': braid_strand['content'],
                'module_intelligence': braid_strand['module_intelligence'],
                'cluster_key': []  # Will be set by the calling system
            }
            
            # Use proper Supabase client method instead of raw SQL
            result = self.supabase_manager.insert_strand(strand_data)
            
            if result:
                self.logger.info(f"Stored braid strand: {braid_strand['id']}")
                return braid_strand['id']
            else:
                self.logger.error(f"Failed to store braid strand: {braid_strand['id']}")
                return None
            
        except Exception as e:
            self.logger.error(f"Error storing braid strand: {e}")
            return None
    
    async def update_source_strands(self, source_strands: List[Dict[str, Any]], braid_id: str) -> bool:
        """Update source strands to reference the created braid"""
        
        try:
            for strand in source_strands:
                # Add braid reference to strand content
                content = strand.get('content', {})
                if 'braid_references' not in content:
                    content['braid_references'] = []
                content['braid_references'].append(braid_id)
                
                # Update strand in database using Direct Supabase Client
                self.supabase_manager.client.table('ad_strands').update({
                    'content': content
                }).eq('id', strand['id']).execute()
            
            self.logger.info(f"Updated {len(source_strands)} source strands with braid reference")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating source strands: {e}")
            return False
    
    async def get_braids_in_cluster(self, cluster_type: str, cluster_key: str, 
                                  braid_level: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get braids in a specific cluster, optionally filtered by braid level"""
        
        try:
            # Use Direct Supabase Client instead of RPC
            if braid_level is not None:
                result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'braid').eq('content->>cluster_type', cluster_type).eq('content->>cluster_key', cluster_key).eq('content->>braid_level', str(braid_level)).order('created_at', desc=True).execute()
            else:
                result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'braid').eq('content->>cluster_type', cluster_type).eq('content->>cluster_key', cluster_key).order('content->>braid_level', desc=False).order('created_at', desc=True).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            self.logger.error(f"Error getting braids in cluster {cluster_type}:{cluster_key}: {e}")
            return []
    
    async def get_braid_statistics(self) -> Dict[str, Any]:
        """Get statistics about braid levels and distribution"""
        
        try:
            # Get all braids using Direct Supabase Client
            result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'braid').execute()
            
            if not result.data:
                return {
                    'total_braids': 0,
                    'max_braid_level': 0,
                    'level_distribution': {},
                    'cluster_distribution': {}
                }
            
            stats = {
                'total_braids': len(result.data),
                'max_braid_level': 0,
                'level_distribution': {},
                'cluster_distribution': {}
            }
            
            # Process braids to calculate statistics
            for braid in result.data:
                content = braid.get('content', {})
                braid_level = int(content.get('braid_level', 0))
                cluster_type = content.get('cluster_type', 'unknown')
                
                stats['max_braid_level'] = max(stats['max_braid_level'], braid_level)
                
                if braid_level not in stats['level_distribution']:
                    stats['level_distribution'][braid_level] = 0
                stats['level_distribution'][braid_level] += 1
                
                if cluster_type not in stats['cluster_distribution']:
                    stats['cluster_distribution'][cluster_type] = 0
                stats['cluster_distribution'][cluster_type] += 1
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting braid statistics: {e}")
            return {'total_braids': 0, 'max_braid_level': 0, 'level_distribution': {}, 'cluster_distribution': {}}
    
    async def process_all_clusters(self, cluster_groups: Dict[str, Dict[str, List[Dict[str, Any]]]]) -> Dict[str, List[str]]:
        """Process braid creation for all cluster groups"""
        
        all_created_braids = {}
        
        for cluster_type, clusters in cluster_groups.items():
            cluster_braids = []
            
            for cluster_key, strands in clusters.items():
                if len(strands) >= self.braid_threshold:
                    created_braids = await self.process_braid_creation(cluster_type, cluster_key)
                    cluster_braids.extend(created_braids)
            
            all_created_braids[cluster_type] = cluster_braids
        
        return all_created_braids
