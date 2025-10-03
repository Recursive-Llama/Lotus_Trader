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
                'total_quantity': 0.0,
                'total_tokens_bought': 0.0,  # Track total tokens bought
                'total_tokens_sold': 0.0,    # Track total tokens sold
                'total_investment_native': 0.0,  # Track total native currency invested
                'total_extracted_native': 0.0,   # Track total native currency extracted
                'total_pnl_native': 0.0,     # Track total P&L in native currency
                'curator_sources': decision.get('content', {}).get('curator_id'),
                'source_tweet_url': source_tweet_url,  # Store for sell notifications
                'first_entry_timestamp': datetime.now(timezone.utc).isoformat()
            }
            if not self.repo.create_position(position):
                self.logger.error("Trader V2: Failed to create position")
                return None

            # Update P&L for all positions after creating new position
            await self._update_all_positions_pnl()

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
                # Calculate cost tracking
                cost_native = e_amt
                cost_usd = 0
                if price_info and 'price_usd' in price_info:
                    # Calculate USD cost based on token price
                    token_price_usd = price_info['price_usd']
                    cost_usd = (e_amt / price) * token_price_usd
                
                tokens_bought = e_amt / price
                
                # Use enhanced mark_entry_executed method for consistent tracking
                self.repo.mark_entry_executed(
                    position_id=position_id,
                    entry_number=1,
                    tx_hash=tx_hash,
                    cost_native=cost_native,
                    cost_usd=cost_usd,
                    tokens_bought=tokens_bought
                )
                
                # Update totals and calculated fields
                await self._update_tokens_bought(position_id, tokens_bought)
                await self._update_total_investment_native(position_id, e_amt)
                await self._update_position_pnl(position_id)
                await self._recalculate_exits_after_entry(position_id)
                
                # Detect tax tokens after successful buy
                await self._detect_and_update_tax_token(contract, e_amt, price, chain)
                
                # Set total_quantity immediately from trade execution and schedule reconciliation
                await self._set_quantity_from_trade(position_id, tokens_bought)
                
                # Update last activity timestamp
                position = self.repo.get_position(position_id)
                if position:
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

            # Store exit rules from config
            exit_rules = self._build_exit_rules_from_config()
            self.repo.update_exit_rules(position_id, exit_rules)
            
            # Store trend exit rules from config
            trend_exit_rules = self._build_trend_exit_rules_from_config()
            self.repo.update_trend_exit_rules(position_id, trend_exit_rules)

            # Exits (staged) - calculate exit prices based on current avg_entry_price
            exits = EntryExitPlanner.build_exits(exit_rules, price, price)  # Use exit_rules and current price as avg_entry_price
            self.repo.update_exits(position_id, exits)

            if not tx_hash:
                self.logger.error("Trader V2: No tx_hash returned; marking execution as failed")
                return None
            return {
                'position_id': position_id,
                'token_ticker': ticker,
                'allocation_pct': allocation_pct,
                'allocation_native': alloc_native,
                # Note: current_price is not stored in database - it comes from price oracle
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
            target_price = target_exit.get('price', 0)
            
            # Calculate tokens to sell from exit_pct and total_quantity
            exit_pct = target_exit.get('exit_pct', 0)
            total_quantity = position.get('total_quantity', 0)
            requested_tokens = total_quantity * (exit_pct / 100)
            
            if requested_tokens <= 0:
                self.logger.error(f"Invalid token quantity for exit: {requested_tokens} (exit_pct: {exit_pct}%, total_quantity: {total_quantity})")
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
                
                # Calculate exit value for cost tracking
                exit_value_native = actual_sell_amount * target_price
                exit_value_usd = 0
                
                # Get current price info for USD calculation
                if chain == 'bsc':
                    price_info = self.price_oracle.price_bsc(contract)
                elif chain == 'base':
                    price_info = self.price_oracle.price_base(contract)
                elif chain == 'ethereum':
                    price_info = self.price_oracle.price_eth(contract)
                elif chain == 'solana':
                    price_info = self.price_oracle.price_solana(contract)
                else:
                    price_info = None
                
                if price_info and 'price_usd' in price_info:
                    token_price_usd = price_info['price_usd']
                    exit_value_usd = actual_sell_amount * token_price_usd
                
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
                
                # Update totals and calculated fields
                await self._update_tokens_sold(position_id, actual_sell_amount)
                await self._update_total_extracted_native(position_id, exit_value_native)
                await self._update_position_pnl(position_id)
                await self._recalculate_exits_after_entry(position_id)
                
                # Set total_quantity immediately from trade execution and schedule reconciliation
                await self._set_quantity_from_trade(position_id, -actual_sell_amount)
                
                # Execute Lotus buyback for SOL exits
                buyback_result = await self._execute_lotus_buyback(exit_value_native, chain)
                
                # Send Telegram sell signal notification
                await self._send_sell_notification_for_exit(
                    position_id=position_id,
                    exit_number=exit_number,
                    tokens_sold=actual_sell_amount,
                    sell_price=target_price,
                    tx_hash=tx_hash,
                    chain=chain,
                    contract=contract,
                    buyback_result=buyback_result
                )
                
                # Update position in database LAST - after all other operations succeed
                # Save the entire updated position, not just the exits
                self.repo.update_position(position_id, position)
                
                self.logger.info(f"✅ Exit {exit_number} executed successfully: {tx_hash}")
                # Spawn trend batch funded by this standard exit (best-effort)
                try:
                    await self._spawn_trend_batch_after_standard_exit(position_id, target_exit)
                except Exception as te:
                    self.logger.error(f"Failed spawning trend batch after exit: {te}")
                return True
            else:
                self.logger.error(f"❌ Exit {exit_number} failed - no transaction hash")
                return False
                
        except Exception as e:
            self.logger.error(f"Error executing exit {exit_number} for position {position_id}: {e}")
            return False
    
    async def _get_current_price_from_db(self, token_contract: str, chain: str) -> Optional[float]:
        """Get current price from database"""
        try:
            # Get latest price from database
            result = self.repo.client.table('lowcap_price_data_1m').select(
                'price_native'
            ).eq('token_contract', token_contract).eq('chain', chain).order(
                'timestamp', desc=True
            ).limit(1).execute()
            
            if result.data:
                return float(result.data[0]['price_native'])
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting price from database: {e}")
            return None

    async def _update_position_pnl(self, position_id: str):
        """Update position P&L using database prices"""
        try:
            # Get current position
            position = self.repo.get_position(position_id)
            if not position:
                self.logger.error(f"Position {position_id} not found for P&L update")
                return
            
            # Get position details
            total_quantity = position.get('total_quantity', 0) or 0
            total_investment_native = position.get('total_investment_native', 0) or 0
            total_extracted_native = position.get('total_extracted_native', 0) or 0
            chain = position.get('token_chain', '').lower()
            contract = position.get('token_contract')
            
            if total_quantity <= 0 or not contract:
                # No tokens or no contract, P&L is extracted minus investment
                total_pnl_native = total_extracted_native - total_investment_native
                position['total_pnl_native'] = total_pnl_native
                position['total_pnl_usd'] = 0.0  # Will be calculated below
                position['total_pnl_pct'] = 0.0
                self.repo.update_position(position_id, position)
                self.logger.info(f"Updated P&L for {position_id}: {total_pnl_native:.8f} native (no tokens)")
                return
            
            # Get current token price from database (not API)
            current_token_price_native = await self._get_current_price_from_db(contract, chain)
            if current_token_price_native is None or current_token_price_native <= 0:
                self.logger.error(f"Could not get current native price for {contract} on {chain} from database")
                return
            
            # Calculate native P&L: (total_extracted_native + current_position_value) - total_investment_native
            current_position_value_native = total_quantity * current_token_price_native
            total_pnl_native = (total_extracted_native + current_position_value_native) - total_investment_native
            
            # Get native currency USD rate for conversion
            native_usd_rate = await self._get_native_usd_rate(chain)
            if native_usd_rate <= 0:
                self.logger.warning(f"Could not get native USD rate for {chain}, using 0 for USD P&L")
                total_pnl_usd = 0.0
            else:
                total_pnl_usd = total_pnl_native * native_usd_rate
            
            # Calculate P&L percentage (based on native investment)
            total_pnl_pct = 0
            if total_investment_native > 0:
                total_pnl_pct = (total_pnl_native / total_investment_native) * 100
            
            # Update position
            position['total_pnl_native'] = total_pnl_native
            position['total_pnl_usd'] = total_pnl_usd
            position['total_pnl_pct'] = total_pnl_pct
            position['last_activity_timestamp'] = datetime.now(timezone.utc).isoformat()
            
            # Save to database
            self.repo.update_position(position_id, position)
            self.logger.info(f"Updated P&L for {position_id}: {total_pnl_native:.8f} native, ${total_pnl_usd:.2f} USD ({total_pnl_pct:.2f}%)")
            
        except Exception as e:
            self.logger.error(f"Error updating P&L for {position_id}: {e}")

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


    async def _recalculate_exits_after_entry(self, position_id: str):
        """Recalculate exit prices based on new avg_entry_price after entry execution"""
        try:
            # Get current position
            position = self.repo.get_position(position_id)
            if not position:
                self.logger.error(f"Position {position_id} not found for exit recalculation")
                return
            
            # Get exit rules and current values
            exit_rules = position.get('exit_rules', {})
            avg_entry_price = position.get('avg_entry_price', 0)
            total_quantity = position.get('total_quantity', 0)
            
            if not exit_rules or not exit_rules.get('stages'):
                self.logger.warning(f"No exit rules found for position {position_id}")
                return
            
            if avg_entry_price <= 0:
                self.logger.warning(f"Invalid avg_entry_price for position {position_id}: {avg_entry_price}")
                return
            
            if total_quantity <= 0:
                self.logger.warning(f"No tokens in wallet for position {position_id}, but creating exits anyway for future entries")
                # Don't return - continue with recalculation even if no tokens
            
            # Reset all pending exits to 'pending' status (unexecute them)
            exits = position.get('exits', [])
            for exit_data in exits:
                if exit_data.get('status') == 'pending':
                    exit_data['status'] = 'pending'  # Keep as pending
                # Note: We don't reset executed exits - they stay executed
            
            # Generate new exits based on updated avg_entry_price
            new_exits = EntryExitPlanner.build_exits(exit_rules, avg_entry_price)
            
            # Update the exits array
            position['exits'] = new_exits
            self.repo.update_position(position_id, position)
            
            self.logger.info(f"Recalculated exits for {position_id} based on avg_entry_price: {avg_entry_price:.8f}")
            
        except Exception as e:
            self.logger.error(f"Error recalculating exits for position {position_id}: {e}")

    async def _spawn_trend_batch_after_standard_exit(self, position_id: str, standard_exit: Dict[str, Any]):
        """Create trend_entries batch after a standard exit executes.

        - Uses config trend_strategy
        - Funds from standard_exit['native_amount']
        - Prices referenced off standard_exit['price']
        - Writes arrays to position: trend_entries (append)
        - Trend exits are deferred and created only after first trend entry executes
        """
        try:
            position = self.repo.get_position(position_id)
            if not position:
                return

            exit_price = float(standard_exit.get('price') or 0.0)
            # Try multiple possible field names for native amount
            native_amount = float(
                standard_exit.get('cost_native') or 
                standard_exit.get('native_amount') or 
                standard_exit.get('tokens', 0) * exit_price or  # Calculate from tokens * price
                0.0
            )
            if exit_price <= 0 or native_amount <= 0:
                self.logger.warning("Trend batch spawn skipped: missing exit price or native amount")
                return

            # Build batch
            batch_id = f"trend-{position_id}-{int(datetime.now(timezone.utc).timestamp())}"
            source_exit_id = str(standard_exit.get('exit_number'))

            trend_entries = EntryExitPlanner.build_trend_entries_from_standard_exit(
                exit_price=exit_price,
                exit_native_amount=native_amount,
                source_exit_id=source_exit_id,
                batch_id=batch_id,
            )
            # Append to arrays (only entries now; exits will be created after first entry executes)
            existing_trend_entries = position.get('trend_entries', []) or []
            existing_trend_entries.extend(trend_entries)

            self.repo.update_trend_entries(position_id, existing_trend_entries)
            self.logger.info(f"Spawned trend batch {batch_id} with {len(trend_entries)} entries (exits deferred)")
        except Exception as e:
            self.logger.error(f"Error spawning trend batch: {e}")

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

            # Note: total_quantity is now updated from wallet balance via _update_total_quantity_from_wallet()

            # Calculate average entry price
            if total_tokens > 0:
                position['avg_entry_price'] = total_cost_native / total_tokens
            else:
                position['avg_entry_price'] = 0

            # Do not reset P&L here; it will be updated by _update_position_pnl

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
                # Get current price info for cost calculation
                chain = position.get('token_chain', '').lower()
                contract = position.get('token_contract')
                
                # Calculate cost tracking
                cost_native = amount
                cost_usd = 0
                tokens_bought = 0
                
                # Get price info for USD calculation
                if chain == 'bsc':
                    price_info = self.price_oracle.price_bsc(contract)
                elif chain == 'base':
                    price_info = self.price_oracle.price_base(contract)
                elif chain == 'ethereum':
                    price_info = self.price_oracle.price_eth(contract)
                elif chain == 'solana':
                    price_info = self.price_oracle.price_solana(contract)
                else:
                    price_info = None
                
                if price_info and 'price_native' in price_info and 'price_usd' in price_info:
                    price = price_info['price_native']
                    token_price_usd = price_info['price_usd']
                    tokens_bought = amount / price
                    cost_usd = tokens_bought * token_price_usd
                
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
                await self._recalculate_exits_after_entry(position_id)
                
                # Set total_quantity immediately from trade execution and schedule reconciliation
                await self._set_quantity_from_trade(position_id, tokens_bought)
                
                # Send notification for additional entries
                await self._send_additional_entry_notification(
                    position_id=position_id,
                    entry_number=entry_number,
                    tx_hash=result,
                    amount_native=amount,
                    cost_usd=cost_usd
                )
                
                self.logger.info(f"Entry {entry_number} executed successfully: {result}")
            else:
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
                        
                        # Get price info for USD calculation
                        if chain == 'bsc':
                            price_info = self.price_oracle.price_bsc(contract)
                        elif chain == 'base':
                            price_info = self.price_oracle.price_base(contract)
                        elif chain == 'ethereum':
                            price_info = self.price_oracle.price_eth(contract)
                        elif chain == 'solana':
                            price_info = self.price_oracle.price_solana(contract)
                        else:
                            price_info = None
                        
                        if price_info and 'price_native' in price_info and 'price_usd' in price_info:
                            price = price_info['price_native']
                            token_price_usd = price_info['price_usd']
                            tokens_bought = amount / price
                            cost_usd = tokens_bought * token_price_usd
                        
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
                        await self._recalculate_exits_after_entry(position_id)
                        
                        # Set total_quantity immediately from trade execution and schedule reconciliation
                        await self._set_quantity_from_trade(position_id, tokens_bought)
                        
                        # Send notification for additional entries
                        await self._send_additional_entry_notification(
                            position_id=position_id,
                            entry_number=entry_number,
                            tx_hash=result,
                            amount_native=amount,
                            cost_usd=cost_usd
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
                    
                    # Get price info for USD calculation
                    if chain == 'solana':
                        price_info = self.price_oracle.price_solana(contract)
                    else:
                        price_info = None
                    
                    if price_info and 'price_native' in price_info and 'price_usd' in price_info:
                        price = price_info['price_native']
                        token_price_usd = price_info['price_usd']
                        tokens_bought = amount / price
                        cost_usd = tokens_bought * token_price_usd
                    
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
                    await self._recalculate_exits_after_entry(position_id)
                    
                    # Set total_quantity immediately from trade execution and schedule reconciliation
                    await self._set_quantity_from_trade(position_id, tokens_bought)
                    
                    # Send notification for additional entries
                    await self._send_additional_entry_notification(
                        position_id=position_id,
                        entry_number=entry_number,
                        tx_hash=result,
                        amount_native=amount,
                        cost_usd=cost_usd
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
            
            # Calculate USD amount for notification
            amount_usd = None
            if chain == 'bsc':
                price_info = self.price_oracle.price_bsc(token_contract)
            elif chain == 'base':
                price_info = self.price_oracle.price_base(token_contract)
            elif chain == 'ethereum':
                price_info = self.price_oracle.price_eth(token_contract)
            elif chain == 'solana':
                price_info = self.price_oracle.price_solana(token_contract)
            else:
                price_info = None
            
            if price_info and 'price_usd' in price_info:
                native_usd_rate = await self._get_native_usd_rate(chain)
                if native_usd_rate > 0:
                    amount_usd = amount_native * native_usd_rate
            
            await self.telegram_notifier.send_buy_signal(
                token_ticker=token_ticker,
                token_contract=token_contract,
                chain=chain,
                amount_native=amount_native,
                price=price,
                tx_hash=tx_hash,
                source_tweet_url=source_tweet_url,
                allocation_pct=allocation_pct,
                amount_usd=amount_usd
            )
            
            self.logger.info(f"Buy signal notification sent for {token_ticker}")
            
        except Exception as e:
            self.logger.error(f"Failed to send buy notification: {e}")

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
            
            # Get position context for enhanced notification
            remaining_tokens = None
            position_value = None
            total_pnl_pct = None
            profit_native = None
            
            if position_id:
                position = self.repo.get_position(position_id)
                if position:
                    remaining_tokens = position.get('total_quantity', 0) - tokens_sold
                    total_pnl_pct = position.get('total_pnl_pct', 0)
                    
                    # Calculate position value
                    if remaining_tokens > 0:
                        current_price = await self._get_current_price_from_db(token_contract, chain)
                        if current_price:
                            position_value = remaining_tokens * current_price
                    
                    # Calculate native P&L for this exit
                    if profit_usd and chain in ['bsc', 'base', 'ethereum']:
                        native_usd_rate = await self._get_native_usd_rate(chain)
                        if native_usd_rate > 0:
                            profit_native = profit_usd / native_usd_rate
            
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
                source_tweet_url=source_tweet_url,
                remaining_tokens=remaining_tokens,
                position_value=position_value,
                total_pnl_pct=total_pnl_pct,
                profit_native=profit_native
            )
            
            self.logger.info(f"Sell signal notification sent for {token_ticker}")
            
        except Exception as e:
            self.logger.error(f"Failed to send sell notification: {e}")

    async def _send_trend_entry_notification(self,
                                           position_id: str,
                                           entry_number: int,
                                           tx_hash: str,
                                           amount_native: float,
                                           price: float,
                                           dip_pct: float,
                                           batch_id: str) -> None:
        """Send notification for trend entries (dip buys)"""
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
            source_tweet_url = position.get('source_tweet_url')
            
            # Calculate USD amount
            amount_usd = None
            if chain in ['bsc', 'base', 'ethereum']:
                native_usd_rate = await self._get_native_usd_rate(chain)
                if native_usd_rate > 0:
                    amount_usd = amount_native * native_usd_rate
            
            await self.telegram_notifier.send_trend_entry_notification(
                token_ticker=token_ticker,
                token_contract=token_contract,
                chain=chain,
                amount_native=amount_native,
                price=price,
                tx_hash=tx_hash,
                dip_pct=dip_pct,
                batch_id=batch_id,
                source_tweet_url=source_tweet_url,
                amount_usd=amount_usd
            )
            
            self.logger.info(f"Trend entry notification sent for {token_ticker} batch {batch_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to send trend entry notification: {e}")

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
        """Send notification for trend exits"""
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
            source_tweet_url = position.get('source_tweet_url')
            
            # Calculate native P&L
            profit_native = None
            if profit_usd and chain in ['bsc', 'base', 'ethereum']:
                native_usd_rate = await self._get_native_usd_rate(chain)
                if native_usd_rate > 0:
                    profit_native = profit_usd / native_usd_rate
            
            await self.telegram_notifier.send_trend_exit_notification(
                token_ticker=token_ticker,
                token_contract=token_contract,
                chain=chain,
                tokens_sold=tokens_sold,
                sell_price=sell_price,
                tx_hash=tx_hash,
                gain_pct=gain_pct,
                batch_id=batch_id,
                profit_pct=profit_pct,
                profit_usd=profit_usd,
                profit_native=profit_native,
                source_tweet_url=source_tweet_url
            )
            
            self.logger.info(f"Trend exit notification sent for {token_ticker} batch {batch_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to send trend exit notification: {e}")

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
            
            # Calculate dollar value of tokens sold in this exit
            # sell_price is always in native token (BNB, ETH, SOL) - need to convert to USD
            native_usd_rate = await self._get_native_usd_rate(chain)
            if native_usd_rate > 0:
                sell_price_usd = sell_price * native_usd_rate
                tokens_sold_value_usd = tokens_sold * sell_price_usd
            else:
                # Fallback: use sell_price as-is (might be wrong but better than error)
                tokens_sold_value_usd = tokens_sold * sell_price
            
            # Get position context for enhanced notification
            remaining_tokens = position.get('total_quantity', 0) - tokens_sold
            position_value = None
            profit_native = None
            
            # Calculate position value
            if remaining_tokens > 0:
                current_price = None
                if chain == 'bsc':
                    price_info = self.price_oracle.price_bsc(contract)
                elif chain == 'base':
                    price_info = self.price_oracle.price_base(contract)
                elif chain == 'ethereum':
                    price_info = self.price_oracle.price_eth(contract)
                elif chain == 'solana':
                    price_info = self.price_oracle.price_solana(contract)
                
                if price_info and 'price_usd' in price_info:
                    current_price = price_info['price_usd']
                
                if current_price:
                    position_value = remaining_tokens * current_price
            
            # Calculate native P&L for this exit
            if profit_usd and chain in ['bsc', 'base', 'ethereum']:
                native_usd_rate = await self._get_native_usd_rate(chain)
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
        try:
            position = self.repo.get_position(position_id)
            if not position:
                self.logger.error(f"Position {position_id} not found for token tracking update")
                return False
            
            # Add tokens bought to total (handle None values)
            current_total = position.get('total_tokens_bought', 0.0) or 0.0
            new_total = current_total + tokens_bought
            position['total_tokens_bought'] = new_total
            
            # Update position in database
            success = self.repo.update_position(position_id, position)
            if success:
                self.logger.info(f"Updated total_tokens_bought for {position_id}: {current_total:.8f} -> {new_total:.8f} (+{tokens_bought:.8f})")
            else:
                self.logger.error(f"Failed to update total_tokens_bought for position {position_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error updating total_tokens_bought for position {position_id}: {e}")
            return False
    
    async def _update_tokens_sold(self, position_id: str, tokens_sold: float) -> bool:
        """Update total_tokens_sold when an exit is executed"""
        try:
            position = self.repo.get_position(position_id)
            if not position:
                self.logger.error(f"Position {position_id} not found for token tracking update")
                return False
            
            # Add tokens sold to total (handle None values)
            current_total = position.get('total_tokens_sold', 0.0) or 0.0
            new_total = current_total + tokens_sold
            position['total_tokens_sold'] = new_total
            
            # Update position in database
            success = self.repo.update_position(position_id, position)
            if success:
                self.logger.info(f"Updated total_tokens_sold for {position_id}: {current_total:.8f} -> {new_total:.8f} (+{tokens_sold:.8f})")
            else:
                self.logger.error(f"Failed to update total_tokens_sold for position {position_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error updating total_tokens_sold for position {position_id}: {e}")
            return False
    
    async def _update_total_investment_native(self, position_id: str, amount_native: float) -> bool:
        """Update total_investment_native when an entry is executed"""
        try:
            position = self.repo.get_position(position_id)
            if not position:
                self.logger.error(f"Position {position_id} not found for investment tracking update")
                return False
            
            # Add native amount invested to total (handle None values)
            current_total = position.get('total_investment_native', 0.0) or 0.0
            new_total = current_total + amount_native
            position['total_investment_native'] = new_total
            
            # Calculate avg_entry_price from totals
            total_tokens = position.get('total_tokens_bought', 0.0) or 0.0
            if total_tokens > 0:
                position['avg_entry_price'] = new_total / total_tokens
            else:
                position['avg_entry_price'] = 0.0
            
            # Update position in database
            success = self.repo.update_position(position_id, position)
            if success:
                self.logger.info(f"Updated total_investment_native for {position_id}: {current_total:.8f} -> {new_total:.8f} (+{amount_native:.8f})")
                self.logger.info(f"Calculated avg_entry_price: {position['avg_entry_price']:.8f}")
            else:
                self.logger.error(f"Failed to update total_investment_native for position {position_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error updating total_investment_native for position {position_id}: {e}")
            return False
    
    async def _update_total_extracted_native(self, position_id: str, amount_native: float) -> bool:
        """Update total_extracted_native when an exit is executed"""
        try:
            position = self.repo.get_position(position_id)
            if not position:
                self.logger.error(f"Position {position_id} not found for extraction tracking update")
                return False
            
            # Add native amount extracted to total (handle None values)
            current_total = position.get('total_extracted_native', 0.0) or 0.0
            new_total = current_total + amount_native
            position['total_extracted_native'] = new_total
            
            # Calculate avg_exit_price from totals
            total_sold = position.get('total_tokens_sold', 0.0) or 0.0
            if total_sold > 0:
                position['avg_exit_price'] = new_total / total_sold
            else:
                position['avg_exit_price'] = 0.0
            
            # Update position in database
            success = self.repo.update_position(position_id, position)
            if success:
                self.logger.info(f"Updated total_extracted_native for {position_id}: {current_total:.8f} -> {new_total:.8f} (+{amount_native:.8f})")
                self.logger.info(f"Calculated avg_exit_price: {position['avg_exit_price']:.8f}")
            else:
                self.logger.error(f"Failed to update total_extracted_native for position {position_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error updating total_extracted_native for position {position_id}: {e}")
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

    async def _update_total_quantity_from_wallet(self, position_id: str) -> bool:
        """Update total_quantity from wallet balance with discrepancy logging"""
        try:
            position = self.repo.get_position(position_id)
            if not position:
                self.logger.error(f"Position {position_id} not found for quantity update")
                return False
            
            token_contract = position.get('token_contract')
            token_chain = position.get('token_chain')
            if not token_contract or not token_chain:
                self.logger.error(f"Missing token_contract or token_chain for position {position_id}")
                return False
            
            # Get wallet balance
            wallet_balance = await self.wallet_manager.get_balance(token_chain, token_contract)
            wallet_balance_float = float(wallet_balance) if wallet_balance else 0.0
            
            # Calculate expected quantity from our trade records
            total_bought = position.get('total_tokens_bought', 0.0) or 0.0
            total_sold = position.get('total_tokens_sold', 0.0) or 0.0
            expected_quantity = total_bought - total_sold
            
            # Update total_quantity with wallet balance (source of truth)
            old_quantity = position.get('total_quantity', 0.0) or 0.0
            position['total_quantity'] = wallet_balance_float
            
            # Log discrepancy if found
            discrepancy = abs(expected_quantity - wallet_balance_float)
            if discrepancy > 0.000001:  # Tolerance for floating point precision
                self.logger.warning(f"Quantity discrepancy detected for {position_id}:")
                self.logger.warning(f"  Expected (bought-sold): {expected_quantity:.8f}")
                self.logger.warning(f"  Actual (wallet): {wallet_balance_float:.8f}")
                self.logger.warning(f"  Difference: {discrepancy:.8f}")
                self.logger.warning(f"  Possible causes: external trades, failed transactions, airdrops, tax burns")
            else:
                self.logger.info(f"Quantity verified for {position_id}: {wallet_balance_float:.8f} tokens")
            
            # Update position in database
            success = self.repo.update_position(position_id, position)
            if success:
                self.logger.info(f"Updated total_quantity for {position_id}: {old_quantity:.8f} -> {wallet_balance_float:.8f}")
            else:
                self.logger.error(f"Failed to update total_quantity for position {position_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error updating total_quantity from wallet for position {position_id}: {e}")
            return False

    async def _reconcile_wallet_quantity(self, position_id: str, expected_quantity: float) -> None:
        """Background reconciliation of wallet quantity with expected amount"""
        try:
            # Wait 45 seconds for transaction to confirm
            await asyncio.sleep(45)
            
            position = self.repo.get_position(position_id)
            if not position:
                self.logger.error(f"Position {position_id} not found for reconciliation")
                return
            
            token_contract = position.get('token_contract')
            token_chain = position.get('token_chain')
            if not token_contract or not token_chain:
                self.logger.error(f"Missing contract or chain for position {position_id}")
                return
            
            # Get wallet balance
            wallet_balance = await self.wallet_manager.get_balance(token_chain, token_contract)
            wallet_balance_float = float(wallet_balance) if wallet_balance else 0.0
            
            # Calculate discrepancy percentage
            if expected_quantity > 0:
                discrepancy_pct = abs(wallet_balance_float - expected_quantity) / expected_quantity * 100
            else:
                discrepancy_pct = 100 if wallet_balance_float > 0 else 0
            
            # Only update if significant discrepancy (>1%)
            if discrepancy_pct > 1.0:
                self.logger.warning(f"Significant quantity discrepancy detected for {position_id}:")
                self.logger.warning(f"  Expected: {expected_quantity:.8f}")
                self.logger.warning(f"  Wallet: {wallet_balance_float:.8f}")
                self.logger.warning(f"  Discrepancy: {discrepancy_pct:.2f}%")
                
                # Update total_quantity to wallet balance
                position['total_quantity'] = wallet_balance_float
                success = self.repo.update_position(position_id, position)
                if success:
                    self.logger.info(f"Reconciled total_quantity for {position_id}: {expected_quantity:.8f} -> {wallet_balance_float:.8f}")
                else:
                    self.logger.error(f"Failed to reconcile position {position_id}")
            else:
                self.logger.info(f"Wallet reconciliation for {position_id}: quantities match (discrepancy: {discrepancy_pct:.2f}%)")
                
        except Exception as e:
            self.logger.error(f"Error in wallet reconciliation for {position_id}: {e}")

    async def _set_quantity_from_trade(self, position_id: str, tokens_bought: float) -> None:
        """Set total_quantity immediately from trade execution and schedule reconciliation"""
        try:
            position = self.repo.get_position(position_id)
            if not position:
                self.logger.error(f"Position {position_id} not found for quantity update")
                return
            
            # Set total_quantity immediately from trade execution
            old_quantity = position.get('total_quantity', 0.0) or 0.0
            new_quantity = old_quantity + tokens_bought
            position['total_quantity'] = new_quantity
            
            # Update position in database
            success = self.repo.update_position(position_id, position)
            if success:
                self.logger.info(f"Set total_quantity from trade for {position_id}: {old_quantity:.8f} -> {new_quantity:.8f} (+{tokens_bought:.8f})")
                
                # Schedule background reconciliation
                asyncio.create_task(self._reconcile_wallet_quantity(position_id, new_quantity))
                self.logger.info(f"Scheduled wallet reconciliation for {position_id} in 45 seconds")
            else:
                self.logger.error(f"Failed to update total_quantity for position {position_id}")
                
        except Exception as e:
            self.logger.error(f"Error setting quantity from trade for {position_id}: {e}")

    async def _execute_lotus_buyback(self, exit_value_native: float, chain: str) -> dict:
        """Execute Lotus token buyback for SOL exits"""
        try:
            # Only execute for SOL exits
            if chain.lower() != 'solana':
                return {'success': True, 'skipped': True, 'reason': 'Not a SOL exit'}
            
            # Get buyback config
            buyback_config = self.config.get('lotus_buyback', {})
            if not buyback_config.get('enabled', False):
                return {'success': True, 'skipped': True, 'reason': 'Buyback disabled'}
            
            # Calculate buyback amount
            percentage = buyback_config.get('percentage', 10.0)
            min_amount = buyback_config.get('min_amount_sol', 0.001)
            buyback_amount = float(exit_value_native) * (percentage / 100.0)
            
            # Check minimum threshold
            if buyback_amount < min_amount:
                self.logger.info(f"Lotus buyback skipped: {buyback_amount:.6f} SOL < {min_amount} SOL minimum")
                return {'success': True, 'skipped': True, 'reason': f'Below minimum threshold ({min_amount} SOL)'}
            
            # Get Lotus contract and holding wallet
            lotus_contract = buyback_config.get('lotus_contract')
            holding_wallet = buyback_config.get('holding_wallet')
            
            if not lotus_contract or not holding_wallet:
                self.logger.error("Lotus buyback config missing contract or holding wallet")
                return {'success': False, 'error': 'Missing config'}
            
            self.logger.info(f"Executing Lotus buyback: {buyback_amount:.6f} SOL -> {lotus_contract}")
            
            # Execute the buyback using existing Solana trading infrastructure
            # This will use the same Raydium/Jupiter integration as regular trades
            result = await self._execute_solana_swap(
                input_amount=buyback_amount,
                input_token='SOL',
                output_token=lotus_contract,
                slippage_pct=5.0  # 5% slippage for buyback
            )
            
            if result and result.get('success', False):
                # Send Lotus tokens to holding wallet
                lotus_amount = result.get('output_amount', 0)
                if lotus_amount > 0:
                    transfer_result = await self._send_tokens_to_wallet(
                        token_contract=lotus_contract,
                        amount=lotus_amount,
                        destination_wallet=holding_wallet,
                        chain='solana'
                    )
                    
                    if transfer_result:
                        self.logger.info(f"Lotus buyback successful: {lotus_amount:.2f} Lotus sent to {holding_wallet}")
                        return {
                            'success': True,
                            'skipped': False,
                            'buyback_amount_sol': buyback_amount,
                            'lotus_tokens': lotus_amount,
                            'transfer_tx_hash': result.get('tx_hash', ''),
                            'holding_wallet': holding_wallet
                        }
                    else:
                        self.logger.error("Failed to send Lotus tokens to holding wallet")
                        return {'success': False, 'error': 'Transfer failed'}
                else:
                    self.logger.error("No Lotus tokens received from swap")
                    return {'success': False, 'error': 'No tokens received'}
            else:
                self.logger.error(f"Lotus buyback swap failed: {result}")
                return {'success': False, 'error': result.get('error', 'Swap failed')}
                
        except Exception as e:
            self.logger.error(f"Error executing Lotus buyback: {e}")
            return {'success': False, 'error': str(e)}

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


