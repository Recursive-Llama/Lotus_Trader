# Enhanced Leakage & Adversarial Audit Specification - Trading Intelligence System

*Source: [build_docs_v1/LEAKAGE_AUDIT_SPEC.md](../build_docs_v1/LEAKAGE_AUDIT_SPEC.md) + Trading Intelligence System Integration*

## Overview

First-class, automated checks that can veto a detector before publication. This institutionalizes leakage detection and adversarial testing as core system components, not afterthoughts. The system prevents data leakage and detects fragility before signals reach production, with all audits producing curator signals that can veto or downgrade detectors.

## Core Principle

**Prevent data leakage and detect fragility before signals reach production.** All audits produce curator signals that can veto or downgrade detectors.

## Leakage Tests

### 1. Future Timestamp Leakage
**Test**: Block if any transform touches future timestamps
```python
def check_future_timestamps(features, target_timestamps):
    """Ensure no feature uses data from future timestamps"""
    for feature_name, feature_data in features.items():
        if feature_data.timestamp > target_timestamps:
            return False, f"Feature {feature_name} uses future data"
    return True, "No future timestamp leakage"

# Enhanced for Trading Intelligence System
def check_future_timestamps_enhanced(trading_plan, dsi_evidence, target_timestamps):
    """Enhanced future timestamp check for trading plans and DSI evidence"""
    # Check trading plan features
    for feature_name, feature_data in trading_plan.features.items():
        if feature_data.timestamp > target_timestamps:
            return False, f"Trading plan feature {feature_name} uses future data"
    
    # Check DSI evidence
    if dsi_evidence and dsi_evidence.get('timestamp', 0) > target_timestamps:
        return False, "DSI evidence uses future data"
    
    return True, "No future timestamp leakage"
```

### 2. Label Bleed Prevention
**Test**: Block if target labels are reused in features
```python
def check_label_bleed(features, target_labels):
    """Ensure target labels are not used as features"""
    for feature_name, feature_data in features.items():
        if np.array_equal(feature_data, target_labels):
            return False, f"Feature {feature_name} contains target labels"
    return True, "No label bleed detected"

# Enhanced for Trading Intelligence System
def check_label_bleed_enhanced(trading_plan, target_returns):
    """Enhanced label bleed check for trading plans"""
    # Check trading plan features against target returns
    for feature_name, feature_data in trading_plan.features.items():
        if np.array_equal(feature_data, target_returns):
            return False, f"Trading plan feature {feature_name} contains target returns"
    
    # Check DSI evidence against target returns
    if hasattr(trading_plan, 'dsi_evidence'):
        dsi_features = trading_plan.dsi_evidence.get('features', {})
        for feature_name, feature_data in dsi_features.items():
            if np.array_equal(feature_data, target_returns):
                return False, f"DSI feature {feature_name} contains target returns"
    
    return True, "No label bleed detected"
```

### 3. Rolling-Origin Cross-Validation
**Test**: Performance degradation gap between in-fold and OOS > τ → veto
```python
def rolling_origin_cv_test(detector, data, cv_folds=5, degradation_threshold=0.2):
    """Test for performance degradation in out-of-sample data"""
    in_fold_scores = []
    oos_scores = []
    
    for fold in range(cv_folds):
        train_data, test_data = split_rolling_origin(data, fold)
        
        # Train on in-fold
        detector.fit(train_data)
        in_score = detector.score(train_data)
        in_fold_scores.append(in_score)
        
        # Test on out-of-sample
        oos_score = detector.score(test_data)
        oos_scores.append(oos_score)
    
    degradation = np.mean(in_fold_scores) - np.mean(oos_scores)
    
    if degradation > degradation_threshold:
        return False, f"Performance degradation: {degradation:.3f} > {degradation_threshold}"
    
    return True, f"Performance degradation: {degradation:.3f} <= {degradation_threshold}"

# Enhanced for Trading Intelligence System
def rolling_origin_cv_test_enhanced(trading_plan_generator, data, cv_folds=5, degradation_threshold=0.2):
    """Enhanced rolling origin CV for trading plan generators"""
    in_fold_scores = []
    oos_scores = []
    
    for fold in range(cv_folds):
        train_data, test_data = split_rolling_origin(data, fold)
        
        # Train trading plan generator
        trading_plan_generator.fit(train_data)
        
        # Evaluate on in-fold
        in_plans = trading_plan_generator.generate_plans(train_data)
        in_score = evaluate_trading_plans(in_plans, train_data)
        in_fold_scores.append(in_score)
        
        # Evaluate on out-of-sample
        oos_plans = trading_plan_generator.generate_plans(test_data)
        oos_score = evaluate_trading_plans(oos_plans, test_data)
        oos_scores.append(oos_score)
    
    degradation = np.mean(in_fold_scores) - np.mean(oos_scores)
    
    if degradation > degradation_threshold:
        return False, f"Trading plan degradation: {degradation:.3f} > {degradation_threshold}"
    
    return True, f"Trading plan degradation: {degradation:.3f} <= {degradation_threshold}"
```

### 4. Shuffle Test
**Test**: Performance collapses to random under label shuffle → pass expected
```python
def shuffle_test(detector, data, n_shuffles=100, random_threshold=0.1):
    """Test if performance collapses under label shuffling"""
    original_score = detector.score(data)
    
    shuffled_scores = []
    for _ in range(n_shuffles):
        shuffled_data = data.copy()
        shuffled_data['target'] = np.random.permutation(shuffled_data['target'])
        shuffled_score = detector.score(shuffled_data)
        shuffled_scores.append(shuffled_score)
    
    random_score = np.mean(shuffled_scores)
    performance_drop = original_score - random_score
    
    if performance_drop < random_threshold:
        return False, f"Performance drop {performance_drop:.3f} < {random_threshold} (suspicious)"
    
    return True, f"Performance drop {performance_drop:.3f} >= {random_threshold} (expected)"

# Enhanced for Trading Intelligence System
def shuffle_test_enhanced(trading_plan_generator, data, n_shuffles=100, random_threshold=0.1):
    """Enhanced shuffle test for trading plan generators"""
    original_plans = trading_plan_generator.generate_plans(data)
    original_score = evaluate_trading_plans(original_plans, data)
    
    shuffled_scores = []
    for _ in range(n_shuffles):
        shuffled_data = data.copy()
        shuffled_data['target_returns'] = np.random.permutation(shuffled_data['target_returns'])
        
        shuffled_plans = trading_plan_generator.generate_plans(shuffled_data)
        shuffled_score = evaluate_trading_plans(shuffled_plans, shuffled_data)
        shuffled_scores.append(shuffled_score)
    
    random_score = np.mean(shuffled_scores)
    performance_drop = original_score - random_score
    
    if performance_drop < random_threshold:
        return False, f"Trading plan performance drop {performance_drop:.3f} < {random_threshold} (suspicious)"
    
    return True, f"Trading plan performance drop {performance_drop:.3f} >= {random_threshold} (expected)"
```

### 5. DSI Evidence Leakage
**Test**: Ensure DSI evidence doesn't contain future information
```python
def check_dsi_evidence_leakage(dsi_evidence, target_timestamps):
    """Check DSI evidence for future information leakage"""
    if not dsi_evidence:
        return True, "No DSI evidence to check"
    
    # Check MicroTape tokens
    microtape_tokens = dsi_evidence.get('microtape_tokens', [])
    for token in microtape_tokens:
        if token.get('timestamp', 0) > target_timestamps:
            return False, f"MicroTape token uses future data: {token['timestamp']}"
    
    # Check expert outputs
    expert_outputs = dsi_evidence.get('expert_outputs', {})
    for expert_name, output in expert_outputs.items():
        if output.get('timestamp', 0) > target_timestamps:
            return False, f"Expert {expert_name} output uses future data"
    
    # Check evidence fusion
    fusion_timestamp = dsi_evidence.get('fusion_timestamp', 0)
    if fusion_timestamp > target_timestamps:
        return False, f"Evidence fusion uses future data: {fusion_timestamp}"
    
    return True, "No DSI evidence leakage detected"
```

### 6. Module Communication Leakage
**Test**: Ensure module communication doesn't leak future information
```python
def check_module_communication_leakage(module_messages, target_timestamps):
    """Check module communication for future information leakage"""
    for message in module_messages:
        # Check message timestamp
        if message.get('timestamp', 0) > target_timestamps:
            return False, f"Module message uses future data: {message['timestamp']}"
        
        # Check message payload
        payload = message.get('payload', {})
        if payload.get('timestamp', 0) > target_timestamps:
            return False, f"Module message payload uses future data"
        
        # Check trading plan in message
        trading_plan = payload.get('trading_plan')
        if trading_plan and trading_plan.get('timestamp', 0) > target_timestamps:
            return False, f"Trading plan in module message uses future data"
    
    return True, "No module communication leakage detected"
```

## Adversarial Tests

### 1. Microstructure Noise Injection
**Test**: Inject noise, check if det_sigma craters beyond cap
```python
def microstructure_noise_test(detector, data, noise_levels=[0.01, 0.05, 0.1], max_degradation=0.3):
    """Test robustness to microstructure noise"""
    original_score = detector.score(data)
    
    for noise_level in noise_levels:
        noisy_data = inject_microstructure_noise(data, noise_level)
        noisy_score = detector.score(noisy_data)
        degradation = original_score - noisy_score
        
        if degradation > max_degradation:
            return False, f"Noise level {noise_level}: degradation {degradation:.3f} > {max_degradation}"
    
    return True, f"All noise levels within degradation limit {max_degradation}"

# Enhanced for Trading Intelligence System
def microstructure_noise_test_enhanced(trading_plan_generator, data, noise_levels=[0.01, 0.05, 0.1], max_degradation=0.3):
    """Enhanced microstructure noise test for trading plan generators"""
    original_plans = trading_plan_generator.generate_plans(data)
    original_score = evaluate_trading_plans(original_plans, data)
    
    for noise_level in noise_levels:
        noisy_data = inject_microstructure_noise(data, noise_level)
        noisy_plans = trading_plan_generator.generate_plans(noisy_data)
        noisy_score = evaluate_trading_plans(noisy_plans, noisy_data)
        degradation = original_score - noisy_score
        
        if degradation > max_degradation:
            return False, f"Noise level {noise_level}: trading plan degradation {degradation:.3f} > {max_degradation}"
    
    return True, f"All noise levels within trading plan degradation limit {max_degradation}"

def inject_microstructure_noise(data, noise_level):
    """Inject microstructure noise into data"""
    noisy_data = data.copy()
    
    # Add noise to price data
    if 'price' in noisy_data.columns:
        noise = np.random.normal(0, noise_level, len(noisy_data))
        noisy_data['price'] *= (1 + noise)
    
    # Add noise to volume data
    if 'volume' in noisy_data.columns:
        noise = np.random.normal(0, noise_level, len(noisy_data))
        noisy_data['volume'] *= (1 + noise)
    
    # Add noise to order book data
    if 'bid_price' in noisy_data.columns:
        noise = np.random.normal(0, noise_level, len(noisy_data))
        noisy_data['bid_price'] *= (1 + noise)
        noisy_data['ask_price'] *= (1 + noise)
    
    return noisy_data
```

### 2. Regime Shift Testing
**Test**: Performance under regime changes
```python
def regime_shift_test(detector, data, regime_changes=5, max_degradation=0.4):
    """Test robustness to regime changes"""
    original_score = detector.score(data)
    
    for i in range(regime_changes):
        # Simulate regime change by shifting data distribution
        shifted_data = simulate_regime_shift(data, shift_magnitude=0.1 * (i + 1))
        shifted_score = detector.score(shifted_data)
        degradation = original_score - shifted_score
        
        if degradation > max_degradation:
            return False, f"Regime shift {i+1}: degradation {degradation:.3f} > {max_degradation}"
    
    return True, f"All regime shifts within degradation limit {max_degradation}"

# Enhanced for Trading Intelligence System
def regime_shift_test_enhanced(trading_plan_generator, data, regime_changes=5, max_degradation=0.4):
    """Enhanced regime shift test for trading plan generators"""
    original_plans = trading_plan_generator.generate_plans(data)
    original_score = evaluate_trading_plans(original_plans, data)
    
    for i in range(regime_changes):
        shifted_data = simulate_regime_shift(data, shift_magnitude=0.1 * (i + 1))
        shifted_plans = trading_plan_generator.generate_plans(shifted_data)
        shifted_score = evaluate_trading_plans(shifted_plans, shifted_data)
        degradation = original_score - shifted_score
        
        if degradation > max_degradation:
            return False, f"Regime shift {i+1}: trading plan degradation {degradation:.3f} > {max_degradation}"
    
    return True, f"All regime shifts within trading plan degradation limit {max_degradation}"

def simulate_regime_shift(data, shift_magnitude=0.1):
    """Simulate regime shift by shifting data distribution"""
    shifted_data = data.copy()
    
    # Shift price data
    if 'price' in shifted_data.columns:
        shift = np.random.normal(0, shift_magnitude, len(shifted_data))
        shifted_data['price'] *= (1 + shift)
    
    # Shift volatility
    if 'volatility' in shifted_data.columns:
        shift = np.random.normal(0, shift_magnitude, len(shifted_data))
        shifted_data['volatility'] *= (1 + shift)
    
    return shifted_data
```

### 3. DSI Expert Failure Testing
**Test**: Performance when DSI experts fail or provide poor evidence
```python
def dsi_expert_failure_test(trading_plan_generator, data, failure_rates=[0.1, 0.3, 0.5], max_degradation=0.2):
    """Test robustness to DSI expert failures"""
    original_plans = trading_plan_generator.generate_plans(data)
    original_score = evaluate_trading_plans(original_plans, data)
    
    for failure_rate in failure_rates:
        # Simulate DSI expert failures
        failed_data = simulate_dsi_expert_failures(data, failure_rate)
        failed_plans = trading_plan_generator.generate_plans(failed_data)
        failed_score = evaluate_trading_plans(failed_plans, failed_data)
        degradation = original_score - failed_score
        
        if degradation > max_degradation:
            return False, f"DSI failure rate {failure_rate}: degradation {degradation:.3f} > {max_degradation}"
    
    return True, f"All DSI failure rates within degradation limit {max_degradation}"

def simulate_dsi_expert_failures(data, failure_rate):
    """Simulate DSI expert failures by corrupting evidence"""
    failed_data = data.copy()
    
    # Corrupt DSI evidence
    if 'dsi_evidence' in failed_data.columns:
        for i in range(len(failed_data)):
            if np.random.random() < failure_rate:
                # Corrupt DSI evidence
                failed_data.loc[i, 'dsi_evidence'] = {
                    'mx_evidence': 0.0,
                    'mx_confirm': False,
                    'mx_confidence': 0.0
                }
    
    return failed_data
```

### 4. Module Communication Failure Testing
**Test**: Performance when module communication fails
```python
def module_communication_failure_test(trading_plan_generator, data, failure_rates=[0.1, 0.3, 0.5], max_degradation=0.2):
    """Test robustness to module communication failures"""
    original_plans = trading_plan_generator.generate_plans(data)
    original_score = evaluate_trading_plans(original_plans, data)
    
    for failure_rate in failure_rates:
        # Simulate module communication failures
        failed_data = simulate_module_communication_failures(data, failure_rate)
        failed_plans = trading_plan_generator.generate_plans(failed_data)
        failed_score = evaluate_trading_plans(failed_plans, failed_data)
        degradation = original_score - failed_score
        
        if degradation > max_degradation:
            return False, f"Module communication failure rate {failure_rate}: degradation {degradation:.3f} > {max_degradation}"
    
    return True, f"All module communication failure rates within degradation limit {max_degradation}"

def simulate_module_communication_failures(data, failure_rate):
    """Simulate module communication failures by corrupting messages"""
    failed_data = data.copy()
    
    # Corrupt module intelligence
    if 'module_intelligence' in failed_data.columns:
        for i in range(len(failed_data)):
            if np.random.random() < failure_rate:
                # Corrupt module intelligence
                failed_data.loc[i, 'module_intelligence'] = {
                    'learning_rate': 0.0,
                    'innovation_score': 0.0,
                    'collaboration_score': 0.0
                }
    
    return failed_data
```

## Audit Integration with Trading Intelligence System

### Curator Integration
```python
class LeakageAuditCurator:
    def __init__(self):
        self.audit_tests = [
            check_future_timestamps_enhanced,
            check_label_bleed_enhanced,
            rolling_origin_cv_test_enhanced,
            shuffle_test_enhanced,
            check_dsi_evidence_leakage,
            check_module_communication_leakage
        ]
        
        self.adversarial_tests = [
            microstructure_noise_test_enhanced,
            regime_shift_test_enhanced,
            dsi_expert_failure_test,
            module_communication_failure_test
        ]
    
    def audit_trading_plan(self, trading_plan, data, target_timestamps):
        """Audit trading plan for leakage and fragility"""
        audit_results = {
            'leakage_tests': {},
            'adversarial_tests': {},
            'overall_pass': True,
            'veto_reasons': []
        }
        
        # Run leakage tests
        for test in self.audit_tests:
            try:
                passed, message = test(trading_plan, data, target_timestamps)
                audit_results['leakage_tests'][test.__name__] = {
                    'passed': passed,
                    'message': message
                }
                if not passed:
                    audit_results['overall_pass'] = False
                    audit_results['veto_reasons'].append(f"Leakage: {message}")
            except Exception as e:
                audit_results['leakage_tests'][test.__name__] = {
                    'passed': False,
                    'message': f"Test failed: {str(e)}"
                }
                audit_results['overall_pass'] = False
                audit_results['veto_reasons'].append(f"Leakage test error: {str(e)}")
        
        # Run adversarial tests
        for test in self.adversarial_tests:
            try:
                passed, message = test(trading_plan, data)
                audit_results['adversarial_tests'][test.__name__] = {
                    'passed': passed,
                    'message': message
                }
                if not passed:
                    audit_results['overall_pass'] = False
                    audit_results['veto_reasons'].append(f"Adversarial: {message}")
            except Exception as e:
                audit_results['adversarial_tests'][test.__name__] = {
                    'passed': False,
                    'message': f"Test failed: {str(e)}"
                }
                audit_results['overall_pass'] = False
                audit_results['veto_reasons'].append(f"Adversarial test error: {str(e)}")
        
        return audit_results
    
    def generate_curator_signal(self, audit_results):
        """Generate curator signal based on audit results"""
        if audit_results['overall_pass']:
            return {
                'action': 'approve',
                'confidence': 1.0,
                'message': 'All audits passed'
            }
        else:
            return {
                'action': 'veto',
                'confidence': 1.0,
                'message': f"Audit failures: {', '.join(audit_results['veto_reasons'])}"
            }
```

### Automated Audit Pipeline
```python
class AutomatedAuditPipeline:
    def __init__(self):
        self.leakage_curator = LeakageAuditCurator()
        self.audit_queue = []
        self.audit_results = {}
    
    def queue_audit(self, trading_plan, data, target_timestamps):
        """Queue trading plan for audit"""
        audit_request = {
            'trading_plan': trading_plan,
            'data': data,
            'target_timestamps': target_timestamps,
            'timestamp': datetime.now(),
            'status': 'queued'
        }
        self.audit_queue.append(audit_request)
    
    def process_audit_queue(self):
        """Process queued audits"""
        while self.audit_queue:
            audit_request = self.audit_queue.pop(0)
            
            try:
                # Run audit
                audit_results = self.leakage_curator.audit_trading_plan(
                    audit_request['trading_plan'],
                    audit_request['data'],
                    audit_request['target_timestamps']
                )
                
                # Store results
                audit_id = f"audit_{len(self.audit_results)}"
                self.audit_results[audit_id] = {
                    **audit_request,
                    'audit_results': audit_results,
                    'status': 'completed'
                }
                
                # Generate curator signal
                curator_signal = self.leakage_curator.generate_curator_signal(audit_results)
                
                # Send signal to curator system
                self.send_curator_signal(curator_signal)
                
            except Exception as e:
                audit_request['status'] = 'failed'
                audit_request['error'] = str(e)
                self.audit_results[f"audit_{len(self.audit_results)}"] = audit_request
    
    def send_curator_signal(self, curator_signal):
        """Send curator signal to curator system"""
        # Implementation would send signal to curator system
        pass
```

## Performance Requirements

### Audit Latency Targets
- **Leakage Tests**: < 100ms per test
- **Adversarial Tests**: < 500ms per test
- **Full Audit Pipeline**: < 2 seconds per trading plan
- **Batch Processing**: 1000+ trading plans per minute

### Audit Accuracy Targets
- **Leakage Detection**: > 95% accuracy
- **False Positive Rate**: < 5%
- **False Negative Rate**: < 2%
- **Adversarial Detection**: > 90% accuracy

## Configuration

```yaml
leakage_audit:
  # Leakage Test Configuration
  leakage_tests:
    future_timestamp:
      enabled: true
      strict_mode: true
    
    label_bleed:
      enabled: true
      threshold: 0.95
    
    rolling_origin_cv:
      enabled: true
      cv_folds: 5
      degradation_threshold: 0.2
    
    shuffle_test:
      enabled: true
      n_shuffles: 100
      random_threshold: 0.1
    
    dsi_evidence_leakage:
      enabled: true
      strict_mode: true
    
    module_communication_leakage:
      enabled: true
      strict_mode: true
  
  # Adversarial Test Configuration
  adversarial_tests:
    microstructure_noise:
      enabled: true
      noise_levels: [0.01, 0.05, 0.1]
      max_degradation: 0.3
    
    regime_shift:
      enabled: true
      regime_changes: 5
      max_degradation: 0.4
    
    dsi_expert_failure:
      enabled: true
      failure_rates: [0.1, 0.3, 0.5]
      max_degradation: 0.2
    
    module_communication_failure:
      enabled: true
      failure_rates: [0.1, 0.3, 0.5]
      max_degradation: 0.2
  
  # Performance Configuration
  performance:
    max_audit_latency_ms: 2000
    batch_size: 100
    parallel_processing: true
    cache_results: true
```

---

*This enhanced leakage and adversarial audit specification provides comprehensive testing for the Trading Intelligence System, ensuring data integrity and system robustness.*
