// Test: Show how we should use the transaction hash we ALREADY HAVE
// After executing a swap, we get a transaction hash - we should use it!

const { Connection, PublicKey } = require('@solana/web3.js');

const KEY_TOKEN = '3nB5Ucpmcpruez9rgfEQNdd2eC9Nnj1VrDuheLQ3pump';

// This is what we get from execute_jupiter_swap() - we ALREADY HAVE THIS!
// const swapResult = {
//     success: true,
//     signature: "JZwa5cNq...",  // <-- WE HAVE THIS!
//     inputAmount: "4470000",
//     outputAmount: "14898822091",  // <-- This is from QUOTE, not actual!
//     priceImpact: "0"
// };

async function parseTransactionForActualAmount(txHash, tokenMint, walletAddress) {
    const RPC_URL = process.env.SOLANA_RPC_URL || process.env.HELIUS_API_KEY ? 
        `https://mainnet.helius-rpc.com/?api-key=${process.env.HELIUS_API_KEY}` :
        'https://api.mainnet-beta.solana.com';
    const connection = new Connection(RPC_URL);
    
    console.log(`\n=== Parsing Transaction for Actual Amount ===`);
    console.log(`TX Hash: ${txHash}`);
    console.log(`Token: ${tokenMint}`);
    console.log(`Wallet: ${walletAddress || 'any'}\n`);
    
    // Wait for transaction to be finalized
    let parsedTx = null;
    for (let attempt = 0; attempt < 30; attempt++) {
        parsedTx = await connection.getParsedTransaction(txHash, {
            commitment: 'finalized',
            maxSupportedTransactionVersion: 0,
        });
        
        if (parsedTx) {
            break;
        }
        
        if (attempt < 29) {
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
    }
    
    if (!parsedTx) {
        throw new Error('Transaction not found');
    }
    
    // Parse token balances
    const meta = parsedTx.meta;
    const postBalances = meta.postTokenBalances || [];
    const preBalances = meta.preTokenBalances || [];
    
    for (const postEntry of postBalances) {
        if (postEntry.mint !== tokenMint) {
            continue;
        }
        
        // Get owner from transaction
        const transaction = parsedTx.transaction;
        let postOwner = postEntry.owner;
        if (!postOwner && transaction?.message?.accountKeys) {
            const accountKey = transaction.message.accountKeys[postEntry.accountIndex];
            if (accountKey && typeof accountKey === 'object' && accountKey.pubkey) {
                postOwner = accountKey.pubkey.toString();
            }
        }
        
        // Filter by wallet if provided
        if (walletAddress && postOwner !== walletAddress) {
            continue;
        }
        
        // Find pre-balance
        const preEntry = preBalances.find(
            e => e.accountIndex === postEntry.accountIndex && e.mint === tokenMint
        );
        
        const postRaw = BigInt(postEntry.uiTokenAmount?.amount ?? postEntry.amount ?? '0');
        const preRaw = preEntry ? BigInt(preEntry.uiTokenAmount?.amount ?? preEntry.amount ?? '0') : 0n;
        const rawDelta = postRaw - preRaw;
        
        if (rawDelta !== 0n) {
            // Get decimals from transaction metadata (more reliable than querying mint)
            const decimals = postEntry.uiTokenAmount?.decimals ?? postEntry.decimals ?? 9;
            const amount = Number(rawDelta) / (10 ** decimals);
            
            return {
                amount,
                rawAmount: rawDelta.toString(),
                decimals,
                owner: postOwner
            };
        }
    }
    
    return null;
}

// Simulate what should happen in our code:
async function demonstrateFlow() {
    console.log('=== How It Should Work ===\n');
    
    console.log('1. Execute swap via Jupiter');
    console.log('   → Get transaction hash: "signature" from result');
    console.log('   → Get quote amount: "outputAmount" from result (ESTIMATE)');
    console.log('');
    
    console.log('2. Parse transaction using hash we already have');
    console.log('   → Get ACTUAL amount received');
    console.log('   → Get ACTUAL decimals from transaction');
    console.log('');
    
    console.log('3. Use actual amount (not quote)');
    console.log('   → Update position with actual amount');
    console.log('   → This matches what\'s in wallet');
    console.log('');
    
    // If we have a transaction hash, test it
    const txHash = process.argv[2];
    if (txHash && txHash.length > 20) {
        console.log('=== Testing with provided hash ===');
        try {
            const walletAddress = process.argv[3]; // Optional
            const result = await parseTransactionForActualAmount(txHash, KEY_TOKEN, walletAddress);
            
            if (result) {
                console.log('\n✅ SUCCESS');
                console.log(`Actual amount: ${result.amount.toFixed(6)} tokens`);
                console.log(`Decimals: ${result.decimals}`);
                console.log(`Raw amount: ${result.rawAmount}`);
                console.log(`Owner: ${result.owner}`);
                
                // Compare with quote
                const quoteAmount = 14898822091; // From Jupiter quote
                const quoteWith6Dec = quoteAmount / (10 ** 6);
                const quoteWith9Dec = quoteAmount / (10 ** 9);
                
                console.log('\n=== Comparison ===');
                console.log(`Quote (6 dec): ${quoteWith6Dec.toFixed(6)} tokens`);
                console.log(`Quote (9 dec): ${quoteWith9Dec.toFixed(6)} tokens`);
                console.log(`Actual (from tx): ${result.amount.toFixed(6)} tokens`);
                console.log(`Difference: ${Math.abs(result.amount - quoteWith6Dec).toFixed(6)} tokens`);
            } else {
                console.log('❌ No token delta found');
            }
        } catch (e) {
            console.error('Error:', e.message);
        }
    } else {
        console.log('=== To test with real transaction ===');
        console.log('Usage: node test_transaction_parsing_integrated.js <tx_hash> [wallet_address]');
        console.log('');
        console.log('The key point: We ALREADY HAVE the tx_hash from swap execution!');
        console.log('We should use it immediately after swap to get actual amount.');
    }
}

demonstrateFlow()
    .then(() => process.exit(0))
    .catch(e => {
        console.error('Fatal error:', e);
        process.exit(1);
    });

