"""
CIL-PlanComposer: Trading Plan Composer

Role: Composes research-grade Trading Plan Drafts from mined motifs + signals.
- Gathers confluence across families/timebases
- Pulls "fails-when" from doctrine to set invalidation rules
- Attaches full provenance: signal_ids, detector versions, experiment refs

Think: takes discovery → a coherent plan users (or future execution) can act on.
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient
from src.llm_integration.prompt_manager import PromptManager
from src.llm_integration.database_driven_context_system import DatabaseDrivenContextSystem


@dataclass
class TradingPlanDraft:
    """Trading Plan Draft data structure"""
    plan_id: str
    evidence_stack: List[str]  # motif_ids, signal_ids
    conditions: Dict[str, Any]  # activate, confirm, invalidate
    scope: Dict[str, Any]  # assets, timeframes, regimes
    provenance: Dict[str, Any]  # exp_ids, detector_versions
    notes: Dict[str, Any]  # mechanism, risks, fails_when
    confidence: float
    created_at: datetime
    status: str  # draft, validated, ready, expired


@dataclass
class EvidenceItem:
    """Evidence item for plan composition"""
    item_id: str
    item_type: str  # motif, signal, confluence, experiment
    confidence: float
    relevance: float
    context: Dict[str, Any]
    provenance: Dict[str, Any]


class CILPlanComposer:
    """
    CIL-PlanComposer: Trading Plan Composer
    
    Responsibilities:
    - Composes research-grade Trading Plan Drafts
    - Gathers confluence across families/timebases
    - Pulls "fails-when" from doctrine
    - Attaches full provenance
    - Creates coherent plans from discovery
    """
    
    def __init__(self, supabase_manager: SupabaseManager, llm_client: OpenRouterClient):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.prompt_manager = PromptManager()
        self.context_system = DatabaseDrivenContextSystem(supabase_manager)
        
        # Plan Management
        self.active_plans: Dict[str, TradingPlanDraft] = {}
        self.completed_plans: Dict[str, TradingPlanDraft] = {}
        
        # Composition Configuration
        self.plan_generation_interval_minutes = 30
        self.min_insights_for_plan = 3
        self.min_confidence_threshold = 0.6
        self.max_plan_age_hours = 24
        
    async def initialize(self):
        """Initialize the plan composer"""
        try:
            # Load existing plans
            await self._load_existing_plans()
            
            # Start composition loop
            asyncio.create_task(self._composition_loop())
            
            print("✅ CIL-PlanComposer initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ CIL-PlanComposer initialization failed: {e}")
            return False
    
    async def _composition_loop(self):
        """Main composition loop"""
        while True:
            try:
                # Check for new insights
                await self._check_for_new_insights()
                
                # Compose new plans if needed
                await self._compose_new_plans()
                
                # Validate existing plans
                await self._validate_existing_plans()
                
                # Clean up expired plans
                await self._cleanup_expired_plans()
                
                # Wait before next iteration
                await asyncio.sleep(self.plan_generation_interval_minutes * 60)
                
            except Exception as e:
                print(f"Error in plan composition loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _check_for_new_insights(self):
        """Check for new insights that could form plans"""
        try:
            # Query for recent high-confidence insights
            query = """
                SELECT * FROM AD_strands 
                WHERE kind IN ('motif', 'confluence_event', 'meta_signal')
                    AND confidence >= %s
                    AND created_at > NOW() - INTERVAL '1 hour'
                ORDER BY confidence DESC, created_at DESC
            """
            
            result = await self.supabase_manager.execute_query(query, [self.min_confidence_threshold])
            
            if len(result) >= self.min_insights_for_plan:
                print(f"✅ Found {len(result)} new insights for plan composition")
                return True
            
            return False
            
        except Exception as e:
            print(f"Error checking for new insights: {e}")
            return False
    
    async def _compose_new_plans(self):
        """Compose new trading plans from available insights"""
        try:
            # Get evidence items for plan composition
            evidence_items = await self._gather_evidence_items()
            
            if len(evidence_items) < self.min_insights_for_plan:
                return
            
            # Group evidence by confluence
            evidence_groups = await self._group_evidence_by_confluence(evidence_items)
            
            # Compose plans for each evidence group
            for group_id, group_evidence in evidence_groups.items():
                if len(group_evidence) >= self.min_insights_for_plan:
                    plan = await self._compose_plan_from_evidence(group_evidence)
                    if plan:
                        self.active_plans[plan.plan_id] = plan
                        await self._publish_plan_draft(plan)
                        
        except Exception as e:
            print(f"Error composing new plans: {e}")
    
    async def _gather_evidence_items(self) -> List[EvidenceItem]:
        """Gather evidence items for plan composition"""
        try:
            evidence_items = []
            
            # Get motif evidence
            motif_query = """
                SELECT * FROM AD_strands 
                WHERE kind = 'motif' 
                    AND confidence >= %s
                    AND created_at > NOW() - INTERVAL '24 hours'
                ORDER BY confidence DESC
            """
            
            motif_result = await self.supabase_manager.execute_query(motif_query, [self.min_confidence_threshold])
            
            for row in motif_result:
                evidence_item = EvidenceItem(
                    item_id=row['motif_id'],
                    item_type='motif',
                    confidence=row.get('confidence', 0.0),
                    relevance=row.get('confidence', 0.0),
                    context={
                        'name': row.get('motif_name', ''),
                        'family': row.get('motif_family', ''),
                        'invariants': row.get('invariants', []),
                        'contexts': row.get('contexts', {})
                    },
                    provenance={
                        'detector': 'motif_miner',
                        'version': '1.0',
                        'created_at': row['created_at']
                    }
                )
                evidence_items.append(evidence_item)
            
            # Get confluence evidence
            confluence_query = """
                SELECT * FROM AD_strands 
                WHERE kind = 'confluence_event' 
                    AND confidence >= %s
                    AND created_at > NOW() - INTERVAL '24 hours'
                ORDER BY confidence DESC
            """
            
            confluence_result = await self.supabase_manager.execute_query(confluence_query, [self.min_confidence_threshold])
            
            for row in confluence_result:
                evidence_item = EvidenceItem(
                    item_id=row['confluence_id'],
                    item_type='confluence',
                    confidence=row.get('confidence', 0.0),
                    relevance=row.get('confidence', 0.0),
                    context={
                        'family_a': row.get('family_a', ''),
                        'family_b': row.get('family_b', ''),
                        'regime': row.get('regime', ''),
                        'session': row.get('session', ''),
                        'lift': row.get('lift', 0.0)
                    },
                    provenance={
                        'detector': 'confluence_detector',
                        'version': '1.0',
                        'created_at': row['created_at']
                    }
                )
                evidence_items.append(evidence_item)
            
            return evidence_items
            
        except Exception as e:
            print(f"Error gathering evidence items: {e}")
            return []
    
    async def _group_evidence_by_confluence(self, evidence_items: List[EvidenceItem]) -> Dict[str, List[EvidenceItem]]:
        """Group evidence items by confluence patterns"""
        try:
            groups = {}
            
            for item in evidence_items:
                # Simple grouping by family/regime/session
                if item.item_type == 'motif':
                    group_key = f"{item.context.get('family', 'unknown')}_{item.context.get('contexts', {}).get('regime', 'unknown')}"
                elif item.item_type == 'confluence':
                    group_key = f"{item.context.get('family_a', 'unknown')}_{item.context.get('family_b', 'unknown')}_{item.context.get('regime', 'unknown')}"
                else:
                    group_key = f"other_{item.item_type}"
                
                if group_key not in groups:
                    groups[group_key] = []
                groups[group_key].append(item)
            
            return groups
            
        except Exception as e:
            print(f"Error grouping evidence by confluence: {e}")
            return {}
    
    async def _compose_plan_from_evidence(self, evidence_items: List[EvidenceItem]) -> Optional[TradingPlanDraft]:
        """Compose trading plan from evidence items using LLM"""
        try:
            # Prepare evidence summary for LLM
            evidence_summary = []
            for item in evidence_items:
                evidence_summary.append({
                    'type': item.item_type,
                    'confidence': item.confidence,
                    'context': item.context,
                    'provenance': item.provenance
                })
            
            # Generate plan using LLM
            prompt = f"""
            Compose a trading plan draft from the following evidence:
            
            Evidence Items: {json.dumps(evidence_summary, indent=2)}
            
            Generate a comprehensive trading plan that includes:
            1. Evidence Stack: List of evidence items that support the plan
            2. Conditions: Activation, confirmation, and invalidation conditions
            3. Scope: Assets, timeframes, and regimes to focus on
            4. Provenance: References to experiments and detector versions
            5. Notes: Mechanism hypothesis, risks, and failure conditions
            
            Return as JSON format with the following structure:
            {{
                "evidence_stack": ["item_id1", "item_id2", ...],
                "conditions": {{
                    "activate": ["condition1", "condition2", ...],
                    "confirm": ["confirmation1", "confirmation2", ...],
                    "invalidate": ["invalidation1", "invalidation2", ...]
                }},
                "scope": {{
                    "assets": ["BTC", "ETH", ...],
                    "timeframes": ["1h", "4h", ...],
                    "regimes": ["high_vol", "sideways", ...]
                }},
                "provenance": {{
                    "experiment_ids": ["exp1", "exp2", ...],
                    "detector_versions": {{"detector1": "v1.0", "detector2": "v1.0"}}
                }},
                "notes": {{
                    "mechanism": "explanation of why this works",
                    "risks": ["risk1", "risk2", ...],
                    "fails_when": ["failure_condition1", "failure_condition2", ...]
                }}
            }}
            """
            
            response = await self.llm_client.generate_response(
                prompt=prompt,
                model="anthropic/claude-3.5-sonnet",
                max_tokens=1000,
                temperature=0.3
            )
            
            # Parse response and create plan
            try:
                plan_data = json.loads(response)
                
                plan_id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                # Calculate overall confidence
                total_confidence = sum(item.confidence for item in evidence_items)
                avg_confidence = total_confidence / len(evidence_items) if evidence_items else 0.0
                
                plan = TradingPlanDraft(
                    plan_id=plan_id,
                    evidence_stack=plan_data.get('evidence_stack', []),
                    conditions=plan_data.get('conditions', {}),
                    scope=plan_data.get('scope', {}),
                    provenance=plan_data.get('provenance', {}),
                    notes=plan_data.get('notes', {}),
                    confidence=avg_confidence,
                    created_at=datetime.now(timezone.utc),
                    status='draft'
                )
                
                return plan
                
            except json.JSONDecodeError:
                print(f"Failed to parse LLM response for plan: {response}")
                return None
                
        except Exception as e:
            print(f"Error composing plan from evidence: {e}")
            return None
    
    async def _validate_existing_plans(self):
        """Validate existing plans against current market conditions"""
        try:
            for plan_id, plan in self.active_plans.items():
                if plan.status == 'draft':
                    # Check if plan is still valid
                    is_valid = await self._validate_plan(plan)
                    
                    if is_valid:
                        plan.status = 'validated'
                        print(f"✅ Plan {plan_id} validated")
                    else:
                        plan.status = 'expired'
                        print(f"⚠️ Plan {plan_id} expired")
                        
        except Exception as e:
            print(f"Error validating existing plans: {e}")
    
    async def _validate_plan(self, plan: TradingPlanDraft) -> bool:
        """Validate a plan against current conditions"""
        try:
            # Check if evidence is still relevant
            for evidence_id in plan.evidence_stack:
                # Query for evidence item
                query = """
                    SELECT * FROM AD_strands 
                    WHERE id = %s AND created_at > NOW() - INTERVAL '24 hours'
                """
                
                result = await self.supabase_manager.execute_query(query, [evidence_id])
                
                if not result:
                    return False  # Evidence no longer exists or is too old
            
            # Check if plan confidence is still above threshold
            if plan.confidence < self.min_confidence_threshold:
                return False
            
            return True
            
        except Exception as e:
            print(f"Error validating plan: {e}")
            return False
    
    async def _cleanup_expired_plans(self):
        """Clean up expired plans"""
        try:
            now = datetime.now(timezone.utc)
            expired_plans = []
            
            for plan_id, plan in self.active_plans.items():
                # Check if plan is too old
                if (now - plan.created_at).total_seconds() > self.max_plan_age_hours * 3600:
                    expired_plans.append(plan_id)
                elif plan.status == 'expired':
                    expired_plans.append(plan_id)
            
            # Move expired plans to completed
            for plan_id in expired_plans:
                plan = self.active_plans[plan_id]
                plan.status = 'expired'
                self.completed_plans[plan_id] = plan
                del self.active_plans[plan_id]
                
                print(f"🗑️ Moved expired plan {plan_id} to completed")
                
        except Exception as e:
            print(f"Error cleaning up expired plans: {e}")
    
    async def _publish_plan_draft(self, plan: TradingPlanDraft):
        """Publish plan draft to database"""
        try:
            strand_data = {
                'kind': 'trading_plan',
                'module': 'alpha',
                'tags': [f"agent:central_intelligence:plan_composer:plan_created"],
                'plan_id': plan.plan_id,
                'evidence_stack': plan.evidence_stack,
                'conditions': plan.conditions,
                'scope': plan.scope,
                'provenance': plan.provenance,
                'notes': plan.notes,
                'confidence': plan.confidence,
                'status': plan.status,
                'cil_team_member': 'plan_composer'
            }
            
            await self.supabase_manager.insert_strand(strand_data)
            
            print(f"✅ Published plan draft {plan.plan_id}")
            
        except Exception as e:
            print(f"Error publishing plan draft: {e}")
    
    async def _load_existing_plans(self):
        """Load existing plans from database"""
        try:
            query = """
                SELECT * FROM AD_strands 
                WHERE kind = 'trading_plan' 
                ORDER BY created_at DESC
            """
            
            result = await self.supabase_manager.execute_query(query)
            
            for row in result:
                plan = TradingPlanDraft(
                    plan_id=row['plan_id'],
                    evidence_stack=row.get('evidence_stack', []),
                    conditions=row.get('conditions', {}),
                    scope=row.get('scope', {}),
                    provenance=row.get('provenance', {}),
                    notes=row.get('notes', {}),
                    confidence=row.get('confidence', 0.0),
                    created_at=row['created_at'],
                    status=row.get('status', 'draft')
                )
                
                if plan.status in ['draft', 'validated', 'ready']:
                    self.active_plans[plan.plan_id] = plan
                else:
                    self.completed_plans[plan.plan_id] = plan
                    
        except Exception as e:
            print(f"Warning: Could not load existing plans: {e}")
    
    async def get_plan_composition_status(self) -> Dict[str, Any]:
        """Get current plan composition status"""
        return {
            'active_plans_count': len(self.active_plans),
            'completed_plans_count': len(self.completed_plans),
            'plan_generation_interval_minutes': self.plan_generation_interval_minutes,
            'min_insights_for_plan': self.min_insights_for_plan,
            'min_confidence_threshold': self.min_confidence_threshold,
            'max_plan_age_hours': self.max_plan_age_hours
        }
    
    async def create_manual_plan(self, evidence_items: List[str], 
                               conditions: Dict[str, Any], scope: Dict[str, Any]) -> str:
        """Create a manual trading plan"""
        try:
            plan_id = f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            plan = TradingPlanDraft(
                plan_id=plan_id,
                evidence_stack=evidence_items,
                conditions=conditions,
                scope=scope,
                provenance={'manual': True, 'created_by': 'user'},
                notes={'mechanism': 'Manual plan', 'risks': [], 'fails_when': []},
                confidence=0.8,  # High confidence for manual plans
                created_at=datetime.now(timezone.utc),
                status='draft'
            )
            
            # Add to active plans
            self.active_plans[plan_id] = plan
            
            # Publish plan
            await self._publish_plan_draft(plan)
            
            print(f"✅ Created manual plan {plan_id}")
            return plan_id
            
        except Exception as e:
            print(f"Error creating manual plan: {e}")
            return None

