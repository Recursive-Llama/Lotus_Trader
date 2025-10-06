#!/usr/bin/env python3
"""
Test the new structured logging system
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from intelligence.trader_lowcap.structured_logger import structured_logger, CorrelationContext, StateDelta, PerformanceMetrics, BusinessLogic

def test_structured_logging():
    """Test the structured logging system"""
    
    # Test decision logging
    structured_logger.log_decision_approved(
        decision_id="test_decision_123",
        token="TEST",
        chain="solana",
        contract="TestContract123",
        allocation_pct=6.0,
        curator_score=0.85,
        constraints_passed=["min_volume", "max_exposure"],
        reasoning="Strong signal with good fundamentals"
    )
    
    # Test entry logging
    structured_logger.log_entry_attempted(
        position_id="TEST_solana_1234567890",
        entry_number=1,
        token="TEST",
        chain="solana",
        contract="TestContract123",
        amount_native=0.1,
        target_price=0.001,
        decision_id="test_decision_123"
    )
    
    # Test successful entry
    state_before = StateDelta(
        total_tokens_bought=0.0,
        total_quantity_before=0.0,
        total_investment_native=0.0,
        avg_entry_price=0.0,
        pnl_native=0.0,
        pnl_usd=0.0,
        pnl_pct=0.0
    )
    
    state_after = StateDelta(
        total_tokens_bought=100.0,
        total_quantity_after=100.0,
        total_investment_native=0.1,
        avg_entry_price=0.001,
        pnl_native=0.05,
        pnl_usd=5.0,
        pnl_pct=50.0
    )
    
    performance = PerformanceMetrics(
        duration_ms=2500,
        executor="sol_executor",
        venue="jupiter"
    )
    
    structured_logger.log_entry_success(
        position_id="TEST_solana_1234567890",
        entry_number=1,
        token="TEST",
        chain="solana",
        contract="TestContract123",
        tx_hash="TestTxHash123456789",
        amount_native=0.1,
        tokens_bought=100.0,
        actual_price=0.001,
        venue="jupiter",
        state_before=state_before,
        state_after=state_after,
        performance=performance
    )
    
    # Test buyback logging
    structured_logger.log_buyback_planned(
        position_id="TEST_solana_1234567890",
        chain="solana",
        exit_value_native=0.5,
        buyback_amount_native=0.075,
        percentage=15.0,
        min_amount=0.01,
        skipped=False,
        reason=None
    )
    
    structured_logger.log_buyback_executed(
        position_id="TEST_solana_1234567890",
        chain="solana",
        buyback_amount_native=0.075,
        lotus_tokens=1500.0,
        tx_hash="BuybackTxHash123456789",
        slippage_pct=2.5
    )
    
    # Test system health
    structured_logger.log_system_health(
        component="price_oracle",
        status="HEALTHY",
        details={"response_time_ms": 150, "success_rate": 0.99},
        latency_ms=150
    )
    
    print("✅ Structured logging test completed!")
    print("Check logs/trading_executions.log for JSON output")

if __name__ == "__main__":
    test_structured_logging()
