import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { existsSync, statSync } from 'node:fs'
import { config as loadEnv } from 'dotenv'
import {
  Solana,
  KeypairWalletAdapter,
  createConfig,
  getRoutes,
  executeRoute,
  getTokens,
  getStatus,
  config as sdkConfig,
} from '@lifi/sdk'
import { ChainId } from '@lifi/types'
import { Connection } from '@solana/web3.js'

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

const solanaPrivateKey = maybeEnv('SOL_WALLET_PRIVATE_KEY')
const heliusApiKey = maybeEnv('HELIUS_API_KEY')
const solanaRpcUrl = heliusApiKey
  ? `https://mainnet.helius-rpc.com/?api-key=${heliusApiKey}`
  : maybeEnv('SOLANA_RPC_URL')

if (!solanaPrivateKey) {
  console.error('SOL_WALLET_PRIVATE_KEY is required')
  process.exit(1)
}

if (!solanaRpcUrl) {
  console.error('HELIUS_API_KEY or SOLANA_RPC_URL is required')
  process.exit(1)
}

const solanaAdapter = new KeypairWalletAdapter(solanaPrivateKey)
const solAddress = solanaAdapter.publicKey?.toString()

if (!solAddress) {
  console.error('Failed to derive Solana address from private key')
  process.exit(1)
}

console.log(`Solana wallet address: ${solAddress}`)

createConfig({
  integrator,
  apiKey,
  providers: [
    Solana({
      getWalletAdapter: async () => solanaAdapter,
    }),
  ],
  rpcUrls: {
    [ChainId.SOL]: [solanaRpcUrl],
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
  console.log('\n=== Solana Spot Swap Test ===\n')
  console.log(`Integrator: ${integrator}`)
  console.log(`Dry run: ${dryRun}`)
  console.log(`RPC: ${solanaRpcUrl.replace(/\/\/.*@/, '//***@')}`)

  const fromToken = await resolveToken(ChainId.SOL, ['USDC'])
  const toToken = await resolveToken(ChainId.SOL, ['SOL'])

  const request = {
    fromChainId: ChainId.SOL,
    toChainId: ChainId.SOL,
    fromAmount: '100000', // 0.1 USDC
    fromTokenAddress: fromToken.address,
    toTokenAddress: toToken.address,
    fromAddress: solAddress,
    toAddress: solAddress,
    options: {
      allowSwitchChain: true,
    },
  }

  console.log('\nRequest:')
  console.log(`  From: ${fromToken.symbol} (${fromToken.address})`)
  console.log(`  To: ${toToken.symbol} (${toToken.address})`)
  console.log(`  Amount: ${request.fromAmount} (${Number(request.fromAmount) / 1e6} ${fromToken.symbol})`)

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
  
  // Our own RPC connection for verification
  const connection = new Connection(solanaRpcUrl)
  
  // Helper to check transaction status using our RPC
  const checkTxStatus = async (txHash) => {
    if (!txHash) return null
    try {
      const status = await connection.getSignatureStatus(txHash, {
        searchTransactionHistory: true,
      })
      return status.value
    } catch (e) {
      return null
    }
  }

  // Capture txHash using updateRouteHook - called whenever execution state updates
  let capturedTxHash = null
  let capturedTxLink = null
  let capturedStepTool = null
  
  const captureTxHash = (updatedRoute) => {
    // Check all steps for txHash
    for (const step of updatedRoute.steps || []) {
      const processes = step.execution?.process || []
      for (const process of processes) {
        if (process.txHash && !capturedTxHash) {
          capturedTxHash = process.txHash
          capturedTxLink = process.txLink
          capturedStepTool = step.toolDetails?.name || step.tool
          console.log(`\n✓ Transaction submitted by SDK: ${capturedTxHash}`)
          console.log(`  Tool: ${capturedStepTool}`)
          if (capturedTxLink) {
            console.log(`  Explorer: ${capturedTxLink}`)
          }
        }
      }
    }
  }

  // Start SDK execution with hook to capture txHash
  const executionPromise = executeRoute(route, {
    executeInBackground: false,
    updateRouteHook: captureTxHash,
  })

  try {
    // Wait for txHash to be captured OR execution to complete
    await Promise.race([
      executionPromise,
      new Promise((resolve) => {
        // Wait up to 30s for txHash to appear
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

    if (capturedTxHash) {
      // Verify confirmation ourselves using our RPC
      console.log(`\nVerifying confirmation using our RPC...`)
      let confirmed = false
      let attempts = 0
      const maxAttempts = 30 // 30 seconds max
      
      while (!confirmed && attempts < maxAttempts) {
        const txStatus = await checkTxStatus(capturedTxHash)
        if (txStatus) {
          if (txStatus.err) {
            console.log(`  ✗ Transaction failed: ${JSON.stringify(txStatus.err)}`)
            throw new Error(`Transaction failed: ${JSON.stringify(txStatus.err)}`)
          } else if (txStatus.confirmationStatus === 'confirmed' || txStatus.confirmationStatus === 'finalized') {
            confirmed = true
            const duration = ((Date.now() - startTime) / 1000).toFixed(1)
            console.log(`  ✓ Transaction confirmed: ${txStatus.confirmationStatus}`)
            console.log(`\n✓ SUCCESS - Transaction completed in ${duration}s`)
            console.log(`  Hash: ${capturedTxHash}`)
            if (capturedTxLink) {
              console.log(`  Explorer: ${capturedTxLink}`)
            }
            // Don't wait for SDK - we're done!
            process.exit(0)
          }
        }
        attempts++
        await new Promise((resolve) => setTimeout(resolve, 1000))
        if (attempts % 5 === 0) {
          console.log(`  [${attempts}s] Waiting for confirmation...`)
        }
      }
      
      if (!confirmed) {
        console.log(`  ⚠ Could not confirm within ${maxAttempts}s, but txHash exists`)
      }
    } else {
      // No txHash captured, wait for SDK execution
      console.log(`  Waiting for SDK execution to complete...`)
      await executionPromise
    }
  } catch (error) {
    // If we captured txHash, verify it succeeded despite the error
    if (capturedTxHash) {
      console.log(`\n⚠ SDK error, but checking transaction status...`)
      const txStatus = await checkTxStatus(capturedTxHash)
      if (txStatus && !txStatus.err && txStatus.confirmationStatus) {
        const duration = ((Date.now() - startTime) / 1000).toFixed(1)
        console.log(`  ✓ Transaction IS confirmed: ${txStatus.confirmationStatus}`)
        console.log(`\n✓ SUCCESS - Transaction completed in ${duration}s (despite SDK error)`)
        console.log(`  Hash: ${capturedTxHash}`)
        if (capturedTxLink) {
          console.log(`  Explorer: ${capturedTxLink}`)
        }
        process.exit(0) // Success!
      } else if (txStatus?.err) {
        console.log(`  ✗ Transaction failed: ${JSON.stringify(txStatus.err)}`)
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

