"""
Trader Lowcap V2 - modularized for safer BSC path

Implements BSC price+execution using PriceOracle and BscExecutor, and isolates
DB writes for entries/exits to avoid brittle cross-dependencies.
"""

import os
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from intelligence.trader_lowcap.price_oracle import PriceOracle
from intelligence.trader_lowcap.evm_executors import BscExecutor, BaseExecutor, EthExecutor
from intelligence.trader_lowcap.position_repository import PositionRepository
from intelligence.trader_lowcap.entry_exit_planner import EntryExitPlanner
from trading.wallet_manager import WalletManager
from trading.jupiter_client import JupiterClient
from trading.js_solana_client import JSSolanaClient
from intelligence.trader_lowcap.solana_executor import SolanaExecutor
from intelligence.trader_lowcap.trader_service import TraderService
from intelligence.trader_lowcap.trader_domain import (
    compute_position_value_native,
    compute_total_pnl_native,
    convert_native_to_usd,
    compute_total_pnl_pct,
)
from intelligence.trader_lowcap.trading_logger import trading_logger
from communication.telegram_signal_notifier import TelegramSignalNotifier

logger = logging.getLogger(__name__)


class TraderLowcapSimpleV2:
    def __init__(self, supabase_manager, config: Optional[Dict[str, Any]] = None):
        self.supabase_manager = supabase_manager
        self.logger = logging.getLogger(__name__)
        self.config = config or {}

        # Wallet + clients
        wallet_config = {
            'ethereum_rpc': os.getenv('ETH_RPC_URL'),
            'base_rpc': os.getenv('BASE_RPC_URL') or os.getenv('RPC_URL'),
            'bsc_rpc': os.getenv('BSC_RPC_URL')
        }
        self.wallet_manager = WalletManager(wallet_config)
        # Set trader reference for SPL token balance checking
        self.wallet_manager.trader = self

        # Initialize BSC client if possible
        try:
            from trading.evm_uniswap_client import EvmUniswapClient
            bsc_pk = (
                os.getenv('BSC_WALLET_PRIVATE_KEY')
                or os.getenv('ETHEREUM_WALLET_PRIVATE_KEY')
                or os.getenv('ETH_WALLET_PRIVATE_KEY')
            )
            bsc_rpc = os.getenv('BSC_RPC_URL', 'https://bsc-dataseed.binance.org')
            self.bsc_client = EvmUniswapClient(chain='bsc', rpc_url=bsc_rpc, private_key=bsc_pk) if bsc_pk else None
            evm_pk = (
                os.getenv('ETHEREUM_WALLET_PRIVATE_KEY')
                or os.getenv('ETH_WALLET_PRIVATE_KEY')
            )
            base_rpc = os.getenv('BASE_RPC_URL', 'https://mainnet.base.org')
            eth_rpc = os.getenv('ETH_RPC_URL', 'https://eth.llamarpc.com')
            self.base_client = EvmUniswapClient(chain='base', rpc_url=base_rpc, private_key=evm_pk) if evm_pk else None
            from trading.evm_uniswap_client_eth import EthUniswapClient as EthClient
            self.eth_client = EthClient(rpc_url=eth_rpc, private_key=evm_pk) if evm_pk else None
        except Exception as e:
            self.logger.warning(f"BSC client unavailable: {e}")
            self.bsc_client = None
            self.base_client = None
            self.eth_client = None

        # Solana
        helius_key = os.getenv('HELIUS_API_KEY')
        rpc_url = f"https://rpc.helius.xyz/?api-key={helius_key}" if helius_key else "https://api.mainnet-beta.solana.com"
        self.jupiter_client = JupiterClient(helius_key) if helius_key else JupiterClient()
        sol_private_key = os.getenv('SOL_WALLET_PRIVATE_KEY')
        self.js_solana_client = JSSolanaClient(rpc_url, sol_private_key) if sol_private_key else None

        self.price_oracle = PriceOracle(bsc_client=self.bsc_client, base_client=self.base_client, eth_client=self.eth_client)
        self.repo = PositionRepository(self.supabase_manager)
        self.bsc_executor = BscExecutor(self.bsc_client, self.repo) if self.bsc_client else None
        self.base_executor = BaseExecutor(self.base_client, self.repo) if self.base_client else None
        self.eth_executor = EthExecutor(self.eth_client, self.repo) if self.eth_client else None
        self.sol_executor = SolanaExecutor(self.js_solana_client) if self.js_solana_client else None
        
        # Log executor status
        trading_logger.log_executor_status('solana', self.sol_executor, f"js_client={self.js_solana_client is not None}")
        trading_logger.log_executor_status('ethereum', self.eth_executor, f"eth_client={self.eth_client is not None}")
        trading_logger.log_executor_status('base', self.base_executor, f"base_client={self.base_client is not None}")
        trading_logger.log_executor_status('bsc', self.bsc_executor, f"bsc_client={self.bsc_client is not None}")
        
        # Initialize TraderService (ports/use-cases facade) with current collaborators.
        # No behavior change: service is available for gradual delegation.
        try:
            self._service = TraderService(
                repo=self.repo,
                price_oracle=self.price_oracle,
                wallet=self.wallet_manager,
                base_executor=self.base_executor,
                bsc_executor=self.bsc_executor,
                eth_executor=self.eth_executor,
                sol_executor=self.sol_executor,
                js_solana_client=self.js_solana_client,
            )
            trading_logger.log_initialization(
                component="TraderService",
                status="SUCCESS",
                details=f"sol_executor={self.sol_executor is not None}, js_client={self.js_solana_client is not None}"
            )
        except Exception as e:
            trading_logger.log_initialization(
                component="TraderService",
                status="FAILED",
                details=str(e)
            )
            self.logger.warning(f"TraderService initialization skipped: {e}")
            self._service = None

        # Initialize Telegram signal notifier
        self.telegram_notifier = self._init_telegram_notifier()

    def _init_telegram_notifier(self) -> Optional[TelegramSignalNotifier]:
        """Initialize Telegram signal notifier if configured"""
        try:
            bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
            channel_id = os.getenv('TELEGRAM_CHANNEL_ID')
            
            if not bot_token or not channel_id:
                self.logger.info("Telegram signal notifications not configured (missing bot token or channel ID)")
                return None
            
            # Use existing API credentials from the system
            api_id = 21826741
            api_hash = "4643cce207a1a9d56d56a5389a4f1f52"
            session_file = "src/config/telegram_session.txt"
            
            notifier = TelegramSignalNotifier(
                bot_token=bot_token,
                channel_id=channel_id,
                api_id=api_id,
                api_hash=api_hash,
                session_file=session_file
            )
            
            self.logger.info(f"Telegram signal notifier initialized for channel: {channel_id}")
            # Attach notifier to service if available
            try:
                if self._service:
                    self._service.set_notifier(notifier)
            except Exception:
                pass
            return notifier
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Telegram signal notifier: {e}")
            return None

    async def execute_decision(self, decision: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            if decision.get('content', {}).get('action') != 'approve':
                return None
            if self._service:
                return await self._service.execute_decision(decision)
            self.logger.error("Trader service unavailable; cannot execute decision")
            return None
        except Exception as e:
            self.logger.error(f"Trader V2: execute_decision error: {e}")
            return None


    async def _execute_exit(self, position_id: str, exit_number: int) -> bool:
        """
        Execute a specific exit for a position with wallet reconciliation
        
        Args:
            position_id: Position ID
            exit_number: Exit number to execute (1, 2, 3, etc.)
            
        Returns:
            bool: True if exit executed successfully, False otherwise
        """
        try:
            # Get position from database
            position = self._service.repo.get_position(position_id) if self._service else None
            if not position:
                self.logger.error(f"Position {position_id} not found")
                return False
            
            if position.get('status') != 'active':
                self.logger.error(f"Position {position_id} is not active")
                return False
            
            # Find the specific exit
            exits = position.get('exits', [])
            target_exit = None
            for exit_data in exits:
                if exit_data.get('exit_number') == exit_number and exit_data.get('status') == 'pending':
                    target_exit = exit_data
                    break
            
            if not target_exit:
                self.logger.error(f"Exit {exit_number} not found or not pending for position {position_id}")
                return False
            
            # Get position details
            chain = position.get('token_chain')
            contract = position.get('token_contract')
            ticker = position.get('token_ticker')
            target_price = target_exit.get('price', 0)
            
            # Calculate tokens to sell from exit_pct and total_quantity
            exit_pct = target_exit.get('exit_pct', 0)
            total_quantity = float(position.get('total_quantity', 0) or 0)
            requested_tokens = total_quantity * (exit_pct / 100)
            
            if requested_tokens <= 0:
                self.logger.error(f"Invalid token quantity for exit: {requested_tokens} (exit_pct: {exit_pct}%, total_quantity: {total_quantity})")
                return False
            
            # Step 1: Check actual wallet balance and reconcile
            self.logger.info(f"Checking wallet balance for {ticker}...")
            try:
                wallet_balance = await self.wallet_manager.get_balance(chain, contract)
                wallet_balance_float = float(wallet_balance) if wallet_balance else 0
                if abs(wallet_balance_float - float(position.get('total_quantity', 0) or 0)) > 0.000001:
                    position['total_quantity'] = wallet_balance_float
                    await self._recalculate_position_totals(position)
                    self.repo.update_position(position_id, position)
            except Exception:
                wallet_balance_float = float(position.get('total_quantity', 0) or 0)
            
            # Step 2: Calculate actual sell amount (min of requested vs available)
            actual_sell_amount = min(requested_tokens, wallet_balance_float)
            if actual_sell_amount <= 0:
                self.logger.error(f"No tokens available to sell (requested: {requested_tokens}, available: {wallet_balance_float})")
                return False
            
            if actual_sell_amount < requested_tokens:
                self.logger.warning(f"Adjusting sell amount: {requested_tokens} -> {actual_sell_amount} (limited by wallet balance)")
            
            self.logger.info(f"Executing exit {exit_number} for {ticker}: {actual_sell_amount} tokens at {target_price} ETH")
            
            # Execute sell based on chain
            tx_hash = None
            if chain in ('base','bsc','ethereum') and self._service:
                tx_hash = self._service.execute_exit(
                    position_id=position_id,
                    chain=chain,
                    contract=contract,
                    token_ticker=ticker,
                    exit_number=exit_number,
                    tokens_to_sell=actual_sell_amount,
                    target_price_native=target_price,
                )
                
                # Execute USDC conversion for Base/BSC exits after successful execution
                if tx_hash and chain.lower() in ['base', 'bsc']:
                    try:
                        usdc_cfg = (self.config or {}).get('usdc_conversion', {})
                        if usdc_cfg.get('enabled', False):
                            # Calculate 10% of native amount received
                            conversion_amount = exit_value_native * (float(usdc_cfg.get('percentage', 10.0)) / 100.0)
                            # Chain-specific minimums from config
                            min_amounts = usdc_cfg.get('min_amount_native', {})
                            min_amount = min_amounts.get(chain.lower(), 0.001)  # Default fallback
                            
                            if conversion_amount >= min_amount:
                                self.logger.info(f"Executing USDC conversion: {conversion_amount:.6f} {chain.upper()} from {exit_value_native:.6f} {chain.upper()} exit")
                                usdc_result = await self._convert_to_usdc_after_exit(
                                    chain=chain,
                                    native_amount=conversion_amount,
                                    slippage_pct=float(usdc_cfg.get('slippage_pct', 2.0))
                                )
                                if usdc_result.get('success'):
                                    self.logger.info(f"USDC conversion successful: {usdc_result.get('usdc_received', 0):.2f} USDC received")
                                else:
                                    self.logger.error(f"USDC conversion failed: {usdc_result.get('error', 'Unknown error')}")
                            else:
                                self.logger.info(f"USDC conversion skipped: {conversion_amount:.6f} {chain.upper()} below minimum {min_amount:.6f}")
                    except Exception as e:
                        self.logger.error(f"Error in USDC conversion: {e}")
            elif chain == 'solana' and self.sol_executor:
                sell_result = await self.sol_executor.execute_sell(contract, actual_sell_amount, target_price)
                if sell_result:
                    tx_hash = sell_result.get('tx_hash')
                    actual_sol_received = sell_result.get('actual_sol_received', 0)
                else:
                    tx_hash = None
                    actual_sol_received = 0
            else:
                self.logger.error(f"No executor available for chain {chain}")
                return False
            
            if tx_hash:
                # Wait for transaction confirmation before marking as executed
                if chain in ['bsc', 'base', 'ethereum'] and self._service:
                    confirmed = await self._service.wait_for_transaction_confirmation(tx_hash, chain)
                    if not confirmed:
                        self.logger.error(f"Exit {exit_number} transaction not confirmed: {tx_hash}")
                        return False
                
                # Calculate exit value for cost tracking - use actual SOL received from transaction
                if chain == 'solana' and 'actual_sol_received' in locals():
                    theoretical_value = actual_sell_amount * target_price
                    exit_value_native = actual_sol_received  # Use actual SOL received from Jupiter
                    self.logger.info(f"Solana exit: theoretical={theoretical_value:.6f} SOL, actual={actual_sol_received:.6f} SOL")
                else:
                    exit_value_native = actual_sell_amount * target_price  # Theoretical for other chains
                exit_value_usd = 0
                
                # Get current price info from database (not API)
                current_price = await self._get_current_price_from_db(contract, chain)
                if current_price and current_price > 0:
                    # Get USD rate for cost calculation
                    native_usd_rate = await self._get_native_usd_rate(chain)
                    if native_usd_rate > 0:
                        exit_value_usd = exit_value_native * native_usd_rate
                    else:
                        exit_value_usd = 0.0
                else:
                    # No DB price available: abort execution (no API fallback)
                    self.logger.error("DB price unavailable for exit; aborting without fallback")
                    return None
                
                # exit_value_usd already calculated above using DB price and native USD rate
                
                # Update exit with transaction details and cost tracking
                target_exit['status'] = 'executed'
                target_exit['tx_hash'] = tx_hash
                target_exit['executed_at'] = datetime.now(timezone.utc).isoformat()
                target_exit['actual_tokens_sold'] = actual_sell_amount
                target_exit['cost_native'] = exit_value_native  # Amount received in native currency
                target_exit['cost_usd'] = exit_value_usd  # Amount received in USD
                # Convenience mirrors for downstream logic
                target_exit['tokens_sold'] = actual_sell_amount
                target_exit['native_amount'] = exit_value_native
                
                # Update totals and calculated fields in a single database write to avoid race conditions
                await self._update_exit_aggregates_atomic(position_id, actual_sell_amount, exit_value_native, target_exit)
                # Note: Exits don't need recalculation - they're already calculated based on entry price
                
                # Update P&L for all positions after successful exit
                await self._update_all_positions_pnl()
                
                # Set total_quantity immediately from trade execution and schedule reconciliation
                if self._service:
                    await self._service.set_quantity_from_trade(position_id, -actual_sell_amount)
                    # schedule reconciliation
                    await self._service.reconcile_wallet_quantity(position_id, position.get('total_quantity', 0))
                else:
                    await self._set_quantity_from_trade(position_id, -actual_sell_amount)
                
                # Update wallet balance for this chain after successful exit
                await self._update_wallet_balance_after_trade(chain)
                
                # Execute Lotus buyback for SOL exits - now we have the actual cost_native value
                buyback_result = None
                if self._service and chain.lower() == 'solana':
                    try:
                        buyback_cfg = (self.config or {}).get('lotus_buyback', {})
                        # Use actual SOL received for buyback calculation
                        actual_sol_received = target_exit.get('cost_native', 0)
                        if actual_sol_received <= 0:
                            self.logger.warning(f"Lotus buyback skipped: no SOL received (cost_native is {actual_sol_received})")
                            buyback_result = {'success': True, 'skipped': True, 'reason': 'No SOL received'}
                        else:
                            plan = self._service.plan_buyback(
                                chain=chain,
                                exit_value_native=actual_sol_received,
                                enabled=bool(buyback_cfg.get('enabled', False)),
                                percentage=float(buyback_cfg.get('percentage', 10.0)),
                                min_amount_native=float(buyback_cfg.get('min_amount_sol', 0.001)),
                            )
                            if plan and plan.get('success') and not plan.get('skipped'):
                                lotus_contract = buyback_cfg.get('lotus_contract')
                                holding_wallet = buyback_cfg.get('holding_wallet')
                                slippage_pct = float(buyback_cfg.get('slippage_pct', 5.0))
                                if lotus_contract and holding_wallet:
                                    buyback_amount = plan.get('buyback_amount_native', 0)
                                    self.logger.info(f"Executing Lotus buyback: {buyback_amount:.6f} SOL from {exit_value_native:.6f} SOL exit")
                                    buyback_result = await self._service.perform_buyback(
                                        lotus_contract=lotus_contract,
                                        holding_wallet=holding_wallet,
                                        buyback_amount_native=buyback_amount,
                                        slippage_pct=slippage_pct,
                                    )
                                    if buyback_result.get('success'):
                                        self.logger.info(f"Lotus buyback successful: {buyback_result.get('lotus_tokens', 0):.6f} Lotus tokens")
                                    else:
                                        self.logger.error(f"Lotus buyback failed: {buyback_result.get('error', 'Unknown error')}")
                                else:
                                    buyback_result = {'success': False, 'error': 'Missing lotus_contract or holding_wallet in config'}
                            else:
                                buyback_result = plan
                    except Exception as e:
                        self.logger.error(f"Lotus buyback failed: {e}")
                        buyback_result = {'success': False, 'error': f'buyback_service_failed: {str(e)}'}
                
                # Send Telegram sell signal notification via service (preferred)
                if self._service and self.telegram_notifier:
                    await self._service.send_sell_signal(
                        position_id=position_id,
                        exit_number=exit_number,
                        tokens_sold=actual_sell_amount,
                        sell_price=target_price,
                        tx_hash=tx_hash,
                        chain=chain,
                        contract=contract,
                        buyback_result=buyback_result,
                    )
                else:
                    pass
                
                # Position already updated atomically above with both exit object and aggregates
                
                trading_logger.log_exit_execution(
                    position_id=position_id,
                    exit_number=exit_number,
                    token=ticker,
                    chain=chain,
                    tokens_sold=actual_sell_amount,
                    price=target_price,
                    tx_hash=tx_hash
                )
                self.logger.info(f"✅ Exit {exit_number} executed successfully: {tx_hash}")
                # Spawn trend batch funded by this standard exit (best-effort)
                try:
                    if self._service:
                        batch_id = self._service.spawn_trend_from_exit(
                            position_id=position_id,
                            exit_price=target_exit.get('price', 0.0),
                            native_amount=target_exit.get('native_amount', 0.0) or target_exit.get('cost_native', 0.0),
                            source_exit_number=str(exit_number),
                        )
                        if batch_id:
                            trading_logger.log_trend_batch_creation(
                                batch_id=batch_id,
                                source_exit=str(exit_number),
                                amount=target_exit.get('native_amount', 0.0) or target_exit.get('cost_native', 0.0),
                                chain=chain
                            )
                            self.logger.info(f"Spawned trend batch via service: {batch_id}")
                except Exception as te:
                    self.logger.error(f"Failed spawning trend batch after exit: {te}")
                return True
            else:
                trading_logger.log_exit_failure(
                    position_id=position_id,
                    exit_number=exit_number,
                    token=ticker,
                    chain=chain,
                    reason='no_transaction_hash',
                    details='Executor returned None'
                )
                self.logger.error(f"❌ Exit {exit_number} failed - no transaction hash")
                return False
                
        except Exception as e:
            self.logger.error(f"Error executing exit {exit_number} for position {position_id}: {e}")
            return False
    
    async def _get_current_price_from_db(self, token_contract: str, chain: str) -> Optional[float]:
        """Get current price from database (delegates to service)."""
        try:
            if self._service:
                return await self._service.get_current_price_native_from_db(token_contract, chain)
            # fallback to direct
            result = self.repo.client.table('lowcap_price_data_1m').select('price_native').eq('token_contract', token_contract).eq('chain', chain).order('timestamp', desc=True).limit(1).execute()
            return float(result.data[0]['price_native']) if result and result.data else None
        except Exception:
            return None

    async def _update_position_pnl(self, position_id: str):
        """Update position P&L using database prices (uses pure domain helpers)."""
        if not self._service:
                return
        return await self._service._update_position_pnl(position_id)

    async def _get_all_active_positions(self) -> List[Dict[str, Any]]:
        """Get all active positions from database"""
        try:
            result = self.repo.client.table('lowcap_positions').select('*').eq('status', 'active').execute()
            return result.data if result.data else []
        except Exception as e:
            self.logger.error(f"Error getting active positions: {e}")
            return []

    async def _update_all_positions_pnl(self):
        """Update P&L for all active positions using database prices"""
        try:
            # Get all active positions
            active_positions = await self._get_all_active_positions()
            
            if not active_positions:
                self.logger.info("No active positions to update P&L for")
                return
            
            # Update P&L for each position
            updated_count = 0
            for position in active_positions:
                try:
                    await self._update_position_pnl(position['id'])
                    updated_count += 1
                except Exception as e:
                    self.logger.error(f"Error updating P&L for position {position.get('id', 'unknown')}: {e}")
            
            self.logger.info(f"Updated P&L for {updated_count}/{len(active_positions)} active positions")
            
        except Exception as e:
            self.logger.error(f"Error updating all positions P&L: {e}")

    async def _update_avg_entry_price(self, position_id: str):
        """Update average entry price based on executed entries"""
        try:
            # Get current position
            position = self.repo.get_position(position_id)
            if not position:
                self.logger.error(f"Position {position_id} not found for avg_entry_price update")
                return
            
            entries = position.get('entries', [])
            
            # Only consider executed entries with tokens_bought
            executed_entries = [
                e for e in entries 
                if e.get('status') == 'executed' and 'tokens_bought' in e
            ]
            
            if not executed_entries:
                # No executed entries yet
                position['avg_entry_price'] = 0
                self.repo.update_position(position_id, position)
                self.logger.info(f"No executed entries found for position {position_id}")
                return
            
            # Calculate weighted average entry price
            total_cost = sum(e.get('cost_native', 0) for e in executed_entries)
            total_tokens = sum(e.get('tokens_bought', 0) for e in executed_entries)
            
            if total_tokens > 0:
                avg_entry_price = total_cost / total_tokens
                position['avg_entry_price'] = avg_entry_price
                self.repo.update_position(position_id, position)
                self.logger.info(f"Updated avg_entry_price for {position_id}: {avg_entry_price:.8f} (from {len(executed_entries)} entries)")
            else:
                position['avg_entry_price'] = 0
                self.repo.update_position(position_id, position)
                self.logger.warning(f"Total tokens is 0 for position {position_id}")
                
        except Exception as e:
            self.logger.error(f"Error updating avg_entry_price for position {position_id}: {e}")


    

    async def _recalculate_position_totals(self, position: Dict[str, Any]):
        """Recalculate all position totals from entry history and wallet balance"""
        try:
            entries = position.get('entries', [])
            total_cost_native = 0
            total_cost_usd = 0

            for entry in entries:
                if entry.get('status') == 'executed':
                    cost_native = entry.get('cost_native', 0)
                    cost_usd = entry.get('cost_usd', 0)

                    total_cost_native += cost_native
                    total_cost_usd += cost_usd

            # Calculate total tokens bought from entries (not current wallet balance)
            total_tokens_bought = sum(entry.get('tokens_bought', 0) for entry in entries if entry.get('status') == 'executed')

            # Calculate average entry price based on original tokens bought
            if total_tokens_bought > 0:
                position['avg_entry_price'] = total_cost_native / total_tokens_bought
            else:
                position['avg_entry_price'] = 0

            # Do not reset P&L here; it will be updated by _update_position_pnl

            self.logger.info(f"Recalculated position totals: {total_tokens_bought} tokens bought, {total_cost_native:.6f} native")

        except Exception as e:
            self.logger.error(f"Error recalculating position totals: {e}")

    async def _execute_entry(self, position_id: str, entry_number: int):
        """
        Execute a planned entry for a position
        
        Args:
            position_id: Position ID
            entry_number: Entry number to execute
        """
        try:
            # Get position data
            position = self.repo.get_position(position_id)
            if not position:
                self.logger.error(f"Position {position_id} not found")
                return
            
            # Get the specific entry
            entries = position.get('entries', [])
            entry = next((e for e in entries if e.get('entry_number') == entry_number), None)
            if not entry:
                self.logger.error(f"Entry {entry_number} not found for position {position_id}")
                return
            
            if entry.get('status') != 'pending':
                self.logger.warning(f"Entry {entry_number} is not pending (status: {entry.get('status')})")
                return
            
            # Execute the entry
            chain = position.get('token_chain', '').lower()
            contract = position.get('token_contract')
            amount = entry.get('amount_native', 0)
            
            # Delegate entries for EVM via service; Solana uses native executor
            if chain in ('bsc','base','ethereum') and self._service:
                result = self._service.execute_entry(
                    position_id=position_id,
                    chain=chain,
                    contract=contract,
                    token_ticker=position.get('token_ticker', 'UNKNOWN'),
                    entry_number=entry_number,
                    amount_native=amount,
                    price_native=entry.get('price', 0.0),
                )
            elif chain == 'solana' and self.sol_executor:
                result = await self.sol_executor.execute_buy(contract, amount)
            else:
                self.logger.error(f"No executor available for chain {chain}")
                return
            
            if result:
                # Get current price info for cost calculation
                chain = position.get('token_chain', '').lower()
                contract = position.get('token_contract')
                
                # Calculate cost tracking
                cost_native = amount
                cost_usd = 0
                tokens_bought = 0
                
                # Get price info from database (not API)
                price = await self._get_current_price_from_db(contract, chain)
                if price and price > 0:
                    tokens_bought = amount / price
                    
                    # Get USD rate for cost calculation
                    native_usd_rate = await self._get_native_usd_rate(chain)
                    if native_usd_rate > 0:
                        cost_usd = amount * native_usd_rate
                    else:
                        cost_usd = 0.0
                else:
                    # No DB price available: abort execution (no API fallback)
                    self.logger.error("DB price unavailable for entry; aborting without fallback")
                    return None
                
                # Mark entry as executed with cost tracking
                self.repo.mark_entry_executed(
                    position_id=position_id,
                    entry_number=entry_number,
                    tx_hash=result,
                    cost_native=cost_native,
                    cost_usd=cost_usd,
                    tokens_bought=tokens_bought
                )
                
                # Update totals and calculated fields
                await self._update_tokens_bought(position_id, tokens_bought)
                await self._update_total_investment_native(position_id, amount)
                await self._update_position_pnl(position_id)
                if self._service:
                    await self._service.recalculate_exits_after_entry(position_id)
                else:
                    # Fallback: recalculate exits using existing method
                    self.recalculate_exits_for_position(position_id, position.get('avg_entry_price', 0))
                # Update P&L for all positions after successful entry
                await self._update_all_positions_pnl()
                
                # Set total_quantity immediately from trade execution and schedule reconciliation
                await self._set_quantity_from_trade(position_id, tokens_bought)
                
                # Update wallet balance for this chain after successful entry
                await self._update_wallet_balance_after_trade(chain)
                
                # Send notification for additional entries via service notifier if configured
                if self._service and self.telegram_notifier:
                    await self._service.send_buy_signal(
                        token_ticker=position.get('token_ticker', 'Unknown'),
                        token_contract=position.get('token_contract', ''),
                        chain=chain,
                        amount_native=amount,
                        price=entry.get('price', 0),
                        tx_hash=result,
                        allocation_pct=None,
                        source_tweet_url=position.get('source_tweet_url'),
                    )
                
                trading_logger.log_entry_execution(
                    position_id=position_id,
                    entry_number=entry_number,
                    token=position.get('token_ticker', 'UNKNOWN'),
                    chain=chain,
                    amount=amount,
                    price=entry.get('price', 0),
                    tx_hash=result
                )
                self.logger.info(f"Entry {entry_number} executed successfully: {result}")
            else:
                trading_logger.log_entry_failure(
                    position_id=position_id,
                    entry_number=entry_number,
                    token=position.get('token_ticker', 'UNKNOWN'),
                    chain=chain,
                    reason='execution_failed',
                    details='No transaction hash returned'
                )
                self.logger.error(f"Entry {entry_number} execution failed")
                # Mark as failed to prevent endless retries
                self.repo.mark_entry_failed(position_id, entry_number, reason='confirmation_failed')
                
        except Exception as e:
            self.logger.error(f"Error executing entry {entry_number} for position {position_id}: {e}")
            # Mark as failed on unexpected error
            try:
                self.repo.mark_entry_failed(position_id, entry_number, reason='execution_exception')
            except Exception:
                pass

    async def _execute_entry_with_confirmation(self, position_id: str, entry_number: int) -> bool:
        """
        Execute a planned entry for a position and wait for confirmation
        
        Args:
            position_id: Position ID
            entry_number: Entry number to execute
            
        Returns:
            True if executed and confirmed, False otherwise
        """
        try:
            # Get position data
            position = self.repo.get_position(position_id)
            if not position:
                self.logger.error(f"Position {position_id} not found")
                return False
            
            # Get the specific entry
            entries = position.get('entries', [])
            entry = next((e for e in entries if e.get('entry_number') == entry_number), None)
            if not entry:
                self.logger.error(f"Entry {entry_number} not found for position {position_id}")
                return False
            
            if entry.get('status') != 'pending':
                self.logger.warning(f"Entry {entry_number} is not pending (status: {entry.get('status')})")
                return False
            
            # Execute the entry
            chain = position.get('token_chain', '').lower()
            contract = position.get('token_contract')
            amount = entry.get('amount_native', 0)
            
            result = None
            if chain == 'bsc' and self.bsc_executor:
                result = self.bsc_executor.execute_buy(contract, amount)
            elif chain == 'base' and self.base_executor:
                result = self.base_executor.execute_buy(contract, amount)
            elif chain == 'ethereum' and self.eth_executor:
                result = self.eth_executor.execute_buy(contract, amount)
            elif chain == 'solana' and self.sol_executor:
                result = await self.sol_executor.execute_buy(contract, amount)
            else:
                self.logger.error(f"No executor available for chain {chain}")
                return False
            
            if result:
                # Wait for transaction confirmation before marking as executed
                if chain in ['bsc', 'base', 'ethereum']:
                    # For EVM chains, wait for transaction confirmation
                    confirmed = await self._wait_for_transaction_confirmation(result, chain)
                    if confirmed:
                        # Calculate cost tracking
                        cost_native = amount
                        cost_usd = 0
                        tokens_bought = 0
                        
                        # Get price from database (not API)
                        price = await self._get_current_price_from_db(contract, chain)
                        if price and price > 0:
                            tokens_bought = amount / price
                            
                            # Get USD rate for cost calculation
                            native_usd_rate = await self._get_native_usd_rate(chain)
                            if native_usd_rate > 0:
                                cost_usd = amount * native_usd_rate
                            else:
                                cost_usd = 0.0
                        else:
                            # No DB price available: use fallback values
                            tokens_bought = 0
                            cost_usd = 0
                        
                        # Mark entry as executed with cost tracking
                        self.repo.mark_entry_executed(
                            position_id=position_id,
                            entry_number=entry_number,
                            tx_hash=result,
                            cost_native=cost_native,
                            cost_usd=cost_usd,
                            tokens_bought=tokens_bought
                        )
                        
                        # Update totals and calculated fields
                        await self._update_tokens_bought(position_id, tokens_bought)
                        await self._update_total_investment_native(position_id, amount)
                        await self._update_position_pnl(position_id)
                        if self._service:
                            await self._service.recalculate_exits_after_entry(position_id)
                        else:
                            # Fallback: recalculate exits using existing method
                            self.recalculate_exits_for_position(position_id, position.get('avg_entry_price', 0))
                        # Update P&L for all positions after successful entry
                        await self._update_all_positions_pnl()
                        
                        # Set total_quantity immediately from trade execution and schedule reconciliation
                        await self._set_quantity_from_trade(position_id, tokens_bought)
                        
                        # Send notification for additional entries via service notifier if configured
                        if self._service and self.telegram_notifier:
                            await self._service.send_buy_signal(
                                token_ticker=position.get('token_ticker', 'Unknown'),
                                token_contract=position.get('token_contract', ''),
                                chain=chain,
                            amount_native=amount,
                                price=entry.get('price', 0),
                                tx_hash=result,
                                allocation_pct=None,
                                source_tweet_url=position.get('source_tweet_url'),
                        )
                        
                        self.logger.info(f"Entry {entry_number} executed and confirmed: {result}")
                        return True
                    else:
                        self.logger.error(f"Entry {entry_number} transaction not confirmed: {result}")
                        return False
                else:
                    # For Solana, assume immediate confirmation
                    # Calculate cost tracking
                    cost_native = amount
                    cost_usd = 0
                    tokens_bought = 0
                    
                    # Get price from database (not API)
                    price = await self._get_current_price_from_db(contract, chain)
                    if price and price > 0:
                        tokens_bought = amount / price
                        
                        # Get USD rate for cost calculation
                        native_usd_rate = await self._get_native_usd_rate(chain)
                        if native_usd_rate > 0:
                            cost_usd = amount * native_usd_rate
                        else:
                            cost_usd = 0.0
                    else:
                        # No DB price available: use fallback values
                        tokens_bought = 0
                        cost_usd = 0
                    
                    # Mark entry as executed with cost tracking
                    self.repo.mark_entry_executed(
                        position_id=position_id,
                        entry_number=entry_number,
                        tx_hash=result,
                        cost_native=cost_native,
                        cost_usd=cost_usd,
                        tokens_bought=tokens_bought
                    )
                    
                    # Update totals and calculated fields
                    await self._update_tokens_bought(position_id, tokens_bought)
                    await self._update_total_investment_native(position_id, amount)
                    await self._update_position_pnl(position_id)
                    if self._service:
                        await self._service.recalculate_exits_after_entry(position_id)
                    else:
                        # Fallback: recalculate exits using existing method
                        self.recalculate_exits_for_position(position_id, position.get('avg_entry_price', 0))
                    # Update P&L for all positions after successful entry
                    await self._update_all_positions_pnl()
                    
                    # Set total_quantity immediately from trade execution and schedule reconciliation
                    await self._set_quantity_from_trade(position_id, tokens_bought)
                    
                    # Send notification for additional entries via service notifier if configured
                    if self._service and self.telegram_notifier:
                        await self._service.send_buy_signal(
                            token_ticker=position.get('token_ticker', 'Unknown'),
                            token_contract=position.get('token_contract', ''),
                            chain=chain,
                        amount_native=amount,
                            price=entry.get('price', 0),
                            tx_hash=result,
                            allocation_pct=None,
                            source_tweet_url=position.get('source_tweet_url'),
                    )
                    
                    self.logger.info(f"Entry {entry_number} executed: {result}")
                    return True
            else:
                self.logger.error(f"Entry {entry_number} execution failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Error executing entry {entry_number} for position {position_id}: {e}")
            return False

    async def _wait_for_transaction_confirmation(self, tx_hash: str, chain: str, timeout: int = 60) -> bool:
        """
        Wait for transaction confirmation on the blockchain
        
        Args:
            tx_hash: Transaction hash
            chain: Blockchain network
            timeout: Timeout in seconds
            
        Returns:
            True if confirmed, False if timeout or failed
        """
        try:
            # Get the appropriate client
            client = None
            if chain == 'base' and self.base_executor:
                client = self.base_executor.client
            elif chain == 'ethereum' and self.eth_executor:
                client = self.eth_executor.client
            elif chain == 'bsc' and self.bsc_executor:
                client = self.bsc_executor.client
            
            if not client:
                self.logger.error(f"No client available for chain {chain}")
                return False
            
            # Wait for transaction confirmation
            import time
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    receipt = client.w3.eth.get_transaction_receipt(tx_hash)
                    if receipt and receipt.status == 1:
                        self.logger.info(f"Transaction confirmed: {tx_hash}")
                        return True
                    elif receipt and receipt.status == 0:
                        self.logger.error(f"Transaction failed: {tx_hash}")
                        return False
                except:
                    # Transaction not yet mined, continue waiting
                    pass
                
                await asyncio.sleep(2)  # Check every 2 seconds
            
            self.logger.error(f"Transaction confirmation timeout: {tx_hash}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error waiting for transaction confirmation: {e}")
            return False

    async def _detect_and_update_tax_token(self, token_address: str, amount_spent: float, price: float, chain: str) -> None:
        """
        Detect if a token has taxes by comparing expected vs actual tokens received
        
        Args:
            token_address: Token contract address
            amount_spent: Amount of native token spent (ETH, BNB, etc.)
            price: Price per token in native currency
            chain: Chain name ('ethereum', 'bsc', 'base', 'solana')
        """
        try:
            print(f"🔍 Detecting tax for token {token_address} on {chain}")
            
            # Calculate expected tokens based on native price
            expected_tokens = amount_spent / price
            print(f"Expected tokens: {expected_tokens}")
            
            # Wait a moment for transaction to be mined and balance to update
            await asyncio.sleep(5)
            
            # Get actual tokens received
            actual_tokens = await self.wallet_manager.get_balance(chain, token_address)
            if actual_tokens is None:
                print(f"❌ Could not get balance for {token_address}")
                return
            
            print(f"Actual tokens received: {actual_tokens}")
            
            # Calculate tax percentage
            if expected_tokens > 0 and actual_tokens > 0:
                # Convert Decimal to float for calculation
                actual_tokens_float = float(actual_tokens)
                tax_pct = ((expected_tokens - actual_tokens_float) / expected_tokens) * 100
                print(f"Tax percentage: {tax_pct:.2f}%")
                
                # If tax is significant (>1%), update the database
                if tax_pct > 1.0:
                    print(f"✅ Detected tax token: {token_address} has {tax_pct:.2f}% tax")
                    success = self.repo.update_tax_percentage(token_address, tax_pct)
                    if success:
                        print(f"✅ Updated database: {token_address} = {tax_pct:.2f}% tax")
                    else:
                        print(f"❌ Failed to update database for {token_address}")
                else:
                    print(f"✅ No significant tax detected for {token_address}")
            else:
                print(f"❌ Invalid token amounts: expected={expected_tokens}, actual={actual_tokens}")
                
        except Exception as e:
            print(f"❌ Error detecting tax for {token_address}: {e}")
            import traceback
            traceback.print_exc()

    async def _send_buy_notification(self, 
                                   token_ticker: str, 
                                   token_contract: str, 
                                   chain: str, 
                                   amount_native: float, 
                                   price: float, 
                                   tx_hash: str,
                                   allocation_pct: float,
                                   decision: Dict[str, Any]) -> None:
        if not (self._service and self.telegram_notifier):
            return
        # Source URL extraction remains here
            source_tweet_url = None
            signal_pack = decision.get('signal_pack', {})
            if signal_pack:
                source_tweet_url = (
                    signal_pack.get('source_tweet_url') or
                    signal_pack.get('tweet_url') or
                    signal_pack.get('url') or
                    signal_pack.get('message', {}).get('url')
                )
            if not source_tweet_url:
                module_intelligence = decision.get('module_intelligence', {})
                social_signal = module_intelligence.get('social_signal', {})
                message = social_signal.get('message', {})
                source_tweet_url = message.get('url')
        await self._service.send_buy_signal(
                token_ticker=token_ticker,
                token_contract=token_contract,
                chain=chain,
                amount_native=amount_native,
                price=price,
                tx_hash=tx_hash,
                allocation_pct=allocation_pct,
            source_tweet_url=source_tweet_url,
            )

    async def _send_additional_entry_notification(self,
                                                position_id: str,
                                                entry_number: int,
                                                tx_hash: str,
                                                amount_native: float,
                                                cost_usd: float) -> None:
        """Send notification for additional entries (not the first one)"""
        if not self.telegram_notifier:
            return
        
        try:
            # Get position data
            position = self.repo.get_position(position_id)
            if not position:
                return
            
            token_ticker = position.get('token_ticker', 'Unknown')
            token_contract = position.get('token_contract', '')
            chain = position.get('token_chain', '').lower()
            
            # Get entry details
            entries = position.get('entries', [])
            entry = next((e for e in entries if e.get('entry_number') == entry_number), None)
            if not entry:
                return
            
            price = entry.get('price', 0)
            entry_type = entry.get('entry_type', 'additional')
            
            # Calculate USD amount
            amount_usd = cost_usd if cost_usd > 0 else None
            
            # Get source tweet URL from position
            source_tweet_url = position.get('source_tweet_url')
            
            # Send notification
            await self.telegram_notifier.send_buy_signal(
                token_ticker=token_ticker,
                token_contract=token_contract,
                chain=chain,
                amount_native=amount_native,
                price=price,
                tx_hash=tx_hash,
                source_tweet_url=source_tweet_url,
                allocation_pct=None,  # Not applicable for additional entries
                amount_usd=amount_usd
            )
            
            self.logger.info(f"Additional entry notification sent for {token_ticker} entry {entry_number}")
            
        except Exception as e:
            self.logger.error(f"Failed to send additional entry notification: {e}")

    async def _send_sell_notification(self,
                                    token_ticker: str,
                                    token_contract: str,
                                    chain: str,
                                    tokens_sold: float,
                                    sell_price: float,
                                    tx_hash: str,
                                    profit_pct: Optional[float] = None,
                                    profit_usd: Optional[float] = None,
                                    total_profit_usd: Optional[float] = None,
                                    position_id: Optional[str] = None) -> None:
        if not (self._service and self.telegram_notifier and position_id):
            return
        await self._service.send_sell_signal(
            position_id=position_id,
            exit_number=0,
                tokens_sold=tokens_sold,
                sell_price=sell_price,
                tx_hash=tx_hash,
            chain=chain,
            contract=token_contract,
            buyback_result=None,
        )

    async def _send_trend_entry_notification(self,
                                           position_id: str,
                                           entry_number: int,
                                           tx_hash: str,
                                           amount_native: float,
                                           price: float,
                                           dip_pct: float,
                                           batch_id: str) -> None:
        if self._service and self.telegram_notifier:
            await self._service.send_trend_entry_notification(
                position_id=position_id,
                entry_number=entry_number,
                tx_hash=tx_hash,
                amount_native=amount_native,
                price=price,
                dip_pct=dip_pct,
                batch_id=batch_id,
            )

    async def _send_trend_exit_notification(self,
                                          position_id: str,
                                          exit_number: int,
                                          tx_hash: str,
                                          tokens_sold: float,
                                          sell_price: float,
                                          gain_pct: float,
                                          batch_id: str,
                                          profit_pct: float = None,
                                          profit_usd: float = None) -> None:
        if self._service and self.telegram_notifier:
            await self._service.send_trend_exit_notification(
                position_id=position_id,
                exit_number=exit_number,
                tx_hash=tx_hash,
                tokens_sold=tokens_sold,
                sell_price=sell_price,
                gain_pct=gain_pct,
                batch_id=batch_id,
                profit_pct=profit_pct,
                profit_usd=profit_usd,
            )

    async def _send_sell_notification_for_exit(self,
                                             position_id: str,
                                             exit_number: int,
                                             tokens_sold: float,
                                             sell_price: float,
                                             tx_hash: str,
                                             chain: str,
                                             contract: str,
                                             buyback_result: dict = None) -> None:
        """Send Telegram sell signal notification for a specific exit"""
        if not self.telegram_notifier:
            return
        
        try:
            # Get position data
            position = self.repo.get_position(position_id)
            if not position:
                self.logger.error(f"Position not found for sell notification: {position_id}")
                return
            
            token_ticker = position.get('token_ticker', 'UNKNOWN')
            
            # Get total position P&L from database
            total_profit_usd = position.get('total_pnl_usd')
            total_pnl_pct = position.get('total_pnl_pct', 0)
            
            # Build sell view for derived values
            sell_view = await build_sell_view(
                position=position,
                tokens_sold=tokens_sold,
                sell_price_native=sell_price,
                chain=chain,
                contract=contract,
                price_oracle=self.price_oracle,
                get_native_usd_rate=self._get_native_usd_rate,
            )
            tokens_sold_value_usd = sell_view.get('tokens_sold_value_usd')
            
            # Get position context for enhanced notification
            remaining_tokens = position.get('total_quantity', 0) - tokens_sold
            position_value = sell_view.get('position_value')
            profit_native = sell_view.get('profit_native')
            
            # Calculate native P&L for this exit
            if profit_usd and chain in ['bsc', 'base', 'ethereum']:
                native_usd_rate = await (self._service.get_native_usd_rate_async(chain) if self._service else self._get_native_usd_rate(chain))
                if native_usd_rate > 0:
                    profit_native = profit_usd / native_usd_rate
            
            # Extract buyback data if available
            buyback_amount_sol = None
            lotus_tokens = None
            buyback_tx_hash = None
            
            if buyback_result and buyback_result.get('success') and not buyback_result.get('skipped'):
                buyback_amount_sol = buyback_result.get('buyback_amount_sol')
                lotus_tokens = buyback_result.get('lotus_tokens')
                buyback_tx_hash = buyback_result.get('transfer_tx_hash')
            
            await self.telegram_notifier.send_sell_signal(
                token_ticker=token_ticker,
                token_contract=contract,
                chain=chain,
                tokens_sold=tokens_sold,
                sell_price=sell_price,
                tx_hash=tx_hash,
                tokens_sold_value_usd=tokens_sold_value_usd,
                total_profit_usd=total_profit_usd,
                source_tweet_url=position.get('source_tweet_url'),
                remaining_tokens=remaining_tokens,
                position_value=position_value,
                total_pnl_pct=total_pnl_pct,
                profit_native=profit_native,
                buyback_amount_sol=buyback_amount_sol,
                lotus_tokens=lotus_tokens,
                buyback_tx_hash=buyback_tx_hash
            )
            
            self.logger.info(f"Sell signal notification sent for {token_ticker} exit {exit_number}")
            
        except Exception as e:
            self.logger.error(f"Failed to send sell notification for exit: {e}")
    
    def _build_exit_rules_from_config(self) -> Dict[str, Any]:
        """Build exit rules from config file"""
        import yaml
        import os
        
        # Load config
        config_path = os.path.join(os.path.dirname(__file__), '../../config/social_trading_config.yaml')
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        exit_strategy = config['position_management']['exit_strategy']
        
        stages = []
        for exit_key, exit_config in exit_strategy.items():
            if exit_key != 'final':  # Handle final exit separately
                stages.append({
                    'gain_pct': exit_config['gain_pct'],
                    'exit_pct': exit_config['exit_pct'],
                    'executed': False
                })
        
        # Add final exit
        final_config = exit_strategy['final']
        stages.append({
            'gain_pct': final_config['gain_pct'],
            'exit_pct': final_config['exit_pct'],
            'executed': False
        })
        
        return {
            'strategy': 'staged',
            'stages': stages
        }

    def _build_trend_exit_rules_from_config(self) -> Dict[str, Any]:
        """Build trend exit rules from config file"""
        import yaml
        import os
        
        # Load config
        config_path = os.path.join(os.path.dirname(__file__), '../../config/social_trading_config.yaml')
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        trend_strategy = config['position_management']['trend_strategy']
        exits_config = trend_strategy['exits']
        
        stages = []
        for exit_config in exits_config:
            stages.append({
                'gain_pct': exit_config['gain_pct'],
                'exit_pct': exit_config['exit_pct'],
                'executed': False
            })
        
        return {
            'strategy': 'trend_dip_recovery',
            'entry_capital_pct': trend_strategy['entry_capital_pct'],
            'stages': stages
        }
    
    async def _update_tokens_bought(self, position_id: str, tokens_bought: float) -> bool:
        """Update total_tokens_bought when an entry is executed"""
        if not self._service:
                return False
        return await self._service._update_tokens_bought(position_id, tokens_bought)
    
    async def _update_tokens_sold(self, position_id: str, tokens_sold: float) -> bool:
        """Update total_tokens_sold when an exit is executed"""
        if not self._service:
                return False
        return await self._service._update_tokens_sold(position_id, tokens_sold)
    
    async def _update_total_investment_native(self, position_id: str, amount_native: float) -> bool:
        """Update total_investment_native when an entry is executed"""
        if not self._service:
                return False
        return await self._service._update_total_investment_native(position_id, amount_native)
    
    async def _update_total_extracted_native(self, position_id: str, amount_native: float) -> bool:
        """Update total_extracted_native when an exit is executed"""
        if not self._service:
                return False
        return await self._service._update_total_extracted_native(position_id, amount_native)

    async def _update_exit_aggregates_atomic(self, position_id: str, tokens_sold: float, native_amount: float, target_exit: Dict[str, Any]) -> bool:
        """Update all exit aggregates and exit object in a single atomic database write to avoid race conditions"""
        try:
            if not self._service:
                return False
            
            # Get position once
            position = self._service.repo.get_position(position_id)
            if not position:
                self.logger.error(f"Position {position_id} not found for atomic exit update")
                return False
            
            # Update exit object in the position
            exits = position.get('exits', [])
            for exit_data in exits:
                if exit_data.get('exit_number') == target_exit.get('exit_number'):
                    # Update the exit object with all the transaction details
                    exit_data.update(target_exit)
                    break
            
            # Update all aggregate fields in memory
            current_tokens_sold = position.get('total_tokens_sold', 0.0) or 0.0
            current_extracted = position.get('total_extracted_native', 0.0) or 0.0
            
            position['total_tokens_sold'] = current_tokens_sold + tokens_sold
            position['total_extracted_native'] = current_extracted + native_amount
            
            # Update P&L in memory
            await self._service._update_position_pnl_in_memory(position)
            
            # Single database write with both exit object and aggregates
            success = self._service.repo.update_position(position_id, position)
            if success:
                self.logger.info(f"Updated exit aggregates atomically for {position_id}: +{tokens_sold:.8f} tokens sold, +{native_amount:.8f} native extracted")
            return success
            
        except Exception as e:
            self.logger.error(f"Error in atomic exit aggregate update for {position_id}: {e}")
            return False
    
    async def _get_native_usd_rate(self, chain: str) -> float:
        """Get native currency USD rate for P&L conversion"""
        try:
            # Map chains to their native token contracts
            native_contracts = {
                'ethereum': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',  # WETH
                'base': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',      # WETH (same as Ethereum)
                'bsc': '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c',       # WBNB
                'solana': 'So11111111111111111111111111111111111111112'      # SOL
            }
            
            native_contract = native_contracts.get(chain.lower())
            if not native_contract:
                self.logger.error(f"Unknown chain for native USD rate: {chain}")
                return 0.0
            
            # Get price from database (from scheduled price collection)
            if chain.lower() in ['ethereum', 'base']:
                # Use Ethereum WETH price for both Ethereum and Base
                lookup_chain = 'ethereum'
            else:
                lookup_chain = chain.lower()
            
            result = self.repo.client.table('lowcap_price_data_1m').select(
                'price_usd'
            ).eq('token_contract', native_contract).eq('chain', lookup_chain).order(
                'timestamp', desc=True
            ).limit(1).execute()
            
            if result.data:
                return float(result.data[0].get('price_usd', 0))
            else:
                self.logger.warning(f"No native USD rate found in database for {chain}")
                return 0.0
                
        except Exception as e:
            self.logger.error(f"Error getting native USD rate for {chain}: {e}")
            return 0.0



    async def _execute_solana_swap(self, input_amount: float, input_token: str, output_token: str, slippage_pct: float) -> dict:
        """Execute a Solana token swap using existing Jupiter infrastructure"""
        try:
            if not self.js_solana_client:
                self.logger.error("JSSolanaClient not available for Lotus buyback")
                return {'success': False, 'error': 'JSSolanaClient not initialized'}
            
            # Convert SOL amount to lamports (9 decimals)
            input_amount_lamports = int(input_amount * 1_000_000_000)
            
            # Convert slippage percentage to basis points
            slippage_bps = int(slippage_pct * 100)
            
            # Execute Jupiter swap: SOL -> Lotus
            result = await self.js_solana_client.execute_jupiter_swap(
                input_mint="So11111111111111111111111111111111111111112",  # SOL mint
                output_mint=output_token,  # Lotus contract
                amount=input_amount_lamports,
                slippage_bps=slippage_bps
            )
            
            if result.get('success', False):
                # The Jupiter response already has the correct output amount
                output_amount = result.get('outputAmount', 0)
                # Convert from the raw amount to token units (assuming 9 decimals for Lotus)
                output_amount_tokens = float(output_amount) / 1_000_000_000
                return {
                    'success': True,
                    'output_amount': output_amount_tokens,
                    'tx_hash': result.get('signature', ''),
                    'input_amount': input_amount,
                    'output_token': output_token
                }
            else:
                self.logger.error(f"Jupiter swap failed: {result.get('error', 'Unknown error')}")
                return {'success': False, 'error': result.get('error', 'Jupiter swap failed')}
                
        except Exception as e:
            self.logger.error(f"Error in Solana swap: {e}")
            return {'success': False, 'error': str(e)}

    async def _send_tokens_to_wallet(self, token_contract: str, amount: float, destination_wallet: str, chain: str) -> bool:
        """Send tokens to a specific wallet address using existing wallet system"""
        try:
            if chain.lower() != 'solana':
                self.logger.error(f"Token transfer only supported for Solana, got: {chain}")
                return False
            
            if not self.js_solana_client:
                self.logger.error("JSSolanaClient not available for token transfer")
                return False
            
            # Use the new send_lotus_tokens method
            result = await self.js_solana_client.send_lotus_tokens(amount, destination_wallet)
            
            if result.get('success'):
                self.logger.info(f"✅ Lotus tokens sent: {amount:.6f} to {destination_wallet}")
                self.logger.info(f"   Transaction: {result.get('signature')}")
                # Update P&L for all positions after successful buyback
                await self._update_all_positions_pnl()
                return True
            else:
                self.logger.error(f"❌ Failed to send Lotus tokens: {result.get('error')}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error in token transfer: {e}")
            return False
    
    def recalculate_exits_for_position(self, position_id: str, new_avg_entry_price: float) -> bool:
        """Recalculate exit prices when avg_entry_price changes"""
        try:
            # Get current position and exit rules
            position = self.repo.get_position(position_id)
            if not position:
                self.logger.error(f"Position {position_id} not found for exit recalculation")
                return False
            
            exit_rules = position.get('exit_rules', {})
            if not exit_rules:
                self.logger.error(f"No exit rules found for position {position_id}")
                return False
            
            # Recalculate exits with new avg_entry_price
            exits = EntryExitPlanner.build_exits(exit_rules, new_avg_entry_price)
            
            # Update exits in database
            success = self.repo.update_exits(position_id, exits)
            if success:
                self.logger.info(f"Recalculated exits for position {position_id} with new avg_entry_price: {new_avg_entry_price}")
            else:
                self.logger.error(f"Failed to update exits for position {position_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error recalculating exits for position {position_id}: {e}")
            return False

    async def _store_native_balance(self, chain: str, balance: float):
        """Store/update native token balance in database for portfolio tracking"""
        try:
            # Get USD value if possible
            balance_usd = None
            if chain in ['ethereum', 'base']:
                eth_rate = await (self._service.get_native_usd_rate_async('ethereum') if self._service else self._get_native_usd_rate('ethereum'))
                balance_usd = float(balance) * eth_rate if eth_rate > 0 else None
            elif chain == 'bsc':
                bnb_rate = await (self._service.get_native_usd_rate_async('bsc') if self._service else self._get_native_usd_rate('bsc'))
                balance_usd = float(balance) * bnb_rate if bnb_rate > 0 else None
            elif chain == 'solana':
                sol_rate = await (self._service.get_native_usd_rate_async('solana') if self._service else self._get_native_usd_rate('solana'))
                balance_usd = float(balance) * sol_rate if sol_rate > 0 else None
            
            # Upsert balance (insert or update)
            self.repo.client.table('wallet_balances').upsert({
                'chain': chain,
                'balance': float(balance),
                'balance_usd': balance_usd,
                'wallet_address': self.wallet_manager.get_wallet_address(chain),
                'last_updated': datetime.now(timezone.utc).isoformat()
            }).execute()
            
            self.logger.debug(f"Updated {chain} balance: {balance:.6f}")
            
        except Exception as e:
            self.logger.error(f"Error storing {chain} balance: {e}")

    async def _update_wallet_balance_after_trade(self, chain: str):
        """Update wallet balance in database after a trade execution"""
        try:
            # Get current native token balance for this chain
            current_balance = await self.wallet_manager.get_balance(chain)
            if current_balance is not None:
                await self._store_native_balance(chain, float(current_balance))
                self.logger.info(f"Updated {chain} wallet balance after trade: {float(current_balance):.6f}")
            else:
                self.logger.warning(f"Could not get current balance for {chain} after trade")
                
        except Exception as e:
            self.logger.error(f"Error updating wallet balance for {chain} after trade: {e}")

    async def _convert_to_usdc_after_exit(self, chain: str, native_amount: float, slippage_pct: float = 2.0) -> Dict[str, Any]:
        """Convert native token to USDC after exit (like Lotus buyback)"""
        try:
            if chain == 'bsc' and self.bsc_executor:
                result = await self.bsc_executor.swap_native_to_usdc(native_amount, slippage_pct)
            elif chain == 'base' and self.base_executor:
                result = await self.base_executor.swap_native_to_usdc(native_amount, slippage_pct)
            else:
                return {'success': False, 'error': f'No executor available for {chain}'}
            
            if result.get('success'):
                usdc_received = result.get('usdc_received', 0)
                self.logger.info(f"USDC conversion successful: {native_amount:.6f} {chain.upper()} → {usdc_received:.2f} USDC")
            else:
                self.logger.error(f"USDC conversion failed: {result.get('error', 'Unknown error')}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in USDC conversion for {chain}: {e}")
            return {'success': False, 'error': str(e)}

    async def _set_quantity_from_trade(self, position_id: str, tokens_delta: float) -> bool:
        """Set total_quantity from trade execution"""
        try:
            if self._service:
                return await self._service.set_quantity_from_trade(position_id, tokens_delta)
            else:
                # Fallback implementation
                position = self.repo.get_position(position_id)
                if not position:
                    return False
                old_quantity = float(position.get('total_quantity', 0.0) or 0.0)
                new_quantity = old_quantity + float(tokens_delta)
                position['total_quantity'] = new_quantity
                return self.repo.update_position(position_id, position)
        except Exception as e:
            self.logger.error(f"Error setting quantity from trade for {position_id}: {e}")
            return False


