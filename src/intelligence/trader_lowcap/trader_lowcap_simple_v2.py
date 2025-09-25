"""
Trader Lowcap V2 - modularized for safer BSC path

Implements BSC price+execution using PriceOracle and BscExecutor, and isolates
DB writes for entries/exits to avoid brittle cross-dependencies.
"""

import os
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from intelligence.trader_lowcap.price_oracle import PriceOracle
from intelligence.trader_lowcap.evm_executors import BscExecutor, BaseExecutor, EthExecutor
from intelligence.trader_lowcap.position_repository import PositionRepository
from intelligence.trader_lowcap.entry_exit_planner import EntryExitPlanner
from trading.wallet_manager import WalletManager
from trading.jupiter_client import JupiterClient
from trading.js_solana_client import JSSolanaClient
from intelligence.trader_lowcap.solana_executor import SolanaExecutor
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
            return notifier
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Telegram signal notifier: {e}")
            return None

    async def execute_decision(self, decision: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            if decision.get('content', {}).get('action') != 'approve':
                return None

            token = (decision.get('signal_pack') or {}).get('token') or {}
            chain = (token.get('chain') or '').lower()
            ticker = token.get('ticker')
            contract = token.get('contract')
            allocation_pct = float(decision.get('content', {}).get('allocation_pct') or 0)

            # Idempotency: skip if this decision was already processed (book_id)
            existing_for_book = self.repo.get_position_by_book_id(decision.get('id'))
            if existing_for_book:
                self.logger.warning(f"Trader V2: Skipping decision {decision.get('id')} - book_id already exists: {existing_for_book.get('id')}")
                return None

            # Select chain path
            if chain == 'bsc':
                if not self.bsc_client:
                    self.logger.error("Trader V2: BSC client not available")
                    return None
                native_symbol = 'bsc'
                native_label = 'BNB'
                balance = await self.wallet_manager.get_balance('bsc')
                price_info = self.price_oracle.price_bsc(contract)
                price = price_info['price_native'] if price_info else None
                executor = self.bsc_executor
                venue = self._resolve_bsc_venue(contract)
            elif chain == 'base':
                if not self.base_client:
                    self.logger.error("Trader V2: Base client not available")
                    return None
                native_symbol = 'base'
                native_label = 'ETH'
                # Base and ETH share wallet; we count balance as ETH equivalent
                balance = await self.wallet_manager.get_balance('base')
                price_info = self.price_oracle.price_base(contract)
                price = price_info['price_native'] if price_info else None
                executor = self.base_executor
                venue = self._resolve_base_venue(contract)
            elif chain == 'ethereum':
                if not self.eth_client:
                    self.logger.error("Trader V2: ETH client not available")
                    return None
                native_symbol = 'ethereum'
                native_label = 'ETH'
                balance = await self.wallet_manager.get_balance('ethereum')
                price_info = self.price_oracle.price_eth(contract)
                price = price_info['price_native'] if price_info else None
                executor = self.eth_executor
                venue = None
            elif chain == 'solana':
                native_symbol = 'solana'
                native_label = 'SOL'
                balance = await self.wallet_manager.get_balance('solana')
                # Price via PriceOracle (SOL/token) with Jupiter fallback
                price = None
                try:
                    # Try PriceOracle first for native SOL pricing
                    price_info = self.price_oracle.price_solana(contract)
                    if price_info and price_info.get('price_native'):
                        price = price_info['price_native']
                        self.logger.info(f"Solana price from PriceOracle: {price} SOL per token")
                    else:
                        raise Exception('PriceOracle failed, trying Jupiter fallback')
                except Exception:
                    try:
                        # Fallback to Jupiter quote-based pricing
                        quote = await self.jupiter_client.get_quote(
                            input_mint="So11111111111111111111111111111111111111112",
                            output_mint=contract,
                            amount=100_000_000  # 0.1 SOL
                        )
                        if quote and 'outAmount' in quote:
                            token_amount = int(quote['outAmount'])
                            # Fetch token decimals via a minimal RPC (reuse V1 heuristic 5 if unknown)
                            # For V2, assume 6 if not available; this only affects pre-price display
                            token_decimals = 6
                            price = 0.1 / (token_amount / (10 ** token_decimals))
                            self.logger.info(f"Solana price from Jupiter fallback: {price} SOL per token")
                    except Exception:
                        price = None
                executor = self.sol_executor
                venue = None
            else:
                self.logger.info(f"Trader V2: unsupported chain {chain} in V2")
                return None

            if not balance or float(balance) <= 0:
                self.logger.error(f"Trader V2: No {native_label} balance")
                return None
            alloc_native = (allocation_pct * float(balance)) / 100.0
            if alloc_native <= 0:
                self.logger.error("Trader V2: Allocation native is zero")
                return None
            if not price:
                self.logger.warning("Trader V2: Could not pre-price token; aborting to ensure entries")
                return None

            position_id = f"{ticker}_{chain}_{int(datetime.now(timezone.utc).timestamp())}"

            # Create position
            # Extract source tweet URL for position storage
            source_tweet_url = None
            signal_pack = decision.get('signal_pack', {})
            if signal_pack:
                source_tweet_url = (
                    signal_pack.get('source_tweet_url') or
                    signal_pack.get('tweet_url') or
                    signal_pack.get('url') or
                    signal_pack.get('message', {}).get('url')
                )
            
            # Also try to get from module_intelligence if available
            if not source_tweet_url:
                module_intelligence = decision.get('module_intelligence', {})
                social_signal = module_intelligence.get('social_signal', {})
                message = social_signal.get('message', {})
                source_tweet_url = message.get('url')
            
            position = {
                'id': position_id,
                'token_chain': chain,
                'token_contract': contract,
                'token_ticker': ticker,
                'book_id': decision.get('id'),
                'status': 'active',
                'total_allocation_pct': allocation_pct,
                'current_invested_usd': 0.0,
                'total_quantity': 0.0,
                'curator_sources': decision.get('content', {}).get('curator_id'),
                'source_tweet_url': source_tweet_url,  # Store for sell notifications
                'first_entry_timestamp': datetime.now(timezone.utc).isoformat()
            }
            if not self.repo.create_position(position):
                self.logger.error("Trader V2: Failed to create position")
                return None

            # Entries (3-way split by amount)
            e_amt = alloc_native / 3.0
            entries = EntryExitPlanner.build_entries(price, alloc_native)
            # Mark pricing unit explicitly to avoid ambiguity in storage/inspection
            for entry in entries:
                entry['unit'] = 'NATIVE'
                entry['native_symbol'] = native_label
            self.repo.update_entries(position_id, entries)

            # Execute first entry on-chain
            tx_hash = None
            if chain == 'bsc' and executor:
                tx_hash = executor.execute_buy(contract, e_amt, venue=venue)
            elif chain == 'base' and executor:
                tx_hash = executor.execute_buy(contract, e_amt, venue=venue)
            elif chain == 'ethereum' and executor:
                tx_hash = executor.execute_buy(contract, e_amt)
            elif chain == 'solana' and executor:
                tx_hash = await executor.execute_buy(contract, e_amt)
            if tx_hash:
                entries[0]['status'] = 'executed'
                entries[0]['executed_at'] = datetime.now(timezone.utc).isoformat()
                entries[0]['tx_hash'] = tx_hash
                entries[0]['tokens_bought'] = e_amt / price
                self.repo.update_entries(position_id, entries)
                
                # Update average entry price after first entry execution
                await self._update_avg_entry_price(position_id)
                
                # Detect tax tokens after successful buy
                await self._detect_and_update_tax_token(contract, e_amt, price, chain)
                
                # Update total_quantity with actual tokens bought
                position = self.repo.get_position(position_id)
                if position:
                    position['total_quantity'] = position.get('total_quantity', 0) + (e_amt / price)
                    position['last_activity_timestamp'] = datetime.now(timezone.utc).isoformat()
                    self.repo.update_position(position_id, position)
                
                # Send Telegram buy signal notification
                await self._send_buy_notification(
                    token_ticker=ticker,
                    token_contract=contract,
                    chain=chain,
                    amount_native=e_amt,
                    price=price,
                    tx_hash=tx_hash,
                    allocation_pct=allocation_pct,
                    decision=decision
                )

            # Exits (staged) - use actual tokens bought, not theoretical
            actual_tokens = e_amt / price if tx_hash else 0
            exits = EntryExitPlanner.build_exits(price, actual_tokens * price)  # Use actual tokens
            self.repo.update_exits(position_id, exits)
            
            # Store exit rules that match the exit strategy
            exit_rules = {
                'strategy': 'staged',
                'stages': [
                    {'gain_pct': 30, 'exit_pct': 30, 'executed': False},
                    {'gain_pct': 200, 'exit_pct': 30, 'executed': False},
                    {'gain_pct': 300, 'exit_pct': 30, 'executed': False}
                ]
            }
            self.repo.update_exit_rules(position_id, exit_rules)

            if not tx_hash:
                self.logger.error("Trader V2: No tx_hash returned; marking execution as failed")
                return None
            return {
                'position_id': position_id,
                'token_ticker': ticker,
                'allocation_pct': allocation_pct,
                'allocation_native': alloc_native,
                'current_price': price,
                'status': 'active'
            }

        except Exception as e:
            self.logger.error(f"Trader V2: execute_decision error: {e}")
            return None

    def _resolve_bsc_venue(self, token_address: str) -> Optional[Dict[str, Any]]:
        try:
            import requests
            r = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{token_address}", timeout=8)
            if not r.ok:
                return None
            pairs = (r.json() or {}).get('pairs') or []
            bsc_pairs = [p for p in pairs if p.get('chainId') == 'bsc']
            cands = [p for p in bsc_pairs if p.get('quoteToken', {}).get('symbol') in ('WBNB','BNB')]
            if not cands:
                return None
            cands.sort(key=lambda p: (p.get('liquidity', {}) .get('usd') or 0), reverse=True)
            chosen = cands[0]
            return {'dex': chosen.get('dexId'), 'pair': chosen.get('pairAddress')}
        except Exception:
            return None

    def _resolve_base_venue(self, token_address: str) -> Optional[Dict[str, Any]]:
        try:
            import requests
            r = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{token_address}", timeout=8)
            if not r.ok:
                return None
            pairs = (r.json() or {}).get('pairs') or []
            base_pairs = [p for p in pairs if p.get('chainId') == 'base']
            
            # Get all WETH pairs across all DEXs and sort by liquidity
            weth_pairs = [p for p in base_pairs if p.get('quoteToken',{}).get('symbol') == 'WETH']
            if not weth_pairs:
                return None
            
            # Sort by liquidity (highest first) and return the best pair
            weth_pairs.sort(key=lambda p: (p.get('liquidity',{}) .get('usd') or 0), reverse=True)
            best_pair = weth_pairs[0]
            return {'dex': best_pair.get('dexId'), 'pair': best_pair.get('pairAddress')}
        except Exception:
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
            position = self.repo.get_position(position_id)
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
            requested_tokens = target_exit.get('tokens', 0)
            target_price = target_exit.get('price', 0)
            
            if requested_tokens <= 0:
                self.logger.error(f"Invalid token quantity for exit: {requested_tokens}")
                return False
            
            # Step 1: Check actual wallet balance and reconcile
            self.logger.info(f"Checking wallet balance for {ticker}...")
            try:
                wallet_balance = await self.wallet_manager.get_balance(chain, contract)
                wallet_balance_float = float(wallet_balance) if wallet_balance else 0
                self.logger.info(f"Wallet balance: {wallet_balance_float:.6f} tokens")
                self.logger.info(f"Database total_quantity: {position.get('total_quantity', 0):.6f} tokens")
                
                # Reconcile if there's a discrepancy
                if abs(wallet_balance_float - position.get('total_quantity', 0)) > 0.000001:
                    self.logger.warning(f"Wallet/database mismatch detected! Reconciling...")
                    position['total_quantity'] = wallet_balance_float
                    # Recalculate other totals from entry history
                    await self._recalculate_position_totals(position)
                    self.repo.update_position(position_id, position)
                    self.logger.info(f"✅ Database reconciled with wallet balance")
            except Exception as e:
                self.logger.error(f"Error checking wallet balance: {e}")
                # Continue with database value as fallback
                wallet_balance_float = position.get('total_quantity', 0)
            
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
            if chain == 'base' and self.base_executor:
                tx_hash = self.base_executor.execute_sell(contract, actual_sell_amount, target_price)
            elif chain == 'bsc' and self.bsc_executor:
                tx_hash = self.bsc_executor.execute_sell(contract, actual_sell_amount, target_price)
            elif chain == 'ethereum' and self.eth_executor:
                tx_hash = self.eth_executor.execute_sell(contract, actual_sell_amount, target_price)
            elif chain == 'solana' and self.sol_executor:
                tx_hash = await self.sol_executor.execute_sell(contract, actual_sell_amount, target_price)
            else:
                self.logger.error(f"No executor available for chain {chain}")
                return False
            
            if tx_hash:
                # Wait for transaction confirmation before marking as executed
                if chain in ['bsc', 'base', 'ethereum']:
                    # For EVM chains, wait for transaction confirmation
                    confirmed = await self._wait_for_transaction_confirmation(tx_hash, chain)
                    if not confirmed:
                        self.logger.error(f"Exit {exit_number} transaction not confirmed: {tx_hash}")
                        return False
                
                # Update exit with transaction details only after confirmation
                target_exit['status'] = 'executed'
                target_exit['tx_hash'] = tx_hash
                target_exit['executed_at'] = datetime.now(timezone.utc).isoformat()
                target_exit['actual_tokens_sold'] = actual_sell_amount  # Track actual amount
                
                # Update position in database
                self.repo.update_exits(position_id, exits)
                
                # Calculate and update P&L
                self._update_position_pnl(position_id, target_exit)
                
                # Send Telegram sell signal notification
                await self._send_sell_notification_for_exit(
                    position_id=position_id,
                    exit_number=exit_number,
                    tokens_sold=actual_sell_amount,
                    sell_price=target_price,
                    tx_hash=tx_hash,
                    chain=chain,
                    contract=contract
                )
                
                self.logger.info(f"✅ Exit {exit_number} executed successfully: {tx_hash}")
                return True
            else:
                self.logger.error(f"❌ Exit {exit_number} failed - no transaction hash")
                return False
                
        except Exception as e:
            self.logger.error(f"Error executing exit {exit_number} for position {position_id}: {e}")
            return False
    
    def _update_position_pnl(self, position_id: str, executed_exit: Dict[str, Any]):
        """Update position P&L after successful exit"""
        try:
            # Get current position
            position = self.repo.get_position(position_id)
            if not position:
                return
            
            # Calculate exit value in ETH - use actual tokens sold, not requested
            tokens_sold = executed_exit.get('actual_tokens_sold', executed_exit.get('tokens', 0))
            exit_price_eth = executed_exit.get('price', 0)
            exit_value_eth = tokens_sold * exit_price_eth
            
            # Get current ETH price for USD conversion (simplified)
            # In a real implementation, you'd fetch current ETH/USD price
            eth_usd_price = 4180  # Approximate current ETH price
            exit_value_usd = exit_value_eth * eth_usd_price
            
            # Update position totals
            current_quantity = position.get('total_quantity', 0)
            new_quantity = current_quantity - tokens_sold
            
            # Calculate P&L (simplified - would need entry price for accurate calculation)
            current_pnl_usd = position.get('total_pnl_usd', 0) + exit_value_usd
            total_allocation_usd = position.get('total_allocation_usd', 0)
            pnl_pct = (current_pnl_usd / total_allocation_usd * 100) if total_allocation_usd > 0 else 0
            
            # Update position
            position['total_quantity'] = new_quantity
            position['total_pnl_usd'] = current_pnl_usd
            position['total_pnl_pct'] = pnl_pct
            position['last_activity_timestamp'] = datetime.now(timezone.utc).isoformat()
            
            # Save to database
            self.repo.update_position(position_id, position)
            
        except Exception as e:
            self.logger.error(f"Error updating P&L for position {position_id}: {e}")

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
            total_cost = sum(e['price'] * e['tokens_bought'] for e in executed_entries)
            total_tokens = sum(e['tokens_bought'] for e in executed_entries)
            
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
                    cost_eth = entry.get('cost_eth', 0)
                    cost_usd = entry.get('cost_usd', 0)

                    total_cost_native += cost_eth
                    total_cost_usd += cost_usd

            # Get actual wallet balance for total_quantity
            try:
                chain = position.get('token_chain', 'ethereum')
                contract = position.get('token_contract')
                if contract:
                    wallet_balance = await self.wallet_manager.get_balance(chain, contract)
                    total_tokens = float(wallet_balance) if wallet_balance else 0
                else:
                    total_tokens = 0
            except Exception as e:
                self.logger.error(f"Error getting wallet balance for recalculation: {e}")
                # Fallback to calculating from entries
                total_tokens = sum(entry.get('tokens_bought', 0) for entry in entries if entry.get('status') == 'executed')

            # Update position totals
            position['total_quantity'] = total_tokens
            position['total_cost_native'] = total_cost_native
            position['total_allocation_usd'] = total_cost_usd

            # Calculate average entry price
            if total_tokens > 0:
                position['avg_entry_price'] = total_cost_native / total_tokens
            else:
                position['avg_entry_price'] = 0

            # Reset P&L (will be updated by _update_position_pnl after sell)
            position['total_pnl_usd'] = 0
            position['total_pnl_pct'] = 0

            self.logger.info(f"Recalculated position totals: {total_tokens} tokens, {total_cost_native:.6f} native")

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
                return
            
            if result:
                # Mark entry as executed
                self.repo.mark_entry_executed(position_id, entry_number, result)
                # Update average entry price after entry execution
                await self._update_avg_entry_price(position_id)
                self.logger.info(f"Entry {entry_number} executed successfully: {result}")
            else:
                self.logger.error(f"Entry {entry_number} execution failed")
                
        except Exception as e:
            self.logger.error(f"Error executing entry {entry_number} for position {position_id}: {e}")

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
                        # Mark entry as executed only after confirmation
                        self.repo.mark_entry_executed(position_id, entry_number, result)
                        # Update average entry price after entry execution
                        await self._update_avg_entry_price(position_id)
                        self.logger.info(f"Entry {entry_number} executed and confirmed: {result}")
                        return True
                    else:
                        self.logger.error(f"Entry {entry_number} transaction not confirmed: {result}")
                        return False
                else:
                    # For Solana, assume immediate confirmation
                    self.repo.mark_entry_executed(position_id, entry_number, result)
                    # Update average entry price after entry execution
                    await self._update_avg_entry_price(position_id)
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
        """Send Telegram buy signal notification"""
        if not self.telegram_notifier:
            return
        
        try:
            # Extract source tweet URL if available
            source_tweet_url = None
            signal_pack = decision.get('signal_pack', {})
            if signal_pack:
                # Try to get tweet URL from various possible locations
                source_tweet_url = (
                    signal_pack.get('source_tweet_url') or
                    signal_pack.get('tweet_url') or
                    signal_pack.get('url') or
                    signal_pack.get('message', {}).get('url')
                )
            
            # Also try to get from module_intelligence if available
            if not source_tweet_url:
                module_intelligence = decision.get('module_intelligence', {})
                social_signal = module_intelligence.get('social_signal', {})
                message = social_signal.get('message', {})
                source_tweet_url = message.get('url')
            
            await self.telegram_notifier.send_buy_signal(
                token_ticker=token_ticker,
                token_contract=token_contract,
                chain=chain,
                amount_native=amount_native,
                price=price,
                tx_hash=tx_hash,
                source_tweet_url=source_tweet_url,
                allocation_pct=allocation_pct
            )
            
            self.logger.info(f"Buy signal notification sent for {token_ticker}")
            
        except Exception as e:
            self.logger.error(f"Failed to send buy notification: {e}")

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
        """Send Telegram sell signal notification"""
        if not self.telegram_notifier:
            return
        
        try:
            # Try to get source tweet URL from position data
            source_tweet_url = None
            if position_id:
                position = self.repo.get_position(position_id)
                if position:
                    # Try to extract from position metadata or related data
                    source_tweet_url = position.get('source_tweet_url')
            
            await self.telegram_notifier.send_sell_signal(
                token_ticker=token_ticker,
                token_contract=token_contract,
                chain=chain,
                tokens_sold=tokens_sold,
                sell_price=sell_price,
                tx_hash=tx_hash,
                profit_pct=profit_pct,
                profit_usd=profit_usd,
                total_profit_usd=total_profit_usd,
                source_tweet_url=source_tweet_url
            )
            
            self.logger.info(f"Sell signal notification sent for {token_ticker}")
            
        except Exception as e:
            self.logger.error(f"Failed to send sell notification: {e}")

    async def _send_sell_notification_for_exit(self,
                                             position_id: str,
                                             exit_number: int,
                                             tokens_sold: float,
                                             sell_price: float,
                                             tx_hash: str,
                                             chain: str,
                                             contract: str) -> None:
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
            
            # Calculate profit metrics
            profit_pct = None
            profit_usd = None
            total_profit_usd = None
            
            # Try to get profit data from the position
            if position.get('total_pnl_pct') is not None:
                profit_pct = position.get('total_pnl_pct')
            if position.get('total_pnl_usd') is not None:
                total_profit_usd = position.get('total_pnl_usd')
            
            # For individual exit profit, we'd need to calculate based on entry price
            # This is a simplified version - you might want to enhance this
            avg_entry_price = position.get('avg_entry_price')
            if avg_entry_price and avg_entry_price > 0:
                exit_profit_pct = ((sell_price - avg_entry_price) / avg_entry_price) * 100
                exit_profit_usd = (sell_price - avg_entry_price) * tokens_sold
                profit_pct = exit_profit_pct
                profit_usd = exit_profit_usd
            
            await self.telegram_notifier.send_sell_signal(
                token_ticker=token_ticker,
                token_contract=contract,
                chain=chain,
                tokens_sold=tokens_sold,
                sell_price=sell_price,
                tx_hash=tx_hash,
                profit_pct=profit_pct,
                profit_usd=profit_usd,
                total_profit_usd=total_profit_usd,
                source_tweet_url=position.get('source_tweet_url')
            )
            
            self.logger.info(f"Sell signal notification sent for {token_ticker} exit {exit_number}")
            
        except Exception as e:
            self.logger.error(f"Failed to send sell notification for exit: {e}")


