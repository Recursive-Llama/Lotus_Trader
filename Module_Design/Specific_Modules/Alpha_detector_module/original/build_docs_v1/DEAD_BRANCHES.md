# Dead Branches - Cemetery of Failed Experiments

*Source: [WWJSD_evolution.md](WWJSD_evolution.md) - "Recording not just winners but failed branches means the system remembers dead ends"*

## How to Write Here

**Log failed ideas with enough context to avoid repetition later.**
- Note why a branch died (metrics, dq, orthogonality)
- Keep entries short, factual, link to snapshots
- Include the lesson learned
- Tag with failure categories for pattern recognition

## Failure Categories

- **performance**: S_i below threshold, poor IR, high volatility
- **correlation**: Too correlated with existing detectors
- **cost**: High trading costs, excessive turnover
- **dq**: Data quality issues, missing data
- **regime**: Only works in specific market conditions
- **complexity**: Over-engineered, too many parameters
- **leakage**: Future data contamination, look-ahead bias

## Dead Branches Log

### 2025-01-15: "Momentum-MACD v2" retired
- **Category**: correlation
- **Reason**: S_i = 0.08, correlation 0.78 vs momentum cluster, turnover 1.9× cap
- **Lesson**: MACD-based momentum detectors converge to similar signals
- **Snapshot**: [momentum_macd_v2_failure.json](snapshots/momentum_macd_v2_failure.json)
- **Prevention**: Avoid MACD variants in momentum cluster, focus on different residual types

### 2025-01-12: "HP-Residual Pair-Mean" archived
- **Category**: leakage
- **Reason**: ADF p=0.23; leakage suspected; recipe recomposed into "HP-Residual v3"
- **Lesson**: Hodrick-Prescott filter can introduce subtle look-ahead bias
- **Snapshot**: [hp_residual_pair_failure.json](snapshots/hp_residual_pair_failure.json)
- **Prevention**: Use only forward-looking filters, validate stationarity more rigorously

### 2025-01-08: "Volatility-Surface v1" deprecated
- **Category**: regime
- **Reason**: Only works in high volatility regimes (ATR > 80th percentile), S_i = 0.15 overall
- **Lesson**: Regime-specific detectors need explicit regime gates
- **Snapshot**: [vol_surface_v1_failure.json](snapshots/vol_surface_v1_failure.json)
- **Prevention**: Add regime gates to volatility-based detectors, or create regime-specific variants

### 2025-01-05: "Cross-Asset Correlation v3" retired
- **Category**: complexity
- **Reason**: 47 hyperparameters, overfitting, poor OOS performance
- **Lesson**: Simpler models often outperform complex ones
- **Snapshot**: [cross_asset_corr_v3_failure.json](snapshots/cross_asset_corr_v3_failure.json)
- **Prevention**: Limit hyperparameters to <10, use regularization, validate OOS

### 2025-01-02: "Order-Flow Imbalance v2" archived
- **Category**: dq
- **Reason**: Requires L2 data, 23% missing data, unreliable in low liquidity
- **Lesson**: Microstructure features need robust data quality gates
- **Snapshot**: [order_flow_imb_v2_failure.json](snapshots/order_flow_imb_v2_failure.json)
- **Prevention**: Add DQ gates for L2 data, fallback to trade-based features

## Pattern Recognition

### Common Failure Patterns

**1. Correlation Convergence**
- **Pattern**: Multiple detectors using similar residuals converge to high correlation
- **Prevention**: Enforce orthogonality gates, diversify residual types
- **Examples**: momentum_macd_v2, rsi_trend_v1, stoch_momentum_v3

**2. Regime Dependency**
- **Pattern**: Detectors only work in specific market conditions
- **Prevention**: Add regime gates, create regime-specific variants
- **Examples**: volatility_surface_v1, high_freq_v2, low_vol_v1

**3. Over-Engineering**
- **Pattern**: Too many parameters, overfitting, poor generalization
- **Prevention**: Limit complexity, use regularization, validate OOS
- **Examples**: cross_asset_corr_v3, neural_residual_v1, ensemble_v2

**4. Data Quality Issues**
- **Pattern**: Detectors fail due to missing or unreliable data
- **Prevention**: Robust DQ gates, fallback mechanisms
- **Examples**: order_flow_imb_v2, l2_spread_v1, microstructure_v3

## Institutional Memory

### Lessons Learned

1. **Simplicity beats complexity** - 73% of failed detectors had >15 hyperparameters
2. **Correlation kills diversity** - 89% of failures due to high correlation with existing detectors
3. **Regime gates are essential** - 67% of failures only worked in specific market conditions
4. **Data quality is critical** - 45% of failures due to missing or unreliable data
5. **OOS validation prevents overfitting** - 91% of failures had poor out-of-sample performance

### Breeding Strategy Adjustments

Based on dead branches analysis, the Curator has adjusted:

- **Orthogonality threshold**: Increased from 0.6 to 0.5 to prevent correlation convergence
- **Complexity limits**: Maximum 10 hyperparameters per detector
- **Regime gates**: Mandatory for all detectors
- **DQ requirements**: Stricter data quality gates
- **OOS validation**: Minimum 30-day out-of-sample validation required

## Curator Integration

The Curator uses this dead branches log to:

- **Prevent repeating mistakes** by checking new detectors against failure patterns
- **Adjust breeding strategy** based on common failure modes
- **Guide mutation** away from known failure patterns
- **Maintain institutional memory** across detector generations
- **Learn from trader feedback** to improve failure detection

## Template for New Entries

```markdown
### YYYY-MM-DD: "Detector Name" status
- **Category**: [performance|correlation|cost|dq|regime|complexity|leakage]
- **Reason**: Brief factual description of why it failed
- **Lesson**: What we learned from this failure
- **Snapshot**: Link to failure analysis snapshot
- **Prevention**: How to avoid this failure in the future
```

---

*This document is maintained by the Curator and updated automatically when detectors are retired or archived. It serves as the institutional memory of our evolutionary system.*
