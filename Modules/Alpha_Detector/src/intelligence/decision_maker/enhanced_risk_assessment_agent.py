"""
Enhanced Risk Assessment Agent for Decision Maker Intelligence

Demonstrates full organic CIL influence with all three phases integrated.
Enhanced risk assessment agent with comprehensive CIL integration.
"""

import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone
import numpy as np

from .enhanced_decision_agent_base import EnhancedDecisionMakerAgent

class EnhancedRiskAssessmentAgent(EnhancedDecisionMakerAgent):
    """
    Enhanced Risk Assessment Agent with full organic CIL influence.
    Demonstrates all three phases of CIL integration for risk management.
    """

    def __init__(self, agent_name: str, supabase_manager: Any, llm_client: Any):
        super().__init__(agent_name, supabase_manager, llm_client)
        self.agent_name = agent_name
        self.logger = logging.getLogger(__name__)
        
        # Add risk-specific capabilities and specializations
        self.capabilities.extend([
            "advanced_risk_assessment",
            "portfolio_risk_analysis",
            "concentration_risk_detection",
            "liquidity_risk_evaluation",
            "compliance_risk_monitoring",
            "risk_doctrine_application"
        ])
        self.specializations.extend([
            "risk_analysis",
            "portfolio_risk_patterns",
            "concentration_risk_patterns",
            "liquidity_risk_patterns",
            "compliance_risk_patterns",
            "risk_based_recommendations"
        ])
        
        # Risk-specific tracking
        self.portfolio_risks_assessed = 0
        self.concentration_risks_identified = 0
        self.liquidity_risks_evaluated = 0
        self.compliance_risks_monitored = 0
        self.risk_doctrine_applications = 0

    async def _perform_core_risk_analysis(self, market_data: Dict[str, Any], raw_data_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform core risk analysis, simulating comprehensive risk assessment logic.
        This method is called by the base class's analyze_risk_with_organic_influence.
        """
        self.logger.info(f"Performing core risk analysis for {self.agent_name}")
        
        # Simulate comprehensive risk assessment
        portfolio_risk_metrics = self._calculate_portfolio_risk_metrics(market_data, raw_data_analysis)
        concentration_risk_analysis = self._analyze_concentration_risk(market_data)
        liquidity_risk_evaluation = self._evaluate_liquidity_risk(market_data)
        compliance_risk_assessment = self._assess_compliance_risk(market_data)
        
        # Simulate overall risk confidence calculation
        risk_confidence = self._calculate_overall_risk_confidence(
            portfolio_risk_metrics, concentration_risk_analysis, 
            liquidity_risk_evaluation, compliance_risk_assessment
        )
        
        # Update tracking metrics
        self.portfolio_risks_assessed += 1
        self.concentration_risks_identified += len(concentration_risk_analysis.get('risks', []))
        self.liquidity_risks_evaluated += len(liquidity_risk_evaluation.get('risks', []))
        self.compliance_risks_monitored += len(compliance_risk_assessment.get('risks', []))

        return {
            'agent': self.agent_name,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'risk_confidence': risk_confidence,
            'risk_type': 'comprehensive_risk_assessment',
            'risk_details': {
                'portfolio_risk_metrics': portfolio_risk_metrics,
                'concentration_risk_analysis': concentration_risk_analysis,
                'liquidity_risk_evaluation': liquidity_risk_evaluation,
                'compliance_risk_assessment': compliance_risk_assessment
            },
            'analysis_components': {
                'portfolio_risk': {'confidence': risk_confidence, 'metrics': len(portfolio_risk_metrics)},
                'concentration_risk': {'confidence': risk_confidence, 'risks': len(concentration_risk_analysis.get('risks', []))},
                'liquidity_risk': {'confidence': risk_confidence, 'risks': len(liquidity_risk_evaluation.get('risks', []))},
                'compliance_risk': {'confidence': risk_confidence, 'risks': len(compliance_risk_assessment.get('risks', []))}
            }
        }

    def _calculate_portfolio_risk_metrics(self, market_data: Dict[str, Any], raw_data_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate calculation of portfolio risk metrics."""
        symbol = market_data.get('symbol', 'BTC')
        price = market_data.get('price', 50000)
        
        # Simulate VaR calculation
        var_1d = price * 0.05  # 5% daily VaR
        var_7d = price * 0.15  # 15% weekly VaR
        
        # Simulate Sharpe ratio
        sharpe_ratio = np.random.uniform(0.5, 2.0)
        
        # Simulate max drawdown
        max_drawdown = np.random.uniform(0.1, 0.3)
        
        return {
            'var_1d': var_1d,
            'var_7d': var_7d,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'portfolio_value': price * 1000,  # Simulate portfolio value
            'risk_score': np.random.uniform(0.3, 0.8)
        }

    def _analyze_concentration_risk(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate analysis of concentration risk."""
        symbol = market_data.get('symbol', 'BTC')
        
        # Simulate concentration risk analysis
        concentration_risks = []
        if symbol == 'BTC':
            concentration_risks.append({
                'type': 'single_asset_concentration',
                'severity': 'high',
                'description': 'Portfolio heavily concentrated in BTC'
            })
        
        return {
            'concentration_score': np.random.uniform(0.4, 0.9),
            'risks': concentration_risks,
            'recommendations': ['Diversify portfolio across multiple assets']
        }

    def _evaluate_liquidity_risk(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate evaluation of liquidity risk."""
        symbol = market_data.get('symbol', 'BTC')
        
        # Simulate liquidity risk evaluation
        liquidity_risks = []
        liquidity_score = np.random.uniform(0.2, 0.8)
        
        if liquidity_score < 0.5:
            liquidity_risks.append({
                'type': 'low_liquidity_warning',
                'severity': 'medium',
                'description': 'Low liquidity detected for trading operations'
            })
        
        return {
            'liquidity_score': liquidity_score,
            'risks': liquidity_risks,
            'recommendations': ['Monitor liquidity conditions closely']
        }

    def _assess_compliance_risk(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate assessment of compliance risk."""
        symbol = market_data.get('symbol', 'BTC')
        
        # Simulate compliance risk assessment
        compliance_risks = []
        compliance_score = np.random.uniform(0.7, 1.0)  # Generally high compliance
        
        if compliance_score < 0.9:
            compliance_risks.append({
                'type': 'regulatory_uncertainty',
                'severity': 'low',
                'description': 'Minor regulatory uncertainty detected'
            })
        
        return {
            'compliance_score': compliance_score,
            'risks': compliance_risks,
            'recommendations': ['Maintain current compliance protocols']
        }

    def _calculate_overall_risk_confidence(self, portfolio_metrics: Dict, concentration_analysis: Dict, 
                                         liquidity_evaluation: Dict, compliance_assessment: Dict) -> float:
        """Simulate overall risk confidence calculation."""
        # Weighted average of different risk components
        portfolio_weight = 0.4
        concentration_weight = 0.25
        liquidity_weight = 0.2
        compliance_weight = 0.15
        
        portfolio_confidence = 1.0 - portfolio_metrics.get('risk_score', 0.5)
        concentration_confidence = 1.0 - concentration_analysis.get('concentration_score', 0.5)
        liquidity_confidence = liquidity_evaluation.get('liquidity_score', 0.5)
        compliance_confidence = compliance_assessment.get('compliance_score', 0.5)
        
        overall_confidence = (
            portfolio_confidence * portfolio_weight +
            concentration_confidence * concentration_weight +
            liquidity_confidence * liquidity_weight +
            compliance_confidence * compliance_weight
        )
        
        return min(1.0, max(0.0, overall_confidence))

    async def apply_risk_doctrine_guidance(self, risk_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply risk doctrine guidance to risk analysis.
        """
        if not self.risk_doctrine_integration_enabled:
            self.logger.warning("Risk doctrine integration is disabled")
            return risk_analysis
        
        try:
            self.logger.info(f"Agent {self.agent_name} applying risk doctrine guidance")
            
            # Query relevant risk doctrine
            doctrine_guidance = await self.risk_doctrine_integration.query_relevant_risk_doctrine(
                risk_analysis.get('risk_type', 'general')
            )
            
            # Apply doctrine guidance
            enhanced_analysis = await self.risk_doctrine_integration.apply_risk_doctrine_guidance(
                risk_analysis, doctrine_guidance
            )
            
            self.risk_doctrine_applications += 1
            self.logger.info(f"Applied risk doctrine guidance. Total applications: {self.risk_doctrine_applications}")
            
            return enhanced_analysis
            
        except Exception as e:
            self.logger.error(f"Failed to apply risk doctrine guidance: {e}")
            return risk_analysis

    async def generate_risk_recommendations(self, risk_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate risk-based recommendations based on comprehensive analysis.
        """
        self.logger.info(f"Generating risk recommendations for {self.agent_name}")
        
        recommendations = []
        
        # Portfolio risk recommendations
        portfolio_metrics = risk_analysis.get('risk_details', {}).get('portfolio_risk_metrics', {})
        if portfolio_metrics.get('risk_score', 0) > 0.7:
            recommendations.append({
                'type': 'portfolio_risk_reduction',
                'priority': 'high',
                'description': 'Reduce portfolio risk exposure',
                'suggested_actions': ['Reduce position sizes', 'Increase diversification']
            })
        
        # Concentration risk recommendations
        concentration_analysis = risk_analysis.get('risk_details', {}).get('concentration_risk_analysis', {})
        if concentration_analysis.get('concentration_score', 0) > 0.8:
            recommendations.append({
                'type': 'concentration_risk_mitigation',
                'priority': 'medium',
                'description': 'Address concentration risk',
                'suggested_actions': ['Diversify across more assets', 'Rebalance portfolio']
            })
        
        # Liquidity risk recommendations
        liquidity_evaluation = risk_analysis.get('risk_details', {}).get('liquidity_risk_evaluation', {})
        if liquidity_evaluation.get('liquidity_score', 1) < 0.5:
            recommendations.append({
                'type': 'liquidity_risk_management',
                'priority': 'high',
                'description': 'Manage liquidity risk',
                'suggested_actions': ['Monitor liquidity conditions', 'Adjust trading strategies']
            })
        
        self.logger.info(f"Generated {len(recommendations)} risk recommendations")
        return recommendations

    async def participate_in_risk_experiments(self, experiment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Participate in risk experiments with doctrine-guided decision making.
        """
        self.logger.info(f"Participating in risk experiment: {experiment_data.get('experiment_id')}")
        
        # Check doctrine contraindications
        is_contraindicated = await self.risk_doctrine_integration.check_risk_doctrine_contraindications(experiment_data)
        
        if is_contraindicated:
            return {
                'participation_status': 'declined',
                'reason': 'Contraindicated by risk doctrine',
                'experiment_id': experiment_data.get('experiment_id')
            }
        
        # Participate in experiment
        participation_result = {
            'participation_status': 'accepted',
            'experiment_id': experiment_data.get('experiment_id'),
            'agent_contribution': 'Risk assessment and monitoring',
            'doctrine_guidance_applied': True,
            'participation_timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        self.logger.info(f"Accepted participation in risk experiment: {experiment_data.get('experiment_id')}")
        return participation_result

    async def get_enhanced_risk_learning_summary(self) -> Dict[str, Any]:
        """
        Get a comprehensive summary of the agent's risk learning and adaptation.
        """
        base_summary = await super().get_risk_learning_summary()
        base_summary.update({
            'portfolio_risks_assessed': self.portfolio_risks_assessed,
            'concentration_risks_identified': self.concentration_risks_identified,
            'liquidity_risks_evaluated': self.liquidity_risks_evaluated,
            'compliance_risks_monitored': self.compliance_risks_monitored,
            'risk_doctrine_applications': self.risk_doctrine_applications,
            'agent_type': 'enhanced_risk_assessment_agent',
            'phase_3_integration': 'complete'
        })
        return base_summary
