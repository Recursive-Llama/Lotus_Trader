# Lotus Buyback Configuration

## Environment Variables

Add these to your `.env` file:

```bash
# Enable/disable Lotus buyback feature
LOTUS_BUYBACK_ENABLED=1

# Lotus Coin contract address (Solana)
LOTUS_CONTRACT=Ch4tXj2qf8V6a4GdpS4X3pxAELvbnkiKTHGdmXjLEXsC

# Holding wallet address (where 69% of bought tokens are sent)
LOTUS_HOLDING_WALLET=AbumtzzxomWWrm9uypY6ViRgruGdJBPFPM2vyHewTFdd

# Percentage of profit to swap (default: 10%)
LOTUS_BUYBACK_PERCENTAGE=10.0

# Percentage of bought tokens to transfer to holding wallet (default: 69%)
LOTUS_TRANSFER_PERCENTAGE=69.0

# Minimum swap amount in USD (default: $1.00) - avoids dust swaps
LOTUS_BUYBACK_MIN_USD=1.0

# Solana RPC URL (for token transfers)
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com

# Solana private key (base58 encoded, for signing transfers)
SOLANA_PRIVATE_KEY=your_base58_private_key_here
```

## How It Works

1. **Position Closure**: When a position fully closes (state S0, total_quantity = 0)
2. **Profit Calculation**: Uses `rpnl_usd` (realized P&L) or calculates `total_extracted_usd - total_allocation_usd`
3. **Swap**: 10% of profit is swapped from USDC (Solana) → Lotus Coin (Solana) via Li.Fi SDK
4. **Transfer**: 69% of received Lotus tokens are transferred to holding wallet
5. **Storage**: Buyback info is stored in `position.features.pm_execution_history.lotus_buyback`

## Result Structure

```json
{
  "success": true,
  "profit_usd": 123.45,
  "swap_amount_usd": 12.35,
  "lotus_tokens": 1000.0,
  "lotus_tokens_kept": 310.0,
  "lotus_tokens_transferred": 690.0,
  "swap_tx_hash": "abc123...",
  "transfer_tx_hash": "def456...",
  "transfer_success": true
}
```

## Notes

- **Fails gracefully**: If buyback fails, position closure still succeeds
- **Cross-chain**: All exits already bridge to Solana USDC via Li.Fi, so swap is always on Solana
- **Minimum amount**: Swaps below `LOTUS_BUYBACK_MIN_USD` are skipped
- **Transfer failure**: If transfer fails, tokens remain in trading wallet (swap still succeeded)

