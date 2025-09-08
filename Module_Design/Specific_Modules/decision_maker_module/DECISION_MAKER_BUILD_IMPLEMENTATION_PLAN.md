# Decision Maker Module - Build Implementation Plan

*Complete implementation guide for the Decision Maker Module with lesson feedback integration and direct table communication*

## Overview

This document provides a comprehensive implementation plan for the Decision Maker Module, ensuring perfect alignment with the enhanced design documents including lesson feedback integration, strand-braid learning, and direct table communication.

## Phase 1: Database Schema Setup

### 1.1 Core Tables

```sql
-- Decision Maker strands (following direct table communication)
CREATE TABLE dm_strand (
    id TEXT PRIMARY KEY,                    -- ULID
    lifecycle_id TEXT,                      -- Thread identifier
    parent_id TEXT,                         -- Linkage to parent strand
    module TEXT DEFAULT 'dm',               -- Module identifier
    kind TEXT,                              -- 'decision'|'evaluation'|'risk_assessment'|'budget_allocation'|'braid'|'meta_braid'
    symbol TEXT,                            -- Trading symbol
    timeframe TEXT,                         -- '1m'|'5m'|'15m'|'1h'|'4h'|'1d'
    session_bucket TEXT,                    -- Session identifier
    regime TEXT,                            -- Market regime
    alpha_bundle_ref TEXT,                  -- Reference to AD_strands
    dm_alpha JSONB,                         -- Fused alpha signal data
    dm_budget JSONB,                        -- Budget allocation data
    dm_decision JSONB,                      -- Decision result
    risk_metrics JSONB,                     -- Risk assessment metrics
    portfolio_impact JSONB,                 -- Portfolio impact analysis
    asymmetries JSONB,                      -- Crypto asymmetry data
    curator_decisions JSONB,                -- Curator evaluation results
    lesson_metadata JSONB,                  -- Lesson feedback integration
    tags TEXT[],                            -- Communication tags
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for fast queries
CREATE INDEX dm_strand_symbol_time ON dm_strand(symbol, created_at DESC);
CREATE INDEX dm_strand_lifecycle ON dm_strand(lifecycle_id);
CREATE INDEX dm_strand_alpha_ref ON dm_strand(alpha_bundle_ref);
CREATE INDEX dm_strand_decision_type ON dm_strand((dm_decision->>'decision_type'));
CREATE INDEX dm_strand_kind ON dm_strand(kind);
CREATE INDEX dm_strand_lesson_metadata ON dm_strand USING GIN(lesson_metadata);
CREATE INDEX dm_strand_tags ON dm_strand USING GIN(tags);
```

### 1.2 Portfolio Management Tables

```sql
-- Portfolio state tracking
CREATE TABLE dm_portfolio_state (
    id TEXT PRIMARY KEY,
    portfolio_value DECIMAL(20,8) NOT NULL,
    cash_balance DECIMAL(20,8) NOT NULL,
    total_risk DECIMAL(8,4) NOT NULL,
    var_95 DECIMAL(8,4) NOT NULL,
    max_drawdown DECIMAL(8,4) NOT NULL,
    sharpe_ratio DECIMAL(8,4) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Position tracking
CREATE TABLE dm_positions (
    id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,                     -- 'long'|'short'
    size DECIMAL(20,8) NOT NULL,
    entry_price DECIMAL(20,8) NOT NULL,
    current_price DECIMAL(20,8) NOT NULL,
    unrealized_pnl DECIMAL(20,8) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

### 1.3 Curator Performance Tables

```sql
-- Curator performance tracking
CREATE TABLE dm_curator_performance (
    id TEXT PRIMARY KEY,
    curator_type TEXT NOT NULL,             -- 'risk_curator'|'budget_curator'|'execution_curator'
    decision_id TEXT NOT NULL,
    contribution_score DECIMAL(8,4) NOT NULL,
    accuracy_score DECIMAL(8,4) NOT NULL,
    learning_metadata JSONB,                -- Lesson feedback integration
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Curator weight tracking
CREATE TABLE dm_curator_weights (
    id TEXT PRIMARY KEY,
    curator_type TEXT NOT NULL,
    weight DECIMAL(8,4) NOT NULL,
    confidence DECIMAL(8,4) NOT NULL,
    lesson_adjustments JSONB,               -- Lesson-driven adjustments
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

### 1.4 PostgreSQL Triggers

```sql
-- Trigger for dm_strand notifications
CREATE OR REPLACE FUNCTION notify_decision_maker_strands()
RETURNS TRIGGER AS $$
BEGIN
    -- Check if tags contain trader:execute
    IF NEW.tags @> '["trader:execute"]'::jsonb THEN
        PERFORM pg_notify('trader_strand_notification', 
            json_build_object(
                'strand_id', NEW.id,
                'module', NEW.module,
                'kind', NEW.kind,
                'tags', NEW.tags
            )::text
        );
    END IF;
    
    -- Check if tags contain alpha:feedback
    IF NEW.tags @> '["alpha:feedback"]'::jsonb THEN
        PERFORM pg_notify('alpha_detector_strand_notification', 
            json_build_object(
                'strand_id', NEW.id,
                'module', NEW.module,
                'kind', NEW.kind,
                'tags', NEW.tags
            )::text
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER decision_maker_strand_notify
    AFTER INSERT OR UPDATE ON dm_strand
    FOR EACH ROW
    EXECUTE FUNCTION notify_decision_maker_strands();
```

## Phase 2: Core Implementation

### 2.1 Lesson Feedback Integration

```python
# File: learning/lesson_feedback_system.py
from learning_systems import LessonFeedbackSystem, LessonEnhancedCuratorOrchestrator
from core_intelligence_architecture import CuratorRegistry, BaseCurator

class DecisionMakerLessonFeedback:
    """Lesson feedback integration for Decision Maker"""
    
    def __init__(self, module_type: str):
        self.module_type = module_type
        self.lesson_feedback = LessonFeedbackSystem(module_type)
        self.lesson_enhanced_curator = LessonEnhancedCuratorOrchestrator(module_type)
        self.db_client = DatabaseClient()
    
    def enhance_decision_with_lessons(self, context: Dict) -> Dict:
        """Enhance decision context with learned lessons"""
        
        # 1. Get relevant lessons for current context
        relevant_lessons = self._get_relevant_lessons(context)
        
        # 2. Apply lesson recommendations to context
        enhanced_context = self._apply_lesson_recommendations(context, relevant_lessons)
        
        # 3. Update curator weights based on lesson insights
        self._update_curator_weights_from_lessons(relevant_lessons)
        
        # 4. Adapt module parameters based on lessons
        self._adapt_parameters_from_lessons(relevant_lessons)
        
        return enhanced_context
    
    def _get_relevant_lessons(self, context: Dict) -> List[Dict]:
        """Get relevant lessons for current decision context"""
        
        # Query lessons based on context similarity
        lessons = self.db_client.fetch_all("""
            SELECT * FROM dm_strand 
            WHERE kind IN ('braid', 'meta_braid', 'meta2_braid')
            AND lesson_metadata @> %s
            ORDER BY created_at DESC
            LIMIT 10
        """, json.dumps({
            'symbol': context.get('symbol'),
            'timeframe': context.get('timeframe'),
            'regime': context.get('regime')
        }))
        
        return lessons
    
    def _apply_lesson_recommendations(self, context: Dict, lessons: List[Dict]) -> Dict:
        """Apply lesson recommendations to decision context"""
        
        enhanced_context = context.copy()
        lessons_applied = []
        confidence_boost = 1.0
        
        for lesson in lessons:
            lesson_data = lesson.get('lesson_metadata', {})
            recommendations = lesson_data.get('recommendations', [])
            
            for recommendation in recommendations:
                if self._is_recommendation_applicable(recommendation, context):
                    enhanced_context = self._apply_recommendation(enhanced_context, recommendation)
                    lessons_applied.append(lesson['id'])
                    confidence_boost *= lesson_data.get('confidence', 1.0)
        
        enhanced_context['lessons_applied'] = lessons_applied
        enhanced_context['confidence_boost'] = confidence_boost
        
        return enhanced_context
```

### 2.2 Strand-Braid Learning System

```python
# File: learning/strand_braid_learning.py
from learning_systems import StrandBraidLearning, LLMClient

class DecisionMakerStrandBraidLearning:
    """Strand-braid learning system for Decision Maker"""
    
    def __init__(self, module_type: str):
        self.module_type = module_type
        self.db_client = DatabaseClient()
        self.llm_client = LLMClient()
        
    def create_decision_strand(self, decision_data: Dict, outcome: Optional[Dict] = None) -> str:
        """Create a new decision strand"""
        
        strand_id = generate_ulid()
        strand_data = {
            'id': strand_id,
            'lifecycle_id': decision_data.get('lifecycle_id'),
            'module': 'dm',
            'kind': 'decision',
            'symbol': decision_data.get('symbol'),
            'timeframe': decision_data.get('timeframe'),
            'dm_decision': decision_data.get('decision'),
            'risk_metrics': decision_data.get('risk_metrics'),
            'portfolio_impact': decision_data.get('portfolio_impact'),
            'outcome': outcome,
            'lesson_metadata': decision_data.get('lesson_metadata', {}),
            'created_at': datetime.now(timezone.utc)
        }
        
        # Insert into dm_strand table
        self.db_client.execute("""
            INSERT INTO dm_strand (
                id, lifecycle_id, module, kind, symbol, timeframe,
                dm_decision, risk_metrics, portfolio_impact, outcome, lesson_metadata
            ) VALUES (
                %(id)s, %(lifecycle_id)s, %(module)s, %(kind)s, %(symbol)s, %(timeframe)s,
                %(dm_decision)s, %(risk_metrics)s, %(portfolio_impact)s, %(outcome)s, %(lesson_metadata)s
            )
        """, strand_data)
        
        return strand_id
    
    def cluster_decision_strands(self, threshold: int = 3) -> List[Dict]:
        """Cluster decision strands by similarity"""
        
        # Get recent decision strands
        strands = self.db_client.fetch_all("""
            SELECT * FROM dm_strand 
            WHERE module = 'dm' AND kind = 'decision'
            AND created_at > NOW() - INTERVAL '30 days'
            ORDER BY created_at DESC
        """)
        
        # Cluster by top-level columns
        clusters = self._cluster_by_columns(strands, [
            'symbol', 'timeframe', 'regime', 'decision_type', 'outcome_type'
        ])
        
        # Create braids for clusters above threshold
        braids = []
        for cluster in clusters:
            if len(cluster['strands']) >= threshold:
                braid = self._create_decision_braid(cluster)
                braids.append(braid)
        
        return braids
    
    def _create_decision_braid(self, cluster: Dict) -> Dict:
        """Create a braid from clustered decision strands"""
        
        # Send to LLM for lesson generation
        lesson = self.llm_client.generate_lesson({
            'strands': cluster['strands'],
            'context': f"Decision Maker decisions for {cluster['symbol']} in {cluster['timeframe']} timeframe",
            'module_type': 'decision_maker'
        })
        
        # Create braid strand
        braid_id = generate_ulid()
        braid_data = {
            'id': braid_id,
            'lifecycle_id': f"braid_{cluster['cluster_id']}",
            'module': 'dm',
            'kind': 'braid',
            'symbol': cluster['symbol'],
            'timeframe': cluster['timeframe'],
            'dm_decision': {
                'lesson': lesson,
                'source_strands': [s['id'] for s in cluster['strands']],
                'accumulated_score': sum(s.get('decision_score', 0) for s in cluster['strands']),
                'cluster_columns': cluster['columns']
            },
            'lesson_metadata': {
                'lesson_type': 'decision_braid',
                'confidence': lesson.get('confidence', 0.0),
                'recommendations': lesson.get('recommendations', [])
            },
            'created_at': datetime.now(timezone.utc)
        }
        
        # Insert braid into dm_strand table
        self.db_client.execute("""
            INSERT INTO dm_strand (
                id, lifecycle_id, module, kind, symbol, timeframe, dm_decision, lesson_metadata
            ) VALUES (
                %(id)s, %(lifecycle_id)s, %(module)s, %(kind)s, %(symbol)s, %(timeframe)s,
                %(dm_decision)s, %(lesson_metadata)s
            )
        """, braid_data)
        
        return braid_data
```

### 2.3 Direct Table Communication

```python
# File: communication/decision_maker_communicator.py
from communication_protocol import DirectTableCommunicator, ModuleListener

class DecisionMakerCommunicator:
    """Direct table communication for Decision Maker"""
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.module_name = 'dm'
        self.listener = ModuleListener('dm')
        
        # Lesson feedback integration
        self.lesson_feedback = LessonFeedbackSystem('decision_maker')
        self.lesson_enhanced_curator = LessonEnhancedCuratorOrchestrator('decision_maker')
    
    def listen_for_alpha_signals(self):
        """Listen for alpha signals from Alpha Detector"""
        self.listener.listen('ad_strand_notification', self._process_alpha_signal)
    
    def listen_for_risk_updates(self):
        """Listen for risk updates from Risk Manager"""
        self.listener.listen('rm_strand_notification', self._process_risk_update)
    
    def listen_for_market_data(self):
        """Listen for market data updates"""
        self.listener.listen('md_strand_notification', self._process_market_data)
    
    def _process_alpha_signal(self, notification_data):
        """Process alpha signal with lesson enhancement"""
        strand_id = notification_data['strand_id']
        
        # Read alpha signal from AD_strands table
        alpha_signal = self.db.fetch_one("""
            SELECT * FROM AD_strands 
            WHERE id = %s AND tags @> %s
        """, strand_id, ['dm:evaluate'])
        
        if alpha_signal:
            # Process with lesson feedback
            decision = self._evaluate_alpha_signal_with_lessons(alpha_signal)
            
            if decision:
                # Send decision to Trader
                self._send_decision_to_trader(decision, ['trader:execute'])
                
                # Send feedback to Alpha Detector
                self._send_feedback_to_alpha_detector(decision, ['alpha:feedback'])
    
    def _evaluate_alpha_signal_with_lessons(self, alpha_signal: Dict) -> Optional[Dict]:
        """Evaluate alpha signal with lesson-enhanced decision making"""
        
        # 1. Prepare context for lesson application
        context = self._prepare_decision_context(alpha_signal)
        
        # 2. Apply lesson feedback to enhance context
        enhanced_context = self.lesson_feedback.apply_lessons_to_decisions(context)
        
        # 3. Apply lesson-enhanced curator evaluation
        curated_decision, approved, contributions = self.lesson_enhanced_curator.curate_signal_with_lessons(
            alpha_signal.get('signal_strength', 0.0), enhanced_context
        )
        
        # 4. Generate decision if approved
        if approved:
            decision = self._generate_decision(alpha_signal, curated_decision, enhanced_context)
            
            # 5. Add lesson metadata to decision
            decision['lesson_enhanced'] = True
            decision['lessons_applied'] = enhanced_context.get('lessons_applied', [])
            decision['confidence_boost'] = enhanced_context.get('confidence_boost', 1.0)
            
            return decision
            
        return None
    
    def send_decision_to_trader(self, decision_data: Dict, tags: List[str]):
        """Send decision to Trader via dm_strand table"""
        
        # Write decision to dm_strand table
        decision_strand = {
            'id': generate_ulid(),
            'lifecycle_id': decision_data.get('lifecycle_id'),
            'module': 'dm',
            'kind': 'decision',
            'symbol': decision_data.get('symbol'),
            'timeframe': decision_data.get('timeframe'),
            'dm_decision': decision_data.get('decision'),
            'risk_metrics': decision_data.get('risk_metrics'),
            'portfolio_impact': decision_data.get('portfolio_impact'),
            'lesson_metadata': decision_data.get('lesson_metadata', {}),
            'tags': tags  # ['trader:execute', 'priority:high']
        }
        
        # Insert into dm_strand table
        self.db.execute("""
            INSERT INTO dm_strand (
                id, lifecycle_id, module, kind, symbol, timeframe,
                dm_decision, risk_metrics, portfolio_impact, lesson_metadata, tags
            ) VALUES (
                %(id)s, %(lifecycle_id)s, %(module)s, %(kind)s, %(symbol)s, %(timeframe)s,
                %(dm_decision)s, %(risk_metrics)s, %(portfolio_impact)s, %(lesson_metadata)s, %(tags)s
            )
        """, decision_strand)
        
        # Trigger pg_notify for Trader
        self.db.execute("""
            NOTIFY trader_strand_notification, %s
        """, json.dumps({
            'strand_id': decision_strand['id'],
            'module': 'dm',
            'kind': 'decision',
            'tags': tags
        }))
    
    def send_feedback_to_alpha_detector(self, feedback_data: Dict, tags: List[str]):
        """Send feedback to Alpha Detector via dm_strand table"""
        
        # Write feedback to dm_strand table
        feedback_strand = {
            'id': generate_ulid(),
            'lifecycle_id': feedback_data.get('lifecycle_id'),
            'module': 'dm',
            'kind': 'feedback',
            'symbol': feedback_data.get('symbol'),
            'alpha_bundle_ref': feedback_data.get('alpha_bundle_ref'),
            'dm_decision': feedback_data.get('feedback'),
            'lesson_metadata': feedback_data.get('lesson_metadata', {}),
            'tags': tags  # ['alpha:feedback', 'learning:update']
        }
        
        # Insert into dm_strand table
        self.db.execute("""
            INSERT INTO dm_strand (
                id, lifecycle_id, module, kind, symbol, alpha_bundle_ref,
                dm_decision, lesson_metadata, tags
            ) VALUES (
                %(id)s, %(lifecycle_id)s, %(module)s, %(kind)s, %(symbol)s, %(alpha_bundle_ref)s,
                %(dm_decision)s, %(lesson_metadata)s, %(tags)s
            )
        """, feedback_strand)
        
        # Trigger pg_notify for Alpha Detector
        self.db.execute("""
            NOTIFY alpha_detector_strand_notification, %s
        """, json.dumps({
            'strand_id': feedback_strand['id'],
            'module': 'dm',
            'kind': 'feedback',
            'tags': tags
        }))
```

## Phase 3: Enhanced Decision Maker Module

### 3.1 Core Module Implementation

```python
# File: decision_maker_module.py
from core_intelligence_architecture import CuratorOrchestrator, BaseCurator
from learning_systems import LessonFeedbackSystem, StrandBraidLearning
from communication_protocol import DirectTableCommunicator

class EnhancedDecisionMakerModule:
    """Enhanced Decision Maker Module with lesson feedback integration"""
    
    def __init__(self, module_id: str, parent_modules=None):
        self.module_id = module_id
        self.module_type = 'decision_maker'
        self.parent_modules = parent_modules or []
        
        # Module Intelligence
        self.learning_rate = 0.01
        self.adaptation_threshold = 0.7
        self.performance_history = []
        self.learning_patterns = {}
        self.innovation_score = 0.0
        self.specialization_index = 0.0
        
        # Core Decision Maker Components
        self.risk_assessor = self.initialize_risk_assessor()
        self.budget_allocator = self.initialize_budget_allocator()
        self.portfolio_manager = self.initialize_portfolio_manager()
        self.curator_layer = self.initialize_curator_layer()
        
        # Lesson feedback integration
        self.lesson_feedback = LessonFeedbackSystem('decision_maker')
        self.lesson_enhanced_curator = LessonEnhancedCuratorOrchestrator('decision_maker')
        self.real_time_lesson_app = RealTimeLessonApplication('decision_maker')
        self.strand_braid_learning = StrandBraidLearning('decision_maker')
        
        # Communication
        self.communicator = DecisionMakerCommunicator(self.db_connection)
    
    def process_alpha_signal_with_lessons(self, alpha_signal: Dict) -> Optional[Dict]:
        """Process alpha signal with lesson-enhanced decision making"""
        
        # 1. Apply lesson feedback to enhance context
        enhanced_context = self.lesson_feedback.apply_lessons_to_decisions(alpha_signal)
        
        # 2. Apply lesson-enhanced curator evaluation
        curated_decision, approved, contributions = self.lesson_enhanced_curator.curate_signal_with_lessons(
            alpha_signal.get('signal_strength', 0.0), enhanced_context
        )
        
        # 3. Generate decision if approved
        if approved:
            decision = self._generate_decision(alpha_signal, curated_decision, enhanced_context)
            
            # 4. Add lesson metadata to decision
            decision['lesson_enhanced'] = True
            decision['lessons_applied'] = enhanced_context.get('lessons_applied', [])
            decision['confidence_boost'] = enhanced_context.get('confidence_boost', 1.0)
            
            return decision
            
        return None
    
    def _generate_decision(self, alpha_signal: Dict, curated_decision: Dict, context: Dict) -> Dict:
        """Generate trading decision with lesson enhancement"""
        
        # Risk assessment with lesson enhancement
        risk_assessment = self.risk_assessor.assess_risk_with_lessons(
            alpha_signal, context
        )
        
        # Budget allocation with lesson enhancement
        budget_allocation = self.budget_allocator.allocate_budget_with_lessons(
            alpha_signal, risk_assessment, context
        )
        
        # Portfolio impact with lesson enhancement
        portfolio_impact = self.portfolio_manager.assess_portfolio_impact_with_lessons(
            alpha_signal, budget_allocation, context
        )
        
        # Generate final decision
        decision = {
            'decision_id': generate_ulid(),
            'lifecycle_id': alpha_signal.get('lifecycle_id'),
            'symbol': alpha_signal.get('symbol'),
            'timeframe': alpha_signal.get('timeframe'),
            'decision_type': 'execute' if curated_decision['approved'] else 'reject',
            'signal_strength': curated_decision['score'],
            'risk_assessment': risk_assessment,
            'budget_allocation': budget_allocation,
            'portfolio_impact': portfolio_impact,
            'curator_contributions': context.get('curator_contributions', []),
            'lesson_metadata': {
                'lesson_enhanced': True,
                'lessons_applied': context.get('lessons_applied', []),
                'confidence_boost': context.get('confidence_boost', 1.0)
            },
            'created_at': datetime.now(timezone.utc)
        }
        
        return decision
```

## Phase 4: Testing and Validation

### 4.1 Unit Tests

```python
# File: tests/test_decision_maker_lesson_feedback.py
import pytest
from decision_maker_module import EnhancedDecisionMakerModule
from learning_systems import LessonFeedbackSystem

class TestDecisionMakerLessonFeedback:
    
    def test_lesson_feedback_integration(self):
        """Test lesson feedback integration"""
        dm = EnhancedDecisionMakerModule('dm_001')
        
        # Test lesson enhancement
        context = {'symbol': 'BTC', 'timeframe': '1h', 'regime': 'bull'}
        enhanced_context = dm.lesson_feedback.apply_lessons_to_decisions(context)
        
        assert 'lessons_applied' in enhanced_context
        assert 'confidence_boost' in enhanced_context
    
    def test_strand_braid_learning(self):
        """Test strand-braid learning system"""
        dm = EnhancedDecisionMakerModule('dm_001')
        
        # Test strand creation
        decision_data = {
            'symbol': 'BTC',
            'timeframe': '1h',
            'decision': {'action': 'buy', 'confidence': 0.8}
        }
        
        strand_id = dm.strand_braid_learning.create_decision_strand(decision_data)
        assert strand_id is not None
    
    def test_curator_lesson_enhancement(self):
        """Test curator lesson enhancement"""
        dm = EnhancedDecisionMakerModule('dm_001')
        
        # Test lesson-enhanced curator evaluation
        context = {'symbol': 'BTC', 'timeframe': '1h'}
        curated_decision, approved, contributions = dm.lesson_enhanced_curator.curate_signal_with_lessons(
            0.8, context
        )
        
        assert isinstance(curated_decision, dict)
        assert isinstance(approved, bool)
        assert isinstance(contributions, list)
```

### 4.2 Integration Tests

```python
# File: tests/test_decision_maker_integration.py
import pytest
from decision_maker_module import EnhancedDecisionMakerModule
from communication_protocol import DirectTableCommunicator

class TestDecisionMakerIntegration:
    
    def test_alpha_signal_processing(self):
        """Test alpha signal processing with lesson feedback"""
        dm = EnhancedDecisionMakerModule('dm_001')
        
        alpha_signal = {
            'id': 'ad_001',
            'symbol': 'BTC',
            'timeframe': '1h',
            'signal_strength': 0.8,
            'trading_plan': {'action': 'buy', 'size': 0.1}
        }
        
        decision = dm.process_alpha_signal_with_lessons(alpha_signal)
        
        if decision:
            assert decision['lesson_enhanced'] == True
            assert 'lessons_applied' in decision
            assert 'confidence_boost' in decision
    
    def test_communication_flow(self):
        """Test communication flow with other modules"""
        dm = EnhancedDecisionMakerModule('dm_001')
        
        # Test listening for alpha signals
        dm.communicator.listen_for_alpha_signals()
        
        # Test sending decisions to trader
        decision_data = {
            'symbol': 'BTC',
            'decision': {'action': 'buy', 'size': 0.1}
        }
        
        dm.communicator.send_decision_to_trader(decision_data, ['trader:execute'])
        
        # Verify decision was written to dm_strand table
        # (Implementation depends on test database setup)
```

## Phase 5: Configuration and Deployment

### 5.1 Configuration File

```yaml
# File: config/decision_maker_config.yaml
decision_maker:
  module_id: "dm_001"
  module_type: "decision_maker"
  
  # Learning Configuration
  learning:
    learning_rate: 0.01
    adaptation_threshold: 0.1
    curator_learning_enabled: true
    strand_braid_learning_enabled: true
    lesson_feedback_enabled: true
    
  # Communication Configuration
  communication:
    type: "direct_table"
    db_connection: "postgresql://user:pass@localhost:5432/trading_intelligence"
    listen_channels:
      - "ad_strand_notification"
      - "rm_strand_notification"
      - "md_strand_notification"
    
  # Curator Configuration
  curators:
    risk_curator:
      weight: 0.3
      threshold: 0.7
      lesson_enhanced: true
    budget_curator:
      weight: 0.25
      threshold: 0.6
      lesson_enhanced: true
    execution_curator:
      weight: 0.2
      threshold: 0.8
      lesson_enhanced: true
    portfolio_curator:
      weight: 0.25
      threshold: 0.75
      lesson_enhanced: true
```

### 5.2 Deployment Script

```bash
#!/bin/bash
# File: deploy_decision_maker.sh

echo "Deploying Decision Maker Module with Lesson Feedback Integration..."

# 1. Create database tables
echo "Creating database tables..."
psql -d trading_intelligence -f sql/dm_strand_schema.sql
psql -d trading_intelligence -f sql/dm_portfolio_schema.sql
psql -d trading_intelligence -f sql/dm_curator_schema.sql
psql -d trading_intelligence -f sql/dm_triggers.sql

# 2. Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# 3. Run tests
echo "Running tests..."
python -m pytest tests/test_decision_maker_lesson_feedback.py -v
python -m pytest tests/test_decision_maker_integration.py -v

# 4. Start Decision Maker module
echo "Starting Decision Maker module..."
python decision_maker_module.py --config config/decision_maker_config.yaml

echo "Decision Maker Module deployed successfully!"
```

## Phase 6: Monitoring and Maintenance

### 6.1 Performance Monitoring

```python
# File: monitoring/decision_maker_monitor.py
class DecisionMakerMonitor:
    """Monitor Decision Maker performance and lesson feedback effectiveness"""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def monitor_lesson_feedback_effectiveness(self):
        """Monitor lesson feedback effectiveness"""
        
        # Query lesson-enhanced decisions
        lesson_enhanced_decisions = self.db.fetch_all("""
            SELECT * FROM dm_strand 
            WHERE lesson_metadata @> '{"lesson_enhanced": true}'
            AND created_at > NOW() - INTERVAL '24 hours'
        """)
        
        # Calculate effectiveness metrics
        total_decisions = len(lesson_enhanced_decisions)
        successful_decisions = len([d for d in lesson_enhanced_decisions 
                                  if d.get('outcome', {}).get('success', False)])
        
        effectiveness_rate = successful_decisions / total_decisions if total_decisions > 0 else 0
        
        return {
            'total_decisions': total_decisions,
            'successful_decisions': successful_decisions,
            'effectiveness_rate': effectiveness_rate
        }
    
    def monitor_curator_learning(self):
        """Monitor curator learning progress"""
        
        # Query curator performance
        curator_performance = self.db.fetch_all("""
            SELECT curator_type, AVG(accuracy_score) as avg_accuracy
            FROM dm_curator_performance 
            WHERE created_at > NOW() - INTERVAL '7 days'
            GROUP BY curator_type
        """)
        
        return curator_performance
```

## Integration Benefits

### **1. Lesson Feedback Loop** ✅
- **Real-time lesson application** - Lessons enhance decisions immediately
- **Curator learning** - Lessons improve curator weights and thresholds
- **Performance tracking** - Outcomes create new learning strands

### **2. Strand-Braid Learning** ✅
- **Hierarchical learning** - Strands → Braids → Meta-braids
- **LLM lesson generation** - Natural language insights
- **Cross-module learning** - Lessons can influence other modules

### **3. Direct Table Communication** ✅
- **Simplified architecture** - No complex message bus
- **Module independence** - Each module owns its data
- **Clear tagging system** - Explicit communication patterns

### **4. Enhanced Decision Making** ✅
- **Lesson-enhanced context** - Decisions use learned insights
- **Curator orchestration** - Multiple curators with lesson feedback
- **Performance improvement** - Continuous learning and adaptation

---

*This implementation plan provides a complete guide for building the Decision Maker Module with lesson feedback integration, ensuring perfect alignment with the enhanced design documents while maintaining the central hub role of the Decision Maker in the Trading Intelligence System.*
