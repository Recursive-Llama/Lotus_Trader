#!/usr/bin/env python3
"""
Wallet Manager for Multi-Chain Trading

Manages wallet operations across Solana, Ethereum, and Base networks.
Handles key generation, balance checking, and transaction signing.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Union
from decimal import Decimal
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Solana imports
try:
    from solana.rpc.api import Client
    from solana.rpc.types import TxOpts
    from solders.keypair import Keypair
    from solders.pubkey import Pubkey as PublicKey
    from solders.transaction import Transaction
    from solders.system_program import transfer, TransferParams
    SOLANA_AVAILABLE = True
except ImportError:
    SOLANA_AVAILABLE = False
    Keypair = None
    logging.warning("Solana libraries not available. Install with: pip install solana")

# Ethereum imports
try:
    from web3 import Web3
    from eth_account import Account
    from eth_account.signers.local import LocalAccount
    ETHEREUM_AVAILABLE = True
except ImportError:
    ETHEREUM_AVAILABLE = False
    LocalAccount = None
    logging.warning("Ethereum libraries not available. Install with: pip install web3 eth-account")

logger = logging.getLogger(__name__)


class WalletManager:
    """
    Multi-chain wallet manager for trading operations
    
    Supports:
    - Solana (via Solana RPC)
    - Ethereum (via Web3)
    - Base (via Web3 with Base RPC)
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize wallet manager
        
        Args:
            config: Configuration dictionary with RPC URLs and API keys
        """
        self.config = config or {}
        self.wallets = {}
        self.rpc_clients = {}
        
        # Initialize RPC clients
        self._setup_rpc_clients()
        
        # Load existing wallets from .env
        self._load_wallets()
    
    def _setup_rpc_clients(self):
        """Setup RPC clients for each network"""
        try:
            # Solana RPC (via Helius)
            helius_key = os.getenv('HELIUS_API_KEY')
            if helius_key and SOLANA_AVAILABLE:
                self.rpc_clients['solana'] = Client(f"https://mainnet.helius-rpc.com/?api-key={helius_key}")
                logger.info("✅ Solana RPC client initialized (Helius)")
            elif SOLANA_AVAILABLE:
                # Fallback to public RPC
                self.rpc_clients['solana'] = Client("https://api.mainnet-beta.solana.com")
                logger.warning("⚠️ Using public Solana RPC (no Helius key)")
            
            # Ethereum RPC
            if ETHEREUM_AVAILABLE:
                ethereum_rpc = self.config.get('ethereum_rpc', 'https://eth.llamarpc.com')
                self.rpc_clients['ethereum'] = Web3(Web3.HTTPProvider(ethereum_rpc))
                
                # Base RPC
                base_rpc = self.config.get('base_rpc', 'https://mainnet.base.org')
                self.rpc_clients['base'] = Web3(Web3.HTTPProvider(base_rpc))
                
                # BSC RPC
                bsc_rpc = self.config.get('bsc_rpc', 'https://bsc-dataseed.binance.org')
                self.rpc_clients['bsc'] = Web3(Web3.HTTPProvider(bsc_rpc))
                
                logger.info("✅ Ethereum, Base, and BSC RPC clients initialized")
            
        except Exception as e:
            logger.error(f"Error setting up RPC clients: {e}")
    
    def _load_wallets(self):
        """Load wallets from environment variables"""
        try:
            # Load Solana wallet
            solana_key = os.getenv('SOL_WALLET_PRIVATE_KEY')
            if solana_key and SOLANA_AVAILABLE:
                self.wallets['solana'] = self._load_solana_wallet(solana_key)
                logger.info("✅ Solana wallet loaded")
            
            # Load Ethereum wallet
            eth_key = os.getenv('ETHEREUM_WALLET_PRIVATE_KEY')
            if eth_key and ETHEREUM_AVAILABLE:
                self.wallets['ethereum'] = self._load_ethereum_wallet(eth_key)
                logger.info("✅ Ethereum wallet loaded")
            
            # Base and BSC use the same wallet as Ethereum (same private key, different network)
            if 'ethereum' in self.wallets:
                self.wallets['base'] = self.wallets['ethereum']
                self.wallets['bsc'] = self.wallets['ethereum']
                logger.info("✅ Base and BSC wallets (reusing Ethereum wallet)")
            
            if not self.wallets:
                logger.warning("⚠️ No wallets loaded. Add private keys to .env file")
                
        except Exception as e:
            logger.error(f"Error loading wallets: {e}")
    
    def _load_solana_wallet(self, private_key: str) -> Optional[Any]:
        """Load Solana wallet from private key"""
        try:
            if private_key.startswith('[') and private_key.endswith(']'):
                # Array format: [1,2,3,...]
                key_bytes = json.loads(private_key)
                return Keypair.from_bytes(bytes(key_bytes))
            elif len(private_key) == 88:  # Base58 format (88 characters)
                # Base58 format - decode to bytes
                import base58
                key_bytes = base58.b58decode(private_key)
                if len(key_bytes) == 32:
                    # 32 bytes = secret only, need to create keypair from seed
                    return Keypair.from_seed(key_bytes)
                elif len(key_bytes) == 64:
                    # 64 bytes = full keypair
                    return Keypair.from_bytes(key_bytes)
                else:
                    raise ValueError(f"Invalid Base58 key length: {len(key_bytes)} bytes")
            else:
                # Hex format - check if it's 32 bytes (secret only) or 64 bytes (full keypair)
                key_bytes = bytes.fromhex(private_key)
                if len(key_bytes) == 32:
                    # 32 bytes = secret only, need to create keypair from seed
                    return Keypair.from_seed(key_bytes)
                elif len(key_bytes) == 64:
                    # 64 bytes = full keypair
                    return Keypair.from_bytes(key_bytes)
                else:
                    raise ValueError(f"Invalid key length: {len(key_bytes)} bytes")
        except Exception as e:
            logger.error(f"Error loading Solana wallet: {e}")
            return None
    
    def _load_ethereum_wallet(self, private_key: str) -> Optional[Any]:
        """Load Ethereum/Base wallet from private key"""
        try:
            if private_key.startswith('0x'):
                private_key = private_key[2:]
            
            account = Account.from_key(private_key)
            return account
        except Exception as e:
            logger.error(f"Error loading Ethereum wallet: {e}")
            return None
    
    def generate_solana_wallet(self) -> Optional[Dict[str, str]]:
        """Generate a new Solana wallet and return key info"""
        try:
            if not SOLANA_AVAILABLE:
                logger.error("Solana libraries not available")
                return None
            
            # Generate new keypair
            keypair = Keypair()
            keypair_bytes = keypair.to_bytes()
            
            # Convert to hex format for .env
            private_key_hex = keypair_bytes.hex()
            
            return {
                'address': str(keypair.pubkey()),
                'private_key': private_key_hex,
                'chain': 'solana'
            }
            
        except Exception as e:
            logger.error(f"Error generating Solana wallet: {e}")
            return None
    
    def generate_ethereum_wallet(self) -> Optional[Dict[str, str]]:
        """Generate a new Ethereum wallet and return key info"""
        try:
            if not ETHEREUM_AVAILABLE:
                logger.error("Ethereum libraries not available")
                return None
            
            # Generate new account
            account = Account.create()
            private_key_hex = account.key.hex()
            
            return {
                'address': account.address,
                'private_key': private_key_hex,
                'chain': 'ethereum'
            }
            
        except Exception as e:
            logger.error(f"Error generating Ethereum wallet: {e}")
            return None
    
    
    def get_wallet_address(self, chain: str) -> Optional[str]:
        """Get wallet address for a specific chain"""
        try:
            if chain == 'solana' and 'solana' in self.wallets:
                return str(self.wallets['solana'].pubkey())
            elif chain in ['ethereum', 'base'] and chain in self.wallets:
                return self.wallets[chain].address
            else:
                logger.warning(f"No wallet available for chain: {chain}")
                return None
        except Exception as e:
            logger.error(f"Error getting wallet address for {chain}: {e}")
            return None
    
    async def get_balance(self, chain: str, token_address: str = None) -> Optional[Decimal]:
        """
        Get wallet balance for a specific chain
        
        Args:
            chain: Blockchain network (solana, ethereum, base, bsc, lotus)
            token_address: Token contract address (None for native token)
            
        Returns:
            Balance in native units (SOL, ETH, etc.)
        """
        try:
            if chain == 'solana':
                return await self._get_solana_balance(token_address)
            elif chain == 'lotus':
                return await self._get_lotus_balance()
            elif chain in ['ethereum', 'base', 'bsc']:
                return await self._get_ethereum_balance(chain, token_address)
            else:
                logger.error(f"Unsupported chain: {chain}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting balance for {chain}: {e}")
            return None
    
    async def _get_solana_balance(self, token_address: str = None) -> Optional[Decimal]:
        """Get Solana balance (SOL or SPL token)"""
        print(f"DEBUG: WalletManager _get_solana_balance called with token_address: {token_address}")
        logger.warning(f"WalletManager _get_solana_balance called with token_address: {token_address}")
        try:
            if not self.wallets.get('solana') or 'solana' not in self.rpc_clients:
                logger.warning("WalletManager: No Solana wallet or RPC client available")
                return None
            
            client = self.rpc_clients['solana']
            wallet_pubkey = self.wallets['solana'].pubkey()
            
            if token_address:
                # SPL token balance
                try:
                    # Get the JSSolanaClient from the trader if available
                    logger.warning(f"WalletManager trader reference: {hasattr(self, 'trader')}")
                    if hasattr(self, 'trader'):
                        logger.warning(f"WalletManager trader object: {self.trader}")
                        if self.trader:
                            logger.warning(f"WalletManager trader has js_solana_client: {hasattr(self.trader, 'js_solana_client')}")
                            if hasattr(self.trader, 'js_solana_client'):
                                logger.warning(f"WalletManager js_solana_client: {self.trader.js_solana_client}")
                    
                    if hasattr(self, 'trader') and self.trader and hasattr(self.trader, 'js_solana_client') and self.trader.js_solana_client:
                        js_client = self.trader.js_solana_client
                        logger.warning(f"Calling comprehensive token balance for {token_address}")
                        result = await js_client.get_spl_token_balance(token_address, str(wallet_pubkey))
                        logger.warning(f"Comprehensive token balance result: {result}")
                        
                        if result.get('success'):
                            # The new method returns the balance already converted to proper units
                            balance_str = result.get('balance', '0')
                            balance = Decimal(balance_str)
                            logger.warning(f"Token balance for {token_address}: {balance}")
                            return balance
                        else:
                            logger.warning(f"Failed to get token balance: {result.get('error')}")
                            return Decimal('0')
                    else:
                        logger.warning("JSSolanaClient not available for token balance check")
                        return None
                except Exception as e:
                    logger.error(f"Error getting SPL token balance: {e}")
                    return None
            else:
                # SOL balance
                balance = client.get_balance(wallet_pubkey)
                if balance.value is not None:
                    return Decimal(balance.value) / Decimal(10**9)  # Convert lamports to SOL
                else:
                    logger.error("Failed to get SOL balance")
                    return None
                
        except Exception as e:
            logger.error(f"Error getting Solana balance: {e}")
            return None
    
    async def _get_lotus_balance(self) -> Optional[Decimal]:
        """Get Lotus token balance from the correct Lotus wallet"""
        try:
            # Lotus token contract and correct wallet
            lotus_contract = 'Ch4tXj2qf8V6a4GdpS4X3pxAELvbnkiKTHGdmXjLEXsC'
            lotus_wallet = 'AbumtzzxomWWrm9uypY6ViRgruGdJBPFPM2vyHewTFdd'
            
            logger.info(f"Getting Lotus token balance from correct wallet: {lotus_wallet}")
            
            # Use JS client directly with the correct wallet address
            if hasattr(self, 'trader') and self.trader and hasattr(self.trader, 'js_solana_client') and self.trader.js_solana_client:
                js_client = self.trader.js_solana_client
                result = await js_client.get_spl_token_balance(lotus_contract, lotus_wallet)
                
                if result.get('success'):
                    balance_str = result.get('balance', '0')
                    balance = Decimal(balance_str)
                    logger.info(f"Lotus token balance from correct wallet: {balance}")
                    return balance
                else:
                    logger.warning(f"Failed to get Lotus token balance: {result.get('error')}")
                    return Decimal('0')
            else:
                logger.warning("JSSolanaClient not available for Lotus balance check")
                return None
                
        except Exception as e:
            logger.error(f"Error getting Lotus token balance: {e}")
            return None
    
    async def get_lotus_token_price(self) -> Optional[float]:
        """Get Lotus token price from DexScreener API"""
        try:
            import requests
            
            lotus_contract = 'Ch4tXj2qf8V6a4GdpS4X3pxAELvbnkiKTHGdmXjLEXsC'
            
            # Get price from DexScreener
            response = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{lotus_contract}", timeout=10)
            
            if response.ok:
                data = response.json()
                pairs = data.get('pairs', [])
                
                if pairs:
                    # Find the best pair (highest liquidity)
                    best_pair = max(pairs, key=lambda p: p.get('liquidity', {}).get('usd', 0))
                    price_usd = best_pair.get('priceUsd')
                    
                    if price_usd:
                        price = float(price_usd)
                        logger.info(f"Lotus token price: ${price}")
                        return price
                    else:
                        logger.warning("No price data found in DexScreener response")
                        return None
                else:
                    logger.warning("No pairs found for Lotus token")
                    return None
            else:
                logger.error(f"DexScreener API error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting Lotus token price: {e}")
            return None
    
    async def update_lotus_wallet_balance(self) -> bool:
        """Update Lotus wallet balance in the database"""
        try:
            from utils.supabase_manager import SupabaseManager
            
            # Get Lotus token balance and price
            balance = await self._get_lotus_balance()
            price = await self.get_lotus_token_price()
            
            if balance is None:
                logger.warning("Could not get Lotus token balance")
                return False
            
            # Calculate USD value
            balance_usd = 0.0
            if price is not None:
                balance_usd = float(balance) * price
            
            # Update database
            supabase = SupabaseManager()
            lotus_wallet = 'AbumtzzxomWWrm9uypY6ViRgruGdJBPFPM2vyHewTFdd'
            
            result = supabase.client.table('wallet_balances').upsert({
                'chain': 'lotus',
                'balance': float(balance),
                'balance_usd': balance_usd,
                'wallet_address': lotus_wallet,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }).execute()
            
            if result.data:
                logger.info(f"Updated Lotus wallet balance: {balance} tokens (${balance_usd:.3f})")
                return True
            else:
                logger.error("Failed to update Lotus wallet balance in database")
                return False
                
        except Exception as e:
            logger.error(f"Error updating Lotus wallet balance: {e}")
            return False
    
    async def _get_native_usd_rate(self, chain: str) -> float:
        """Get native currency USD rate for balance conversion"""
        try:
            from utils.supabase_manager import SupabaseManager
            
            # Map chains to their native token contracts
            native_contracts = {
                'ethereum': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',  # WETH
                'base': '0x4200000000000000000000000000000000000006',      # WETH (Base)
                'bsc': '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c',       # WBNB
                'solana': 'So11111111111111111111111111111111111111112'      # SOL
            }
            
            native_contract = native_contracts.get(chain.lower())
            if not native_contract:
                logger.error(f"Unknown chain for native USD rate: {chain}")
                return 0.0
            
            # Get price from database (from scheduled price collection)
            supabase = SupabaseManager()
            if chain.lower() in ['ethereum', 'base']:
                # Use Ethereum WETH price for both Ethereum and Base
                lookup_chain = 'ethereum'
            else:
                lookup_chain = chain.lower()
            
            result = supabase.client.table('lowcap_price_data_1m').select(
                'price_usd'
            ).eq('token_contract', native_contract).eq('chain', lookup_chain).order(
                'timestamp', desc=True
            ).limit(1).execute()
            
            if result.data:
                return float(result.data[0].get('price_usd', 0))
            else:
                logger.warning(f"No native USD rate found in database for {chain}")
                return 0.0
                
        except Exception as e:
            logger.error(f"Error getting native USD rate for {chain}: {e}")
            return 0.0
    
    async def _get_ethereum_balance(self, chain: str, token_address: str = None) -> Optional[Decimal]:
        """Get Ethereum/Base balance (ETH or ERC-20 token)"""
        try:
            if chain not in self.wallets or chain not in self.rpc_clients:
                return None
            
            wallet = self.wallets[chain]
            w3 = self.rpc_clients[chain]
            
            if token_address:
                # ERC-20 token balance
                try:
                    # Import the EVM client for this chain
                    if chain == 'ethereum':
                        from .evm_uniswap_client_eth import EthUniswapClient
                        client = EthUniswapClient()
                    elif chain == 'base':
                        from .evm_uniswap_client import EvmUniswapClient
                        base_rpc = self.config.get('base_rpc') or os.getenv('BASE_RPC_URL') or os.getenv('RPC_URL')
                        client = EvmUniswapClient(chain='base', rpc_url=base_rpc)
                    elif chain == 'bsc':
                        from .evm_uniswap_client import EvmUniswapClient
                        bsc_rpc = self.config.get('bsc_rpc') or os.getenv('BSC_RPC_URL')
                        client = EvmUniswapClient(chain='bsc', rpc_url=bsc_rpc)
                    else:
                        logger.warning(f"Unsupported chain for ERC-20 balance: {chain}")
                        return None
                    
                    # Get token balance
                    balance = client.get_token_balance(token_address)
                    if balance is not None:
                        return Decimal(str(balance))
                    else:
                        return None
                        
                except Exception as e:
                    logger.error(f"Error getting ERC-20 balance for {token_address} on {chain}: {e}")
                    return None
            else:
                # Native ETH balance
                balance_wei = w3.eth.get_balance(wallet.address)
                return Decimal(balance_wei) / Decimal(10**18)  # Convert wei to ETH
                
        except Exception as e:
            logger.error(f"Error getting {chain} balance: {e}")
            return None
    
    def can_trade(self, chain: str) -> bool:
        """Check if wallet can trade on a specific chain"""
        return (
            chain in self.wallets and 
            chain in self.rpc_clients and
            self.wallets[chain] is not None
        )
    
    def get_supported_chains(self) -> List[str]:
        """Get list of supported chains with active wallets"""
        return [chain for chain in self.wallets.keys() if self.can_trade(chain)]
    
    def generate_all_wallets(self) -> Dict[str, Any]:
        """Generate wallets for all supported chains"""
        try:
            generated = {}
            
            # Generate Solana wallet
            if SOLANA_AVAILABLE and 'solana' not in self.wallets:
                solana_wallet = self.generate_solana_wallet()
                if solana_wallet:
                    generated['solana'] = solana_wallet
            
            # Generate Ethereum wallet
            if ETHEREUM_AVAILABLE and 'ethereum' not in self.wallets:
                eth_wallet = self.generate_ethereum_wallet()
                if eth_wallet:
                    generated['ethereum'] = eth_wallet
                    
                    # Base uses the same wallet as Ethereum
                    generated['base'] = {
                        'address': eth_wallet['address'],
                        'private_key': eth_wallet['private_key'],
                        'chain': 'base'
                    }
            
            return generated
            
        except Exception as e:
            logger.error(f"Error generating all wallets: {e}")
            return {}
    
    def get_wallet_info(self) -> Dict[str, Any]:
        """Get wallet information summary"""
        info = {
            'supported_chains': self.get_supported_chains(),
            'wallets': {}
        }
        
        for chain in self.wallets:
            if self.wallets[chain]:
                info['wallets'][chain] = {
                    'address': self.get_wallet_address(chain),
                    'can_trade': self.can_trade(chain)
                }
        
        return info


# Example usage and testing
if __name__ == "__main__":
    # Test wallet manager
    try:
        wallet_manager = WalletManager()
        
        print("🔑 Wallet Manager Test")
        print("=" * 40)
        
        # Show wallet info
        info = wallet_manager.get_wallet_info()
        print(f"Supported chains: {info['supported_chains']}")
        
        for chain, wallet_info in info['wallets'].items():
            print(f"\n{chain.upper()}:")
            print(f"  Address: {wallet_info['address']}")
            print(f"  Can trade: {wallet_info['can_trade']}")
        
        # Note: Balance checking requires async context
        print("\nNote: Balance checking requires async context")
        print("Use wallet_manager.get_balance(chain) in async functions")
        
    except Exception as e:
        print(f"❌ Error testing wallet manager: {e}")
