import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { config as loadEnv } from 'dotenv'
import {
  EVM,
  createConfig,
  getRoutes,
  executeRoute,
  getTokens,
  config as sdkConfig,
} from '@lifi/sdk'
import { ChainId } from '@lifi/types'
import { createWalletClient, createPublicClient, http, erc20Abi } from 'viem'
import { privateKeyToAccount } from 'viem/accounts'
import { bsc } from 'viem/chains'

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

const bscPrivateKey = normalizePrivateKey(maybeEnv('BSC_WALLET_PRIVATE_KEY'))
const bscRpcUrl = maybeEnv('BSC_RPC_URL')

if (!bscPrivateKey || !bscRpcUrl) {
  console.error('BSC_WALLET_PRIVATE_KEY and BSC_RPC_URL are required')
  process.exit(1)
}

const account = privateKeyToAccount(bscPrivateKey)
const walletClient = createWalletClient({
  account,
  chain: bsc,
  transport: http(bscRpcUrl, { retryCount: 2 }),
})

const publicClient = createPublicClient({
  chain: bsc,
  transport: http(bscRpcUrl, { retryCount: 2 }),
})

console.log(`BSC wallet address: ${account.address}`)

createConfig({
  integrator,
  apiKey,
  providers: [
    EVM({
      getWalletClient: async () => walletClient,
      switchChain: async () => walletClient,
    }),
  ],
  rpcUrls: {
    [ChainId.BSC]: [bscRpcUrl],
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
  console.log('\n=== BSC Spot Swap Test ===\n')
  console.log(`Integrator: ${integrator}`)
  console.log(`Dry run: ${dryRun}`)
  console.log(`RPC: ${bscRpcUrl.replace(/\/\/.*@/, '//***@')}`)

  const fromToken = await resolveToken(ChainId.BSC, ['USDC', 'USDC.E'])
  const toToken = await resolveToken(ChainId.BSC, ['WBNB', 'BNB'])

  // Check balances first
  const nativeBalance = await publicClient.getBalance({ address: account.address })
  console.log(`  Native balance: ${(Number(nativeBalance) / 1e18).toFixed(6)} BNB`)
  
  // Check token balance
  const fromAmount = '100000' // 0.1 USDC (6 decimals)
  
  // Check if we have enough of the source token
  try {
    const tokenBalance = await publicClient.readContract({
      address: fromToken.address,
      abi: erc20Abi,
      functionName: 'balanceOf',
      args: [account.address],
    })
    const decimals = fromToken.decimals || 18
    const balanceFormatted = Number(tokenBalance) / (10 ** decimals)
    console.log(`  ${fromToken.symbol} balance: ${balanceFormatted.toFixed(6)}`)
    
    if (Number(tokenBalance) < Number(fromAmount)) {
      console.error(`\n✗ Insufficient ${fromToken.symbol} balance`)
      console.error(`  Required: ${Number(fromAmount) / (10 ** decimals)} ${fromToken.symbol}`)
      console.error(`  Available: ${balanceFormatted} ${fromToken.symbol}`)
      process.exit(1)
    }
  } catch (e) {
    console.warn(`  Could not check ${fromToken.symbol} balance: ${e.message}`)
  }
  
  const request = {
    fromChainId: ChainId.BSC,
    toChainId: ChainId.BSC,
    fromAmount: fromAmount,
    fromTokenAddress: fromToken.address,
    toTokenAddress: toToken.address,
    fromAddress: account.address,
    toAddress: account.address,
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
  
  // Helper to check transaction status using our RPC
  const checkTxStatus = async (txHash) => {
    if (!txHash) return null
    try {
      const receipt = await publicClient.getTransactionReceipt({ hash: txHash })
      return receipt
    } catch (e) {
      // Transaction might not be confirmed yet
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
      const maxAttempts = 60 // 60 seconds max for EVM
      
      while (!confirmed && attempts < maxAttempts) {
        const receipt = await checkTxStatus(capturedTxHash)
        if (receipt) {
          if (receipt.status === 'success') {
            confirmed = true
            const duration = ((Date.now() - startTime) / 1000).toFixed(1)
            console.log(`  ✓ Transaction confirmed: success`)
            console.log(`  Gas used: ${receipt.gasUsed.toString()}`)
            console.log(`  Block: ${receipt.blockNumber.toString()}`)
            console.log(`\n✓ SUCCESS - Transaction completed in ${duration}s`)
            console.log(`  Hash: ${capturedTxHash}`)
            if (capturedTxLink) {
              console.log(`  Explorer: ${capturedTxLink}`)
            }
            // Don't wait for SDK - we're done!
            process.exit(0)
          } else if (receipt.status === 'reverted') {
            console.log(`  ✗ Transaction reverted`)
            throw new Error(`Transaction reverted`)
          }
        }
        attempts++
        await new Promise((resolve) => setTimeout(resolve, 2000)) // Check every 2 seconds for EVM
        if (attempts % 5 === 0) {
          console.log(`  [${attempts * 2}s] Waiting for confirmation...`)
        }
      }
      
      if (!confirmed) {
        console.log(`  ⚠ Could not confirm within ${maxAttempts * 2}s, but txHash exists`)
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
      const receipt = await checkTxStatus(capturedTxHash)
      if (receipt && receipt.status === 'success') {
        const duration = ((Date.now() - startTime) / 1000).toFixed(1)
        console.log(`  ✓ Transaction IS confirmed: success`)
        console.log(`\n✓ SUCCESS - Transaction completed in ${duration}s (despite SDK error)`)
        console.log(`  Hash: ${capturedTxHash}`)
        if (capturedTxLink) {
          console.log(`  Explorer: ${capturedTxLink}`)
        }
        process.exit(0) // Success!
      } else if (receipt?.status === 'reverted') {
        console.log(`  ✗ Transaction reverted`)
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

