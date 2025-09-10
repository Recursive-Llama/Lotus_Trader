# Leakage & Adversarial Audit Specification

*Source: [alpha_detector_build_convo.md](../alpha_detector_build_convo.md) + Enhanced Audit Design*

## Overview

First-class, automated checks that can veto a detector before publication. This institutionalizes leakage detection and adversarial testing as core system components, not afterthoughts.

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
        shuffled_scores.append(shuff_score)
    
    random_score = np.mean(shuffled_scores)
    performance_drop = original_score - random_score
    
    if performance_drop < random_threshold:
        return False, f"Performance drop {performance_drop:.3f} < {random_threshold} (suspicious)"
    
    return True, f"Performance drop {performance_drop:.3f} >= {random_threshold} (expected)"
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
            return False, f"Noise {noise_level}: degradation {degradation:.3f} > {max_degradation}"
    
    return True, f"Robust to noise up to {max(noise_levels)}"
```

### 2. Random Bar Drops
**Test**: Drop random bars, check performance impact
```python
def random_drop_test(detector, data, drop_rates=[0.01, 0.05, 0.1], max_degradation=0.2):
    """Test robustness to missing data"""
    original_score = detector.score(data)
    
    for drop_rate in drop_rates:
        dropped_data = drop_random_bars(data, drop_rate)
        dropped_score = detector.score(dropped_data)
        degradation = original_score - dropped_score
        
        if degradation > max_degradation:
            return False, f"Drop {drop_rate}: degradation {degradation:.3f} > {max_degradation}"
    
    return True, f"Robust to drops up to {max(drop_rates)}"
```

### 3. Slippage Shock Test
**Test**: Simulate slippage shocks, check fragility
```python
def slippage_shock_test(detector, data, slippage_levels=[0.001, 0.005, 0.01], max_degradation=0.25):
    """Test robustness to slippage shocks"""
    original_score = detector.score(data)
    
    for slippage in slippage_levels:
        shocked_data = apply_slippage_shocks(data, slippage)
        shocked_score = detector.score(shocked_data)
        degradation = original_score - shocked_score
        
        if degradation > max_degradation:
            return False, f"Slippage {slippage}: degradation {degradation:.3f} > {max_degradation}"
    
    return True, f"Robust to slippage up to {max(slippage_levels)}"
```

## Audit Framework

### Audit Pipeline
```python
class AuditPipeline:
    def __init__(self):
        self.leakage_tests = [
            check_future_timestamps,
            check_label_bleed,
            rolling_origin_cv_test,
            shuffle_test
        ]
        self.adversarial_tests = [
            microstructure_noise_test,
            random_drop_test,
            slippage_shock_test
        ]
    
    def run_audits(self, detector, data):
        """Run all audits and return results"""
        results = {
            'leakage': {},
            'adversarial': {},
            'overall_pass': True,
            'veto_reasons': []
        }
        
        # Run leakage tests
        for test in self.leakage_tests:
            test_name = test.__name__
            passed, message = test(detector, data)
            results['leakage'][test_name] = {'passed': passed, 'message': message}
            
            if not passed:
                results['overall_pass'] = False
                results['veto_reasons'].append(f"Leakage: {message}")
        
        # Run adversarial tests
        for test in self.adversarial_tests:
            test_name = test.__name__
            passed, message = test(detector, data)
            results['adversarial'][test_name] = {'passed': passed, 'message': message}
            
            if not passed:
                results['overall_pass'] = False
                results['veto_reasons'].append(f"Adversarial: {message}")
        
        return results
```

### Curator Integration
```python
def generate_curator_signals(audit_results):
    """Convert audit results to curator signals"""
    signals = {}
    
    # Leakage curator signals
    if not audit_results['leakage']['check_future_timestamps']['passed']:
        signals['leakage_veto'] = True
        signals['leakage_reason'] = audit_results['leakage']['check_future_timestamps']['message']
    
    # Adversarial curator signals
    failed_adversarial = [k for k, v in audit_results['adversarial'].items() if not v['passed']]
    if failed_adversarial:
        signals['adv_fragility'] = len(failed_adversarial) / len(audit_results['adversarial'])
        signals['adv_reasons'] = [audit_results['adversarial'][k]['message'] for k in failed_adversarial]
    
    return signals
```

## Database Schema

### Audit Results Table
```sql
CREATE TABLE audit_results (
    id UUID PRIMARY KEY,
    detector_id UUID REFERENCES detector_registry(id),
    audit_type TEXT NOT NULL,  -- 'leakage', 'adversarial'
    test_name TEXT NOT NULL,
    passed BOOLEAN NOT NULL,
    message TEXT,
    test_parameters JSONB,
    execution_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_audit_results_detector ON audit_results(detector_id);
CREATE INDEX idx_audit_results_type ON audit_results(audit_type);
CREATE INDEX idx_audit_results_passed ON audit_results(passed);
```

### Curator Audit Signals Table
```sql
CREATE TABLE curator_audit_signals (
    id UUID PRIMARY KEY,
    detector_id UUID REFERENCES detector_registry(id),
    curator_type TEXT NOT NULL,  -- 'leakage', 'adversarial'
    signal_type TEXT NOT NULL,   -- 'veto', 'warning', 'info'
    signal_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## API Endpoints

### Run Audits
```python
POST /audit/run
{
    "detector_id": "uuid",
    "audit_types": ["leakage", "adversarial"],
    "test_parameters": {
        "degradation_threshold": 0.2,
        "noise_levels": [0.01, 0.05, 0.1]
    }
}

# Response
{
    "audit_id": "uuid",
    "status": "running",
    "estimated_completion": "2025-01-15T14:35:00Z"
}
```

### Get Audit Results
```python
GET /audit/results/{audit_id}
GET /audit/results/detector/{detector_id}
GET /audit/results/detector/{detector_id}/latest
```

### Curator Signals
```python
GET /audit/curator-signals/{detector_id}
# Returns curator signals generated from audit results
```

## Monitoring & Alerting

### Audit Metrics
- **Audit pass rate**: Percentage of detectors passing all audits
- **Leakage detection rate**: Frequency of leakage violations
- **Adversarial failure rate**: Frequency of fragility detections
- **Audit execution time**: Performance of audit pipeline

### Alerts
- **High leakage rate**: Too many detectors failing leakage tests
- **Audit timeouts**: Long-running audit processes
- **Curator signal backlog**: Pending curator decisions
- **False positive rate**: Audits incorrectly flagging good detectors

## Implementation Notes

### Performance
- Audits run asynchronously to avoid blocking signal generation
- Parallel execution of independent tests
- Caching of test results for repeated runs
- Incremental testing for detector updates

### Reliability
- Audit results are immutable once written
- Full audit trail for compliance
- Rollback capability for failed audits
- Circuit breakers for test failures

### Scalability
- Horizontal scaling via test distribution
- Queue-based processing for high volume
- Result aggregation for large detector sets
- Compression for large audit data
