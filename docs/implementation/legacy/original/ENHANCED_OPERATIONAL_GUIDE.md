# Enhanced Operational Guide - Trading Intelligence System

*Source: [build_docs_v1/OPERATOR_GUIDE.md](../build_docs_v1/OPERATOR_GUIDE.md) + Trading Intelligence System Integration*

## Overview

This guide provides comprehensive operational procedures for the Trading Intelligence System, including startup procedures, health monitoring, troubleshooting, and maintenance workflows. This system operates as a **Trading Intelligence System** with module-level intelligence and organic replication.

## System Lifecycle

### Life of a Minute

The system operates as a conveyor belt that ticks once per minute:

1. **WS Ingest** → Per-asset accumulators (trades, BBO, L2)
2. **Minute Close** → Bar closes with lateness watermark (~1-1.5s)
3. **Feature Build** → Raw features → baselines → z/quantiles → DQ
4. **Snapshot Write** → UPSERT to `features_snapshot`
5. **Market Context** → Build breadth/leader/RS for timestamp
6. **Detector Pass** → Evaluate rules on finished 1m row
7. **DSI Processing** → MicroTape tokenization and expert evaluation
8. **Trading Plan Generation** → Complete trading plans with DSI validation
9. **Module Communication** → Inter-module intelligence sharing
10. **Event Publish** → Score, debounce, and send events

## Run Modes

### 1. Dry-Run
- **What**: Ingest + build + write snapshots + DSI processing
- **Trading Plans**: Generate but don't publish (log candidates)
- **Module Communication**: Internal only, no external publishing
- **Goal**: Prove bars are correct and fast enough

### 2. Shadow
- **What**: Trading plans write to internal table/topic
- **Module Communication**: Full internal communication
- **Goal**: Sanity-check counts, severities, suppression

### 3. Canary
- **What**: Real publications for few high-liquidity symbols
- **Module Communication**: Limited external communication
- **Goal**: Confirm behavior under real flow

### 4. Production
- **What**: Full Top-N + hotlist with all controls
- **Module Communication**: Full inter-module communication
- **Goal**: Live system with budgets, cooldowns, gates

### 5. Replay
- **What**: Offline, deterministic validation
- **Module Communication**: Simulated communication
- **Goal**: Guarantee bit-identical reproduction

## First Hour Checklist

### 0-10 minutes
- [ ] Start WS ingest for 3-5 symbols (BTC/ETH/SOL)
- [ ] Verify 1m rows appear ~150-300ms after minute close
- [ ] Check DQ ≥95% ok (no trades? BBO still gives mid_close)
- [ ] Confirm DSI processing latency < 10ms

### 10-20 minutes
- [ ] Watch baselines warm (z_* = NULL until ~200 samples)
- [ ] Confirm `ingest_lag_ms` p95 < 300ms
- [ ] Check `book_staleness_ms` typically < 1000ms on majors
- [ ] Verify module communication channels are active

### 20-40 minutes (dry-run)
- [ ] Enable 3 spike detectors in shadow
- [ ] See shadowed candidates on active names
- [ ] Verify suppression = 0 (not publishing)
- [ ] Confirm DSI evidence generation working

### 40-60 minutes (canary)
- [ ] Flip canary on BTC/ETH for spikes only
- [ ] Confirm events show up <150ms after snapshot write
- [ ] Check budget utilization < 0.5 for spike class
- [ ] Verify no events during `dq_status != ok` minutes
- [ ] Confirm trading plan generation working

## Health Indicators

### 1. Pipeline Latency
- **Green**: Bar finalize p95 < 300ms; end-to-end p95 < 450ms
- **Amber**: p95 300-500ms → detector deferrals may kick in
- **Red**: p95 > 500ms → fix before widening scope

### 2. Data Quality
- **Green**: ≥95% 1m rows `dq=ok` on majors; few nulls outside L2
- **Amber**: Growing `book_staleness_ms`, OI staleness >20s
- **Red**: Frequent stale → events sparse; check WS and clock skew

### 3. Event Health
- **Green**: Class mix close to defaults; suppression <5%; severities p50 ~60-70
- **Amber**: Floods (budgets hit) or droughts → thresholds need tuning
- **Red**: Everything suppressed for DQ/illiquidity → guardrails too tight

### 4. Baseline Drift
- **Green**: |mean| ≤ 0.2, std in [0.8,1.2]
- **Amber/Red**: Drift means normalizer off; Curator will propose tweaks

### 5. DSI Health
- **Green**: DSI processing < 10ms; evidence accuracy > 70%
- **Amber**: DSI latency 10-20ms; evidence accuracy 60-70%
- **Red**: DSI latency > 20ms; evidence accuracy < 60%

### 6. Module Communication Health
- **Green**: Message delivery rate > 99%; latency < 50ms
- **Amber**: Message delivery rate 95-99%; latency 50-100ms
- **Red**: Message delivery rate < 95%; latency > 100ms

### 7. Module Intelligence Health
- **Green**: Learning rates stable; innovation scores > 0.5
- **Amber**: Learning rates fluctuating; innovation scores 0.3-0.5
- **Red**: Learning rates declining; innovation scores < 0.3

## Troubleshooting

### Common Issues

#### 1. High Latency
**Symptoms**: p95 latency > 500ms
**Causes**:
- WebSocket connection issues
- Database connection pool exhaustion
- DSI processing bottlenecks
- Module communication delays

**Solutions**:
```bash
# Check WebSocket connections
curl -s http://localhost:8080/health/websocket

# Check database connections
curl -s http://localhost:8080/health/database

# Check DSI processing
curl -s http://localhost:8080/health/dsi

# Check module communication
curl -s http://localhost:8080/health/modules
```

#### 2. Data Quality Issues
**Symptoms**: DQ < 95%, frequent nulls
**Causes**:
- WebSocket data gaps
- Clock skew
- L2 book staleness

**Solutions**:
```bash
# Check WebSocket data flow
tail -f logs/websocket.log | grep "data_gap"

# Check clock synchronization
ntpq -p

# Check L2 book staleness
sql "SELECT AVG(book_staleness_ms) FROM features_snapshot WHERE timestamp > NOW() - INTERVAL '1 hour'"
```

#### 3. DSI Processing Issues
**Symptoms**: DSI latency > 20ms, evidence accuracy < 60%
**Causes**:
- MicroTape tokenization bottlenecks
- Expert evaluation delays
- Evidence fusion problems

**Solutions**:
```bash
# Check MicroTape processing
curl -s http://localhost:8080/health/microtape

# Check expert performance
curl -s http://localhost:8080/health/experts

# Check evidence fusion
curl -s http://localhost:8080/health/fusion
```

#### 4. Module Communication Issues
**Symptoms**: Message delivery rate < 95%, high latency
**Causes**:
- Redis connection issues
- Message queue backlog
- Network connectivity problems

**Solutions**:
```bash
# Check Redis health
redis-cli ping

# Check message queue status
curl -s http://localhost:8080/health/message_queue

# Check network connectivity
ping module1.internal
ping module2.internal
```

#### 5. Module Intelligence Issues
**Symptoms**: Learning rates declining, innovation scores < 0.3
**Causes**:
- Insufficient training data
- Learning rate too low
- Module replication failures

**Solutions**:
```bash
# Check module performance
curl -s http://localhost:8080/health/module_performance

# Check learning rates
sql "SELECT module_id, learning_rate FROM module_intelligence WHERE timestamp > NOW() - INTERVAL '1 hour'"

# Check replication status
curl -s http://localhost:8080/health/replication
```

### Emergency Procedures

#### 1. System Overload
**Symptoms**: CPU > 90%, memory > 90%, latency > 1000ms
**Actions**:
1. **Immediate**: Reduce symbol universe to top 5
2. **Short-term**: Disable non-critical detectors
3. **Medium-term**: Scale up resources
4. **Long-term**: Optimize algorithms

#### 2. Data Corruption
**Symptoms**: Inconsistent snapshots, failed validations
**Actions**:
1. **Immediate**: Stop all processing
2. **Short-term**: Restore from backup
3. **Medium-term**: Rebuild corrupted data
4. **Long-term**: Improve data validation

#### 3. Module Failure
**Symptoms**: Module unresponsive, communication failures
**Actions**:
1. **Immediate**: Failover to backup module
2. **Short-term**: Restart failed module
3. **Medium-term**: Investigate root cause
4. **Long-term**: Improve module resilience

## Monitoring & Alerting

### Key Metrics

#### System Metrics
- **Latency**: p95, p99, max
- **Throughput**: Events per second, messages per second
- **Error Rate**: Failed requests, exceptions
- **Resource Usage**: CPU, memory, disk, network

#### Business Metrics
- **Signal Quality**: Accuracy, precision, stability
- **Trading Plan Quality**: Success rate, risk-adjusted returns
- **Module Performance**: Learning rates, innovation scores
- **DSI Evidence**: Accuracy, confidence, processing time

### Alerting Rules

#### Critical Alerts
- **System Down**: Any module unresponsive > 5 minutes
- **Data Loss**: DQ < 90% for > 10 minutes
- **High Latency**: p95 > 1000ms for > 5 minutes
- **Memory Leak**: Memory usage > 95% for > 10 minutes

#### Warning Alerts
- **Performance Degradation**: p95 > 500ms for > 15 minutes
- **DQ Issues**: DQ < 95% for > 30 minutes
- **Module Issues**: Learning rate < 0.01 for > 1 hour
- **DSI Issues**: Evidence accuracy < 70% for > 30 minutes

### Dashboard Configuration

#### System Overview Dashboard
- **Real-time Metrics**: Latency, throughput, error rate
- **Resource Usage**: CPU, memory, disk, network
- **Module Status**: Health, performance, communication
- **DSI Status**: Processing time, evidence quality

#### Business Intelligence Dashboard
- **Signal Performance**: Quality metrics, success rates
- **Trading Plan Performance**: Execution quality, returns
- **Module Intelligence**: Learning progress, innovation
- **System Evolution**: Replication, adaptation, growth

## Maintenance Procedures

### Daily Maintenance
- [ ] Check system health indicators
- [ ] Review error logs and alerts
- [ ] Monitor module performance
- [ ] Verify DSI evidence quality
- [ ] Check module communication health

### Weekly Maintenance
- [ ] Review module replication status
- [ ] Analyze performance trends
- [ ] Update module intelligence parameters
- [ ] Clean up old data and logs
- [ ] Test backup and recovery procedures

### Monthly Maintenance
- [ ] Full system health audit
- [ ] Performance optimization review
- [ ] Security update review
- [ ] Capacity planning review
- [ ] Disaster recovery testing

## Configuration Management

### Runtime Configuration Updates
```bash
# Update detector parameters
curl -X POST http://localhost:8080/config/detectors \
  -H "Content-Type: application/json" \
  -d '{"detector_id": "spike_vol_v1", "threshold": 0.7}'

# Update DSI parameters
curl -X POST http://localhost:8080/config/dsi \
  -H "Content-Type: application/json" \
  -d '{"expert_weights": {"fsm": 0.3, "classifier": 0.3, "anomaly": 0.2, "divergence": 0.2}}'

# Update module communication parameters
curl -X POST http://localhost:8080/config/modules \
  -H "Content-Type: application/json" \
  -d '{"message_ttl": 300, "retry_attempts": 3}'
```

### Configuration Validation
```bash
# Validate configuration
curl -s http://localhost:8080/config/validate

# Check configuration history
curl -s http://localhost:8080/config/history

# Rollback configuration
curl -X POST http://localhost:8080/config/rollback \
  -H "Content-Type: application/json" \
  -d '{"version": "v1.2.3"}'
```

## Performance Tuning

### Latency Optimization
1. **WebSocket Optimization**: Connection pooling, message batching
2. **Database Optimization**: Query optimization, index tuning
3. **DSI Optimization**: Parallel processing, caching
4. **Module Communication**: Message batching, compression

### Throughput Optimization
1. **Parallel Processing**: Multi-threading, async processing
2. **Resource Scaling**: CPU, memory, network
3. **Algorithm Optimization**: Efficient algorithms, data structures
4. **Caching**: Result caching, feature caching

### Memory Optimization
1. **Data Structures**: Efficient data types, memory pools
2. **Garbage Collection**: Tuning GC parameters
3. **Memory Leaks**: Detection and prevention
4. **Resource Management**: Proper cleanup, resource limits

## Security Procedures

### Access Control
- **Authentication**: JWT tokens, multi-factor authentication
- **Authorization**: Role-based access control (RBAC)
- **Audit Logging**: All access and changes logged
- **Network Security**: TLS encryption, VPN access

### Data Protection
- **Encryption**: Data at rest and in transit
- **Key Management**: Secure key storage and rotation
- **Backup Security**: Encrypted backups, secure storage
- **Data Retention**: Automated data lifecycle management

### Incident Response
1. **Detection**: Automated monitoring and alerting
2. **Assessment**: Impact analysis and severity classification
3. **Containment**: Isolate affected systems
4. **Recovery**: Restore normal operations
5. **Post-Incident**: Root cause analysis and improvements

## Disaster Recovery

### Backup Procedures
- **Database Backups**: Daily full backups, hourly incremental
- **Configuration Backups**: Version-controlled configuration
- **Code Backups**: Git repositories, deployment artifacts
- **Data Backups**: Feature snapshots, trading plans

### Recovery Procedures
1. **Assessment**: Determine scope of failure
2. **Restoration**: Restore from backups
3. **Validation**: Verify system integrity
4. **Resumption**: Restart normal operations
5. **Monitoring**: Enhanced monitoring during recovery

### Business Continuity
- **Redundancy**: Multiple data centers, failover systems
- **Load Balancing**: Distribute load across systems
- **Graceful Degradation**: Maintain core functionality
- **Communication**: Stakeholder notification procedures

---

*This enhanced operational guide provides comprehensive procedures for operating the Trading Intelligence System with module-level intelligence and organic replication.*
