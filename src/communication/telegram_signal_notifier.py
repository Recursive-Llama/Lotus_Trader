"""
Telegram Signal Notifier

Sends buy/sell trading signals to a private Telegram group with rich formatting.
Integrates with existing Telegram infrastructure for seamless notifications.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from telethon import TelegramClient
from telethon.sessions import StringSession
from utils.supabase_manager import SupabaseManager

logger = logging.getLogger(__name__)


class TelegramSignalNotifier:
    """Sends trading signals to Telegram group with rich formatting"""
    
    @staticmethod
    def _stage_glyph(stage: str) -> str:
        mapping = {
            "S0": "🜁0",
            "S1": "🜂1",
            "S2": "🜃2",
            "S3": "🜓3",
            "S4": "🝪4",
        }
        return mapping.get(str(stage), str(stage))
    
    def __init__(self, bot_token: str, channel_id: str, api_id: int, api_hash: str, session_file: str = None):
        """
        Initialize Telegram Signal Notifier
        
        Args:
            bot_token: Telegram bot token for sending messages
            channel_id: Target channel/group ID (can be @username or numeric ID)
            api_id: Telegram API ID (reuse existing)
            api_hash: Telegram API Hash (reuse existing)
            session_file: Path to existing session file
        """
        self.bot_token = bot_token
        self.channel_id = channel_id
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_file = session_file or "src/config/telegram_session.txt"
        self.client = None
        self.supabase_manager = SupabaseManager()
        
        logger.info(f"Telegram Signal Notifier initialized for channel: {channel_id}")
    
    def _get_lotus_price_per_sol(self) -> Optional[float]:
        """Get current Lotus token price in SOL from wallet_balances table"""
        try:
            # Get Lotus token price from wallet_balances
            result = self.supabase_manager.client.table('wallet_balances').select(
                'balance_usd', 'balance'
            ).eq('chain', 'lotus').order('last_updated', desc=True).limit(1).execute()
            
            if result.data and len(result.data) > 0:
                lotus_data = result.data[0]
                balance_usd = float(lotus_data.get('balance_usd', 0) or 0)
                balance_tokens = float(lotus_data.get('balance', 0) or 0)
                
                if balance_tokens > 0 and balance_usd > 0:
                    # Calculate price per token in USD
                    price_per_token_usd = balance_usd / balance_tokens
                    
                    # Get SOL price in USD
                    sol_result = self.supabase_manager.client.table('wallet_balances').select(
                        'balance_usd', 'balance'
                    ).eq('chain', 'solana').order('last_updated', desc=True).limit(1).execute()
                    
                    if sol_result.data and len(sol_result.data) > 0:
                        sol_data = sol_result.data[0]
                        sol_balance_usd = float(sol_data.get('balance_usd', 0) or 0)
                        sol_balance = float(sol_data.get('balance', 0) or 0)
                        
                        if sol_balance > 0 and sol_balance_usd > 0:
                            sol_price_usd = sol_balance_usd / sol_balance
                            # Convert Lotus price from USD to SOL
                            lotus_price_per_sol = price_per_token_usd / sol_price_usd
                            return lotus_price_per_sol
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting Lotus price: {e}")
            return None
    
    def _get_usdc_conversion_to_lotus_tokens(self, exit_value_native: float, chain: str) -> Optional[float]:
        """Calculate how many Lotus tokens the 10% USDC conversion would buy"""
        try:
            # Get native token price in USD from wallet_balances
            native_result = self.supabase_manager.client.table('wallet_balances').select(
                'balance_usd', 'balance'
            ).eq('chain', chain).order('last_updated', desc=True).limit(1).execute()
            
            if not native_result.data or len(native_result.data) == 0:
                return None
                
            native_data = native_result.data[0]
            native_balance_usd = float(native_data.get('balance_usd', 0) or 0)
            native_balance = float(native_data.get('balance', 0) or 0)
            
            if native_balance <= 0 or native_balance_usd <= 0:
                return None
                
            # Calculate native token price in USD
            native_price_usd = native_balance_usd / native_balance
            
            # Calculate 10% USDC value in USD
            usdc_value_usd = exit_value_native * native_price_usd * 0.10
            
            # Get Lotus price in USD
            lotus_result = self.supabase_manager.client.table('wallet_balances').select(
                'balance_usd', 'balance'
            ).eq('chain', 'lotus').order('last_updated', desc=True).limit(1).execute()
            
            if not lotus_result.data or len(lotus_result.data) == 0:
                return None
                
            lotus_data = lotus_result.data[0]
            lotus_balance_usd = float(lotus_data.get('balance_usd', 0) or 0)
            lotus_balance = float(lotus_data.get('balance', 0) or 0)
            
            if lotus_balance <= 0 or lotus_balance_usd <= 0:
                return None
                
            # Calculate Lotus price in USD
            lotus_price_usd = lotus_balance_usd / lotus_balance
            
            # Calculate how many Lotus tokens the USDC can buy
            lotus_tokens = usdc_value_usd / lotus_price_usd
            return lotus_tokens
            
        except Exception as e:
            logger.error(f"Error calculating USDC conversion to Lotus tokens: {e}")
            return None
    
    async def _get_client(self) -> TelegramClient:
        """Get or create Telegram client using bot token (not user session)
        
        Uses bot token to avoid conflicts with TelegramScanner which uses user session.
        This allows both to run simultaneously without session ID conflicts.
        """
        if not self.client:
            # Always use bot token (not user session) to avoid conflicts with TelegramScanner
            self.client = TelegramClient('signal_bot', self.api_id, self.api_hash)
            await self.client.start(bot_token=self.bot_token)
            logger.debug("Telegram signal notifier connected using bot token")
        
        if not self.client.is_connected():
            await self.client.start(bot_token=self.bot_token)
        
        return self.client
    
    async def send_buy_signal(self, 
                            token_ticker: str, 
                            token_contract: str, 
                            chain: str, 
                            amount_native: float, 
                            price: float, 
                            tx_hash: str,
                            source_tweet_url: Optional[str] = None,
                            allocation_pct: Optional[float] = None,
                            amount_usd: Optional[float] = None) -> bool:
        """
        Send buy signal notification
        
        Args:
            token_ticker: Token symbol (e.g., "PEPE")
            token_contract: Token contract address
            chain: Blockchain (bsc, base, ethereum, solana)
            amount_native: Amount spent in native currency
            price: Entry price per token
            tx_hash: Transaction hash
            source_tweet_url: URL of source tweet (optional)
            allocation_pct: Portfolio allocation percentage (optional)
            
        Returns:
            True if message sent successfully, False otherwise
        """
        try:
            # Format native currency symbol
            native_symbol = self._get_native_symbol(chain)
            
            # Create transaction link
            tx_link = self._create_transaction_link(tx_hash, chain)
            
            # Create token link
            token_link = self._create_token_link(token_contract, chain)
            
            # Format message
            message = self._format_buy_message(
                token_ticker, token_link, amount_native, native_symbol, 
                price, tx_link, source_tweet_url, allocation_pct, amount_usd
            )
            
            # Send message
            return await self._send_message(message)
            
        except Exception as e:
            logger.error(f"Error sending buy signal: {e}")
            return False
    
    async def send_sell_signal(self,
                             token_ticker: str,
                             token_contract: str,
                             chain: str,
                             tokens_sold: float,
                             sell_price: float,
                             tx_hash: str,
                             tokens_sold_value_usd: Optional[float] = None,
                             total_profit_usd: Optional[float] = None,
                             source_tweet_url: Optional[str] = None,
                             remaining_tokens: Optional[float] = None,
                             position_value: Optional[float] = None,
                             total_pnl_pct: Optional[float] = None,
                             profit_native: Optional[float] = None,
                             buyback_amount_sol: Optional[float] = None,
                             lotus_tokens: Optional[float] = None,
                             buyback_tx_hash: Optional[str] = None) -> bool:
        """
        Send sell signal notification
        
        Args:
            token_ticker: Token symbol
            token_contract: Token contract address
            chain: Blockchain
            tokens_sold: Amount of tokens sold
            sell_price: Sell price per token
            tx_hash: Transaction hash
            profit_pct: Profit percentage for this sell
            profit_usd: Profit in USD for this sell
            total_profit_usd: Total profit for this position
            source_tweet_url: URL of source tweet (optional)
            
        Returns:
            True if message sent successfully, False otherwise
        """
        try:
            # Format native currency symbol
            native_symbol = self._get_native_symbol(chain)
            
            # Create transaction link
            tx_link = self._create_transaction_link(tx_hash, chain)
            
            # Create token link
            token_link = self._create_token_link(token_contract, chain)
            
            # Format message
            message = self._format_sell_message(
                token_ticker, token_link, tokens_sold, sell_price, native_symbol,
                tx_link, chain, tokens_sold_value_usd, total_profit_usd, source_tweet_url,
                remaining_tokens, position_value, total_pnl_pct, profit_native,
                buyback_amount_sol, lotus_tokens, buyback_tx_hash
            )
            
            # Send message
            return await self._send_message(message)
            
        except Exception as e:
            logger.error(f"Error sending sell signal: {e}")
            return False
    
    async def send_trend_entry_notification(self,
                                          token_ticker: str,
                                          token_contract: str,
                                          chain: str,
                                          amount_native: float,
                                          price: float,
                                          tx_hash: str,
                                          dip_pct: float,
                                          batch_id: str,
                                          source_tweet_url: Optional[str] = None,
                                          amount_usd: Optional[float] = None) -> bool:
        """Send trend entry (dip buy) notification"""
        try:
            native_symbol = self._get_native_symbol(chain)
            tx_link = self._create_transaction_link(tx_hash, chain)
            token_link = self._create_token_link(token_contract, chain)
            
            timestamp = datetime.now(timezone.utc).strftime("%H:%M UTC")
            
            message = f"⚘ **LOTUS TREND ENTRY** ⟁\n\n"
            message += f"**Token:** [{token_ticker}]({token_link})\n"
            message += f"**Dip Buy:** {abs(dip_pct):.1f}% discount\n"
            
            if amount_usd:
                message += f"**Amount:** {amount_native:.4f} {native_symbol} (${amount_usd:.2f})\n"
            else:
                message += f"**Amount:** {amount_native:.4f} {native_symbol}\n"
                
            message += f"**Entry Price:** {price:.8f} {native_symbol}\n"
            message += f"**Batch ID:** {batch_id}\n"
            message += f"**Transaction:** [View on Explorer]({tx_link})\n"
            message += f"**Time:** {timestamp}\n"
            
            if source_tweet_url:
                message += f"**Source:** [Tweet]({source_tweet_url})\n"
            
            message += "\n🎯 Trend dip buy executed!"
            
            return await self._send_message(message)
            
        except Exception as e:
            logger.error(f"Error sending trend entry notification: {e}")
            return False
    
    async def send_trend_exit_notification(self,
                                         token_ticker: str,
                                         token_contract: str,
                                         chain: str,
                                         tokens_sold: float,
                                         sell_price: float,
                                         tx_hash: str,
                                         gain_pct: float,
                                         batch_id: str,
                                         profit_pct: Optional[float] = None,
                                         profit_usd: Optional[float] = None,
                                         profit_native: Optional[float] = None,
                                         source_tweet_url: Optional[str] = None) -> bool:
        """Send trend exit notification"""
        try:
            native_symbol = self._get_native_symbol(chain)
            tx_link = self._create_transaction_link(tx_hash, chain)
            token_link = self._create_token_link(token_contract, chain)
            
            timestamp = datetime.now(timezone.utc).strftime("%H:%M UTC")
            
            message = f"⚘ **LOTUS TREND EXIT** ⟁\n\n"
            message += f"**Token:** [{token_ticker}]({token_link})\n"
            message += f"**Gain Target:** +{gain_pct:.1f}%\n"
            message += f"**Amount Sold:** {tokens_sold:.2f} tokens\n"
            message += f"**Sell Price:** ${sell_price:.8f}\n"
            message += f"**Batch ID:** {batch_id}\n"
            message += f"**Transaction:** [View on Explorer]({tx_link})\n"
            
            if profit_pct is not None:
                emoji = "📈" if profit_pct > 0 else "📉"
                message += f"**P&L:** {emoji} {profit_pct:+.1f}%\n"
            
            if profit_native is not None:
                emoji = "💰" if profit_native > 0 else "💸"
                message += f"**Native P&L:** {emoji} {profit_native:+.6f} {native_symbol}\n"
            
            if profit_usd is not None:
                emoji = "💰" if profit_usd > 0 else "💸"
                message += f"**USD P&L:** {emoji} ${profit_usd:+.2f}\n"
            
            message += f"**Time:** {timestamp}\n"
            
            if source_tweet_url:
                message += f"**Source:** [Tweet]({source_tweet_url})\n"
            
            message += "\n🎯 Trend exit executed!"
            
            return await self._send_message(message)
            
        except Exception as e:
            logger.error(f"Error sending trend exit notification: {e}")
            return False
    
    def _get_native_symbol(self, chain: str) -> str:
        """Get native currency symbol for chain"""
        symbols = {
            'bsc': 'BNB',
            'base': 'ETH',
            'ethereum': 'ETH',
            'solana': 'SOL'
        }
        return symbols.get(chain.lower(), 'ETH')
    
    def _create_transaction_link(self, tx_hash: str, chain: str) -> str:
        """Create transaction explorer link"""
        # Ensure tx_hash has 0x prefix for EVM chains
        if chain.lower() in ['bsc', 'base', 'ethereum'] and not tx_hash.startswith('0x'):
            tx_hash = f"0x{tx_hash}"
        
        explorers = {
            'bsc': f"https://bscscan.com/tx/{tx_hash}",
            'base': f"https://basescan.org/tx/{tx_hash}",
            'ethereum': f"https://etherscan.io/tx/{tx_hash}",
            'solana': f"https://solscan.io/tx/{tx_hash}"
        }
        return explorers.get(chain.lower(), f"https://etherscan.io/tx/{tx_hash}")
    
    def _create_token_link(self, contract: str, chain: str) -> str:
        """Create token explorer link"""
        explorers = {
            'bsc': f"https://bscscan.com/token/{contract}",
            'base': f"https://basescan.org/token/{contract}",
            'ethereum': f"https://etherscan.io/token/{contract}",
            'solana': f"https://solscan.io/token/{contract}"
        }
        return explorers.get(chain.lower(), f"https://etherscan.io/token/{contract}")
    
    def _format_buy_message(self, 
                          token_ticker: str, 
                          token_link: str, 
                          amount_native: float, 
                          native_symbol: str,
                          price: float, 
                          tx_link: str, 
                          source_tweet_url: Optional[str] = None,
                          allocation_pct: Optional[float] = None,
                          amount_usd: Optional[float] = None) -> str:
        """Format buy signal message"""
        timestamp = datetime.now(timezone.utc).strftime("%H:%M UTC")
        
        message = f"⚘ **LOTUS BUY SIGNAL** ⟁\n\n"
        message += f"**Token:** [{token_ticker}]({token_link})\n"
        
        # Show native amount with USD equivalent if available
        if amount_usd:
            message += f"**Amount:** {amount_native:.4f} {native_symbol} (${amount_usd:.2f})\n"
        else:
            message += f"**Amount:** {amount_native:.4f} {native_symbol}\n"
            
        message += f"**Entry Price:** {price:.8f} {native_symbol}\n"
        
        if allocation_pct:
            message += f"**Allocation:** {allocation_pct:.1f}% of portfolio\n"
        
        message += f"**Transaction:** [View on Explorer]({tx_link})\n"
        message += f"**Time:** {timestamp}\n"
        
        if source_tweet_url:
            message += f"**Source:** [Tweet]({source_tweet_url})\n"
        
        message += "\n🚀 Position opened successfully!"
        
        return message
    
    def _format_sell_message(self,
                           token_ticker: str,
                           token_link: str,
                           tokens_sold: float,
                           sell_price: float,
                           native_symbol: str,
                           tx_link: str,
                           chain: str,
                           tokens_sold_value_usd: Optional[float] = None,
                           total_profit_usd: Optional[float] = None,
                           source_tweet_url: Optional[str] = None,
                           remaining_tokens: Optional[float] = None,
                           position_value: Optional[float] = None,
                           total_pnl_pct: Optional[float] = None,
                           profit_native: Optional[float] = None,
                           buyback_amount_sol: Optional[float] = None,
                           lotus_tokens: Optional[float] = None,
                           buyback_tx_hash: Optional[str] = None) -> str:
        """Format sell signal message"""
        timestamp = datetime.now(timezone.utc).strftime("%H:%M UTC")
        
        message = f"⚘ **LOTUS SELL SIGNAL** ⟁\n\n"
        message += f"**Token:** [{token_ticker}]({token_link})\n"
        message += f"**Amount Sold:** {tokens_sold:.2f} tokens\n"
        message += f"**Sell Price:** {sell_price:.8f} {native_symbol}\n"
        message += f"**Transaction:** [View on Explorer]({tx_link})\n"
        
        # Position context
        if remaining_tokens is not None:
            message += f"**Remaining:** {remaining_tokens:.2f} tokens\n"
        
        if position_value is not None:
            message += f"**Position Value:** ${position_value:.2f}\n"
        
        # Dollar value of tokens sold
        if tokens_sold_value_usd is not None:
            message += f"**$ of Tokens Sold:** ${tokens_sold_value_usd:.2f}\n"
        
        # Total position P&L information
        if total_profit_usd is not None:
            message += f"**Total Position P&L:** ${total_profit_usd:+.2f}\n"
        
        if total_pnl_pct is not None:
            emoji = "📈" if total_pnl_pct > 0 else "📉"
            message += f"**Total P&L %:** {emoji} {total_pnl_pct:+.1f}%\n"
        
        # Add Lotus buyback information if available
        if buyback_amount_sol is not None:
            # Calculate expected Lotus tokens from SOL amount and current price
            lotus_price_per_sol = self._get_lotus_price_per_sol()
            if lotus_price_per_sol and lotus_price_per_sol > 0:
                expected_lotus_tokens = buyback_amount_sol / lotus_price_per_sol
                message += f"⚘ **Lotus Buyback:** {buyback_amount_sol:.6f} SOL → {expected_lotus_tokens:.3f} ⚘❈ tokens\n"
            else:
                message += f"⚘ **Lotus Buyback:** {buyback_amount_sol:.6f} SOL → ? ⚘❈ tokens\n"
        
        # Add USDC conversion information for Base/BSC chains
        if chain.lower() in ['base', 'bsc'] and tokens_sold_value_usd is not None:
            # Calculate exit value in native currency
            exit_value_native = tokens_sold * sell_price
            # Calculate expected Lotus tokens from 10% USDC conversion
            usdc_lotus_tokens = self._get_usdc_conversion_to_lotus_tokens(exit_value_native, chain)
            if usdc_lotus_tokens and usdc_lotus_tokens > 0:
                usdc_amount_native = exit_value_native * 0.10
                message += f"⚘ **USDC Conversion:** {usdc_amount_native:.6f} {native_symbol} → {usdc_lotus_tokens:.3f} ⚘❈ tokens\n"
            else:
                usdc_amount_native = exit_value_native * 0.10
                message += f"⚘ **USDC Conversion:** {usdc_amount_native:.6f} {native_symbol} → ? ⚘❈ tokens\n"
        
        message += f"**Time:** {timestamp}\n"
        
        if source_tweet_url:
            message += f"**Source:** [Tweet]({source_tweet_url})\n"
        
        # Add celebration or commiseration based on total P&L percentage
        if total_pnl_pct and total_pnl_pct > 0:
            if total_pnl_pct > 100:
                message += "\n🎉 **MASSIVE WIN!** 🎉"
            elif total_pnl_pct > 50:
                message += "\n🔥 **Great trade!** 🔥"
            else:
                message += "\n✅ **Profit secured!** ✅"
        elif total_pnl_pct and total_pnl_pct < 0:
            message += "\n💪 **Learning experience!** 💪"
        
        return message
    
    # ============================================================================
    # New PM Notification Methods (matching design document)
    # ============================================================================
    
    async def send_entry_notification(
        self,
        token_ticker: str,
        token_contract: str,
        chain: str,
        timeframe: str,
        amount_usd: float,
        entry_price_usd: float,
        tx_hash: str,
        state: str,
        signal: str,
        a_score: float,
        e_score: float,
        allocation_pct: Optional[float] = None,
        source_tweet_url: Optional[str] = None
    ) -> bool:
        """Send entry notification (initial position)"""
        try:
            state_glyph = self._stage_glyph(state)
            tx_link = self._create_transaction_link(tx_hash, chain)
            token_link = self._create_token_link(token_contract, chain)
            timestamp = datetime.now(timezone.utc).strftime("%H:%M UTC")
            
            # Format signal description
            signal_desc = {
                "buy_signal": "Entry zone (S1)",
                "buy_flag": "Retest buy (S2)" if state == "S2" else "Entry",
                "first_dip_buy_flag": "First dip buy (S3)",
                "reclaimed_ema333": "Reclaimed EMA333 (S3)"
            }.get(signal, signal)
            
            message = f"⚘𒀭 **LOTUS TRADER ENTRY** ⚘⟁⌖\n\n"
            message += f"**Token:** [{token_ticker}]({token_link})\n"
            message += f"**Chain:** {chain.upper()}\n"
            message += f"**Timeframe:** {timeframe}\n\n"
            message += f"**Amount:** ${amount_usd:.2f}\n"
            message += f"**Entry Price:** ${entry_price_usd:.8f}\n"
            if allocation_pct:
                message += f"**Allocation:** {allocation_pct:.1f}% of portfolio\n\n"
            message += f"**State:** {state_glyph}\n"
            message += f"**Signal:** {signal_desc}\n"
            message += f"**A/E:** {a_score:.2f}/{e_score:.2f}\n\n"
            message += f"**Transaction:** [View]({tx_link})\n"
            message += f"**Time:** {timestamp}\n"
            if source_tweet_url:
                message += f"**Source:** [Tweet]({source_tweet_url})\n"
            message += f"\n⚘𒀭 **POSITION OPENED** ⚘⟁⌖"
            
            return await self._send_message(message)
        except Exception as e:
            logger.error(f"Error sending entry notification: {e}")
            return False
    
    async def send_add_notification(
        self,
        token_ticker: str,
        token_contract: str,
        chain: str,
        timeframe: str,
        amount_usd: float,
        entry_price_usd: float,
        tx_hash: str,
        state: str,
        signal: str,
        a_score: float,
        e_score: float,
        size_frac: float,
        position_size: float,
        position_value_usd: float,
        avg_entry_price_usd: float,
        total_pnl_usd: float,
        total_pnl_pct: float,
        rpnl_usd: float,
        rpnl_pct: float,
        source_tweet_url: Optional[str] = None
    ) -> bool:
        """Send add notification (scaling up position)"""
        try:
            state_glyph = self._stage_glyph(state)
            tx_link = self._create_transaction_link(tx_hash, chain)
            token_link = self._create_token_link(token_contract, chain)
            timestamp = datetime.now(timezone.utc).strftime("%H:%M UTC")
            
            # Format signal description
            signal_desc = {
                "buy_flag": "Retest add (S2)" if state == "S2" else "DX buy (S3)",
                "reclaimed_ema333": "Auto-rebuy (S3)"
            }.get(signal, signal)
            
            message = f"⚘⥈ **LOTUS TRADER ADD** ⚘⟁⌖\n\n"
            message += f"**Token:** [{token_ticker}]({token_link})\n"
            message += f"**Chain:** {chain.upper()}\n"
            message += f"**Timeframe:** {timeframe}\n\n"
            message += f"**Amount Added:** ${amount_usd:.2f}\n"
            message += f"**Entry Price:** ${entry_price_usd:.8f}\n"
            message += f"**Size:** {size_frac*100:.1f}% of remaining allocation\n\n"
            message += f"**State:** {state_glyph}\n"
            message += f"**Signal:** {signal_desc}\n"
            message += f"**A/E:** {a_score:.2f}/{e_score:.2f}\n\n"
            message += f"**Position Size:** {position_size:.2f} tokens\n"
            message += f"**Position Value:** ${position_value_usd:.2f}\n"
            message += f"**Avg Entry:** ${avg_entry_price_usd:.8f}\n\n"
            message += f"**Current P&L:** ${total_pnl_usd:+.2f} ({total_pnl_pct:+.1f}%)\n"
            message += f"**Realized P&L:** ${rpnl_usd:+.2f} ({rpnl_pct:+.1f}%)\n\n"
            message += f"**Transaction:** [View]({tx_link})\n"
            message += f"**Time:** {timestamp}\n"
            if source_tweet_url:
                message += f"**Source:** [Tweet]({source_tweet_url})\n"
            message += f"\n⚘⥈ **POSITION SCALED UP** ⚘⟁⌖"
            
            return await self._send_message(message)
        except Exception as e:
            logger.error(f"Error sending add notification: {e}")
            return False
    
    async def send_trim_notification(
        self,
        token_ticker: str,
        token_contract: str,
        chain: str,
        timeframe: str,
        tokens_sold: float,
        sell_price_usd: float,
        value_extracted_usd: float,
        size_frac: float,
        tx_hash: str,
        state: str,
        signal: str,
        e_score: float,
        remaining_tokens: float,
        position_value_usd: float,
        total_pnl_usd: float,
        total_pnl_pct: float,
        rpnl_usd: float,
        rpnl_pct: float,
        source_tweet_url: Optional[str] = None
    ) -> bool:
        """Send trim notification (partial exit)"""
        logger.info(
            f"TELEGRAM NOTIFICATION: send_trim_notification called | "
            f"{token_ticker}/{chain} tf={timeframe} | "
            f"tokens_sold={tokens_sold:.2f} tx_hash={tx_hash[:8] if tx_hash else 'None'}"
        )
        try:
            state_glyph = self._stage_glyph(state)
            tx_link = self._create_transaction_link(tx_hash, chain)
            token_link = self._create_token_link(token_contract, chain)
            timestamp = datetime.now(timezone.utc).strftime("%H:%M UTC")
            
            # Format signal description
            signal_desc = {
                "trim_flag": "Profit trim (S2)" if state == "S2" else "Exhaustion trim (S3)"
            }.get(signal, signal)
            
            message = f"⚘𒋻 **LOTUS TRADER TRIM** ⚘⟁⌖\n\n"
            message += f"**Token:** [{token_ticker}]({token_link})\n"
            message += f"**Chain:** {chain.upper()}\n"
            message += f"**Timeframe:** {timeframe}\n\n"
            message += f"**Amount Sold:** {tokens_sold:.2f} tokens\n"
            message += f"**Sell Price:** ${sell_price_usd:.8f}\n"
            message += f"**Value Extracted:** ${value_extracted_usd:.2f}\n"
            message += f"**Size:** {size_frac*100:.1f}% of position\n\n"
            message += f"**State:** {state_glyph}\n"
            message += f"**Signal:** {signal_desc}\n"
            message += f"**E Score:** {e_score:.2f}\n\n"
            message += f"**Remaining:** {remaining_tokens:.2f} tokens\n"
            message += f"**Position Value:** ${position_value_usd:.2f}\n\n"
            message += f"**Current P&L:** ${total_pnl_usd:+.2f} ({total_pnl_pct:+.1f}%)\n"
            message += f"**Realized P&L:** ${rpnl_usd:+.2f} ({rpnl_pct:+.1f}%)\n\n"
            message += f"**Transaction:** [View]({tx_link})\n"
            message += f"**Time:** {timestamp}\n"
            if source_tweet_url:
                message += f"**Source:** [Tweet]({source_tweet_url})\n"
            message += f"\n⚘𒋻 **PARTIAL PROFIT SECURED** ⚘𒋻"
            
            result = await self._send_message(message)
            if result:
                logger.info(f"TELEGRAM NOTIFICATION SUCCESS: trim {token_ticker}/{chain} tf={timeframe}")
            else:
                logger.warning(f"TELEGRAM NOTIFICATION FAILED: trim {token_ticker}/{chain} tf={timeframe} (_send_message returned False)")
            return result
        except Exception as e:
            logger.error(f"TELEGRAM NOTIFICATION ERROR: trim {token_ticker}/{chain} tf={timeframe} - {e}", exc_info=True)
            return False
    
    async def send_emergency_exit_notification(
        self,
        token_ticker: str,
        token_contract: str,
        chain: str,
        timeframe: str,
        tokens_sold: float,
        sell_price_usd: float,
        value_extracted_usd: float,
        tx_hash: str,
        state: str,
        reason: str,
        e_score: float,
        total_pnl_usd: float,
        total_pnl_pct: float,
        rpnl_usd: float,
        rpnl_pct: float,
        source_tweet_url: Optional[str] = None
    ) -> bool:
        """Send emergency exit notification (full exit)"""
        logger.info(
            f"TELEGRAM NOTIFICATION: send_emergency_exit_notification called | "
            f"{token_ticker}/{chain} tf={timeframe} | "
            f"tokens_sold={tokens_sold:.2f} tx_hash={tx_hash[:8] if tx_hash else 'None'} reason={reason}"
        )
        try:
            state_glyph = self._stage_glyph(state)
            tx_link = self._create_transaction_link(tx_hash, chain)
            token_link = self._create_token_link(token_contract, chain)
            timestamp = datetime.now(timezone.utc).strftime("%H:%M UTC")
            
            # Format reason
            reason_desc = {
                "structural_exit": "Structural exit",
                "trend_ending": "Trend ending",
                "emergency_exit": "Trend ending" if state == "S3" else "Structural exit"
            }.get(reason.lower(), reason)
            
            message = f"⚘𒉿 **LOTUS TRADER EXIT** ⚘⟁⌖\n\n"
            message += f"**Token:** [{token_ticker}]({token_link})\n"
            message += f"**Chain:** {chain.upper()}\n"
            message += f"**Timeframe:** {timeframe}\n\n"
            message += f"**Amount Sold:** {tokens_sold:.2f} tokens\n"
            message += f"**Sell Price:** ${sell_price_usd:.8f}\n"
            message += f"**Value Extracted:** ${value_extracted_usd:.2f}\n\n"
            message += f"**State:** {state_glyph}\n"
            message += f"**Reason:** {reason_desc}\n"
            message += f"**E Score:** {e_score:.2f}\n\n"
            message += f"**Total P&L:** ${total_pnl_usd:+.2f} ({total_pnl_pct:+.1f}%)\n"
            message += f"**Realized P&L:** ${rpnl_usd:+.2f} ({rpnl_pct:+.1f}%)\n\n"
            message += f"**Transaction:** [View]({tx_link})\n"
            message += f"**Time:** {timestamp}\n"
            if source_tweet_url:
                message += f"**Source:** [Tweet]({source_tweet_url})\n"
            message += f"\n⚘𒉿 **FINAL EXIT - TREND ENDED** ⚘𒉿"
            
            result = await self._send_message(message)
            if result:
                logger.info(f"TELEGRAM NOTIFICATION SUCCESS: emergency_exit {token_ticker}/{chain} tf={timeframe}")
            else:
                logger.warning(f"TELEGRAM NOTIFICATION FAILED: emergency_exit {token_ticker}/{chain} tf={timeframe} (_send_message returned False)")
            return result
        except Exception as e:
            logger.error(f"TELEGRAM NOTIFICATION ERROR: emergency_exit {token_ticker}/{chain} tf={timeframe} - {e}", exc_info=True)
            return False
    
    async def send_position_summary_notification(
        self,
        token_ticker: str,
        token_contract: str,
        chain: str,
        timeframe: str,
        final_exit_type: str,
        exit_reason: str,
        total_allocation_usd: float,
        total_extracted_usd: float,
        rpnl_usd: float,
        rpnl_pct: float,
        total_pnl_usd: float,
        total_pnl_pct: float,
        hold_time_days: Optional[float] = None,
        rr: Optional[float] = None,
        return_mult: Optional[float] = None,
        max_drawdown_pct: Optional[float] = None,
        max_gain_mult: Optional[float] = None,
        completed_trades: Optional[int] = None,
        entry_context: Optional[str] = None,
        lotus_buyback: Optional[Dict[str, Any]] = None,
        source_tweet_url: Optional[str] = None
    ) -> bool:
        """Send position summary notification (full closure confirmation)"""
        logger.info(
            f"TELEGRAM NOTIFICATION: send_position_summary_notification called | "
            f"{token_ticker}/{chain} tf={timeframe} | "
            f"exit_type={final_exit_type} total_invested=${total_allocation_usd:.2f} total_extracted=${total_extracted_usd:.2f}"
        )
        try:
            token_link = self._create_token_link(token_contract, chain)
            timestamp = datetime.now(timezone.utc).strftime("%H:%M UTC")
            
            message = f"⚘🝗⩜ **LOTUS TRADER POSITION SUMMARY** ⚘⟁⌖\n\n"
            message += f"**Token:** [{token_ticker}]({token_link})\n"
            message += f"**Chain:** {chain.upper()}\n"
            message += f"**Timeframe:** {timeframe}\n\n"
            message += f"**Final Exit:** {final_exit_type}\n"
            message += f"**Exit Reason:** {exit_reason}\n\n"
            message += f"**Total Invested:** ${total_allocation_usd:.2f}\n"
            message += f"**Total Extracted:** ${total_extracted_usd:.2f}\n"
            message += f"**Realized P&L:** ${rpnl_usd:+.2f} ({rpnl_pct:+.1f}%)\n"
            message += f"**Total P&L:** ${total_pnl_usd:+.2f} ({total_pnl_pct:+.1f}%)\n\n"
            
            if hold_time_days is not None:
                message += f"**Hold Time:** {hold_time_days:.1f} days\n"
            if rr is not None:
                message += f"**R/R:** {rr:.2f}\n"
            if return_mult is not None:
                message += f"**Return:** {return_mult:.2f}x\n"
            if max_drawdown_pct is not None:
                message += f"**Max Drawdown:** {max_drawdown_pct:.1f}%\n"
            if max_gain_mult is not None:
                message += f"**Max Gain:** {max_gain_mult:.2f}x\n"
            
            # Lotus buyback section
            if lotus_buyback and lotus_buyback.get("success"):
                message += f"\n⚘❈ **LOTUS BUYBACK**⚘❈\n"
                profit_usd = lotus_buyback.get("profit_usd", 0)
                swap_amount_usd = lotus_buyback.get("swap_amount_usd", 0)
                lotus_tokens = lotus_buyback.get("lotus_tokens", 0)
                transfer_amount = lotus_buyback.get("lotus_tokens_transferred", 0)
                swap_tx = lotus_buyback.get("swap_tx_hash")
                transfer_tx = lotus_buyback.get("transfer_tx_hash")
                
                message += f"**Profit:** ${profit_usd:.2f}\n"
                message += f"**Swap Amount:** ${swap_amount_usd:.2f} (10%)\n"
                message += f"**Lotus Tokens:** {lotus_tokens:.6f} ⚘❈\n"
                message += f"**Transfer:** {transfer_amount:.6f} ⚘❈ → Holding Wallet\n"
                if swap_tx:
                    swap_link = self._create_transaction_link(swap_tx, "solana")
                    message += f"**Swap TX:** [View]({swap_link})\n"
                if transfer_tx:
                    transfer_link = self._create_transaction_link(transfer_tx, "solana")
                    message += f"**Transfer TX:** [View]({transfer_link})\n"
            elif lotus_buyback and not lotus_buyback.get("success"):
                message += f"\n⚘❈ **LOTUS BUYBACK**⚘❈\n"
                message += f"**Status:** Failed\n"
                message += f"**Error:** {lotus_buyback.get('error', 'Unknown error')}\n"
            
            if completed_trades is not None:
                message += f"\n**Completed Trades:** {completed_trades}\n"
            if entry_context:
                message += f"**Entry Context:** {entry_context}\n"
            
            message += f"\n**Time:** {timestamp}\n"
            if source_tweet_url:
                message += f"**Source:** [Tweet]({source_tweet_url})\n"
            message += f"\n⚘🝗⩜ **TREND ENDED PROFIT SECURED** ⚘🝗⩜"
            
            result = await self._send_message(message)
            if result:
                logger.info(f"TELEGRAM NOTIFICATION SUCCESS: position_summary {token_ticker}/{chain} tf={timeframe}")
            else:
                logger.warning(f"TELEGRAM NOTIFICATION FAILED: position_summary {token_ticker}/{chain} tf={timeframe} (_send_message returned False)")
            return result
        except Exception as e:
            logger.error(f"TELEGRAM NOTIFICATION ERROR: position_summary {token_ticker}/{chain} tf={timeframe} - {e}", exc_info=True)
            return False
    
    async def _send_message(self, message: str) -> bool:
        """Send message to Telegram channel"""
        try:
            client = await self._get_client()
            
            # Send message with markdown formatting
            await client.send_message(
                entity=self.channel_id,
                message=message,
                parse_mode='markdown',
                link_preview=False
            )
            
            logger.info(f"Signal notification sent to {self.channel_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """Test connection to Telegram channel"""
        try:
            client = await self._get_client()
            
            # Try to get channel info
            entity = await client.get_entity(self.channel_id)
            logger.info(f"Successfully connected to channel: {entity.title}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Telegram channel: {e}")
            return False
    
    async def close(self):
        """Close Telegram client connection"""
        if self.client and self.client.is_connected():
            await self.client.disconnect()
            logger.info("Telegram Signal Notifier connection closed")


# Example usage and testing
async def test_signal_notifier():
    """Test the signal notifier with sample data"""
    
    # Configuration - you'll need to set these
    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
    CHANNEL_ID = "@your_channel_username"  # or numeric ID
    API_ID = 21826741  # Your existing API ID
    API_HASH = "4643cce207a1a9d56d56a5389a4f1f52"  # Your existing API hash
    
    notifier = TelegramSignalNotifier(BOT_TOKEN, CHANNEL_ID, API_ID, API_HASH)
    
    # Test connection
    if await notifier.test_connection():
        print("✅ Connection test successful!")
        
        # Test buy signal
        await notifier.send_buy_signal(
            token_ticker="PEPE",
            token_contract="0x6982508145454Ce325dDbE47a25d4ec3d2311933",
            chain="base",
            amount_native=0.1,
            price=0.00000123,
            tx_hash="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            source_tweet_url="https://twitter.com/example/status/1234567890",
            allocation_pct=2.5
        )
        
        # Test sell signal
        await notifier.send_sell_signal(
            token_ticker="PEPE",
            token_contract="0x6982508145454Ce325dDbE47a25d4ec3d2311933",
            chain="base",
            tokens_sold=1000000,
            sell_price=0.00000246,
            tx_hash="0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            profit_pct=100.0,
            profit_usd=123.45,
            total_profit_usd=123.45,
            source_tweet_url="https://twitter.com/example/status/1234567890"
        )
        
        print("✅ Test signals sent!")
    
    await notifier.close()


if __name__ == "__main__":
    asyncio.run(test_signal_notifier())
