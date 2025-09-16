#!/usr/bin/env python3
"""
Wallet Setup Script

Generates wallets for all supported chains and saves them to .env file.
"""

import os
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from trading.wallet_manager import WalletManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Main wallet setup function"""
    print("🔑 Wallet Setup Script")
    print("=" * 50)
    print()
    
    try:
        # Initialize wallet manager
        wallet_manager = WalletManager()
        
        # Get current wallet info
        print("📊 Current Wallet Status:")
        info = wallet_manager.get_wallet_info()
        
        for chain, wallet_info in info['wallets'].items():
            status = "✅ Ready" if wallet_info['can_trade'] else "❌ Not Ready"
            print(f"  {chain.upper()}: {wallet_info['address']} - {status}")
        
        print()
        
        # Generate missing wallets
        print("🔧 Generating missing wallets...")
        generated = wallet_manager.generate_all_wallets()
        
        if generated:
            print("✅ Generated wallet keys:")
            print()
            print("📝 Add these to your .env file:")
            print("-" * 40)
            
            for chain, wallet_data in generated.items():
                print(f"# {chain.upper()} Wallet")
                print(f"{chain.upper()}_WALLET_PRIVATE_KEY={wallet_data['private_key']}")
                print(f"{chain.upper()}_WALLET_ADDRESS={wallet_data['address']}")
                print()
        else:
            print("ℹ️  All wallets already exist in .env file")
        
        print()
        print("⚠️  IMPORTANT SECURITY NOTES:")
        print("  - Add the keys above to your .env file manually")
        print("  - Keep .env file secure and never commit to git")
        print("  - Consider using hardware wallets for production")
        print("  - Fund wallets with native tokens for gas fees")
        print("  - Base and Ethereum use the same wallet (same private key)")
        print("  - You only need to fund one wallet for both networks")
        
    except Exception as e:
        logger.error(f"Error setting up wallets: {e}")
        print(f"❌ Error: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
