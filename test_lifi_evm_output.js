#!/usr/bin/env node
/**
 * Parse EVM transaction to get actual token amount received
 */

import { createPublicClient, http, erc20Abi, decodeEventLog } from 'viem'
import { base as baseChain, bsc, mainnet } from 'viem/chains'

const CHAIN_CONFIG = {
  1: { viemChain: mainnet, label: 'ethereum', rpcEnv: ['ETH_RPC_URL', 'ETHEREUM_RPC_URL'] },
  8453: { viemChain: baseChain, label: 'base', rpcEnv: ['BASE_RPC_URL'] },
  56: { viemChain: bsc, label: 'bsc', rpcEnv: ['BSC_RPC_URL'] },
}

const normalizeHex = (addr) => {
  if (!addr) return ''
  return addr.toLowerCase().startsWith('0x') ? addr.toLowerCase() : `0x${addr.toLowerCase()}`
}

const getRpcClient = (chainId) => {
  const config = CHAIN_CONFIG[chainId]
  if (!config) {
    throw new Error(`Unsupported chainId: ${chainId}`)
  }
  
  const rpcUrl = process.env[config.rpcEnv[0]] || process.env[config.rpcEnv[1]]
  if (!rpcUrl) {
    throw new Error(`No RPC URL found for ${config.label}. Tried: ${config.rpcEnv.join(', ')}`)
  }
  
  return createPublicClient({
    chain: config.viemChain,
    transport: http(rpcUrl),
  })
}

const deriveEvmTokenDelta = async (chainId, txHash, tokenAddress, walletAddress) => {
  const client = getRpcClient(chainId)
  const receipt = await client.getTransactionReceipt({ hash: txHash })
  
  if (!receipt) {
    return null
  }
  
  const walletLower = normalizeHex(walletAddress)
  const tokenLower = normalizeHex(tokenAddress)
  let rawDelta = 0n
  
  for (const log of receipt.logs || []) {
    if (normalizeHex(log.address) !== tokenLower) {
      continue
    }
    try {
      const decoded = decodeEventLog({
        abi: erc20Abi,
        data: log.data,
        topics: log.topics,
      })
      if (decoded.eventName !== 'Transfer') {
        continue
      }
      const from = normalizeHex(decoded.args.from)
      const to = normalizeHex(decoded.args.to)
      const value = BigInt(decoded.args.value ?? 0n)
      if (to === walletLower) {
        rawDelta += value
      }
      if (from === walletLower) {
        rawDelta -= value
      }
    } catch (error) {
      continue
    }
  }
  
  if (rawDelta === 0n) {
    return null
  }
  
  const decimals = await client.readContract({
    address: tokenAddress,
    abi: erc20Abi,
    functionName: 'decimals',
  })
  
  const amount = Number(rawDelta) / (10 ** Number(decimals))
  
  return {
    amount,
    rawAmount: rawDelta.toString(),
    decimals: Number(decimals),
  }
}

const test = async () => {
  const args = process.argv.slice(2)
  
  if (args.length < 4) {
    console.log('Usage: node test_lifi_evm_output.js <chainId> <txHash> <tokenAddress> <walletAddress>')
    process.exit(1)
  }
  
  const chainId = parseInt(args[0])
  const txHash = args[1]
  const tokenAddress = args[2]
  const walletAddress = args[3]
  
  try {
    const result = await deriveEvmTokenDelta(chainId, txHash, tokenAddress, walletAddress)
    console.log(JSON.stringify(result, null, 2))
  } catch (error) {
    console.error(`ERROR: ${error.message}`)
    process.exit(1)
  }
}

test()

