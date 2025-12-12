#!/usr/bin/env node
/**
 * Li.Fi SDK Executor - Wrapper for Python integration
 * 
 * Accepts JSON input via stdin or command-line args:
 * {
 *   "action": "swap" | "bridge",
 *   "chain": "solana" | "ethereum" | "base" | "bsc",
 *   "fromToken": "USDC" | token_contract_address,
 *   "toToken": token_contract_address,
 *   "amount": "1000000",  // Amount in token's smallest unit (e.g., 1 USDC = 1000000 for 6 decimals)
 *   "slippage": 0.5,  // Optional, default 0.5%
 *   "dryRun": false
 * }
 * 
 * Returns JSON output:
 * {
 *   "success": true | false,
 *   "tx_hash": "...",
 *   "tx_link": "...",
 *   "tokens_received": "...",
 *   "price": 0.0015,
 *   "slippage": 0.02,
 *   "error": "..."
 * }
 */

import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { config as loadEnv } from 'dotenv'
import {
  EVM,
  Solana,
  KeypairWalletAdapter,
  createConfig,
  getRoutes,
  executeRoute,
  getTokens,
  config as sdkConfig,
} from '@lifi/sdk'
import { ChainId } from '@lifi/types'
import { createWalletClient, createPublicClient, http, erc20Abi, decodeEventLog } from 'viem'
import { privateKeyToAccount } from 'viem/accounts'
import { base as baseChain, bsc, mainnet } from 'viem/chains'
import { Connection } from '@solana/web3.js'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

// Load environment variables
const envPath = resolve(__dirname, '../../../.env')
loadEnv({ path: envPath })

const integrator = process.env.LIFI_INTEGRATOR ?? 'LotusTrader'
const apiKey = process.env.LIFI_API_KEY

// Chain ID mapping
const CHAIN_ID_MAP = {
  'solana': ChainId.SOL,
  'ethereum': ChainId.ETH,
  'eth': ChainId.ETH,
  'base': ChainId.BAS,
  'bsc': ChainId.BSC,
}

// Chain config mapping
const CHAIN_CONFIG = {
  [ChainId.ETH]: { viemChain: mainnet, label: 'ethereum', rpcEnv: ['ETH_RPC_URL', 'ETHEREUM_RPC_URL'], keyEnv: ['ETH_WALLET_PRIVATE_KEY', 'ETHEREUM_WALLET_PRIVATE_KEY'] },
  [ChainId.BAS]: { viemChain: baseChain, label: 'base', rpcEnv: ['BASE_RPC_URL'], keyEnv: ['BASE_WALLET_PRIVATE_KEY'] },
  [ChainId.BSC]: { viemChain: bsc, label: 'bsc', rpcEnv: ['BSC_RPC_URL'], keyEnv: ['BSC_WALLET_PRIVATE_KEY'] },
}

const resolveEnv = (names, { optional = false } = {}) => {
  const lookup = Array.isArray(names) ? names : [names]
  for (const name of lookup) {
    const value = process.env[name]
    if (value && value.trim().length) {
      return value.trim()
    }
  }
  if (optional) {
    return undefined
  }
  throw new Error(`Missing required environment variable. Tried: ${lookup.join(', ')}`)
}

const maybeEnv = (names) => resolveEnv(names, { optional: true })

const normalizePrivateKey = (privateKey) => {
  if (!privateKey) return undefined
  const trimmed = privateKey.trim()
  return trimmed.startsWith('0x') ? trimmed : `0x${trimmed}`
}

// Initialize SDK config (one-time setup)
let sdkInitialized = false
const initSDK = async () => {
  if (sdkInitialized) return
  
  const providers = []
  const rpcUrls = {}
  
  // Setup EVM chains
  for (const [chainId, config] of Object.entries(CHAIN_CONFIG)) {
    const privateKey = normalizePrivateKey(maybeEnv(config.keyEnv))
    let rpcUrl = maybeEnv(config.rpcEnv)
    
    // Construct Base RPC from ETH RPC if needed
    if (!rpcUrl && chainId === ChainId.BAS) {
      const ethRpc = maybeEnv(['ETH_RPC_URL', 'ETHEREUM_RPC_URL'])
      if (ethRpc && ethRpc.includes('rpc.ankr.com/eth/')) {
        const apiKeyMatch = ethRpc.match(/rpc\.ankr\.com\/eth\/([^\/]+)/)
        if (apiKeyMatch) {
          rpcUrl = `https://rpc.ankr.com/base/${apiKeyMatch[1]}`
        }
      }
    }
    
    if (privateKey && rpcUrl) {
      rpcUrls[chainId] = [rpcUrl]
    }
  }
  
  // Setup Solana
  const solanaPrivateKey = maybeEnv('SOL_WALLET_PRIVATE_KEY')
  const heliusApiKey = maybeEnv('HELIUS_API_KEY')
  const solanaRpcUrl = heliusApiKey
    ? `https://mainnet.helius-rpc.com/?api-key=${heliusApiKey}`
    : maybeEnv('SOLANA_RPC_URL')
  
  if (solanaPrivateKey && solanaRpcUrl) {
    rpcUrls[ChainId.SOL] = [solanaRpcUrl]
    const solanaAdapter = new KeypairWalletAdapter(solanaPrivateKey)
    providers.push(
      Solana({
        getWalletAdapter: async () => solanaAdapter,
      })
    )
  }
  
  // Setup EVM provider
  const getWalletClient = async (chainId) => {
    const config = CHAIN_CONFIG[chainId]
    if (!config) {
      throw new Error(`No config for chainId ${chainId}`)
    }
    const privateKey = normalizePrivateKey(maybeEnv(config.keyEnv))
    if (!privateKey) {
      throw new Error(`No private key for chainId ${chainId}`)
    }
    let rpcUrl = maybeEnv(config.rpcEnv)
    
    // Construct Base RPC from ETH RPC if needed
    if (!rpcUrl && chainId === ChainId.BAS) {
      const ethRpc = maybeEnv(['ETH_RPC_URL', 'ETHEREUM_RPC_URL'])
      if (ethRpc && ethRpc.includes('rpc.ankr.com/eth/')) {
        const apiKeyMatch = ethRpc.match(/rpc\.ankr\.com\/eth\/([^\/]+)/)
        if (apiKeyMatch) {
          rpcUrl = `https://rpc.ankr.com/base/${apiKeyMatch[1]}`
        }
      }
    }
    
    if (!rpcUrl) {
      throw new Error(`No RPC URL for chainId ${chainId}`)
    }
    
    const account = privateKeyToAccount(privateKey)
    return createWalletClient({
      account,
      chain: config.viemChain,
      transport: http(rpcUrl, { retryCount: 2 }),
    })
  }
  
  if (Object.keys(rpcUrls).length > 0) {
    providers.push(
      EVM({
        getWalletClient: async () => {
          // Return first available EVM chain's wallet client
          for (const chainId of [ChainId.BAS, ChainId.BSC, ChainId.ETH]) {
            try {
              return await getWalletClient(chainId)
            } catch (e) {
              continue
            }
          }
          throw new Error('No EVM wallet client available')
        },
        switchChain: async (targetChainId) => getWalletClient(targetChainId),
      })
    )
  }
  
  createConfig({
    integrator,
    apiKey,
    providers: providers.length > 0 ? providers : undefined,
    rpcUrls: Object.keys(rpcUrls).length > 0 ? rpcUrls : undefined,
    debug: false,
  })
  
  await sdkConfig.getChains()
  sdkInitialized = true
}

// Token resolution cache
const tokensCache = new Map()
const tokenDecimalsCache = new Map()

const resolveToken = async (chainId, symbolOrAddress) => {
  // If it's an address (starts with 0x or is a long base58 string), use it directly
  if (symbolOrAddress.startsWith('0x') || symbolOrAddress.length > 40) {
    // It's an address - we need to get token info
    // For now, assume it's a token address and return it
    // Li.Fi SDK will handle it
    return { address: symbolOrAddress }
  }
  
  // It's a symbol - resolve via SDK
  if (!tokensCache.has(chainId)) {
    const response = await getTokens({ chains: [chainId] })
    tokensCache.set(chainId, response.tokens?.[chainId] ?? [])
  }
  const tokens = tokensCache.get(chainId)
  const symbolUpper = symbolOrAddress.toUpperCase()
  const match = tokens.find((token) => {
    if (!token.symbol) return false
    return token.symbol.toUpperCase() === symbolUpper
  })
  if (!match) {
    throw new Error(`Token not found: ${symbolOrAddress} on chain ${chainId}`)
  }
  return match
}

const getAccountKey = (transaction, index) => {
  if (!transaction?.message) {
    return undefined
  }
  const message = transaction.message
  if (Array.isArray(message.accountKeys) && message.accountKeys[index]) {
    const key = message.accountKeys[index]
    if (typeof key === 'string') {
      return key
    }
    if (key?.pubkey) {
      return key.pubkey.toString()
    }
  }
  if (Array.isArray(message.staticAccountKeys) && message.staticAccountKeys[index]) {
    const key = message.staticAccountKeys[index]
    if (typeof key === 'string') {
      return key
    }
    if (key?.toString) {
      return key.toString()
    }
  }
  return undefined
}

const deriveSolanaTokenDelta = (parsedTx, mint, owner) => {
  const meta = parsedTx?.meta
  if (!meta) {
    return null
  }
  const postBalances = meta.postTokenBalances || []
  const preBalances = meta.preTokenBalances || []
  const transaction = parsedTx?.transaction

  const normalizeOwner = (entry) => {
    if (entry?.owner) {
      return entry.owner
    }
    return getAccountKey(transaction, entry.accountIndex)
  }

  const findMatchingEntry = (balances, accountIndex) => {
    return balances.find((entry) => entry.accountIndex === accountIndex && entry.mint === mint)
  }

  let fallbackDelta = null

  if (process.env.LOTUS_DEBUG_LIFI === '1') {
    console.log('[LiFi] Solana balances snapshot', {
      mint,
      postCount: postBalances.length,
      preCount: preBalances.length,
    })
  }

  for (const postEntry of postBalances) {
    if (postEntry.mint !== mint) {
      continue
    }
    const postOwner = normalizeOwner(postEntry)
    if (process.env.LOTUS_DEBUG_LIFI === '1') {
      console.log('[LiFi] checking postEntry', {
        owner: postOwner,
        mint: postEntry.mint,
        amount: postEntry.uiTokenAmount?.amount,
        decimals: postEntry.uiTokenAmount?.decimals,
      })
    }
    if (owner && postOwner !== owner) {
      continue
    }
    const preEntry = findMatchingEntry(preBalances, postEntry.accountIndex)
    const postRaw = BigInt(postEntry.uiTokenAmount?.amount ?? postEntry.amount ?? '0')
    const preRaw = preEntry ? BigInt(preEntry.uiTokenAmount?.amount ?? preEntry.amount ?? '0') : 0n
    const rawDelta = postRaw - preRaw
    // If owner filter supplied and delta negative (token left a temp ATA), skip
    if (owner && rawDelta < 0n) {
      continue
    }
    if (owner && postOwner === owner && rawDelta !== 0n) {
      const decimals = postEntry.uiTokenAmount?.decimals ?? postEntry.decimals ?? 9
      const amount = Number(rawDelta) / (10 ** decimals)
      return {
        amount,
        rawAmount: rawDelta.toString(),
        decimals,
      }
    }
    if (!owner && rawDelta > 0n && !fallbackDelta) {
      const decimals = postEntry.uiTokenAmount?.decimals ?? postEntry.decimals ?? 9
      const amount = Number(rawDelta) / (10 ** decimals)
      fallbackDelta = {
        amount,
        rawAmount: rawDelta.toString(),
        decimals,
      }
    }
    if (owner && postOwner !== owner && rawDelta > 0n && !fallbackDelta) {
      const decimals = postEntry.uiTokenAmount?.decimals ?? postEntry.decimals ?? 9
      const amount = Number(rawDelta) / (10 ** decimals)
      fallbackDelta = {
        amount,
        rawAmount: rawDelta.toString(),
        decimals,
      }
    }
  }
  return fallbackDelta
}

const normalizeHex = (value) => value ? value.toLowerCase() : value

const fetchEvmTokenDecimals = async (client, tokenAddress) => {
  const key = `${client.chain?.id || 'unknown'}:${tokenAddress.toLowerCase()}`
  if (tokenDecimalsCache.has(key)) {
    return tokenDecimalsCache.get(key)
  }
  try {
    const decimals = await client.readContract({
      address: tokenAddress,
      abi: erc20Abi,
      functionName: 'decimals',
    })
    tokenDecimalsCache.set(key, Number(decimals))
    return Number(decimals)
  } catch (error) {
    tokenDecimalsCache.set(key, 18)
    return 18
  }
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
  const decimals = await fetchEvmTokenDecimals(client, tokenAddress)
  const amount = Number(rawDelta) / (10 ** decimals)
  return {
    amount,
    rawAmount: rawDelta.toString(),
    decimals,
  }
}

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

const resolveActualOutput = async ({ chainId, txHash, tokenAddress, walletAddress, expectedOutput, fallbackDecimals }) => {
  if (!txHash) {
    return null
  }
  try {
    if (process.env.LOTUS_DEBUG_LIFI === '1') {
      console.log('[LiFi] resolveActualOutput chainId', chainId)
    }
    if (chainId === ChainId.SOL) {
      const client = getRpcClient(chainId)
      let parsedTx = null
      for (let attempt = 0; attempt < 30; attempt++) {
        parsedTx = await client.getParsedTransaction(txHash, {
          commitment: 'finalized',
          maxSupportedTransactionVersion: 0,
        })
        if (parsedTx) {
          break
        }
        await delay(1000)
      }
      if (!parsedTx) {
        if (process.env.LOTUS_DEBUG_LIFI === '1') {
          console.warn('[LiFi] Parsed transaction not found for', txHash)
        }
        return null
      }
      const delta = deriveSolanaTokenDelta(parsedTx, tokenAddress, walletAddress)
      if (delta) {
        if (process.env.LOTUS_DEBUG_LIFI === '1') {
          console.log('[LiFi] Solana delta', delta)
        }
        return delta
      }
      if (process.env.LOTUS_DEBUG_LIFI === '1') {
        console.warn('[LiFi] Solana delta not found for', walletAddress)
      }
      return null
    } else {
      // EVM chains (ETH, Base, BSC)
      // CRITICAL: For cross-chain swaps, ensure we're using the destination chain's transaction hash
      // Li.Fi's expectedOutput might be from the first swap (e.g., USDC→ETH), not the final amount
      const delta = await deriveEvmTokenDelta(chainId, txHash, tokenAddress, walletAddress)
      if (delta) {
        if (process.env.LOTUS_DEBUG_LIFI === '1') {
          console.log('[LiFi] EVM delta found', { chainId, txHash, tokenAddress, delta })
        }
        return delta
      }
      // If delta is null, expectedOutput might be wrong (could be from first swap, not final)
      // Log warning so we can investigate
      console.warn(
        `[LiFi] deriveEvmTokenDelta returned null for chainId=${chainId}, txHash=${txHash}, ` +
        `tokenAddress=${tokenAddress}, walletAddress=${walletAddress}. ` +
        `Falling back to expectedOutput=${expectedOutput} which may be incorrect for cross-chain swaps.`
      )
      if (typeof expectedOutput === 'number') {
        return {
          amount: expectedOutput,
          rawAmount: null,
          decimals: fallbackDecimals,
        }
      }
      return null
    }
  } catch (error) {
    console.warn(`resolveActualOutput fallback (${chainId}) due to ${error.message}`)
    if (typeof expectedOutput === 'number') {
      return {
        amount: expectedOutput,
        rawAmount: null,
        decimals: fallbackDecimals,
      }
    }
    return null
  }
}

// Get wallet address for a chain
const getWalletAddress = async (chainId) => {
  if (chainId === ChainId.SOL) {
    const solanaPrivateKey = maybeEnv('SOL_WALLET_PRIVATE_KEY')
    if (!solanaPrivateKey) {
      throw new Error('SOL_WALLET_PRIVATE_KEY not found')
    }
    const adapter = new KeypairWalletAdapter(solanaPrivateKey)
    return adapter.publicKey?.toString()
  } else {
    const config = CHAIN_CONFIG[chainId]
    if (!config) {
      throw new Error(`No config for chainId ${chainId}`)
    }
    const privateKey = normalizePrivateKey(maybeEnv(config.keyEnv))
    if (!privateKey) {
      throw new Error(`No private key for chainId ${chainId}`)
    }
    const account = privateKeyToAccount(privateKey)
    return account.address
  }
}

// Get RPC client for confirmation
const getRpcClient = (chainId) => {
  if (chainId === ChainId.SOL) {
    const heliusApiKey = maybeEnv('HELIUS_API_KEY')
    const solanaRpcUrl = heliusApiKey
      ? `https://mainnet.helius-rpc.com/?api-key=${heliusApiKey}`
      : maybeEnv('SOLANA_RPC_URL')
    if (!solanaRpcUrl) {
      throw new Error('No Solana RPC URL')
    }
    return new Connection(solanaRpcUrl)
  } else {
    const config = CHAIN_CONFIG[chainId]
    if (!config) {
      throw new Error(`No config for chainId ${chainId}`)
    }
    let rpcUrl = maybeEnv(config.rpcEnv)
    
    // Construct Base RPC from ETH RPC if needed
    if (!rpcUrl && chainId === ChainId.BAS) {
      const ethRpc = maybeEnv(['ETH_RPC_URL', 'ETHEREUM_RPC_URL'])
      if (ethRpc && ethRpc.includes('rpc.ankr.com/eth/')) {
        const apiKeyMatch = ethRpc.match(/rpc\.ankr\.com\/eth\/([^\/]+)/)
        if (apiKeyMatch) {
          rpcUrl = `https://rpc.ankr.com/base/${apiKeyMatch[1]}`
        }
      }
    }
    
    if (!rpcUrl) {
      throw new Error(`No RPC URL for chainId ${chainId}`)
    }
    
    return createPublicClient({
      chain: config.viemChain,
      transport: http(rpcUrl, { retryCount: 2 }),
    })
  }
}

// Check transaction status
const checkTxStatus = async (chainId, txHash) => {
  const client = getRpcClient(chainId)
  
  if (chainId === ChainId.SOL) {
    const status = await client.getSignatureStatus(txHash, {
      searchTransactionHistory: true,
    })
    return status.value
  } else {
    const receipt = await client.getTransactionReceipt({ hash: txHash })
    return receipt
  }
}

// Main execution function
const executeSwap = async (input) => {
  try {
    await initSDK()
    
    const fromChainId = CHAIN_ID_MAP[input.fromChain?.toLowerCase() || input.chain?.toLowerCase()]
    const toChainId = CHAIN_ID_MAP[input.toChain?.toLowerCase() || input.chain?.toLowerCase()]
    
    if (!fromChainId) {
      throw new Error(`Unsupported from chain: ${input.fromChain || input.chain}`)
    }
    if (!toChainId) {
      throw new Error(`Unsupported to chain: ${input.toChain || input.chain}`)
    }
    
    const fromToken = await resolveToken(fromChainId, input.fromToken)
    const toToken = await resolveToken(toChainId, input.toToken)
    const fromAddress = await getWalletAddress(fromChainId)
    const toAddress = input.toAddress || await getWalletAddress(toChainId)
  if (process.env.LOTUS_DEBUG_LIFI === '1') {
    console.log('[LiFi] fromAddress', fromAddress, 'toAddress', toAddress)
  }
    
    const request = {
      fromChainId: fromChainId,
      toChainId: toChainId,
      fromAmount: input.amount,
      fromTokenAddress: fromToken.address,
      toTokenAddress: toToken.address,
      fromAddress: fromAddress,
      toAddress: toAddress,
      options: {
        allowSwitchChain: true,
        slippage: input.slippage || 0.5,
      },
    }
    
    // Get route
    const { routes, unavailableRoutes } = await getRoutes(request)
    
    if (!routes?.length) {
      throw new Error(`No routes available: ${JSON.stringify(unavailableRoutes)}`)
    }
    
    const route = routes[0]
    
    if (input.dryRun) {
      return {
        success: true,
        dryRun: true,
        estimatedOutput: route.toAmountMin ?? route.toAmount,
        estimatedUSD: route.toAmountUSD,
        route: route.steps.map(s => s.toolDetails?.name || s.tool).join(' → '),
      }
    }
    
    // Execute route
    // Handle cross-chain bridge vs single-chain swap
    const isBridge = fromChainId !== toChainId
    
    let capturedTxHash = null
    let capturedTxLink = null
    let capturedStepTool = null
    
    if (isBridge) {
      // Cross-chain bridge: need to capture and confirm both source and destination transactions
      let capturedTxHashes = []
      let capturedTxLinks = []
      let capturedStepChains = []
      
      const captureTxHash = (updatedRoute) => {
        for (const step of updatedRoute.steps || []) {
          const processes = step.execution?.process || []
          for (const process of processes) {
            if (process.txHash && !capturedTxHashes.includes(process.txHash)) {
              const chainId = process.type === 'RECEIVING_CHAIN' 
                ? step.action.toChainId 
                : (step.action.fromChainId || step.action.toChainId)
              capturedTxHashes.push(process.txHash)
              capturedTxLinks.push(process.txLink)
              capturedStepChains.push(chainId)
            }
          }
        }
      }
      
      const executionPromise = executeRoute(route, {
        executeInBackground: false,
        updateRouteHook: captureTxHash,
      })
      
      // Wait for execution to start and capture transactions
      // For bridges, we need at least the source transaction (destination may come later)
      await Promise.race([
        executionPromise,
        new Promise((resolve) => {
          const checkInterval = setInterval(() => {
            if (capturedTxHashes.length >= 1) {  // At least source transaction
              clearInterval(checkInterval)
              resolve(null)
            }
          }, 100)
          setTimeout(() => {
            clearInterval(checkInterval)
            resolve(null)
          }, 60000) // 60s timeout for bridges
        }),
      ])
      
      if (capturedTxHashes.length === 0) {
        throw new Error('No transaction hashes captured for bridge')
      }
      
      // Verify both source and destination transactions
      let sourceConfirmed = false
      let destConfirmed = false
      let sourceTxHash = null
      let destTxHash = null
      
      for (let i = 0; i < capturedTxHashes.length; i++) {
        const chainId = capturedStepChains[i]
        if (chainId === fromChainId) {
          sourceTxHash = capturedTxHashes[i]
        } else if (chainId === toChainId) {
          destTxHash = capturedTxHashes[i]
        }
      }
      
      // Confirm source transaction
      if (sourceTxHash) {
        let attempts = 0
        const maxAttempts = fromChainId === ChainId.SOL ? 30 : 60
        while (!sourceConfirmed && attempts < maxAttempts) {
          const status = await checkTxStatus(fromChainId, sourceTxHash)
          if (fromChainId === ChainId.SOL) {
            if (status && !status.err && (status.confirmationStatus === 'confirmed' || status.confirmationStatus === 'finalized')) {
              sourceConfirmed = true
            } else if (status?.err) {
              throw new Error(`Source transaction failed: ${JSON.stringify(status.err)}`)
            }
          } else {
            if (status?.status === 'success') {
              sourceConfirmed = true
            } else if (status?.status === 'reverted') {
              throw new Error('Source transaction reverted')
            }
          }
          if (!sourceConfirmed) {
            attempts++
            await new Promise((resolve) => setTimeout(resolve, fromChainId === ChainId.SOL ? 1000 : 2000))
          }
        }
      }
      
      // Wait for destination transaction (may take longer for bridges)
      if (!destTxHash) {
        // Wait up to 5 minutes for destination transaction
        let waitAttempts = 0
        while (!destTxHash && waitAttempts < 300) {
          await new Promise((resolve) => setTimeout(resolve, 1000))
          // Re-check captured hashes (SDK may add destination later)
          for (let i = 0; i < capturedTxHashes.length; i++) {
            if (capturedStepChains[i] === toChainId) {
              destTxHash = capturedTxHashes[i]
              break
            }
          }
          waitAttempts++
        }
      }
      
      // Confirm destination transaction
      if (destTxHash) {
        let attempts = 0
        const maxAttempts = toChainId === ChainId.SOL ? 30 : 60
        while (!destConfirmed && attempts < maxAttempts) {
          const status = await checkTxStatus(toChainId, destTxHash)
          if (toChainId === ChainId.SOL) {
            if (status && !status.err && (status.confirmationStatus === 'confirmed' || status.confirmationStatus === 'finalized')) {
              destConfirmed = true
            } else if (status?.err) {
              throw new Error(`Destination transaction failed: ${JSON.stringify(status.err)}`)
            }
          } else {
            if (status?.status === 'success') {
              destConfirmed = true
            } else if (status?.status === 'reverted') {
              throw new Error('Destination transaction reverted')
            }
          }
          if (!destConfirmed) {
            attempts++
            await new Promise((resolve) => setTimeout(resolve, toChainId === ChainId.SOL ? 1000 : 2000))
          }
        }
      }
      
      if (!sourceConfirmed) {
        throw new Error('Source transaction not confirmed')
      }
      if (isBridge && !destConfirmed) {
        throw new Error('Destination transaction not confirmed (bridge may still be processing)')
      }
      
      // Use destination txHash if available, otherwise source
      capturedTxHash = destTxHash || sourceTxHash
      const txLinkIndex = capturedTxHashes.indexOf(capturedTxHash)
      capturedTxLink = txLinkIndex >= 0 ? capturedTxLinks[txLinkIndex] : null
      capturedStepTool = route.steps.map(s => s.toolDetails?.name || s.tool).join(' → ')
      
    } else {
      // Single-chain swap: original logic
      let hookCallCount = 0
      const captureTxHash = (updatedRoute) => {
        hookCallCount++
        for (const step of updatedRoute.steps || []) {
          const processes = step.execution?.process || []
          for (const process of processes) {
            if (process.txHash && !capturedTxHash) {
              capturedTxHash = process.txHash
              capturedTxLink = process.txLink
              capturedStepTool = step.toolDetails?.name || step.tool
            }
          }
        }
      }
      
      const executionPromise = executeRoute(route, {
        executeInBackground: false,
        updateRouteHook: captureTxHash,
      })
      
      let finalRoute = null
      let executionError = null
      try {
        await Promise.race([
          executionPromise.then(route => { finalRoute = route; return route }),
          new Promise((resolve) => {
            const checkInterval = setInterval(() => {
              if (capturedTxHash) {
                clearInterval(checkInterval)
                resolve(null)
              }
            }, 100)
            setTimeout(() => {
              clearInterval(checkInterval)
              resolve(null)
            }, 30000)
          }),
        ])
      } catch (e) {
        // Execution may have failed, but check if we got txHash
        executionError = e
        // Log to stderr so Python can capture it
        console.error(`[LiFi] executeRoute error: ${e.message}`)
        if (e.stack) {
          console.error(`[LiFi] executeRoute stack: ${e.stack.split('\n').slice(0, 5).join('\n')}`)
        }
      }
      
      // If no txHash captured yet, try to extract from final route
      if (!capturedTxHash && finalRoute) {
        for (const step of finalRoute.steps || []) {
          const processes = step.execution?.process || []
          for (const process of processes) {
            if (process.txHash) {
              capturedTxHash = process.txHash
              capturedTxLink = process.txLink
              break
            }
          }
        }
      }
      
      if (!capturedTxHash) {
        // Log diagnostic information to stderr so Python can capture it
        const diagnostics = {
          hookCallCount: hookCallCount,
          hasFinalRoute: !!finalRoute,
          finalRouteSteps: finalRoute?.steps?.length || 0,
          executionError: executionError?.message || null,
          fromChain: fromChainId,
          toChain: toChainId,
          fromToken: fromToken.address,
          toToken: toToken.address,
        }
        console.error(`[LiFi] No transaction hash captured. Diagnostics: ${JSON.stringify(diagnostics)}`)
        
        // Log route structure summary if available
        if (finalRoute) {
          const routeSummary = {
            steps: finalRoute.steps?.map(step => ({
              tool: step.toolDetails?.name || step.tool,
              executionStatus: step.execution?.status,
              processCount: step.execution?.process?.length || 0,
              processes: step.execution?.process?.map(p => ({
                type: p.type,
                status: p.status,
                hasTxHash: !!p.txHash,
                error: p.error?.message || null,
              })) || [],
            })) || [],
          }
          console.error(`[LiFi] Route structure: ${JSON.stringify(routeSummary)}`)
        }
        
        throw new Error(`No transaction hash captured. ${executionError ? `Execution error: ${executionError.message}` : 'No execution error caught.'}`)
      }
      
      // Verify confirmation
      let confirmed = false
      let attempts = 0
      const maxAttempts = fromChainId === ChainId.SOL ? 30 : 60
      
      while (!confirmed && attempts < maxAttempts) {
        const status = await checkTxStatus(fromChainId, capturedTxHash)
        
        if (fromChainId === ChainId.SOL) {
          if (status && !status.err && (status.confirmationStatus === 'confirmed' || status.confirmationStatus === 'finalized')) {
            confirmed = true
          } else if (status?.err) {
            throw new Error(`Transaction failed: ${JSON.stringify(status.err)}`)
          }
        } else {
          if (status) {
            if (status.status === 'success') {
              confirmed = true
            } else if (status.status === 'reverted') {
              throw new Error('Transaction reverted')
            }
          }
        }
        
        if (!confirmed) {
          attempts++
          await new Promise((resolve) => setTimeout(resolve, fromChainId === ChainId.SOL ? 1000 : 2000))
        }
      }
      
      if (!confirmed) {
        throw new Error(`Transaction not confirmed within ${maxAttempts * (fromChainId === ChainId.SOL ? 1 : 2)}s`)
      }
    }
    
    // Calculate actual tokens received and slippage
    const fromTokenDecimals = fromToken.decimals || 18
    let toTokenDecimals = toToken.decimals || 18
    const rawToAmount = Number(route.toAmountMin ?? route.toAmount)
    const fromAmount = Number(input.amount) / (10 ** fromTokenDecimals)
    let expectedOutput = rawToAmount / (10 ** toTokenDecimals)
    let actualOutput = expectedOutput
    let tokensReceivedRaw = null
    
    if (process.env.LOTUS_DEBUG_LIFI === '1') {
      console.log('[LiFi] resolveActualOutput input', {
        toChainId,
        txHash: capturedTxHash,
        tokenAddress: toToken.address,
        walletAddress: toAddress,
      })
    }
    const actualInfo = await resolveActualOutput({
      chainId: toChainId,
      txHash: capturedTxHash,
      tokenAddress: toToken.address,
      walletAddress: toAddress,
      expectedOutput,
      fallbackDecimals: toTokenDecimals,
    })
    
    if (actualInfo) {
      actualOutput = actualInfo.amount
      tokensReceivedRaw = actualInfo.rawAmount
      if (actualInfo.decimals != null) {
        toTokenDecimals = actualInfo.decimals
        expectedOutput = rawToAmount / (10 ** toTokenDecimals)
      }
    }
    
    if (!tokensReceivedRaw && actualOutput !== undefined && actualOutput !== null) {
      try {
        tokensReceivedRaw = BigInt(Math.round(actualOutput * (10 ** toTokenDecimals))).toString()
      } catch (error) {
        tokensReceivedRaw = null
      }
    }
    
    const slippage = expectedOutput > 0 ? ((expectedOutput - actualOutput) / expectedOutput) * 100 : 0
    
    // Calculate price (fromToken price in toToken)
    const price = fromAmount > 0 ? actualOutput / fromAmount : 0
    
  return {
    success: true,
    tx_hash: capturedTxHash,
    tx_link: capturedTxLink,
    tokens_received: actualOutput,
    tokens_received_raw: tokensReceivedRaw,
    to_token_decimals: toTokenDecimals,
    from_token_decimals: fromTokenDecimals,
    price: price,
    slippage: slippage,
    tool: capturedStepTool,
  }
  console.log('[LiFi] fromAddress', fromAddress, 'toAddress', toAddress)
    
  } catch (error) {
    return {
      success: false,
      error: error.message,
    }
  }
}

// Bridge execution function
const executeBridge = async (input) => {
  try {
    await initSDK()
    
    const fromChainId = CHAIN_ID_MAP[input.fromChain?.toLowerCase()]
    const toChainId = CHAIN_ID_MAP[input.toChain?.toLowerCase()]
    
    if (!fromChainId || !toChainId) {
      throw new Error(`Unsupported chains: ${input.fromChain} → ${input.toChain}`)
    }
    
    const fromToken = await resolveToken(fromChainId, input.fromToken)
    const toToken = await resolveToken(toChainId, input.toToken)
    const fromAddress = await getWalletAddress(fromChainId)
    const toAddress = input.toAddress || await getWalletAddress(toChainId)
    
    const request = {
      fromChainId: fromChainId,
      toChainId: toChainId,
      fromAmount: input.amount,
      fromTokenAddress: fromToken.address,
      toTokenAddress: toToken.address,
      fromAddress: fromAddress,
      toAddress: toAddress,
      options: {
        allowSwitchChain: true,
        slippage: input.slippage || 0.5,
      },
    }
    
    // Get route
    const { routes, unavailableRoutes } = await getRoutes(request)
    
    if (!routes?.length) {
      throw new Error(`No routes available: ${JSON.stringify(unavailableRoutes)}`)
    }
    
    const route = routes[0]
    
    if (input.dryRun) {
      return {
        success: true,
        dryRun: true,
        estimatedOutput: route.toAmountMin ?? route.toAmount,
        estimatedUSD: route.toAmountUSD,
        route: route.steps.map(s => s.toolDetails?.name || s.tool).join(' → '),
      }
    }
    
    // Execute bridge (same logic as swap but with cross-chain handling)
    // This will be handled in executeSwap when fromChainId !== toChainId
    return await executeSwap(input)
    
  } catch (error) {
    return {
      success: false,
      error: error.message,
    }
  }
}

// Main entry point
const main = async () => {
  try {
    // Read input from stdin or command-line args
    let input
    if (process.argv.length > 2) {
      // Command-line args: JSON string
      input = JSON.parse(process.argv[2])
    } else {
      // Read from stdin
      let stdinData = ''
      for await (const chunk of process.stdin) {
        stdinData += chunk
      }
      input = JSON.parse(stdinData)
    }
    
    // Route to appropriate function based on action
    let result
    if (input.action === 'bridge') {
      result = await executeBridge(input)
    } else {
      result = await executeSwap(input)
    }
    
    console.log(JSON.stringify(result))
    
  } catch (error) {
    console.error(JSON.stringify({
      success: false,
      error: error.message,
    }))
    process.exit(1)
  }
}

main()

