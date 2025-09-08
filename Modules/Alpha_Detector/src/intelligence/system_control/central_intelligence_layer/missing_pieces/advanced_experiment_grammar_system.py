"""
CIL Advanced Experiment Grammar System - Missing Piece 4
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple, Set
from dataclasses import dataclass
from enum import Enum

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient


class ExperimentShape(Enum):
    """Canonical experiment shapes"""
    DURABILITY = "durability"
    STACK = "stack"
    LEAD_LAG = "lead_lag"
    ABLATION = "ablation"
    BOUNDARY = "boundary"


class ExperimentComplexity(Enum):
    """Experiment complexity levels"""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    ADVANCED = "advanced"


class ValidationStatus(Enum):
    """Experiment validation status"""
    PENDING = "pending"
    VALIDATED = "validated"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


class ExperimentPhase(Enum):
    """Experiment execution phases"""
    DESIGN = "design"
    SETUP = "setup"
    EXECUTION = "execution"
    MONITORING = "monitoring"
    ANALYSIS = "analysis"
    COMPLETION = "completion"


@dataclass
class ExperimentGrammar:
    """Grammar rules for experiment design"""
    grammar_id: str
    experiment_shape: ExperimentShape
    complexity_level: ExperimentComplexity
    grammar_rules: Dict[str, Any]
    validation_criteria: List[str]
    success_metrics: List[str]
    failure_conditions: List[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class ExperimentTemplate:
    """Template for experiment design"""
    template_id: str
    template_name: str
    experiment_shape: ExperimentShape
    complexity_level: ExperimentComplexity
    template_structure: Dict[str, Any]
    required_fields: List[str]
    optional_fields: List[str]
    default_values: Dict[str, Any]
    validation_rules: List[str]
    created_at: datetime


@dataclass
class ExperimentDesign:
    """A designed experiment following grammar rules"""
    design_id: str
    experiment_shape: ExperimentShape
    complexity_level: ExperimentComplexity
    design_structure: Dict[str, Any]
    validation_status: ValidationStatus
    validation_results: Dict[str, Any]
    grammar_compliance: float
    design_quality: float
    created_at: datetime
    updated_at: datetime


@dataclass
class ExperimentValidation:
    """Validation result for an experiment design"""
    validation_id: str
    design_id: str
    validation_status: ValidationStatus
    validation_score: float
    compliance_issues: List[str]
    quality_issues: List[str]
    recommendations: List[str]
    validation_details: Dict[str, Any]
    created_at: datetime


class AdvancedExperimentGrammarSystem:
    """CIL Advanced Experiment Grammar System - Canonical experiment shapes and validation"""
    
    def __init__(self, supabase_manager: SupabaseManager, llm_client: OpenRouterClient):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        
        # Configuration
        self.validation_threshold = 0.8
        self.grammar_compliance_threshold = 0.7
        self.design_quality_threshold = 0.6
        self.max_experiment_duration_hours = 24
        self.min_sample_size = 10
        
        # Grammar state
        self.experiment_grammars: Dict[str, ExperimentGrammar] = {}
        self.experiment_templates: Dict[str, ExperimentTemplate] = {}
        self.active_designs: Dict[str, ExperimentDesign] = {}
        self.validation_history: List[ExperimentValidation] = []
        
        # LLM prompt templates
        self.grammar_analysis_prompt = self._load_grammar_analysis_prompt()
        self.validation_prompt = self._load_validation_prompt()
        self.template_generation_prompt = self._load_template_generation_prompt()
        
        # Initialize experiment grammars
        self._initialize_experiment_grammars()
        self._initialize_experiment_templates()
    
    def _load_grammar_analysis_prompt(self) -> str:
        """Load grammar analysis prompt template"""
        return """
        Analyze the following experiment design against the canonical experiment grammar.
        
        Experiment Design:
        - Shape: {experiment_shape}
        - Complexity: {complexity_level}
        - Structure: {design_structure}
        - Requirements: {requirements}
        
        Grammar Rules:
        {grammar_rules}
        
        Analyze:
        1. Grammar compliance (0.0-1.0)
        2. Design quality (0.0-1.0)
        3. Validation issues
        4. Quality improvements
        5. Compliance recommendations
        
        Respond in JSON format:
        {{
            "grammar_compliance": 0.0-1.0,
            "design_quality": 0.0-1.0,
            "compliance_issues": ["list of compliance issues"],
            "quality_issues": ["list of quality issues"],
            "recommendations": ["list of recommendations"],
            "validation_score": 0.0-1.0,
            "uncertainty_flags": ["any uncertainties"]
        }}
        """
    
    def _load_validation_prompt(self) -> str:
        """Load validation prompt template"""
        return """
        Validate the following experiment design against canonical experiment shapes.
        
        Experiment Design:
        - Shape: {experiment_shape}
        - Structure: {design_structure}
        - Validation Criteria: {validation_criteria}
        
        Canonical Shapes:
        - Durability: Tests pattern persistence over time
        - Stack: Tests pattern combination effects
        - Lead-Lag: Tests temporal relationships
        - Ablation: Tests component removal effects
        - Boundary: Tests pattern limits and edges
        
        Validate:
        1. Shape appropriateness
        2. Structure completeness
        3. Validation criteria compliance
        4. Success metrics alignment
        5. Failure condition coverage
        
        Respond in JSON format:
        {{
            "validation_status": "validated|rejected|needs_revision",
            "validation_score": 0.0-1.0,
            "shape_appropriateness": 0.0-1.0,
            "structure_completeness": 0.0-1.0,
            "criteria_compliance": 0.0-1.0,
            "issues": ["list of issues"],
            "recommendations": ["list of recommendations"]
        }}
        """
    
    def _load_template_generation_prompt(self) -> str:
        """Load template generation prompt template"""
        return """
        Generate an experiment template for the specified canonical shape.
        
        Requirements:
        - Shape: {experiment_shape}
        - Complexity: {complexity_level}
        - Context: {context}
        - Constraints: {constraints}
        
        Generate:
        1. Template structure
        2. Required fields
        3. Optional fields
        4. Default values
        5. Validation rules
        
        Respond in JSON format:
        {{
            "template_structure": {{"key": "value"}},
            "required_fields": ["list of required fields"],
            "optional_fields": ["list of optional fields"],
            "default_values": {{"key": "value"}},
            "validation_rules": ["list of validation rules"],
            "template_quality": 0.0-1.0
        }}
        """
    
    def _initialize_experiment_grammars(self):
        """Initialize canonical experiment grammars"""
        self.experiment_grammars = {
            "durability_grammar": ExperimentGrammar(
                grammar_id="durability_grammar",
                experiment_shape=ExperimentShape.DURABILITY,
                complexity_level=ExperimentComplexity.MODERATE,
                grammar_rules={
                    "time_series_required": True,
                    "persistence_metrics": ["duration", "decay_rate", "stability"],
                    "control_conditions": ["baseline", "noise_level", "regime_stability"],
                    "success_criteria": ["min_duration", "max_decay_rate", "stability_threshold"]
                },
                validation_criteria=["time_series_present", "persistence_metrics_defined", "control_conditions_set"],
                success_metrics=["pattern_duration", "decay_rate", "stability_score"],
                failure_conditions=["rapid_decay", "instability", "regime_shift"],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            ),
            "stack_grammar": ExperimentGrammar(
                grammar_id="stack_grammar",
                experiment_shape=ExperimentShape.STACK,
                complexity_level=ExperimentComplexity.COMPLEX,
                grammar_rules={
                    "multiple_patterns_required": True,
                    "interaction_metrics": ["synergy", "interference", "amplification"],
                    "combination_rules": ["additive", "multiplicative", "conditional"],
                    "success_criteria": ["synergy_threshold", "interference_limit", "amplification_target"]
                },
                validation_criteria=["multiple_patterns_present", "interaction_metrics_defined", "combination_rules_set"],
                success_metrics=["synergy_score", "interference_level", "amplification_factor"],
                failure_conditions=["negative_synergy", "high_interference", "amplification_failure"],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            ),
            "lead_lag_grammar": ExperimentGrammar(
                grammar_id="lead_lag_grammar",
                experiment_shape=ExperimentShape.LEAD_LAG,
                complexity_level=ExperimentComplexity.ADVANCED,
                grammar_rules={
                    "temporal_analysis_required": True,
                    "lag_metrics": ["lead_time", "lag_correlation", "causality_strength"],
                    "temporal_conditions": ["time_window", "frequency_analysis", "phase_relationship"],
                    "success_criteria": ["min_lead_time", "correlation_threshold", "causality_confidence"]
                },
                validation_criteria=["temporal_analysis_present", "lag_metrics_defined", "temporal_conditions_set"],
                success_metrics=["lead_time", "lag_correlation", "causality_score"],
                failure_conditions=["no_lead_lag", "weak_correlation", "spurious_causality"],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            ),
            "ablation_grammar": ExperimentGrammar(
                grammar_id="ablation_grammar",
                experiment_shape=ExperimentShape.ABLATION,
                complexity_level=ExperimentComplexity.MODERATE,
                grammar_rules={
                    "component_removal_required": True,
                    "ablation_metrics": ["performance_drop", "component_importance", "redundancy_level"],
                    "removal_conditions": ["systematic_removal", "random_removal", "targeted_removal"],
                    "success_criteria": ["performance_threshold", "importance_ranking", "redundancy_analysis"]
                },
                validation_criteria=["component_removal_present", "ablation_metrics_defined", "removal_conditions_set"],
                success_metrics=["performance_drop", "component_importance", "redundancy_score"],
                failure_conditions=["no_performance_drop", "unclear_importance", "redundancy_confusion"],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            ),
            "boundary_grammar": ExperimentGrammar(
                grammar_id="boundary_grammar",
                experiment_shape=ExperimentShape.BOUNDARY,
                complexity_level=ExperimentComplexity.SIMPLE,
                grammar_rules={
                    "limit_testing_required": True,
                    "boundary_metrics": ["limit_threshold", "edge_behavior", "transition_smoothness"],
                    "limit_conditions": ["parameter_limits", "condition_limits", "context_limits"],
                    "success_criteria": ["limit_identification", "edge_behavior_analysis", "transition_characterization"]
                },
                validation_criteria=["limit_testing_present", "boundary_metrics_defined", "limit_conditions_set"],
                success_metrics=["limit_threshold", "edge_behavior_score", "transition_smoothness"],
                failure_conditions=["no_limits_found", "unclear_edges", "abrupt_transitions"],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
        }
    
    def _initialize_experiment_templates(self):
        """Initialize experiment templates"""
        self.experiment_templates = {
            "durability_template": ExperimentTemplate(
                template_id="durability_template",
                template_name="Pattern Durability Test",
                experiment_shape=ExperimentShape.DURABILITY,
                complexity_level=ExperimentComplexity.MODERATE,
                template_structure={
                    "hypothesis": "Pattern X will persist for duration Y under conditions Z",
                    "methodology": "Time series analysis with persistence metrics",
                    "variables": ["pattern_strength", "time_duration", "regime_conditions"],
                    "controls": ["baseline_pattern", "noise_level", "regime_stability"],
                    "metrics": ["duration", "decay_rate", "stability_score"]
                },
                required_fields=["hypothesis", "methodology", "variables", "controls", "metrics"],
                optional_fields=["assumptions", "limitations", "extensions"],
                default_values={
                    "min_duration": 60,
                    "max_decay_rate": 0.1,
                    "stability_threshold": 0.8
                },
                validation_rules=["time_series_present", "persistence_metrics_defined", "control_conditions_set"],
                created_at=datetime.now(timezone.utc)
            ),
            "stack_template": ExperimentTemplate(
                template_id="stack_template",
                template_name="Pattern Stack Analysis",
                experiment_shape=ExperimentShape.STACK,
                complexity_level=ExperimentComplexity.COMPLEX,
                template_structure={
                    "hypothesis": "Patterns A and B will interact with synergy/interference effect",
                    "methodology": "Multi-pattern analysis with interaction metrics",
                    "variables": ["pattern_a", "pattern_b", "interaction_type"],
                    "controls": ["individual_patterns", "baseline_interaction", "noise_level"],
                    "metrics": ["synergy_score", "interference_level", "amplification_factor"]
                },
                required_fields=["hypothesis", "methodology", "variables", "controls", "metrics"],
                optional_fields=["interaction_rules", "combination_methods", "scaling_factors"],
                default_values={
                    "synergy_threshold": 0.2,
                    "interference_limit": 0.3,
                    "amplification_target": 1.5
                },
                validation_rules=["multiple_patterns_present", "interaction_metrics_defined", "combination_rules_set"],
                created_at=datetime.now(timezone.utc)
            )
        }
    
    async def process_experiment_grammar_analysis(self, experiment_designs: List[Dict[str, Any]],
                                                validation_requests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process experiment grammar analysis and validation"""
        try:
            # Analyze experiment designs against grammar
            grammar_analyses = await self._analyze_experiment_designs(experiment_designs)
            
            # Validate experiment designs
            validation_results = await self._validate_experiment_designs(validation_requests)
            
            # Generate experiment templates
            template_generations = await self._generate_experiment_templates(experiment_designs)
            
            # Update grammar compliance tracking
            compliance_updates = await self._update_grammar_compliance(grammar_analyses)
            
            # Compile results
            results = {
                'grammar_analyses': grammar_analyses,
                'validation_results': validation_results,
                'template_generations': template_generations,
                'compliance_updates': compliance_updates,
                'grammar_timestamp': datetime.now(timezone.utc),
                'grammar_errors': []
            }
            
            # Publish results
            await self._publish_grammar_results(results)
            
            return results
            
        except Exception as e:
            print(f"Error processing experiment grammar analysis: {e}")
            return {
                'grammar_analyses': [],
                'validation_results': [],
                'template_generations': [],
                'compliance_updates': [],
                'grammar_timestamp': datetime.now(timezone.utc),
                'grammar_errors': [str(e)]
            }
    
    async def _analyze_experiment_designs(self, experiment_designs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze experiment designs against grammar rules"""
        analyses = []
        
        for design in experiment_designs:
            # Determine experiment shape and complexity
            experiment_shape = ExperimentShape(design.get('experiment_shape', 'durability'))
            complexity_level = ExperimentComplexity(design.get('complexity_level', 'moderate'))
            
            # Get relevant grammar
            grammar = self._get_grammar_for_shape(experiment_shape)
            if not grammar:
                continue
            
            # Generate grammar analysis using LLM
            analysis = await self._generate_grammar_analysis(design, grammar)
            
            if analysis:
                analyses.append({
                    'design_id': design.get('design_id', f"DESIGN_{int(datetime.now().timestamp())}"),
                    'experiment_shape': experiment_shape.value,
                    'complexity_level': complexity_level.value,
                    'grammar_compliance': analysis.get('grammar_compliance', 0.0),
                    'design_quality': analysis.get('design_quality', 0.0),
                    'compliance_issues': analysis.get('compliance_issues', []),
                    'quality_issues': analysis.get('quality_issues', []),
                    'recommendations': analysis.get('recommendations', []),
                    'validation_score': analysis.get('validation_score', 0.0),
                    'uncertainty_flags': analysis.get('uncertainty_flags', [])
                })
        
        return analyses
    
    def _get_grammar_for_shape(self, experiment_shape: ExperimentShape) -> Optional[ExperimentGrammar]:
        """Get grammar for a specific experiment shape"""
        for grammar in self.experiment_grammars.values():
            if grammar.experiment_shape == experiment_shape:
                return grammar
        return None
    
    async def _generate_grammar_analysis(self, design: Dict[str, Any], grammar: ExperimentGrammar) -> Optional[Dict[str, Any]]:
        """Generate grammar analysis using LLM"""
        try:
            # Prepare prompt data
            prompt_data = {
                'experiment_shape': design.get('experiment_shape', 'durability'),
                'complexity_level': design.get('complexity_level', 'moderate'),
                'design_structure': design.get('design_structure', {}),
                'requirements': design.get('requirements', []),
                'grammar_rules': grammar.grammar_rules
            }
            
            # Generate analysis using LLM
            analysis = await self._generate_llm_analysis(
                self.grammar_analysis_prompt, prompt_data
            )
            
            return analysis
            
        except Exception as e:
            print(f"Error generating grammar analysis: {e}")
            return None
    
    async def _validate_experiment_designs(self, validation_requests: List[Dict[str, Any]]) -> List[ExperimentValidation]:
        """Validate experiment designs against canonical shapes"""
        validations = []
        
        for request in validation_requests:
            # Get experiment design
            design_id = request.get('design_id', '')
            design = request.get('design', {})
            
            # Generate validation using LLM
            validation = await self._generate_validation_analysis(design)
            
            if validation:
                # Create validation result
                validation_result = ExperimentValidation(
                    validation_id=f"VALIDATION_{int(datetime.now().timestamp())}",
                    design_id=design_id,
                    validation_status=ValidationStatus(validation.get('validation_status', 'pending')),
                    validation_score=validation.get('validation_score', 0.0),
                    compliance_issues=validation.get('issues', []),
                    quality_issues=[],
                    recommendations=validation.get('recommendations', []),
                    validation_details=validation,
                    created_at=datetime.now(timezone.utc)
                )
                
                validations.append(validation_result)
                self.validation_history.append(validation_result)
        
        return validations
    
    async def _generate_validation_analysis(self, design: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate validation analysis using LLM"""
        try:
            # Prepare prompt data
            prompt_data = {
                'experiment_shape': design.get('experiment_shape', 'durability'),
                'design_structure': design.get('design_structure', {}),
                'validation_criteria': design.get('validation_criteria', [])
            }
            
            # Generate validation using LLM
            validation = await self._generate_llm_analysis(
                self.validation_prompt, prompt_data
            )
            
            return validation
            
        except Exception as e:
            print(f"Error generating validation analysis: {e}")
            return None
    
    async def _generate_experiment_templates(self, experiment_designs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate experiment templates based on designs"""
        template_generations = []
        
        for design in experiment_designs:
            # Determine if template generation is needed
            experiment_shape = ExperimentShape(design.get('experiment_shape', 'durability'))
            complexity_level = ExperimentComplexity(design.get('complexity_level', 'moderate'))
            
            # Check if template already exists
            template_key = f"{experiment_shape.value}_template"
            if template_key in self.experiment_templates:
                continue  # Template already exists
            
            # Generate new template using LLM
            template = await self._generate_template(experiment_shape, complexity_level, design)
            
            if template:
                template_generations.append({
                    'template_id': f"TEMPLATE_{int(datetime.now().timestamp())}",
                    'experiment_shape': experiment_shape.value,
                    'complexity_level': complexity_level.value,
                    'template_structure': template.get('template_structure', {}),
                    'required_fields': template.get('required_fields', []),
                    'optional_fields': template.get('optional_fields', []),
                    'default_values': template.get('default_values', {}),
                    'validation_rules': template.get('validation_rules', []),
                    'template_quality': template.get('template_quality', 0.0)
                })
        
        return template_generations
    
    async def _generate_template(self, experiment_shape: ExperimentShape, complexity_level: ExperimentComplexity,
                               design: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate experiment template using LLM"""
        try:
            # Prepare prompt data
            prompt_data = {
                'experiment_shape': experiment_shape.value,
                'complexity_level': complexity_level.value,
                'context': design.get('context', {}),
                'constraints': design.get('constraints', [])
            }
            
            # Generate template using LLM
            template = await self._generate_llm_analysis(
                self.template_generation_prompt, prompt_data
            )
            
            return template
            
        except Exception as e:
            print(f"Error generating template: {e}")
            return None
    
    async def _update_grammar_compliance(self, grammar_analyses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Update grammar compliance tracking"""
        compliance_updates = []
        
        for analysis in grammar_analyses:
            # Track compliance metrics
            compliance_update = {
                'design_id': analysis['design_id'],
                'experiment_shape': analysis['experiment_shape'],
                'grammar_compliance': analysis['grammar_compliance'],
                'design_quality': analysis['design_quality'],
                'validation_score': analysis['validation_score'],
                'compliance_issues_count': len(analysis['compliance_issues']),
                'quality_issues_count': len(analysis['quality_issues']),
                'recommendations_count': len(analysis['recommendations']),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            compliance_updates.append(compliance_update)
        
        return compliance_updates
    
    async def _generate_llm_analysis(self, prompt_template: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate LLM analysis using prompt template"""
        try:
            # Format prompt with data
            formatted_prompt = prompt_template.format(**data)
            
            # Call LLM (mock implementation)
            # In real implementation, use self.llm_client
            if 'grammar_compliance' in formatted_prompt:
                response = {
                    "grammar_compliance": 0.85,
                    "design_quality": 0.78,
                    "compliance_issues": ["missing_control_conditions", "undefined_success_criteria"],
                    "quality_issues": ["insufficient_sample_size", "unclear_methodology"],
                    "recommendations": ["add_control_conditions", "define_success_criteria", "increase_sample_size"],
                    "validation_score": 0.82,
                    "uncertainty_flags": ["limited_historical_data"]
                }
            elif 'validation_status' in formatted_prompt:
                response = {
                    "validation_status": "validated",
                    "validation_score": 0.88,
                    "shape_appropriateness": 0.9,
                    "structure_completeness": 0.85,
                    "criteria_compliance": 0.88,
                    "issues": [],
                    "recommendations": ["monitor_execution", "adjust_parameters"]
                }
            else:
                response = {
                    "template_structure": {
                        "hypothesis": "Generated hypothesis template",
                        "methodology": "Generated methodology template",
                        "variables": ["var1", "var2", "var3"],
                        "controls": ["control1", "control2"],
                        "metrics": ["metric1", "metric2"]
                    },
                    "required_fields": ["hypothesis", "methodology", "variables"],
                    "optional_fields": ["assumptions", "limitations"],
                    "default_values": {"default1": "value1", "default2": "value2"},
                    "validation_rules": ["rule1", "rule2", "rule3"],
                    "template_quality": 0.85
                }
            
            return response
            
        except Exception as e:
            print(f"Error generating LLM analysis: {e}")
            return None
    
    async def _publish_grammar_results(self, results: Dict[str, Any]):
        """Publish grammar results as CIL strand"""
        try:
            # Create CIL grammar strand
            cil_strand = {
                'id': f"cil_experiment_grammar_{int(datetime.now().timestamp())}",
                'kind': 'cil_experiment_grammar',
                'module': 'alpha',
                'symbol': 'ALL',
                'timeframe': '1h',
                'session_bucket': 'ALL',
                'regime': 'all',
                'tags': ['agent:central_intelligence:advanced_experiment_grammar_system:grammar_analysis'],
                'content': json.dumps(results, default=str),
                'sig_sigma': 0.9,
                'sig_confidence': 0.95,
                'outcome_score': 0.0,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'agent_id': 'central_intelligence_layer',
                'cil_team_member': 'advanced_experiment_grammar_system',
                'strategic_meta_type': 'experiment_grammar_analysis',
                'resonance_score': 0.9
            }
            
            # Insert into database
            await self.supabase_manager.insert_strand(cil_strand)
            
        except Exception as e:
            print(f"Error publishing grammar results: {e}")


# Example usage and testing
async def main():
    """Example usage of AdvancedExperimentGrammarSystem"""
    from src.utils.supabase_manager import SupabaseManager
    from src.llm_integration.openrouter_client import OpenRouterClient
    
    # Initialize components
    supabase_manager = SupabaseManager()
    llm_client = OpenRouterClient()
    
    # Create advanced experiment grammar system
    grammar_system = AdvancedExperimentGrammarSystem(supabase_manager, llm_client)
    
    # Mock experiment designs
    experiment_designs = [
        {
            'design_id': 'design_1',
            'experiment_shape': 'durability',
            'complexity_level': 'moderate',
            'design_structure': {
                'hypothesis': 'RSI divergence will persist for 60 minutes',
                'methodology': 'Time series analysis',
                'variables': ['rsi_divergence', 'time_duration'],
                'controls': ['baseline_rsi', 'noise_level']
            },
            'requirements': ['time_series_analysis', 'persistence_metrics'],
            'context': {'market_regime': 'high_vol', 'session': 'US'},
            'constraints': ['max_duration_2h', 'min_sample_50']
        },
        {
            'design_id': 'design_2',
            'experiment_shape': 'stack',
            'complexity_level': 'complex',
            'design_structure': {
                'hypothesis': 'RSI divergence and volume spike will show synergy',
                'methodology': 'Multi-pattern analysis',
                'variables': ['rsi_divergence', 'volume_spike', 'interaction_type'],
                'controls': ['individual_patterns', 'baseline_interaction']
            },
            'requirements': ['multiple_patterns', 'interaction_metrics'],
            'context': {'market_regime': 'sideways', 'session': 'EU'},
            'constraints': ['max_complexity_advanced', 'min_synergy_0.2']
        }
    ]
    
    validation_requests = [
        {
            'design_id': 'design_1',
            'design': experiment_designs[0]
        },
        {
            'design_id': 'design_2',
            'design': experiment_designs[1]
        }
    ]
    
    # Process experiment grammar analysis
    results = await grammar_system.process_experiment_grammar_analysis(experiment_designs, validation_requests)
    
    print("Advanced Experiment Grammar Analysis Results:")
    print(f"Grammar Analyses: {len(results['grammar_analyses'])}")
    print(f"Validation Results: {len(results['validation_results'])}")
    print(f"Template Generations: {len(results['template_generations'])}")
    print(f"Compliance Updates: {len(results['compliance_updates'])}")


if __name__ == "__main__":
    asyncio.run(main())
