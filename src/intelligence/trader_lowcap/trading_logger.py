#!/usr/bin/env python3
"""
Dedicated Trading Logger

Provides comprehensive logging for all trading operations across all networks.
Logs go to dedicated files for easy analysis and debugging.
"""

import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any

class TradingLogger:
    """Dedicated logger for all trading operations"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        self._ensure_log_dir()
        self._setup_loggers()
    
    def _ensure_log_dir(self):
        """Ensure log directory exists"""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
    
    def _setup_loggers(self):
        """Setup dedicated loggers for different trading aspects"""
        
        # Main trading logger
        self.trader = self._create_logger(
            'trader',
            'trading_executions.log',
            'Trading Executions - All trade attempts, successes, and failures'
        )
        
        # Decision making logger
        self.decisions = self._create_logger(
            'decisions',
            'trading_decisions.log',
            'Decision Making - All decision approvals, rejections, and reasoning'
        )
        
        # Network-specific loggers
        self.solana = self._create_logger(
            'solana',
            'trading_solana.log',
            'Solana Trading - All Solana-specific operations'
        )
        
        self.ethereum = self._create_logger(
            'ethereum',
            'trading_ethereum.log',
            'Ethereum Trading - All Ethereum-specific operations'
        )
        
        self.base = self._create_logger(
            'base',
            'trading_base.log',
            'Base Trading - All Base-specific operations'
        )
        
        self.bsc = self._create_logger(
            'bsc',
            'trading_bsc.log',
            'BSC Trading - All BSC-specific operations'
        )
        
        # Price and balance logger
        self.prices = self._create_logger(
            'prices',
            'trading_prices.log',
            'Price & Balance - All price retrievals and balance checks'
        )
        
        # Position management logger
        self.positions = self._create_logger(
            'positions',
            'trading_positions.log',
            'Position Management - All position creation, updates, and management'
        )
        
        # Error logger
        self.errors = self._create_logger(
            'errors',
            'trading_errors.log',
            'Trading Errors - All trading-related errors and exceptions'
        )
    
    def _create_logger(self, name: str, filename: str, description: str) -> logging.Logger:
        """Create a dedicated logger with file output"""
        logger = logging.getLogger(f'trading.{name}')
        logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers to avoid duplicates
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Create file handler
        file_handler = logging.FileHandler(
            os.path.join(self.log_dir, filename),
            mode='a'
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(file_handler)
        
        # Prevent propagation to root logger
        logger.propagate = False
        
        return logger
    
    # Convenience methods for common logging patterns
    
    def log_trade_attempt(self, chain: str, token: str, action: str, details: Dict[str, Any]):
        """Log a trade attempt"""
        self.trader.info(f"TRADE_ATTEMPT | {chain.upper()} | {token} | {action} | {details}")
    
    def log_trade_success(self, chain: str, token: str, tx_hash: str, details: Dict[str, Any]):
        """Log a successful trade"""
        self.trader.info(f"TRADE_SUCCESS | {chain.upper()} | {token} | {tx_hash} | {details}")
    
    def log_trade_failure(self, chain: str, token: str, reason: str, details: Dict[str, Any]):
        """Log a failed trade"""
        self.trader.error(f"TRADE_FAILURE | {chain.upper()} | {token} | {reason} | {details}")
    
    def log_decision_approval(self, token: str, allocation: float, curator: str, reasoning: str):
        """Log a decision approval"""
        self.decisions.info(f"DECISION_APPROVED | {token} | {allocation}% | {curator} | {reasoning}")
    
    def log_decision_rejection(self, token: str, reason: str, details: Dict[str, Any]):
        """Log a decision rejection"""
        self.decisions.warning(f"DECISION_REJECTED | {token} | {reason} | {details}")
    
    def log_price_retrieval(self, chain: str, token: str, price: Optional[float], source: str):
        """Log price retrieval attempt"""
        if price:
            self.prices.info(f"PRICE_SUCCESS | {chain.upper()} | {token} | {price} | {source}")
        else:
            self.prices.warning(f"PRICE_FAILED | {chain.upper()} | {token} | {source}")
    
    def log_balance_check(self, chain: str, balance: Optional[float], required: Optional[float] = None):
        """Log balance check"""
        if balance is not None:
            status = "SUFFICIENT" if required is None or balance >= required else "INSUFFICIENT"
            self.prices.info(f"BALANCE_CHECK | {chain.upper()} | {balance} | {status}")
        else:
            self.prices.error(f"BALANCE_ERROR | {chain.upper()} | Failed to retrieve balance")
    
    def log_position_creation(self, position_id: str, token: str, chain: str, allocation: float):
        """Log position creation"""
        self.positions.info(f"POSITION_CREATED | {position_id} | {token} | {chain.upper()} | {allocation}%")
    
    def log_position_update(self, position_id: str, field: str, old_value: Any, new_value: Any):
        """Log position update"""
        self.positions.info(f"POSITION_UPDATED | {position_id} | {field} | {old_value} -> {new_value}")
    
    def log_executor_status(self, chain: str, executor: Optional[Any], details: str = ""):
        """Log executor status"""
        if executor:
            self.trader.info(f"EXECUTOR_READY | {chain.upper()} | {details}")
        else:
            self.trader.error(f"EXECUTOR_MISSING | {chain.upper()} | {details}")
    
    def log_initialization(self, component: str, status: str, details: str = ""):
        """Log component initialization"""
        if status == "SUCCESS":
            self.trader.info(f"INIT_SUCCESS | {component} | {details}")
        else:
            self.trader.error(f"INIT_FAILED | {component} | {details}")
    
    # Trend trading specific logging
    def log_trend_entry(self, position_id: str, token: str, chain: str, amount: float, price: float, dip_pct: float, batch_id: str):
        """Log trend entry execution"""
        self.trader.info(f"TREND_ENTRY | {position_id} | {token} | {chain.upper()} | {amount} | {price} | {dip_pct}% | {batch_id}")
    
    def log_trend_exit(self, position_id: str, token: str, chain: str, tokens_sold: float, price: float, gain_pct: float, batch_id: str):
        """Log trend exit execution"""
        self.trader.info(f"TREND_EXIT | {position_id} | {token} | {chain.upper()} | {tokens_sold} | {price} | {gain_pct}% | {batch_id}")
    
    def log_trend_batch_creation(self, batch_id: str, source_exit: str, amount: float, chain: str):
        """Log trend batch creation"""
        self.trader.info(f"TREND_BATCH_CREATED | {batch_id} | {source_exit} | {amount} | {chain.upper()}")
    
    # Entry/Exit specific logging
    def log_entry_execution(self, position_id: str, entry_number: int, token: str, chain: str, amount: float, price: float, tx_hash: str):
        """Log entry execution"""
        self.trader.info(f"ENTRY_EXECUTED | {position_id} | {entry_number} | {token} | {chain.upper()} | {amount} | {price} | {tx_hash}")
    
    def log_exit_execution(self, position_id: str, exit_number: int, token: str, chain: str, tokens_sold: float, price: float, tx_hash: str):
        """Log exit execution"""
        self.trader.info(f"EXIT_EXECUTED | {position_id} | {exit_number} | {token} | {chain.upper()} | {tokens_sold} | {price} | {tx_hash}")
    
    def log_entry_failure(self, position_id: str, entry_number: int, token: str, chain: str, reason: str, details: str = ""):
        """Log entry execution failure"""
        self.trader.error(f"ENTRY_FAILED | {position_id} | {entry_number} | {token} | {chain.upper()} | {reason} | {details}")
    
    def log_exit_failure(self, position_id: str, exit_number: int, token: str, chain: str, reason: str, details: str = ""):
        """Log exit execution failure"""
        self.trader.error(f"EXIT_FAILED | {position_id} | {exit_number} | {token} | {chain.upper()} | {reason} | {details}")
    
    # Chain-specific detailed logging
    def log_chain_operation(self, chain: str, operation: str, token: str, details: Dict[str, Any]):
        """Log chain-specific operations"""
        chain_logger = getattr(self, chain.lower(), self.trader)
        chain_logger.info(f"{operation.upper()} | {token} | {details}")
    
    def log_venue_resolution(self, chain: str, token: str, venue: Optional[Dict[str, Any]]):
        """Log venue resolution for trading"""
        if venue:
            self.trader.info(f"VENUE_RESOLVED | {chain.upper()} | {token} | {venue.get('dex', 'unknown')} | {venue.get('address', 'unknown')}")
        else:
            self.trader.warning(f"VENUE_NOT_FOUND | {chain.upper()} | {token}")
    
    def log_slippage_detection(self, chain: str, token: str, expected: float, actual: float, slippage_pct: float):
        """Log slippage detection"""
        self.trader.info(f"SLIPPAGE_DETECTED | {chain.upper()} | {token} | {expected} -> {actual} | {slippage_pct}%")
    
    def log_gas_estimation(self, chain: str, operation: str, gas_limit: int, gas_price: float, total_cost: float):
        """Log gas estimation"""
        self.trader.info(f"GAS_ESTIMATED | {chain.upper()} | {operation} | {gas_limit} | {gas_price} | {total_cost}")

# Global instance
trading_logger = TradingLogger()
