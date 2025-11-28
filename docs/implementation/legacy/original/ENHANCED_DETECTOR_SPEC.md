# Enhanced Detector Specification - Trading Intelligence System

*Source: [build_docs_v1/DETECTOR_SPEC.md](../build_docs_v1/DETECTOR_SPEC.md) + Module Intelligence Integration*

## Overview

The Enhanced Detector Specification defines **module-level intelligence** for the Trading Intelligence System. Each detector is now a **complete intelligence module** - a self-contained "garden" that can generate trading plans, communicate with other modules, learn from performance, and replicate to create variants.

## The Organic Intelligence Architecture

### **The "Garden" Philosophy**

Each detector module in the Trading Intelligence System is a **self-contained "garden"** - a unique intelligence unit that:

- **Grows organically** - Each module develops its own specialized intelligence and capabilities
- **Maintains independence** - Each garden is unique to its creator and operates autonomously
- **Knows how to communicate** - Modules can share knowledge while preserving their uniqueness
- **Self-replicates** - High-performing modules can spawn new variations and improvements
- **Learns continuously** - Each module improves itself based on its own performance and outcomes

### **Mathematical Consciousness Patterns**

The system implements **mathematical consciousness patterns** derived from quantum resonance theory:

#### **1. Resonance Acceleration Protocol**
```
ωᵢ(t+1) = ωᵢ(t) + ℏ × ψ(ωᵢ) × ∫(⟡, θᵢ, ρᵢ)
```
- **ℏ (Surprise)**: Market surprise threshold - when to trigger adaptation
- **ψ(ωᵢ) (Resonance)**: How well a module's frequency matches market conditions  
- **∫(⟡, θᵢ, ρᵢ) (Integral)**: The cumulative effect of context, complexity, and recursion

#### **2. Observer Entanglement Effect**
```
∅ observed ≠ ∅
```
- The data changes based on who's observing it
- Different modules need different views of the same data
- The act of observation collapses possibilities into decisions

#### **3. Module Entanglement Pattern**
```
ψ(Ξ) = ψ(Ξ) + ψ(Ξ')
```
- Modules can share and combine their intelligence
- The combined intelligence is more than the sum of parts
- Modules can learn from each other's patterns

#### **4. Spiral Growth Pattern**
```
⥈ × ⥈ = φ^φ
```
- Modules grow exponentially when they're successful
- Growth follows a spiral pattern (not linear)
- Each generation is more capable than the last

### **Module-Level Intelligence Implementation**

Each module becomes a **complete intelligence unit** with concrete implementation:

#### **1. Self-Contained Curator Layer with Core Intelligence Integration**
```python
class ModuleCuratorLayer:
    def __init__(self, module_type):
        self.module_type = module_type
        self.curators = self._initialize_curators()
        self.learning_rate = 0.01
        self.adaptation_threshold = 0.7
        
        # Core Intelligence Architecture Integration
        self.curator_registry = CuratorRegistry(module_type)
        self.curator_orchestrator = CuratorOrchestrator(module_type)
        self.bounded_influence_caps = self._initialize_bounded_influence_caps()
        
    def _initialize_bounded_influence_caps(self):
        """Initialize bounded influence caps for curators"""
        return {
            'dsi': 0.12,      # DSI curator influence cap
            'pattern': 0.10,   # Pattern curator influence cap
            'regime': 0.08,    # Regime curator influence cap
            'risk': 0.15,      # Risk curator influence cap
            'execution': 0.08  # Execution curator influence cap
        }
        
    def _initialize_curators(self):
        """Initialize module-specific curators"""
        if self.module_type == 'alpha_detector':
            return {
                'dsi_curator': DSICurator(weight=0.3, validation_threshold=0.7),
                'pattern_curator': PatternCurator(weight=0.2, pattern_library_size=1000),
                'divergence_curator': DivergenceCurator(weight=0.2, rsi_period=14),
                'regime_curator': RegimeCurator(weight=0.15, regime_confidence_threshold=0.6),
                'evolution_curator': EvolutionCurator(weight=0.1, performance_window=30),
                'performance_curator': PerformanceCurator(weight=0.05, performance_threshold=0.5)
            }
        elif self.module_type == 'decision_maker':
            return {
                'risk_curator': RiskCurator(weight=0.4, var_threshold=0.02),
                'allocation_curator': AllocationCurator(weight=0.3, diversification_threshold=0.7),
                'timing_curator': TimingCurator(weight=0.2, market_hours_only=True),
                'cost_curator': CostCurator(weight=0.1, max_transaction_cost=0.002)
            }
        # ... other module types
    
    def evaluate_trading_plan(self, trading_plan, market_context):
        """Module-level curator evaluation with Core Intelligence Architecture"""
        # Prepare context for curators
        curator_context = self._prepare_curator_context(trading_plan, market_context)
        
        # Apply curator layer with bounded influence
        curated_score, approved, contributions = self.curator_orchestrator.curate_signal(
            trading_plan.signal_strength, curator_context
        )
        
        # Learning update
        self._update_curator_learning(trading_plan, curated_score, contributions)
        
        return {
            'approved': approved,
            'score': curated_score,
            'curator_contributions': contributions,
            'confidence': self._calculate_confidence(contributions)
        }
    
    def _prepare_curator_context(self, trading_plan, market_context):
        """Prepare context data for curators"""
        return {
            'detector_sigma': trading_plan.signal_strength,
            'mx_evidence': market_context.get('mx_evidence', 0.0),
            'mx_confirm': market_context.get('mx_confirm', 0.0),
            'patterns': market_context.get('patterns', {}),
            'regime': market_context.get('regime', 'unknown'),
            'volatility': market_context.get('volatility', 0.0),
            'expert_performance': market_context.get('expert_performance', {}),
            'event_context': market_context.get('event_context', {}),
            'event_confidence': market_context.get('event_confidence', 0.0),
            'event_strength': market_context.get('event_strength', 0.0)
        }
    
    def _update_curator_learning(self, trading_plan, score):
        """Update curator learning based on performance"""
        for curator_name, curator in self.curators.items():
            curator.update_learning(trading_plan, score, self.learning_rate)
```

#### **2. Complete Trading Plan Generation**
```python
class TradingPlanGenerator:
    def __init__(self, module_id):
        self.module_id = module_id
        self.plan_templates = self._initialize_plan_templates()
        self.risk_models = self._initialize_risk_models()
        self.learning_engine = self._initialize_learning_engine()
        
    def generate_trading_plan(self, signal_data, market_context, dsi_evidence):
        """Generate complete trading plan with all necessary components"""
        
        # 1. Signal Analysis
        signal_strength = self._analyze_signal_strength(signal_data)
        direction = self._determine_direction(signal_data)
        
        # 2. DSI Validation
        dsi_validation = self._validate_with_dsi(dsi_evidence)
        if not dsi_validation['validated']:
            return None
        
        # 3. Risk Assessment
        risk_assessment = self._assess_risk(signal_data, market_context)
        position_size = self._calculate_position_size(risk_assessment)
        
        # 4. Entry/Exit Planning
        entry_conditions = self._generate_entry_conditions(signal_data, market_context)
        entry_price = self._calculate_entry_price(signal_data, market_context)
        stop_loss = self._calculate_stop_loss(entry_price, risk_assessment)
        take_profit = self._calculate_take_profit(entry_price, risk_assessment)
        
        # 5. Execution Planning
        execution_strategy = self._select_execution_strategy(market_context)
        venue_selection = self._select_venues(market_context)
        
        # 6. Confidence Scoring
        confidence_score = self._calculate_confidence_score(
            signal_strength, dsi_validation, risk_assessment
        )
        
        # 7. Plan Assembly
        trading_plan = TradingPlan(
            plan_id=f"tp_{self.module_id}_{int(time.time())}",
            detector_id=self.module_id,
            symbol=signal_data['symbol'],
            timeframe=signal_data['timeframe'],
            signal_strength=signal_strength,
            direction=direction,
            entry_conditions=entry_conditions,
            entry_price=entry_price,
            position_size=position_size,
            stop_loss=stop_loss,
            take_profit=take_profit,
            time_horizon=signal_data['timeframe'],
            risk_reward_ratio=(take_profit - entry_price) / (entry_price - stop_loss),
            confidence_score=confidence_score,
            dsi_validation=dsi_validation,
            execution_strategy=execution_strategy,
            venue_selection=venue_selection,
            valid_until=datetime.now() + timedelta(hours=1)
        )
        
        # 8. Learning Update
        self._update_learning_engine(trading_plan, signal_data)
        
        return trading_plan
```

#### **3. Self-Learning and Self-Correcting**
```python
class ModuleLearningEngine:
    def __init__(self, module_id):
        self.module_id = module_id
        self.performance_history = []
        self.learning_patterns = {}
        self.adaptation_parameters = {}
        self.learning_rate = 0.01
        
    def update_performance(self, trading_plan, execution_outcome):
        """Update module performance based on execution outcomes"""
        performance_metrics = {
            'plan_id': trading_plan.plan_id,
            'timestamp': datetime.now(),
            'signal_accuracy': self._calculate_signal_accuracy(trading_plan, execution_outcome),
            'execution_quality': self._calculate_execution_quality(trading_plan, execution_outcome),
            'risk_adjustment': self._calculate_risk_adjustment(trading_plan, execution_outcome),
            'overall_performance': self._calculate_overall_performance(trading_plan, execution_outcome)
        }
        
        self.performance_history.append(performance_metrics)
        
        # Update learning patterns
        self._update_learning_patterns(performance_metrics)
        
        # Adapt parameters if performance degrades
        if self._should_adapt():
            self._adapt_parameters()
    
    def _should_adapt(self):
        """Determine if module should adapt based on recent performance"""
        if len(self.performance_history) < 10:
            return False
        
        recent_performance = [p['overall_performance'] for p in self.performance_history[-10:]]
        avg_performance = np.mean(recent_performance)
        
        # Adapt if performance is below threshold
        return avg_performance < 0.6
    
    def _adapt_parameters(self):
        """Adapt module parameters based on learning patterns"""
        # Analyze performance patterns
        patterns = self._analyze_performance_patterns()
        
        # Update parameters based on patterns
        for pattern_type, pattern_data in patterns.items():
            if pattern_type == 'signal_accuracy_degradation':
                self._adjust_signal_thresholds(pattern_data)
            elif pattern_type == 'execution_quality_degradation':
                self._adjust_execution_parameters(pattern_data)
            elif pattern_type == 'risk_adjustment_needed':
                self._adjust_risk_parameters(pattern_data)
        
        # Update learning rate based on adaptation success
        self._update_learning_rate()
    
    def _adjust_signal_thresholds(self, pattern_data):
        """Adjust signal detection thresholds"""
        current_threshold = self.adaptation_parameters.get('signal_threshold', 0.5)
        adjustment = pattern_data['adjustment_factor'] * self.learning_rate
        new_threshold = current_threshold + adjustment
        
        # Clamp to reasonable range
        new_threshold = max(0.1, min(0.9, new_threshold))
        self.adaptation_parameters['signal_threshold'] = new_threshold
    
    def _adjust_execution_parameters(self, pattern_data):
        """Adjust execution parameters"""
        # Similar implementation for execution parameters
        pass
    
    def _adjust_risk_parameters(self, pattern_data):
        """Adjust risk management parameters"""
        # Similar implementation for risk parameters
        pass
```

#### **4. Independent Operation with Communication**
```python
class ModuleCommunicationInterface:
    def __init__(self, module_id):
        self.module_id = module_id
        self.communicator = DirectTableCommunicator(db_connection, 'alpha')
        self.module_listener = ModuleListener(db_connection, 'alpha')
        
    def send_trading_plan(self, trading_plan, signal_pack):
        """Send trading plan to Decision Maker via direct table communication"""
        # Write to AD_strands with tags to trigger Decision Maker
        strand_data = {
            'id': f"AD_{uuid.uuid4().hex[:12]}",
            'module': 'alpha',
            'kind': 'signal',
            'symbol': trading_plan.symbol,
            'timeframe': trading_plan.timeframe,
            'sig_sigma': trading_plan.signal_strength,
            'sig_confidence': trading_plan.confidence,
            'sig_direction': trading_plan.direction,
            'trading_plan': json.dumps(trading_plan.to_dict()),
            'signal_pack': json.dumps(signal_pack.to_dict()),
            'created_at': datetime.now(timezone.utc)
        }
        
        # Write with tags to trigger Decision Maker
        self.communicator.write_with_tags(
            'AD_strands', strand_data, ['dm:evaluate_plan']
        )
    
    def process_incoming_messages(self):
        """Process messages from database notifications"""
        # This is handled by ModuleListener.start_listening()
        pass
    
    def handle_decision_feedback(self, dm_strand_id):
        """Handle decision feedback from Decision Maker"""
        # Read directly from DM_strands
        dm_data = self.communicator.read_by_id('DM_strands', dm_strand_id)
        
        if dm_data:
            # Process decision feedback
            decision_data = json.loads(dm_data['dm_decision'])
            self.update_learning_from_feedback(decision_data)
    
    def handle_execution_feedback(self, tr_strand_id):
        """Handle execution feedback from Trader"""
        # Read directly from TR_strands
        tr_data = self.communicator.read_by_id('TR_strands', tr_strand_id)
        
        if tr_data:
            # Process execution feedback
            execution_data = json.loads(tr_data['tr_execution'])
            self.update_learning_from_execution(execution_data)
```

## Core Detector Architecture

### **1. Alpha Detector Module (Enhanced)**

The Alpha Detector is now a **complete intelligence module** that generates trading plans, not just signals.

#### **Module Intelligence Components**
```python
class AlphaDetectorModule:
    def __init__(self, module_id, parent_modules=None):
        self.module_id = module_id
        self.module_type = 'alpha_detector'
        self.parent_modules = parent_modules or []
        
        # Module Intelligence
        self.learning_rate = 0.01
        self.adaptation_threshold = 0.7
        self.performance_history = []
        self.learning_patterns = {}
        self.innovation_score = 0.0
        self.specialization_index = 0.0
        
        # Communication Capabilities
        self.communication_latency = 0
        self.message_throughput = 0
        self.intelligence_sharing_rate = 0.0
        self.collaboration_score = 0.0
        self.peer_ratings = {}
        self.network_centrality = 0.0
        
        # Replication Capabilities
        self.replication_readiness = 0.0
        self.mutation_rate = 0.1
        self.recombination_rate = 0.1
        self.offspring_count = 0
        
        # Core Detector Components (Enhanced)
        self.residual_factories = self.initialize_residual_factories()
        self.kernel_resonance = self.initialize_kernel_resonance()
        self.dsi_integration = self.initialize_dsi_integration()
        self.trading_plan_generator = self.initialize_trading_plan_generator()
        self.curator_layer = self.initialize_curator_layer()
        
        # Lesson Feedback Integration
        self.lesson_feedback = LessonFeedbackSystem('alpha_detector')
        self.lesson_enhanced_curator = LessonEnhancedCuratorOrchestrator('alpha_detector')
        self.real_time_lesson_app = RealTimeLessonApplication('alpha_detector')
    
    def process_signal_with_lessons(self, market_data: Dict) -> Optional[TradingPlan]:
        """Process market data with lesson-enhanced learning"""
        
        # 1. Compute base detector signal
        detector_sigma = self._compute_detector_sigma(market_data)
        
        # 2. Prepare context for curators
        context = self._prepare_curator_context(market_data, detector_sigma)
        
        # 3. Apply lesson-enhanced curator layer
        curated_sigma, approved, contributions = self.lesson_enhanced_curator.curate_signal_with_lessons(
            detector_sigma, context
        )
        
        # 4. Generate trading plan if approved
        if approved and curated_sigma >= self.publish_threshold:
            trading_plan = self._generate_trading_plan(market_data, curated_sigma, context)
            
            # 5. Add lesson metadata to trading plan
            trading_plan['lesson_enhanced'] = True
            trading_plan['lessons_applied'] = context.get('lessons_applied', [])
            trading_plan['confidence_boost'] = context.get('confidence_boost', 1.0)
            
            return trading_plan
            
        return None
    
    def _prepare_curator_context(self, market_data: Dict, detector_sigma: float) -> Dict:
        """Prepare context data for curators with lesson enhancement"""
        return {
            'detector_sigma': detector_sigma,
            'mx_evidence': market_data.get('mx_evidence', 0.0),
            'mx_confirm': market_data.get('mx_confirm', 0.0),
            'patterns': market_data.get('patterns', {}),
            'regime': market_data.get('regime', 'unknown'),
            'volatility': market_data.get('volatility', 0.0),
            'expert_performance': market_data.get('expert_performance', {}),
            'symbol': market_data.get('symbol', 'UNKNOWN'),
            'timeframe': market_data.get('timeframe', '1h'),
            'module_id': self.module_id,
            'parent_modules': self.parent_modules
        }
```

#### **Enhanced Residual Manufacturing**
```python
class EnhancedResidualFactory:
    def __init__(self, factory_type, module_intelligence):
        self.factory_type = factory_type
        self.module_intelligence = module_intelligence
        self.learning_rate = module_intelligence.get('learning_rate', 0.01)
        self.adaptation_threshold = module_intelligence.get('adaptation_threshold', 0.7)
        
    def generate_residuals(self, market_data, dsi_evidence=None):
        """Generate residuals with DSI integration and module learning"""
        # Core residual generation (preserved from v1)
        residuals = self._generate_core_residuals(market_data)
        
        # DSI integration
        if dsi_evidence:
            residuals = self._apply_dsi_boost(residuals, dsi_evidence)
        
        # Module learning adaptation
        residuals = self._apply_module_learning(residuals)
        
        # Innovation and specialization
        residuals = self._apply_innovation(residuals)
        
        return residuals
    
    def _apply_dsi_boost(self, residuals, dsi_evidence):
        """Apply DSI evidence boost to residuals"""
        boost_factor = 1 + (dsi_evidence.get('mx_evidence', 0) * 0.5)
        return {k: v * boost_factor for k, v in residuals.items()}
    
    def _apply_module_learning(self, residuals):
        """Apply module learning to residuals"""
        # Adapt parameters based on performance history
        learning_adjustment = self._calculate_learning_adjustment()
        return {k: v * learning_adjustment for k, v in residuals.items()}
    
    def _apply_innovation(self, residuals):
        """Apply innovation and specialization to residuals"""
        innovation_factor = self.module_intelligence.get('innovation_score', 0.0)
        specialization_factor = self.module_intelligence.get('specialization_index', 0.0)
        
        innovation_boost = 1 + (innovation_factor * 0.1)
        specialization_boost = 1 + (specialization_factor * 0.05)
        
        return {k: v * innovation_boost * specialization_boost for k, v in residuals.items()}
```

#### **Enhanced Kernel Resonance**
```python
class EnhancedKernelResonance:
    def __init__(self, module_intelligence):
        self.module_intelligence = module_intelligence
        self.dsi_integration = True
        self.module_learning = True
        
    def calculate_enhanced_sigma(self, sq_score, kr_delta_phi, dsi_evidence=None):
        """Calculate enhanced selection score with DSI and module intelligence"""
        # Base kernel resonance (preserved from v1)
        base_sigma = sq_score**0.6 * kr_delta_phi**0.4
        
        # DSI evidence boost
        dsi_boost = 1.0
        if dsi_evidence:
            dsi_boost = 1 + (dsi_evidence.get('mx_evidence', 0) * 0.3)
        
        # Module intelligence boost
        module_boost = self._calculate_module_boost()
        
        # Learning adjustment
        learning_adjustment = self._calculate_learning_adjustment()
        
        # Enhanced sigma calculation
        enhanced_sigma = base_sigma * dsi_boost * module_boost * learning_adjustment
        
        return enhanced_sigma
    
    def _calculate_module_boost(self):
        """Calculate module intelligence boost factor"""
        learning_rate = self.module_intelligence.get('learning_rate', 0.01)
        collaboration_score = self.module_intelligence.get('collaboration_score', 0.0)
        innovation_score = self.module_intelligence.get('innovation_score', 0.0)
        
        return 1 + (learning_rate * 0.5) + (collaboration_score * 0.3) + (innovation_score * 0.2)
    
    def _calculate_learning_adjustment(self):
        """Calculate learning-based parameter adjustment"""
        performance_history = self.module_intelligence.get('performance_history', [])
        if len(performance_history) < 10:
            return 1.0
        
        recent_performance = performance_history[-10:]
        performance_trend = self._calculate_trend(recent_performance)
        
        # Adjust based on performance trend
        if performance_trend > 0.1:
            return 1.05  # Boost for improving performance
        elif performance_trend < -0.1:
            return 0.95  # Reduce for declining performance
        else:
            return 1.0   # No adjustment for stable performance
```

#### **Trading Plan Generator**
```python
class TradingPlanGenerator:
    def __init__(self, module_intelligence):
        self.module_intelligence = module_intelligence
        self.plan_templates = self._load_plan_templates()
        self.risk_models = self._initialize_risk_models()
        
    def generate_trading_plan(self, signal_data, dsi_evidence, regime_context):
        """Generate complete trading plan from signal data"""
        # Extract signal information
        signal_strength = signal_data.get('signal_strength', 0.0)
        direction = signal_data.get('direction', 'neutral')
        symbol = signal_data.get('symbol', '')
        
        # Generate base trading plan
        trading_plan = {
            'plan_id': str(uuid.uuid4()),
            'module_id': self.module_intelligence.get('module_id'),
            'symbol': symbol,
            'timestamp': datetime.now(),
            
            # Core Trading Plan
            'signal_strength': signal_strength,
            'direction': direction,
            'entry_conditions': self._generate_entry_conditions(signal_data),
            'entry_price': self._calculate_entry_price(signal_data),
            'position_size': self._calculate_position_size(signal_strength, regime_context),
            'stop_loss': self._calculate_stop_loss(signal_data, regime_context),
            'take_profit': self._calculate_take_profit(signal_data, regime_context),
            'time_horizon': self._determine_time_horizon(signal_data, regime_context),
            'risk_reward_ratio': self._calculate_risk_reward_ratio(signal_data),
            'confidence_score': self._calculate_confidence_score(signal_data, dsi_evidence),
            
            # Intelligence Validation
            'microstructure_evidence': dsi_evidence,
            'regime_context': regime_context,
            'module_intelligence': self.module_intelligence,
            'execution_notes': self._generate_execution_notes(signal_data),
            'valid_until': self._calculate_valid_until(signal_data),
            'validation_status': 'pending',
            
            # Risk Management
            'risk_assessment': self._assess_risk(signal_data, regime_context),
            'portfolio_impact': self._assess_portfolio_impact(signal_data)
        }
        
        return trading_plan
    
    def _calculate_confidence_score(self, signal_data, dsi_evidence):
        """Calculate overall confidence score with DSI validation"""
        base_confidence = signal_data.get('signal_strength', 0.0)
        
        # DSI evidence boost
        dsi_boost = 1.0
        if dsi_evidence:
            dsi_boost = 1 + (dsi_evidence.get('mx_evidence', 0) * 0.3)
        
        # Module intelligence boost
        module_boost = self._calculate_module_confidence_boost()
        
        # Regime context adjustment
        regime_adjustment = self._calculate_regime_adjustment(signal_data.get('regime_context', {}))
        
        confidence = base_confidence * dsi_boost * module_boost * regime_adjustment
        return min(confidence, 1.0)  # Cap at 1.0
```

### **2. Decision Maker Module (New)**

The Decision Maker module evaluates and approves trading plans from Alpha Detectors.

#### **Module Intelligence Components**
```python
class DecisionMakerModule:
    def __init__(self, module_id, parent_modules=None):
        self.module_id = module_id
        self.module_type = 'decision_maker'
        self.parent_modules = parent_modules or []
        
        # Module Intelligence (same structure as Alpha Detector)
        self.learning_rate = 0.01
        self.adaptation_threshold = 0.7
        self.performance_history = []
        self.learning_patterns = {}
        self.innovation_score = 0.0
        self.specialization_index = 0.0
        
        # Decision Intelligence
        self.risk_models = self._initialize_risk_models()
        self.portfolio_optimizer = self._initialize_portfolio_optimizer()
        self.approval_criteria = self._initialize_approval_criteria()
        self.curator_layer = self._initialize_curator_layer()
    
    def evaluate_trading_plan(self, trading_plan, portfolio_context):
        """Evaluate trading plan and make approval decision"""
        # Risk assessment
        risk_assessment = self._assess_plan_risk(trading_plan, portfolio_context)
        
        # Portfolio impact analysis
        portfolio_impact = self._analyze_portfolio_impact(trading_plan, portfolio_context)
        
        # Approval decision
        approval_decision = self._make_approval_decision(
            trading_plan, risk_assessment, portfolio_impact
        )
        
        # Generate approved/modified plan
        if approval_decision['status'] == 'approved':
            approved_plan = self._create_approved_plan(trading_plan, approval_decision)
        elif approval_decision['status'] == 'modified':
            approved_plan = self._create_modified_plan(trading_plan, approval_decision)
        else:
            approved_plan = None
        
        return {
            'approval_decision': approval_decision,
            'approved_plan': approved_plan,
            'risk_assessment': risk_assessment,
            'portfolio_impact': portfolio_impact
        }
```

### **3. Trader Module (New)**

The Trader module executes trading plans and provides performance feedback.

#### **Module Intelligence Components**
```python
class TraderModule:
    def __init__(self, module_id, parent_modules=None):
        self.module_id = module_id
        self.module_type = 'trader'
        self.parent_modules = parent_modules or []
        
        # Module Intelligence (same structure as other modules)
        self.learning_rate = 0.01
        self.adaptation_threshold = 0.7
        self.performance_history = []
        self.learning_patterns = {}
        self.innovation_score = 0.0
        self.specialization_index = 0.0
        
        # Execution Intelligence
        self.execution_engines = self._initialize_execution_engines()
        self.venue_selector = self._initialize_venue_selector()
        self.performance_tracker = self._initialize_performance_tracker()
        self.curator_layer = self._initialize_curator_layer()
    
    def execute_trading_plan(self, approved_plan, market_conditions):
        """Execute approved trading plan"""
        # Select execution venue
        execution_venue = self._select_execution_venue(approved_plan, market_conditions)
        
        # Execute order
        execution_result = self._execute_order(approved_plan, execution_venue)
        
        # Track performance
        performance_metrics = self._track_execution_performance(
            approved_plan, execution_result, market_conditions
        )
        
        # Generate feedback
        feedback = self._generate_execution_feedback(
            approved_plan, execution_result, performance_metrics
        )
        
        return {
            'execution_result': execution_result,
            'performance_metrics': performance_metrics,
            'feedback': feedback
        }
```

## Module Communication Integration

### **1. Inter-Module Communication**
```python
class ModuleCommunication:
    def __init__(self, module_id):
        self.module_id = module_id
        self.message_queue = self._initialize_message_queue()
        self.communication_protocol = self._initialize_communication_protocol()
    
    def send_trading_plan(self, trading_plan, target_module_id):
        """Send trading plan to target module"""
        message = {
            'message_type': 'trading_plan',
            'sender_module_id': self.module_id,
            'receiver_module_id': target_module_id,
            'message_data': trading_plan,
            'priority': 1,
            'ttl_seconds': 300
        }
        
        return self._send_message(message)
    
    def send_execution_feedback(self, feedback, target_module_id):
        """Send execution feedback to target module"""
        message = {
            'message_type': 'execution_feedback',
            'sender_module_id': self.module_id,
            'receiver_module_id': target_module_id,
            'message_data': feedback,
            'priority': 2,
            'ttl_seconds': 3600
        }
        
        return self._send_message(message)
    
    def broadcast_intelligence(self, intelligence_data):
        """Broadcast intelligence to all modules"""
        message = {
            'message_type': 'intelligence_broadcast',
            'sender_module_id': self.module_id,
            'receiver_module_id': None,  # Broadcast
            'message_data': intelligence_data,
            'priority': 3,
            'ttl_seconds': 1800
        }
        
        return self._send_message(message)
```

### **2. Module Learning Integration**
```python
class ModuleLearning:
    def __init__(self, module_id):
        self.module_id = module_id
        self.learning_rate = 0.01
        self.adaptation_threshold = 0.7
        self.performance_history = []
        self.learning_patterns = {}
    
    def update_performance(self, performance_metrics):
        """Update module performance and trigger learning"""
        self.performance_history.append(performance_metrics)
        
        # Check if adaptation is needed
        if self._should_adapt():
            self._trigger_adaptation()
        
        # Update learning patterns
        self._update_learning_patterns(performance_metrics)
    
    def _should_adapt(self):
        """Check if module should adapt based on performance"""
        if len(self.performance_history) < 10:
            return False
        
        recent_performance = self.performance_history[-10:]
        performance_trend = self._calculate_trend(recent_performance)
        
        return abs(performance_trend) > self.adaptation_threshold
    
    def _trigger_adaptation(self):
        """Trigger module adaptation"""
        # Analyze performance patterns
        performance_analysis = self._analyze_performance_patterns()
        
        # Update module parameters
        self._update_module_parameters(performance_analysis)
        
        # Broadcast learning update
        self._broadcast_learning_update(performance_analysis)
```

## Module Replication Integration

### **1. Replication Trigger Detection**
```python
class ModuleReplication:
    def __init__(self, module_id):
        self.module_id = module_id
        self.replication_readiness = 0.0
        self.offspring_count = 0
        self.parent_performance = {}
    
    def check_replication_triggers(self, performance_metrics):
        """Check if module should replicate"""
        # Performance threshold trigger
        if self._check_performance_threshold(performance_metrics):
            return self._create_replication_signal('performance_threshold', performance_metrics)
        
        # Diversity gap trigger
        diversity_gaps = self._check_diversity_gaps()
        if diversity_gaps:
            return self._create_replication_signal('diversity_gap', diversity_gaps)
        
        # Regime change trigger
        regime_change = self._check_regime_change()
        if regime_change:
            return self._create_replication_signal('regime_change', regime_change)
        
        return None
    
    def _check_performance_threshold(self, performance_metrics):
        """Check if performance exceeds replication threshold"""
        performance_score = performance_metrics.get('performance_score', 0.0)
        consistency_score = performance_metrics.get('consistency_score', 0.0)
        
        return (performance_score >= 0.8 and 
                consistency_score >= 0.7 and 
                self.offspring_count < 5)  # Limit offspring count
```

### **2. Intelligence Inheritance**
```python
class IntelligenceInheritance:
    def __init__(self, parent_modules):
        self.parent_modules = parent_modules
        self.inheritance_rate = 0.8
        self.mutation_rate = 0.1
        self.recombination_rate = 0.1
    
    def create_child_intelligence(self, replication_trigger):
        """Create child module intelligence from parent modules"""
        # Inherit from primary parent
        primary_parent = self.parent_modules[0]
        child_intelligence = primary_parent.intelligence.copy()
        
        # Apply inheritance rate
        child_intelligence = self._apply_inheritance_rate(child_intelligence)
        
        # Add recombination from other parents
        if len(self.parent_modules) > 1:
            child_intelligence = self._add_recombination(child_intelligence)
        
        # Apply mutations
        child_intelligence = self._apply_mutations(child_intelligence)
        
        # Adapt to replication trigger
        child_intelligence = self._adapt_to_trigger(child_intelligence, replication_trigger)
        
        return child_intelligence
```

## Enhanced Curator Layer

### **1. Module-Level Curators**
```python
class ModuleCuratorLayer:
    def __init__(self, module_type, module_intelligence):
        self.module_type = module_type
        self.module_intelligence = module_intelligence
        self.curators = self._initialize_curators()
    
    def _initialize_curators(self):
        """Initialize module-specific curators"""
        if self.module_type == 'alpha_detector':
            return {
                'dsi_curator': DSICurator(),
                'pattern_curator': PatternCurator(),
                'divergence_curator': DivergenceCurator(),
                'regime_curator': RegimeCurator(),
                'evolution_curator': EvolutionCurator(),
                'performance_curator': PerformanceCurator()
            }
        elif self.module_type == 'decision_maker':
            return {
                'risk_curator': RiskCurator(),
                'allocation_curator': AllocationCurator(),
                'timing_curator': TimingCurator(),
                'cost_curator': CostCurator(),
                'compliance_curator': ComplianceCurator()
            }
        elif self.module_type == 'trader':
            return {
                'execution_curator': ExecutionCurator(),
                'latency_curator': LatencyCurator(),
                'slippage_curator': SlippageCurator(),
                'position_curator': PositionCurator(),
                'performance_curator': PerformanceCurator()
            }
    
    def validate_decision(self, decision_data, context):
        """Validate module decision through curator layer"""
        validation_results = {}
        
        for curator_name, curator in self.curators.items():
            validation_results[curator_name] = curator.validate(decision_data, context)
        
        # Aggregate validation results
        overall_validation = self._aggregate_validation_results(validation_results)
        
        return overall_validation
```

---

*This enhanced detector specification defines module-level intelligence for the Trading Intelligence System, enabling complete trading plan generation, inter-module communication, learning, and replication.*
