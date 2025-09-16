"""
Trader Lowcap - Simplified Version

Executes trades based on decision_lowcap strands from Decision Maker.
Implements simple 3-entry strategy and staged exit strategy.
"""

import logging
import os
import sys
import asyncio
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

# Add src to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from trading.jupiter_client import JupiterClient
from trading.zeroex_client import ZeroExClient
from trading.wallet_manager import WalletManager
from trading.js_solana_client import JSSolanaClient
from trading.js_ethereum_client import JSEthereumClient
from trading.trading_executor import TradingExecutor

logger = logging.getLogger(__name__)


class TraderLowcapSimple:
    """
    Simplified Trader Lowcap
    
    This module:
    - Reads decision_lowcap strands from Decision Maker
    - Executes 3-entry strategy: now, -30%, -60%
    - Implements staged exits: 30% at every 100% gain
    - Uses simplified positions schema
    """
    
    def __init__(self, supabase_manager, config: Dict[str, Any] = None):
        """
        Initialize Simplified Trader Lowcap
        
        Args:
            supabase_manager: Database manager for positions
            config: Configuration dictionary
        """
        self.supabase_manager = supabase_manager
        self.logger = logging.getLogger(__name__)
        
        # Simple configuration
        self.config = config or self._get_default_config()
        self.book_id = self.config.get('book_id', 'social')
        # No hardcoded book_nav - we get real balances from wallets
        
        # Initialize trading components
        helius_key = os.getenv('HELIUS_API_KEY')
        zeroex_key = os.getenv('0X_API_KEY')
        self.jupiter_client = JupiterClient(helius_key)
        self.zeroex_client = ZeroExClient(zeroex_key)
        self.wallet_manager = WalletManager()
        self.trading_executor = TradingExecutor(self.jupiter_client, self.wallet_manager, self.zeroex_client)
        
        # Initialize JavaScript Solana client for real execution
        # DISABLED: Comment out for mock trading
        # rpc_url = f"https://rpc.helius.xyz/?api-key={helius_key}" if helius_key else "https://api.mainnet-beta.solana.com"
        # sol_private_key = os.getenv('SOL_WALLET_PRIVATE_KEY')
        # if sol_private_key:
        #     self.js_solana_client = JSSolanaClient(rpc_url, sol_private_key)
        # else:
        #     self.js_solana_client = None
        #     self.logger.warning("SOL_WALLET_PRIVATE_KEY not found - real execution disabled")
        
        # Mock trading mode
        self.js_solana_client = None
        self.js_ethereum_client = None
        self.logger.info("Mock trading mode enabled")
        
        # Entry strategy: 3 entries
        self.entry_strategy = {
            'entry_1': {'timing': 'immediate', 'allocation_pct': 33.33},  # Now
            'entry_2': {'timing': 'dip', 'dip_pct': -30, 'allocation_pct': 33.33},  # -30% dip
            'entry_3': {'timing': 'dip', 'dip_pct': -60, 'allocation_pct': 33.34}   # -60% dip
        }
        
        # Exit strategy: 30% of REMAINING position at every 100% gain
        self.exit_strategy = {
            'exit_1': {'gain_pct': 100, 'exit_pct': 30},  # 30% of remaining at 100% gain
            'exit_2': {'gain_pct': 200, 'exit_pct': 30},  # 30% of remaining at 200% gain
            'exit_3': {'gain_pct': 300, 'exit_pct': 30},  # 30% of remaining at 300% gain
            'exit_4': {'gain_pct': 400, 'exit_pct': 30},  # 30% of remaining at 400% gain
            'exit_5': {'gain_pct': 500, 'exit_pct': 30},  # 30% of remaining at 500% gain
            'exit_6': {'gain_pct': 600, 'exit_pct': 30},  # 30% of remaining at 600% gain
            'final': {'gain_pct': 1000, 'exit_pct': 100}  # 100% at 1000% gain (final exit)
        }
        
        self.logger.info(f"Simplified Trader Lowcap initialized for book: {self.book_id}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            'book_id': 'social',
            'book_nav': 100000.0,
            'min_sol_balance': 0.1,  # Minimum SOL balance required
            'max_slippage_pct': 5.0,  # Maximum slippage tolerance
            'default_venue': 'Raydium'  # Default DEX for Solana
        }
    
    async def execute_decision(self, decision: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute trade based on decision_lowcap strand from Decision Maker
        
        Args:
            decision: decision_lowcap strand from Decision Maker
            
        Returns:
            Created position or None if execution failed
        """
        try:
            # Store the decision strand for use in entry/exit creation
            self.current_decision = decision
            if decision['content']['action'] != 'approve':
                self.logger.info(f"Decision not approved, skipping execution: {decision['content']['reasoning']}")
                return None
            
            # Extract data from signal_pack
            signal_pack = decision['signal_pack']
            token_data = signal_pack['token']
            venue_data = signal_pack['venue']
            curator_data = signal_pack['curator']
            trading_signals = signal_pack['trading_signals']
            
            allocation_pct = decision['content']['allocation_pct']
            curator_id = decision['content']['curator_id']
            
            # Get network and calculate allocation in native token
            chain = token_data.get('chain', 'solana').lower()
            native_balance = await self._get_native_balance(chain)
            if not native_balance:
                self.logger.warning(f"Could not get {chain} balance")
                return None
                
            allocation_native = allocation_pct * native_balance / 100
            
            self.logger.info(f"Executing trade: {token_data['ticker']} - {allocation_pct}% ({allocation_native:.4f} {chain.upper()})")
            
            # Step 1: Check native token balance
            if native_balance < allocation_native:
                self.logger.warning(f"Insufficient {chain.upper()} balance: {native_balance:.4f} < {allocation_native:.4f}")
                return None
            
            # Step 2: Get current price
            current_price = await self._get_current_price(token_data)
            if not current_price:
                self.logger.error(f"Could not get current price for {token_data['ticker']}")
                return None
            
            # Step 3: Create position with simplified schema
            position_id = f"{token_data['ticker']}_{token_data['chain']}_{int(datetime.now().timestamp())}"
            
            # Create position using simple table insert
            position_data = {
                'id': position_id,  # Use position_id as the primary key
                'token_chain': token_data['chain'],
                'token_contract': token_data['contract'],
                'token_ticker': token_data['ticker'],
                'book_id': decision['id'],  # Link to decision strand ID
                'status': 'active',
                'total_allocation_pct': allocation_pct,
                'total_allocation_usd': 0.0,  # Will be updated when entries are made
                'total_quantity': 0.0,  # Will be updated when entries are made
                'average_entry_price': 0.0,  # Will be updated when entries are made
                'curator_sources': curator_data.get('id', 'unknown'),  # Add curator ID
                'first_entry_timestamp': datetime.now(timezone.utc).isoformat()  # Track first entry timestamp
            }
            
            try:
                result = self.supabase_manager.client.table('lowcap_positions').insert(position_data).execute()
                if not result.data:
                    self.logger.error(f"Failed to create position for {token_data['ticker']}")
                    return None
                self.logger.info(f"✅ Position created: {position_id}")
                
            except Exception as e:
                self.logger.error(f"Error creating position: {e}")
                return None
            
            # Step 4: Set exit rules (30% of remaining at each level)
            exit_rules = {
                'strategy': 'staged',
                'stages': [
                    {'gain_pct': 100, 'exit_pct': 30, 'executed': False},  # 30% of remaining
                    {'gain_pct': 200, 'exit_pct': 30, 'executed': False},  # 30% of remaining
                    {'gain_pct': 300, 'exit_pct': 30, 'executed': False},  # 30% of remaining
                    {'gain_pct': 400, 'exit_pct': 30, 'executed': False},  # 30% of remaining
                    {'gain_pct': 500, 'exit_pct': 30, 'executed': False},  # 30% of remaining
                    {'gain_pct': 600, 'exit_pct': 30, 'executed': False},  # 30% of remaining
                    {'gain_pct': 1000, 'exit_pct': 100, 'executed': False} # 100% final exit
                ]
            }
            
            # Update position with exit rules
            try:
                self.supabase_manager.client.table('lowcap_positions').update({
                    'exit_rules': exit_rules
                }).eq('id', position_id).execute()
                self.logger.info(f"✅ Exit rules set for {position_id}")
            except Exception as e:
                self.logger.error(f"Error setting exit rules: {e}")
            
            # Step 5: Create and store all 3 entries
            await self._create_all_entries(position_id, current_price, allocation_native)
            
            # Step 6: Execute first entry (immediate)
            await self._execute_entry(position_id, 1)
            
            # Step 7: Calculate and store initial exits
            await self._calculate_initial_exits(position_id, current_price, allocation_native)
            
            self.logger.info(f"✅ Position created and first entry executed: {token_data['ticker']}")
            return {
                'position_id': position_id,
                'token_ticker': token_data['ticker'],
                'allocation_pct': allocation_pct,
                'allocation_native': allocation_native,
                'current_price': current_price,
                'status': 'active'
            }
            
        except Exception as e:
            self.logger.error(f"Failed to execute decision: {e}")
            return None
    
    
    async def _get_native_balance(self, chain: str) -> Optional[float]:
        """
        Get native token balance for the specified chain
        
        Args:
            chain: Blockchain network (solana, ethereum, base)
            
        Returns:
            Native token balance or None if failed
        """
        try:
            # Use WalletManager to get native token balance
            balance = await self.wallet_manager.get_balance(chain)
            if balance is not None:
                return float(balance)
            else:
                self.logger.error(f"Could not get {chain} balance")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting {chain} balance: {e}")
            return None

    async def _get_token_decimals(self, token_address: str) -> int:
        """
        Get token decimals using Solana RPC
        
        Args:
            token_address: Token mint address
            
        Returns:
            Token decimals (defaults to 5 if failed)
        """
        try:
            import aiohttp
            
            # Get token supply to get decimals
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTokenSupply",
                "params": [token_address]
            }
            
            rpc_url = "https://api.mainnet-beta.solana.com"
            async with aiohttp.ClientSession() as session:
                async with session.post(rpc_url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'result' in data and 'value' in data['result']:
                            decimals = data['result']['value']['decimals']
                            self.logger.info(f"Token {token_address} has {decimals} decimals")
                            return decimals
                        else:
                            self.logger.warning(f"Could not get decimals for {token_address}, defaulting to 5")
                            return 5
                    else:
                        self.logger.warning(f"RPC error getting decimals for {token_address}, defaulting to 5")
                        return 5
                        
        except Exception as e:
            self.logger.warning(f"Error getting token decimals: {e}, defaulting to 5")
            return 5

    async def _get_current_price(self, token_data: Dict[str, Any]) -> Optional[float]:
        """
        Get current price for token using Jupiter quote API (for Solana) or ZeroEx (for others)
        
        Args:
            token_data: Token information
            
        Returns:
            Current price in native token or None
        """
        try:
            token_address = token_data.get('contract')
            chain = token_data.get('chain', 'solana').lower()
            
            if not token_address:
                self.logger.error("No token contract address provided")
                return None
            
            # Get price from appropriate API based on chain
            if chain == 'solana':
                # Use Jupiter quote API for Solana tokens
                # Get quote for 0.1 SOL to calculate price
                quote_amount = 100_000_000  # 0.1 SOL in lamports
                quote = await self.jupiter_client.get_quote(
                    input_mint="So11111111111111111111111111111111111111112",  # SOL
                    output_mint=token_address,  # Token
                    amount=quote_amount
                )
                
                if quote and 'outAmount' in quote:
                    # Calculate price: SOL per token
                    token_amount = int(quote['outAmount'])
                    token_decimals = await self._get_token_decimals(token_address)
                    price = 0.1 / (token_amount / (10 ** token_decimals))
                    self.logger.info(f"Price via Jupiter quote: {price:.8f} SOL per {token_data.get('ticker', 'unknown')}")
                    return price
                else:
                    self.logger.warning(f"Could not get Jupiter quote for {token_data.get('ticker', 'unknown')}")
                    return None
                    
            elif chain in ['ethereum', 'base', 'polygon', 'arbitrum']:
                price_info = await self.zeroex_client.get_token_price(chain, token_address)
                if not price_info:
                    self.logger.error(f"Could not get price for {token_data.get('ticker', 'unknown')} on {chain}")
                    return None
                price = float(price_info['price'])
                self.logger.info(f"Current price for {token_data.get('ticker', 'unknown')} on {chain}: {price:.6f} ETH")
                return price
            else:
                self.logger.error(f"Unsupported chain for price fetching: {chain}")
                return None
            
        except Exception as e:
            self.logger.error(f"Error getting current price: {e}")
            return None
    
    def _execute_entry(self, position_id: str, entry_number: int, price: float, allocation_native: float, entry_type: str) -> bool:
        """
        Execute an entry for the position
        
        Args:
            position_id: Position ID
            entry_number: Entry number (1, 2, 3)
            price: Entry price
            allocation_native: Native token amount for this entry
            entry_type: Type of entry (immediate, dip)
            
        Returns:
            True if successful
        """
        try:
            quantity = allocation_native / price
            
            # Execute entry using simple table insert
            entry_data = {
                'position_id': position_id,
                'entry_number': entry_number,
                'entry_price': price,
                'quantity': quantity,
                'allocation_native': allocation_native,
                'venue': self.config.get('default_venue', 'Raydium'),
                'tx_hash': f"mock_tx_{entry_number}_{int(datetime.now().timestamp())}",
                'entry_type': entry_type,
                'status': 'executed',
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            try:
                result = self.supabase_manager.client.table('position_entries').insert(entry_data).execute()
                if result.data:
                    self.logger.info(f"Entry {entry_number} executed: {quantity:,.0f} tokens at ${price:.6f}")
                    return True
                else:
                    self.logger.error(f"Failed to execute entry {entry_number}")
                    return False
            except Exception as e:
                self.logger.error(f"Error executing entry {entry_number}: {e}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error executing entry {entry_number}: {e}")
            return False
    
    def _plan_dip_entries(self, position_id: str, current_price: float, total_allocation_native: float) -> None:
        """
        Plan dip entries for the position and store in database
        
        Args:
            position_id: Position ID
            current_price: Current price
            total_allocation_native: Total allocation in native token
        """
        try:
            # Plan entry 2: -30% dip
            dip_30_price = current_price * 0.7  # 30% down
            entry_2_native = total_allocation_native / 3
            entry_2_quantity = entry_2_native / dip_30_price
            
            # Plan entry 3: -60% dip  
            dip_60_price = current_price * 0.4  # 60% down
            entry_3_native = total_allocation_native / 3
            entry_3_quantity = entry_3_native / dip_60_price
            
            # Store planned entries in database as "pending" entries
            self._store_planned_entry(position_id, 2, dip_30_price, entry_2_quantity, entry_2_native, 'dip_30')
            self._store_planned_entry(position_id, 3, dip_60_price, entry_3_quantity, entry_3_native, 'dip_60')
            
            self.logger.info(f"Planned dip entries for {position_id}:")
            self.logger.info(f"  Entry 2: {entry_2_native:.4f} native at ${dip_30_price:.6f} (-30%) - PENDING")
            self.logger.info(f"  Entry 3: {entry_3_native:.4f} native at ${dip_60_price:.6f} (-60%) - PENDING")
            
        except Exception as e:
            self.logger.error(f"Error planning dip entries: {e}")
    
    def _store_planned_entry(self, position_id: str, entry_number: int, price: float, quantity: float, allocation_native: float, entry_type: str) -> bool:
        """
        Store a planned entry in the database
        
        Args:
            position_id: Position ID
            entry_number: Entry number (2, 3)
            price: Planned entry price
            quantity: Planned quantity
            allocation_native: Native token amount
            entry_type: Type of entry (dip_30, dip_60)
            
        Returns:
            True if successful
        """
        try:
            # Store as pending entry in the entries JSON array
            # This would be handled by the database schema's planned entries system
            # For now, we'll log it and the price monitoring system would pick it up
            
            self.logger.info(f"Stored planned entry {entry_number}: {quantity:,.0f} tokens at ${price:.6f} ({entry_type})")
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing planned entry: {e}")
            return False
    
    def check_exit_conditions(self, position_id: str) -> None:
        """
        Check if any exit conditions are met for a position
        
        Args:
            position_id: Position ID to check
        """
        try:
            # Get position data
            result = self.supabase_manager.table('lowcap_positions').select(
                'id, token_ticker, current_price, avg_entry_price, total_quantity, exit_rules'
            ).eq('id', position_id).eq('status', 'active').execute()
            
            if not result.data:
                return
            
            position = result.data[0]
            current_price = position.get('current_price', 0)
            avg_entry_price = position.get('avg_entry_price', 0)
            
            if avg_entry_price <= 0:
                return
            
            # Calculate current gain percentage
            gain_pct = ((current_price - avg_entry_price) / avg_entry_price) * 100
            
            # Check exit rules
            exit_rules = position.get('exit_rules', {})
            stages = exit_rules.get('stages', [])
            
            for stage in stages:
                stage_gain = stage.get('gain_pct', 0)
                stage_exit_pct = stage.get('exit_pct', 0)
                
                if gain_pct >= stage_gain:
                    # Execute exit
                    self._execute_exit(position_id, current_price, stage_exit_pct, f"take_profit_{stage_gain}%")
            
        except Exception as e:
            self.logger.error(f"Error checking exit conditions for {position_id}: {e}")
    
    def _execute_exit(self, position_id: str, price: float, exit_pct: float, exit_type: str) -> bool:
        """
        Execute an exit for the position (30% of REMAINING position)
        
        Args:
            position_id: Position ID
            price: Exit price
            exit_pct: Percentage of REMAINING position to exit
            exit_type: Type of exit
            
        Returns:
            True if successful
        """
        try:
            # Get current position quantity (remaining after previous exits)
            result = self.supabase_manager.table('lowcap_positions').select(
                'total_quantity'
            ).eq('id', position_id).execute()
            
            if not result.data:
                return False
            
            remaining_quantity = result.data[0].get('total_quantity', 0)
            exit_quantity = remaining_quantity * (exit_pct / 100)
            
            # Execute exit using simplified schema
            success = self.supabase_manager.rpc(
                'add_position_exit',
                {
                    'position_id_param': position_id,
                    'exit_price_param': price,
                    'quantity_param': exit_quantity,
                    'venue_param': self.config.get('default_venue', 'Raydium'),
                    'tx_hash_param': f"mock_exit_{int(datetime.now().timestamp())}",
                    'exit_type_param': exit_type
                }
            )
            
            if success.data:
                self.logger.info(f"Exit executed: {exit_quantity:,.0f} tokens at ${price:.6f} ({exit_pct}% of remaining)")
                return True
            else:
                self.logger.error(f"Failed to execute exit")
                return False
                
        except Exception as e:
            self.logger.error(f"Error executing exit: {e}")
            return False
    
    def get_active_positions(self) -> List[Dict[str, Any]]:
        """Get all active positions"""
        try:
            result = self.supabase_manager.table('lowcap_positions').select(
                'id, token_ticker, token_chain, total_allocation_pct, total_allocation_usd, '
                'current_price, avg_entry_price, total_quantity, total_pnl_pct, status'
            ).eq('book_id', self.book_id).eq('status', 'active').execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            self.logger.error(f"Error getting active positions: {e}")
            return []
    
    def update_position_prices(self) -> None:
        """Update current prices for all active positions"""
        try:
            positions = self.get_active_positions()
            
            for position in positions:
                token_data = {
                    'ticker': position['token_ticker'],
                    'chain': position['token_chain']
                }
                
                current_price = self._get_current_price(token_data)
                if current_price:
                    # Update current price in database
                    self.supabase_manager.table('lowcap_positions').update({
                        'current_price': current_price,
                        'last_activity_timestamp': datetime.now(timezone.utc).isoformat()
                    }).eq('id', position['id']).execute()
                    
                    # Check exit conditions
                    self.check_exit_conditions(position['id'])
            
        except Exception as e:
            self.logger.error(f"Error updating position prices: {e}")

    async def _create_all_entries(self, position_id: str, current_price: float, total_allocation_native: float) -> None:
        """
        Create all 3 entries and store them in the entries array
        """
        try:
            # Calculate entry amounts (divide by 3)
            entry_amount = total_allocation_native / 3
            
            # Entry 1: Immediate
            entry_1 = {
                'entry_number': 1,
                'price': current_price,
                'amount_native': entry_amount,
                'entry_type': 'immediate',
                'status': 'pending',
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Entry 2: -30% dip
            entry_2 = {
                'entry_number': 2,
                'price': current_price * 0.7,  # 30% down
                'amount_native': entry_amount,
                'entry_type': 'dip_30',
                'status': 'pending',
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Entry 3: -60% dip
            entry_3 = {
                'entry_number': 3,
                'price': current_price * 0.4,  # 60% down
                'amount_native': entry_amount,
                'entry_type': 'dip_60',
                'status': 'pending',
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Store all entries in the entries array
            entries = [entry_1, entry_2, entry_3]
            
            self.supabase_manager.client.table('lowcap_positions').update({
                'entries': entries
            }).eq('id', position_id).execute()
            
            self.logger.info(f"✅ Created 3 entries for {position_id}")
            
        except Exception as e:
            self.logger.error(f"Error creating entries: {e}")

    async def _execute_entry(self, position_id: str, entry_number: int) -> bool:
        """
        Execute a specific entry (mark as executed and update position)
        """
        try:
            # Get current position
            result = self.supabase_manager.client.table('lowcap_positions').select('entries').eq('id', position_id).execute()
            if not result.data:
                self.logger.error(f"Position {position_id} not found")
                return False
            
            entries = result.data[0].get('entries', [])
            
            # Find the entry to execute
            entry_to_execute = None
            for entry in entries:
                if entry['entry_number'] == entry_number and entry['status'] == 'pending':
                    entry_to_execute = entry
                    break
            
            if not entry_to_execute:
                self.logger.warning(f"Entry {entry_number} not found or already executed")
                return False
            
            # Execute the actual trade if JavaScript client is available
            tx_hash = None
            if self.js_solana_client or self.js_ethereum_client:
                try:
                    # Get position details for the swap
                    position_result = self.supabase_manager.client.table('lowcap_positions').select('token_contract, token_chain, total_allocation_pct').eq('id', position_id).execute()
                    if position_result.data:
                        position = position_result.data[0]
                        token_contract = position['token_contract']
                        token_chain = position['token_chain']
                        allocation_pct = position['total_allocation_pct']
                        
                        if token_chain.lower() == 'solana' and self.js_solana_client:
                            # Execute Solana swap
                            sol_balance = await self._get_native_balance('solana')
                            if sol_balance:
                                sol_amount = (allocation_pct / 100) * sol_balance
                                sol_lamports = int(sol_amount * 1e9)  # Convert to lamports
                                
                                swap_result = await self.js_solana_client.execute_jupiter_swap(
                                    input_mint="So11111111111111111111111111111111111111112",  # SOL
                                    output_mint=token_contract,  # Token
                                    amount=sol_lamports,
                                    slippage_bps=50
                                )
                                
                                if swap_result.get('success'):
                                    tx_hash = swap_result.get('tx_hash')
                                    self.logger.info(f"✅ Solana trade executed: {tx_hash}")
                                else:
                                    self.logger.error(f"❌ Solana trade failed: {swap_result.get('error')}")
                            else:
                                self.logger.error("Could not get SOL balance for trade execution")
                                
                        elif token_chain.lower() in ['ethereum', 'base'] and self.js_ethereum_client:
                            # Execute Ethereum/Base swap
                            eth_balance = await self._get_native_balance(token_chain)
                            if eth_balance:
                                eth_amount = (allocation_pct / 100) * eth_balance
                                eth_wei = int(eth_amount * 1e18)  # Convert to wei
                                
                                # Get quote from 0x
                                taker_address = os.getenv('ETHEREUM_WALLET_ADDRESS')
                                quote = await self.zeroex_client.get_quote(
                                    chain=token_chain,
                                    sell_token="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # WETH
                                    buy_token=token_contract,
                                    sell_amount=str(eth_wei),
                                    taker=taker_address,
                                    slippage_bps=50
                                )
                                
                                if quote:
                                    swap_result = await self.js_ethereum_client.execute_swap(
                                        sell_token="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                                        buy_token=token_contract,
                                        sell_amount=str(eth_wei),
                                        quote_data=quote
                                    )
                                    
                                    if swap_result.get('success'):
                                        tx_hash = swap_result.get('tx_hash')
                                        self.logger.info(f"✅ {token_chain} trade executed: {tx_hash}")
                                    else:
                                        self.logger.error(f"❌ {token_chain} trade failed: {swap_result.get('error')}")
                                else:
                                    self.logger.error(f"Could not get quote for {token_chain} trade")
                            else:
                                self.logger.error(f"Could not get {token_chain.upper()} balance for trade execution")
                        else:
                            self.logger.warning(f"No execution client available for {token_chain}")
                            
                except Exception as e:
                    self.logger.error(f"Error executing real trade: {e}")
            
            # Mark entry as executed
            entry_to_execute['status'] = 'executed'
            entry_to_execute['executed_at'] = datetime.now(timezone.utc).isoformat()
            entry_to_execute['tx_hash'] = tx_hash or f"mock_tx_{entry_number}_{int(datetime.now().timestamp())}"
            
            # Calculate tokens bought for this entry
            entry_to_execute['tokens_bought'] = entry_to_execute['amount_native'] / entry_to_execute['price']
            
            # Update the entries array
            self.supabase_manager.client.table('lowcap_positions').update({
                'entries': entries
            }).eq('id', position_id).execute()
            
            # Update position totals (total_quantity, average_entry_price, total_allocation_usd)
            await self._update_position_totals(position_id)
            
            # Recalculate exits if this is not the first entry (average price changed)
            if entry_number > 1:
                await self._recalculate_exits(position_id)
            
            # Create entry strand
            await self._create_entry_strand(position_id, entry_to_execute, entry_number)
            
            self.logger.info(f"✅ Executed entry {entry_number}: {entry_to_execute['amount_native']:.4f} native at ${entry_to_execute['price']:.6f}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error executing entry {entry_number}: {e}")
            return False

    async def _calculate_initial_exits(self, position_id: str, current_price: float, total_allocation_native: float) -> None:
        """
        Calculate initial 3 exits based on current price and store in exits array
        """
        try:
            # Calculate exit points (30% of remaining at each level)
            total_tokens = total_allocation_native / current_price  # Total tokens we'll have
            
            # Exit 1: 100% gain (30% of remaining)
            exit_1_tokens = total_tokens * 0.30
            exit_1 = {
                'exit_number': 1,
                'price': current_price * 2.0,  # 100% gain
                'tokens': exit_1_tokens,
                'gain_pct': 100,
                'status': 'pending',
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Exit 2: 200% gain (30% of remaining 70%)
            remaining_after_1 = total_tokens * 0.70
            exit_2_tokens = remaining_after_1 * 0.30
            exit_2 = {
                'exit_number': 2,
                'price': current_price * 3.0,  # 200% gain
                'tokens': exit_2_tokens,
                'gain_pct': 200,
                'status': 'pending',
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Exit 3: 300% gain (30% of remaining 49%)
            remaining_after_2 = remaining_after_1 * 0.70
            exit_3_tokens = remaining_after_2 * 0.30
            exit_3 = {
                'exit_number': 3,
                'price': current_price * 4.0,  # 300% gain
                'tokens': exit_3_tokens,
                'gain_pct': 300,
                'status': 'pending',
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Store all exits in the exits array
            exits = [exit_1, exit_2, exit_3]
            
            self.supabase_manager.client.table('lowcap_positions').update({
                'exits': exits
            }).eq('id', position_id).execute()
            
            self.logger.info(f"✅ Calculated 3 exits for {position_id}")
            
        except Exception as e:
            self.logger.error(f"Error calculating initial exits: {e}")

    async def start_position_monitoring(self) -> None:
        """
        Start the position monitoring loop - checks every 3 minutes
        """
        self.logger.info("🔄 Starting position monitoring (3-minute intervals)")
        
        while True:
            try:
                await self._monitor_all_positions()
                await asyncio.sleep(180)  # 3 minutes = 180 seconds
            except Exception as e:
                self.logger.error(f"Error in position monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def _monitor_all_positions(self) -> None:
        """
        Monitor all active positions for entry/exit opportunities
        """
        try:
            # Get all active positions
            positions = await self._get_active_positions()
            
            if not positions:
                self.logger.debug("No active positions to monitor")
                return
                
            self.logger.info(f"🔍 Monitoring {len(positions)} active positions")
            
            for position in positions:
                await self._monitor_single_position(position)
                
        except Exception as e:
            self.logger.error(f"Error monitoring positions: {e}")

    async def _get_active_positions(self) -> List[Dict[str, Any]]:
        """
        Get all active positions from database
        """
        try:
            result = self.supabase_manager.client.table('lowcap_positions').select('*').eq('status', 'active').execute()
            return result.data if result.data else []
        except Exception as e:
            self.logger.error(f"Error getting active positions: {e}")
            return []

    async def _monitor_single_position(self, position: Dict[str, Any]) -> None:
        """
        Monitor a single position for entry/exit opportunities
        """
        try:
            position_id = position['position_id']
            token_ticker = position['token_ticker']
            
            # Get current price
            current_price = self._get_current_price_from_position(position)
            if not current_price:
                self.logger.warning(f"Could not get current price for {token_ticker}")
                return
                
            # Check for planned entries (dip buys)
            await self._check_planned_entries(position, current_price)
            
            # Check for exit opportunities
            await self._check_exit_opportunities(position, current_price)
            
        except Exception as e:
            self.logger.error(f"Error monitoring position {position.get('position_id', 'unknown')}: {e}")

    def _get_current_price_from_position(self, position: Dict[str, Any]) -> Optional[float]:
        """
        Get current price for a position's token
        """
        try:
            token_data = {
                'ticker': position['token_ticker'],
                'contract': position['token_contract'],
                'chain': position['token_chain'],
                'dex': position.get('dex', 'pumpswap')
            }
            return self._get_current_price(token_data)
        except Exception as e:
            self.logger.error(f"Error getting current price for position: {e}")
            return None

    async def _check_planned_entries(self, position: Dict[str, Any], current_price: float) -> None:
        """
        Check if any planned entries should be executed
        """
        try:
            position_id = position['id']  # Use 'id' not 'position_id'
            token_ticker = position['token_ticker']
            
            # Get entries from position data
            entries = position.get('entries', [])
            
            for entry in entries:
                if entry.get('status') == 'pending':
                    entry_price = entry.get('price')
                    entry_number = entry.get('entry_number')
                    
                    if current_price <= entry_price:
                        # Execute the planned entry
                        self.logger.info(f"🎯 Executing planned entry {entry_number} for {token_ticker} at {current_price:.6f}")
                        
                        success = await self._execute_entry(position_id, entry_number)
                        
                        if not success:
                            self.logger.warning(f"Failed to execute planned entry {entry_number}")
                            
        except Exception as e:
            self.logger.error(f"Error checking planned entries: {e}")

    async def _check_exit_opportunities(self, position: Dict[str, Any], current_price: float) -> None:
        """
        Check if any exit opportunities should be executed
        """
        try:
            position_id = position['id']  # Use 'id' not 'position_id'
            token_ticker = position['token_ticker']
            
            # Get exits from position data
            exits = position.get('exits', [])
            
            for exit_order in exits:
                if exit_order.get('status') == 'pending':
                    exit_price = exit_order.get('price')
                    exit_number = exit_order.get('exit_number')
                    
                    if current_price >= exit_price:
                        # Execute the exit
                        self.logger.info(f"💰 Executing exit {exit_number} for {token_ticker} at {current_price:.6f} (target: {exit_price:.6f})")
                        
                        success = await self._execute_exit(position_id, exit_number)
                        
                        if not success:
                            self.logger.warning(f"Failed to execute exit {exit_number}")
                            
        except Exception as e:
            self.logger.error(f"Error checking exit opportunities: {e}")

    async def _create_entry_strand(self, position_id: str, entry_data: Dict[str, Any], entry_number: int) -> None:
        """
        Create an entry_lowcap strand in ad_strands table
        """
        try:
            # Get the parent decision strand ID from the position's book_id
            position_result = self.supabase_manager.client.table('lowcap_positions').select('book_id, token_ticker, token_chain, token_contract').eq('id', position_id).execute()
            if not position_result.data:
                self.logger.error(f"Position {position_id} not found for entry strand creation")
                return

            position_info = position_result.data[0]
            parent_decision_id = position_info['book_id']
            token_ticker = position_info['token_ticker']
            token_chain = position_info['token_chain']
            token_contract = position_info['token_contract']

            # Get the full decision strand to copy important fields
            # Use stored decision if available, otherwise fetch from database
            if hasattr(self, 'current_decision') and self.current_decision:
                decision_strand = self.current_decision
            else:
                decision_result = self.supabase_manager.client.table('ad_strands').select('*').eq('id', parent_decision_id).execute()
                decision_strand = decision_result.data[0] if decision_result.data else {}

            # Create trading plan with entries and exits
            trading_plan = {
                "strategy": "3_entry_staged_exit",
                "entries": [
                    {"entry": 1, "type": "immediate", "allocation_pct": 100},
                    {"entry": 2, "type": "dip_buy", "trigger_pct": -30, "allocation_pct": 50},
                    {"entry": 3, "type": "dip_buy", "trigger_pct": -60, "allocation_pct": 25}
                ],
                "exits": [
                    {"exit": 1, "trigger_pct": 100, "exit_pct": 30},
                    {"exit": 2, "trigger_pct": 200, "exit_pct": 30},
                    {"exit": 3, "trigger_pct": 300, "exit_pct": 30}
                ]
            }

            entry_strand_data = {
                "id": str(uuid.uuid4()),
                "module": "trader_lowcap",
                "kind": "entry_lowcap",
                "symbol": token_ticker,
                "parent_id": parent_decision_id,
                "tags": ["trade", "entry", "lowcap", f"entry_{entry_number}"],
                "session_bucket": decision_strand.get('session_bucket'),
                "sig_confidence": decision_strand.get('sig_confidence'),
                "sig_direction": decision_strand.get('sig_direction'),
                "confidence": decision_strand.get('confidence'),
                "signal_pack": decision_strand.get('signal_pack'),
                "module_intelligence": decision_strand.get('module_intelligence'),
                "trading_plan": trading_plan,
                "content": {
                    "position_id": position_id,
                    "entry_number": entry_number,
                    "price": entry_data['price'],
                    "amount_native": entry_data['amount_native'],
                    "entry_type": entry_data['entry_type'],
                    "status": entry_data['status'],
                    "tx_hash": entry_data.get('tx_hash'),
                    "token_ticker": token_ticker,
                    "token_chain": token_chain,
                    "token_contract": token_contract
                },
                "status": "active",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            result = self.supabase_manager.client.table('ad_strands').insert(entry_strand_data).execute()
            if result.data:
                self.logger.info(f"✅ Created entry_lowcap strand for {position_id}, entry {entry_number}")
            else:
                self.logger.error(f"Failed to create entry_lowcap strand for {position_id}, entry {entry_number}")
        except Exception as e:
            self.logger.error(f"Error creating entry strand: {e}")

    async def _create_exit_strand(self, position_id: str, exit_data: Dict[str, Any], exit_number: int) -> None:
        """
        Create an exit_lowcap strand in ad_strands table
        """
        try:
            # Get the parent decision strand ID from the position's book_id
            position_result = self.supabase_manager.client.table('lowcap_positions').select('book_id, token_ticker, token_chain, token_contract').eq('id', position_id).execute()
            if not position_result.data:
                self.logger.error(f"Position {position_id} not found for exit strand creation")
                return

            position_info = position_result.data[0]
            parent_decision_id = position_info['book_id']
            token_ticker = position_info['token_ticker']
            token_chain = position_info['token_chain']
            token_contract = position_info['token_contract']

            # Get the full decision strand to copy important fields
            # Use stored decision if available, otherwise fetch from database
            if hasattr(self, 'current_decision') and self.current_decision:
                decision_strand = self.current_decision
            else:
                decision_result = self.supabase_manager.client.table('ad_strands').select('*').eq('id', parent_decision_id).execute()
                decision_strand = decision_result.data[0] if decision_result.data else {}

            # Create trading plan with entries and exits
            trading_plan = {
                "strategy": "3_entry_staged_exit",
                "entries": [
                    {"entry": 1, "type": "immediate", "allocation_pct": 100},
                    {"entry": 2, "type": "dip_buy", "trigger_pct": -30, "allocation_pct": 50},
                    {"entry": 3, "type": "dip_buy", "trigger_pct": -60, "allocation_pct": 25}
                ],
                "exits": [
                    {"exit": 1, "trigger_pct": 100, "exit_pct": 30},
                    {"exit": 2, "trigger_pct": 200, "exit_pct": 30},
                    {"exit": 3, "trigger_pct": 300, "exit_pct": 30}
                ]
            }

            exit_strand_data = {
                "id": str(uuid.uuid4()),
                "module": "trader_lowcap",
                "kind": "exit_lowcap",
                "symbol": token_ticker,
                "parent_id": parent_decision_id,
                "tags": ["trade", "exit", "lowcap", f"exit_{exit_number}"],
                "session_bucket": decision_strand.get('session_bucket'),
                "sig_confidence": decision_strand.get('sig_confidence'),
                "sig_direction": decision_strand.get('sig_direction'),
                "confidence": decision_strand.get('confidence'),
                "signal_pack": decision_strand.get('signal_pack'),
                "module_intelligence": decision_strand.get('module_intelligence'),
                "trading_plan": trading_plan,
                "content": {
                    "position_id": position_id,
                    "exit_number": exit_number,
                    "price": exit_data['price'],
                    "tokens_sold": exit_data['tokens'],
                    "gain_pct": exit_data['gain_pct'],
                    "status": exit_data['status'],
                    "tx_hash": exit_data.get('tx_hash'),
                    "token_ticker": token_ticker,
                    "token_chain": token_chain,
                    "token_contract": token_contract
                },
                "status": "active",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            result = self.supabase_manager.client.table('ad_strands').insert(exit_strand_data).execute()
            if result.data:
                self.logger.info(f"✅ Created exit_lowcap strand for {position_id}, exit {exit_number}")
            else:
                self.logger.error(f"Failed to create exit_lowcap strand for {position_id}, exit {exit_number}")
        except Exception as e:
            self.logger.error(f"Error creating exit strand: {e}")

    async def _execute_exit(self, position_id: str, exit_number: int) -> bool:
        """
        Execute a specific exit (mark as executed)
        """
        try:
            # Get current position
            result = self.supabase_manager.client.table('lowcap_positions').select('exits').eq('id', position_id).execute()
            if not result.data:
                self.logger.error(f"Position {position_id} not found")
                return False
            
            exits = result.data[0].get('exits', [])
            
            # Find the exit to execute
            exit_to_execute = None
            for exit_order in exits:
                if exit_order['exit_number'] == exit_number and exit_order['status'] == 'pending':
                    exit_to_execute = exit_order
                    break
            
            if not exit_to_execute:
                self.logger.warning(f"Exit {exit_number} not found or already executed")
                return False
            
            # Mark exit as executed
            exit_to_execute['status'] = 'executed'
            exit_to_execute['executed_at'] = datetime.now(timezone.utc).isoformat()
            exit_to_execute['tx_hash'] = f"mock_exit_{exit_number}_{int(datetime.now().timestamp())}"
            
            # Update the exits array
            self.supabase_manager.client.table('lowcap_positions').update({
                'exits': exits
            }).eq('id', position_id).execute()
            
            # Create exit strand
            await self._create_exit_strand(position_id, exit_to_execute, exit_number)
            
            self.logger.info(f"✅ Executed exit {exit_number}: {exit_to_execute['tokens']:.0f} tokens at ${exit_to_execute['price']:.6f}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error executing exit {exit_number}: {e}")
            return False

    async def _update_position_totals(self, position_id: str) -> None:
        """
        Update position totals (total_quantity, average_entry_price, total_allocation_usd)
        based on executed entries
        """
        try:
            # Get position and executed entries
            position_result = self.supabase_manager.client.table('lowcap_positions').select('entries, token_chain').eq('id', position_id).execute()
            if not position_result.data:
                self.logger.error(f"Position {position_id} not found")
                return
                
            position = position_result.data[0]
            entries = position.get('entries', [])
            
            # Calculate totals from executed entries
            total_native_spent = 0.0
            total_tokens_bought = 0.0
            
            for entry in entries:
                if entry.get('status') == 'executed':
                    total_native_spent += entry.get('amount_native', 0)
                    total_tokens_bought += entry.get('tokens_bought', 0)
            
            if total_tokens_bought > 0:
                average_entry_price = total_native_spent / total_tokens_bought
                
                # Get current price to convert native tokens spent to USD
                current_price = await self._get_current_price_from_position(position_id)
                # total_allocation_usd = total native tokens spent * current price (converts to USD)
                total_allocation_usd = total_native_spent * current_price if current_price else 0.0
                
                # Update position
                self.supabase_manager.client.table('lowcap_positions').update({
                    'total_quantity': total_tokens_bought,
                    'average_entry_price': average_entry_price,
                    'total_allocation_usd': total_allocation_usd
                }).eq('id', position_id).execute()
                
                self.logger.info(f"Updated position totals: {total_tokens_bought:.2f} tokens, avg price: {average_entry_price:.6f}, USD value: ${total_allocation_usd:.2f}")
            else:
                self.logger.warning(f"No executed entries found for position {position_id}")
                
        except Exception as e:
            self.logger.error(f"Error updating position totals: {e}")

    async def _recalculate_exits(self, position_id: str) -> None:
        """
        Recalculate exit targets when new entries are made (average price changed)
        """
        try:
            # Get position data
            position_result = self.supabase_manager.client.table('lowcap_positions').select('total_quantity, average_entry_price, exits').eq('id', position_id).execute()
            if not position_result.data:
                self.logger.error(f"Position {position_id} not found")
                return
                
            position = position_result.data[0]
            total_quantity = position.get('total_quantity', 0)
            average_entry_price = position.get('average_entry_price', 0)
            
            if total_quantity <= 0 or average_entry_price <= 0:
                self.logger.warning(f"Invalid position data for recalculation: quantity={total_quantity}, avg_price={average_entry_price}")
                return
            
            # Get current exits
            exits = position.get('exits', [])
            
            # Recalculate exit targets based on new average price
            for exit_data in exits:
                if exit_data.get('status') == 'pending':
                    exit_number = exit_data.get('exit_number', 1)
                    gain_multiplier = exit_number  # 100%, 200%, 300% gain
                    
                    # Calculate new target price
                    target_price = average_entry_price * (1 + gain_multiplier)
                    
                    # Update exit target
                    exit_data['target_price'] = target_price
                    exit_data['tokens_to_sell'] = total_quantity * 0.30  # 30% of remaining
                    exit_data['expected_native'] = exit_data['tokens_to_sell'] * target_price
                    
                    self.logger.info(f"Recalculated exit {exit_number}: target price ${target_price:.6f}, tokens: {exit_data['tokens_to_sell']:.2f}")
            
            # Update exits in database
            self.supabase_manager.client.table('lowcap_positions').update({
                'exits': exits
            }).eq('id', position_id).execute()
            
            self.logger.info(f"Recalculated exits for position {position_id} based on new average price ${average_entry_price:.6f}")
            
        except Exception as e:
            self.logger.error(f"Error recalculating exits: {e}")


# Example usage
if __name__ == "__main__":
    # Mock supabase manager for testing
    class MockSupabaseManager:
        def rpc(self, function_name, params):
            print(f"RPC call: {function_name} with params: {params}")
            return {'data': True}
        
        def table(self, table_name):
            class MockTable:
                def select(self, columns):
                    return self
                def eq(self, column, value):
                    return self
                def update(self, data):
                    return self
                def execute(self):
                    return {'data': []}
            return MockTable()
    
    # Test the simplified trader
    trader = TraderLowcapSimple(MockSupabaseManager())
    
    # Mock decision from Decision Maker
    decision = {
        'id': 'decision_123',
        'content': {
            'action': 'approve',
            'curator_id': '0xdetweiler',
            'curator_confidence': 0.85,
            'allocation_pct': 3.0,
            'allocation_usd': 3000.0,
            'token': {
                'ticker': 'PEPE',
                'contract': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
                'chain': 'solana',
                'name': 'Pepe Coin'
            },
            'reasoning': 'Approved: Curator score 0.85, allocating 3%'
        }
    }
    
    # Execute decision
    result = trader.execute_decision(decision)
    print(f"Execution result: {result}")
