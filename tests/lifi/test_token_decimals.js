// Test 1: Check if we can get token decimals for KEY token
// This tests the get_token_decimals() function in isolation

const { Connection, PublicKey } = require('@solana/web3.js');
const { getMint } = require('@solana/spl-token');

async function testTokenDecimals() {
    const KEY_TOKEN = '3nB5Ucpmcpruez9rgfEQNdd2eC9Nnj1VrDuheLQ3pump';
    
    // Use the same RPC as our code
    const RPC_URL = process.env.SOLANA_RPC_URL || 'https://api.mainnet-beta.solana.com';
    const connection = new Connection(RPC_URL);
    
    console.log('\n=== Testing Token Decimals ===');
    console.log(`Token: ${KEY_TOKEN}`);
    console.log(`RPC: ${RPC_URL}\n`);
    
    try {
        const mintAddress = new PublicKey(KEY_TOKEN);
        console.log('Querying mint account...');
        
        // Try standard SPL token first
        let decimals = null;
        let mintInfo = null;
        
        try {
            mintInfo = await getMint(connection, mintAddress);
            decimals = mintInfo.decimals;
            console.log('✅ Standard SPL Token');
        } catch (splError) {
            console.log('⚠️  Not standard SPL token, trying Token-2022...');
            console.log(`   Error: ${splError.constructor.name}`);
            
            // Try getting account info directly (works for Token-2022)
            const accountInfo = await connection.getAccountInfo(mintAddress);
            if (accountInfo) {
                console.log('✅ Account found');
                console.log(`   Owner: ${accountInfo.owner.toString()}`);
                console.log(`   Data length: ${accountInfo.data.length}`);
                
                // Mint account structure: decimals are at offset 44
                // For Token-2022, structure is similar
                if (accountInfo.data.length >= 45) {
                    decimals = accountInfo.data.readUInt8(44);
                    console.log(`   Decimals from raw data: ${decimals}`);
                } else {
                    throw new Error('Account data too short');
                }
            } else {
                throw new Error('Account does not exist');
            }
        }
        
        if (decimals === null) {
            throw new Error('Could not determine decimals');
        }
        
        console.log(`\n✅ SUCCESS - Decimals: ${decimals}`);
        if (mintInfo) {
            console.log(`Supply: ${mintInfo.supply.toString()}`);
            console.log(`Mint Authority: ${mintInfo.mintAuthority?.toString() || 'None'}`);
            console.log(`Freeze Authority: ${mintInfo.freezeAuthority?.toString() || 'None'}`);
        }
        
        // Test conversion
        const rawAmount = 14898822091; // From Jupiter
        const tokens_correct = rawAmount / (10 ** decimals);
        const tokens_wrong = rawAmount / (10 ** 9); // What we used (wrong)
        
        console.log('\n=== Conversion Test ===');
        console.log(`Raw amount: ${rawAmount}`);
        console.log(`Correct (${decimals} decimals): ${tokens_correct.toFixed(6)} tokens`);
        console.log(`Wrong (9 decimals): ${tokens_wrong.toFixed(6)} tokens`);
        console.log(`Wallet shows: 14897 tokens`);
        console.log(`Difference (correct): ${Math.abs(tokens_correct - 14897).toFixed(6)}`);
        console.log(`Difference (wrong): ${Math.abs(tokens_wrong - 14897).toFixed(6)}`);
        
        return {
            success: true,
            decimals: decimals,
            is_token2022: !mintInfo
        };
        
    } catch (error) {
        console.error('❌ ERROR');
        console.error(`Error message: ${error.message}`);
        console.error(`Error type: ${error.constructor.name}`);
        
        // Check if it's the same error handling as our code
        if (error.message.includes('could not find account') || 
            error.message.includes('Account does not exist') ||
            error.message === '') {
            console.log('\n⚠️  This would default to 9 decimals in our code');
        }
        
        return {
            success: false,
            error: error.message
        };
    }
}

testTokenDecimals()
    .then(result => {
        console.log('\n=== Result ===');
        console.log(JSON.stringify(result, null, 2));
        process.exit(result.success ? 0 : 1);
    })
    .catch(error => {
        console.error('Fatal error:', error);
        process.exit(1);
    });

