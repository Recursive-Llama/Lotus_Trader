// Test 2: Parse actual transaction to get real amount received
// This tests if we can get actual token amount from transaction (like Li.Fi does)

// Load environment variables
try {
    require('dotenv').config();
} catch (e) {
    // dotenv not available, assume env vars are set
}

const { Connection, PublicKey } = require('@solana/web3.js');
const bs58 = require('bs58');

// Transaction hash from the buy
const TX_HASH = 'JZwa5cNq...'; // We'll need the full hash
const KEY_TOKEN = '3nB5Ucpmcpruez9rgfEQNdd2eC9Nnj1VrDuheLQ3pump';
const WALLET_ADDRESS = process.env.SOLANA_WALLET_ADDRESS; // Need wallet address

function deriveSolanaTokenDelta(parsedTx, mint, owner) {
    const meta = parsedTx?.meta;
    if (!meta) {
        return null;
    }
    
    const postBalances = meta.postTokenBalances || [];
    const preBalances = meta.preTokenBalances || [];
    const transaction = parsedTx?.transaction;
    
    const normalizeOwner = (entry) => {
        if (entry?.owner) {
            return entry.owner;
        }
        // Get owner from transaction accounts
        if (transaction?.message?.accountKeys) {
            const accountKey = transaction.message.accountKeys[entry.accountIndex];
            if (accountKey && typeof accountKey === 'object' && accountKey.pubkey) {
                return accountKey.pubkey.toString();
            }
            if (typeof accountKey === 'string') {
                return accountKey;
            }
        }
        return null;
    };
    
    const findMatchingEntry = (balances, accountIndex) => {
        return balances.find((entry) => entry.accountIndex === accountIndex && entry.mint === mint);
    };
    
    console.log('\n=== Token Balance Analysis ===');
    console.log(`Mint: ${mint}`);
    console.log(`Owner filter: ${owner || 'none'}`);
    console.log(`Pre balances: ${preBalances.length}`);
    console.log(`Post balances: ${postBalances.length}`);
    
    for (const postEntry of postBalances) {
        if (postEntry.mint !== mint) {
            continue;
        }
        
        const postOwner = normalizeOwner(postEntry);
        console.log(`\nPost entry:`);
        console.log(`  Account index: ${postEntry.accountIndex}`);
        console.log(`  Owner: ${postOwner}`);
        console.log(`  Mint: ${postEntry.mint}`);
        console.log(`  Amount (raw): ${postEntry.uiTokenAmount?.amount || postEntry.amount || '0'}`);
        console.log(`  Decimals: ${postEntry.uiTokenAmount?.decimals || postEntry.decimals || 'unknown'}`);
        console.log(`  UI Amount: ${postEntry.uiTokenAmount?.uiAmount || 'N/A'}`);
        
        if (owner && postOwner !== owner) {
            console.log(`  ⏭️  Skipping - owner mismatch`);
            continue;
        }
        
        const preEntry = findMatchingEntry(preBalances, postEntry.accountIndex);
        const postRaw = BigInt(postEntry.uiTokenAmount?.amount ?? postEntry.amount ?? '0');
        const preRaw = preEntry ? BigInt(preEntry.uiTokenAmount?.amount ?? preEntry.amount ?? '0') : 0n;
        const rawDelta = postRaw - preRaw;
        
        console.log(`  Pre amount (raw): ${preRaw.toString()}`);
        console.log(`  Post amount (raw): ${postRaw.toString()}`);
        console.log(`  Delta (raw): ${rawDelta.toString()}`);
        
        if (owner && postOwner === owner && rawDelta !== 0n) {
            const decimals = postEntry.uiTokenAmount?.decimals ?? postEntry.decimals ?? 9;
            const amount = Number(rawDelta) / (10 ** decimals);
            console.log(`  ✅ Delta: ${amount.toFixed(6)} tokens (using ${decimals} decimals)`);
            return {
                amount,
                rawAmount: rawDelta.toString(),
                decimals,
            };
        }
    }
    
    return null;
}

async function testTransactionParsing() {
    let txHash = process.argv[2] || TX_HASH;
    let walletAddress = process.argv[3] || WALLET_ADDRESS;
    
    // Try to derive wallet address from private key if not provided
    if (!walletAddress) {
        const privateKey = process.env.SOL_WALLET_PRIVATE_KEY;
        if (privateKey) {
            try {
                const { Keypair } = require('@solana/web3.js');
                const bs58 = require('bs58');
                const keyBytes = bs58.decode(privateKey);
                const wallet = Keypair.fromSecretKey(keyBytes);
                walletAddress = wallet.publicKey.toString();
                console.log(`✅ Derived wallet address from private key: ${walletAddress}`);
            } catch (e) {
                console.log(`⚠️  Could not derive wallet address: ${e.message}`);
            }
        }
    }
    
    // If txHash is partial, try to find it
    if (!txHash || txHash === 'JZwa5cNq...' || txHash.length < 64) {
        console.log('⚠️  Transaction hash not provided or incomplete');
        console.log('   Trying to find recent transactions for wallet...');
        
        if (!walletAddress) {
            console.error('❌ Need either transaction hash or wallet address');
            console.error('Usage: node test_transaction_parsing.js [tx_hash] [wallet_address]');
            process.exit(1);
        }
        
        // Try to find recent transactions
        const RPC_URL = process.env.SOLANA_RPC_URL || 'https://api.mainnet-beta.solana.com';
        const connection = new Connection(RPC_URL);
        
        try {
            const pubkey = new PublicKey(walletAddress);
            const signatures = await connection.getSignaturesForAddress(pubkey, { limit: 10 });
            
            if (signatures.length === 0) {
                console.error('❌ No transactions found for wallet');
                process.exit(1);
            }
            
            // Look for transactions involving KEY token
            console.log(`\nFound ${signatures.length} recent transactions`);
            console.log('Looking for KEY token transaction...\n');
            
            for (const sig of signatures) {
                if (sig.signature.startsWith('JZwa5cNq') || !txHash || txHash === 'JZwa5cNq...') {
                    txHash = sig.signature;
                    console.log(`✅ Found matching transaction: ${txHash}`);
                    break;
                }
            }
            
            if (!txHash || txHash === 'JZwa5cNq...') {
                // Use most recent transaction
                txHash = signatures[0].signature;
                console.log(`⚠️  Using most recent transaction: ${txHash}`);
            }
        } catch (e) {
            console.error(`❌ Error finding transactions: ${e.message}`);
            process.exit(1);
        }
    }
    
    const RPC_URL = process.env.SOLANA_RPC_URL || 'https://api.mainnet-beta.solana.com';
    const connection = new Connection(RPC_URL);
    
    console.log('\n=== Testing Transaction Parsing ===');
    console.log(`Transaction: ${txHash}`);
    console.log(`Token: ${KEY_TOKEN}`);
    console.log(`Wallet: ${walletAddress || 'not provided (will try all)'}`);
    console.log(`RPC: ${RPC_URL}\n`);
    
    try {
        console.log('Fetching parsed transaction...');
        let parsedTx = null;
        
        // Try multiple times (transaction might not be finalized yet)
        for (let attempt = 0; attempt < 10; attempt++) {
            parsedTx = await connection.getParsedTransaction(txHash, {
                commitment: 'finalized',
                maxSupportedTransactionVersion: 0,
            });
            
            if (parsedTx) {
                console.log(`✅ Transaction found (attempt ${attempt + 1})`);
                break;
            }
            
            if (attempt < 9) {
                console.log(`⏳ Transaction not found, retrying... (${attempt + 1}/10)`);
                await new Promise(resolve => setTimeout(resolve, 1000));
            }
        }
        
        if (!parsedTx) {
            console.error('❌ Transaction not found after 10 attempts');
            console.error('   Transaction might not be finalized yet, or hash is incorrect');
            return { success: false, error: 'Transaction not found' };
        }
        
        console.log('\n=== Transaction Info ===');
        console.log(`Slot: ${parsedTx.slot}`);
        console.log(`Block time: ${parsedTx.blockTime ? new Date(parsedTx.blockTime * 1000).toISOString() : 'N/A'}`);
        console.log(`Success: ${parsedTx.meta?.err ? 'NO' : 'YES'}`);
        if (parsedTx.meta?.err) {
            console.log(`Error: ${JSON.stringify(parsedTx.meta.err)}`);
        }
        
        // Get token delta
        const delta = deriveSolanaTokenDelta(parsedTx, KEY_TOKEN, walletAddress);
        
        if (delta) {
            console.log('\n✅ SUCCESS - Token Delta Found');
            console.log(`Amount received: ${delta.amount.toFixed(6)} tokens`);
            console.log(`Raw amount: ${delta.rawAmount}`);
            console.log(`Decimals used: ${delta.decimals}`);
            
            // Compare with what we logged
            console.log('\n=== Comparison ===');
            console.log(`Logged amount: 14.898822 tokens (from quote)`);
            console.log(`Actual amount: ${delta.amount.toFixed(6)} tokens (from transaction)`);
            console.log(`Difference: ${Math.abs(delta.amount - 14.898822).toFixed(6)} tokens`);
            console.log(`Wallet shows: 14897 tokens`);
            console.log(`Difference from wallet: ${Math.abs(delta.amount - 14897).toFixed(6)} tokens`);
            
            return {
                success: true,
                delta: delta,
                logged_amount: 14.898822,
                actual_amount: delta.amount,
                wallet_amount: 14897
            };
        } else {
            console.log('\n⚠️  No token delta found');
            console.log('   This might mean:');
            console.log('   - Wallet address is wrong');
            console.log('   - Token mint is wrong');
            console.log('   - Transaction doesn\'t involve this token');
            
            return {
                success: false,
                error: 'No token delta found'
            };
        }
        
    } catch (error) {
        console.error('\n❌ ERROR');
        console.error(`Error message: ${error.message}`);
        console.error(`Error type: ${error.constructor.name}`);
        if (error.stack) {
            console.error(`Stack: ${error.stack}`);
        }
        
        return {
            success: false,
            error: error.message
        };
    }
}

testTransactionParsing()
    .then(result => {
        console.log('\n=== Final Result ===');
        console.log(JSON.stringify(result, null, 2));
        process.exit(result.success ? 0 : 1);
    })
    .catch(error => {
        console.error('Fatal error:', error);
        process.exit(1);
    });

