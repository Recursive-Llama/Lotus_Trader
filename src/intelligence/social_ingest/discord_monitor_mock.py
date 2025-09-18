#!/usr/bin/env python3
"""
Mock Discord Monitor Script for Testing

This script simulates Discord monitoring by returning mock token data.
Use this for testing the integration while we fix the Discord token issue.
"""

import json
import random
from datetime import datetime, timezone

def generate_mock_token():
    """Generate mock token data for testing"""
    tokens = [
        {
            'ticker': 'PEPE',
            'contract': 'So11111111111111111111111111111111111111112',
            'market_cap': random.randint(100000, 5000000),
            'liquidity': random.randint(50000, 500000),
            'holders': random.randint(100, 5000),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'raw_content': '🚀 NEW TOKEN ALERT! PEPE - Contract: So11111111111111111111111111111111111111112 - MC: 2.5M - Liq: 500K'
        },
        {
            'ticker': 'DOGE',
            'contract': 'So11111111111111111111111111111111111111113',
            'market_cap': random.randint(500000, 10000000),
            'liquidity': random.randint(100000, 1000000),
            'holders': random.randint(500, 10000),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'raw_content': '💎 GEM ALERT! DOGE - Contract: So11111111111111111111111111111111111111113 - MC: 5.2M - Liq: 800K'
        },
        {
            'ticker': 'SHIB',
            'contract': 'So11111111111111111111111111111111111111114',
            'market_cap': random.randint(200000, 3000000),
            'liquidity': random.randint(75000, 750000),
            'holders': random.randint(200, 3000),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'raw_content': '🔥 HOT PICK! SHIB - Contract: So11111111111111111111111111111111111111114 - MC: 1.8M - Liq: 300K'
        }
    ]
    
    return random.choice(tokens)

def main():
    """Main function - randomly returns new token data or empty"""
    # 30% chance of returning new token data
    if random.random() < 0.3:
        token_data = generate_mock_token()
        
        output = {
            'status': 'new_tokens_found',
            'count': 1,
            'tokens': [token_data],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        print(json.dumps(output, indent=2))
    else:
        # Return empty output for no changes
        print("")

if __name__ == "__main__":
    main()
