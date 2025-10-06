#!/usr/bin/env python3
"""
Structured Trading Logger - LLM Optimized

Provides JSON-structured logging for all trading operations with correlation IDs,
business logic visibility, and LLM-searchable format.
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict

@dataclass
class CorrelationContext:
    """Correlation context for tracking related operations"""
    position_id: Optional[str] = None
    decision_id: Optional[str] = None
    chain: Optional[str] = None
    contract: Optional[str] = None
    token: Optional[str] = None
    action_type: Optional[str] = None  # decision, entry, exit, trend, buyback
    entry_number: Optional[int] = None
    exit_number: Optional[int] = None
    batch_id: Optional[str] = None

@dataclass
class PerformanceMetrics:
    """Performance metrics for operations"""
    duration_ms: Optional[int] = None
    retries: int = 0
    executor: Optional[str] = None
    venue: Optional[str] = None
    route_version: Optional[str] = None  # v2, v3, etc.

@dataclass
class StateDelta:
    """State changes from operations"""
    total_tokens_bought: Optional[float] = None
    total_tokens_sold: Optional[float] = None
    total_quantity_before: Optional[float] = None
    total_quantity_after: Optional[float] = None
    total_investment_native: Optional[float] = None
    total_extracted_native: Optional[float] = None
    avg_entry_price: Optional[float] = None
    avg_exit_price: Optional[float] = None
    pnl_native: Optional[float] = None
    pnl_usd: Optional[float] = None
    pnl_pct: Optional[float] = None

@dataclass
class BusinessLogic:
    """Business logic and reasoning"""
    curator_score: Optional[float] = None
    allocation_pct: Optional[float] = None
    constraints_passed: Optional[List[str]] = None
    constraints_failed: Optional[List[str]] = None
    price_quality: Optional[str] = None  # good, stale, missing
    venue_available: Optional[bool] = None
    reasoning: Optional[str] = None

class StructuredTradingLogger:
    """Structured logger optimized for LLM search and analysis"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        self._ensure_log_dir()
        self._setup_logger()
        self._retry_cache = {}  # For deduplication
        self._last_summary = 0
    
    def _ensure_log_dir(self):
        """Ensure log directory exists"""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
    
    def _setup_logger(self):
        """Setup the main structured logger"""
        self.logger = logging.getLogger('structured_trading')
        self.logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Create file handler for main log
        file_handler = logging.FileHandler(
            os.path.join(self.log_dir, 'trading_executions.log'),
            mode='a'
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Create JSON formatter
        formatter = logging.Formatter('%(message)s')
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.propagate = False
    
    def _create_log_entry(self, 
                         event: str,
                         level: str,
                         correlation: CorrelationContext,
                         action: Optional[Dict[str, Any]] = None,
                         state: Optional[StateDelta] = None,
                         performance: Optional[PerformanceMetrics] = None,
                         business: Optional[BusinessLogic] = None,
                         error: Optional[Dict[str, Any]] = None,
                         **kwargs) -> Dict[str, Any]:
        """Create a structured log entry"""
        
        log_entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "event": event,
            "correlation": asdict(correlation) if correlation else {},
            "action": action or {},
            "state": asdict(state) if state else {},
            "performance": asdict(performance) if performance else {},
            "business": asdict(business) if business else {},
            "error": error or {},
            **kwargs
        }
        
        # Remove None values
        return {k: v for k, v in log_entry.items() if v is not None}
    
    def _log_structured(self, log_entry: Dict[str, Any]):
        """Log structured entry"""
        self.logger.info(json.dumps(log_entry, default=str))
    
    def _should_deduplicate(self, key: str, max_age_seconds: int = 300) -> bool:
        """Check if we should deduplicate this error"""
        now = time.time()
        if key in self._retry_cache:
            last_time = self._retry_cache[key]
            if now - last_time < max_age_seconds:
                return True
        self._retry_cache[key] = now
        return False
    
    # =====================
    # DECISION LOGGING
    # =====================
    
    def log_decision_approved(self, 
                             decision_id: str,
                             token: str,
                             chain: str,
                             contract: str,
                             allocation_pct: float,
                             curator_score: float,
                             constraints_passed: List[str],
                             reasoning: str):
        """Log decision approval with full context"""
        correlation = CorrelationContext(
            decision_id=decision_id,
            chain=chain,
            contract=contract,
            token=token,
            action_type="decision"
        )
        
        business = BusinessLogic(
            curator_score=curator_score,
            allocation_pct=allocation_pct,
            constraints_passed=constraints_passed,
            reasoning=reasoning
        )
        
        log_entry = self._create_log_entry(
            event="DECISION_APPROVED",
            level="INFO",
            correlation=correlation,
            business=business
        )
        
        self._log_structured(log_entry)
    
    def log_decision_rejected(self,
                             decision_id: str,
                             token: str,
                             chain: str,
                             contract: str,
                             reason: str,
                             constraints_failed: List[str],
                             details: Dict[str, Any]):
        """Log decision rejection with context"""
        correlation = CorrelationContext(
            decision_id=decision_id,
            chain=chain,
            contract=contract,
            token=token,
            action_type="decision"
        )
        
        business = BusinessLogic(
            constraints_failed=constraints_failed,
            reasoning=reason
        )
        
        log_entry = self._create_log_entry(
            event="DECISION_REJECTED",
            level="WARNING",
            correlation=correlation,
            business=business,
            rejection_details=details
        )
        
        self._log_structured(log_entry)
    
    # =====================
    # ENTRY LOGGING
    # =====================
    
    def log_entry_attempted(self,
                           position_id: str,
                           entry_number: int,
                           token: str,
                           chain: str,
                           contract: str,
                           amount_native: float,
                           target_price: float,
                           decision_id: str):
        """Log entry attempt with full context"""
        correlation = CorrelationContext(
            position_id=position_id,
            decision_id=decision_id,
            chain=chain,
            contract=contract,
            token=token,
            action_type="entry",
            entry_number=entry_number
        )
        
        action = {
            "type": "entry",
            "number": entry_number,
            "amount_native": amount_native,
            "target_price": target_price,
            "venue": None  # Will be filled by executor
        }
        
        log_entry = self._create_log_entry(
            event="ENTRY_ATTEMPTED",
            level="INFO",
            correlation=correlation,
            action=action
        )
        
        self._log_structured(log_entry)
    
    def log_entry_success(self,
                         position_id: str,
                         entry_number: int,
                         token: str,
                         chain: str,
                         contract: str,
                         tx_hash: str,
                         amount_native: float,
                         tokens_bought: float,
                         actual_price: float,
                         venue: str,
                         state_before: StateDelta,
                         state_after: StateDelta,
                         performance: PerformanceMetrics):
        """Log successful entry with state deltas"""
        correlation = CorrelationContext(
            position_id=position_id,
            chain=chain,
            contract=contract,
            token=token,
            action_type="entry",
            entry_number=entry_number
        )
        
        action = {
            "type": "entry",
            "number": entry_number,
            "tx_hash": tx_hash,
            "amount_native": amount_native,
            "tokens_bought": tokens_bought,
            "actual_price": actual_price,
            "venue": venue
        }
        
        # Calculate state changes
        state_delta = StateDelta(
            total_tokens_bought=state_after.total_tokens_bought,
            total_quantity_after=state_after.total_quantity_after,
            total_investment_native=state_after.total_investment_native,
            avg_entry_price=state_after.avg_entry_price,
            pnl_native=state_after.pnl_native,
            pnl_usd=state_after.pnl_usd,
            pnl_pct=state_after.pnl_pct
        )
        
        log_entry = self._create_log_entry(
            event="ENTRY_SUCCESS",
            level="INFO",
            correlation=correlation,
            action=action,
            state=state_delta,
            performance=performance
        )
        
        self._log_structured(log_entry)
    
    def log_entry_failed(self,
                        position_id: str,
                        entry_number: int,
                        token: str,
                        chain: str,
                        contract: str,
                        reason: str,
                        error_details: Dict[str, Any],
                        retry_count: int = 0):
        """Log entry failure with deduplication"""
        correlation = CorrelationContext(
            position_id=position_id,
            chain=chain,
            contract=contract,
            token=token,
            action_type="entry",
            entry_number=entry_number
        )
        
        # Create deduplication key
        dedup_key = f"{position_id}:entry:{entry_number}:{reason}"
        
        if self._should_deduplicate(dedup_key):
            # Log as aggregated failure
            log_entry = self._create_log_entry(
                event="ENTRY_FAILED_AGGREGATED",
                level="ERROR",
                correlation=correlation,
                error={
                    "reason": reason,
                    "retry_count": retry_count,
                    "deduplicated": True
                }
            )
        else:
            # Log as new failure
            log_entry = self._create_log_entry(
                event="ENTRY_FAILED",
                level="ERROR",
                correlation=correlation,
                error={
                    "reason": reason,
                    "details": error_details,
                    "retry_count": retry_count
                }
            )
        
        self._log_structured(log_entry)
    
    # =====================
    # EXIT LOGGING
    # =====================
    
    def log_exit_attempted(self,
                          position_id: str,
                          exit_number: int,
                          token: str,
                          chain: str,
                          contract: str,
                          tokens_to_sell: float,
                          target_price: float):
        """Log exit attempt with context"""
        correlation = CorrelationContext(
            position_id=position_id,
            chain=chain,
            contract=contract,
            token=token,
            action_type="exit",
            exit_number=exit_number
        )
        
        action = {
            "type": "exit",
            "number": exit_number,
            "tokens_to_sell": tokens_to_sell,
            "target_price": target_price,
            "venue": None  # Will be filled by executor
        }
        
        log_entry = self._create_log_entry(
            event="EXIT_ATTEMPTED",
            level="INFO",
            correlation=correlation,
            action=action
        )
        
        self._log_structured(log_entry)
    
    def log_exit_success(self,
                        position_id: str,
                        exit_number: int,
                        token: str,
                        chain: str,
                        contract: str,
                        tx_hash: str,
                        tokens_sold: float,
                        native_amount: float,
                        actual_price: float,
                        venue: str,
                        state_before: StateDelta,
                        state_after: StateDelta,
                        performance: PerformanceMetrics):
        """Log successful exit with state deltas"""
        correlation = CorrelationContext(
            position_id=position_id,
            chain=chain,
            contract=contract,
            token=token,
            action_type="exit",
            exit_number=exit_number
        )
        
        action = {
            "type": "exit",
            "number": exit_number,
            "tx_hash": tx_hash,
            "tokens_sold": tokens_sold,
            "native_amount": native_amount,
            "actual_price": actual_price,
            "venue": venue
        }
        
        # Calculate state changes
        state_delta = StateDelta(
            total_tokens_sold=state_after.total_tokens_sold,
            total_quantity_after=state_after.total_quantity_after,
            total_extracted_native=state_after.total_extracted_native,
            avg_exit_price=state_after.avg_exit_price,
            pnl_native=state_after.pnl_native,
            pnl_usd=state_after.pnl_usd,
            pnl_pct=state_after.pnl_pct
        )
        
        log_entry = self._create_log_entry(
            event="EXIT_SUCCESS",
            level="INFO",
            correlation=correlation,
            action=action,
            state=state_delta,
            performance=performance
        )
        
        self._log_structured(log_entry)
    
    def log_exit_failed(self,
                       position_id: str,
                       exit_number: int,
                       token: str,
                       chain: str,
                       contract: str,
                       reason: str,
                       error_details: Dict[str, Any],
                       retry_count: int = 0):
        """Log exit failure with deduplication"""
        correlation = CorrelationContext(
            position_id=position_id,
            chain=chain,
            contract=contract,
            token=token,
            action_type="exit",
            exit_number=exit_number
        )
        
        # Create deduplication key
        dedup_key = f"{position_id}:exit:{exit_number}:{reason}"
        
        if self._should_deduplicate(dedup_key):
            # Log as aggregated failure
            log_entry = self._create_log_entry(
                event="EXIT_FAILED_AGGREGATED",
                level="ERROR",
                correlation=correlation,
                error={
                    "reason": reason,
                    "retry_count": retry_count,
                    "deduplicated": True
                }
            )
        else:
            # Log as new failure
            log_entry = self._create_log_entry(
                event="EXIT_FAILED",
                level="ERROR",
                correlation=correlation,
                error={
                    "reason": reason,
                    "details": error_details,
                    "retry_count": retry_count
                }
            )
        
        self._log_structured(log_entry)
    
    # =====================
    # TREND LOGGING
    # =====================
    
    def log_trend_batch_created(self,
                               position_id: str,
                               batch_id: str,
                               source_exit_number: int,
                               funded_amount: float,
                               chain: str,
                               token: str):
        """Log trend batch creation"""
        correlation = CorrelationContext(
            position_id=position_id,
            batch_id=batch_id,
            chain=chain,
            token=token,
            action_type="trend"
        )
        
        action = {
            "type": "trend_batch",
            "batch_id": batch_id,
            "source_exit_number": source_exit_number,
            "funded_amount": funded_amount
        }
        
        log_entry = self._create_log_entry(
            event="TREND_BATCH_CREATED",
            level="INFO",
            correlation=correlation,
            action=action
        )
        
        self._log_structured(log_entry)
    
    def log_trend_entry_executed(self,
                                position_id: str,
                                batch_id: str,
                                entry_number: int,
                                token: str,
                                chain: str,
                                amount_native: float,
                                tokens_bought: float,
                                price: float,
                                dip_pct: float,
                                tx_hash: str):
        """Log trend entry execution"""
        correlation = CorrelationContext(
            position_id=position_id,
            batch_id=batch_id,
            chain=chain,
            token=token,
            action_type="trend",
            entry_number=entry_number
        )
        
        action = {
            "type": "trend_entry",
            "batch_id": batch_id,
            "entry_number": entry_number,
            "amount_native": amount_native,
            "tokens_bought": tokens_bought,
            "price": price,
            "dip_pct": dip_pct,
            "tx_hash": tx_hash
        }
        
        log_entry = self._create_log_entry(
            event="TREND_ENTRY_EXECUTED",
            level="INFO",
            correlation=correlation,
            action=action
        )
        
        self._log_structured(log_entry)
    
    # =====================
    # BUYBACK LOGGING
    # =====================
    
    def log_buyback_planned(self,
                           position_id: str,
                           chain: str,
                           exit_value_native: float,
                           buyback_amount_native: float,
                           percentage: float,
                           min_amount: float,
                           skipped: bool,
                           reason: Optional[str] = None):
        """Log buyback planning"""
        correlation = CorrelationContext(
            position_id=position_id,
            chain=chain,
            action_type="buyback"
        )
        
        action = {
            "type": "buyback_plan",
            "exit_value_native": exit_value_native,
            "buyback_amount_native": buyback_amount_native,
            "percentage": percentage,
            "min_amount": min_amount,
            "skipped": skipped,
            "reason": reason
        }
        
        log_entry = self._create_log_entry(
            event="BUYBACK_PLANNED",
            level="INFO",
            correlation=correlation,
            action=action
        )
        
        self._log_structured(log_entry)
    
    def log_buyback_executed(self,
                            position_id: str,
                            chain: str,
                            buyback_amount_native: float,
                            lotus_tokens: float,
                            tx_hash: str,
                            slippage_pct: float):
        """Log buyback execution"""
        correlation = CorrelationContext(
            position_id=position_id,
            chain=chain,
            action_type="buyback"
        )
        
        action = {
            "type": "buyback_execute",
            "buyback_amount_native": buyback_amount_native,
            "lotus_tokens": lotus_tokens,
            "tx_hash": tx_hash,
            "slippage_pct": slippage_pct
        }
        
        log_entry = self._create_log_entry(
            event="BUYBACK_EXECUTED",
            level="INFO",
            correlation=correlation,
            action=action
        )
        
        self._log_structured(log_entry)
    
    # =====================
    # SYSTEM LOGGING
    # =====================
    
    def log_system_health(self,
                         component: str,
                         status: str,
                         details: Dict[str, Any],
                         latency_ms: Optional[int] = None):
        """Log system health status"""
        log_entry = self._create_log_entry(
            event="SYSTEM_HEALTH",
            level="INFO" if status == "HEALTHY" else "WARNING",
            correlation=CorrelationContext(action_type="system"),
            action={
                "component": component,
                "status": status,
                "details": details
            },
            performance=PerformanceMetrics(duration_ms=latency_ms)
        )
        
        self._log_structured(log_entry)
    
    def log_performance_summary(self):
        """Log periodic performance summary"""
        now = time.time()
        if now - self._last_summary < 60:  # Every minute
            return
        
        self._last_summary = now
        
        # This would be implemented with actual metrics collection
        log_entry = self._create_log_entry(
            event="PERFORMANCE_SUMMARY",
            level="INFO",
            correlation=CorrelationContext(action_type="system"),
            action={
                "summary_type": "periodic",
                "timestamp": now
            }
        )
        
        self._log_structured(log_entry)

# Global instance
structured_logger = StructuredTradingLogger()
