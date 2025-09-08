"""
Test CIL Advanced Experiment Grammar System
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.intelligence.system_control.central_intelligence_layer.missing_pieces.advanced_experiment_grammar_system import (
    AdvancedExperimentGrammarSystem, ExperimentShape, ExperimentComplexity, ValidationStatus,
    ExperimentPhase, ExperimentGrammar, ExperimentTemplate, ExperimentDesign, ExperimentValidation
)


class TestAdvancedExperimentGrammarSystem:
    """Test CIL Advanced Experiment Grammar System"""
    
    @pytest.fixture
    def mock_supabase_manager(self):
        """Mock SupabaseManager"""
        manager = Mock()
        manager.execute_query = AsyncMock()
        manager.insert_strand = AsyncMock()
        return manager
    
    @pytest.fixture
    def mock_llm_client(self):
        """Mock OpenRouterClient"""
        return Mock()
    
    @pytest.fixture
    def grammar_system(self, mock_supabase_manager, mock_llm_client):
        """Create AdvancedExperimentGrammarSystem instance"""
        return AdvancedExperimentGrammarSystem(mock_supabase_manager, mock_llm_client)
    
    @pytest.fixture
    def mock_experiment_designs(self):
        """Mock experiment designs"""
        return [
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
            },
            {
                'design_id': 'design_3',
                'experiment_shape': 'lead_lag',
                'complexity_level': 'advanced',
                'design_structure': {
                    'hypothesis': 'Volume spike leads price movement by 30 seconds',
                    'methodology': 'Temporal correlation analysis',
                    'variables': ['volume_spike', 'price_movement', 'time_offset'],
                    'controls': ['baseline_correlation', 'noise_level']
                },
                'requirements': ['temporal_analysis', 'lag_metrics'],
                'context': {'market_regime': 'trending', 'session': 'ASIA'},
                'constraints': ['max_lag_60s', 'min_correlation_0.7']
            }
        ]
    
    @pytest.fixture
    def mock_validation_requests(self, mock_experiment_designs):
        """Mock validation requests"""
        return [
            {
                'design_id': 'design_1',
                'design': mock_experiment_designs[0]
            },
            {
                'design_id': 'design_2',
                'design': mock_experiment_designs[1]
            },
            {
                'design_id': 'design_3',
                'design': mock_experiment_designs[2]
            }
        ]
    
    def test_grammar_system_initialization(self, grammar_system):
        """Test AdvancedExperimentGrammarSystem initialization"""
        assert grammar_system.supabase_manager is not None
        assert grammar_system.llm_client is not None
        assert grammar_system.validation_threshold == 0.8
        assert grammar_system.grammar_compliance_threshold == 0.7
        assert grammar_system.design_quality_threshold == 0.6
        assert grammar_system.max_experiment_duration_hours == 24
        assert grammar_system.min_sample_size == 10
        assert grammar_system.grammar_analysis_prompt is not None
        assert grammar_system.validation_prompt is not None
        assert grammar_system.template_generation_prompt is not None
        assert isinstance(grammar_system.experiment_grammars, dict)
        assert isinstance(grammar_system.experiment_templates, dict)
        assert isinstance(grammar_system.active_designs, dict)
        assert isinstance(grammar_system.validation_history, list)
        assert len(grammar_system.experiment_grammars) == 5  # Should have 5 canonical shapes
        assert len(grammar_system.experiment_templates) == 2  # Should have 2 default templates
    
    def test_load_prompt_templates(self, grammar_system):
        """Test prompt template loading"""
        # Test grammar analysis prompt
        assert 'experiment_shape' in grammar_system.grammar_analysis_prompt
        assert 'complexity_level' in grammar_system.grammar_analysis_prompt
        assert 'design_structure' in grammar_system.grammar_analysis_prompt
        assert 'requirements' in grammar_system.grammar_analysis_prompt
        assert 'grammar_rules' in grammar_system.grammar_analysis_prompt
        
        # Test validation prompt
        assert 'experiment_shape' in grammar_system.validation_prompt
        assert 'design_structure' in grammar_system.validation_prompt
        assert 'validation_criteria' in grammar_system.validation_prompt
        
        # Test template generation prompt
        assert 'experiment_shape' in grammar_system.template_generation_prompt
        assert 'complexity_level' in grammar_system.template_generation_prompt
        assert 'context' in grammar_system.template_generation_prompt
        assert 'constraints' in grammar_system.template_generation_prompt
    
    def test_initialize_experiment_grammars(self, grammar_system):
        """Test experiment grammars initialization"""
        grammars = grammar_system.experiment_grammars
        
        assert len(grammars) == 5
        
        # Check specific grammars
        durability_grammar = grammars['durability_grammar']
        assert durability_grammar.experiment_shape == ExperimentShape.DURABILITY
        assert durability_grammar.complexity_level == ExperimentComplexity.MODERATE
        assert 'time_series_required' in durability_grammar.grammar_rules
        assert 'persistence_metrics' in durability_grammar.grammar_rules
        assert 'control_conditions' in durability_grammar.grammar_rules
        assert 'success_criteria' in durability_grammar.grammar_rules
        assert len(durability_grammar.validation_criteria) > 0
        assert len(durability_grammar.success_metrics) > 0
        assert len(durability_grammar.failure_conditions) > 0
        
        stack_grammar = grammars['stack_grammar']
        assert stack_grammar.experiment_shape == ExperimentShape.STACK
        assert stack_grammar.complexity_level == ExperimentComplexity.COMPLEX
        assert 'multiple_patterns_required' in stack_grammar.grammar_rules
        assert 'interaction_metrics' in stack_grammar.grammar_rules
        assert 'combination_rules' in stack_grammar.grammar_rules
        
        lead_lag_grammar = grammars['lead_lag_grammar']
        assert lead_lag_grammar.experiment_shape == ExperimentShape.LEAD_LAG
        assert lead_lag_grammar.complexity_level == ExperimentComplexity.ADVANCED
        assert 'temporal_analysis_required' in lead_lag_grammar.grammar_rules
        assert 'lag_metrics' in lead_lag_grammar.grammar_rules
        assert 'temporal_conditions' in lead_lag_grammar.grammar_rules
        
        ablation_grammar = grammars['ablation_grammar']
        assert ablation_grammar.experiment_shape == ExperimentShape.ABLATION
        assert ablation_grammar.complexity_level == ExperimentComplexity.MODERATE
        assert 'component_removal_required' in ablation_grammar.grammar_rules
        assert 'ablation_metrics' in ablation_grammar.grammar_rules
        assert 'removal_conditions' in ablation_grammar.grammar_rules
        
        boundary_grammar = grammars['boundary_grammar']
        assert boundary_grammar.experiment_shape == ExperimentShape.BOUNDARY
        assert boundary_grammar.complexity_level == ExperimentComplexity.SIMPLE
        assert 'limit_testing_required' in boundary_grammar.grammar_rules
        assert 'boundary_metrics' in boundary_grammar.grammar_rules
        assert 'limit_conditions' in boundary_grammar.grammar_rules
    
    def test_initialize_experiment_templates(self, grammar_system):
        """Test experiment templates initialization"""
        templates = grammar_system.experiment_templates
        
        assert len(templates) == 2
        
        # Check durability template
        durability_template = templates['durability_template']
        assert durability_template.experiment_shape == ExperimentShape.DURABILITY
        assert durability_template.complexity_level == ExperimentComplexity.MODERATE
        assert durability_template.template_name == "Pattern Durability Test"
        assert 'hypothesis' in durability_template.template_structure
        assert 'methodology' in durability_template.template_structure
        assert 'variables' in durability_template.template_structure
        assert 'controls' in durability_template.template_structure
        assert 'metrics' in durability_template.template_structure
        assert len(durability_template.required_fields) > 0
        assert len(durability_template.optional_fields) > 0
        assert len(durability_template.default_values) > 0
        assert len(durability_template.validation_rules) > 0
        
        # Check stack template
        stack_template = templates['stack_template']
        assert stack_template.experiment_shape == ExperimentShape.STACK
        assert stack_template.complexity_level == ExperimentComplexity.COMPLEX
        assert stack_template.template_name == "Pattern Stack Analysis"
        assert 'hypothesis' in stack_template.template_structure
        assert 'methodology' in stack_template.template_structure
        assert 'variables' in stack_template.template_structure
        assert 'controls' in stack_template.template_structure
        assert 'metrics' in stack_template.template_structure
        assert len(stack_template.required_fields) > 0
        assert len(stack_template.optional_fields) > 0
        assert len(stack_template.default_values) > 0
        assert len(stack_template.validation_rules) > 0
    
    @pytest.mark.asyncio
    async def test_process_experiment_grammar_analysis_success(self, grammar_system, mock_experiment_designs, mock_validation_requests):
        """Test successful experiment grammar analysis processing"""
        # Process experiment grammar analysis
        results = await grammar_system.process_experiment_grammar_analysis(mock_experiment_designs, mock_validation_requests)
        
        # Verify structure
        assert 'grammar_analyses' in results
        assert 'validation_results' in results
        assert 'template_generations' in results
        assert 'compliance_updates' in results
        assert 'grammar_timestamp' in results
        assert 'grammar_errors' in results
        
        # Verify processing timestamp
        assert isinstance(results['grammar_timestamp'], datetime)
        
        # Verify results are correct types
        assert isinstance(results['grammar_analyses'], list)
        assert isinstance(results['validation_results'], list)
        assert isinstance(results['template_generations'], list)
        assert isinstance(results['compliance_updates'], list)
        assert isinstance(results['grammar_errors'], list)
    
    @pytest.mark.asyncio
    async def test_analyze_experiment_designs(self, grammar_system, mock_experiment_designs):
        """Test experiment design analysis"""
        # Analyze experiment designs
        analyses = await grammar_system._analyze_experiment_designs(mock_experiment_designs)
        
        # Verify results
        assert isinstance(analyses, list)
        assert len(analyses) == 3  # Should analyze all 3 designs
        
        # Check analysis structure
        for analysis in analyses:
            assert 'design_id' in analysis
            assert 'experiment_shape' in analysis
            assert 'complexity_level' in analysis
            assert 'grammar_compliance' in analysis
            assert 'design_quality' in analysis
            assert 'compliance_issues' in analysis
            assert 'quality_issues' in analysis
            assert 'recommendations' in analysis
            assert 'validation_score' in analysis
            assert 'uncertainty_flags' in analysis
            
            # Verify specific values
            assert analysis['design_id'] in ['design_1', 'design_2', 'design_3']
            assert analysis['experiment_shape'] in ['durability', 'stack', 'lead_lag']
            assert analysis['complexity_level'] in ['moderate', 'complex', 'advanced']
            assert 0.0 <= analysis['grammar_compliance'] <= 1.0
            assert 0.0 <= analysis['design_quality'] <= 1.0
            assert 0.0 <= analysis['validation_score'] <= 1.0
            assert isinstance(analysis['compliance_issues'], list)
            assert isinstance(analysis['quality_issues'], list)
            assert isinstance(analysis['recommendations'], list)
            assert isinstance(analysis['uncertainty_flags'], list)
    
    def test_get_grammar_for_shape(self, grammar_system):
        """Test getting grammar for experiment shape"""
        # Test durability grammar
        durability_grammar = grammar_system._get_grammar_for_shape(ExperimentShape.DURABILITY)
        assert durability_grammar is not None
        assert durability_grammar.experiment_shape == ExperimentShape.DURABILITY
        assert durability_grammar.complexity_level == ExperimentComplexity.MODERATE
        
        # Test stack grammar
        stack_grammar = grammar_system._get_grammar_for_shape(ExperimentShape.STACK)
        assert stack_grammar is not None
        assert stack_grammar.experiment_shape == ExperimentShape.STACK
        assert stack_grammar.complexity_level == ExperimentComplexity.COMPLEX
        
        # Test lead-lag grammar
        lead_lag_grammar = grammar_system._get_grammar_for_shape(ExperimentShape.LEAD_LAG)
        assert lead_lag_grammar is not None
        assert lead_lag_grammar.experiment_shape == ExperimentShape.LEAD_LAG
        assert lead_lag_grammar.complexity_level == ExperimentComplexity.ADVANCED
        
        # Test ablation grammar
        ablation_grammar = grammar_system._get_grammar_for_shape(ExperimentShape.ABLATION)
        assert ablation_grammar is not None
        assert ablation_grammar.experiment_shape == ExperimentShape.ABLATION
        assert ablation_grammar.complexity_level == ExperimentComplexity.MODERATE
        
        # Test boundary grammar
        boundary_grammar = grammar_system._get_grammar_for_shape(ExperimentShape.BOUNDARY)
        assert boundary_grammar is not None
        assert boundary_grammar.experiment_shape == ExperimentShape.BOUNDARY
        assert boundary_grammar.complexity_level == ExperimentComplexity.SIMPLE
    
    @pytest.mark.asyncio
    async def test_generate_grammar_analysis(self, grammar_system, mock_experiment_designs):
        """Test grammar analysis generation"""
        design = mock_experiment_designs[0]  # Durability design
        grammar = grammar_system._get_grammar_for_shape(ExperimentShape.DURABILITY)
        
        # Generate grammar analysis
        analysis = await grammar_system._generate_grammar_analysis(design, grammar)
        
        # Verify analysis
        assert analysis is not None
        assert isinstance(analysis, dict)
        assert 'grammar_compliance' in analysis
        assert 'design_quality' in analysis
        assert 'compliance_issues' in analysis
        assert 'quality_issues' in analysis
        assert 'recommendations' in analysis
        assert 'validation_score' in analysis
        assert 'uncertainty_flags' in analysis
        
        # Verify specific values
        assert analysis['grammar_compliance'] == 0.85
        assert analysis['design_quality'] == 0.78
        assert analysis['compliance_issues'] == ['missing_control_conditions', 'undefined_success_criteria']
        assert analysis['quality_issues'] == ['insufficient_sample_size', 'unclear_methodology']
        assert analysis['recommendations'] == ['add_control_conditions', 'define_success_criteria', 'increase_sample_size']
        assert analysis['validation_score'] == 0.82
        assert analysis['uncertainty_flags'] == ['limited_historical_data']
    
    @pytest.mark.asyncio
    async def test_validate_experiment_designs(self, grammar_system, mock_validation_requests):
        """Test experiment design validation"""
        # Validate experiment designs
        validations = await grammar_system._validate_experiment_designs(mock_validation_requests)
        
        # Verify results
        assert isinstance(validations, list)
        assert len(validations) == 3  # Should validate all 3 designs
        
        # Check validation structure
        for validation in validations:
            assert isinstance(validation, ExperimentValidation)
            assert validation.validation_id.startswith('VALIDATION_')
            assert validation.design_id in ['design_1', 'design_2', 'design_3']
            assert isinstance(validation.validation_status, ValidationStatus)
            assert 0.0 <= validation.validation_score <= 1.0
            assert isinstance(validation.compliance_issues, list)
            assert isinstance(validation.quality_issues, list)
            assert isinstance(validation.recommendations, list)
            assert isinstance(validation.validation_details, dict)
            assert isinstance(validation.created_at, datetime)
            
            # Verify specific values
            assert validation.validation_status == ValidationStatus.VALIDATED
            assert validation.validation_score == 0.88
            assert validation.compliance_issues == []
            assert validation.recommendations == ['monitor_execution', 'adjust_parameters']
        
        # Verify validation history was updated
        assert len(grammar_system.validation_history) == 3
    
    @pytest.mark.asyncio
    async def test_generate_validation_analysis(self, grammar_system, mock_experiment_designs):
        """Test validation analysis generation"""
        design = mock_experiment_designs[0]  # Durability design
        
        # Generate validation analysis
        validation = await grammar_system._generate_validation_analysis(design)
        
        # Verify validation
        assert validation is not None
        assert isinstance(validation, dict)
        assert 'validation_status' in validation
        assert 'validation_score' in validation
        assert 'shape_appropriateness' in validation
        assert 'structure_completeness' in validation
        assert 'criteria_compliance' in validation
        assert 'issues' in validation
        assert 'recommendations' in validation
        
        # Verify specific values
        assert validation['validation_status'] == 'validated'
        assert validation['validation_score'] == 0.88
        assert validation['shape_appropriateness'] == 0.9
        assert validation['structure_completeness'] == 0.85
        assert validation['criteria_compliance'] == 0.88
        assert validation['issues'] == []
        assert validation['recommendations'] == ['monitor_execution', 'adjust_parameters']
    
    @pytest.mark.asyncio
    async def test_generate_experiment_templates(self, grammar_system, mock_experiment_designs):
        """Test experiment template generation"""
        # Generate experiment templates
        template_generations = await grammar_system._generate_experiment_templates(mock_experiment_designs)
        
        # Verify results
        assert isinstance(template_generations, list)
        # Should generate templates for lead_lag (not already existing)
        assert len(template_generations) >= 1
        
        # Check template generation structure
        for template in template_generations:
            assert 'template_id' in template
            assert 'experiment_shape' in template
            assert 'complexity_level' in template
            assert 'template_structure' in template
            assert 'required_fields' in template
            assert 'optional_fields' in template
            assert 'default_values' in template
            assert 'validation_rules' in template
            assert 'template_quality' in template
            
            # Verify specific values
            assert template['template_id'].startswith('TEMPLATE_')
            assert template['experiment_shape'] in ['durability', 'stack', 'lead_lag', 'ablation', 'boundary']
            assert template['complexity_level'] in ['simple', 'moderate', 'complex', 'advanced']
            assert isinstance(template['template_structure'], dict)
            assert isinstance(template['required_fields'], list)
            assert isinstance(template['optional_fields'], list)
            assert isinstance(template['default_values'], dict)
            assert isinstance(template['validation_rules'], list)
            assert 0.0 <= template['template_quality'] <= 1.0
    
    @pytest.mark.asyncio
    async def test_generate_template(self, grammar_system, mock_experiment_designs):
        """Test template generation"""
        design = mock_experiment_designs[2]  # Lead-lag design
        
        # Generate template
        template = await grammar_system._generate_template(
            ExperimentShape.LEAD_LAG, ExperimentComplexity.ADVANCED, design
        )
        
        # Verify template
        assert template is not None
        assert isinstance(template, dict)
        assert 'template_structure' in template
        assert 'required_fields' in template
        assert 'optional_fields' in template
        assert 'default_values' in template
        assert 'validation_rules' in template
        assert 'template_quality' in template
        
        # Verify specific values
        assert isinstance(template['template_structure'], dict)
        assert 'hypothesis' in template['template_structure']
        assert 'methodology' in template['template_structure']
        assert 'variables' in template['template_structure']
        assert 'controls' in template['template_structure']
        assert 'metrics' in template['template_structure']
        assert isinstance(template['required_fields'], list)
        assert 'hypothesis' in template['required_fields']
        assert 'methodology' in template['required_fields']
        assert 'variables' in template['required_fields']
        assert isinstance(template['optional_fields'], list)
        assert 'assumptions' in template['optional_fields']
        assert 'limitations' in template['optional_fields']
        assert isinstance(template['default_values'], dict)
        assert 'default1' in template['default_values']
        assert 'default2' in template['default_values']
        assert isinstance(template['validation_rules'], list)
        assert len(template['validation_rules']) == 3
        assert template['template_quality'] == 0.85
    
    @pytest.mark.asyncio
    async def test_update_grammar_compliance(self, grammar_system):
        """Test grammar compliance updates"""
        # Mock grammar analyses
        grammar_analyses = [
            {
                'design_id': 'design_1',
                'experiment_shape': 'durability',
                'grammar_compliance': 0.85,
                'design_quality': 0.78,
                'validation_score': 0.82,
                'compliance_issues': ['issue1', 'issue2'],
                'quality_issues': ['quality1'],
                'recommendations': ['rec1', 'rec2', 'rec3']
            },
            {
                'design_id': 'design_2',
                'experiment_shape': 'stack',
                'grammar_compliance': 0.92,
                'design_quality': 0.88,
                'validation_score': 0.90,
                'compliance_issues': ['issue3'],
                'quality_issues': ['quality2', 'quality3'],
                'recommendations': ['rec4', 'rec5']
            }
        ]
        
        # Update grammar compliance
        compliance_updates = await grammar_system._update_grammar_compliance(grammar_analyses)
        
        # Verify results
        assert isinstance(compliance_updates, list)
        assert len(compliance_updates) == 2
        
        # Check compliance update structure
        for update in compliance_updates:
            assert 'design_id' in update
            assert 'experiment_shape' in update
            assert 'grammar_compliance' in update
            assert 'design_quality' in update
            assert 'validation_score' in update
            assert 'compliance_issues_count' in update
            assert 'quality_issues_count' in update
            assert 'recommendations_count' in update
            assert 'updated_at' in update
            
            # Verify specific values
            assert update['design_id'] in ['design_1', 'design_2']
            assert update['experiment_shape'] in ['durability', 'stack']
            assert 0.0 <= update['grammar_compliance'] <= 1.0
            assert 0.0 <= update['design_quality'] <= 1.0
            assert 0.0 <= update['validation_score'] <= 1.0
            assert update['compliance_issues_count'] >= 0
            assert update['quality_issues_count'] >= 0
            assert update['recommendations_count'] >= 0
            assert isinstance(update['updated_at'], str)
    
    @pytest.mark.asyncio
    async def test_generate_llm_analysis(self, grammar_system):
        """Test LLM analysis generation"""
        prompt_template = "Test grammar_compliance prompt with {test_field}"
        data = {'test_field': 'test_value'}
        
        # Generate LLM analysis
        analysis = await grammar_system._generate_llm_analysis(prompt_template, data)
        
        # Verify analysis
        assert analysis is not None
        assert isinstance(analysis, dict)
        assert 'grammar_compliance' in analysis
        assert 'design_quality' in analysis
        assert 'compliance_issues' in analysis
        assert 'quality_issues' in analysis
        assert 'recommendations' in analysis
        assert 'validation_score' in analysis
        assert 'uncertainty_flags' in analysis
        
        # Verify specific values
        assert analysis['grammar_compliance'] == 0.85
        assert analysis['design_quality'] == 0.78
        assert analysis['compliance_issues'] == ['missing_control_conditions', 'undefined_success_criteria']
        assert analysis['quality_issues'] == ['insufficient_sample_size', 'unclear_methodology']
        assert analysis['recommendations'] == ['add_control_conditions', 'define_success_criteria', 'increase_sample_size']
        assert analysis['validation_score'] == 0.82
        assert analysis['uncertainty_flags'] == ['limited_historical_data']
    
    @pytest.mark.asyncio
    async def test_publish_grammar_results(self, grammar_system, mock_supabase_manager):
        """Test publishing grammar results"""
        results = {
            'grammar_analyses': [{'analysis_id': 'ANALYSIS_1'}],
            'validation_results': [{'validation_id': 'VALIDATION_1'}],
            'template_generations': [{'template_id': 'TEMPLATE_1'}],
            'compliance_updates': [{'update_id': 'UPDATE_1'}],
            'grammar_timestamp': datetime.now(timezone.utc),
            'grammar_errors': []
        }
        
        await grammar_system._publish_grammar_results(results)
        
        # Verify strand was inserted
        mock_supabase_manager.insert_strand.assert_called_once()
        call_args = mock_supabase_manager.insert_strand.call_args[0][0]
        assert call_args['kind'] == 'cil_experiment_grammar'
        assert call_args['agent_id'] == 'central_intelligence_layer'
        assert call_args['cil_team_member'] == 'advanced_experiment_grammar_system'
        assert call_args['strategic_meta_type'] == 'experiment_grammar_analysis'
        assert call_args['resonance_score'] == 0.9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
