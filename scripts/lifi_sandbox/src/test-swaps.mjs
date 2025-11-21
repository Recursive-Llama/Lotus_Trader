import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { existsSync, statSync } from 'node:fs'
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
import { createWalletClient, http } from 'viem'
import { privateKeyToAccount } from 'viem/accounts'
import { base as baseChain, bsc, mainnet } from 'viem/chains'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const envPath = resolve(__dirname, '../../../.env')
if (process.env.DEBUG_LIFI) {
  console.log('Loading .env from:', envPath)
  const exists = existsSync(envPath)
  console.log('  File exists:', exists)
  if (exists) {
    const stats = statSync(envPath)
    console.log('  File size:', stats.size, 'bytes')
  }
}

const result = loadEnv({ path: envPath })
if (process.env.DEBUG_LIFI) {
  console.log('Dotenv result:', result)
}

const chainRegistry = new Map([
  [ChainId.ETH, { viemChain: mainnet, label: 'ethereum' }],
  [ChainId.BAS, { viemChain: baseChain, label: 'base' }],
  [ChainId.BSC, { viemChain: bsc, label: 'bsc' }],
])

const __optional = { optional: true }

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

const maybeEnv = (names) => resolveEnv(names, __optional)

const dryRun = process.env.LIFI_DRY_RUN !== 'false'
const integrator = process.env.LIFI_INTEGRATOR ?? 'LotusTraderSandbox'
const apiKey = maybeEnv('LIFI_API_KEY')

const normalizePrivateKey = (privateKey) => {
  if (!privateKey) {
    return undefined
  }
  const trimmed = privateKey.trim()
  return trimmed.startsWith('0x') ? trimmed : `0x${trimmed}`
}

const evmChainConfigs = Array.from(chainRegistry.entries())
  .map(([chainId, baseConfig]) => {
    const envVarMap = {
      [ChainId.ETH]: { 
        key: ['ETH_WALLET_PRIVATE_KEY', 'ETHEREUM_WALLET_PRIVATE_KEY'], 
        rpc: ['ETH_RPC_URL', 'ETHEREUM_RPC_URL'] 
      },
      [ChainId.BAS]: { 
        key: ['BASE_WALLET_PRIVATE_KEY'], 
        rpc: ['BASE_RPC_URL'] 
      },
      [ChainId.BSC]: { 
        key: ['BSC_WALLET_PRIVATE_KEY'], 
        rpc: ['BSC_RPC_URL'] 
      },
    }
    const mapping = envVarMap[chainId]
    if (!mapping) {
      return undefined
    }
    const privateKey = normalizePrivateKey(maybeEnv(mapping.key))
    let rpcUrl = maybeEnv(mapping.rpc)
    
    // If RPC URL is missing but we have ETH_RPC_URL with Ankr pattern, construct it for Base
    if (!rpcUrl && chainId === ChainId.BAS) {
      const ethRpc = maybeEnv(['ETH_RPC_URL', 'ETHEREUM_RPC_URL'])
      if (ethRpc && ethRpc.includes('rpc.ankr.com/eth/')) {
        // Extract API key from ETH RPC and construct BASE RPC
        const apiKeyMatch = ethRpc.match(/rpc\.ankr\.com\/eth\/([^\/]+)/)
        if (apiKeyMatch) {
          rpcUrl = `https://rpc.ankr.com/base/${apiKeyMatch[1]}`
        }
      }
    }

    if (!privateKey || !rpcUrl) {
      return undefined
    }

    return {
      chainId,
      label: baseConfig.label,
      viemChain: baseConfig.viemChain,
      rpcUrl,
      privateKey,
    }
  })
  .filter(Boolean)

const evmConfigByChain = new Map(evmChainConfigs.map((cfg) => [cfg.chainId, cfg]))

// Debug: log what we found
if (process.env.DEBUG_LIFI) {
  console.log('EVM configs found:', evmChainConfigs.map(c => ({ chainId: c.chainId, label: c.label, hasRpc: !!c.rpcUrl, hasKey: !!c.privateKey })))
  console.log('Checking env vars:')
  console.log('  ETH_WALLET_PRIVATE_KEY:', process.env.ETH_WALLET_PRIVATE_KEY ? 'SET' : 'NOT SET')
  console.log('  ETH_RPC_URL:', process.env.ETH_RPC_URL ? 'SET' : 'NOT SET')
  console.log('  BASE_WALLET_PRIVATE_KEY:', process.env.BASE_WALLET_PRIVATE_KEY ? 'SET' : 'NOT SET')
  console.log('  BASE_RPC_URL:', process.env.BASE_RPC_URL ? 'SET' : 'NOT SET')
  console.log('  BSC_WALLET_PRIVATE_KEY:', process.env.BSC_WALLET_PRIVATE_KEY ? 'SET' : 'NOT SET')
  console.log('  BSC_RPC_URL:', process.env.BSC_RPC_URL ? 'SET' : 'NOT SET')
  console.log('  SOL_WALLET_PRIVATE_KEY:', process.env.SOL_WALLET_PRIVATE_KEY ? 'SET' : 'NOT SET')
  console.log('  HELIUS_API_KEY:', process.env.HELIUS_API_KEY ? 'SET' : 'NOT SET')
}

const solanaPrivateKey = maybeEnv('SOL_WALLET_PRIVATE_KEY')

const heliusApiKey = maybeEnv('HELIUS_API_KEY')
const solanaRpcUrl = heliusApiKey
  ? `https://mainnet.helius-rpc.com/?api-key=${heliusApiKey}`
  : maybeEnv('SOLANA_RPC_URL')

if (process.env.DEBUG_LIFI) {
  console.log('Solana config:', { hasPrivateKey: !!solanaPrivateKey, hasRpcUrl: !!solanaRpcUrl, hasHeliusKey: !!heliusApiKey })
}

const rpcUrls = {}

for (const cfg of evmChainConfigs) {
  rpcUrls[cfg.chainId] = [cfg.rpcUrl]
}

if (solanaRpcUrl) {
  rpcUrls[ChainId.SOL] = [solanaRpcUrl]
}

const walletClientCache = new Map()
const accountCache = new Map()

const getAccount = (privateKey) => {
  if (!privateKey) {
    throw new Error('Private key is required to derive an account.')
  }
  if (accountCache.has(privateKey)) {
    return accountCache.get(privateKey)
  }
  const account = privateKeyToAccount(privateKey)
  accountCache.set(privateKey, account)
  return account
}

const getWalletClient = async (chainId) => {
  if (walletClientCache.has(chainId)) {
    return walletClientCache.get(chainId)
  }
  const cfg = evmConfigByChain.get(chainId)
  if (!cfg) {
    throw new Error(`No EVM configuration found for chainId ${chainId}`)
  }
  const account = getAccount(cfg.privateKey)
  const client = createWalletClient({
    account,
    chain: cfg.viemChain,
    transport: http(cfg.rpcUrl, { retryCount: 2 }),
  })
  walletClientCache.set(chainId, client)
  return client
}

const providers = []

if (evmChainConfigs.length) {
  const [primary] = evmChainConfigs
  providers.push(
    EVM({
      getWalletClient: async () => getWalletClient(primary.chainId),
      switchChain: async (targetChainId) => getWalletClient(targetChainId),
    })
  )
}

let solanaAdapter
if (solanaPrivateKey) {
  solanaAdapter = new KeypairWalletAdapter(solanaPrivateKey)
  providers.push(
    Solana({
      getWalletAdapter: async () => solanaAdapter,
    })
  )
}

// For dry-run (quote-only), we don't need providers
// Providers are only needed for actual execution
if (!dryRun && !providers.length) {
  console.error('No providers configured. Ensure EVM and/or Solana env vars are present.')
  console.error('Note: Providers are only needed for execution. For quote-only mode (dry-run), providers are optional.')
  process.exit(1)
}

createConfig({
  integrator,
  apiKey,
  providers: providers.length > 0 ? providers : undefined,
  rpcUrls: Object.keys(rpcUrls).length > 0 ? rpcUrls : undefined,
  debug: true,
})

await sdkConfig.getChains()

const tokensCache = new Map()

const resolveToken = async (chainId, preferredSymbols) => {
  const symbols = preferredSymbols.map((symbol) => symbol.toUpperCase())
  if (!tokensCache.has(chainId)) {
    const response = await getTokens({ chains: [chainId] })
    tokensCache.set(chainId, response.tokens?.[chainId] ?? [])
  }
  const tokens = tokensCache.get(chainId)
  const match = tokens.find((token) => {
    if (!token.symbol) {
      return false
    }
    const symbol = token.symbol.toUpperCase()
    return symbols.includes(symbol)
  })
  if (!match) {
    throw new Error(
      `Unable to locate token for symbols [${preferredSymbols.join(', ')}] on chainId ${chainId}.`
    )
  }
  return match
}

// Test addresses provided by user
const TEST_ADDRESSES = {
  [ChainId.SOL]: '9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump',
  [ChainId.BAS]: '0xFAC77f01957ed1B3DD1cbEa992199B8f85B6E886',
  [ChainId.ETH]: '0x40e3d1A4B2C47d9AA61261F5606136ef73E28042',
  [ChainId.BSC]: '0x000Ae314E2A2172a039B26378814C252734f556A',
}

const tests = []

const addIfEvm = (chainId, label, fromSymbols, toSymbols, amount, testAddress) => {
  // For execution, we MUST use the address from the private key
  // For dry-run, we can use test addresses
  let address
  if (evmConfigByChain.has(chainId)) {
    try {
      address = getAccount(evmConfigByChain.get(chainId).privateKey).address
    } catch (e) {
      if (process.env.DEBUG_LIFI) {
        console.warn(`Failed to derive address for ${label}:`, e.message)
      }
      return
    }
  } else if (dryRun && testAddress) {
    // For dry-run only, allow using test addresses without private keys
    address = testAddress
  } else {
    if (process.env.DEBUG_LIFI) {
      console.warn(`Skipping ${label}: no address available (chainId: ${chainId}, dryRun: ${dryRun})`)
    }
    return
  }
  
  tests.push({
    label,
    request: {
      fromChainId: chainId,
      toChainId: chainId,
      fromAmount: amount,
    },
    fromSymbols,
    toSymbols,
    fromAddress: address,
    toAddress: address,
  })
}

// Small test amounts (in token's smallest unit)
// USDC: 1 USDC = 1000000 (6 decimals)
// WETH: 0.001 WETH = 1000000000000000 (18 decimals)
// BNB: 0.001 BNB = 1000000000000000 (18 decimals)
// SOL: 0.1 SOL = 100000000 (9 decimals)

// Test lower gas cost chains first
addIfEvm(ChainId.BAS, 'Base spot swap (USDC → WETH)', ['USDC', 'USDBC', 'USDC.E'], ['WETH'], '1000000', TEST_ADDRESSES[ChainId.BAS])
addIfEvm(ChainId.BSC, 'BSC spot swap (USDT → WBNB)', ['USDT', 'USDT.E'], ['WBNB', 'BNB'], '1000000000000000', TEST_ADDRESSES[ChainId.BSC])
addIfEvm(ChainId.ETH, 'Ethereum spot swap (USDC → WETH)', ['USDC', 'USDC.E'], ['WETH'], '1000000', TEST_ADDRESSES[ChainId.ETH])

// Solana tests - use adapter address if available, otherwise skip for execution
if (solanaAdapter) {
  const solAddress = solanaAdapter.publicKey?.toString()
  if (!solAddress) {
    console.warn('Skipping Solana tests: failed to get address from adapter')
  } else {
    tests.push({
      label: 'Solana spot swap (USDC → SOL)',
      request: {
        fromChainId: ChainId.SOL,
        toChainId: ChainId.SOL,
        fromAmount: '100000', // 0.1 USDC
      },
      fromSymbols: ['USDC'],
      toSymbols: ['SOL'],
      fromAddress: solAddress,
      toAddress: solAddress,
    })

    // Cross-chain bridge test
    if (evmConfigByChain.has(ChainId.BAS)) {
      try {
        const baseAddress = getAccount(evmConfigByChain.get(ChainId.BAS).privateKey).address
        tests.push({
          label: 'Base → Solana bridge (USDC → USDC)',
          request: {
            fromChainId: ChainId.BAS,
            toChainId: ChainId.SOL,
            fromAmount: '1000000', // 1 USDC
          },
          fromSymbols: ['USDC', 'USDBC'],
          toSymbols: ['USDC'],
          fromAddress: baseAddress,
          toAddress: solAddress,
        })
      } catch (e) {
        if (process.env.DEBUG_LIFI) {
          console.warn('Skipping Base → Solana bridge: failed to get Base address', e.message)
        }
      }
    }
  }
} else if (dryRun && TEST_ADDRESSES[ChainId.SOL]) {
  // For dry-run only, allow using test address
  const solAddress = TEST_ADDRESSES[ChainId.SOL]
  tests.push({
    label: 'Solana spot swap (USDC → SOL) [DRY-RUN]',
    request: {
      fromChainId: ChainId.SOL,
      toChainId: ChainId.SOL,
      fromAmount: '100000',
    },
    fromSymbols: ['USDC'],
    toSymbols: ['SOL'],
    fromAddress: solAddress,
    toAddress: solAddress,
  })
}

const formatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 6,
})

const summarizeRoute = (route) => {
  const steps = route.steps
  const summary = steps
    .map((step, idx) => {
      const tool = step.toolDetails?.name ?? step.tool
      const action = step.action.type ?? 'swap'
      const amount =
        step.estimate?.toAmountMin ??
        step.estimate?.toAmount ??
        step.action.fromAmount
      const tokenSymbol = step.action.fromToken?.symbol ?? 'TOKEN'
      return `  ${idx + 1}. ${tool} (${action}) — amount: ${amount} ${tokenSymbol}`
    })
    .join('\n')
  return summary
}

const main = async () => {
  if (!tests.length) {
    console.warn('No tests configured. Ensure requisite environment variables are set.')
    return
  }

  console.log('Li.Fi sandbox configuration:')
  console.log(`  Integrator: ${integrator}`)
  console.log(`  Dry run: ${dryRun}`)
  console.log(`  Enabled chains: ${tests
    .map((test) => `${test.request.fromChainId}->${test.request.toChainId}`)
    .join(', ')}`)

  for (const test of tests) {
    console.log(`\n=== ${test.label} ===`)

    const fromToken = await resolveToken(test.request.fromChainId, test.fromSymbols)
    const toToken = await resolveToken(test.request.toChainId, test.toSymbols)

    const request = {
      ...test.request,
      fromTokenAddress: fromToken.address,
      toTokenAddress: toToken.address,
      fromAddress: test.fromAddress,
      toAddress: test.toAddress,
      options: {
        allowSwitchChain: true,
      },
    }

    console.log('Request payload:')
    console.dir(request, { depth: 4 })

    const { routes, unavailableRoutes } = await getRoutes(request)

    if (!routes?.length) {
      console.warn('No routes available.', unavailableRoutes)
      continue
    }

    const [route] = routes
    console.log('Route summary:')
    console.log(summarizeRoute(route))
    console.log(
      `  Estimated output: ${route.toAmountMin ?? route.toAmount} ${toToken.symbol} (~$${formatter.format(
        Number(route.toAmountUSD ?? 0)
      )})`
    )

    if (dryRun) {
      continue
    }

    console.log('Executing route...')
    try {
      const executedRoute = await executeRoute(route, {
        executeInBackground: false,
        switchChainHook: async (targetChainId) => getWalletClient(targetChainId),
      })

      for (const step of executedRoute.steps) {
        const status = step.execution?.status ?? 'UNKNOWN'
        const process = step.execution?.process?.slice(-1)[0]
        const txHash = process?.txHash
        const txLink = process?.txLink
        console.log(
          `  Step ${step.id}: status=${status}${txHash ? ` txHash=${txHash}` : ''}${txLink ? `\n    ${txLink}` : ''}`
        )
      }

      const finalStatus = executedRoute.steps.every(s => s.execution?.status === 'DONE')
        ? 'SUCCESS'
        : 'PARTIAL'
      console.log(`Route execution: ${finalStatus}`)
    } catch (error) {
      console.error(`  Execution failed: ${error.message}`)
      if (error.cause?.details) {
        console.error(`  Details: ${error.cause.details}`)
      }
      // Continue to next test
    }
  }
}

main().catch((error) => {
  console.error('Li.Fi sandbox run failed:', error)
  process.exitCode = 1
})

