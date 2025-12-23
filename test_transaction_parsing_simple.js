// Simplified test: Show how transaction parsing works
// Can work with any Solana transaction hash

const { Connection, PublicKey } = require('@solana/web3.js');

const KEY_TOKEN = '3nB5Ucpmcpruez9rgfEQNdd2eC9Nnj1VrDuheLQ3pump';

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
        const decimals = postEntry.uiTokenAmount?.decimals ?? postEntry.decimals ?? 9;
        const postRaw = BigInt(postEntry.uiTokenAmount?.amount ?? postEntry.amount ?? '0');
        
        console.log(`\nPost entry:`);
        console.log(`  Account index: ${postEntry.accountIndex}`);
        console.log(`  Owner: ${postOwner}`);
        console.log(`  Amount (raw): ${postRaw.toString()}`);
        console.log(`  Decimals: ${decimals}`);
        console.log(`  UI Amount: ${postEntry.uiTokenAmount?.uiAmount || 'N/A'}`);
        
        if (owner && postOwner !== owner) {
            console.log(`  ⏭️  Skipping - owner mismatch`);
            continue;
        }
        
        const preEntry = findMatchingEntry(preBalances, postEntry.accountIndex);
        const preRaw = preEntry ? BigInt(preEntry.uiTokenAmount?.amount ?? preEntry.amount ?? '0') : 0n;
        const rawDelta = postRaw - preRaw;
        
        console.log(`  Pre amount (raw): ${preRaw.toString()}`);
        console.log(`  Post amount (raw): ${postRaw.toString()}`);
        console.log(`  Delta (raw): ${rawDelta.toString()}`);
        
        if (rawDelta !== 0n) {
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
    const txHash = process.argv[2];
    
    if (!txHash) {
        console.error('❌ Please provide transaction hash');
        console.error('Usage: node test_transaction_parsing_simple.js <tx_hash>');
        console.error('\nExample:');
        console.error('  node test_transaction_parsing_simple.js JZwa5cNq...');
        process.exit(1);
    }
    
    const RPC_URL = process.env.SOLANA_RPC_URL || process.env.HELIUS_API_KEY ? 
        `https://mainnet.helius-rpc.com/?api-key=${process.env.HELIUS_API_KEY}` :
        'https://api.mainnet-beta.solana.com';
    const connection = new Connection(RPC_URL);
    
    console.log('\n=== Testing Transaction Parsing ===');
    console.log(`Transaction: ${txHash}`);
    console.log(`Token: ${KEY_TOKEN}`);
    console.log(`RPC: ${RPC_URL}\n`);
    
    try {
        console.log('Fetching parsed transaction...');
        let parsedTx = null;
        
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
            return { success: false, error: 'Transaction not found' };
        }
        
        console.log('\n=== Transaction Info ===');
        console.log(`Slot: ${parsedTx.slot}`);
        console.log(`Block time: ${parsedTx.blockTime ? new Date(parsedTx.blockTime * 1000).toISOString() : 'N/A'}`);
        console.log(`Success: ${parsedTx.meta?.err ? 'NO' : 'YES'}`);
        if (parsedTx.meta?.err) {
            console.log(`Error: ${JSON.stringify(parsedTx.meta.err)}`);
        }
        
        // Try without wallet filter first (will find any token delta)
        const delta = deriveSolanaTokenDelta(parsedTx, KEY_TOKEN, null);
        
        if (delta) {
            console.log('\n✅ SUCCESS - Token Delta Found');
            console.log(`Amount received: ${delta.amount.toFixed(6)} tokens`);
            console.log(`Raw amount: ${delta.rawAmount}`);
            console.log(`Decimals used: ${delta.decimals}`);
            
            // Compare with what we logged
            console.log('\n=== Comparison ===');
            console.log(`Logged amount (from quote): 14.898822 tokens`);
            console.log(`Actual amount (from tx): ${delta.amount.toFixed(6)} tokens`);
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
            console.log('\n⚠️  No token delta found for KEY token');
            console.log('   This might mean:');
            console.log('   - Transaction doesn\'t involve KEY token');
            console.log('   - Token mint address is different');
            
            return {
                success: false,
                error: 'No token delta found'
            };
        }
        
    } catch (error) {
        console.error('\n❌ ERROR');
        console.error(`Error message: ${error.message}`);
        console.error(`Error type: ${error.constructor.name}`);
        
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

