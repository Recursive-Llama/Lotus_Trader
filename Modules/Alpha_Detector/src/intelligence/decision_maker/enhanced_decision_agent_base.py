"""
Enhanced Decision Maker Agent Base Class

Enhanced base class for organically CIL-influenced decision maker agents.
Integrates risk resonance, uncertainty-driven curiosity, and strategic insight consumption
to create agents that participate in the CIL's organic intelligence network.

Key Features:
- Organic CIL influence through risk resonance and insights
- Risk uncertainty-driven exploration and learning
- Risk motif creation and enhancement
- Strategic risk intelligence contribution
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient

from .risk_resonance_integration import RiskResonanceIntegration
from .risk_uncertainty_handler import RiskUncertaintyHandler
from .risk_motif_integration import RiskMotifIntegration
from .strategic_risk_insight_consumer import StrategicRiskInsightConsumer
from .cross_team_risk_integration import CrossTeamRiskIntegration
from .risk_doctrine_integration import RiskDoctrineIntegration
from .decision_maker_strand_listener import DecisionMakerStrandListener
from .portfolio_data_integration import PortfolioDataIntegration

class EnhancedDecisionMakerAgent:
    """
    Enhanced base class for organically CIL-influenced decision maker agents
    """

    def __init__(self, agent_name: str, supabase_manager: Any, llm_client: Any):
        self.agent_name = agent_name
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
        
        # Core CIL integration components
        self.risk_resonance_integration = RiskResonanceIntegration(supabase_manager)
        self.risk_uncertainty_handler = RiskUncertaintyHandler(supabase_manager)
        
        # Phase 2 components - Strategic Risk Intelligence Integration
        self.risk_motif_integration = RiskMotifIntegration(supabase_manager)
        self.strategic_risk_insight_consumer = StrategicRiskInsightConsumer(supabase_manager)
        self.cross_team_risk_integration = CrossTeamRiskIntegration(supabase_manager)
        
        # Phase 3 components - Organic Risk Doctrine Integration
        self.risk_doctrine_integration = RiskDoctrineIntegration(supabase_manager)
        
        # New components - CIL Integration and Portfolio Data
        self.strand_listener = DecisionMakerStrandListener(supabase_manager)
        self.portfolio_data_integration = PortfolioDataIntegration(supabase_manager)
        
        # Agent capabilities and specializations
        self.capabilities = [
            "risk_analysis",
            "risk_uncertainty_driven_exploration",
            "risk_resonance_calculation",
            "organic_cil_integration",
            "risk_motif_creation",
            "strategic_risk_insight_consumption",
            "cross_team_risk_pattern_awareness",
            "risk_doctrine_integration",
            "strategic_risk_learning"
        ]
        
        self.specializations = [
            "risk_pattern_detection",
            "risk_uncertainty_identification",
            "risk_resonance_enhancement",
            "organic_risk_learning",
            "risk_motif_evolution",
            "strategic_risk_analysis",
            "cross_team_risk_confluence",
            "risk_doctrine_application",
            "strategic_risk_doctrine_learning"
        ]
        
        # CIL integration state
        self.cil_integration_enabled = True
        self.risk_uncertainty_embrace_enabled = True
        self.risk_resonance_enhancement_enabled = True
        self.risk_motif_integration_enabled = True
        self.strategic_risk_insight_consumption_enabled = True
        self.cross_team_risk_awareness_enabled = True
        self.risk_doctrine_integration_enabled = True
        
        # Learning and adaptation tracking
        self.learning_history = []
        self.risk_uncertainty_resolution_count = 0
        self.risk_resonance_contributions = 0
        self.organic_risk_insights_gained = 0
        self.risk_motif_contributions = 0
        self.strategic_risk_insights_consumed = 0
        self.cross_team_risk_confluence_detections = 0
        self.risk_doctrine_queries = 0
        self.risk_doctrine_contributions = 0
        self.risk_contraindication_checks = 0
        
        # New tracking metrics
        self.cil_insights_received = 0
        self.portfolio_updates_processed = 0
        self.risk_alerts_handled = 0
        
        # CIL integration state
        self.cil_risk_insights = None
        self.cil_risk_guidance = None
        self.cil_execution_constraints = None
        self.cil_strategic_plan = None
        self.cil_synthesis_insights = None
        self.current_portfolio_state = None
        self.current_risk_alerts = []

    async def initialize(self):
        """Initialize the Decision Maker agent with all components."""
        try:
            self.logger.info(f"Initializing Decision Maker agent: {self.agent_name}")
            
            # Initialize portfolio data integration
            await self.portfolio_data_integration.initialize()
            
            # Register portfolio update callback
            self.portfolio_data_integration.add_portfolio_update_callback(self._handle_portfolio_update)
            
            # Register risk alert callback
            self.portfolio_data_integration.add_risk_alert_callback(self._handle_risk_alert)
            
            # Register strand listener callbacks
            self.strand_listener.register_insight_handler('risk_insights', self._handle_cil_risk_insights)
            self.strand_listener.register_insight_handler('cil_directive', self._handle_cil_directive)
            self.strand_listener.register_insight_handler('synthesis_insights', self._handle_synthesis_insights)
            
            # Start strand listening
            await self.strand_listener.start_listening()
            
            self.logger.info(f"Decision Maker agent initialized successfully: {self.agent_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Decision Maker agent: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the Decision Maker agent."""
        try:
            self.logger.info(f"Shutting down Decision Maker agent: {self.agent_name}")
            
            # Stop strand listening
            await self.strand_listener.stop_listening()
            
            # Shutdown portfolio data integration
            await self.portfolio_data_integration.shutdown()
            
            self.logger.info(f"Decision Maker agent shut down successfully: {self.agent_name}")
            
        except Exception as e:
            self.logger.error(f"Error shutting down Decision Maker agent: {e}")

    async def analyze_risk_with_organic_influence(self, market_data: Dict[str, Any], raw_data_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze risk with natural CIL influence through resonance and insights
        """
        try:
            self.logger.info(f"Agent {self.agent_name} performing risk analysis with organic CIL influence.")
            
            # 1. Perform core risk analysis (placeholder)
            base_risk_analysis = await self._perform_core_risk_analysis(market_data, raw_data_analysis)
            
            # 2. Calculate risk resonance for the analysis result and enhance score
            if self.risk_resonance_enhancement_enabled:
                risk_resonance_results = await self.risk_resonance_integration.calculate_risk_resonance(base_risk_analysis)
                base_risk_analysis['risk_resonance'] = risk_resonance_results
                base_risk_analysis['enhanced_risk_score'] = risk_resonance_results.get('enhanced_risk_score', base_risk_analysis.get('risk_confidence', 0.0))
            
            # 3. Consume valuable CIL risk insights naturally (Phase 2)
            if self.cil_integration_enabled and self.strategic_risk_insight_consumption_enabled:
                cil_risk_insights = await self.strategic_risk_insight_consumer.consume_cil_risk_insights(
                    base_risk_analysis.get('risk_type', 'general')
                )
                base_risk_analysis['cil_risk_insights'] = cil_risk_insights
                self.strategic_risk_insights_consumed += len(cil_risk_insights)
            
            # 4. Contribute to risk motif creation (Phase 2)
            if self.cil_integration_enabled and self.risk_motif_integration_enabled:
                risk_motif_contribution = await self.risk_motif_integration.create_risk_motif_from_pattern(base_risk_analysis)
                base_risk_analysis['risk_motif_contribution'] = risk_motif_contribution
                if risk_motif_contribution:
                    self.risk_motif_contributions += 1
            
            # 5. Cross-team risk pattern awareness (Phase 2)
            if self.cil_integration_enabled and self.cross_team_risk_awareness_enabled:
                cross_team_risk_confluence = await self.cross_team_risk_integration.detect_cross_team_risk_confluence("5m")
                base_risk_analysis['cross_team_risk_confluence'] = cross_team_risk_confluence
                self.cross_team_risk_confluence_detections += len(cross_team_risk_confluence)
            
            # 6. Risk doctrine integration (Phase 3)
            if self.cil_integration_enabled and self.risk_doctrine_integration_enabled:
                risk_doctrine_guidance = await self.risk_doctrine_integration.query_relevant_risk_doctrine(
                    base_risk_analysis.get('risk_type', 'general')
                )
                base_risk_analysis['risk_doctrine_guidance'] = risk_doctrine_guidance
                self.risk_doctrine_queries += 1
            
            # 7. Handle risk uncertainty-driven exploration
            if self.risk_uncertainty_embrace_enabled:
                risk_uncertainty_analysis = await self.risk_uncertainty_handler.detect_risk_uncertainty(base_risk_analysis)
                base_risk_analysis['risk_uncertainty_analysis'] = risk_uncertainty_analysis
                
                # Publish risk uncertainty strands if uncertainty detected
                if risk_uncertainty_analysis.get('risk_uncertainty_detected', False):
                    risk_uncertainty_strand_id = await self.risk_uncertainty_handler.publish_risk_uncertainty_strand(risk_uncertainty_analysis)
                    base_risk_analysis['risk_uncertainty_strand_id'] = risk_uncertainty_strand_id
                    self.risk_uncertainty_resolution_count += 1
            
            # 8. Publish results with risk resonance values
            enhanced_strand_id = await self._publish_enhanced_risk_results(base_risk_analysis)
            base_risk_analysis['enhanced_strand_id'] = enhanced_strand_id
            
            # 9. Update learning and adaptation tracking
            await self._update_risk_learning_tracking(base_risk_analysis)
            
            self.logger.info(f"Completed organic CIL-influenced risk analysis for {self.agent_name}")
            return base_risk_analysis
            
        except Exception as e:
            self.logger.error(f"Error during organic CIL-influenced risk analysis for {self.agent_name}: {e}")
            return {'error': str(e), 'agent': self.agent_name, 'timestamp': datetime.now(timezone.utc).isoformat()}

    async def _perform_core_risk_analysis(self, market_data: Dict[str, Any], raw_data_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform core risk analysis - to be implemented by subclasses
        """
        # Placeholder implementation - subclasses should override this
        return {
            'agent': self.agent_name,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'risk_confidence': 0.5,
            'risk_type': 'general_risk_analysis',
            'risk_pattern_details': 'Core risk analysis placeholder',
            'analysis_components': {}
        }

    async def _publish_enhanced_risk_results(self, risk_analysis: Dict[str, Any]) -> str:
        """
        Publish enhanced risk results to AD_strands with resonance values
        """
        try:
            # Create enhanced risk strand content
            strand_content = {
                'type': 'risk_analysis',
                'agent': self.agent_name,
                'risk_analysis': risk_analysis,
                'risk_resonance': risk_analysis.get('risk_resonance', {}),
                'risk_uncertainty': risk_analysis.get('risk_uncertainty_analysis', {}),
                'enhanced_risk_score': risk_analysis.get('enhanced_risk_score', risk_analysis.get('risk_confidence', 0.0)),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Create appropriate tags
            risk_type = risk_analysis.get('risk_type', 'general')
            tags = f"dm:risk_assessment:{risk_type}"
            
            # Simulate publishing to AD_strands
            strand_id = f"risk_strand_{self.agent_name}_{datetime.now(timezone.utc).timestamp()}"
            self.logger.info(f"Published enhanced risk results strand: {strand_id}")
            
            # In a real system, this would publish to AD_strands via communication_protocol
            # await self.supabase_manager.insert_data('AD_strands', {'id': strand_id, 'content': strand_content, 'tags': tags})
            
            return strand_id
            
        except Exception as e:
            self.logger.error(f"Failed to publish enhanced risk results: {e}")
            return ""

    async def _update_risk_learning_tracking(self, risk_analysis: Dict[str, Any]):
        """
        Update learning and adaptation tracking based on risk analysis results
        """
        try:
            # Track risk resonance contributions
            if 'risk_resonance' in risk_analysis:
                self.risk_resonance_contributions += 1
            
            # Track organic risk insights gained
            if risk_analysis.get('enhanced_risk_score', 0) > risk_analysis.get('risk_confidence', 0):
                self.organic_risk_insights_gained += 1
            
            # Add to learning history
            learning_entry = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'agent': self.agent_name,
                'risk_type': risk_analysis.get('risk_type', 'general'),
                'risk_confidence': risk_analysis.get('risk_confidence', 0.0),
                'enhanced_risk_score': risk_analysis.get('enhanced_risk_score', 0.0),
                'risk_resonance_contribution': 'risk_resonance' in risk_analysis,
                'risk_uncertainty_detected': risk_analysis.get('risk_uncertainty_analysis', {}).get('risk_uncertainty_detected', False)
            }
            
            self.learning_history.append(learning_entry)
            
            # Keep only recent history (last 100 entries)
            if len(self.learning_history) > 100:
                self.learning_history = self.learning_history[-100:]
                
        except Exception as e:
            self.logger.error(f"Failed to update risk learning tracking: {e}")

    async def get_risk_learning_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the agent's risk learning and adaptation.
        """
        try:
            return {
                'agent': self.agent_name,
                'risk_uncertainty_resolutions': self.risk_uncertainty_resolution_count,
                'risk_resonance_contributions': self.risk_resonance_contributions,
                'organic_risk_insights_gained': self.organic_risk_insights_gained,
                'risk_motif_contributions': self.risk_motif_contributions,
                'strategic_risk_insights_consumed': self.strategic_risk_insights_consumed,
                'cross_team_risk_confluence_detections': self.cross_team_risk_confluence_detections,
                'risk_doctrine_queries': self.risk_doctrine_queries,
                'risk_doctrine_contributions': self.risk_doctrine_contributions,
                'risk_contraindication_checks': self.risk_contraindication_checks,
                'learning_history_length': len(self.learning_history),
                'cil_integration_enabled': self.cil_integration_enabled,
                'risk_uncertainty_embrace_enabled': self.risk_uncertainty_embrace_enabled,
                'risk_resonance_enhancement_enabled': self.risk_resonance_enhancement_enabled,
                'risk_motif_integration_enabled': self.risk_motif_integration_enabled,
                'strategic_risk_insight_consumption_enabled': self.strategic_risk_insight_consumption_enabled,
                'cross_team_risk_awareness_enabled': self.cross_team_risk_awareness_enabled,
                'risk_doctrine_integration_enabled': self.risk_doctrine_integration_enabled,
                'recent_risk_learning': self.learning_history[-5:] if self.learning_history else []
            }
            
        except Exception as e:
            self.logger.error(f"Risk learning summary generation failed: {e}")
            return {'error': str(e)}

    async def contribute_to_risk_motif(self, risk_pattern_data: Dict[str, Any]):
        """
        Contribute risk pattern data to motif creation for organic evolution
        """
        try:
            self.logger.info(f"Agent {self.agent_name} contributing to risk motif creation")
            # Placeholder for risk motif contribution
            # In Phase 2, this will be implemented with RiskMotifIntegration
            return "risk_motif_contribution_placeholder"
            
        except Exception as e:
            self.logger.error(f"Failed to contribute to risk motif: {e}")
            return None

    async def calculate_risk_resonance_contribution(self, risk_strand_data: Dict[str, Any]):
        """
        Calculate risk resonance contribution for organic evolution
        """
        try:
            self.logger.info(f"Agent {self.agent_name} calculating risk resonance contribution")
            
            # Calculate risk φ, ρ values
            risk_resonance_results = await self.risk_resonance_integration.calculate_risk_resonance(risk_strand_data)
            
            # Update risk telemetry
            self.logger.debug(f"Risk resonance calculated: φ={risk_resonance_results.get('phi', 0):.2f}, ρ={risk_resonance_results.get('rho', 0):.2f}")
            
            # Contribute to global risk θ field
            await self.risk_resonance_integration._contribute_to_global_risk_theta(risk_resonance_results)
            
            # Enable organic risk influence through resonance
            risk_influence = await self.risk_resonance_integration._calculate_organic_risk_influence(risk_resonance_results)
            
            return {
                'risk_resonance': risk_resonance_results,
                'risk_influence': risk_influence,
                'contribution_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to calculate risk resonance contribution: {e}")
            return None

    def get_capabilities(self) -> List[str]:
        """Get agent capabilities"""
        return self.capabilities.copy()

    def get_specializations(self) -> List[str]:
        """Get agent specializations"""
        return self.specializations.copy()

    def enable_cil_integration(self, enabled: bool = True):
        """Enable or disable CIL integration"""
        self.cil_integration_enabled = enabled
        self.logger.info(f"CIL integration {'enabled' if enabled else 'disabled'} for {self.agent_name}")

    def enable_risk_uncertainty_embrace(self, enabled: bool = True):
        """Enable or disable risk uncertainty embrace"""
        self.risk_uncertainty_embrace_enabled = enabled
        self.logger.info(f"Risk uncertainty embrace {'enabled' if enabled else 'disabled'} for {self.agent_name}")

    def enable_risk_resonance_enhancement(self, enabled: bool = True):
        """Enable or disable risk resonance enhancement"""
        self.risk_resonance_enhancement_enabled = enabled
        self.logger.info(f"Risk resonance enhancement {'enabled' if enabled else 'disabled'} for {self.agent_name}")

    # Phase 2: Strategic Risk Intelligence Integration Methods
    
    async def contribute_to_risk_motif(self, risk_pattern_data: Dict[str, Any]) -> str:
        """
        Contribute risk pattern data to motif creation for organic evolution.
        """
        if not self.risk_motif_integration_enabled:
            self.logger.warning("Risk motif integration is disabled")
            return None
        
        try:
            self.logger.info(f"Agent {self.agent_name} contributing to risk motif creation")
            
            # Create risk motif from pattern
            risk_motif_id = await self.risk_motif_integration.create_risk_motif_from_pattern(risk_pattern_data)
            
            if risk_motif_id:
                self.risk_motif_contributions += 1
                self.logger.info(f"Contributed to risk motif: {risk_motif_id}")
            
            return risk_motif_id
            
        except Exception as e:
            self.logger.error(f"Failed to contribute to risk motif: {e}")
            return None

    async def consume_strategic_risk_insights(self, risk_type: str) -> List[Dict[str, Any]]:
        """
        Consume strategic risk insights from CIL organically.
        """
        if not self.strategic_risk_insight_consumption_enabled:
            self.logger.warning("Strategic risk insight consumption is disabled")
            return []
        
        try:
            self.logger.info(f"Agent {self.agent_name} consuming strategic risk insights for: {risk_type}")
            
            # Consume CIL risk insights
            risk_insights = await self.strategic_risk_insight_consumer.consume_cil_risk_insights(risk_type)
            
            self.strategic_risk_insights_consumed += len(risk_insights)
            self.logger.info(f"Consumed {len(risk_insights)} strategic risk insights")
            
            return risk_insights
            
        except Exception as e:
            self.logger.error(f"Failed to consume strategic risk insights: {e}")
            return []

    async def detect_cross_team_risk_confluence(self, time_window: str = "5m") -> List[Dict[str, Any]]:
        """
        Detect cross-team risk confluence patterns organically.
        """
        if not self.cross_team_risk_awareness_enabled:
            self.logger.warning("Cross-team risk awareness is disabled")
            return []
        
        try:
            self.logger.info(f"Agent {self.agent_name} detecting cross-team risk confluence")
            
            # Detect cross-team risk confluence
            confluence_patterns = await self.cross_team_risk_integration.detect_cross_team_risk_confluence(time_window)
            
            self.cross_team_risk_confluence_detections += len(confluence_patterns)
            self.logger.info(f"Detected {len(confluence_patterns)} cross-team risk confluence patterns")
            
            return confluence_patterns
            
        except Exception as e:
            self.logger.error(f"Failed to detect cross-team risk confluence: {e}")
            return []

    def enable_risk_motif_integration(self, enabled: bool = True):
        """Enable or disable risk motif integration"""
        self.risk_motif_integration_enabled = enabled
        self.logger.info(f"Risk motif integration {'enabled' if enabled else 'disabled'} for {self.agent_name}")

    def enable_strategic_risk_insight_consumption(self, enabled: bool = True):
        """Enable or disable strategic risk insight consumption"""
        self.strategic_risk_insight_consumption_enabled = enabled
        self.logger.info(f"Strategic risk insight consumption {'enabled' if enabled else 'disabled'} for {self.agent_name}")

    def enable_cross_team_risk_awareness(self, enabled: bool = True):
        """Enable or disable cross-team risk awareness"""
        self.cross_team_risk_awareness_enabled = enabled
        self.logger.info(f"Cross-team risk awareness {'enabled' if enabled else 'disabled'} for {self.agent_name}")

    # Phase 3: Organic Risk Doctrine Integration Methods
    
    async def query_relevant_risk_doctrine(self, risk_type: str) -> Dict[str, Any]:
        """
        Query relevant risk doctrine for risk type organically.
        """
        if not self.risk_doctrine_integration_enabled:
            self.logger.warning("Risk doctrine integration is disabled")
            return {}
        
        try:
            self.logger.info(f"Agent {self.agent_name} querying relevant risk doctrine for: {risk_type}")
            
            # Query relevant risk doctrine
            risk_doctrine_guidance = await self.risk_doctrine_integration.query_relevant_risk_doctrine(risk_type)
            
            self.risk_doctrine_queries += 1
            self.logger.info(f"Retrieved risk doctrine guidance with {len(risk_doctrine_guidance.get('recommendations', []))} recommendations")
            
            return risk_doctrine_guidance
            
        except Exception as e:
            self.logger.error(f"Risk doctrine query failed: {e}")
            return {}

    async def contribute_to_risk_doctrine(self, risk_pattern_evidence: Dict[str, Any]) -> str:
        """
        Contribute risk pattern evidence to doctrine for organic learning.
        """
        if not self.risk_doctrine_integration_enabled:
            self.logger.warning("Risk doctrine integration is disabled")
            return None
        
        try:
            self.logger.info(f"Agent {self.agent_name} contributing to risk doctrine")
            
            # Contribute to risk doctrine
            contribution_id = await self.risk_doctrine_integration.contribute_to_risk_doctrine(risk_pattern_evidence)
            
            if contribution_id:
                self.risk_doctrine_contributions += 1
                self.logger.info(f"Contributed to risk doctrine: {contribution_id}")
            
            return contribution_id
            
        except Exception as e:
            self.logger.error(f"Risk doctrine contribution failed: {e}")
            return None

    async def check_risk_doctrine_contraindications(self, proposed_risk_experiment: Dict[str, Any]) -> bool:
        """
        Check if proposed risk experiment is contraindicated organically.
        """
        if not self.risk_doctrine_integration_enabled:
            self.logger.warning("Risk doctrine integration is disabled")
            return False
        
        try:
            self.logger.info(f"Agent {self.agent_name} checking risk doctrine contraindications")
            
            # Check contraindications
            is_contraindicated = await self.risk_doctrine_integration.check_risk_doctrine_contraindications(proposed_risk_experiment)
            
            self.risk_contraindication_checks += 1
            self.logger.info(f"Risk contraindication check result: {'contraindicated' if is_contraindicated else 'safe to proceed'}")
            
            return is_contraindicated
            
        except Exception as e:
            self.logger.error(f"Risk contraindication check failed: {e}")
            return False

    def enable_risk_doctrine_integration(self, enabled: bool = True):
        """Enable or disable risk doctrine integration"""
        self.risk_doctrine_integration_enabled = enabled
        self.logger.info(f"Risk doctrine integration {'enabled' if enabled else 'disabled'} for {self.agent_name}")

    def get_risk_doctrine_integration_summary(self) -> Dict[str, Any]:
        """
        Get summary of risk doctrine integration.
        """
        if not self.risk_doctrine_integration_enabled:
            return {'risk_doctrine_integration': 'disabled'}
        
        try:
            return self.risk_doctrine_integration.get_risk_doctrine_integration_summary()
        except Exception as e:
            self.logger.error(f"Risk doctrine integration summary failed: {e}")
            return {'error': str(e)}
    
    # New callback handler methods for CIL integration and portfolio data
    
    async def _handle_cil_risk_insights(self, insights: Dict[str, Any]):
        """Handle CIL risk insights received via strand listening."""
        try:
            self.logger.info(f"Processing CIL risk insights: {insights.get('source_strand_id', 'unknown')}")
            
            # Extract risk insights
            risk_assessment = insights.get('risk_assessment', {})
            risk_parameters = insights.get('risk_parameters', {})
            execution_constraints = insights.get('execution_constraints', {})
            strategic_guidance = insights.get('strategic_guidance', {})
            
            # Apply insights to Decision Maker's risk assessment
            await self._apply_cil_risk_insights(risk_assessment, risk_parameters, execution_constraints, strategic_guidance)
            
            self.cil_insights_received += 1
            self.logger.info(f"Successfully processed CIL risk insights")
            
        except Exception as e:
            self.logger.error(f"Error handling CIL risk insights: {e}")
    
    async def _handle_cil_directive(self, directive: Dict[str, Any]):
        """Handle CIL directive received via strand listening."""
        try:
            self.logger.info(f"Processing CIL directive: {directive.get('source_strand_id', 'unknown')}")
            
            # Extract directive information
            directive_content = directive.get('directive', {})
            directive_type = directive_content.get('type', 'unknown')
            
            # Process directive based on type
            if directive_type == 'risk_guidance':
                await self._apply_risk_guidance_directive(directive_content)
            elif directive_type == 'execution_constraints':
                await self._apply_execution_constraints_directive(directive_content)
            elif directive_type == 'strategic_plan':
                await self._apply_strategic_plan_directive(directive_content)
            else:
                self.logger.warning(f"Unknown directive type: {directive_type}")
            
            self.cil_insights_received += 1
            self.logger.info(f"Successfully processed CIL directive")
            
        except Exception as e:
            self.logger.error(f"Error handling CIL directive: {e}")
    
    async def _handle_synthesis_insights(self, insights: Dict[str, Any]):
        """Handle synthesis insights received via strand listening."""
        try:
            self.logger.info(f"Processing synthesis insights: {insights.get('source_strand_id', 'unknown')}")
            
            # Extract synthesis data
            synthesis_data = insights.get('synthesis_data', {})
            
            # Apply synthesis insights to Decision Maker's understanding
            await self._apply_synthesis_insights(synthesis_data)
            
            self.cil_insights_received += 1
            self.logger.info(f"Successfully processed synthesis insights")
            
        except Exception as e:
            self.logger.error(f"Error handling synthesis insights: {e}")
    
    async def _handle_portfolio_update(self, portfolio_state):
        """Handle portfolio update from portfolio data integration."""
        try:
            self.logger.info(f"Processing portfolio update: {portfolio_state.total_value:.2f} total value")
            
            # Update Decision Maker's understanding of current portfolio state
            await self._update_portfolio_understanding(portfolio_state)
            
            self.portfolio_updates_processed += 1
            self.logger.info(f"Successfully processed portfolio update")
            
        except Exception as e:
            self.logger.error(f"Error handling portfolio update: {e}")
    
    async def _handle_risk_alert(self, alert: Dict[str, Any]):
        """Handle risk alert from portfolio data integration."""
        try:
            self.logger.info(f"Processing risk alert: {alert.get('type', 'unknown')}")
            
            # Process risk alert
            await self._process_risk_alert(alert)
            
            self.risk_alerts_handled += 1
            self.logger.info(f"Successfully processed risk alert")
            
        except Exception as e:
            self.logger.error(f"Error handling risk alert: {e}")
    
    # Helper methods for processing insights and updates
    
    async def _apply_cil_risk_insights(self, risk_assessment: Dict[str, Any], risk_parameters: Dict[str, Any], 
                                     execution_constraints: Dict[str, Any], strategic_guidance: Dict[str, Any]):
        """Apply CIL risk insights to Decision Maker's risk assessment."""
        try:
            # Update risk assessment with CIL insights
            self.logger.info(f"Applying CIL risk insights - Risk level: {risk_assessment.get('level', 'unknown')}")
            
            # Store insights for use in decision making
            self.cil_risk_insights = {
                'risk_assessment': risk_assessment,
                'risk_parameters': risk_parameters,
                'execution_constraints': execution_constraints,
                'strategic_guidance': strategic_guidance,
                'applied_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error applying CIL risk insights: {e}")
    
    async def _apply_risk_guidance_directive(self, directive_content: Dict[str, Any]):
        """Apply risk guidance directive from CIL."""
        try:
            self.logger.info("Applying risk guidance directive from CIL")
            
            # Store directive for use in decision making
            self.cil_risk_guidance = {
                'directive': directive_content,
                'applied_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error applying risk guidance directive: {e}")
    
    async def _apply_execution_constraints_directive(self, directive_content: Dict[str, Any]):
        """Apply execution constraints directive from CIL."""
        try:
            self.logger.info("Applying execution constraints directive from CIL")
            
            # Store constraints for use in decision making
            self.cil_execution_constraints = {
                'constraints': directive_content,
                'applied_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error applying execution constraints directive: {e}")
    
    async def _apply_strategic_plan_directive(self, directive_content: Dict[str, Any]):
        """Apply strategic plan directive from CIL."""
        try:
            self.logger.info("Applying strategic plan directive from CIL")
            
            # Store plan for use in decision making
            self.cil_strategic_plan = {
                'plan': directive_content,
                'applied_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error applying strategic plan directive: {e}")
    
    async def _apply_synthesis_insights(self, synthesis_data: Dict[str, Any]):
        """Apply synthesis insights to Decision Maker's understanding."""
        try:
            self.logger.info("Applying synthesis insights from CIL")
            
            # Store synthesis insights for use in decision making
            self.cil_synthesis_insights = {
                'synthesis_data': synthesis_data,
                'applied_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error applying synthesis insights: {e}")
    
    async def _update_portfolio_understanding(self, portfolio_state):
        """Update Decision Maker's understanding of current portfolio state."""
        try:
            self.logger.info("Updating portfolio understanding")
            
            # Store current portfolio state
            self.current_portfolio_state = portfolio_state
            
            # Update risk assessment based on current portfolio
            await self._reassess_risk_based_on_portfolio(portfolio_state)
            
        except Exception as e:
            self.logger.error(f"Error updating portfolio understanding: {e}")
    
    async def _process_risk_alert(self, alert: Dict[str, Any]):
        """Process risk alert from portfolio data integration."""
        try:
            alert_type = alert.get('type', 'unknown')
            self.logger.warning(f"Processing risk alert: {alert_type}")
            
            # Store alert for decision making
            self.current_risk_alerts = self.current_risk_alerts or []
            self.current_risk_alerts.append({
                'alert': alert,
                'received_at': datetime.now(timezone.utc).isoformat()
            })
            
            # Take appropriate action based on alert type
            if alert_type == 'high_concentration':
                await self._handle_high_concentration_alert(alert)
            elif alert_type == 'high_leverage':
                await self._handle_high_leverage_alert(alert)
            elif alert_type == 'low_margin':
                await self._handle_low_margin_alert(alert)
            
        except Exception as e:
            self.logger.error(f"Error processing risk alert: {e}")
    
    async def _reassess_risk_based_on_portfolio(self, portfolio_state):
        """Reassess risk based on current portfolio state."""
        try:
            # This would integrate with the existing risk assessment methods
            # to incorporate current portfolio state
            self.logger.info("Reassessing risk based on current portfolio state")
            
        except Exception as e:
            self.logger.error(f"Error reassessing risk based on portfolio: {e}")
    
    async def _handle_high_concentration_alert(self, alert: Dict[str, Any]):
        """Handle high concentration risk alert."""
        try:
            self.logger.warning("Handling high concentration risk alert")
            # Implement high concentration risk handling logic
            
        except Exception as e:
            self.logger.error(f"Error handling high concentration alert: {e}")
    
    async def _handle_high_leverage_alert(self, alert: Dict[str, Any]):
        """Handle high leverage risk alert."""
        try:
            self.logger.warning("Handling high leverage risk alert")
            # Implement high leverage risk handling logic
            
        except Exception as e:
            self.logger.error(f"Error handling high leverage alert: {e}")
    
    async def _handle_low_margin_alert(self, alert: Dict[str, Any]):
        """Handle low margin risk alert."""
        try:
            self.logger.warning("Handling low margin risk alert")
            # Implement low margin risk handling logic
            
        except Exception as e:
            self.logger.error(f"Error handling low margin alert: {e}")
    
    def get_cil_integration_summary(self) -> Dict[str, Any]:
        """Get summary of CIL integration and portfolio data activity."""
        return {
            'cil_insights_received': self.cil_insights_received,
            'portfolio_updates_processed': self.portfolio_updates_processed,
            'risk_alerts_handled': self.risk_alerts_handled,
            'strand_listener_summary': self.strand_listener.get_listener_summary(),
            'portfolio_integration_summary': self.portfolio_data_integration.get_integration_summary(),
            'current_portfolio_value': self.current_portfolio_state.total_value if self.current_portfolio_state else 0,
            'active_risk_alerts': len(self.current_risk_alerts) if hasattr(self, 'current_risk_alerts') else 0
        }
