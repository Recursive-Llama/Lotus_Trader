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

logger = logging.getLogger(__name__)


class TelegramSignalNotifier:
    """Sends trading signals to Telegram group with rich formatting"""
    
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
        
        logger.info(f"Telegram Signal Notifier initialized for channel: {channel_id}")
    
    async def _get_client(self) -> TelegramClient:
        """Get or create Telegram client"""
        if not self.client:
            if os.path.exists(self.session_file):
                with open(self.session_file, 'r') as f:
                    session_string = f.read().strip()
                self.client = TelegramClient(StringSession(session_string), self.api_id, self.api_hash)
            else:
                # Fallback to bot client if no session file
                self.client = TelegramClient('signal_bot', self.api_id, self.api_hash)
                await self.client.start(bot_token=self.bot_token)
        
        if not self.client.is_connected():
            await self.client.start()
        
        return self.client
    
    async def send_buy_signal(self, 
                            token_ticker: str, 
                            token_contract: str, 
                            chain: str, 
                            amount_native: float, 
                            price: float, 
                            tx_hash: str,
                            source_tweet_url: Optional[str] = None,
                            allocation_pct: Optional[float] = None) -> bool:
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
                price, tx_link, source_tweet_url, allocation_pct
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
                             profit_pct: Optional[float] = None,
                             profit_usd: Optional[float] = None,
                             total_profit_usd: Optional[float] = None,
                             source_tweet_url: Optional[str] = None) -> bool:
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
                tx_link, profit_pct, profit_usd, total_profit_usd, source_tweet_url
            )
            
            # Send message
            return await self._send_message(message)
            
        except Exception as e:
            logger.error(f"Error sending sell signal: {e}")
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
                          allocation_pct: Optional[float] = None) -> str:
        """Format buy signal message"""
        timestamp = datetime.now(timezone.utc).strftime("%H:%M UTC")
        
        message = f"🟢 **LOTUS BUY SIGNAL** 🟢\n\n"
        message += f"**Token:** [{token_ticker}]({token_link})\n"
        message += f"**Amount:** {amount_native:.4f} {native_symbol}\n"
        message += f"**Entry Price:** ${price:.8f}\n"
        
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
                           profit_pct: Optional[float] = None,
                           profit_usd: Optional[float] = None,
                           total_profit_usd: Optional[float] = None,
                           source_tweet_url: Optional[str] = None) -> str:
        """Format sell signal message"""
        timestamp = datetime.now(timezone.utc).strftime("%H:%M UTC")
        
        message = f"🔴 **LOTUS SELL SIGNAL** 🔴\n\n"
        message += f"**Token:** [{token_ticker}]({token_link})\n"
        message += f"**Amount Sold:** {tokens_sold:.2f} tokens\n"
        message += f"**Sell Price:** ${sell_price:.8f}\n"
        message += f"**Transaction:** [View on Explorer]({tx_link})\n"
        
        if profit_pct is not None:
            emoji = "📈" if profit_pct > 0 else "📉"
            message += f"**Profit:** {emoji} {profit_pct:+.1f}%\n"
        
        if profit_usd is not None:
            emoji = "💰" if profit_usd > 0 else "💸"
            message += f"**P&L:** {emoji} ${profit_usd:+.2f}\n"
        
        if total_profit_usd is not None:
            message += f"**Total Position P&L:** ${total_profit_usd:+.2f}\n"
        
        message += f"**Time:** {timestamp}\n"
        
        if source_tweet_url:
            message += f"**Source:** [Tweet]({source_tweet_url})\n"
        
        # Add celebration or commiseration
        if profit_pct and profit_pct > 0:
            if profit_pct > 100:
                message += "\n🎉 **MASSIVE WIN!** 🎉"
            elif profit_pct > 50:
                message += "\n🔥 **Great trade!** 🔥"
            else:
                message += "\n✅ **Profit secured!** ✅"
        elif profit_pct and profit_pct < 0:
            message += "\n💪 **Learning experience!** 💪"
        
        return message
    
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
