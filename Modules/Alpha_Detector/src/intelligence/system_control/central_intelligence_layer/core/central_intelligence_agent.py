"""
Central Intelligence Agent - CIL Team Coordinator

Coordinates all CIL team members and manages strategic intelligence operations.
This is the main coordinator for the Central Intelligence Layer team.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import json

from src.llm_integration.openrouter_client import OpenRouterClient
from src.utils.supabase_manager import SupabaseManager
from .strategic_pattern_miner import StrategicPatternMiner

logger = logging.getLogger(__name__)


class CentralIntelligenceAgent:
    """
    Central Intelligence Agent - Coordinates all CIL team members
    
    This is the main coordinator for the Central Intelligence Layer team.
    It manages the strategic intelligence operations and coordinates between team members.
    """
    
    def __init__(self, db_manager: SupabaseManager, llm_client: OpenRouterClient):
        """
        Initialize the Central Intelligence Agent
        
        Args:
            db_manager: Database manager for system access
            llm_client: LLM client for strategic analysis
        """
        self.db_manager = db_manager
        self.llm_client = llm_client
        
        # CIL team identification
        self.team_id = "central_intelligence_layer"
        self.agent_id = "central_intelligence_agent"
        
        # Initialize CIL team members
        self.team_members = {
            "strategic_pattern_miner": StrategicPatternMiner(db_manager, llm_client),
            # TODO: Add other team members as they are implemented
            # "experiment_orchestrator": ExperimentOrchestrator(db_manager, llm_client),
            # "doctrine_keeper": DoctrineKeeper(db_manager, llm_client),
            # "plan_composer": PlanComposer(db_manager, llm_client),
            # "system_resonance_manager": SystemResonanceManager(db_manager, llm_client)
        }
        
        logger.info(f"CentralIntelligenceAgent initialized with {len(self.team_members)} team members")
    
    async def start_cil_team(self) -> Dict[str, Any]:
        """
        Start all CIL team members and begin strategic intelligence operations
        
        Returns:
            Dict containing startup results
        """
        try:
            logger.info("Starting CIL team operations")
            
            startup_results = {}
            
            # Start each team member
            for member_name, member in self.team_members.items():
                try:
                    logger.info(f"Starting CIL team member: {member_name}")
                    
                    # Each team member can have its own startup logic
                    if hasattr(member, 'start'):
                        result = await member.start()
                        startup_results[member_name] = result
                    else:
                        startup_results[member_name] = {"status": "started", "message": "No startup method"}
                    
                    logger.info(f"CIL team member {member_name} started successfully")
                    
                except Exception as e:
                    logger.error(f"Error starting CIL team member {member_name}: {e}")
                    startup_results[member_name] = {"status": "error", "error": str(e)}
            
            # Create initial strategic strand to announce CIL team startup
            await self._create_startup_strand(startup_results)
            
            logger.info("CIL team startup completed")
            
            return {
                "success": True,
                "team_id": self.team_id,
                "agent_id": self.agent_id,
                "team_members": list(self.team_members.keys()),
                "startup_results": startup_results
            }
            
        except Exception as e:
            logger.error(f"Error starting CIL team: {e}")
            return {"success": False, "error": str(e)}
    
    async def coordinate_strategic_analysis(self, analysis_type: str = "comprehensive") -> Dict[str, Any]:
        """
        Coordinate strategic analysis across all CIL team members
        
        Args:
            analysis_type: Type of analysis to coordinate (comprehensive, confluence, patterns)
            
        Returns:
            Dict containing coordinated analysis results
        """
        try:
            logger.info(f"Coordinating strategic analysis: {analysis_type}")
            
            coordination_results = {}
            
            # Coordinate based on analysis type
            if analysis_type == "comprehensive":
                coordination_results = await self._coordinate_comprehensive_analysis()
            elif analysis_type == "confluence":
                coordination_results = await self._coordinate_confluence_analysis()
            elif analysis_type == "patterns":
                coordination_results = await self._coordinate_pattern_analysis()
            else:
                return {"error": f"Unknown analysis type: {analysis_type}"}
            
            # Create coordination summary strand
            await self._create_coordination_strand(analysis_type, coordination_results)
            
            logger.info(f"Strategic analysis coordination completed: {analysis_type}")
            
            return {
                "success": True,
                "analysis_type": analysis_type,
                "coordination_results": coordination_results,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error coordinating strategic analysis: {e}")
            return {"success": False, "error": str(e)}
    
    async def generate_strategic_meta_signals(self) -> Dict[str, Any]:
        """
        Generate strategic meta-signals from CIL team analysis
        
        Returns:
            Dict containing generated meta-signals
        """
        try:
            logger.info("Generating strategic meta-signals")
            
            meta_signals = []
            
            # Get strategic patterns from pattern miner
            if "strategic_pattern_miner" in self.team_members:
                pattern_miner = self.team_members["strategic_pattern_miner"]
                
                # Analyze cross-team patterns
                pattern_analysis = await pattern_miner.analyze_cross_team_patterns()
                
                if pattern_analysis.get("strategic_strands"):
                    meta_signals.extend(pattern_analysis["strategic_strands"])
                
                # Detect strategic confluence
                confluence_analysis = await pattern_miner.detect_strategic_confluence()
                
                if confluence_analysis.get("meta_signals"):
                    meta_signals.extend(confluence_analysis["meta_signals"])
            
            # TODO: Add meta-signal generation from other team members
            # - Experiment Orchestrator: strategic experiments
            # - Doctrine Keeper: strategic learning
            # - Plan Composer: strategic plans
            # - System Resonance Manager: resonance-based signals
            
            logger.info(f"Generated {len(meta_signals)} strategic meta-signals")
            
            return {
                "success": True,
                "meta_signals": meta_signals,
                "count": len(meta_signals),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating strategic meta-signals: {e}")
            return {"success": False, "error": str(e)}
    
    async def _coordinate_comprehensive_analysis(self) -> Dict[str, Any]:
        """Coordinate comprehensive strategic analysis across all team members"""
        try:
            results = {}
            
            # Strategic Pattern Miner analysis
            if "strategic_pattern_miner" in self.team_members:
                pattern_miner = self.team_members["strategic_pattern_miner"]
                
                # Cross-team pattern analysis
                pattern_analysis = await pattern_miner.analyze_cross_team_patterns()
                results["pattern_analysis"] = pattern_analysis
                
                # Confluence detection
                confluence_analysis = await pattern_miner.detect_strategic_confluence()
                results["confluence_analysis"] = confluence_analysis
            
            # TODO: Add coordination for other team members
            # - Experiment Orchestrator: experiment design and assignment
            # - Doctrine Keeper: knowledge curation and doctrine updates
            # - Plan Composer: strategic plan composition
            # - System Resonance Manager: resonance analysis and scoring
            
            return results
            
        except Exception as e:
            logger.error(f"Error in comprehensive analysis coordination: {e}")
            return {"error": str(e)}
    
    async def _coordinate_confluence_analysis(self) -> Dict[str, Any]:
        """Coordinate confluence analysis across teams"""
        try:
            results = {}
            
            # Focus on confluence detection
            if "strategic_pattern_miner" in self.team_members:
                pattern_miner = self.team_members["strategic_pattern_miner"]
                
                confluence_analysis = await pattern_miner.detect_strategic_confluence()
                results["confluence_analysis"] = confluence_analysis
            
            return results
            
        except Exception as e:
            logger.error(f"Error in confluence analysis coordination: {e}")
            return {"error": str(e)}
    
    async def _coordinate_pattern_analysis(self) -> Dict[str, Any]:
        """Coordinate pattern analysis across teams"""
        try:
            results = {}
            
            # Focus on pattern analysis
            if "strategic_pattern_miner" in self.team_members:
                pattern_miner = self.team_members["strategic_pattern_miner"]
                
                pattern_analysis = await pattern_miner.analyze_cross_team_patterns()
                results["pattern_analysis"] = pattern_analysis
            
            return results
            
        except Exception as e:
            logger.error(f"Error in pattern analysis coordination: {e}")
            return {"error": str(e)}
    
    async def _create_startup_strand(self, startup_results: Dict[str, Any]) -> None:
        """Create a strand to announce CIL team startup"""
        try:
            startup_strand = {
                "kind": "cil_team_startup",
                "module": "alpha",
                "symbol": "SYSTEM",
                "timeframe": "system",
                "session_bucket": "system",
                "regime": "system",
                "tags": [
                    f"agent:central_intelligence:central_intelligence_agent:team_startup",
                    f"cil_team:{self.team_id}",
                    f"cil_agent:{self.agent_id}"
                ],
                "content": f"CIL team started with {len(self.team_members)} members: {', '.join(self.team_members.keys())}",
                "sig_sigma": 1.0,  # High confidence in startup
                "sig_confidence": 1.0,
                "outcome_score": 0.0,
                "strategic_meta_type": "team_startup",
                "cil_team_member": self.agent_id,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            result = await self.db_manager.insert_strand(startup_strand)
            
            if result.get("success"):
                logger.info(f"CIL team startup strand created: {result.get('strand_id')}")
            else:
                logger.error(f"Failed to create CIL team startup strand: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Error creating startup strand: {e}")
    
    async def _create_coordination_strand(self, analysis_type: str, coordination_results: Dict[str, Any]) -> None:
        """Create a strand to record coordination results"""
        try:
            # Count successful analyses
            successful_analyses = 0
            total_analyses = 0
            
            for result_type, result_data in coordination_results.items():
                total_analyses += 1
                if not result_data.get("error"):
                    successful_analyses += 1
            
            coordination_strand = {
                "kind": "cil_coordination",
                "module": "alpha",
                "symbol": "SYSTEM",
                "timeframe": "system",
                "session_bucket": "system",
                "regime": "system",
                "tags": [
                    f"agent:central_intelligence:central_intelligence_agent:coordination",
                    f"cil_team:{self.team_id}",
                    f"cil_agent:{self.agent_id}",
                    f"analysis_type:{analysis_type}"
                ],
                "content": f"CIL coordination completed: {analysis_type} analysis with {successful_analyses}/{total_analyses} successful",
                "sig_sigma": successful_analyses / max(total_analyses, 1),
                "sig_confidence": successful_analyses / max(total_analyses, 1),
                "outcome_score": 0.0,
                "strategic_meta_type": "coordination",
                "cil_team_member": self.agent_id,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            result = await self.db_manager.insert_strand(coordination_strand)
            
            if result.get("success"):
                logger.info(f"CIL coordination strand created: {result.get('strand_id')}")
            else:
                logger.error(f"Failed to create CIL coordination strand: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Error creating coordination strand: {e}")
    
    def get_team_status(self) -> Dict[str, Any]:
        """
        Get the current status of all CIL team members
        
        Returns:
            Dict containing team member statuses
        """
        try:
            status = {
                "team_id": self.team_id,
                "agent_id": self.agent_id,
                "team_members": {},
                "total_members": len(self.team_members),
                "active_members": 0
            }
            
            for member_name, member in self.team_members.items():
                member_status = {
                    "name": member_name,
                    "class": member.__class__.__name__,
                    "status": "active" if member else "inactive"
                }
                
                # Add member-specific status if available
                if hasattr(member, 'get_status'):
                    member_status.update(member.get_status())
                
                status["team_members"][member_name] = member_status
                
                if member_status["status"] == "active":
                    status["active_members"] += 1
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting team status: {e}")
            return {"error": str(e)}
