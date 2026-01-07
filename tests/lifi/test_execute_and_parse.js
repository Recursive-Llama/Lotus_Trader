// Execute a small swap → Get hash → Parse immediately → Show actual vs quote

const { Connection, Keypair, VersionedTransaction } = require('@solana/web3.js');
const bs58 = require('bs58');
const axios = require('axios');

// Load environment - try multiple methods
let envLoaded = false;
try {
    require('dotenv').config();
    envLoaded = true;
} catch (e) {
    // dotenv not available, try reading .env manually
    try {
        const fs = require('fs');
        const envContent = fs.readFileSync('.env', 'utf8');
        envContent.split('\n').forEach(line => {
            const match = line.match(/^([^#=]+)=(.*)$/);
            if (match) {
                const key = match[1].trim();
                const value = match[2].trim().replace(/^["']|["']$/g, '');
                if (!process.env[key]) {
                    process.env[key] = value;
                }
            }
        });
        envLoaded = true;
    } catch (e2) {
        // .env file not found or can't read
    }
}

const KEY_TOKEN = '3nB5Ucpmcpruez9rgfEQNdd2eC9Nnj1VrDuheLQ3pump';
const USDC_MINT = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v';

async function parseTransaction(connection, txHash, tokenMint, walletAddress) {
    let parsedTx = null;
    for (let attempt = 0; attempt < 30; attempt++) {
        parsedTx = await connection.getParsedTransaction(txHash, {
            commitment: 'finalized',
            maxSupportedTransactionVersion: 0,
        });
        if (parsedTx) break;
        if (attempt < 29) await new Promise(resolve => setTimeout(resolve, 1000));
    }
    
    if (!parsedTx) throw new Error('Transaction not found');
    
    const meta = parsedTx.meta;
    const postBalances = meta.postTokenBalances || [];
    const preBalances = meta.preTokenBalances || [];
    const transaction = parsedTx.transaction;
    
    for (const postEntry of postBalances) {
        if (postEntry.mint !== tokenMint) continue;
        
        let postOwner = postEntry.owner;
        if (!postOwner && transaction?.message?.accountKeys) {
            const accountKey = transaction.message.accountKeys[postEntry.accountIndex];
            if (accountKey?.pubkey) postOwner = accountKey.pubkey.toString();
        }
        
        if (walletAddress && postOwner !== walletAddress) continue;
        
        const preEntry = preBalances.find(
            e => e.accountIndex === postEntry.accountIndex && e.mint === tokenMint
        );
        
        const postRaw = BigInt(postEntry.uiTokenAmount?.amount ?? postEntry.amount ?? '0');
        const preRaw = preEntry ? BigInt(preEntry.uiTokenAmount?.amount ?? preEntry.amount ?? '0') : 0n;
        const rawDelta = postRaw - preRaw;
        
        if (rawDelta !== 0n) {
            const decimals = postEntry.uiTokenAmount?.decimals ?? postEntry.decimals ?? 9;
            const amount = Number(rawDelta) / (10 ** decimals);
            return { amount, rawAmount: rawDelta.toString(), decimals, owner: postOwner };
        }
    }
    return null;
}

async function test() {
    const privateKey = process.env.SOL_WALLET_PRIVATE_KEY;
    if (!privateKey) {
        console.error('❌ SOL_WALLET_PRIVATE_KEY not found');
        process.exit(1);
    }
    
    const heliusKey = process.env.HELIUS_API_KEY;
    const rpcUrl = heliusKey ? 
        `https://mainnet.helius-rpc.com/?api-key=${heliusKey}` :
        (process.env.SOLANA_RPC_URL || 'https://api.mainnet-beta.solana.com');
    
    const connection = new Connection(rpcUrl);
    const keyBytes = bs58.decode(privateKey);
    const wallet = Keypair.fromSecretKey(keyBytes);
    
    console.log('=== Execute Swap and Parse Transaction ===\n');
    console.log(`Wallet: ${wallet.publicKey.toString()}`);
    console.log(`RPC: ${rpcUrl}\n`);
    
    // Execute a small swap (0.1 USDC = 100,000 raw)
    const usdcAmount = 100000; // 0.1 USDC
    console.log(`Executing swap: ${usdcAmount / 1_000_000} USDC → KEY token...\n`);
    
    try {
        // Get quote
        const quoteResponse = await axios.get('https://lite-api.jup.ag/swap/v1/quote', {
            params: {
                inputMint: USDC_MINT,
                outputMint: KEY_TOKEN,
                amount: usdcAmount.toString(),
                slippageBps: '50',
                onlyDirectRoutes: 'false',
                asLegacyTransaction: 'false'
            }
        });
        
        if (quoteResponse.data.error) {
            throw new Error(quoteResponse.data.error);
        }
        
        const quote = quoteResponse.data;
        const quoteOutputRaw = quote.outAmount;
        console.log(`Quote output (raw): ${quoteOutputRaw}`);
        
        // Execute swap
        const swapRequest = {
            quoteResponse: quote,
            userPublicKey: wallet.publicKey.toString(),
            wrapAndUnwrapSol: true,
            useSharedAccounts: false,
            prioritizationFeeLamports: 'auto',
            asLegacyTransaction: false
        };
        
        const swapResponse = await axios.post('https://lite-api.jup.ag/swap/v1/swap', swapRequest);
        
        if (swapResponse.data.error) {
            throw new Error(swapResponse.data.error);
        }
        
        // Deserialize and sign
        const swapTransactionBuf = Buffer.from(swapResponse.data.swapTransaction, 'base64');
        const transaction = VersionedTransaction.deserialize(swapTransactionBuf);
        transaction.sign([wallet]);
        
        // Send transaction
        const signature = await connection.sendTransaction(transaction, {
            skipPreflight: false,
            preflightCommitment: 'processed'
        });
        
        console.log(`✅ Transaction sent: ${signature}`);
        
        // Wait for confirmation
        const confirmation = await connection.confirmTransaction(signature, 'confirmed');
        if (confirmation.value.err) {
            throw new Error(`Transaction failed: ${JSON.stringify(confirmation.value.err)}`);
        }
        
        console.log(`✅ Transaction confirmed\n`);
        
        // NOW PARSE IT IMMEDIATELY (this is what we should do in production!)
        console.log('=== Parsing Transaction for Actual Amount ===\n');
        const actual = await parseTransaction(connection, signature, KEY_TOKEN, wallet.publicKey.toString());
        
        if (actual) {
            console.log('✅ SUCCESS - Got Actual Amount from Transaction');
            console.log(`Actual amount: ${actual.amount.toFixed(6)} tokens`);
            console.log(`Decimals: ${actual.decimals}`);
            console.log(`Raw amount: ${actual.rawAmount}\n`);
            
            // Compare with quote
            const quoteWith6Dec = parseInt(quoteOutputRaw) / (10 ** 6);
            const quoteWith9Dec = parseInt(quoteOutputRaw) / (10 ** 9);
            
            console.log('=== Quote vs Actual ===');
            console.log(`Quote (6 dec): ${quoteWith6Dec.toFixed(6)} tokens`);
            console.log(`Quote (9 dec): ${quoteWith9Dec.toFixed(6)} tokens`);
            console.log(`Actual (from tx): ${actual.amount.toFixed(6)} tokens`);
            console.log(`Difference (6dec): ${Math.abs(actual.amount - quoteWith6Dec).toFixed(6)} tokens`);
            console.log(`Difference (9dec): ${Math.abs(actual.amount - quoteWith9Dec).toFixed(6)} tokens`);
            console.log(`\n✅ This proves: We should use actual amount, not quote!`);
        } else {
            console.log('❌ No token delta found in transaction');
        }
        
    } catch (error) {
        console.error('❌ Error:', error.message);
        if (error.response) {
            console.error('Response:', error.response.data);
        }
        process.exit(1);
    }
}

test();

