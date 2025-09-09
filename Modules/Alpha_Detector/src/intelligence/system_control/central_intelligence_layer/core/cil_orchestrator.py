"""
CIL-Orchestrator: Agent Manager/Conductor

Role: Owns coordination; does not search patterns itself.
- Maintains Experiment Registry (IDs, hypotheses, TTL, owners)
- Routes what to do next based on cluster deltas & doctrine
- Resolves overlaps, assigns owners, tracks status
- Sets autonomy dials (strict/bounded/exploratory) per external agent
- Ensures every directive has logging/lesson keys

Think: queue manager + policy brain.
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient
from src.llm_integration.prompt_manager import PromptManager
from src.llm_integration.database_driven_context_system import DatabaseDrivenContextSystem


@dataclass
class Experiment:
    """Experiment data structure"""
    exp_id: str
    hypothesis: str
    owner_agent: str
    shape: str  # durability, stack, lead_lag, ablation, boundary
    criteria: Dict[str, Any]
    ttl_hours: int
    status: str  # pending, active, completed, failed, cancelled
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    results: Optional[Dict[str, Any]] = None
    lesson_keys: List[str] = None


@dataclass
class AgentDirective:
    """Directive to send to an agent"""
    directive_id: str
    target_agent: str
    directive_type: str  # experiment_assignment, focus_directive, coordination_request, resource_allocation
    content: Dict[str, Any]
    autonomy_level: str  # strict, bounded, exploratory
    ttl_hours: int
    created_at: datetime
    status: str  # pending, sent, acknowledged, completed, failed
    response_deadline: Optional[datetime] = None


class CILOrchestrator:
    """
    CIL-Orchestrator: Agent Manager/Conductor
    
    Responsibilities:
    - Maintains Experiment Registry
    - Routes directives based on cluster deltas & doctrine
    - Resolves overlaps and assigns owners
    - Sets autonomy dials per agent
    - Ensures logging/lesson keys for all directives
    """
    
    def __init__(self, supabase_manager: SupabaseManager, llm_client: OpenRouterClient):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.prompt_manager = PromptManager()
        self.context_system = DatabaseDrivenContextSystem(supabase_manager)
        
        # Experiment Registry
        self.active_experiments: Dict[str, Experiment] = {}
        self.completed_experiments: Dict[str, Experiment] = {}
        self.pending_directives: Dict[str, AgentDirective] = {}
        
        # Agent Management
        self.agent_autonomy_levels: Dict[str, str] = {
            'raw_data_intelligence': 'bounded',
            'indicator_intelligence': 'bounded', 
            'pattern_intelligence': 'bounded',
            'system_control': 'strict'
        }
        
        # Orchestration State
        self.max_concurrent_experiments = 10
        self.experiment_timeout_hours = 24
        self.directive_timeout_hours = 2
        
    async def initialize(self):
        """Initialize the orchestrator"""
        try:
            # Load existing experiments from database
            await self._load_experiment_registry()
            
            # Load pending directives
            await self._load_pending_directives()
            
            # Start monitoring loop
            asyncio.create_task(self._monitoring_loop())
            
            print("✅ CIL-Orchestrator initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ CIL-Orchestrator initialization failed: {e}")
            return False
    
    async def _load_experiment_registry(self):
        """Load experiment registry from database"""
        try:
            # Query for active experiments
            query = """
                SELECT * FROM AD_strands 
                WHERE kind = 'experiment' 
                AND status IN ('pending', 'active')
                ORDER BY created_at DESC
            """
            
            result = await self.supabase_manager.execute_query(query)
            
            for row in result:
                exp = Experiment(
                    exp_id=row['experiment_id'],
                    hypothesis=row.get('hypothesis', ''),
                    owner_agent=row.get('owner_agent', ''),
                    shape=row.get('experiment_shape', 'durability'),
                    criteria=row.get('experiment_criteria', {}),
                    ttl_hours=row.get('ttl_hours', 24),
                    status=row.get('status', 'pending'),
                    created_at=row['created_at'],
                    started_at=row.get('started_at'),
                    completed_at=row.get('completed_at'),
                    results=row.get('results'),
                    lesson_keys=row.get('lesson_keys', [])
                )
                self.active_experiments[exp.exp_id] = exp
                
        except Exception as e:
            print(f"Warning: Could not load experiment registry: {e}")
    
    async def _load_pending_directives(self):
        """Load pending directives from database"""
        try:
            # Query for pending directives
            query = """
                SELECT * FROM AD_strands 
                WHERE kind = 'directive' 
                AND status = 'pending'
                ORDER BY created_at DESC
            """
            
            result = await self.supabase_manager.execute_query(query)
            
            for row in result:
                directive = AgentDirective(
                    directive_id=row['directive_id'],
                    target_agent=row.get('target_agent', ''),
                    directive_type=row.get('directive_type', ''),
                    content=row.get('directive_content', {}),
                    autonomy_level=row.get('autonomy_level', 'bounded'),
                    ttl_hours=row.get('ttl_hours', 2),
                    created_at=row['created_at'],
                    status=row.get('status', 'pending'),
                    response_deadline=row.get('response_deadline')
                )
                self.pending_directives[directive.directive_id] = directive
                
        except Exception as e:
            print(f"Warning: Could not load pending directives: {e}")
    
    async def _monitoring_loop(self):
        """Main monitoring loop for orchestration"""
        while True:
            try:
                # Check for expired experiments
                await self._check_expired_experiments()
                
                # Check for expired directives
                await self._check_expired_directives()
                
                # Process new cluster deltas
                await self._process_cluster_deltas()
                
                # Update experiment statuses
                await self._update_experiment_statuses()
                
                # Wait before next iteration
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                print(f"Error in orchestrator monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _check_expired_experiments(self):
        """Check for expired experiments and handle them"""
        now = datetime.now(timezone.utc)
        expired_experiments = []
        
        for exp_id, exp in self.active_experiments.items():
            if exp.status == 'active':
                # Check if experiment has exceeded TTL
                if exp.started_at and (now - exp.started_at).total_seconds() > exp.ttl_hours * 3600:
                    expired_experiments.append(exp_id)
        
        # Handle expired experiments
        for exp_id in expired_experiments:
            await self._handle_expired_experiment(exp_id)
    
    async def _check_expired_directives(self):
        """Check for expired directives and handle them"""
        now = datetime.now(timezone.utc)
        expired_directives = []
        
        for directive_id, directive in self.pending_directives.items():
            if directive.status == 'sent':
                # Check if directive has exceeded TTL
                if directive.response_deadline and now > directive.response_deadline:
                    expired_directives.append(directive_id)
        
        # Handle expired directives
        for directive_id in expired_directives:
            await self._handle_expired_directive(directive_id)
    
    async def _process_cluster_deltas(self):
        """Process new cluster deltas and route accordingly"""
        try:
            # Get recent cluster deltas from strands
            query = """
                SELECT * FROM AD_strands 
                WHERE kind = 'cluster_delta' 
                AND created_at > NOW() - INTERVAL '5 minutes'
                ORDER BY created_at DESC
            """
            
            result = await self.supabase_manager.execute_query(query)
            
            for row in result:
                await self._route_cluster_delta(row)
                
        except Exception as e:
            print(f"Error processing cluster deltas: {e}")
    
    async def _route_cluster_delta(self, cluster_delta: Dict[str, Any]):
        """Route a cluster delta to appropriate agents"""
        try:
            # Analyze cluster delta content
            cluster_type = cluster_delta.get('cluster_type', '')
            confidence = cluster_delta.get('confidence', 0.0)
            affected_agents = cluster_delta.get('affected_agents', [])
            
            # Determine routing strategy based on cluster type and confidence
            if confidence > 0.8:
                # High confidence - create experiment directive
                await self._create_experiment_directive(cluster_delta, affected_agents)
            elif confidence > 0.5:
                # Medium confidence - create focus directive
                await self._create_focus_directive(cluster_delta, affected_agents)
            else:
                # Low confidence - create coordination request
                await self._create_coordination_request(cluster_delta, affected_agents)
                
        except Exception as e:
            print(f"Error routing cluster delta: {e}")
    
    async def _create_experiment_directive(self, cluster_delta: Dict[str, Any], affected_agents: List[str]):
        """Create experiment directive for high-confidence cluster deltas"""
        try:
            # Generate experiment hypothesis using LLM
            hypothesis = await self._generate_experiment_hypothesis(cluster_delta)
            
            # Create experiment
            exp_id = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.active_experiments)}"
            
            experiment = Experiment(
                exp_id=exp_id,
                hypothesis=hypothesis,
                owner_agent=affected_agents[0] if affected_agents else 'raw_data_intelligence',
                shape='durability',  # Default shape
                criteria={
                    'min_samples': 100,
                    'success_threshold': 0.7,
                    'time_window_hours': 24
                },
                ttl_hours=24,
                status='pending',
                created_at=datetime.now(timezone.utc),
                lesson_keys=[]
            )
            
            # Add to registry
            self.active_experiments[exp_id] = experiment
            
            # Create directive for agent
            directive_id = f"dir_{exp_id}"
            directive = AgentDirective(
                directive_id=directive_id,
                target_agent=experiment.owner_agent,
                directive_type='experiment_assignment',
                content={
                    'experiment_id': exp_id,
                    'hypothesis': hypothesis,
                    'criteria': experiment.criteria,
                    'ttl_hours': experiment.ttl_hours
                },
                autonomy_level=self.agent_autonomy_levels.get(experiment.owner_agent, 'bounded'),
                ttl_hours=self.directive_timeout_hours,
                created_at=datetime.now(timezone.utc),
                status='pending',
                response_deadline=datetime.now(timezone.utc) + timedelta(hours=self.directive_timeout_hours)
            )
            
            # Add to pending directives
            self.pending_directives[directive_id] = directive
            
            # Publish directive to database
            await self._publish_directive(directive)
            
            print(f"✅ Created experiment directive {directive_id} for {experiment.owner_agent}")
            
        except Exception as e:
            print(f"Error creating experiment directive: {e}")
    
    async def _create_focus_directive(self, cluster_delta: Dict[str, Any], affected_agents: List[str]):
        """Create focus directive for medium-confidence cluster deltas"""
        try:
            directive_id = f"focus_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            directive = AgentDirective(
                directive_id=directive_id,
                target_agent=affected_agents[0] if affected_agents else 'raw_data_intelligence',
                directive_type='focus_directive',
                content={
                    'focus_area': cluster_delta.get('cluster_type', ''),
                    'confidence': cluster_delta.get('confidence', 0.0),
                    'context': cluster_delta.get('context', {})
                },
                autonomy_level='bounded',
                ttl_hours=self.directive_timeout_hours,
                created_at=datetime.now(timezone.utc),
                status='pending',
                response_deadline=datetime.now(timezone.utc) + timedelta(hours=self.directive_timeout_hours)
            )
            
            # Add to pending directives
            self.pending_directives[directive_id] = directive
            
            # Publish directive to database
            await self._publish_directive(directive)
            
            print(f"✅ Created focus directive {directive_id} for {directive.target_agent}")
            
        except Exception as e:
            print(f"Error creating focus directive: {e}")
    
    async def _create_coordination_request(self, cluster_delta: Dict[str, Any], affected_agents: List[str]):
        """Create coordination request for low-confidence cluster deltas"""
        try:
            directive_id = f"coord_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            directive = AgentDirective(
                directive_id=directive_id,
                target_agent=affected_agents[0] if affected_agents else 'raw_data_intelligence',
                directive_type='coordination_request',
                content={
                    'request_type': 'cluster_analysis',
                    'cluster_data': cluster_delta,
                    'coordination_needed': True
                },
                autonomy_level='exploratory',
                ttl_hours=self.directive_timeout_hours,
                created_at=datetime.now(timezone.utc),
                status='pending',
                response_deadline=datetime.now(timezone.utc) + timedelta(hours=self.directive_timeout_hours)
            )
            
            # Add to pending directives
            self.pending_directives[directive_id] = directive
            
            # Publish directive to database
            await self._publish_directive(directive)
            
            print(f"✅ Created coordination request {directive_id} for {directive.target_agent}")
            
        except Exception as e:
            print(f"Error creating coordination request: {e}")
    
    async def _generate_experiment_hypothesis(self, cluster_delta: Dict[str, Any]) -> str:
        """Generate experiment hypothesis using LLM"""
        try:
            # Get context for hypothesis generation
            context = self.context_system.get_relevant_context(
                query="experiment hypothesis generation",
                context_type="strategic_analysis",
                max_results=5
            )
            
            # Create prompt for hypothesis generation
            prompt = f"""
            Based on the following cluster delta and context, generate a clear, testable hypothesis for an experiment:
            
            Cluster Delta: {json.dumps(cluster_delta, indent=2)}
            
            Context: {json.dumps(context, indent=2)}
            
            Generate a hypothesis that:
            1. Is specific and testable
            2. Relates to the cluster delta
            3. Can be validated with measurable criteria
            4. Is relevant to alpha detection
            
            Return only the hypothesis statement, no additional text.
            """
            
            # Generate hypothesis using LLM
            response = await self.llm_client.generate_response(
                prompt=prompt,
                model="anthropic/claude-3.5-sonnet",
                max_tokens=200,
                temperature=0.3
            )
            
            return response.strip()
            
        except Exception as e:
            print(f"Error generating experiment hypothesis: {e}")
            return f"Test hypothesis for cluster delta: {cluster_delta.get('cluster_type', 'unknown')}"
    
    async def _publish_directive(self, directive: AgentDirective):
        """Publish directive to database"""
        try:
            # Create strand for directive
            strand_data = {
                'kind': 'directive',
                'module': 'alpha',
                'tags': [f"agent:central_intelligence:orchestrator:directive_created"],
                'directive_id': directive.directive_id,
                'target_agent': directive.target_agent,
                'directive_type': directive.directive_type,
                'directive_content': directive.content,
                'autonomy_level': directive.autonomy_level,
                'ttl_hours': directive.ttl_hours,
                'status': directive.status,
                'response_deadline': directive.response_deadline.isoformat() if directive.response_deadline else None,
                'team_member': 'orchestrator'
            }
            
            # Insert into database
            await self.supabase_manager.insert_strand(strand_data)
            
        except Exception as e:
            print(f"Error publishing directive: {e}")
    
    async def _handle_expired_experiment(self, exp_id: str):
        """Handle expired experiment"""
        try:
            exp = self.active_experiments[exp_id]
            exp.status = 'failed'
            exp.completed_at = datetime.now(timezone.utc)
            
            # Move to completed experiments
            self.completed_experiments[exp_id] = exp
            del self.active_experiments[exp_id]
            
            # Update database
            await self._update_experiment_in_database(exp)
            
            print(f"⚠️ Experiment {exp_id} expired and marked as failed")
            
        except Exception as e:
            print(f"Error handling expired experiment: {e}")
    
    async def _handle_expired_directive(self, directive_id: str):
        """Handle expired directive"""
        try:
            directive = self.pending_directives[directive_id]
            directive.status = 'failed'
            
            # Update database
            await self._update_directive_in_database(directive)
            
            print(f"⚠️ Directive {directive_id} expired and marked as failed")
            
        except Exception as e:
            print(f"Error handling expired directive: {e}")
    
    async def _update_experiment_statuses(self):
        """Update experiment statuses from database"""
        try:
            # Query for updated experiment statuses
            query = """
                SELECT experiment_id, status, results, completed_at 
                FROM AD_strands 
                WHERE kind = 'experiment' 
                AND experiment_id IN ({})
            """.format(','.join([f"'{exp_id}'" for exp_id in self.active_experiments.keys()]))
            
            result = await self.supabase_manager.execute_query(query)
            
            for row in result:
                exp_id = row['experiment_id']
                if exp_id in self.active_experiments:
                    exp = self.active_experiments[exp_id]
                    exp.status = row['status']
                    exp.results = row.get('results')
                    if row.get('completed_at'):
                        exp.completed_at = row['completed_at']
                    
                    # Move completed experiments
                    if exp.status in ['completed', 'failed']:
                        self.completed_experiments[exp_id] = exp
                        del self.active_experiments[exp_id]
                        
        except Exception as e:
            print(f"Error updating experiment statuses: {e}")
    
    async def _update_experiment_in_database(self, experiment: Experiment):
        """Update experiment in database"""
        try:
            # Update experiment strand
            update_data = {
                'status': experiment.status,
                'completed_at': experiment.completed_at.isoformat() if experiment.completed_at else None,
                'results': experiment.results
            }
            
            # Update in database
            await self.supabase_manager.update_strand(
                strand_id=experiment.exp_id,
                update_data=update_data
            )
            
        except Exception as e:
            print(f"Error updating experiment in database: {e}")
    
    async def _update_directive_in_database(self, directive: AgentDirective):
        """Update directive in database"""
        try:
            # Update directive strand
            update_data = {
                'status': directive.status
            }
            
            # Update in database
            await self.supabase_manager.update_strand(
                strand_id=directive.directive_id,
                update_data=update_data
            )
            
        except Exception as e:
            print(f"Error updating directive in database: {e}")
    
    async def get_orchestration_status(self) -> Dict[str, Any]:
        """Get current orchestration status"""
        return {
            'active_experiments': len(self.active_experiments),
            'completed_experiments': len(self.completed_experiments),
            'pending_directives': len(self.pending_directives),
            'agent_autonomy_levels': self.agent_autonomy_levels,
            'max_concurrent_experiments': self.max_concurrent_experiments,
            'experiment_timeout_hours': self.experiment_timeout_hours,
            'directive_timeout_hours': self.directive_timeout_hours
        }
    
    async def set_agent_autonomy(self, agent_name: str, autonomy_level: str):
        """Set autonomy level for an agent"""
        if autonomy_level in ['strict', 'bounded', 'exploratory']:
            self.agent_autonomy_levels[agent_name] = autonomy_level
            print(f"✅ Set {agent_name} autonomy level to {autonomy_level}")
        else:
            print(f"❌ Invalid autonomy level: {autonomy_level}")
    
    async def create_manual_experiment(self, hypothesis: str, owner_agent: str, 
                                     shape: str = 'durability', criteria: Dict[str, Any] = None) -> str:
        """Create a manual experiment"""
        try:
            exp_id = f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            experiment = Experiment(
                exp_id=exp_id,
                hypothesis=hypothesis,
                owner_agent=owner_agent,
                shape=shape,
                criteria=criteria or {
                    'min_samples': 100,
                    'success_threshold': 0.7,
                    'time_window_hours': 24
                },
                ttl_hours=24,
                status='pending',
                created_at=datetime.now(timezone.utc),
                lesson_keys=[]
            )
            
            # Add to registry
            self.active_experiments[exp_id] = experiment
            
            # Create directive
            await self._create_experiment_directive_from_experiment(experiment)
            
            print(f"✅ Created manual experiment {exp_id} for {owner_agent}")
            return exp_id
            
        except Exception as e:
            print(f"Error creating manual experiment: {e}")
            return None
    
    async def _create_experiment_directive_from_experiment(self, experiment: Experiment):
        """Create directive from experiment"""
        directive_id = f"dir_{experiment.exp_id}"
        directive = AgentDirective(
            directive_id=directive_id,
            target_agent=experiment.owner_agent,
            directive_type='experiment_assignment',
            content={
                'experiment_id': experiment.exp_id,
                'hypothesis': experiment.hypothesis,
                'criteria': experiment.criteria,
                'ttl_hours': experiment.ttl_hours
            },
            autonomy_level=self.agent_autonomy_levels.get(experiment.owner_agent, 'bounded'),
            ttl_hours=self.directive_timeout_hours,
            created_at=datetime.now(timezone.utc),
            status='pending',
            response_deadline=datetime.now(timezone.utc) + timedelta(hours=self.directive_timeout_hours)
        )
        
        # Add to pending directives
        self.pending_directives[directive_id] = directive
        
        # Publish directive to database
        await self._publish_directive(directive)

