# Module Replication & Build Packs

*Source: [organic_intelligence_overview.md](../organic_intelligence_overview.md) + [intelligence_commincation_roughplan.md](../build_docs/intelligence_commincation_roughplan.md)*

## Goal
Enable easy replication of modules while maintaining uniqueness, creating a system where each module is its own "garden" that can be easily replicated but is unique to its creator.

**This folder provides practical implementation guides for creating new modules using the architectural templates from:**
- `@communication_protocol/` - Direct table communication
- `@learning_systems/` - Strand-braid learning system  
- `@core_intelligence_architecture/` - Curator layer design

## Core Philosophy

### Organic Intelligence System
- **Each module is its own "garden"** - self-contained intelligence
- **Modules know how to communicate** - but each is unique to its creator
- **All pipelines are modules** - but modules can be anything
- **Everything communicates back in** - creating continuous learning

### Build Pack Principles
- **Simple .md files** that let the IDE do the hard work
- **Everything needed to rebuild** a module in one folder
- **Module independence** while maintaining communication
- **Easy replication** while preserving uniqueness

## Using Design Document Templates

### **Step 1: Choose Your Module Type**
Before creating a new module, determine which design document templates to use:

#### **All Modules Need:**
- **`@communication_protocol/`** - Direct table communication with tags
- **`@learning_systems/`** - Strand-braid learning system
- **`@core_intelligence_architecture/`** - Curator layer design

#### **Module-Specific Templates:**
- **Alpha Detector**: Use `@Alpha_detector_module/` as reference implementation
- **Decision Maker**: Use `@decision_maker_module/` as reference implementation  
- **Trader**: Use `@trader_module/` as reference implementation
- **New Module Type**: Follow the general templates and customize

### **Step 2: Implement Design Document Templates**
Each new module must implement the three core templates:

```python
# 1. Communication Protocol Implementation
from communication_protocol import DirectTableCommunicator, ModuleListener

class MyModuleCommunicator:
    def __init__(self, module_name):
        self.communicator = DirectTableCommunicator(db_connection, module_name)
        self.listener = ModuleListener(module_name)
    
    def send_to_decision_maker(self, data, tags):
        # Only tag Decision Maker (pipeline modules)
        self.communicator.write_with_tags('DM_strands', data, tags)

# 2. Learning Systems Implementation  
from learning_systems import EnhancedModuleLearning, StrandBraidLearning

class MyModuleLearning:
    def __init__(self, module_type):
        self.learning_system = EnhancedModuleLearning(module_type)
        self.strand_braid = StrandBraidLearning(module_type)
    
    def update_performance(self, strand_data, outcome):
        # Update learning with strand-braid system
        self.learning_system.update_performance(strand_data, outcome)

# 3. Core Intelligence Architecture Implementation
from core_intelligence_architecture import CuratorOrchestrator, BaseCurator

class MyModuleCurator(BaseCurator):
    def __init__(self):
        super().__init__("my_curator", kappa=0.10)
    
    def evaluate(self, detector_sigma, context):
        # Implement curator logic
        pass

class MyModuleIntelligence:
    def __init__(self):
        self.curator_orchestrator = CuratorOrchestrator("my_module")
        self.curator_orchestrator.setup_curators()
```

### **Step 3: Follow Build Pack Structure**
Use the standard build pack layout below to organize your module.

## Build Pack Structure

### Standard Build Pack Layout
```
module_name/
├── README.md                    # Module overview and quick start
├── module.yaml                  # Module manifest and configuration
├── database/
│   ├── schema.sql              # Database schema
│   ├── migrations/             # Database migrations
│   └── seeds/                  # Sample data
├── src/
│   ├── main.py                 # Main module entry point
│   ├── curators/               # Curator implementations
│   ├── components/             # Core components
│   ├── models/                 # Data models
│   └── utils/                  # Utility functions
├── config/
│   ├── default.yaml           # Default configuration
│   ├── development.yaml       # Development configuration
│   └── production.yaml        # Production configuration
├── tests/
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   └── fixtures/              # Test fixtures
├── docs/
│   ├── architecture.md        # Architecture documentation
│   ├── api.md                 # API documentation
│   └── examples.md            # Usage examples
├── scripts/
│   ├── setup.sh              # Setup script
│   ├── deploy.sh             # Deployment script
│   └── test.sh               # Test script
└── requirements.txt           # Python dependencies
```

## Module Manifest (module.yaml)

### Standard Module Manifest
```yaml
module:
  name: "alpha_detector"
  version: "1.0.0"
  description: "Alpha signal detection and trading plan generation"
  author: "Your Name"
  created_at: "2024-01-01"
  updated_at: "2024-01-01"
  
  # Module capabilities
  capabilities:
    - "signal_detection"
    - "trading_plan_generation"
    - "pattern_recognition"
    - "microstructure_analysis"
  
  # Database schema
  database:
    schema: "alpha_detector"
    tables:
      - "detector_registry"
      - "feature_snapshots"
      - "anomaly_events"
      - "trading_plans"
      - "outbox"
      - "inbox"
    migrations:
      - "001_initial_schema.sql"
      - "002_add_dsi_tables.sql"
      - "003_add_curator_tables.sql"
  
  # Communication
  events:
    published:
      - "det-alpha-1.0"
      - "ms-1.0"
    consumed:
      - "exec-report-1.0"
  
  # Curators
  curators:
    - "dsi"
    - "pattern"
    - "divergence"
    - "regime"
    - "evolution"
    - "performance"
  
  # Dependencies
  dependencies:
    - "hyperliquid_client"
    - "supabase_client"
    - "dsi_system"
    - "numpy"
    - "pandas"
    - "scikit-learn"
  
  # Configuration
  configuration:
    required_env_vars:
      - "SUPABASE_URL"
      - "SUPABASE_KEY"
      - "HYPERLIQUID_API_KEY"
    optional_env_vars:
      - "DETECTOR_UNIVERSE_SIZE"
      - "DSI_ENABLED"
    default_config:
      detector_universe_size: 25
      dsi_enabled: true
      curator_weights:
        dsi: 0.3
        pattern: 0.2
        divergence: 0.2
        regime: 0.15
        evolution: 0.1
        performance: 0.05
  
  # Health checks
  health_checks:
    - "database_connectivity"
    - "event_bus_connectivity"
    - "external_api_connectivity"
    - "curator_health"
  
  # Monitoring
  monitoring:
    metrics:
      - "signal_generation_rate"
      - "trading_plan_quality"
      - "curator_performance"
      - "dsi_evidence_quality"
    alerts:
      - "high_signal_failure_rate"
      - "curator_veto_rate_exceeded"
      - "dsi_evidence_quality_degraded"
```

## Build Pack Templates

### 1. Alpha Detector Build Pack
```markdown
# Alpha Detector Build Pack

## Quick Start
1. Copy this folder to your desired location
2. Run `./scripts/setup.sh` to install dependencies
3. Configure environment variables in `.env`
4. Run `python src/main.py` to start the module

## What This Module Does
- Detects alpha signals from market data
- Generates complete trading plans
- Uses DSI for microstructure intelligence
- Applies curator layer for quality control
- Self-learns and improves over time

## Key Components
- **Signal Detection**: Evolutionary detector system
- **DSI Integration**: Microstructure intelligence
- **Curator Layer**: Quality control and governance
- **Trading Plan Generation**: Complete plan creation
- **Self-Learning**: Continuous improvement

## Design Document Implementation
This module implements the following design document templates:

### **Communication Protocol** (`@communication_protocol/`)
- **Direct Table Communication**: Uses `DirectTableCommunicator` and `ModuleListener`
- **Tagging Hierarchy**: Only tags Decision Maker (pipeline module)
- **Database Integration**: Stores data in `AD_strands` table with communication tags

### **Learning Systems** (`@learning_systems/`)
- **Strand-Braid Learning**: Hierarchical learning with clustering and LLM lessons
- **Module-Specific Scoring**: Alpha Detector scoring weights for signal strength and confidence
- **Curator Learning**: Curators learn from their own performance decisions

### **Core Intelligence Architecture** (`@core_intelligence_architecture/`)
- **Curator Layer**: DSI, Pattern, Regime, and other specialized curators
- **Bounded Influence**: Curator contributions capped at κ ≤ 0.15
- **Curator Learning**: Performance tracking and weight adaptation

## Communication
- **Publishes**: Trading plans to Decision Maker via `DM_strands` table
- **Consumes**: Feedback from Decision Maker via `AD_strands` table
- **Database**: `AD_strands` table with direct table communication
- **Tags**: `['dm:evaluate_plan']` for Decision Maker communication

## Configuration
See `config/default.yaml` for all configuration options.
Key settings:
- `detector_universe_size`: Number of detectors to maintain
- `dsi_enabled`: Enable Deep Signal Intelligence
- `curator_weights`: Curator influence weights
- `learning_enabled`: Enable strand-braid learning system

## Development
- Run tests: `./scripts/test.sh`
- Deploy: `./scripts/deploy.sh`
- Monitor: Check health endpoints
```

### 2. Decision Maker Build Pack
```markdown
# Decision Maker Build Pack

## Quick Start
1. Copy this folder to your desired location
2. Run `./scripts/setup.sh` to install dependencies
3. Configure environment variables in `.env`
4. Run `python src/main.py` to start the module

## What This Module Does
- Evaluates trading plans from Alpha Detector
- Provides yes/no approval or modifications
- Manages portfolio risk and allocation
- Applies crypto asymmetry scaling
- Self-learns from decision outcomes

## Key Components
- **Alpha Normalizer**: Signal standardization
- **Context Engine**: Portfolio state management
- **Fusion Engine**: Signal combination
- **Portfolio Allocator**: Risk-optimized allocation
- **Crypto Asymmetry**: Crypto-specific scaling

## Communication
- **Publishes**: `dm-decision-1.0`
- **Consumes**: `det-alpha-1.0`, `exec-report-1.0`
- **Database**: `decision_maker` schema
- **Events**: Outbox → Herald → Inbox pattern

## Configuration
See `config/default.yaml` for all configuration options.
Key settings:
- `max_position_size`: Maximum position size
- `crypto_asymmetry_enabled`: Enable crypto scaling
- `curator_weights`: Curator influence weights
```

### 3. Trader Build Pack
```markdown
# Trader Build Pack

## Quick Start
1. Copy this folder to your desired location
2. Run `./scripts/setup.sh` to install dependencies
3. Configure environment variables in `.env`
4. Run `python src/main.py` to start the module

## What This Module Does
- Executes approved trading plans
- Manages positions and P&L tracking
- Optimizes execution strategies
- Provides performance feedback
- Self-learns from execution outcomes

## Key Components
- **Trigger Evaluator**: Condition monitoring
- **Order Management**: Execution coordination
- **Position Tracking**: P&L management
- **Outcome Publisher**: Feedback generation
- **Executor Scoring**: Performance measurement

## Communication
- **Publishes**: `exec-report-1.0`, `trader-performance-1.0`
- **Consumes**: `dm-decision-1.0`
- **Database**: `trader` schema
- **Events**: Outbox → Herald → Inbox pattern

## Configuration
See `config/default.yaml` for all configuration options.
Key settings:
- `default_strategy`: Default execution strategy
- `max_slippage`: Maximum acceptable slippage
- `venue_weights`: Venue selection weights
```

## Replication Process

### 1. Module Creation
```bash
# Create new module from template
./scripts/create_module.sh my_new_module

# This creates:
# - my_new_module/ folder with standard structure
# - module.yaml with basic configuration
# - README.md with module overview
# - Basic src/ structure
# - Configuration files
# - Test framework
```

### 2. Module Customization
```yaml
# Edit module.yaml to customize
module:
  name: "my_new_module"
  description: "My custom module for X"
  capabilities:
    - "custom_capability_1"
    - "custom_capability_2"
  
  # Add custom curators
  curators:
    - "custom_curator_1"
    - "custom_curator_2"
  
  # Define custom events
  events:
    published:
      - "my-custom-event-1.0"
    consumed:
      - "other-module-event-1.0"
```

### 3. Module Development
```python
# Implement custom components
class MyCustomComponent:
    def __init__(self, config):
        self.config = config
    
    def process(self, data):
        # Custom processing logic
        return processed_data

# Implement custom curators
class MyCustomCurator:
    def __init__(self):
        self.mandate = "Custom curator mandate"
    
    def evaluate(self, data):
        # Custom evaluation logic
        return evaluation_result
```

### 4. Module Testing
```bash
# Run tests
./scripts/test.sh

# Run specific test types
./scripts/test.sh unit
./scripts/test.sh integration
./scripts/test.sh e2e
```

### 5. Module Deployment
```bash
# Deploy module
./scripts/deploy.sh

# Deploy to specific environment
./scripts/deploy.sh development
./scripts/deploy.sh production
```

## Communication Integration

### Event Schema Registration
```yaml
# Register custom events in module.yaml
events:
  published:
    - "my-custom-event-1.0"
  consumed:
    - "other-module-event-1.0"

# Define event schemas
event_schemas:
  "my-custom-event-1.0":
    description: "My custom event"
    payload_schema:
      type: "object"
      properties:
        custom_field:
          type: "string"
        custom_data:
          type: "object"
```

### Database Schema Integration
```sql
-- Custom tables for module
CREATE TABLE my_custom_table (
    id UUID PRIMARY KEY,
    custom_field TEXT NOT NULL,
    custom_data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Integration with standard tables
CREATE TABLE my_module_outbox (
    id UUID PRIMARY KEY,
    event_type TEXT NOT NULL,
    target_modules TEXT[] NOT NULL,
    payload JSONB NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Quality Assurance

### Module Validation
```python
class ModuleValidator:
    def validate_module(self, module_path):
        """Validate module structure and configuration"""
        # Check required files
        required_files = [
            'module.yaml',
            'README.md',
            'src/main.py',
            'database/schema.sql'
        ]
        
        for file in required_files:
            if not os.path.exists(os.path.join(module_path, file)):
                raise ValidationError(f"Missing required file: {file}")
        
        # Validate module.yaml
        self.validate_module_yaml(module_path)
        
        # Validate database schema
        self.validate_database_schema(module_path)
        
        # Validate event schemas
        self.validate_event_schemas(module_path)
```

### Integration Testing
```python
class IntegrationTester:
    def test_module_integration(self, module_name):
        """Test module integration with system"""
        # Test database connectivity
        self.test_database_connectivity(module_name)
        
        # Test event publishing
        self.test_event_publishing(module_name)
        
        # Test event consumption
        self.test_event_consumption(module_name)
        
        # Test curator functionality
        self.test_curator_functionality(module_name)
```

## Monitoring and Maintenance

### Module Health Monitoring
```yaml
# Health check configuration
health_checks:
  - name: "database_connectivity"
    type: "database"
    config:
      connection_string: "${DATABASE_URL}"
  
  - name: "event_bus_connectivity"
    type: "event_bus"
    config:
      event_bus_url: "${EVENT_BUS_URL}"
  
  - name: "curator_health"
    type: "curator"
    config:
      curator_types: ["dsi", "pattern", "divergence"]
```

### Performance Monitoring
```yaml
# Performance metrics
monitoring:
  metrics:
    - name: "processing_rate"
      type: "counter"
      description: "Events processed per second"
    
    - name: "error_rate"
      type: "gauge"
      description: "Error rate percentage"
    
    - name: "latency"
      type: "histogram"
      description: "Processing latency"
```

## Best Practices

### Module Design
1. **Single Responsibility**: Each module should have one clear purpose
2. **Loose Coupling**: Minimize dependencies between modules
3. **High Cohesion**: Related functionality should be grouped together
4. **Clear Interfaces**: Well-defined communication contracts

### Development Process
1. **Start with Template**: Use standard build pack template
2. **Customize Gradually**: Add custom functionality incrementally
3. **Test Continuously**: Maintain high test coverage
4. **Document Everything**: Keep documentation up to date

### Deployment Strategy
1. **Environment Separation**: Separate dev/staging/prod environments
2. **Configuration Management**: Use environment-specific configs
3. **Health Monitoring**: Implement comprehensive health checks
4. **Rollback Plan**: Always have rollback capability

## Design Document Integration

### **How Module Replication Works with Design Documents**

The `@module_replication/` folder provides **practical implementation guides** that use the **architectural templates** from the design documents:

#### **Design Documents = Architectural Templates** 🏗️
- **`@communication_protocol/`** - How modules communicate (direct table communication)
- **`@learning_systems/`** - How modules learn (strand-braid learning system)
- **`@core_intelligence_architecture/`** - How modules think (curator layer design)

#### **Module Replication = Implementation Guides** 🛠️
- **Build Pack Templates** - Practical folder structures and files
- **Module Creation Scripts** - Automated module generation
- **Configuration Examples** - Real-world configuration files
- **Deployment Guides** - How to actually build and deploy modules

### **The Complete Module Creation Process**

```mermaid
graph TD
    A[Want to Create New Module] --> B[Read Design Documents]
    B --> C[Choose Module Type]
    C --> D[Use Module Replication Templates]
    D --> E[Implement Design Document Templates]
    E --> F[Customize for Your Use Case]
    F --> G[Deploy Module]
    
    B --> H[@communication_protocol/]
    B --> I[@learning_systems/]
    B --> J[@core_intelligence_architecture/]
    
    D --> K[Build Pack Templates]
    D --> L[Creation Scripts]
    D --> M[Configuration Examples]
```

### **Example: Creating a New "Risk Manager" Module**

1. **Read Design Documents** 📚
   - Study `@communication_protocol/` for direct table communication
   - Study `@learning_systems/` for strand-braid learning
   - Study `@core_intelligence_architecture/` for curator layer

2. **Use Module Replication** 🛠️
   - Copy build pack template from `@module_replication/`
   - Run `./scripts/create_module.sh risk_manager`
   - Customize `module.yaml` for risk management

3. **Implement Design Templates** 🏗️
   - Implement `DirectTableCommunicator` for communication
   - Implement `StrandBraidLearning` for learning
   - Implement `CuratorOrchestrator` for intelligence

4. **Deploy and Test** 🚀
   - Run `./scripts/deploy.sh`
   - Test communication with other modules
   - Verify learning system works

### **Why Both Are Needed**

- **Design Documents**: Provide the **"what"** and **"how"** of the architecture
- **Module Replication**: Provides the **"where"** and **"when"** of implementation
- **Together**: Complete system for creating any type of module

---

*This specification provides a comprehensive framework for module replication and build packs, enabling easy creation and deployment of new modules while maintaining system coherence and communication capabilities. It works in conjunction with the design document templates to provide both architectural guidance and practical implementation tools.*
