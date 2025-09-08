"""
CIL-HypothesisWriter: LLM Counterfactuals & Experiment Shapes

Role: Writes crisp hypotheses + test shapes for Orchestrator to register/assign.
- Drafts counterfactuals ("remove volume → does divergence still predict?")
- Ensures tests are comparable via the small Experiment Grammar
- Creates hypotheses labeled as Durability / Stack / Lead-Lag / Ablation / Boundary

Think: the LLM that generates testable hypotheses and experiment designs.
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient
from src.llm_integration.prompt_manager import PromptManager
from src.llm_integration.database_driven_context_system import DatabaseDrivenContextSystem


class ExperimentShape(Enum):
    """Experiment shape types"""
    DURABILITY = "durability"
    STACK = "stack"
    LEAD_LAG = "lead_lag"
    ABLATION = "ablation"
    BOUNDARY = "boundary"


@dataclass
class Hypothesis:
    """Hypothesis data structure"""
    hypothesis_id: str
    hypothesis_text: str
    shape: ExperimentShape
    success_metric: str
    min_samples: int
    ttl_hours: int
    lesson_keys: List[str]
    counterfactuals: List[str]
    context: Dict[str, Any]
    confidence: float
    created_at: datetime
    status: str  # pending, active, completed, failed


@dataclass
class Counterfactual:
    """Counterfactual data structure"""
    counterfactual_id: str
    hypothesis_id: str
    counterfactual_text: str
    test_type: str  # ablation, boundary, control
    expected_outcome: str
    test_parameters: Dict[str, Any]
    created_at: datetime


class CILHypothesisWriter:
    """
    CIL-HypothesisWriter: LLM Counterfactuals & Experiment Shapes
    
    Responsibilities:
    - Writes crisp hypotheses + test shapes
    - Drafts counterfactuals for causal testing
    - Ensures tests are comparable via Experiment Grammar
    - Creates hypotheses for all 5 canonical shapes
    """
    
    def __init__(self, supabase_manager: SupabaseManager, llm_client: OpenRouterClient):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.prompt_manager = PromptManager()
        self.context_system = DatabaseDrivenContextSystem(supabase_manager)
        
        # Hypothesis Management
        self.active_hypotheses: Dict[str, Hypothesis] = {}
        self.completed_hypotheses: Dict[str, Hypothesis] = {}
        self.counterfactuals: Dict[str, Counterfactual] = {}
        
        # Writing Configuration
        self.hypothesis_generation_interval_minutes = 20
        self.min_confidence_for_hypothesis = 0.6
        self.max_hypotheses_per_cycle = 5
        
    async def initialize(self):
        """Initialize the hypothesis writer"""
        try:
            # Load existing hypotheses
            await self._load_existing_hypotheses()
            
            # Start hypothesis writing loop
            asyncio.create_task(self._hypothesis_writing_loop())
            
            print("✅ CIL-HypothesisWriter initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ CIL-HypothesisWriter initialization failed: {e}")
            return False
    
    async def _hypothesis_writing_loop(self):
        """Main hypothesis writing loop"""
        while True:
            try:
                # Check for new patterns that need hypotheses
                await self._check_for_new_patterns()
                
                # Generate new hypotheses
                await self._generate_new_hypotheses()
                
                # Create counterfactuals for existing hypotheses
                await self._create_counterfactuals()
                
                # Update hypothesis statuses
                await self._update_hypothesis_statuses()
                
                # Wait before next iteration
                await asyncio.sleep(self.hypothesis_generation_interval_minutes * 60)
                
            except Exception as e:
                print(f"Error in hypothesis writing loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _check_for_new_patterns(self):
        """Check for new patterns that need hypotheses"""
        try:
            # Query for recent patterns without hypotheses
            query = """
                SELECT * FROM AD_strands 
                WHERE kind IN ('motif', 'confluence_event', 'meta_signal')
                    AND confidence >= %s
                    AND created_at > NOW() - INTERVAL '2 hours'
                    AND id NOT IN (
                        SELECT DISTINCT hypothesis_id FROM AD_strands 
                        WHERE kind = 'hypothesis'
                    )
                ORDER BY confidence DESC, created_at DESC
                LIMIT %s
            """
            
            result = await self.supabase_manager.execute_query(query, [self.min_confidence_for_hypothesis, self.max_hypotheses_per_cycle])
            
            if result:
                print(f"✅ Found {len(result)} new patterns needing hypotheses")
                return result
            
            return []
            
        except Exception as e:
            print(f"Error checking for new patterns: {e}")
            return []
    
    async def _generate_new_hypotheses(self):
        """Generate new hypotheses from patterns"""
        try:
            # Get new patterns
            new_patterns = await self._check_for_new_patterns()
            
            for pattern in new_patterns:
                # Generate hypothesis for this pattern
                hypothesis = await self._create_hypothesis_from_pattern(pattern)
                
                if hypothesis:
                    self.active_hypotheses[hypothesis.hypothesis_id] = hypothesis
                    await self._publish_hypothesis(hypothesis)
                    
        except Exception as e:
            print(f"Error generating new hypotheses: {e}")
    
    async def _create_hypothesis_from_pattern(self, pattern: Dict[str, Any]) -> Optional[Hypothesis]:
        """Create hypothesis from pattern using LLM"""
        try:
            # Determine experiment shape based on pattern type
            shape = await self._determine_experiment_shape(pattern)
            
            # Generate hypothesis using LLM
            prompt = f"""
            Create a testable hypothesis for this pattern:
            
            Pattern: {json.dumps(pattern, indent=2)}
            
            Experiment Shape: {shape.value}
            
            Generate a hypothesis that:
            1. Is specific and testable
            2. Relates to the pattern
            3. Can be validated with measurable criteria
            4. Is relevant to alpha detection
            5. Follows the {shape.value} experiment shape
            
            Also provide:
            - Success metric (what to measure)
            - Minimum samples needed
            - TTL in hours
            - Lesson keys (what to learn)
            
            Return as JSON format:
            {{
                "hypothesis_text": "clear, testable hypothesis",
                "success_metric": "what to measure",
                "min_samples": 100,
                "ttl_hours": 24,
                "lesson_keys": ["lesson1", "lesson2"],
                "context": {{"pattern_type": "motif", "confidence": 0.8}}
            }}
            """
            
            response = await self.llm_client.generate_response(
                prompt=prompt,
                model="anthropic/claude-3.5-sonnet",
                max_tokens=500,
                temperature=0.3
            )
            
            # Parse response and create hypothesis
            try:
                hypothesis_data = json.loads(response)
                
                hypothesis_id = f"hyp_{pattern['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                hypothesis = Hypothesis(
                    hypothesis_id=hypothesis_id,
                    hypothesis_text=hypothesis_data.get('hypothesis_text', ''),
                    shape=shape,
                    success_metric=hypothesis_data.get('success_metric', ''),
                    min_samples=hypothesis_data.get('min_samples', 100),
                    ttl_hours=hypothesis_data.get('ttl_hours', 24),
                    lesson_keys=hypothesis_data.get('lesson_keys', []),
                    counterfactuals=[],
                    context=hypothesis_data.get('context', {}),
                    confidence=pattern.get('confidence', 0.0),
                    created_at=datetime.now(timezone.utc),
                    status='pending'
                )
                
                return hypothesis
                
            except json.JSONDecodeError:
                print(f"Failed to parse LLM response for hypothesis: {response}")
                return None
                
        except Exception as e:
            print(f"Error creating hypothesis from pattern: {e}")
            return None
    
    async def _determine_experiment_shape(self, pattern: Dict[str, Any]) -> ExperimentShape:
        """Determine experiment shape based on pattern type"""
        try:
            pattern_type = pattern.get('kind', '')
            confidence = pattern.get('confidence', 0.0)
            
            if pattern_type == 'motif':
                # Motifs often need durability testing
                return ExperimentShape.DURABILITY
            elif pattern_type == 'confluence_event':
                # Confluence events need stack testing
                return ExperimentShape.STACK
            elif pattern_type == 'meta_signal':
                # Meta-signals might need lead-lag testing
                return ExperimentShape.LEAD_LAG
            else:
                # Default to boundary testing for unknown patterns
                return ExperimentShape.BOUNDARY
                
        except Exception as e:
            print(f"Error determining experiment shape: {e}")
            return ExperimentShape.DURABILITY
    
    async def _create_counterfactuals(self):
        """Create counterfactuals for existing hypotheses"""
        try:
            for hypothesis_id, hypothesis in self.active_hypotheses.items():
                if not hypothesis.counterfactuals:
                    # Generate counterfactuals for this hypothesis
                    counterfactuals = await self._generate_counterfactuals(hypothesis)
                    
                    if counterfactuals:
                        hypothesis.counterfactuals = [cf.counterfactual_id for cf in counterfactuals]
                        
                        # Store counterfactuals
                        for cf in counterfactuals:
                            self.counterfactuals[cf.counterfactual_id] = cf
                            
        except Exception as e:
            print(f"Error creating counterfactuals: {e}")
    
    async def _generate_counterfactuals(self, hypothesis: Hypothesis) -> List[Counterfactual]:
        """Generate counterfactuals for a hypothesis using LLM"""
        try:
            # Generate counterfactuals using LLM
            prompt = f"""
            Create counterfactuals for this hypothesis:
            
            Hypothesis: {hypothesis.hypothesis_text}
            Shape: {hypothesis.shape.value}
            Success Metric: {hypothesis.success_metric}
            
            Generate 2-3 counterfactuals that test:
            1. What happens if we remove key components? (ablation)
            2. What happens at the boundaries? (boundary)
            3. What happens in control conditions? (control)
            
            Each counterfactual should:
            - Be specific and testable
            - Have a clear expected outcome
            - Include test parameters
            
            Return as JSON array:
            [
                {{
                    "counterfactual_text": "what if we remove X?",
                    "test_type": "ablation",
                    "expected_outcome": "hypothesis should fail",
                    "test_parameters": {{"remove_component": "X", "measure": "Y"}}
                }},
                ...
            ]
            """
            
            response = await self.llm_client.generate_response(
                prompt=prompt,
                model="anthropic/claude-3.5-sonnet",
                max_tokens=800,
                temperature=0.4
            )
            
            # Parse response and create counterfactuals
            try:
                counterfactuals_data = json.loads(response)
                
                counterfactuals = []
                for i, cf_data in enumerate(counterfactuals_data):
                    counterfactual_id = f"cf_{hypothesis.hypothesis_id}_{i}"
                    
                    counterfactual = Counterfactual(
                        counterfactual_id=counterfactual_id,
                        hypothesis_id=hypothesis.hypothesis_id,
                        counterfactual_text=cf_data.get('counterfactual_text', ''),
                        test_type=cf_data.get('test_type', 'ablation'),
                        expected_outcome=cf_data.get('expected_outcome', ''),
                        test_parameters=cf_data.get('test_parameters', {}),
                        created_at=datetime.now(timezone.utc)
                    )
                    
                    counterfactuals.append(counterfactual)
                
                return counterfactuals
                
            except json.JSONDecodeError:
                print(f"Failed to parse LLM response for counterfactuals: {response}")
                return []
                
        except Exception as e:
            print(f"Error generating counterfactuals: {e}")
            return []
    
    async def _update_hypothesis_statuses(self):
        """Update hypothesis statuses from database"""
        try:
            # Query for updated hypothesis statuses
            query = """
                SELECT hypothesis_id, status, results, completed_at 
                FROM AD_strands 
                WHERE kind = 'hypothesis' 
                AND hypothesis_id IN ({})
            """.format(','.join([f"'{hyp_id}'" for hyp_id in self.active_hypotheses.keys()]))
            
            result = await self.supabase_manager.execute_query(query)
            
            for row in result:
                hypothesis_id = row['hypothesis_id']
                if hypothesis_id in self.active_hypotheses:
                    hypothesis = self.active_hypotheses[hypothesis_id]
                    hypothesis.status = row['status']
                    
                    # Move completed hypotheses
                    if hypothesis.status in ['completed', 'failed']:
                        self.completed_hypotheses[hypothesis_id] = hypothesis
                        del self.active_hypotheses[hypothesis_id]
                        
        except Exception as e:
            print(f"Error updating hypothesis statuses: {e}")
    
    async def _publish_hypothesis(self, hypothesis: Hypothesis):
        """Publish hypothesis to database"""
        try:
            strand_data = {
                'kind': 'hypothesis',
                'module': 'alpha',
                'tags': [f"agent:central_intelligence:hypothesis_writer:hypothesis_created"],
                'hypothesis_id': hypothesis.hypothesis_id,
                'hypothesis_text': hypothesis.hypothesis_text,
                'experiment_shape': hypothesis.shape.value,
                'success_metric': hypothesis.success_metric,
                'min_samples': hypothesis.min_samples,
                'ttl_hours': hypothesis.ttl_hours,
                'lesson_keys': hypothesis.lesson_keys,
                'counterfactuals': hypothesis.counterfactuals,
                'context': hypothesis.context,
                'confidence': hypothesis.confidence,
                'status': hypothesis.status,
                'cil_team_member': 'hypothesis_writer'
            }
            
            await self.supabase_manager.insert_strand(strand_data)
            
            print(f"✅ Published hypothesis {hypothesis.hypothesis_id}")
            
        except Exception as e:
            print(f"Error publishing hypothesis: {e}")
    
    async def _load_existing_hypotheses(self):
        """Load existing hypotheses from database"""
        try:
            query = """
                SELECT * FROM AD_strands 
                WHERE kind = 'hypothesis' 
                ORDER BY created_at DESC
            """
            
            result = await self.supabase_manager.execute_query(query)
            
            for row in result:
                hypothesis = Hypothesis(
                    hypothesis_id=row['hypothesis_id'],
                    hypothesis_text=row.get('hypothesis_text', ''),
                    shape=ExperimentShape(row.get('experiment_shape', 'durability')),
                    success_metric=row.get('success_metric', ''),
                    min_samples=row.get('min_samples', 100),
                    ttl_hours=row.get('ttl_hours', 24),
                    lesson_keys=row.get('lesson_keys', []),
                    counterfactuals=row.get('counterfactuals', []),
                    context=row.get('context', {}),
                    confidence=row.get('confidence', 0.0),
                    created_at=row['created_at'],
                    status=row.get('status', 'pending')
                )
                
                if hypothesis.status in ['pending', 'active']:
                    self.active_hypotheses[hypothesis.hypothesis_id] = hypothesis
                else:
                    self.completed_hypotheses[hypothesis.hypothesis_id] = hypothesis
                    
        except Exception as e:
            print(f"Warning: Could not load existing hypotheses: {e}")
    
    async def get_hypothesis_writing_status(self) -> Dict[str, Any]:
        """Get current hypothesis writing status"""
        return {
            'active_hypotheses_count': len(self.active_hypotheses),
            'completed_hypotheses_count': len(self.completed_hypotheses),
            'counterfactuals_count': len(self.counterfactuals),
            'hypothesis_generation_interval_minutes': self.hypothesis_generation_interval_minutes,
            'min_confidence_for_hypothesis': self.min_confidence_for_hypothesis,
            'max_hypotheses_per_cycle': self.max_hypotheses_per_cycle
        }
    
    async def create_manual_hypothesis(self, hypothesis_text: str, shape: str, 
                                     success_metric: str, min_samples: int = 100) -> str:
        """Create a manual hypothesis"""
        try:
            hypothesis_id = f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            hypothesis = Hypothesis(
                hypothesis_id=hypothesis_id,
                hypothesis_text=hypothesis_text,
                shape=ExperimentShape(shape),
                success_metric=success_metric,
                min_samples=min_samples,
                ttl_hours=24,
                lesson_keys=[],
                counterfactuals=[],
                context={'manual': True, 'created_by': 'user'},
                confidence=0.8,  # High confidence for manual hypotheses
                created_at=datetime.now(timezone.utc),
                status='pending'
            )
            
            # Add to active hypotheses
            self.active_hypotheses[hypothesis_id] = hypothesis
            
            # Publish hypothesis
            await self._publish_hypothesis(hypothesis)
            
            print(f"✅ Created manual hypothesis {hypothesis_id}")
            return hypothesis_id
            
        except Exception as e:
            print(f"Error creating manual hypothesis: {e}")
            return None

