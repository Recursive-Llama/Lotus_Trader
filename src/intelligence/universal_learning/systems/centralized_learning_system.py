"""
Centralized Learning System

Main entry point for the centralized learning system. Provides a unified interface
for processing any strand type through the complete learning workflow.
"""

import asyncio
from typing import Dict, Any, List, Optional
from ..pipeline.strand_processor import StrandProcessor, StrandType
from ..pipeline.learning_pipeline import LearningPipeline
from ..engines.mathematical_resonance_engine import MathematicalResonanceEngine
from ..module_specific_scoring import ModuleSpecificScoring
from ..engines.context_injection_engine import ContextInjectionEngine
from ..engines.module_triggering_engine import ModuleTriggeringEngine


class CentralizedLearningSystem:
    """
    Centralized learning system that processes any strand type
    
    This is the main entry point for all learning functionality. It provides
    a unified interface for processing strands through the complete learning
    workflow, regardless of strand type.
    """
    
    def __init__(
        self,
        supabase_manager,
        llm_client,
        prompt_manager
    ):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.prompt_manager = prompt_manager
        
        # Initialize components
        self.strand_processor = StrandProcessor()
        self.learning_pipeline = LearningPipeline(
            supabase_manager, llm_client, prompt_manager
        )
        self.resonance_engine = MathematicalResonanceEngine()
        self.module_scoring = ModuleSpecificScoring()
        self.context_engine = ContextInjectionEngine(supabase_manager)
        self.triggering_engine = ModuleTriggeringEngine(supabase_manager, self)
    
    async def process_strand(self, strand: Dict[str, Any]) -> bool:
        """
        Process a single strand through the learning system
        
        Args:
            strand: Strand data from database
            
        Returns:
            True if processing succeeded, False otherwise
        """
        try:
            # Calculate module-specific scores first
            await self._calculate_module_scores(strand)
            
            # Process through learning pipeline
            return await self.learning_pipeline.process_strand(strand)
            
        except Exception as e:
            print(f"Error processing strand: {e}")
            return False
    
    async def process_strand_by_id(self, strand_id: str) -> bool:
        """
        Process a strand by its ID
        
        Args:
            strand_id: The ID of the strand to process
            
        Returns:
            True if processing succeeded, False otherwise
        """
        try:
            # Get strand from database
            result = await self.supabase_manager.client.table('AD_strands').select(
                '*'
            ).eq('id', strand_id).execute()
            
            if not result.data:
                print(f"Strand not found: {strand_id}")
                return False
            
            strand = result.data[0]
            return await self.process_strand(strand)
            
        except Exception as e:
            print(f"Error processing strand {strand_id}: {e}")
            return False
    
    async def process_learning_queue(self, limit: int = 10) -> Dict[str, int]:
        """
        DEPRECATED: Learning queue has been removed. Strands are now processed directly.
        This method is kept for backward compatibility but will always return empty results.
        
        Args:
            limit: Maximum number of strands to process (ignored)
            
        Returns:
            Dictionary with processing statistics (always empty)
        """
        return await self.learning_pipeline.process_learning_queue(limit)
    
    async def process_strands_by_type(
        self, 
        strand_type: str, 
        limit: int = 10
    ) -> Dict[str, int]:
        """
        Process strands of a specific type
        
        Args:
            strand_type: The type of strands to process
            limit: Maximum number of strands to process
            
        Returns:
            Dictionary with processing statistics
        """
        try:
            # Check if strand type is supported
            if not self.strand_processor.is_learning_supported(strand_type):
                print(f"Learning not supported for strand type: {strand_type}")
                return {'processed': 0, 'successful': 0, 'failed': 0}
            
            # Get strands of this type
            result = await self.supabase_manager.client.table('AD_strands').select(
                '*'
            ).eq('kind', strand_type).limit(limit).execute()
            
            if not result.data:
                print(f"No strands found for type: {strand_type}")
                return {'processed': 0, 'successful': 0, 'failed': 0}
            
            # Process each strand
            successful = 0
            failed = 0
            
            for strand in result.data:
                success = await self.process_strand(strand)
                if success:
                    successful += 1
                else:
                    failed += 1
            
            return {
                'processed': len(result.data),
                'successful': successful,
                'failed': failed
            }
            
        except Exception as e:
            print(f"Error processing {strand_type} strands: {e}")
            return {'processed': 0, 'successful': 0, 'failed': 0}
    
    async def get_learning_status(self) -> Dict[str, Any]:
        """
        Get current learning system status
        
        Returns:
            Dictionary with learning system status information
        """
        try:
            # Get queue status
            queue_result = await self.supabase_manager.client.table('learning_queue').select(
                'status'
            ).execute()
            
            queue_stats = {}
            for item in queue_result.data:
                status = item['status']
                queue_stats[status] = queue_stats.get(status, 0) + 1
            
            # Get supported strand types
            supported_types = self.strand_processor.get_supported_strand_types()
            
            # Get recent braid creation stats
            braid_result = await self.supabase_manager.client.table('AD_strands').select(
                'kind, braid_level'
            ).gte('braid_level', 2).execute()
            
            braid_stats = {}
            for item in braid_result.data:
                key = f"{item['kind']}_level_{item['braid_level']}"
                braid_stats[key] = braid_stats.get(key, 0) + 1
            
            return {
                'queue_status': queue_stats,
                'supported_strand_types': supported_types,
                'recent_braids': braid_stats,
                'system_status': 'operational'
            }
            
        except Exception as e:
            print(f"Error getting learning status: {e}")
            return {
                'queue_status': {},
                'supported_strand_types': [],
                'recent_braids': {},
                'system_status': 'error'
            }
    
    def get_supported_strand_types(self) -> List[str]:
        """
        Get list of supported strand types
        
        Returns:
            List of supported strand type strings
        """
        return self.strand_processor.get_supported_strand_types()
    
    def is_learning_supported(self, strand_type: str) -> bool:
        """
        Check if learning is supported for a strand type
        
        Args:
            strand_type: The strand type string
            
        Returns:
            True if supported, False otherwise
        """
        return self.strand_processor.is_learning_supported(strand_type)
    
    async def get_context_for_module(self, module_id: str, context_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get context for a specific module based on its subscriptions
        
        Args:
            module_id: Module identifier (rdi, cil, ctp, dm, td)
            context_data: Additional context data for filtering
            
        Returns:
            Context dictionary with relevant insights for the module
        """
        try:
            return await self.context_engine.get_context_for_module(module_id, context_data)
        except Exception as e:
            print(f"Error getting context for module {module_id}: {e}")
            return {}
    
    async def get_resonance_context(self, strand_type: str, 
                                   context_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get resonance-enhanced context for a module (legacy method)
        
        Uses Simons' resonance principles to provide intelligent context injection
        
        Args:
            strand_type: The strand type the module subscribes to
            context_data: Additional context data
            
        Returns:
            Resonance-enhanced context for the module
        """
        try:
            # Get basic context from learning pipeline
            basic_context = await self.learning_pipeline.get_context_for_strand_type(
                strand_type, context_data
            )
            
            # Enhance with resonance calculations
            resonance_context = await self._enhance_with_resonance(
                basic_context, strand_type
            )
            
            return resonance_context
            
        except Exception as e:
            print(f"Error getting resonance context: {e}")
            return {}
    
    async def _enhance_with_resonance(self, basic_context: Dict[str, Any], 
                                     strand_type: str) -> Dict[str, Any]:
        """
        Enhance basic context with resonance calculations
        
        Args:
            basic_context: Basic context from learning pipeline
            strand_type: The strand type
            
        Returns:
            Resonance-enhanced context
        """
        try:
            # Get current resonance state
            resonance_state = self.resonance_engine.get_resonance_state()
            
            # Calculate pattern quality (φ) if pattern data available
            if 'pattern_data' in basic_context:
                phi = self.resonance_engine.calculate_phi(
                    basic_context['pattern_data'], 
                    ['1m', '5m', '15m', '1h']
                )
                basic_context['phi'] = phi
            
            # Add global intelligence field (θ)
            basic_context['global_theta'] = resonance_state.theta
            
            # Add learning strength (ρ)
            basic_context['learning_strength'] = resonance_state.rho
            
            # Add resonance acceleration (ω)
            basic_context['resonance_acceleration'] = resonance_state.omega
            
            # Add selection score if pattern data available
            if 'pattern_data' in basic_context:
                selection_score = self.resonance_engine.calculate_selection_score(
                    basic_context['pattern_data']
                )
                basic_context['selection_score'] = {
                    'accuracy': selection_score.accuracy,
                    'precision': selection_score.precision,
                    'stability': selection_score.stability,
                    'orthogonality': selection_score.orthogonality,
                    'cost': selection_score.cost,
                    'total': selection_score.total_score
                }
            
            return basic_context
            
        except Exception as e:
            print(f"Error enhancing with resonance: {e}")
            return basic_context
    
    async def _calculate_module_scores(self, strand: Dict[str, Any]) -> None:
        """
        Calculate module-specific scores for a strand
        
        Args:
            strand: Strand data from database
        """
        try:
            # Determine module type from strand kind
            module_type = self._get_module_type_from_kind(strand.get('kind', ''))
            
            if not module_type:
                print(f"Unknown strand kind: {strand.get('kind', '')}")
                return
            
            # Calculate module-specific scores
            scores = self.module_scoring.calculate_module_scores(strand, module_type)
            
            # Calculate resonance scores
            resonance_scores = self.resonance_engine.calculate_module_resonance(strand, module_type)
            
            # Update strand with scores
            await self._update_strand_scores(strand['id'], scores, resonance_scores)
            
        except Exception as e:
            print(f"Error calculating module scores: {e}")
    
    def _get_module_type_from_kind(self, kind: str) -> str:
        """
        Get module type from strand kind
        
        Args:
            kind: Strand kind string
            
        Returns:
            Module type string or None if unknown
        """
        kind_to_module = {
            'pattern': 'rdi',
            'prediction_review': 'cil',
            'conditional_trading_plan': 'ctp',
            'trading_decision': 'dm',
            'execution_outcome': 'td'
        }
        
        return kind_to_module.get(kind)
    
    async def _update_strand_scores(self, strand_id: str, scores: Dict[str, Any], 
                                   resonance_scores: Dict[str, Any]) -> None:
        """
        Update strand with calculated scores
        
        Args:
            strand_id: Strand ID
            scores: Module-specific scores
            resonance_scores: Resonance scores
        """
        try:
            # Update strand with scores
            update_data = {
                'persistence_score': scores.get('persistence_score', 0.5),
                'novelty_score': scores.get('novelty_score', 0.5),
                'surprise_rating': scores.get('surprise_rating', 0.5),
                'resonance_scores': resonance_scores,
                'updated_at': 'now()'
            }
            
            await self.supabase_manager.client.table('AD_strands').update(
                update_data
            ).eq('id', strand_id).execute()
            
        except Exception as e:
            print(f"Error updating strand scores: {e}")
    
    async def start_continuous_learning(self, interval_seconds: int = 30):
        """
        Start continuous learning processing with module triggering
        
        Args:
            interval_seconds: Seconds between processing cycles
        """
        print(f"Starting continuous learning with {interval_seconds}s interval")
        
        # Start module triggering system
        triggering_started = await self.start_module_triggering()
        if triggering_started:
            print("✅ Module triggering system started")
        else:
            print("⚠️  Module triggering system failed to start")
        
        while True:
            try:
                # Process learning queue
                stats = await self.process_learning_queue(limit=20)
                
                if stats['processed'] > 0:
                    print(f"Processed {stats['processed']} strands: "
                          f"{stats['successful']} successful, {stats['failed']} failed")
                
                # Wait for next cycle
                await asyncio.sleep(interval_seconds)
                
            except KeyboardInterrupt:
                print("Stopping continuous learning")
                await self.stop_module_triggering()
                break
            except Exception as e:
                print(f"Error in continuous learning: {e}")
                await asyncio.sleep(interval_seconds)
    
    async def start_module_triggering(self) -> bool:
        """
        Start the module triggering system
        
        Returns:
            True if started successfully, False otherwise
        """
        try:
            return await self.triggering_engine.start()
        except Exception as e:
            print(f"Error starting module triggering: {e}")
            return False
    
    async def stop_module_triggering(self) -> bool:
        """
        Stop the module triggering system
        
        Returns:
            True if stopped successfully, False otherwise
        """
        try:
            return await self.triggering_engine.stop()
        except Exception as e:
            print(f"Error stopping module triggering: {e}")
            return False
    
    async def get_triggering_status(self) -> Dict[str, Any]:
        """
        Get module triggering status
        
        Returns:
            Dictionary with triggering status information
        """
        try:
            return await self.triggering_engine.get_triggering_status()
        except Exception as e:
            print(f"Error getting triggering status: {e}")
            return {'error': str(e)}
    
    async def force_trigger_module(self, module: str, strand_type: str = None) -> bool:
        """
        Force trigger a specific module (for testing)
        
        Args:
            module: Module to trigger (cil, ctp, dm, td)
            strand_type: Specific strand type to use for triggering
            
        Returns:
            True if triggered successfully, False otherwise
        """
        try:
            return await self.triggering_engine.force_trigger_module(module, strand_type)
        except Exception as e:
            print(f"Error force triggering module {module}: {e}")
            return False
