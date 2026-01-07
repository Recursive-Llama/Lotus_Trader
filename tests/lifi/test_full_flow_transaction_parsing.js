// Full flow test: Execute swap → Get hash → Parse transaction → Get actual amount
// This tests the complete flow as it should work in production

const { Connection, PublicKey, Keypair, VersionedTransaction } = require('@solana/web3.js');
const bs58 = require('bs58');
const axios = require('axios');

// Load environment
try {
    require('dotenv').config();
} catch (e) {
    // dotenv not available
}

const KEY_TOKEN = '3nB5Ucpmcpruez9rgfEQNdd2eC9Nnj1VrDuheLQ3pump';
const USDC_MINT = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v';

async function parseTransactionForActualAmount(connection, txHash, tokenMint, walletAddress) {
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
    const transaction = parsedTx.transaction;
    
    for (const postEntry of postBalances) {
        if (postEntry.mint !== tokenMint) {
            continue;
        }
        
        // Get owner
        let postOwner = postEntry.owner;
        if (!postOwner && transaction?.message?.accountKeys) {
            const accountKey = transaction.message.accountKeys[postEntry.accountIndex];
            if (accountKey && typeof accountKey === 'object' && accountKey.pubkey) {
                postOwner = accountKey.pubkey.toString();
            }
        }
        
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

async function testFullFlow() {
    console.log('\n=== Full Flow Test: Swap → Parse Transaction ===\n');
    
    // Setup
    const privateKey = process.env.SOL_WALLET_PRIVATE_KEY;
    if (!privateKey) {
        console.error('❌ SOL_WALLET_PRIVATE_KEY not found');
        console.error('   Set it in environment or .env file');
        process.exit(1);
    }
    
    const heliusKey = process.env.HELIUS_API_KEY;
    const rpcUrl = heliusKey ? 
        `https://mainnet.helius-rpc.com/?api-key=${heliusKey}` :
        (process.env.SOLANA_RPC_URL || 'https://api.mainnet-beta.solana.com');
    
    const connection = new Connection(rpcUrl);
    const keyBytes = bs58.decode(privateKey);
    const wallet = Keypair.fromSecretKey(keyBytes);
    
    console.log(`Wallet: ${wallet.publicKey.toString()}`);
    console.log(`RPC: ${rpcUrl}\n`);
    
    // Option 1: Use existing transaction hash (if provided)
    const existingTxHash = process.argv[2];
    if (existingTxHash && existingTxHash.length > 20) {
        console.log('=== Using Provided Transaction Hash ===');
        console.log(`TX: ${existingTxHash}\n`);
        
        try {
            const result = await parseTransactionForActualAmount(
                connection, 
                existingTxHash, 
                KEY_TOKEN, 
                wallet.publicKey.toString()
            );
            
            if (result) {
                console.log('✅ SUCCESS - Parsed Transaction');
                console.log(`Actual amount: ${result.amount.toFixed(6)} tokens`);
                console.log(`Decimals: ${result.decimals}`);
                console.log(`Raw amount: ${result.rawAmount}`);
                console.log(`Owner: ${result.owner}`);
                
                // Compare with quote
                const quoteAmount = 14898822091; // Example from logs
                const quoteWith6Dec = quoteAmount / (10 ** 6);
                const quoteWith9Dec = quoteAmount / (10 ** 9);
                
                console.log('\n=== Comparison ===');
                console.log(`Quote (6 dec): ${quoteWith6Dec.toFixed(6)} tokens`);
                console.log(`Quote (9 dec): ${quoteWith9Dec.toFixed(6)} tokens`);
                console.log(`Actual (from tx): ${result.amount.toFixed(6)} tokens`);
                console.log(`Difference (6dec): ${Math.abs(result.amount - quoteWith6Dec).toFixed(6)} tokens`);
                console.log(`Difference (9dec): ${Math.abs(result.amount - quoteWith9Dec).toFixed(6)} tokens`);
            } else {
                console.log('❌ No token delta found');
            }
        } catch (e) {
            console.error('Error:', e.message);
        }
        return;
    }
    
    // Option 2: Execute a small swap and parse it
    console.log('=== Option 2: Execute Swap and Parse ===');
    console.log('This would execute a real swap - skipping for safety');
    console.log('To test with existing transaction:');
    console.log('  node test_full_flow_transaction_parsing.js <tx_hash>');
    console.log('');
    console.log('Or find a recent transaction hash from logs/explorer');
}

testFullFlow()
    .then(() => process.exit(0))
    .catch(e => {
        console.error('Fatal error:', e);
        process.exit(1);
    });

