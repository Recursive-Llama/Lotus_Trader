"""
CIL-DoctrineKeeper: Lessons & Negative Doctrine

Role: Curates doctrine from strand lessons/braids; guards against retesting dead ends.
- Promotes/retire patterns; records provenance/lineage
- Blocks new experiments overlapping contraindicated unless a new Why-Map exists
- Maintains doctrine status: provisional, affirmed, retired, contraindicated

Think: the curator of what works, what doesn't, and what to avoid.
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


class DoctrineStatus(Enum):
    """Doctrine status types"""
    PROVISIONAL = "provisional"
    AFFIRMED = "affirmed"
    RETIRED = "retired"
    CONTRAINDICATED = "contraindicated"


@dataclass
class DoctrineEntry:
    """Doctrine entry data structure"""
    doctrine_id: str
    pattern_type: str  # motif, confluence, hypothesis, experiment
    pattern_id: str
    doctrine_status: DoctrineStatus
    evidence_count: int
    success_rate: float
    failure_rate: float
    last_updated: datetime
    lineage: Dict[str, Any]
    why_map: Dict[str, Any]
    contraindications: List[str]
    created_at: datetime


@dataclass
class Lesson:
    """Lesson data structure"""
    lesson_id: str
    source_type: str  # experiment, hypothesis, motif, confluence
    source_id: str
    lesson_type: str  # success, failure, anomaly, insight
    lesson_content: str
    context: Dict[str, Any]
    confidence: float
    created_at: datetime


class CILDoctrineKeeper:
    """
    CIL-DoctrineKeeper: Lessons & Negative Doctrine
    
    Responsibilities:
    - Curates doctrine from strand lessons/braids
    - Guards against retesting dead ends
    - Promotes/retires patterns with provenance/lineage
    - Blocks contraindicated experiments
    - Maintains doctrine status and negative doctrine
    """
    
    def __init__(self, supabase_manager: SupabaseManager, llm_client: OpenRouterClient):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.prompt_manager = PromptManager()
        self.context_system = DatabaseDrivenContextSystem(supabase_manager)
        
        # Doctrine Management
        self.doctrine_entries: Dict[str, DoctrineEntry] = {}
        self.lessons: Dict[str, Lesson] = {}
        self.contraindicated_patterns: Dict[str, List[str]] = {}
        
        # Doctrine Configuration
        self.doctrine_update_interval_hours = 6
        self.negative_doctrine_threshold = 0.3
        self.min_evidence_for_affirmation = 10
        self.max_failure_rate_for_retirement = 0.7
        
    async def initialize(self):
        """Initialize the doctrine keeper"""
        try:
            # Load existing doctrine
            await self._load_existing_doctrine()
            
            # Load existing lessons
            await self._load_existing_lessons()
            
            # Start doctrine curation loop
            asyncio.create_task(self._doctrine_curation_loop())
            
            print("✅ CIL-DoctrineKeeper initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ CIL-DoctrineKeeper initialization failed: {e}")
            return False
    
    async def _doctrine_curation_loop(self):
        """Main doctrine curation loop"""
        while True:
            try:
                # Process new lessons
                await self._process_new_lessons()
                
                # Update doctrine statuses
                await self._update_doctrine_statuses()
                
                # Identify contraindicated patterns
                await self._identify_contraindicated_patterns()
                
                # Promote/retire patterns
                await self._promote_retire_patterns()
                
                # Wait before next iteration
                await asyncio.sleep(self.doctrine_update_interval_hours * 3600)
                
            except Exception as e:
                print(f"Error in doctrine curation loop: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour on error
    
    async def _process_new_lessons(self):
        """Process new lessons and update doctrine"""
        try:
            # Query for new lessons
            query = """
                SELECT * FROM AD_strands 
                WHERE kind = 'lesson' 
                    AND created_at > NOW() - INTERVAL '%s hours'
                ORDER BY created_at DESC
            """
            
            result = await self.supabase_manager.execute_query(query, [self.doctrine_update_interval_hours])
            
            for row in result:
                # Create lesson object
                lesson = Lesson(
                    lesson_id=row['id'],
                    source_type=row.get('source_type', ''),
                    source_id=row.get('source_id', ''),
                    lesson_type=row.get('lesson_type', ''),
                    lesson_content=row.get('lesson_content', ''),
                    context=row.get('context', {}),
                    confidence=row.get('confidence', 0.0),
                    created_at=row['created_at']
                )
                
                # Store lesson
                self.lessons[lesson.lesson_id] = lesson
                
                # Update doctrine based on lesson
                await self._update_doctrine_from_lesson(lesson)
                
        except Exception as e:
            print(f"Error processing new lessons: {e}")
    
    async def _update_doctrine_from_lesson(self, lesson: Lesson):
        """Update doctrine based on lesson"""
        try:
            # Find or create doctrine entry for this pattern
            doctrine_id = f"doctrine_{lesson.source_type}_{lesson.source_id}"
            
            if doctrine_id not in self.doctrine_entries:
                # Create new doctrine entry
                doctrine_entry = DoctrineEntry(
                    doctrine_id=doctrine_id,
                    pattern_type=lesson.source_type,
                    pattern_id=lesson.source_id,
                    doctrine_status=DoctrineStatus.PROVISIONAL,
                    evidence_count=0,
                    success_rate=0.0,
                    failure_rate=0.0,
                    last_updated=datetime.now(timezone.utc),
                    lineage={'parents': [], 'children': []},
                    why_map={},
                    contraindications=[],
                    created_at=datetime.now(timezone.utc)
                )
                self.doctrine_entries[doctrine_id] = doctrine_entry
            
            # Update doctrine entry
            doctrine_entry = self.doctrine_entries[doctrine_id]
            doctrine_entry.evidence_count += 1
            doctrine_entry.last_updated = datetime.now(timezone.utc)
            
            # Update success/failure rates based on lesson type
            if lesson.lesson_type == 'success':
                doctrine_entry.success_rate = (doctrine_entry.success_rate * (doctrine_entry.evidence_count - 1) + 1.0) / doctrine_entry.evidence_count
            elif lesson.lesson_type == 'failure':
                doctrine_entry.failure_rate = (doctrine_entry.failure_rate * (doctrine_entry.evidence_count - 1) + 1.0) / doctrine_entry.evidence_count
            
            # Update why_map with lesson insights
            if lesson.lesson_content:
                await self._update_why_map_from_lesson(doctrine_entry, lesson)
            
            print(f"✅ Updated doctrine for {doctrine_id} (evidence: {doctrine_entry.evidence_count})")
            
        except Exception as e:
            print(f"Error updating doctrine from lesson: {e}")
    
    async def _update_why_map_from_lesson(self, doctrine_entry: DoctrineEntry, lesson: Lesson):
        """Update why_map with insights from lesson using LLM"""
        try:
            # Generate why_map insights using LLM
            prompt = f"""
            Extract insights from this lesson to update the why_map:
            
            Lesson: {lesson.lesson_content}
            Lesson Type: {lesson.lesson_type}
            Context: {json.dumps(lesson.context, indent=2)}
            
            Current Why-Map: {json.dumps(doctrine_entry.why_map, indent=2)}
            
            Update the why_map with:
            1. Mechanism insights (why it works/doesn't work)
            2. Supporting evidence
            3. Failure conditions
            4. Context dependencies
            
            Return updated why_map as JSON:
            {{
                "mechanism_hypothesis": "updated hypothesis",
                "supports": ["evidence1", "evidence2", ...],
                "fails_when": ["condition1", "condition2", ...],
                "context_dependencies": {{"regime": "high_vol", "session": "US"}}
            }}
            """
            
            response = await self.llm_client.generate_response(
                prompt=prompt,
                model="anthropic/claude-3.5-sonnet",
                max_tokens=500,
                temperature=0.3
            )
            
            # Parse response and update why_map
            try:
                updated_why_map = json.loads(response)
                doctrine_entry.why_map.update(updated_why_map)
                
            except json.JSONDecodeError:
                print(f"Failed to parse LLM response for why_map: {response}")
                
        except Exception as e:
            print(f"Error updating why_map from lesson: {e}")
    
    async def _update_doctrine_statuses(self):
        """Update doctrine statuses based on evidence"""
        try:
            for doctrine_id, doctrine_entry in self.doctrine_entries.items():
                # Determine new status based on evidence
                new_status = await self._determine_doctrine_status(doctrine_entry)
                
                if new_status != doctrine_entry.doctrine_status:
                    doctrine_entry.doctrine_status = new_status
                    print(f"✅ Updated {doctrine_id} status to {new_status.value}")
                    
        except Exception as e:
            print(f"Error updating doctrine statuses: {e}")
    
    async def _determine_doctrine_status(self, doctrine_entry: DoctrineEntry) -> DoctrineStatus:
        """Determine doctrine status based on evidence"""
        try:
            # Check if we have enough evidence
            if doctrine_entry.evidence_count < self.min_evidence_for_affirmation:
                return DoctrineStatus.PROVISIONAL
            
            # Check failure rate for retirement
            if doctrine_entry.failure_rate > self.max_failure_rate_for_retirement:
                return DoctrineStatus.RETIRED
            
            # Check success rate for affirmation
            if doctrine_entry.success_rate > 0.7 and doctrine_entry.failure_rate < 0.3:
                return DoctrineStatus.AFFIRMED
            
            # Check for contraindications
            if doctrine_entry.failure_rate > 0.8:
                return DoctrineStatus.CONTRAINDICATED
            
            return DoctrineStatus.PROVISIONAL
            
        except Exception as e:
            print(f"Error determining doctrine status: {e}")
            return DoctrineStatus.PROVISIONAL
    
    async def _identify_contraindicated_patterns(self):
        """Identify patterns that should be contraindicated"""
        try:
            for doctrine_id, doctrine_entry in self.doctrine_entries.items():
                if doctrine_entry.doctrine_status == DoctrineStatus.CONTRAINDICATED:
                    # Add to contraindicated patterns
                    pattern_key = f"{doctrine_entry.pattern_type}:{doctrine_entry.pattern_id}"
                    
                    if pattern_key not in self.contraindicated_patterns:
                        self.contraindicated_patterns[pattern_key] = []
                    
                    # Add contraindication reasons
                    contraindication_reasons = [
                        f"High failure rate: {doctrine_entry.failure_rate:.2f}",
                        f"Low success rate: {doctrine_entry.success_rate:.2f}",
                        f"Evidence count: {doctrine_entry.evidence_count}"
                    ]
                    
                    self.contraindicated_patterns[pattern_key] = contraindication_reasons
                    
                    print(f"⚠️ Contraindicated pattern: {pattern_key}")
                    
        except Exception as e:
            print(f"Error identifying contraindicated patterns: {e}")
    
    async def _promote_retire_patterns(self):
        """Promote or retire patterns based on doctrine status"""
        try:
            for doctrine_id, doctrine_entry in self.doctrine_entries.items():
                if doctrine_entry.doctrine_status == DoctrineStatus.AFFIRMED:
                    # Promote pattern - update in database
                    await self._promote_pattern(doctrine_entry)
                elif doctrine_entry.doctrine_status == DoctrineStatus.RETIRED:
                    # Retire pattern - update in database
                    await self._retire_pattern(doctrine_entry)
                elif doctrine_entry.doctrine_status == DoctrineStatus.CONTRAINDICATED:
                    # Contraindicate pattern - update in database
                    await self._contraindicate_pattern(doctrine_entry)
                    
        except Exception as e:
            print(f"Error promoting/retiring patterns: {e}")
    
    async def _promote_pattern(self, doctrine_entry: DoctrineEntry):
        """Promote pattern to affirmed status"""
        try:
            # Update pattern in database
            update_data = {
                'doctrine_status': doctrine_entry.doctrine_status.value,
                'success_rate': doctrine_entry.success_rate,
                'failure_rate': doctrine_entry.failure_rate,
                'evidence_count': doctrine_entry.evidence_count,
                'why_map': doctrine_entry.why_map,
                'last_updated': doctrine_entry.last_updated.isoformat()
            }
            
            await self.supabase_manager.update_strand(
                strand_id=doctrine_entry.pattern_id,
                update_data=update_data
            )
            
            print(f"✅ Promoted pattern {doctrine_entry.pattern_id} to affirmed")
            
        except Exception as e:
            print(f"Error promoting pattern: {e}")
    
    async def _retire_pattern(self, doctrine_entry: DoctrineEntry):
        """Retire pattern"""
        try:
            # Update pattern in database
            update_data = {
                'doctrine_status': doctrine_entry.doctrine_status.value,
                'success_rate': doctrine_entry.success_rate,
                'failure_rate': doctrine_entry.failure_rate,
                'evidence_count': doctrine_entry.evidence_count,
                'why_map': doctrine_entry.why_map,
                'last_updated': doctrine_entry.last_updated.isoformat()
            }
            
            await self.supabase_manager.update_strand(
                strand_id=doctrine_entry.pattern_id,
                update_data=update_data
            )
            
            print(f"✅ Retired pattern {doctrine_entry.pattern_id}")
            
        except Exception as e:
            print(f"Error retiring pattern: {e}")
    
    async def _contraindicate_pattern(self, doctrine_entry: DoctrineEntry):
        """Contraindicate pattern"""
        try:
            # Update pattern in database
            update_data = {
                'doctrine_status': doctrine_entry.doctrine_status.value,
                'success_rate': doctrine_entry.success_rate,
                'failure_rate': doctrine_entry.failure_rate,
                'evidence_count': doctrine_entry.evidence_count,
                'why_map': doctrine_entry.why_map,
                'contraindications': doctrine_entry.contraindications,
                'last_updated': doctrine_entry.last_updated.isoformat()
            }
            
            await self.supabase_manager.update_strand(
                strand_id=doctrine_entry.pattern_id,
                update_data=update_data
            )
            
            print(f"✅ Contraindicated pattern {doctrine_entry.pattern_id}")
            
        except Exception as e:
            print(f"Error contraindicating pattern: {e}")
    
    async def check_contraindication(self, pattern_type: str, pattern_id: str) -> bool:
        """Check if a pattern is contraindicated"""
        try:
            pattern_key = f"{pattern_type}:{pattern_id}"
            return pattern_key in self.contraindicated_patterns
            
        except Exception as e:
            print(f"Error checking contraindication: {e}")
            return False
    
    async def get_contraindication_reasons(self, pattern_type: str, pattern_id: str) -> List[str]:
        """Get contraindication reasons for a pattern"""
        try:
            pattern_key = f"{pattern_type}:{pattern_id}"
            return self.contraindicated_patterns.get(pattern_key, [])
            
        except Exception as e:
            print(f"Error getting contraindication reasons: {e}")
            return []
    
    async def _load_existing_doctrine(self):
        """Load existing doctrine from database"""
        try:
            query = """
                SELECT * FROM AD_strands 
                WHERE doctrine_status IS NOT NULL
                ORDER BY created_at DESC
            """
            
            result = await self.supabase_manager.execute_query(query)
            
            for row in result:
                doctrine_entry = DoctrineEntry(
                    doctrine_id=f"doctrine_{row['kind']}_{row['id']}",
                    pattern_type=row['kind'],
                    pattern_id=row['id'],
                    doctrine_status=DoctrineStatus(row.get('doctrine_status', 'provisional')),
                    evidence_count=row.get('evidence_count', 0),
                    success_rate=row.get('success_rate', 0.0),
                    failure_rate=row.get('failure_rate', 0.0),
                    last_updated=row.get('last_updated', row['created_at']),
                    lineage=row.get('lineage', {}),
                    why_map=row.get('why_map', {}),
                    contraindications=row.get('contraindications', []),
                    created_at=row['created_at']
                )
                
                self.doctrine_entries[doctrine_entry.doctrine_id] = doctrine_entry
                
        except Exception as e:
            print(f"Warning: Could not load existing doctrine: {e}")
    
    async def _load_existing_lessons(self):
        """Load existing lessons from database"""
        try:
            query = """
                SELECT * FROM AD_strands 
                WHERE kind = 'lesson'
                ORDER BY created_at DESC
            """
            
            result = await self.supabase_manager.execute_query(query)
            
            for row in result:
                lesson = Lesson(
                    lesson_id=row['id'],
                    source_type=row.get('source_type', ''),
                    source_id=row.get('source_id', ''),
                    lesson_type=row.get('lesson_type', ''),
                    lesson_content=row.get('lesson_content', ''),
                    context=row.get('context', {}),
                    confidence=row.get('confidence', 0.0),
                    created_at=row['created_at']
                )
                
                self.lessons[lesson.lesson_id] = lesson
                
        except Exception as e:
            print(f"Warning: Could not load existing lessons: {e}")
    
    async def get_doctrine_status(self) -> Dict[str, Any]:
        """Get current doctrine status"""
        return {
            'doctrine_entries_count': len(self.doctrine_entries),
            'lessons_count': len(self.lessons),
            'contraindicated_patterns_count': len(self.contraindicated_patterns),
            'doctrine_update_interval_hours': self.doctrine_update_interval_hours,
            'negative_doctrine_threshold': self.negative_doctrine_threshold,
            'min_evidence_for_affirmation': self.min_evidence_for_affirmation,
            'max_failure_rate_for_retirement': self.max_failure_rate_for_retirement
        }
    
    async def create_manual_lesson(self, source_type: str, source_id: str, 
                                 lesson_type: str, lesson_content: str) -> str:
        """Create a manual lesson"""
        try:
            lesson_id = f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            lesson = Lesson(
                lesson_id=lesson_id,
                source_type=source_type,
                source_id=source_id,
                lesson_type=lesson_type,
                lesson_content=lesson_content,
                context={'manual': True, 'created_by': 'user'},
                confidence=0.8,  # High confidence for manual lessons
                created_at=datetime.now(timezone.utc)
            )
            
            # Store lesson
            self.lessons[lesson_id] = lesson
            
            # Update doctrine from lesson
            await self._update_doctrine_from_lesson(lesson)
            
            print(f"✅ Created manual lesson {lesson_id}")
            return lesson_id
            
        except Exception as e:
            print(f"Error creating manual lesson: {e}")
            return None
