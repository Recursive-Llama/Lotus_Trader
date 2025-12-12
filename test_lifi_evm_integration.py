#!/usr/bin/env python3
"""
Integration test for Li.Fi EVM chain swaps

This test:
1. Makes an actual swap via Li.Fi (or uses a known transaction hash)
2. Captures what Li.Fi returns (tokens_received, etc.)
3. Parses the actual transaction to see what really happened
4. Compares the two to find discrepancies

Usage:
    python test_lifi_evm_integration.py [--dry-run] [--tx-hash <hash>] [--chain <chain>] [--token <address>]
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# Load environment
load_dotenv()

# Chain name mapping (from executor.py _get_chain_id)
CHAIN_NAME_MAP = {
    'solana': 'solana',
    'sol': 'solana',
    'ethereum': 'ethereum',
    'eth': 'ethereum',
    'base': 'base',
    'bsc': 'bsc',
}

# Chain ID mapping for transaction parsing
CHAIN_ID_MAP = {
    'solana': 'solana',
    'ethereum': 1,
    'eth': 1,
    'base': 8453,
    'bsc': 56,
}

def get_chain_name(chain: str) -> str:
    """Get Li.Fi chain name from chain name (returns string like 'ethereum', not numeric ID)"""
    chain_lower = chain.lower()
    return CHAIN_NAME_MAP.get(chain_lower, chain_lower)

def get_chain_id(chain: str) -> int:
    """Get numeric chain ID for transaction parsing"""
    chain_lower = chain.lower()
    if chain_lower in CHAIN_ID_MAP:
        return CHAIN_ID_MAP[chain_lower]
    raise ValueError(f"Unknown chain: {chain}")

def call_lifi_executor(
    action: str,
    from_token: str,
    to_token: str,
    amount: str,
    from_chain: str,
    to_chain: str,
    slippage: float = 0.5,
    dry_run: bool = False
) -> Dict[str, Any]:
    """Call Li.Fi executor exactly like the real system does"""
    lifi_path = project_root / "scripts" / "lifi_sandbox" / "src" / "lifi_executor.mjs"
    
    if not lifi_path.exists():
        return {
            "success": False,
            "error": f"Li.Fi executor not found at {lifi_path}"
        }
    
    input_data = {
        "action": action,
        "fromToken": from_token,
        "toToken": to_token,
        "amount": amount,
        "slippage": slippage,
        "dryRun": dry_run,
        "fromChain": get_chain_name(from_chain),
        "toChain": get_chain_name(to_chain),
    }
    
    print(f"\n{'='*60}")
    print(f"Calling Li.Fi Executor")
    print(f"{'='*60}")
    print(f"Action: {action}")
    print(f"From: {from_token} on {from_chain}")
    print(f"To: {to_token} on {to_chain}")
    print(f"Amount: {amount}")
    print(f"Dry Run: {dry_run}")
    print(f"Input JSON: {json.dumps(input_data, indent=2)}")
    
    try:
        result = subprocess.run(
            ["node", str(lifi_path), json.dumps(input_data)],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(lifi_path.parent.parent)
        )
        
        print(f"\nReturn code: {result.returncode}")
        print(f"Stdout length: {len(result.stdout)}")
        print(f"Stderr length: {len(result.stderr)}")
        
        if result.returncode != 0:
            print(f"\n❌ Li.Fi executor failed:")
            print(f"Stdout: {result.stdout[:1000]}")
            print(f"Stderr: {result.stderr[:1000]}")
            return {
                "success": False,
                "error": result.stderr or result.stdout or "Unknown error"
            }
        
        # Parse JSON output (same logic as executor.py)
        stdout_lines = result.stdout.strip().split('\n')
        json_line = None
        
        for line in stdout_lines:
            line_stripped = line.strip()
            if line_stripped.startswith('{'):
                json_line = line_stripped
                break
        
        if not json_line:
            print(f"\n❌ No JSON output found")
            print(f"Stdout: {result.stdout[:500]}")
            return {
                "success": False,
                "error": "No JSON output from Li.Fi executor"
            }
        
        output = json.loads(json_line)
        
        print(f"\n✅ Li.Fi Response:")
        print(json.dumps(output, indent=2))
        
        return output
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Li.Fi executor timed out"
        }
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"Failed to parse JSON: {e}. Output: {result.stdout[:500]}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error calling Li.Fi executor: {e}"
        }

def parse_evm_transaction(chain_id: int, tx_hash: str, token_address: str, wallet_address: str) -> Optional[Dict[str, Any]]:
    """Parse EVM transaction to get actual token amount received"""
    # Use the Node.js script we created
    test_script = project_root / "test_lifi_evm_output.js"
    
    if not test_script.exists():
        print(f"⚠️  Test script not found at {test_script}")
        return None
    
    print(f"\n{'='*60}")
    print(f"Parsing Transaction")
    print(f"{'='*60}")
    print(f"Chain ID: {chain_id}")
    print(f"Transaction Hash: {tx_hash}")
    print(f"Token Address: {token_address}")
    print(f"Wallet Address: {wallet_address}")
    
    try:
        result = subprocess.run(
            ["node", str(test_script), str(chain_id), tx_hash, token_address, wallet_address],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        print(f"\nReturn code: {result.returncode}")
        print(f"\n{result.stdout}")
        
        if result.returncode != 0:
            print(f"\n❌ Transaction parsing failed:")
            print(result.stderr)
            return None
        
        # Try to extract the result from output
        # The script prints JSON at the end
        for line in reversed(result.stdout.split('\n')):
            if line.strip().startswith('{'):
                try:
                    return json.loads(line.strip())
                except:
                    pass
        
        return None
        
    except Exception as e:
        print(f"\n❌ Error parsing transaction: {e}")
        return None

def get_wallet_address(chain: str) -> str:
    """Get wallet address for chain from environment or derive from private key"""
    chain_lower = chain.lower()
    
    # Try environment variable first
    if chain_lower == 'solana':
        addr = os.getenv('SOL_WALLET_ADDRESS', '')
        if addr:
            return addr
    elif chain_lower in ['ethereum', 'eth']:
        addr = os.getenv('ETH_WALLET_ADDRESS', '')
        if addr:
            return addr
        # Try to derive from private key
        try:
            from eth_account import Account
            priv_key = os.getenv('ETH_WALLET_PRIVATE_KEY') or os.getenv('ETHEREUM_WALLET_PRIVATE_KEY')
            if priv_key:
                priv_key = priv_key.strip()
                if not priv_key.startswith('0x'):
                    priv_key = '0x' + priv_key
                account = Account.from_key(priv_key)
                return account.address
        except Exception:
            pass
    elif chain_lower == 'base':
        addr = os.getenv('BASE_WALLET_ADDRESS', '')
        if addr:
            return addr
        try:
            from eth_account import Account
            priv_key = os.getenv('BASE_WALLET_PRIVATE_KEY')
            if priv_key:
                priv_key = priv_key.strip()
                if not priv_key.startswith('0x'):
                    priv_key = '0x' + priv_key
                account = Account.from_key(priv_key)
                return account.address
        except Exception:
            pass
    elif chain_lower == 'bsc':
        addr = os.getenv('BSC_WALLET_ADDRESS', '')
        if addr:
            return addr
        try:
            from eth_account import Account
            priv_key = os.getenv('BSC_WALLET_PRIVATE_KEY')
            if priv_key:
                priv_key = priv_key.strip()
                if not priv_key.startswith('0x'):
                    priv_key = '0x' + priv_key
                account = Account.from_key(priv_key)
                return account.address
        except Exception:
            pass
    
    return ''

def main():
    parser = argparse.ArgumentParser(description='Test Li.Fi EVM chain integration')
    parser.add_argument('--dry-run', action='store_true', help='Use dry run mode')
    parser.add_argument('--tx-hash', type=str, help='Transaction hash to analyze (skip swap)')
    parser.add_argument('--chain', type=str, default='ethereum', help='Target chain (ethereum, base, bsc)')
    parser.add_argument('--token', type=str, help='Token address to buy')
    parser.add_argument('--amount', type=str, help='Amount in smallest unit (e.g., 1000000 for 1 USDC)')
    
    args = parser.parse_args()
    
    print("="*60)
    print("Li.Fi EVM Chain Integration Test")
    print("="*60)
    
    # If tx_hash provided, just parse it
    if args.tx_hash:
        chain_id = get_chain_id(args.chain)
        token_address = args.token or input("Token address: ")
        wallet_address = get_wallet_address(args.chain) or input("Wallet address: ")
        
        result = parse_evm_transaction(chain_id, args.tx_hash, token_address, wallet_address)
        
        if result:
            print(f"\n✅ Transaction Analysis Complete")
            print(f"Tokens received: {result.get('amount')}")
            print(f"Raw amount: {result.get('rawAmount')}")
            print(f"Decimals: {result.get('decimals')}")
        else:
            print(f"\n❌ Failed to parse transaction")
        
        return
    
    # Otherwise, make a swap
    if not args.token:
        print("❌ Token address required (use --token)")
        return
    
    from_chain = 'solana'
    to_chain = args.chain
    from_token = 'USDC'
    to_token = args.token
    amount = args.amount or '1000000'  # 1 USDC default
    
    print(f"\n📋 Test Configuration:")
    print(f"   From Chain: {from_chain}")
    print(f"   To Chain: {to_chain}")
    print(f"   From Token: {from_token}")
    print(f"   To Token: {to_token}")
    print(f"   Amount: {amount} (smallest units)")
    print(f"   Dry Run: {args.dry_run}")
    
    # Get wallet address
    wallet_address = get_wallet_address(to_chain)
    if not wallet_address:
        print(f"\n❌ Error: No wallet address found for {to_chain}")
        print(f"   Please set {to_chain.upper()}_WALLET_ADDRESS or {to_chain.upper()}_WALLET_PRIVATE_KEY in .env")
        return
    else:
        print(f"\n✅ Wallet address for {to_chain}: {wallet_address}")
    
    # Make the swap
    lifi_result = call_lifi_executor(
        action="swap",
        from_token=from_token,
        to_token=to_token,
        amount=amount,
        from_chain=from_chain,
        to_chain=to_chain,
        dry_run=args.dry_run
    )
    
    if not lifi_result.get("success"):
        print(f"\n❌ Swap failed: {lifi_result.get('error')}")
        return
    
    # Extract values from Li.Fi response
    tx_hash = lifi_result.get("tx_hash")
    tokens_received_lifi = lifi_result.get("tokens_received")
    tokens_received_raw_lifi = lifi_result.get("tokens_received_raw")
    to_token_decimals_lifi = lifi_result.get("to_token_decimals")
    price_lifi = lifi_result.get("price")
    
    print(f"\n{'='*60}")
    print(f"Li.Fi Returned Values")
    print(f"{'='*60}")
    print(f"Transaction Hash: {tx_hash}")
    print(f"Tokens Received: {tokens_received_lifi}")
    print(f"Tokens Received (Raw): {tokens_received_raw_lifi}")
    print(f"Token Decimals: {to_token_decimals_lifi}")
    print(f"Price: {price_lifi}")
    
    # Parse the actual transaction
    if tx_hash:
        chain_id = get_chain_id(to_chain)
        actual_result = parse_evm_transaction(chain_id, tx_hash, to_token, wallet_address)
        
        if actual_result:
            print(f"\n{'='*60}")
            print(f"Transaction Analysis")
            print(f"{'='*60}")
            print(f"Tokens Received (Actual): {actual_result.get('amount')}")
            print(f"Tokens Received (Raw): {actual_result.get('rawAmount')}")
            print(f"Decimals: {actual_result.get('decimals')}")
            
            # Compare
            print(f"\n{'='*60}")
            print(f"Comparison")
            print(f"{'='*60}")
            
            actual_amount = actual_result.get('amount')
            lifi_amount = tokens_received_lifi
            
            if actual_amount and lifi_amount:
                diff = abs(actual_amount - lifi_amount)
                diff_pct = (diff / actual_amount * 100) if actual_amount > 0 else 0
                
                print(f"Li.Fi says: {lifi_amount}")
                print(f"Transaction shows: {actual_amount}")
                print(f"Difference: {diff} ({diff_pct:.2f}%)")
                
                if diff_pct > 1.0:
                    print(f"\n⚠️  WARNING: Significant discrepancy detected!")
                else:
                    print(f"\n✅ Values match")
        else:
            print(f"\n⚠️  Could not parse transaction to verify")
    else:
        print(f"\n⚠️  No transaction hash to verify")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
