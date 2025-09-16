#!/usr/bin/env node

const { Connection, Keypair, VersionedTransaction, LAMPORTS_PER_SOL } = require('@solana/web3.js');
const bs58 = require('bs58');

async function testTransaction() {
    try {
        // Load wallet from environment
        const privateKey = process.env.SOL_WALLET_PRIVATE_KEY;
        if (!privateKey) {
            throw new Error('No SOL_WALLET_PRIVATE_KEY in environment');
        }
        
        // Create wallet from private key
        const keyBytes = bs58.decode(privateKey);
        const wallet = Keypair.fromSecretKey(keyBytes);
        
        console.log(`Wallet loaded: ${wallet.publicKey.toString()}`);
        
        // Get RPC client
        const heliusKey = process.env.HELIUS_API_KEY;
        const rpcUrl = heliusKey 
            ? `https://mainnet.helius-rpc.com/?api-key=${heliusKey}`
            : 'https://api.mainnet-beta.solana.com';
            
        const connection = new Connection(rpcUrl);
        
        // Check balance
        const balance = await connection.getBalance(wallet.publicKey);
        console.log(`Balance: ${balance / LAMPORTS_PER_SOL} SOL`);
        
        if (balance < 1000000) {
            throw new Error('Insufficient balance for test');
        }
        
        // Get recent blockhash
        const { blockhash } = await connection.getLatestBlockhash();
        
        // Create a simple transfer instruction
        const { SystemProgram } = require('@solana/web3.js');
        const transferInstruction = SystemProgram.transfer({
            fromPubkey: wallet.publicKey,
            toPubkey: wallet.publicKey, // Send to ourselves
            lamports: 100000 // 0.0001 SOL
        });
        
        // Create VersionedTransaction directly
        const { TransactionMessage, AddressLookupTableAccount } = require('@solana/web3.js');
        
        const message = new VersionedTransaction(
            new TransactionMessage({
                payerKey: wallet.publicKey,
                recentBlockhash: blockhash,
                instructions: [transferInstruction]
            }).compileToV0Message()
        );
        
        console.log('Message created');
        
        // THE KEY: Sign the transaction (this is what works in JS)
        message.sign([wallet]);
        
        console.log('Transaction signed successfully!');
        
        // Send the transaction
        const signature = await connection.sendTransaction(message, {
            skipPreflight: false,
            preflightCommitment: 'processed'
        });
        
        console.log(`Transaction submitted: ${signature}`);
        
        // Wait for confirmation
        const confirmation = await connection.confirmTransaction(signature, 'confirmed');
        
        if (confirmation.value.err) {
            throw new Error(`Transaction failed: ${confirmation.value.err}`);
        }
        
        console.log('Transaction confirmed successfully!');
        console.log('SUCCESS: JavaScript approach works!');
        
        return {
            success: true,
            signature: signature
        };
        
    } catch (error) {
        console.error('Error:', error.message);
        return {
            success: false,
            error: error.message
        };
    }
}

// Run the test
testTransaction().then(result => {
    console.log('Result:', JSON.stringify(result, null, 2));
}).catch(error => {
    console.error('Fatal error:', error);
    process.exit(1);
});
