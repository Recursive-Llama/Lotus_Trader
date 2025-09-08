"""
Direct Table Communicator
Phase 1.5.1: Direct table-to-table communication with Decision Maker
"""

import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from decimal import Decimal

from src.utils.supabase_manager import SupabaseManager
from trading_plans.models import TradingPlan, SignalPack

logger = logging.getLogger(__name__)


class DirectTableCommunicator:
    """
    Handles direct table-to-table communication with Decision Maker
    Uses AD_strands table with tags to trigger PostgreSQL notifications
    """
    
    def __init__(self, db_manager: Optional[SupabaseManager] = None):
        self.db_manager = db_manager or SupabaseManager()
        self.module_type = 'alpha'
        
        # Communication tags for different message types
        self.communication_tags = {
            'trading_plan': ['dm:evaluate_plan'],
            'signal_update': ['dm:signal_update'],
            'intelligence': ['dm:intelligence_update'],
            'feedback_request': ['dm:feedback_request']
        }
    
    def publish_trading_plan(self, trading_plan: TradingPlan, signal_pack: SignalPack) -> Optional[str]:
        """
        Publish trading plan to AD_strands table with communication tags
        
        Args:
            trading_plan: TradingPlan object to publish
            signal_pack: SignalPack object to publish
            
        Returns:
            str: Strand ID if successful, None if failed
        """
        try:
            # Generate unique strand ID
            strand_id = f"AD_{uuid.uuid4().hex[:12]}"
            
            # Prepare strand data for AD_strands table
            strand_data = {
                'id': strand_id,
                'module': 'alpha',
                'kind': 'trading_plan',
                'symbol': trading_plan.symbol,
                'timeframe': trading_plan.timeframe,
                'session_bucket': self._generate_session_bucket(),
                'regime': trading_plan.market_context.get('regime', 'unknown'),
                'sig_sigma': float(trading_plan.strength_score),
                'sig_confidence': float(trading_plan.confidence_score),
                'sig_direction': trading_plan.direction,
                'trading_plan': self._serialize_trading_plan(trading_plan),
                'signal_pack': self._serialize_signal_pack(signal_pack),
                'dsi_evidence': {},  # Phase 2+ feature
                'regime_context': trading_plan.market_context,
                'event_context': {},  # Phase 2+ feature
                'module_intelligence': {},  # Phase 3+ feature
                'curator_feedback': {},  # Phase 3+ feature
                'tags': self.communication_tags['trading_plan'],
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Insert into AD_strands table
            result = self.db_manager.insert('AD_strands', strand_data)
            
            if result:
                logger.info(f"Trading plan published: {strand_id} - {trading_plan.symbol} {trading_plan.direction}")
                logger.debug(f"Published to Decision Maker with tags: {self.communication_tags['trading_plan']}")
                return strand_id
            else:
                logger.error(f"Failed to publish trading plan: {strand_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error publishing trading plan: {e}")
            return None
    
    def publish_signal_update(self, signal: Dict[str, Any], update_type: str = 'signal_update') -> Optional[str]:
        """
        Publish signal update to AD_strands table
        
        Args:
            signal: Signal data to publish
            update_type: Type of signal update
            
        Returns:
            str: Strand ID if successful, None if failed
        """
        try:
            strand_id = f"AD_{uuid.uuid4().hex[:12]}"
            
            strand_data = {
                'id': strand_id,
                'module': 'alpha',
                'kind': 'signal',
                'symbol': signal.get('symbol', 'UNKNOWN'),
                'timeframe': signal.get('timeframe', '1m'),
                'session_bucket': self._generate_session_bucket(),
                'regime': signal.get('regime', 'unknown'),
                'sig_sigma': signal.get('strength', 0.0),
                'sig_confidence': signal.get('confidence', 0.0),
                'sig_direction': signal.get('direction', 'neutral'),
                'trading_plan': {},
                'signal_pack': {},
                'dsi_evidence': {},
                'regime_context': signal.get('regime_context', {}),
                'event_context': {},
                'module_intelligence': {},
                'curator_feedback': {},
                'tags': self.communication_tags.get(update_type, ['dm:signal_update']),
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            result = self.db_manager.insert('AD_strands', strand_data)
            
            if result:
                logger.info(f"Signal update published: {strand_id} - {signal.get('symbol', 'UNKNOWN')}")
                return strand_id
            else:
                logger.error(f"Failed to publish signal update: {strand_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error publishing signal update: {e}")
            return None
    
    def publish_multiple_trading_plans(self, trading_plans: List[TradingPlan], signal_packs: List[SignalPack]) -> List[str]:
        """
        Publish multiple trading plans in batch
        
        Args:
            trading_plans: List of TradingPlan objects
            signal_packs: List of SignalPack objects
            
        Returns:
            List[str]: List of successful strand IDs
        """
        successful_ids = []
        
        for trading_plan, signal_pack in zip(trading_plans, signal_packs):
            strand_id = self.publish_trading_plan(trading_plan, signal_pack)
            if strand_id:
                successful_ids.append(strand_id)
        
        logger.info(f"Published {len(successful_ids)}/{len(trading_plans)} trading plans")
        return successful_ids
    
    def _serialize_trading_plan(self, trading_plan: TradingPlan) -> Dict[str, Any]:
        """Serialize TradingPlan object for database storage"""
        try:
            # Convert Decimal to float for JSON serialization
            def convert_decimals(obj):
                if isinstance(obj, Decimal):
                    return float(obj)
                elif isinstance(obj, dict):
                    return {k: convert_decimals(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_decimals(item) for item in obj]
                else:
                    return obj
            
            plan_dict = trading_plan.to_dict()
            return convert_decimals(plan_dict)
            
        except Exception as e:
            logger.error(f"Error serializing trading plan: {e}")
            return {}
    
    def _serialize_signal_pack(self, signal_pack: SignalPack) -> Dict[str, Any]:
        """Serialize SignalPack object for database storage"""
        try:
            # Convert Decimal to float for JSON serialization
            def convert_decimals(obj):
                if isinstance(obj, Decimal):
                    return float(obj)
                elif isinstance(obj, dict):
                    return {k: convert_decimals(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_decimals(item) for item in obj]
                else:
                    return obj
            
            pack_dict = signal_pack.to_dict()
            return convert_decimals(pack_dict)
            
        except Exception as e:
            logger.error(f"Error serializing signal pack: {e}")
            return {}
    
    def _generate_session_bucket(self) -> str:
        """Generate session bucket identifier"""
        now = datetime.now(timezone.utc)
        return f"session_{now.strftime('%Y%m%d_%H')}"
    
    def get_communication_status(self) -> Dict[str, Any]:
        """Get communication status and statistics"""
        try:
            # Get recent strands count
            recent_strands = self.db_manager.query(
                "AD_strands",
                select="id, kind, created_at, tags",
                order="created_at.desc",
                limit=10
            )
            
            return {
                'module_type': self.module_type,
                'recent_strands_count': len(recent_strands) if recent_strands else 0,
                'communication_tags': self.communication_tags,
                'database_connected': self.db_manager.is_connected(),
                'last_check': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting communication status: {e}")
            return {
                'module_type': self.module_type,
                'error': str(e),
                'database_connected': False
            }
