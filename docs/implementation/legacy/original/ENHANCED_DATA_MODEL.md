# Enhanced Data Model - Trading Intelligence System

*Source: [build_docs_v1/DATA_MODEL.md](../build_docs_v1/DATA_MODEL.md) + Trading Intelligence System Architecture*

## Overview

The Enhanced Data Model supports the **Trading Intelligence System** with **module-level intelligence**, **complete trading plans**, **DSI integration**, and **organic replication**. This model enables each module to be a **self-contained intelligence unit** that can communicate, learn, and replicate.

## Core Data Architecture

### **1. Module Intelligence Tables**

#### **modules**
```sql
CREATE TABLE modules (
    module_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    module_type VARCHAR(50) NOT NULL, -- 'alpha_detector', 'decision_maker', 'trader'
    module_version VARCHAR(20) NOT NULL,
    parent_modules JSONB, -- Array of parent module IDs
    offspring_modules JSONB, -- Array of offspring module IDs
    generational_depth INTEGER DEFAULT 0,
    
    -- Module Intelligence
    learning_rate DECIMAL(3,2) DEFAULT 0.01, -- 0-1
    adaptation_threshold DECIMAL(3,2) DEFAULT 0.7, -- 0-1
    performance_history JSONB, -- Historical performance data
    learning_patterns JSONB, -- Learned patterns and behaviors
    innovation_score DECIMAL(3,2) DEFAULT 0.0, -- 0-1
    specialization_index DECIMAL(3,2) DEFAULT 0.0, -- 0-1
    
    -- Module Communication
    communication_latency_ms INTEGER DEFAULT 0,
    message_throughput_per_sec INTEGER DEFAULT 0,
    intelligence_sharing_rate DECIMAL(3,2) DEFAULT 0.0, -- 0-1
    collaboration_score DECIMAL(3,2) DEFAULT 0.0, -- 0-1
    peer_ratings JSONB, -- Ratings from other modules
    network_centrality DECIMAL(3,2) DEFAULT 0.0, -- 0-1
    
    -- Module Replication
    replication_readiness DECIMAL(3,2) DEFAULT 0.0, -- 0-1
    parent_performance JSONB, -- Performance of parent modules
    mutation_rate DECIMAL(3,2) DEFAULT 0.1, -- 0-1
    recombination_rate DECIMAL(3,2) DEFAULT 0.1, -- 0-1
    offspring_count INTEGER DEFAULT 0,
    
    -- Module Lifecycle
    lifecycle_stage VARCHAR(20) DEFAULT 'experimental', -- 'experimental', 'active', 'deprecated', 'archived'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'active' -- 'active', 'inactive', 'failed'
);
```

#### **module_performance**
```sql
CREATE TABLE module_performance (
    performance_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    module_id UUID REFERENCES modules(module_id),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Performance Metrics
    performance_score DECIMAL(3,2) NOT NULL, -- 0-1
    consistency_score DECIMAL(3,2) NOT NULL, -- 0-1
    innovation_score DECIMAL(3,2) NOT NULL, -- 0-1
    specialization_score DECIMAL(3,2) NOT NULL, -- 0-1
    collaboration_score DECIMAL(3,2) NOT NULL, -- 0-1
    
    -- Trading Performance
    trading_plan_success_rate DECIMAL(3,2), -- 0-1
    execution_quality DECIMAL(3,2), -- 0-1
    risk_adjusted_returns DECIMAL(8,4),
    sharpe_ratio DECIMAL(8,4),
    max_drawdown DECIMAL(8,4),
    
    -- Module Intelligence
    learning_effectiveness DECIMAL(3,2), -- 0-1
    adaptation_speed DECIMAL(3,2), -- 0-1
    intelligence_sharing_effectiveness DECIMAL(3,2), -- 0-1
    
    -- Context
    market_regime VARCHAR(20),
    asset_class VARCHAR(20),
    time_horizon VARCHAR(10)
);
```

### **2. Trading Plan Tables**

#### **trading_plans**
```sql
CREATE TABLE trading_plans (
    plan_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    module_id UUID REFERENCES modules(module_id),
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Core Trading Plan
    signal_strength DECIMAL(3,2) NOT NULL, -- 0-1
    direction VARCHAR(10) NOT NULL, -- 'long', 'short', 'neutral'
    entry_conditions JSONB, -- Trigger conditions
    entry_price DECIMAL(20,8),
    position_size DECIMAL(5,2), -- % of portfolio
    stop_loss DECIMAL(20,8),
    take_profit DECIMAL(20,8),
    time_horizon VARCHAR(10), -- '1m', '5m', '15m', '1h', '4h', '1d'
    risk_reward_ratio DECIMAL(5,2),
    confidence_score DECIMAL(3,2) NOT NULL, -- 0-1
    
    -- Intelligence Validation
    microstructure_evidence JSONB, -- DSI evidence
    regime_context JSONB, -- Market regime context
    module_intelligence JSONB, -- Module-specific intelligence
    execution_notes TEXT,
    valid_until TIMESTAMP WITH TIME ZONE,
    validation_status VARCHAR(20) DEFAULT 'pending', -- 'validated', 'pending', 'failed'
    
    -- Risk Management
    risk_assessment JSONB, -- Risk analysis results
    portfolio_impact JSONB, -- Portfolio impact analysis
    
    -- Performance Tracking
    execution_status VARCHAR(20), -- 'executed', 'partial', 'failed', 'cancelled'
    executed_price DECIMAL(20,8),
    executed_quantity DECIMAL(20,8),
    execution_cost DECIMAL(20,8),
    slippage DECIMAL(8,4),
    pnl DECIMAL(20,8),
    performance_metrics JSONB, -- Detailed performance analysis
    attribution_analysis JSONB -- Performance attribution analysis
);
```

#### **trading_plan_approvals**
```sql
CREATE TABLE trading_plan_approvals (
    approval_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID REFERENCES trading_plans(plan_id),
    decision_maker_module_id UUID REFERENCES modules(module_id),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Approval Decision
    approval_status VARCHAR(20) NOT NULL, -- 'approved', 'rejected', 'modified'
    approval_reason TEXT,
    modifications JSONB, -- Any modifications made
    
    -- Risk Assessment
    risk_assessment JSONB, -- Risk analysis results
    risk_controls JSONB, -- Applied risk controls
    portfolio_impact JSONB, -- Portfolio impact analysis
    
    -- Decision Intelligence
    decision_confidence DECIMAL(3,2), -- 0-1
    decision_factors JSONB, -- Factors that influenced decision
    alternative_plans JSONB -- Alternative plans considered
);
```

### **3. DSI Integration Tables**

#### **dsi_evidence**
```sql
CREATE TABLE dsi_evidence (
    evidence_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID REFERENCES trading_plans(plan_id),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- MicroTape Evidence
    mx_evidence DECIMAL(3,2) NOT NULL, -- 0-1
    mx_confirm BOOLEAN NOT NULL,
    mx_expert_contributions JSONB, -- Individual expert outputs
    mx_microtape_hash VARCHAR(64), -- Hash of input MicroTape
    mx_processing_latency_ms INTEGER,
    mx_confidence_interval JSONB, -- Confidence interval for evidence score
    
    -- Micro-Expert Ecosystem
    mx_fsm_experts JSONB, -- Grammar/FSM expert outputs
    mx_classifier_experts JSONB, -- Tiny sequence classifier outputs
    mx_anomaly_experts JSONB, -- Anomaly scorer outputs
    mx_divergence_experts JSONB, -- Divergence verifier outputs
    mx_expert_weights JSONB, -- Learned weights for expert contributions
    mx_expert_survival_rates JSONB, -- Expert survival rates over time
    
    -- DSI Integration
    mx_evidence_boost DECIMAL(5,4), -- Evidence boost factor
    mx_confirm_rate DECIMAL(3,2), -- Confirmation rate across micro-experts
    mx_expert_survival_rate DECIMAL(3,2), -- Expert contribution survival rate
    mx_latency_p50 INTEGER, -- 50th percentile processing latency
    mx_latency_p95 INTEGER, -- 95th percentile processing latency
    mx_throughput_per_second INTEGER -- Expert processing throughput
);
```

### **4. Module Communication Tables**

#### **module_messages**
```sql
CREATE TABLE module_messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sender_module_id UUID REFERENCES modules(module_id),
    receiver_module_id UUID REFERENCES modules(module_id),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Message Content
    message_type VARCHAR(50) NOT NULL, -- 'trading_plan', 'execution_feedback', 'intelligence_broadcast', 'replication_signal'
    message_data JSONB NOT NULL, -- Message payload
    priority INTEGER DEFAULT 2, -- 1=high, 2=medium, 3=low
    ttl_seconds INTEGER DEFAULT 3600, -- Time to live
    
    -- Message Status
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'delivered', 'failed', 'expired'
    delivery_attempts INTEGER DEFAULT 0,
    last_delivery_attempt TIMESTAMP WITH TIME ZONE,
    error_message TEXT
);
```

#### **module_intelligence_sharing**
```sql
CREATE TABLE module_intelligence_sharing (
    sharing_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sender_module_id UUID REFERENCES modules(module_id),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Intelligence Data
    intelligence_type VARCHAR(50) NOT NULL, -- 'performance_update', 'learning_update', 'capability_update'
    intelligence_data JSONB NOT NULL, -- Module-specific intelligence
    
    -- Performance Metrics
    performance_score DECIMAL(3,2), -- Module performance score
    confidence_level DECIMAL(3,2), -- Confidence in intelligence
    last_updated TIMESTAMP WITH TIME ZONE,
    
    -- Sharing Context
    target_modules JSONB, -- Target module IDs (null = broadcast)
    sharing_scope VARCHAR(20) DEFAULT 'broadcast', -- 'broadcast', 'targeted', 'private'
    sharing_priority INTEGER DEFAULT 3 -- 1=high, 2=medium, 3=low
);
```

### **5. Module Replication Tables**

#### **module_replications**
```sql
CREATE TABLE module_replications (
    replication_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_module_id UUID REFERENCES modules(module_id),
    child_module_id UUID REFERENCES modules(module_id),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Replication Trigger
    trigger_type VARCHAR(50) NOT NULL, -- 'performance_threshold', 'diversity_gap', 'regime_change', 'failure_recovery'
    trigger_data JSONB, -- Trigger-specific data
    replication_reason TEXT,
    
    -- Replication Parameters
    target_capabilities JSONB, -- Required capabilities
    performance_threshold DECIMAL(3,2), -- Minimum performance threshold
    diversity_requirements JSONB, -- Diversity requirements
    
    -- Replication Process
    replication_status VARCHAR(20) DEFAULT 'initiated', -- 'initiated', 'in_progress', 'completed', 'failed'
    creation_time_ms INTEGER, -- Time to create module
    validation_time_ms INTEGER, -- Time to validate module
    initialization_time_ms INTEGER, -- Time to initialize module
    
    -- Intelligence Inheritance
    inherited_intelligence JSONB, -- Intelligence inherited from parents
    mutation_applied JSONB, -- Mutations applied during replication
    recombination_applied JSONB -- Recombination applied during replication
);
```

#### **module_replication_triggers**
```sql
CREATE TABLE module_replication_triggers (
    trigger_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    module_id UUID REFERENCES modules(module_id),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Trigger Details
    trigger_type VARCHAR(50) NOT NULL, -- 'performance_threshold', 'diversity_gap', 'regime_change', 'failure_recovery'
    trigger_data JSONB NOT NULL, -- Trigger-specific data
    trigger_priority INTEGER DEFAULT 2, -- 1=high, 2=medium, 3=low
    
    -- Trigger Status
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'processed', 'expired', 'cancelled'
    processed_at TIMESTAMP WITH TIME ZONE,
    replication_id UUID REFERENCES module_replications(replication_id)
);
```

### **6. Enhanced Feature Tables (Preserved + Enhanced)**

#### **market_data_1m** (Enhanced with DSI)
```sql
CREATE TABLE market_data_1m (
    -- Core OHLCV data (preserved)
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    open DECIMAL(20,8) NOT NULL,
    high DECIMAL(20,8) NOT NULL,
    low DECIMAL(20,8) NOT NULL,
    close DECIMAL(20,8) NOT NULL,
    volume DECIMAL(20,8) NOT NULL,
    
    -- DSI Integration (new)
    mx_evidence DECIMAL(3,2), -- DSI evidence score
    mx_confirm BOOLEAN, -- DSI confirmation flag
    mx_expert_contributions JSONB, -- DSI expert outputs
    
    -- Module Intelligence (new)
    module_intelligence JSONB, -- Module-specific intelligence
    module_learning_updates JSONB, -- Learning updates from modules
    
    -- Enhanced Features (preserved + enhanced)
    -- ... (all existing features from v1)
    
    PRIMARY KEY (symbol, timestamp)
);
```

#### **anomaly_events** (Enhanced with Trading Plans)
```sql
CREATE TABLE anomaly_events (
    -- Core event data (preserved)
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    anomaly_type VARCHAR(50) NOT NULL,
    anomaly_score DECIMAL(5,4) NOT NULL,
    
    -- Trading Plan Integration (new)
    trading_plan_id UUID REFERENCES trading_plans(plan_id),
    plan_generation_module_id UUID REFERENCES modules(module_id),
    
    -- Enhanced Signal Pack (preserved + enhanced)
    signal_pack JSONB NOT NULL, -- Enhanced signal pack with trading plans
    
    -- DSI Integration (new)
    dsi_evidence_id UUID REFERENCES dsi_evidence(evidence_id),
    microstructure_validation JSONB, -- DSI validation results
    
    -- Module Intelligence (new)
    module_intelligence JSONB, -- Module intelligence used
    intelligence_confidence DECIMAL(3,2), -- Confidence in intelligence
    
    -- Performance Tracking (new)
    plan_execution_status VARCHAR(20), -- Trading plan execution status
    plan_performance_metrics JSONB, -- Trading plan performance
    attribution_analysis JSONB -- Performance attribution
);
```

## Data Relationships

### **Module Intelligence Relationships**
```
modules (1) ←→ (N) module_performance
modules (1) ←→ (N) trading_plans
modules (1) ←→ (N) module_messages (sender)
modules (1) ←→ (N) module_messages (receiver)
modules (1) ←→ (N) module_intelligence_sharing
modules (1) ←→ (N) module_replications (parent)
modules (1) ←→ (N) module_replications (child)
```

### **Trading Plan Relationships**
```
trading_plans (1) ←→ (1) dsi_evidence
trading_plans (1) ←→ (N) trading_plan_approvals
trading_plans (1) ←→ (N) anomaly_events
```

### **DSI Integration Relationships**
```
dsi_evidence (1) ←→ (N) anomaly_events
market_data_1m (1) ←→ (N) dsi_evidence (via timestamp)
```

## Data Indexing Strategy

### **Performance Indexes**
```sql
-- Module performance indexes
CREATE INDEX idx_module_performance_module_id_timestamp ON module_performance(module_id, timestamp DESC);
CREATE INDEX idx_module_performance_score ON module_performance(performance_score DESC);

-- Trading plan indexes
CREATE INDEX idx_trading_plans_module_id_timestamp ON trading_plans(module_id, timestamp DESC);
CREATE INDEX idx_trading_plans_symbol_timestamp ON trading_plans(symbol, timestamp DESC);
CREATE INDEX idx_trading_plans_confidence_score ON trading_plans(confidence_score DESC);

-- DSI evidence indexes
CREATE INDEX idx_dsi_evidence_plan_id ON dsi_evidence(plan_id);
CREATE INDEX idx_dsi_evidence_timestamp ON dsi_evidence(timestamp DESC);
CREATE INDEX idx_dsi_evidence_mx_evidence ON dsi_evidence(mx_evidence DESC);

-- Module communication indexes
CREATE INDEX idx_module_messages_sender_timestamp ON module_messages(sender_module_id, timestamp DESC);
CREATE INDEX idx_module_messages_receiver_timestamp ON module_messages(receiver_module_id, timestamp DESC);
CREATE INDEX idx_module_messages_type_status ON module_messages(message_type, status);

-- Module replication indexes
CREATE INDEX idx_module_replications_parent_timestamp ON module_replications(parent_module_id, timestamp DESC);
CREATE INDEX idx_module_replications_child_timestamp ON module_replications(child_module_id, timestamp DESC);
CREATE INDEX idx_module_replications_trigger_type ON module_replications(trigger_type);
```

## Data Retention Strategy

### **Module Data Retention**
- **Module Performance**: 1 year (for learning and replication)
- **Module Messages**: 30 days (for communication debugging)
- **Module Intelligence Sharing**: 6 months (for learning)
- **Module Replications**: Permanent (for lineage tracking)

### **Trading Plan Data Retention**
- **Trading Plans**: 2 years (for performance analysis)
- **Trading Plan Approvals**: 2 years (for decision analysis)
- **DSI Evidence**: 1 year (for validation analysis)

### **Market Data Retention** (Enhanced)
- **1-minute data**: 7 days (with DSI integration)
- **15-minute data**: 30 days (with DSI integration)
- **1-hour data**: 1 year (with DSI integration)

## Data Validation

### **Module Intelligence Validation**
- **Learning Rate**: 0 ≤ learning_rate ≤ 1
- **Adaptation Threshold**: 0 ≤ adaptation_threshold ≤ 1
- **Performance Score**: 0 ≤ performance_score ≤ 1
- **Innovation Score**: 0 ≤ innovation_score ≤ 1

### **Trading Plan Validation**
- **Signal Strength**: 0 ≤ signal_strength ≤ 1
- **Confidence Score**: 0 ≤ confidence_score ≤ 1
- **Position Size**: 0 < position_size ≤ 100
- **Risk/Reward Ratio**: 0 < risk_reward_ratio ≤ 10

### **DSI Evidence Validation**
- **Evidence Score**: 0 ≤ mx_evidence ≤ 1
- **Confirmation Rate**: 0 ≤ mx_confirm_rate ≤ 1
- **Processing Latency**: 0 < mx_processing_latency_ms < 10000
- **Throughput**: 0 < mx_throughput_per_second < 10000

---

*This enhanced data model supports the Trading Intelligence System with module-level intelligence, complete trading plans, DSI integration, and organic replication capabilities.*
