"""
CIL Doctrine of Negatives System - Missing Piece 5
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple, Set
from dataclasses import dataclass
from enum import Enum

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient


class NegativeType(Enum):
    """Types of negative patterns"""
    CONTRAINDICATED = "contraindicated"
    FAILURE_MODE = "failure_mode"
    ANTI_PATTERN = "anti_pattern"
    TOXIC_COMBINATION = "toxic_combination"
    REGIME_INCOMPATIBLE = "regime_incompatible"
    TIMING_INAPPROPRIATE = "timing_inappropriate"


class NegativeSeverity(Enum):
    """Severity levels for negative patterns"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NegativeStatus(Enum):
    """Status of negative pattern entries"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    RETIRED = "retired"
    INVESTIGATING = "investigating"


class NegativeSource(Enum):
    """Source of negative pattern identification"""
    EXPERIMENTAL_FAILURE = "experimental_failure"
    HISTORICAL_ANALYSIS = "historical_analysis"
    LLM_INSIGHT = "llm_insight"
    HUMAN_INPUT = "human_input"
    SYSTEM_DETECTION = "system_detection"


@dataclass
class NegativePattern:
    """A negative pattern or contraindicated combination"""
    negative_id: str
    negative_type: NegativeType
    pattern_description: str
    contraindicated_conditions: List[str]
    failure_mechanisms: List[str]
    severity: NegativeSeverity
    confidence_level: float
    evidence_count: int
    source: NegativeSource
    status: NegativeStatus
    created_at: datetime
    updated_at: datetime
    last_observed: Optional[datetime]


@dataclass
class NegativeDoctrine:
    """Doctrine entry for negative patterns"""
    doctrine_id: str
    doctrine_name: str
    negative_patterns: List[str]
    doctrine_rules: Dict[str, Any]
    enforcement_level: str
    exceptions: List[str]
    review_frequency: int
    created_at: datetime
    updated_at: datetime


@dataclass
class NegativeViolation:
    """A violation of negative doctrine"""
    violation_id: str
    negative_pattern_id: str
    violation_description: str
    violated_conditions: List[str]
    severity: NegativeSeverity
    detected_at: datetime
    resolved_at: Optional[datetime]
    resolution_notes: Optional[str]
    created_at: datetime


@dataclass
class NegativeAnalysis:
    """Analysis of negative patterns"""
    analysis_id: str
    analysis_type: str
    negative_patterns_analyzed: List[str]
    analysis_results: Dict[str, Any]
    recommendations: List[str]
    confidence_score: float
    created_at: datetime


class DoctrineOfNegativesSystem:
    """CIL Doctrine of Negatives System - Contraindicated patterns and failure modes"""
    
    def __init__(self, supabase_manager: SupabaseManager, llm_client: OpenRouterClient):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        
        # Configuration
        self.negative_confidence_threshold = 0.7
        self.violation_severity_threshold = 0.8
        self.doctrine_review_interval_hours = 24
        self.negative_evidence_threshold = 3
        self.max_negative_patterns = 1000
        
        # Negative doctrine state
        self.negative_patterns: Dict[str, NegativePattern] = {}
        self.negative_doctrines: Dict[str, NegativeDoctrine] = {}
        self.negative_violations: List[NegativeViolation] = []
        self.negative_analyses: List[NegativeAnalysis] = []
        
        # LLM prompt templates
        self.negative_analysis_prompt = self._load_negative_analysis_prompt()
        self.violation_detection_prompt = self._load_violation_detection_prompt()
        self.doctrine_evolution_prompt = self._load_doctrine_evolution_prompt()
        
        # Initialize negative patterns
        self._initialize_negative_patterns()
        self._initialize_negative_doctrines()
    
    def _load_negative_analysis_prompt(self) -> str:
        """Load negative analysis prompt template"""
        return """
        Analyze the following patterns and conditions for negative or contraindicated combinations.
        
        Patterns/Conditions:
        {patterns_conditions}
        
        Context:
        - Market Regime: {market_regime}
        - Session: {session}
        - Timeframe: {timeframe}
        - Historical Performance: {historical_performance}
        
        Identify:
        1. Contraindicated pattern combinations
        2. Failure modes and anti-patterns
        3. Toxic combinations that should be avoided
        4. Regime-incompatible patterns
        5. Timing-inappropriate conditions
        
        Respond in JSON format:
        {{
            "negative_patterns": [
                {{
                    "negative_type": "contraindicated|failure_mode|anti_pattern|toxic_combination|regime_incompatible|timing_inappropriate",
                    "pattern_description": "description of the negative pattern",
                    "contraindicated_conditions": ["list of conditions"],
                    "failure_mechanisms": ["list of failure mechanisms"],
                    "severity": "low|medium|high|critical",
                    "confidence_level": 0.0-1.0,
                    "evidence": ["list of evidence"]
                }}
            ],
            "negative_insights": ["list of insights"],
            "uncertainty_flags": ["any uncertainties"]
        }}
        """
    
    def _load_violation_detection_prompt(self) -> str:
        """Load violation detection prompt template"""
        return """
        Detect violations of negative doctrine in the following experiment or pattern.
        
        Experiment/Pattern:
        {experiment_pattern}
        
        Negative Doctrine:
        {negative_doctrine}
        
        Context:
        - Current Conditions: {current_conditions}
        - Historical Violations: {historical_violations}
        - Risk Level: {risk_level}
        
        Detect:
        1. Direct violations of negative patterns
        2. Potential violations based on conditions
        3. Severity assessment of violations
        4. Recommended actions for violations
        
        Respond in JSON format:
        {{
            "violations_detected": [
                {{
                    "negative_pattern_id": "pattern_id",
                    "violation_type": "direct|potential|conditional",
                    "violation_description": "description of violation",
                    "violated_conditions": ["list of violated conditions"],
                    "severity": "low|medium|high|critical",
                    "confidence": 0.0-1.0,
                    "recommended_action": "block|warn|monitor|investigate"
                }}
            ],
            "violation_insights": ["list of insights"],
            "risk_assessment": "low|medium|high|critical"
        }}
        """
    
    def _load_doctrine_evolution_prompt(self) -> str:
        """Load doctrine evolution prompt template"""
        return """
        Evolve the negative doctrine based on new evidence and patterns.
        
        Current Doctrine:
        {current_doctrine}
        
        New Evidence:
        {new_evidence}
        
        Violation History:
        {violation_history}
        
        Performance Metrics:
        {performance_metrics}
        
        Evolve:
        1. Update negative patterns based on new evidence
        2. Adjust severity levels based on performance
        3. Add new negative patterns from failures
        4. Retire outdated negative patterns
        5. Refine doctrine rules and exceptions
        
        Respond in JSON format:
        {{
            "doctrine_updates": [
                {{
                    "update_type": "add_pattern|update_severity|retire_pattern|refine_rule|add_exception",
                    "target_id": "pattern_id|rule_id",
                    "update_details": {{"key": "value"}},
                    "rationale": "reason for update",
                    "confidence": 0.0-1.0
                }}
            ],
            "evolution_insights": ["list of insights"],
            "doctrine_health": 0.0-1.0
        }}
        """
    
    def _initialize_negative_patterns(self):
        """Initialize default negative patterns"""
        self.negative_patterns = {
            "high_vol_rsi_divergence": NegativePattern(
                negative_id="high_vol_rsi_divergence",
                negative_type=NegativeType.CONTRAINDICATED,
                pattern_description="RSI divergence signals in high volatility regimes",
                contraindicated_conditions=["volatility > 2.0", "regime = high_vol", "session = news"],
                failure_mechanisms=["false_signals", "whipsaws", "overtrading"],
                severity=NegativeSeverity.HIGH,
                confidence_level=0.85,
                evidence_count=15,
                source=NegativeSource.EXPERIMENTAL_FAILURE,
                status=NegativeStatus.ACTIVE,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                last_observed=datetime.now(timezone.utc)
            ),
            "low_volume_breakout": NegativePattern(
                negative_id="low_volume_breakout",
                negative_type=NegativeType.FAILURE_MODE,
                pattern_description="Breakout patterns with low volume confirmation",
                contraindicated_conditions=["volume < 0.5x_average", "breakout_strength > 0.02"],
                failure_mechanisms=["fake_breakout", "lack_of_participation", "quick_reversal"],
                severity=NegativeSeverity.MEDIUM,
                confidence_level=0.75,
                evidence_count=8,
                source=NegativeSource.HISTORICAL_ANALYSIS,
                status=NegativeStatus.ACTIVE,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                last_observed=datetime.now(timezone.utc)
            ),
            "trend_reversal_during_news": NegativePattern(
                negative_id="trend_reversal_during_news",
                negative_type=NegativeType.TIMING_INAPPROPRIATE,
                pattern_description="Trend reversal signals during high-impact news events",
                contraindicated_conditions=["news_impact = high", "trend_reversal_signal = true"],
                failure_mechanisms=["news_override", "unpredictable_volatility", "liquidity_gaps"],
                severity=NegativeSeverity.CRITICAL,
                confidence_level=0.95,
                evidence_count=25,
                source=NegativeSource.EXPERIMENTAL_FAILURE,
                status=NegativeStatus.ACTIVE,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                last_observed=datetime.now(timezone.utc)
            ),
            "multiple_divergence_conflict": NegativePattern(
                negative_id="multiple_divergence_conflict",
                negative_type=NegativeType.TOXIC_COMBINATION,
                pattern_description="Multiple conflicting divergence signals",
                contraindicated_conditions=["rsi_divergence = bullish", "macd_divergence = bearish", "volume_divergence = neutral"],
                failure_mechanisms=["signal_confusion", "indecision", "analysis_paralysis"],
                severity=NegativeSeverity.MEDIUM,
                confidence_level=0.70,
                evidence_count=12,
                source=NegativeSource.LLM_INSIGHT,
                status=NegativeStatus.ACTIVE,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                last_observed=datetime.now(timezone.utc)
            )
        }
    
    def _initialize_negative_doctrines(self):
        """Initialize negative doctrines"""
        self.negative_doctrines = {
            "volatility_doctrine": NegativeDoctrine(
                doctrine_id="volatility_doctrine",
                doctrine_name="High Volatility Contraindications",
                negative_patterns=["high_vol_rsi_divergence", "trend_reversal_during_news"],
                doctrine_rules={
                    "volatility_threshold": 2.0,
                    "enforcement_action": "block",
                    "exception_conditions": ["confirmed_breakout", "volume_confirmation"]
                },
                enforcement_level="strict",
                exceptions=["confirmed_breakout", "volume_confirmation"],
                review_frequency=24,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            ),
            "volume_doctrine": NegativeDoctrine(
                doctrine_id="volume_doctrine",
                doctrine_name="Volume Confirmation Requirements",
                negative_patterns=["low_volume_breakout"],
                doctrine_rules={
                    "volume_threshold": 0.5,
                    "enforcement_action": "warn",
                    "exception_conditions": ["news_catalyst", "institutional_flow"]
                },
                enforcement_level="moderate",
                exceptions=["news_catalyst", "institutional_flow"],
                review_frequency=12,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            ),
            "divergence_doctrine": NegativeDoctrine(
                doctrine_id="divergence_doctrine",
                doctrine_name="Divergence Signal Conflicts",
                negative_patterns=["multiple_divergence_conflict"],
                doctrine_rules={
                    "conflict_threshold": 2,
                    "enforcement_action": "monitor",
                    "exception_conditions": ["strong_volume_confirmation", "regime_alignment"]
                },
                enforcement_level="lenient",
                exceptions=["strong_volume_confirmation", "regime_alignment"],
                review_frequency=6,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
        }
    
    async def process_doctrine_of_negatives_analysis(self, experiment_designs: List[Dict[str, Any]],
                                                   pattern_conditions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process doctrine of negatives analysis"""
        try:
            # Analyze patterns for negative combinations
            negative_analyses = await self._analyze_negative_patterns(experiment_designs, pattern_conditions)
            
            # Detect violations of negative doctrine
            violation_detections = await self._detect_negative_violations(experiment_designs)
            
            # Evolve negative doctrine based on new evidence
            doctrine_evolution = await self._evolve_negative_doctrine(negative_analyses, violation_detections)
            
            # Update negative pattern database
            pattern_updates = await self._update_negative_patterns(negative_analyses, doctrine_evolution)
            
            # Compile results
            results = {
                'negative_analyses': negative_analyses,
                'violation_detections': violation_detections,
                'doctrine_evolution': doctrine_evolution,
                'pattern_updates': pattern_updates,
                'doctrine_timestamp': datetime.now(timezone.utc),
                'doctrine_errors': []
            }
            
            # Publish results
            await self._publish_doctrine_results(results)
            
            return results
            
        except Exception as e:
            print(f"Error processing doctrine of negatives analysis: {e}")
            return {
                'negative_analyses': [],
                'violation_detections': [],
                'doctrine_evolution': [],
                'pattern_updates': [],
                'doctrine_timestamp': datetime.now(timezone.utc),
                'doctrine_errors': [str(e)]
            }
    
    async def _analyze_negative_patterns(self, experiment_designs: List[Dict[str, Any]],
                                       pattern_conditions: List[Dict[str, Any]]) -> List[NegativeAnalysis]:
        """Analyze patterns for negative combinations"""
        analyses = []
        
        for design in experiment_designs:
            # Prepare analysis data
            analysis_data = {
                'patterns_conditions': design.get('patterns', []) + [cond.get('condition', '') for cond in pattern_conditions],
                'market_regime': design.get('market_regime', 'unknown'),
                'session': design.get('session', 'unknown'),
                'timeframe': design.get('timeframe', 'unknown'),
                'historical_performance': design.get('historical_performance', {})
            }
            
            # Generate negative analysis using LLM
            analysis = await self._generate_negative_analysis(analysis_data)
            
            if analysis:
                # Create negative analysis result
                negative_analysis = NegativeAnalysis(
                    analysis_id=f"NEGATIVE_ANALYSIS_{int(datetime.now().timestamp())}",
                    analysis_type="pattern_analysis",
                    negative_patterns_analyzed=design.get('patterns', []),
                    analysis_results=analysis,
                    recommendations=analysis.get('negative_insights', []),
                    confidence_score=analysis.get('confidence_score', 0.0),
                    created_at=datetime.now(timezone.utc)
                )
                
                analyses.append(negative_analysis)
                self.negative_analyses.append(negative_analysis)
        
        return analyses
    
    async def _generate_negative_analysis(self, analysis_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate negative analysis using LLM"""
        try:
            # Generate analysis using LLM
            analysis = await self._generate_llm_analysis(
                self.negative_analysis_prompt, analysis_data
            )
            
            return analysis
            
        except Exception as e:
            print(f"Error generating negative analysis: {e}")
            return None
    
    async def _detect_negative_violations(self, experiment_designs: List[Dict[str, Any]]) -> List[NegativeViolation]:
        """Detect violations of negative doctrine"""
        violations = []
        
        for design in experiment_designs:
            # Check against each negative doctrine
            for doctrine in self.negative_doctrines.values():
                # Prepare violation detection data
                detection_data = {
                    'experiment_pattern': design,
                    'negative_doctrine': doctrine.__dict__,
                    'current_conditions': design.get('conditions', {}),
                    'historical_violations': [v.__dict__ for v in self.negative_violations[-10:]],  # Last 10 violations
                    'risk_level': design.get('risk_level', 'medium')
                }
                
                # Generate violation detection using LLM
                detection = await self._generate_violation_detection(detection_data)
                
                if detection and detection.get('violations_detected'):
                    for violation_data in detection['violations_detected']:
                        # Create violation record
                        violation = NegativeViolation(
                            violation_id=f"VIOLATION_{int(datetime.now().timestamp())}",
                            negative_pattern_id=violation_data.get('negative_pattern_id', 'unknown'),
                            violation_description=violation_data.get('violation_description', ''),
                            violated_conditions=violation_data.get('violated_conditions', []),
                            severity=NegativeSeverity(violation_data.get('severity', 'medium')),
                            detected_at=datetime.now(timezone.utc),
                            resolved_at=None,
                            resolution_notes=None,
                            created_at=datetime.now(timezone.utc)
                        )
                        
                        violations.append(violation)
                        self.negative_violations.append(violation)
        
        return violations
    
    async def _generate_violation_detection(self, detection_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate violation detection using LLM"""
        try:
            # Generate detection using LLM
            detection = await self._generate_llm_analysis(
                self.violation_detection_prompt, detection_data
            )
            
            return detection
            
        except Exception as e:
            print(f"Error generating violation detection: {e}")
            return None
    
    async def _evolve_negative_doctrine(self, negative_analyses: List[NegativeAnalysis],
                                      violation_detections: List[NegativeViolation]) -> List[Dict[str, Any]]:
        """Evolve negative doctrine based on new evidence"""
        evolution_updates = []
        
        # Prepare evolution data
        evolution_data = {
            'current_doctrine': {name: doctrine.__dict__ for name, doctrine in self.negative_doctrines.items()},
            'new_evidence': [analysis.__dict__ for analysis in negative_analyses],
            'violation_history': [violation.__dict__ for violation in violation_detections],
            'performance_metrics': self._calculate_doctrine_performance_metrics()
        }
        
        # Generate doctrine evolution using LLM
        evolution = await self._generate_doctrine_evolution(evolution_data)
        
        if evolution and evolution.get('doctrine_updates'):
            for update_data in evolution['doctrine_updates']:
                evolution_updates.append({
                    'update_type': update_data.get('update_type', ''),
                    'target_id': update_data.get('target_id', ''),
                    'update_details': update_data.get('update_details', {}),
                    'rationale': update_data.get('rationale', ''),
                    'confidence': update_data.get('confidence', 0.0)
                })
        
        return evolution_updates
    
    async def _generate_doctrine_evolution(self, evolution_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate doctrine evolution using LLM"""
        try:
            # Generate evolution using LLM
            evolution = await self._generate_llm_analysis(
                self.doctrine_evolution_prompt, evolution_data
            )
            
            return evolution
            
        except Exception as e:
            print(f"Error generating doctrine evolution: {e}")
            return None
    
    def _calculate_doctrine_performance_metrics(self) -> Dict[str, float]:
        """Calculate doctrine performance metrics"""
        metrics = {
            'total_violations': len(self.negative_violations),
            'resolved_violations': len([v for v in self.negative_violations if v.resolved_at is not None]),
            'active_patterns': len([p for p in self.negative_patterns.values() if p.status == NegativeStatus.ACTIVE]),
            'doctrine_effectiveness': 0.0
        }
        
        if metrics['total_violations'] > 0:
            metrics['doctrine_effectiveness'] = metrics['resolved_violations'] / metrics['total_violations']
        
        return metrics
    
    async def _update_negative_patterns(self, negative_analyses: List[NegativeAnalysis],
                                      doctrine_evolution: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Update negative patterns based on analysis and evolution"""
        pattern_updates = []
        
        for analysis in negative_analyses:
            # Extract negative patterns from analysis
            negative_patterns = analysis.analysis_results.get('negative_patterns', [])
            
            for pattern_data in negative_patterns:
                # Check if pattern already exists
                pattern_id = f"pattern_{int(datetime.now().timestamp())}"
                
                # Create new negative pattern
                negative_pattern = NegativePattern(
                    negative_id=pattern_id,
                    negative_type=NegativeType(pattern_data.get('negative_type', 'contraindicated')),
                    pattern_description=pattern_data.get('pattern_description', ''),
                    contraindicated_conditions=pattern_data.get('contraindicated_conditions', []),
                    failure_mechanisms=pattern_data.get('failure_mechanisms', []),
                    severity=NegativeSeverity(pattern_data.get('severity', 'medium')),
                    confidence_level=pattern_data.get('confidence_level', 0.5),
                    evidence_count=len(pattern_data.get('evidence', [])),
                    source=NegativeSource.LLM_INSIGHT,
                    status=NegativeStatus.INVESTIGATING,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    last_observed=datetime.now(timezone.utc)
                )
                
                # Add to negative patterns if confidence is high enough
                if negative_pattern.confidence_level >= self.negative_confidence_threshold:
                    self.negative_patterns[pattern_id] = negative_pattern
                    
                    pattern_updates.append({
                        'pattern_id': pattern_id,
                        'update_type': 'add_pattern',
                        'pattern_data': negative_pattern.__dict__,
                        'confidence': negative_pattern.confidence_level,
                        'updated_at': datetime.now(timezone.utc).isoformat()
                    })
        
        return pattern_updates
    
    async def _generate_llm_analysis(self, prompt_template: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate LLM analysis using prompt template"""
        try:
            # Format prompt with data
            formatted_prompt = prompt_template.format(**data)
            
            # Call LLM (mock implementation)
            # In real implementation, use self.llm_client
            if 'negative_patterns' in formatted_prompt and 'patterns_conditions' in formatted_prompt:
                response = {
                    "negative_patterns": [
                        {
                            "negative_type": "contraindicated",
                            "pattern_description": "High volatility RSI divergence signals",
                            "contraindicated_conditions": ["volatility > 2.0", "regime = high_vol"],
                            "failure_mechanisms": ["false_signals", "whipsaws"],
                            "severity": "high",
                            "confidence_level": 0.85,
                            "evidence": ["experimental_failure", "historical_analysis"]
                        }
                    ],
                    "negative_insights": ["High volatility reduces RSI reliability", "News events override technical signals"],
                    "uncertainty_flags": ["limited_sample_size"]
                }
            elif 'violations_detected' in formatted_prompt or 'experiment_pattern' in formatted_prompt:
                response = {
                    "violations_detected": [
                        {
                            "negative_pattern_id": "high_vol_rsi_divergence",
                            "violation_type": "direct",
                            "violation_description": "RSI divergence signal in high volatility regime",
                            "violated_conditions": ["volatility > 2.0", "rsi_divergence = true"],
                            "severity": "high",
                            "confidence": 0.9,
                            "recommended_action": "block"
                        }
                    ],
                    "violation_insights": ["High confidence violation detected", "Immediate action required"],
                    "risk_assessment": "high"
                }
            elif 'doctrine_updates' in formatted_prompt or 'current_doctrine' in formatted_prompt:
                response = {
                    "doctrine_updates": [
                        {
                            "update_type": "add_pattern",
                            "target_id": "new_pattern_1",
                            "update_details": {"severity": "high", "confidence": 0.85},
                            "rationale": "New evidence from experimental failures",
                            "confidence": 0.8
                        }
                    ],
                    "evolution_insights": ["Doctrine evolution based on new evidence"],
                    "doctrine_health": 0.85
                }
            else:
                response = {
                    "negative_patterns": [
                        {
                            "negative_type": "contraindicated",
                            "pattern_description": "High volatility RSI divergence signals",
                            "contraindicated_conditions": ["volatility > 2.0", "regime = high_vol"],
                            "failure_mechanisms": ["false_signals", "whipsaws"],
                            "severity": "high",
                            "confidence_level": 0.85,
                            "evidence": ["experimental_failure", "historical_analysis"]
                        }
                    ],
                    "negative_insights": ["High volatility reduces RSI reliability", "News events override technical signals"],
                    "uncertainty_flags": ["limited_sample_size"]
                }
            
            return response
            
        except Exception as e:
            print(f"Error generating LLM analysis: {e}")
            return None
    
    async def _publish_doctrine_results(self, results: Dict[str, Any]):
        """Publish doctrine results as CIL strand"""
        try:
            # Create CIL doctrine strand
            cil_strand = {
                'id': f"cil_doctrine_of_negatives_{int(datetime.now().timestamp())}",
                'kind': 'cil_doctrine_of_negatives',
                'module': 'alpha',
                'symbol': 'ALL',
                'timeframe': '1h',
                'session_bucket': 'ALL',
                'regime': 'all',
                'tags': ['agent:central_intelligence:doctrine_of_negatives_system:doctrine_analysis'],
                'content': json.dumps(results, default=str),
                'sig_sigma': 0.9,
                'sig_confidence': 0.95,
                'outcome_score': 0.0,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'agent_id': 'central_intelligence_layer',
                'cil_team_member': 'doctrine_of_negatives_system',
                'strategic_meta_type': 'doctrine_analysis',
                'resonance_score': 0.9
            }
            
            # Insert into database
            await self.supabase_manager.insert_strand(cil_strand)
            
        except Exception as e:
            print(f"Error publishing doctrine results: {e}")


# Example usage and testing
async def main():
    """Example usage of DoctrineOfNegativesSystem"""
    from src.utils.supabase_manager import SupabaseManager
    from src.llm_integration.openrouter_client import OpenRouterClient
    
    # Initialize components
    supabase_manager = SupabaseManager()
    llm_client = OpenRouterClient()
    
    # Create doctrine of negatives system
    doctrine_system = DoctrineOfNegativesSystem(supabase_manager, llm_client)
    
    # Mock experiment designs
    experiment_designs = [
        {
            'patterns': ['rsi_divergence', 'volume_spike'],
            'market_regime': 'high_vol',
            'session': 'US',
            'timeframe': '1h',
            'historical_performance': {'success_rate': 0.6},
            'conditions': {'volatility': 2.5, 'rsi_divergence': True},
            'risk_level': 'high'
        },
        {
            'patterns': ['breakout', 'volume_confirmation'],
            'market_regime': 'sideways',
            'session': 'EU',
            'timeframe': '4h',
            'historical_performance': {'success_rate': 0.8},
            'conditions': {'volume': 0.3, 'breakout_strength': 0.03},
            'risk_level': 'medium'
        }
    ]
    
    pattern_conditions = [
        {'condition': 'volatility > 2.0'},
        {'condition': 'volume < 0.5x_average'},
        {'condition': 'news_impact = high'}
    ]
    
    # Process doctrine of negatives analysis
    results = await doctrine_system.process_doctrine_of_negatives_analysis(experiment_designs, pattern_conditions)
    
    print("Doctrine of Negatives Analysis Results:")
    print(f"Negative Analyses: {len(results['negative_analyses'])}")
    print(f"Violation Detections: {len(results['violation_detections'])}")
    print(f"Doctrine Evolution: {len(results['doctrine_evolution'])}")
    print(f"Pattern Updates: {len(results['pattern_updates'])}")


if __name__ == "__main__":
    asyncio.run(main())
