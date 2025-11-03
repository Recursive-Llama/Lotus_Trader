const { Connection, Keypair, VersionedTransaction } = require('@solana/web3.js');
const bs58 = require('bs58');
const axios = require('axios');

async function testPumpTransaction() {
    try {
        console.log('🧪 Testing PUMP Transaction Execution');
        console.log('=====================================');
        
        // Load wallet (replace with actual private key)
        const privateKey = 'YOUR_PRIVATE_KEY_HERE';
        const keyBytes = bs58.decode(privateKey);
        const wallet = Keypair.fromSecretKey(keyBytes);
        
        console.log('💰 Wallet address:', wallet.publicKey.toString());
        
        // Get RPC client
        const connection = new Connection('https://mainnet.helius-rpc.com/?api-key=YOUR_API_KEY_HERE');
        
        // PUMP token details
        const pumpMint = 'pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn';
        const solMint = 'So11111111111111111111111111111111111111112';
        const amount = 1000000; // 1 token (6 decimals)
        const slippageBps = 100; // 1% slippage
        
        console.log('🎯 Testing PUMP -> SOL swap');
        console.log('   Amount:', amount, 'raw units');
        console.log('   Slippage:', slippageBps, 'bps');
        
        // Get quote from Jupiter
        console.log('\n📡 Getting quote from Jupiter...');
        const quoteResponse = await axios.get('https://lite-api.jup.ag/swap/v1/quote', {
            params: {
                inputMint: pumpMint,
                outputMint: solMint,
                amount: amount.toString(),
                slippageBps: slippageBps.toString(),
                onlyDirectRoutes: 'false',
                asLegacyTransaction: 'false'
            }
        });
        
        if (!quoteResponse.data || quoteResponse.data.error) {
            throw new Error(quoteResponse.data?.error || 'Invalid quote response');
        }
        
        console.log('✅ Quote successful!');
        console.log('   Input amount:', quoteResponse.data.inAmount);
        console.log('   Output amount:', quoteResponse.data.outAmount);
        console.log('   Price impact:', quoteResponse.data.priceImpactPct + '%');
        
        // Get swap transaction
        console.log('\n🔧 Creating swap transaction...');
        const swapRequest = {
            quoteResponse: quoteResponse.data,
            userPublicKey: wallet.publicKey.toString(),
            wrapAndUnwrapSol: true,
            useSharedAccounts: false,
            prioritizationFeeLamports: 'auto',
            asLegacyTransaction: false
        };
        
        const swapResponse = await axios.post('https://lite-api.jup.ag/swap/v1/swap', swapRequest);
        
        if (!swapResponse.data || swapResponse.data.error) {
            throw new Error(swapResponse.data?.error || 'Invalid swap response');
        }
        
        console.log('✅ Swap transaction created!');
        console.log('   Transaction length:', swapResponse.data.swapTransaction.length);
        
        // Deserialize and sign the transaction
        console.log('\n🔐 Deserializing and signing transaction...');
        const swapTransactionBuf = Buffer.from(swapResponse.data.swapTransaction, 'base64');
        const transaction = VersionedTransaction.deserialize(swapTransactionBuf);
        
        // Sign the transaction
        transaction.sign([wallet]);
        console.log('✅ Transaction signed');
        
        // Test with simulation first
        console.log('\n🧪 Simulating transaction...');
        try {
            const simulation = await connection.simulateTransaction(transaction, {
                commitment: 'processed'
            });
            
            console.log('📊 Simulation result:');
            console.log('   Error:', simulation.value.err);
            console.log('   Logs:', simulation.value.logs);
            console.log('   Compute units consumed:', simulation.value.unitsConsumed);
            
            if (simulation.value.err) {
                console.log('❌ Simulation failed!');
                console.log('   Error details:', JSON.stringify(simulation.value.err, null, 2));
                return;
            }
            
            console.log('✅ Simulation successful!');
            
        } catch (simError) {
            console.log('❌ Simulation error:', simError.message);
            return;
        }
        
        // Try to send the transaction with different options
        console.log('\n📤 Attempting to send transaction...');
        
        try {
            // First try with preflight enabled
            console.log('   Trying with preflight enabled...');
            const signature = await connection.sendTransaction(transaction, {
                skipPreflight: false,
                preflightCommitment: 'processed'
            });
            
            console.log('✅ Transaction sent successfully!');
            console.log('   Signature:', signature);
            
            // Wait for confirmation
            console.log('\n⏳ Waiting for confirmation...');
            const confirmation = await connection.confirmTransaction(signature, 'confirmed');
            
            if (confirmation.value.err) {
                console.log('❌ Transaction failed during confirmation:');
                console.log('   Error:', confirmation.value.err);
            } else {
                console.log('✅ Transaction confirmed successfully!');
            }
            
        } catch (sendError) {
            console.log('❌ Send transaction failed:', sendError.message);
            
            // Try with preflight disabled
            console.log('\n   Trying with preflight disabled...');
            try {
                const signature2 = await connection.sendTransaction(transaction, {
                    skipPreflight: true,
                    preflightCommitment: 'processed'
                });
                
                console.log('✅ Transaction sent with preflight disabled!');
                console.log('   Signature:', signature2);
                
            } catch (sendError2) {
                console.log('❌ Send transaction failed even with preflight disabled:', sendError2.message);
            }
        }
        
    } catch (error) {
        console.log('❌ Error during test:', error.message);
        console.log('   Stack:', error.stack);
    }
}

// Run the test
testPumpTransaction().then(() => {
    console.log('\n🏁 Test completed');
}).catch(error => {
    console.log('❌ Test failed:', error);
});
