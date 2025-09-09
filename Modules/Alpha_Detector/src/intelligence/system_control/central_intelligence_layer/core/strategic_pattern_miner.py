"""
Strategic Pattern Miner - CIL Team Member

Analyzes patterns across all intelligence teams and creates strategic meta-signals.
This is one of the core CIL team members that works together to provide strategic intelligence.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import json

from src.llm_integration.prompt_manager import PromptManager
from src.llm_integration.openrouter_client import OpenRouterClient
from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.database_driven_context_system import DatabaseDrivenContextSystem

logger = logging.getLogger(__name__)


class StrategicPatternMiner:
    """
    Strategic Pattern Miner - Finds cross-team patterns and creates strategic meta-signals
    
    This CIL team member:
    1. Reads strands from all intelligence teams
    2. Finds patterns that span multiple teams
    3. Creates strategic meta-signals for interesting patterns
    4. Publishes strategic insights back to the system
    """
    
    def __init__(self, db_manager: SupabaseManager, llm_client: OpenRouterClient):
        """
        Initialize the Strategic Pattern Miner
        
        Args:
            db_manager: Database manager for accessing strands
            llm_client: LLM client for strategic analysis
        """
        self.db_manager = db_manager
        self.llm_client = llm_client
        self.prompt_manager = PromptManager()
        self.context_system = DatabaseDrivenContextSystem(db_manager)
        
        # CIL team member identification
        self.team_member_id = "strategic_pattern_miner"
        self.cil_team = "central_intelligence_layer"
        
        logger.info(f"StrategicPatternMiner initialized as CIL team member: {self.team_member_id}")
    
    async def analyze_cross_team_patterns(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """
        Analyze patterns across all intelligence teams
        
        Args:
            time_window_hours: How far back to look for patterns
            
        Returns:
            Dict containing cross-team pattern analysis
        """
        try:
            logger.info(f"Starting cross-team pattern analysis for last {time_window_hours} hours")
            
            # Get strands from all teams in the time window
            strands = await self._get_team_strands(time_window_hours)
            
            if not strands:
                logger.warning("No strands found for cross-team analysis")
                return {"error": "No strands found", "patterns": []}
            
            # Get context for the analysis
            context = self.context_system.get_relevant_context(
                current_analysis={"strands": strands, "analysis_type": "cross_team_patterns"},
                top_k=10,
                similarity_threshold=0.7
            )
            
            # Get the strategic pattern mining prompt
            prompt_template = self.prompt_manager.get_prompt("strategic_pattern_miner")
            
            # Format the prompt with context
            formatted_prompt = self._format_prompt(prompt_template, context)
            
            # Get LLM analysis
            response = await self.llm_client.complete(
                prompt=formatted_prompt,
                max_tokens=3000,
                temperature=0.3
            )
            
            # Parse the response
            analysis_result = self._parse_llm_response(response)
            
            # Create strategic strands from the analysis
            strategic_strands = await self._create_strategic_strands(analysis_result)
            
            logger.info(f"Cross-team pattern analysis completed: {len(strategic_strands)} strategic strands created")
            
            return {
                "analysis_result": analysis_result,
                "strategic_strands": strategic_strands,
                "strands_analyzed": len(strands),
                "time_window_hours": time_window_hours
            }
            
        except Exception as e:
            logger.error(f"Error in cross-team pattern analysis: {e}")
            return {"error": str(e)}
    
    async def detect_strategic_confluence(self, confluence_threshold: float = 0.7) -> Dict[str, Any]:
        """
        Detect when multiple teams find similar patterns (strategic confluence)
        
        Args:
            confluence_threshold: Minimum confluence strength to report
            
        Returns:
            Dict containing confluence detection results
        """
        try:
            logger.info(f"Detecting strategic confluence with threshold {confluence_threshold}")
            
            # Get recent strands from all teams
            strands = await self._get_team_strands(time_window_hours=6)  # Last 6 hours
            
            if not strands:
                return {"error": "No strands found", "confluence_events": []}
            
            # Group strands by time windows and similarity
            confluence_events = await self._find_confluence_events(strands, confluence_threshold)
            
            # Create strategic meta-signals for confluence events
            meta_signals = await self._create_confluence_meta_signals(confluence_events)
            
            logger.info(f"Strategic confluence detection completed: {len(confluence_events)} events found")
            
            return {
                "confluence_events": confluence_events,
                "meta_signals": meta_signals,
                "threshold_used": confluence_threshold,
                "strands_analyzed": len(strands)
            }
            
        except Exception as e:
            logger.error(f"Error in strategic confluence detection: {e}")
            return {"error": str(e)}
    
    async def create_strategic_meta_signal(self, pattern_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a strategic meta-signal for interesting patterns
        
        Args:
            pattern_data: Data about the pattern to create meta-signal for
            
        Returns:
            Dict containing the created meta-signal
        """
        try:
            logger.info(f"Creating strategic meta-signal for pattern: {pattern_data.get('pattern_name', 'unknown')}")
            
            # Determine meta-signal type based on pattern
            meta_signal_type = self._determine_meta_signal_type(pattern_data)
            
            # Create the meta-signal strand
            meta_signal_strand = {
                "kind": "strategic_meta_signal",
                "module": "alpha",
                "symbol": pattern_data.get("symbol", "MULTI"),
                "timeframe": pattern_data.get("timeframe", "multi"),
                "session_bucket": pattern_data.get("session_bucket", "multi"),
                "regime": pattern_data.get("regime", "multi"),
                "tags": [
                    f"agent:central_intelligence:strategic_pattern_miner:meta_signal_created",
                    f"meta_signal_type:{meta_signal_type}",
                    f"team_member:{self.team_member_id}"
                ],
                "content": pattern_data.get("description", ""),
                "sig_sigma": pattern_data.get("strength", 0.5),
                "sig_confidence": pattern_data.get("confidence", 0.5),
                "outcome_score": 0.0,  # Will be updated based on results
                "strategic_meta_type": meta_signal_type,
                "team_member": self.team_member_id,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Add pattern-specific data
            if "teams_involved" in pattern_data:
                meta_signal_strand["content"] += f" Teams involved: {', '.join(pattern_data['teams_involved'])}"
            
            if "strategic_implications" in pattern_data:
                meta_signal_strand["content"] += f" Strategic implications: {pattern_data['strategic_implications']}"
            
            # Insert the meta-signal strand
            result = await self.db_manager.insert_strand(meta_signal_strand)
            
            if result.get("success"):
                logger.info(f"Strategic meta-signal created successfully: {result.get('strand_id')}")
                return {
                    "success": True,
                    "meta_signal": meta_signal_strand,
                    "strand_id": result.get("strand_id")
                }
            else:
                logger.error(f"Failed to create strategic meta-signal: {result.get('error')}")
                return {"success": False, "error": result.get("error")}
                
        except Exception as e:
            logger.error(f"Error creating strategic meta-signal: {e}")
            return {"success": False, "error": str(e)}
    
    async def _get_team_strands(self, time_window_hours: int) -> List[Dict[str, Any]]:
        """Get strands from all intelligence teams in the time window"""
        try:
            # Calculate time threshold
            time_threshold = datetime.now(timezone.utc).timestamp() - (time_window_hours * 3600)
            
            # Query strands from all teams
            query = """
                SELECT * FROM AD_strands 
                WHERE created_at >= to_timestamp(%s)
                AND tags && ARRAY[
                    'agent:raw_data_intelligence:',
                    'agent:indicator_intelligence:',
                    'agent:pattern_intelligence:',
                    'agent:system_control:'
                ]
                ORDER BY created_at DESC
            """
            
            result = await self.db_manager.execute_query(query, [time_threshold])
            
            if result.get("success"):
                return result.get("data", [])
            else:
                logger.error(f"Error querying team strands: {result.get('error')}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting team strands: {e}")
            return []
    
    async def _find_confluence_events(self, strands: List[Dict[str, Any]], threshold: float) -> List[Dict[str, Any]]:
        """Find confluence events where multiple teams detect similar patterns"""
        try:
            confluence_events = []
            
            # Group strands by time windows (e.g., 15-minute windows)
            time_windows = {}
            for strand in strands:
                # Round to 15-minute windows
                timestamp = datetime.fromisoformat(strand["created_at"].replace("Z", "+00:00"))
                window_key = timestamp.replace(minute=(timestamp.minute // 15) * 15, second=0, microsecond=0)
                
                if window_key not in time_windows:
                    time_windows[window_key] = []
                time_windows[window_key].append(strand)
            
            # Analyze each time window for confluence
            for window_time, window_strands in time_windows.items():
                if len(window_strands) < 2:  # Need at least 2 strands for confluence
                    continue
                
                # Group by team
                teams = {}
                for strand in window_strands:
                    # Extract team from tags
                    team = self._extract_team_from_tags(strand.get("tags", []))
                    if team:
                        if team not in teams:
                            teams[team] = []
                        teams[team].append(strand)
                
                # Check for confluence (multiple teams in same window)
                if len(teams) >= 2:
                    confluence_strength = self._calculate_confluence_strength(teams)
                    
                    if confluence_strength >= threshold:
                        confluence_events.append({
                            "event_id": f"confluence_{window_time.isoformat()}",
                            "teams_converged": list(teams.keys()),
                            "convergence_time": window_time.isoformat(),
                            "confluence_strength": confluence_strength,
                            "strands_involved": window_strands,
                            "market_context": self._extract_market_context(window_strands)
                        })
            
            return confluence_events
            
        except Exception as e:
            logger.error(f"Error finding confluence events: {e}")
            return []
    
    def _extract_team_from_tags(self, tags: List[str]) -> Optional[str]:
        """Extract team name from strand tags"""
        for tag in tags:
            if tag.startswith("agent:"):
                parts = tag.split(":")
                if len(parts) >= 2:
                    return parts[1]  # Return team name
        return None
    
    def _calculate_confluence_strength(self, teams: Dict[str, List[Dict[str, Any]]]) -> float:
        """Calculate confluence strength based on team overlap and pattern similarity"""
        try:
            # Simple confluence calculation based on number of teams and strand similarity
            team_count = len(teams)
            total_strands = sum(len(strands) for strands in teams.values())
            
            # Base confluence from team count
            base_confluence = min(team_count / 4.0, 1.0)  # Max at 4 teams
            
            # Boost from strand count
            strand_boost = min(total_strands / 10.0, 0.3)  # Max 0.3 boost
            
            return min(base_confluence + strand_boost, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating confluence strength: {e}")
            return 0.0
    
    def _extract_market_context(self, strands: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract market context from strands"""
        try:
            context = {
                "symbols": set(),
                "timeframes": set(),
                "sessions": set(),
                "regimes": set()
            }
            
            for strand in strands:
                if strand.get("symbol"):
                    context["symbols"].add(strand["symbol"])
                if strand.get("timeframe"):
                    context["timeframes"].add(strand["timeframe"])
                if strand.get("session_bucket"):
                    context["sessions"].add(strand["session_bucket"])
                if strand.get("regime"):
                    context["regimes"].add(strand["regime"])
            
            # Convert sets to lists for JSON serialization
            return {
                "symbols": list(context["symbols"]),
                "timeframes": list(context["timeframes"]),
                "sessions": list(context["sessions"]),
                "regimes": list(context["regimes"])
            }
            
        except Exception as e:
            logger.error(f"Error extracting market context: {e}")
            return {}
    
    def _determine_meta_signal_type(self, pattern_data: Dict[str, Any]) -> str:
        """Determine the type of meta-signal based on pattern data"""
        try:
            pattern_type = pattern_data.get("pattern_type", "unknown")
            
            if pattern_type == "confluence":
                return "strategic_confluence"
            elif pattern_type == "lead_lag":
                return "strategic_experiment"
            elif pattern_type == "meta_pattern":
                return "strategic_learning"
            elif pattern_type == "strategic_opportunity":
                return "strategic_warning"
            else:
                return "strategic_learning"  # Default
                
        except Exception as e:
            logger.error(f"Error determining meta-signal type: {e}")
            return "strategic_learning"
    
    async def _create_confluence_meta_signals(self, confluence_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create meta-signals for confluence events"""
        try:
            meta_signals = []
            
            for event in confluence_events:
                meta_signal_data = {
                    "pattern_name": f"Confluence Event {event['event_id']}",
                    "pattern_type": "confluence",
                    "teams_involved": event["teams_converged"],
                    "strength": event["confluence_strength"],
                    "confidence": min(event["confluence_strength"] * 1.2, 1.0),
                    "description": f"Multiple teams ({', '.join(event['teams_converged'])}) detected similar patterns at {event['convergence_time']}",
                    "strategic_implications": "High confluence suggests strong market signal requiring coordinated response"
                }
                
                result = await self.create_strategic_meta_signal(meta_signal_data)
                if result.get("success"):
                    meta_signals.append(result)
            
            return meta_signals
            
        except Exception as e:
            logger.error(f"Error creating confluence meta-signals: {e}")
            return []
    
    async def _create_strategic_strands(self, analysis_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create strategic strands from analysis result"""
        try:
            strategic_strands = []
            
            # Create strands for strategic patterns
            if "strategic_patterns" in analysis_result:
                for pattern in analysis_result["strategic_patterns"]:
                    strand = {
                        "kind": "strategic_pattern",
                        "module": "alpha",
                        "symbol": "MULTI",
                        "timeframe": "multi",
                        "session_bucket": "multi",
                        "regime": "multi",
                        "tags": [
                            f"agent:central_intelligence:strategic_pattern_miner:pattern_discovered",
                            f"team_member:{self.team_member_id}",
                            f"pattern_type:{pattern.get('pattern_type', 'unknown')}"
                        ],
                        "content": pattern.get("description", ""),
                        "sig_sigma": pattern.get("strength", 0.5),
                        "sig_confidence": pattern.get("confidence", 0.5),
                        "outcome_score": 0.0,
                        "strategic_meta_type": "strategic_pattern",
                        "team_member": self.team_member_id,
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }
                    
                    result = await self.db_manager.insert_strand(strand)
                    if result.get("success"):
                        strategic_strands.append(result)
            
            return strategic_strands
            
        except Exception as e:
            logger.error(f"Error creating strategic strands: {e}")
            return []
    
    def _format_prompt(self, prompt_template: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Format the prompt template with context"""
        try:
            prompt_text = prompt_template.get("prompt", "")
            return prompt_text.format(context=json.dumps(context, indent=2))
            
        except Exception as e:
            logger.error(f"Error formatting prompt: {e}")
            return prompt_text
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured data"""
        try:
            # Try to parse as JSON
            if response.strip().startswith("{"):
                return json.loads(response)
            else:
                # If not JSON, create a basic structure
                return {
                    "analysis_summary": response,
                    "strategic_patterns": [],
                    "confluence_events": [],
                    "meta_signals": []
                }
                
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing LLM response as JSON: {e}")
            return {
                "analysis_summary": response,
                "strategic_patterns": [],
                "confluence_events": [],
                "meta_signals": []
            }
