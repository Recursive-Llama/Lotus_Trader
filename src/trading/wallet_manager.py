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
                
                logger.info("✅ Ethereum and Base RPC clients initialized")
            
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
            
            # Base uses the same wallet as Ethereum (same private key, different network)
            if 'ethereum' in self.wallets:
                self.wallets['base'] = self.wallets['ethereum']
                logger.info("✅ Base wallet (reusing Ethereum wallet)")
            
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
            chain: Blockchain network (solana, ethereum, base)
            token_address: Token contract address (None for native token)
            
        Returns:
            Balance in native units (SOL, ETH, etc.)
        """
        try:
            if chain == 'solana':
                return await self._get_solana_balance(token_address)
            elif chain in ['ethereum', 'base']:
                return await self._get_ethereum_balance(chain, token_address)
            else:
                logger.error(f"Unsupported chain: {chain}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting balance for {chain}: {e}")
            return None
    
    async def _get_solana_balance(self, token_address: str = None) -> Optional[Decimal]:
        """Get Solana balance (SOL or SPL token)"""
        try:
            if not self.wallets.get('solana') or 'solana' not in self.rpc_clients:
                return None
            
            client = self.rpc_clients['solana']
            wallet_pubkey = self.wallets['solana'].pubkey()
            
            if token_address:
                # SPL token balance
                # This would require additional SPL token program calls
                logger.warning("SPL token balance not implemented yet")
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
    
    async def _get_ethereum_balance(self, chain: str, token_address: str = None) -> Optional[Decimal]:
        """Get Ethereum/Base balance (ETH or ERC-20 token)"""
        try:
            if chain not in self.wallets or chain not in self.rpc_clients:
                return None
            
            wallet = self.wallets[chain]
            w3 = self.rpc_clients[chain]
            
            if token_address:
                # ERC-20 token balance
                # This would require ERC-20 contract calls
                logger.warning("ERC-20 token balance not implemented yet")
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
