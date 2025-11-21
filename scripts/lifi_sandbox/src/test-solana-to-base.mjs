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
import { createWalletClient, createPublicClient, http } from 'viem'
import { privateKeyToAccount } from 'viem/accounts'
import { base as baseChain } from 'viem/chains'
import { Connection, PublicKey } from '@solana/web3.js'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const envPath = resolve(__dirname, '../../../.env')
loadEnv({ path: envPath })

const dryRun = process.env.LIFI_DRY_RUN !== 'false'
const integrator = process.env.LIFI_INTEGRATOR ?? 'LotusTraderSandbox'
const apiKey = process.env.LIFI_API_KEY

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

// Solana setup
const solanaPrivateKey = maybeEnv('SOL_WALLET_PRIVATE_KEY')
const heliusApiKey = maybeEnv('HELIUS_API_KEY')
const solanaRpcUrl = heliusApiKey
  ? `https://mainnet.helius-rpc.com/?api-key=${heliusApiKey}`
  : maybeEnv('SOLANA_RPC_URL')

if (!solanaPrivateKey || !solanaRpcUrl) {
  console.error('SOL_WALLET_PRIVATE_KEY and HELIUS_API_KEY (or SOLANA_RPC_URL) are required')
  process.exit(1)
}

const solanaAdapter = new KeypairWalletAdapter(solanaPrivateKey)
const solAddress = solanaAdapter.publicKey?.toString()

if (!solAddress) {
  console.error('Failed to derive Solana address from private key')
  process.exit(1)
}

// Base setup
let basePrivateKey = normalizePrivateKey(maybeEnv('BASE_WALLET_PRIVATE_KEY'))
let baseRpcUrl = maybeEnv('BASE_RPC_URL')

// Construct BASE RPC from ETH RPC if needed
if (!baseRpcUrl) {
  const ethRpc = maybeEnv(['ETH_RPC_URL', 'ETHEREUM_RPC_URL'])
  if (ethRpc && ethRpc.includes('rpc.ankr.com/eth/')) {
    const apiKeyMatch = ethRpc.match(/rpc\.ankr\.com\/eth\/([^\/]+)/)
    if (apiKeyMatch) {
      baseRpcUrl = `https://rpc.ankr.com/base/${apiKeyMatch[1]}`
    }
  }
}

if (!basePrivateKey || !baseRpcUrl) {
  console.error('BASE_WALLET_PRIVATE_KEY and BASE_RPC_URL (or ETH_RPC_URL) are required')
  process.exit(1)
}

const baseAccount = privateKeyToAccount(basePrivateKey)
const baseWalletClient = createWalletClient({
  account: baseAccount,
  chain: baseChain,
  transport: http(baseRpcUrl, { retryCount: 2 }),
})

const basePublicClient = createPublicClient({
  chain: baseChain,
  transport: http(baseRpcUrl, { retryCount: 2 }),
})

console.log(`Solana wallet: ${solAddress}`)
console.log(`Base wallet: ${baseAccount.address}`)

createConfig({
  integrator,
  apiKey,
  providers: [
    Solana({
      getWalletAdapter: async () => solanaAdapter,
    }),
    EVM({
      getWalletClient: async () => baseWalletClient,
      switchChain: async () => baseWalletClient,
    }),
  ],
  rpcUrls: {
    [ChainId.SOL]: [solanaRpcUrl],
    [ChainId.BAS]: [baseRpcUrl],
  },
  debug: true,
})

await sdkConfig.getChains()

const resolveToken = async (chainId, preferredSymbols) => {
  const symbols = preferredSymbols.map((s) => s.toUpperCase())
  const response = await getTokens({ chains: [chainId] })
  const tokens = response.tokens?.[chainId] ?? []
  const match = tokens.find((token) => {
    if (!token.symbol) return false
    return symbols.includes(token.symbol.toUpperCase())
  })
  if (!match) {
    throw new Error(
      `Unable to locate token for symbols [${preferredSymbols.join(', ')}] on chainId ${chainId}`
    )
  }
  return match
}

const main = async () => {
  console.log('\n=== Solana → Base Cross-Chain Bridge Test ===\n')
  console.log(`Integrator: ${integrator}`)
  console.log(`Dry run: ${dryRun}`)
  console.log(`Solana RPC: ${solanaRpcUrl.replace(/\/\/.*@/, '//***@')}`)
  console.log(`Base RPC: ${baseRpcUrl.replace(/\/\/.*@/, '//***@')}`)

  const fromToken = await resolveToken(ChainId.SOL, ['SOL'])
  const toToken = await resolveToken(ChainId.BAS, ['WETH', 'ETH'])

  // Check Solana balance
  const solConnection = new Connection(solanaRpcUrl)
  const solPublicKey = new PublicKey(solAddress)
  const solBalance = await solConnection.getBalance(solPublicKey)
  console.log(`  Solana balance: ${(solBalance / 1e9).toFixed(6)} SOL`)

  // Check Base balance
  const baseBalance = await basePublicClient.getBalance({ address: baseAccount.address })
  console.log(`  Base balance: ${(Number(baseBalance) / 1e18).toFixed(6)} ETH`)

  // Small amount for testing - 0.01 SOL
  const fromAmount = '10000000' // 0.01 SOL (9 decimals)

  if (solBalance < Number(fromAmount)) {
    console.error(`\n✗ Insufficient SOL balance`)
    console.error(`  Required: ${Number(fromAmount) / 1e9} SOL`)
    console.error(`  Available: ${solBalance / 1e9} SOL`)
    process.exit(1)
  }

  const request = {
    fromChainId: ChainId.SOL,
    toChainId: ChainId.BAS,
    fromAmount: fromAmount,
    fromTokenAddress: fromToken.address,
    toTokenAddress: toToken.address,
    fromAddress: solAddress,
    toAddress: baseAccount.address,
    options: {
      allowSwitchChain: true,
    },
  }

  console.log('\nRequest:')
  console.log(`  From: ${fromToken.symbol} on Solana (${fromToken.address})`)
  console.log(`  To: ${toToken.symbol} on Base (${toToken.address})`)
  console.log(`  Amount: ${request.fromAmount} (${Number(request.fromAmount) / 1e9} ${fromToken.symbol})`)

  console.log('\nFetching routes...')
  const { routes, unavailableRoutes } = await getRoutes(request)

  if (!routes?.length) {
    console.error('No routes available')
    if (unavailableRoutes?.failed?.length) {
      console.error('Failed routes:', unavailableRoutes.failed)
    }
    return
  }

  const route = routes[0]
  console.log(`\nRoute found: ${route.steps.map(s => s.toolDetails?.name || s.tool).join(' → ')}`)
  console.log(`  Estimated output: ${route.toAmountMin ?? route.toAmount} ${toToken.symbol}`)
  console.log(`  Estimated USD: $${Number(route.toAmountUSD ?? 0).toFixed(4)}`)

  if (dryRun) {
    console.log('\n✓ Dry run complete - route is valid')
    return
  }

  console.log('\nExecuting route...')
  const startTime = Date.now()

  // Helper to check Solana transaction status
  const checkSolanaTxStatus = async (txHash) => {
    if (!txHash) return null
    try {
      const status = await solConnection.getSignatureStatus(txHash, {
        searchTransactionHistory: true,
      })
      return status.value
    } catch (e) {
      return null
    }
  }

  // Helper to check Base transaction status
  const checkBaseTxStatus = async (txHash) => {
    if (!txHash) return null
    try {
      const receipt = await basePublicClient.getTransactionReceipt({ hash: txHash })
      return receipt
    } catch (e) {
      return null
    }
  }

  // Capture txHash using updateRouteHook - called whenever execution state updates
  let capturedTxHashes = []
  let capturedTxLinks = []
  let capturedStepTools = []
  let capturedStepChains = []

  const captureTxHash = (updatedRoute) => {
    // Check all steps for txHash
    for (const step of updatedRoute.steps || []) {
      const processes = step.execution?.process || []
      for (const process of processes) {
        if (process.txHash && !capturedTxHashes.includes(process.txHash)) {
          // Determine chain ID: for RECEIVING_CHAIN, use toChainId; otherwise fromChainId
          const chainId = process.type === 'RECEIVING_CHAIN' 
            ? step.action.toChainId 
            : (step.action.fromChainId || step.action.toChainId)
          
          capturedTxHashes.push(process.txHash)
          capturedTxLinks.push(process.txLink)
          capturedStepTools.push(step.toolDetails?.name || step.tool)
          capturedStepChains.push(chainId)
          console.log(`\n✓ Transaction submitted: ${process.txHash}`)
          console.log(`  Step: ${step.toolDetails?.name || step.tool}`)
          console.log(`  Type: ${process.type}`)
          console.log(`  Chain: ${chainId} (${chainId === ChainId.SOL ? 'Solana' : chainId === ChainId.BAS ? 'Base' : 'Unknown'})`)
          if (process.txLink) {
            console.log(`  Explorer: ${process.txLink}`)
          }
        }
      }
    }
  }

  // Start SDK execution with hook to capture txHash
  // Don't await immediately - let it run while we check for transactions
  let executionCompleted = false
  let executionError = null
  
  // Start execution in background (don't await)
  const executionPromise = (async () => {
    try {
      await executeRoute(route, {
        executeInBackground: false,
        updateRouteHook: captureTxHash,
      })
      executionCompleted = true
    } catch (err) {
      executionError = err
    }
  })()
  
  // Suppress unhandled rejection warnings
  executionPromise.catch(() => {})

  try {
    // Wait for source transaction to be captured
    let sourceTxCaptured = false
    let waitForSourceAttempts = 0
    const maxWaitForSource = 60

    while (!sourceTxCaptured && waitForSourceAttempts < maxWaitForSource) {
      // Check if we have a Solana transaction
      for (let i = 0; i < capturedTxHashes.length; i++) {
        const chainId = capturedStepChains[i]
        if (chainId === ChainId.SOL) {
          sourceTxCaptured = true
          break
        }
      }
      
      if (!sourceTxCaptured) {
        waitForSourceAttempts++
        await new Promise((resolve) => setTimeout(resolve, 1000))
        if (waitForSourceAttempts % 5 === 0) {
          console.log(`  [${waitForSourceAttempts}s] Waiting for source transaction...`)
        }
      }
    }

    if (!sourceTxCaptured) {
      throw new Error('Source transaction not captured within timeout')
    }

    if (capturedTxHashes.length > 0) {
      console.log(`\nVerifying transactions using our RPCs...`)

      // Find Solana transaction by chain ID
      let solanaTxHash = null
      let solanaTxLink = null
      for (let i = 0; i < capturedTxHashes.length; i++) {
        const chainId = capturedStepChains[i]
        if (chainId === ChainId.SOL) {
          solanaTxHash = capturedTxHashes[i]
          solanaTxLink = capturedTxLinks[i]
          break
        }
      }

      // Verify source chain transaction (Solana)
      if (!solanaTxHash) {
        throw new Error('Solana transaction hash not found')
      }

      console.log(`\nChecking Solana transaction: ${solanaTxHash.substring(0, 16)}...`)
      let solConfirmed = false
      let attempts = 0
      const maxAttempts = 30

      while (!solConfirmed && attempts < maxAttempts) {
        const txStatus = await checkSolanaTxStatus(solanaTxHash)
        if (txStatus) {
          if (txStatus.err) {
            console.log(`  ✗ Solana transaction failed: ${JSON.stringify(txStatus.err)}`)
            throw new Error(`Solana transaction failed: ${JSON.stringify(txStatus.err)}`)
          } else if (
            txStatus.confirmationStatus === 'confirmed' ||
            txStatus.confirmationStatus === 'finalized'
          ) {
            solConfirmed = true
            console.log(`  ✓ Solana transaction confirmed: ${txStatus.confirmationStatus}`)
            break
          }
        }
        attempts++
        await new Promise((resolve) => setTimeout(resolve, 1000))
        if (attempts % 5 === 0) {
          console.log(`  [${attempts}s] Waiting for Solana confirmation...`)
        }
      }

      // For cross-chain, wait for destination chain transaction
      // The SDK will provide it via updateRouteHook as the bridge completes
      console.log(`\nWaiting for destination transaction on Base...`)
      let baseTxHash = null
      let baseTxLink = null
      let waitForDestinationAttempts = 0
      const maxWaitForDestination = 300 // 5 minutes max to wait for destination tx

      // Find Base transaction by chain ID
      const findBaseTx = () => {
        for (let i = 0; i < capturedTxHashes.length; i++) {
          const chainId = capturedStepChains[i]
          if (chainId === ChainId.BAS) {
            return {
              hash: capturedTxHashes[i],
              link: capturedTxLinks[i],
            }
          }
        }
        return null
      }

      // Keep checking for destination transaction from SDK
      // The hook will be called multiple times as the route progresses
      while (!baseTxHash && waitForDestinationAttempts < maxWaitForDestination) {
        // Check if SDK has provided a Base transaction hash
        const baseTx = findBaseTx()
        if (baseTx) {
          baseTxHash = baseTx.hash
          baseTxLink = baseTx.link
          break
        }
        
        waitForDestinationAttempts++
        await new Promise((resolve) => setTimeout(resolve, 2000))
        if (waitForDestinationAttempts % 10 === 0) {
          console.log(`  [${waitForDestinationAttempts * 2}s] Waiting for SDK to provide destination transaction...`)
        }
      }

      // If we still don't have destination tx, wait for execution to complete
      // and check the final route state (hook might be called one more time)
      if (!baseTxHash) {
        console.log(`  SDK hasn't provided destination tx yet, waiting for execution to complete...`)
        // Wait for execution to finish (with timeout)
        const executionWaitStart = Date.now()
        while (!executionCompleted && !executionError && (Date.now() - executionWaitStart) < 300000) {
          await new Promise((resolve) => setTimeout(resolve, 1000))
        }
        
        // Check one more time after execution completes
        const baseTx = findBaseTx()
        if (baseTx) {
          baseTxHash = baseTx.hash
          baseTxLink = baseTx.link
        }
      }

      if (baseTxHash) {
        // We have destination transaction - confirm it on Base
        console.log(`\nChecking Base transaction: ${baseTxHash.substring(0, 16)}...`)
        let baseConfirmed = false
        let attempts = 0
        const maxAttempts = 60

        while (!baseConfirmed && attempts < maxAttempts) {
          const receipt = await checkBaseTxStatus(baseTxHash)
          if (receipt) {
            if (receipt.status === 'success') {
              baseConfirmed = true
              const duration = ((Date.now() - startTime) / 1000).toFixed(1)
              console.log(`  ✓ Base transaction confirmed: success`)
              console.log(`  Gas used: ${receipt.gasUsed.toString()}`)
              console.log(`  Block: ${receipt.blockNumber.toString()}`)
              console.log(`\n✓ SUCCESS - Cross-chain bridge completed in ${duration}s`)
              console.log(`  Solana tx: ${solanaTxHash}`)
              console.log(`  Base tx: ${baseTxHash}`)
              if (solanaTxLink) {
                console.log(`  Solana explorer: ${solanaTxLink}`)
              }
              if (baseTxLink) {
                console.log(`  Base explorer: ${baseTxLink}`)
              }
              process.exit(0)
            } else if (receipt.status === 'reverted') {
              console.log(`  ✗ Base transaction reverted`)
              throw new Error(`Base transaction reverted`)
            }
          }
          attempts++
          await new Promise((resolve) => setTimeout(resolve, 2000))
          if (attempts % 5 === 0) {
            console.log(`  [${attempts * 2}s] Waiting for Base confirmation...`)
          }
        }

        if (!baseConfirmed) {
          console.log(`  ⚠ Could not confirm Base transaction within ${maxAttempts * 2}s, but txHash exists`)
          console.log(`  Base tx: ${baseTxHash}`)
          if (baseTxLink) {
            console.log(`  Explorer: ${baseTxLink}`)
          }
        }
      } else {
        // No destination transaction found - bridge might be async or SDK didn't provide it
        const duration = ((Date.now() - startTime) / 1000).toFixed(1)
        console.log(`\n⚠ SDK did not provide destination transaction hash within ${maxWaitForDestination * 2}s`)
        console.log(`  Solana tx confirmed: ${solanaTxHash}`)
        if (solanaTxLink) {
          console.log(`  Solana explorer: ${solanaTxLink}`)
        }
        console.log(`\n  Note: Bridge may complete asynchronously. Check Base wallet for incoming funds.`)
        console.log(`  Bridge time: ${duration}s (source confirmed, destination pending)`)
        process.exit(0)
      }
    } else {
      // No txHash captured, wait for SDK execution
      console.log(`  Waiting for SDK execution to complete...`)
      await executionPromise
    }
  } catch (error) {
    // If we captured txHash, verify it succeeded despite the error
    if (capturedTxHashes.length > 0) {
      console.log(`\n⚠ SDK error, but checking transaction status...`)
      for (let i = 0; i < capturedTxHashes.length; i++) {
        const txHash = capturedTxHashes[i]
        console.log(`  Checking tx ${i + 1}: ${txHash.substring(0, 16)}...`)

        // Try Solana first
        const solStatus = await checkSolanaTxStatus(txHash)
        if (solStatus && !solStatus.err && solStatus.confirmationStatus) {
          console.log(`  ✓ Solana tx confirmed: ${solStatus.confirmationStatus}`)
          continue
        }

        // Try Base
        const baseReceipt = await checkBaseTxStatus(txHash)
        if (baseReceipt && baseReceipt.status === 'success') {
          const duration = ((Date.now() - startTime) / 1000).toFixed(1)
          console.log(`  ✓ Base tx confirmed: success`)
          console.log(`\n✓ SUCCESS - Transaction completed in ${duration}s (despite SDK error)`)
          console.log(`  Hash: ${txHash}`)
          if (capturedTxLinks[i]) {
            console.log(`  Explorer: ${capturedTxLinks[i]}`)
          }
          process.exit(0)
        }
      }
    }

    const duration = ((Date.now() - startTime) / 1000).toFixed(1)
    console.error(`\n✗ Execution failed after ${duration}s`)
    console.error(`Error: ${error.message}`)
    process.exitCode = 1
  }
}

main().catch((error) => {
  console.error('Fatal error:', error)
  process.exitCode = 1
})

