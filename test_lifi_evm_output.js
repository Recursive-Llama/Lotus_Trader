#!/usr/bin/env node
/**
 * Test script to understand what Li.Fi returns for EVM chain swaps
 * 
 * This will help us understand:
 * 1. What tokens_received value we get from Li.Fi
 * 2. What tokens_received_raw value we get
 * 3. What the actual transaction shows on-chain
 * 4. Whether we're using the right transaction hash
 */

import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { config as loadEnv } from 'dotenv'
import { createPublicClient, http, erc20Abi, decodeEventLog } from 'viem'
import { base as baseChain, bsc, mainnet } from 'viem/chains'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

// Load environment variables
const envPath = resolve(__dirname, '.env')
loadEnv({ path: envPath })

// Chain config
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
  console.log(`\n=== Parsing Transaction ===`)
  console.log(`Chain ID: ${chainId} (${CHAIN_CONFIG[chainId]?.label || 'unknown'})`)
  console.log(`Transaction Hash: ${txHash}`)
  console.log(`Token Address: ${tokenAddress}`)
  console.log(`Wallet Address: ${walletAddress}`)
  
  const client = getRpcClient(chainId)
  const receipt = await client.getTransactionReceipt({ hash: txHash })
  
  if (!receipt) {
    console.log(`❌ No transaction receipt found`)
    return null
  }
  
  console.log(`✅ Transaction receipt found`)
  console.log(`   Block Number: ${receipt.blockNumber}`)
  console.log(`   Status: ${receipt.status}`)
  console.log(`   Logs Count: ${receipt.logs.length}`)
  
  const walletLower = normalizeHex(walletAddress)
  const tokenLower = normalizeHex(tokenAddress)
  let rawDelta = 0n
  let matchingLogs = 0
  
  console.log(`\n=== Scanning Logs for Token Transfers ===`)
  for (let i = 0; i < receipt.logs.length; i++) {
    const log = receipt.logs[i]
    const logAddress = normalizeHex(log.address)
    
    if (logAddress !== tokenLower) {
      continue
    }
    
    matchingLogs++
    console.log(`\n  Log ${i}: Token address matches`)
    console.log(`    Address: ${log.address}`)
    console.log(`    Topics: ${log.topics.length} topics`)
    
    try {
      const decoded = decodeEventLog({
        abi: erc20Abi,
        data: log.data,
        topics: log.topics,
      })
      
      if (decoded.eventName !== 'Transfer') {
        console.log(`    ⚠️  Not a Transfer event: ${decoded.eventName}`)
        continue
      }
      
      const from = normalizeHex(decoded.args.from)
      const to = normalizeHex(decoded.args.to)
      const value = BigInt(decoded.args.value ?? 0n)
      
      console.log(`    ✅ Transfer event decoded:`)
      console.log(`       From: ${from}`)
      console.log(`       To: ${to}`)
      console.log(`       Value (raw): ${value.toString()}`)
      console.log(`       Wallet matches: ${walletLower === to ? '✅ RECEIVED' : walletLower === from ? '✅ SENT' : '❌'}`)
      
      if (to === walletLower) {
        rawDelta += value
        console.log(`       ➕ Added to delta: +${value.toString()}`)
      }
      if (from === walletLower) {
        rawDelta -= value
        console.log(`       ➖ Subtracted from delta: -${value.toString()}`)
      }
    } catch (error) {
      console.log(`    ⚠️  Failed to decode log: ${error.message}`)
      continue
    }
  }
  
  console.log(`\n=== Results ===`)
  console.log(`Matching token logs: ${matchingLogs}`)
  console.log(`Raw delta: ${rawDelta.toString()}`)
  
  if (rawDelta === 0n) {
    console.log(`❌ No net token delta found`)
    return null
  }
  
  // Fetch decimals
  const tokenContract = {
    address: tokenAddress,
    abi: erc20Abi,
  }
  const decimals = await client.readContract({
    ...tokenContract,
    functionName: 'decimals',
  })
  
  const amount = Number(rawDelta) / (10 ** Number(decimals))
  
  console.log(`✅ Token delta found:`)
  console.log(`   Raw amount: ${rawDelta.toString()}`)
  console.log(`   Decimals: ${decimals}`)
  console.log(`   Human-readable: ${amount}`)
  
  return {
    amount,
    rawAmount: rawDelta.toString(),
    decimals: Number(decimals),
  }
}

// Test function - call with actual transaction details
const test = async () => {
  const args = process.argv.slice(2)
  
  if (args.length < 4) {
    console.log(`
Usage: node test_lifi_evm_output.js <chainId> <txHash> <tokenAddress> <walletAddress>

Example:
  node test_lifi_evm_output.js 1 0x123... 0x9Ac9468E7E3E1D194080827226B45d0B892C77Fd 0xF67F89A8...8bd940dcF

Chain IDs:
  1 = Ethereum
  8453 = Base
  56 = BSC
`)
    process.exit(1)
  }
  
  const chainId = parseInt(args[0])
  const txHash = args[1]
  const tokenAddress = args[2]
  const walletAddress = args[3]
  
  console.log(`\n🔍 Testing Li.Fi EVM Output Parsing`)
  console.log(`=====================================`)
  
  try {
    const result = await deriveEvmTokenDelta(chainId, txHash, tokenAddress, walletAddress)
    
    if (result) {
      console.log(`\n✅ SUCCESS`)
      console.log(`Final result:`, JSON.stringify(result, null, 2))
    } else {
      console.log(`\n❌ FAILED - Could not parse token delta from transaction`)
    }
  } catch (error) {
    console.error(`\n❌ ERROR:`, error.message)
    console.error(error.stack)
    process.exit(1)
  }
}

test()
