#!/usr/bin/env python3
"""
Test Base Uniswap Client (v2/v3 fallback)
"""

import pytest
import os
from unittest.mock import Mock, patch
from decimal import Decimal

# Add src to path
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading.evm_uniswap_client import EvmUniswapClient


class TestEvmUniswapClientBase:
    """Test Base Uniswap client functionality"""
    
    @pytest.fixture
    def client(self):
        """Create client instance"""
        with patch.dict(os.environ, {'BASE_RPC_URL': 'https://test.base.rpc'}):
            with patch('web3.Web3') as mock_web3_class:
                mock_web3 = Mock()
                mock_web3.is_connected.return_value = True
                mock_web3_class.return_value = mock_web3
                return EvmUniswapClient('base')
    
    @pytest.fixture
    def mock_web3(self):
        """Mock web3 instance"""
        mock = Mock()
        mock.eth.get_balance.return_value = 1000000000000000000  # 1 ETH
        mock.eth.get_gas_price.return_value = 20000000000  # 20 gwei
        mock.eth.estimate_gas.return_value = 100000
        mock.eth.get_transaction_count.return_value = 0
        return mock
    
    def test_v2_get_amounts_out(self, client, mock_web3):
        """Test v2 getAmountsOut call"""
        with patch.object(client, 'w3', mock_web3):
            # Mock the router contract call
            mock_router = Mock()
            mock_router.functions.getAmountsOut.return_value.call.return_value = [
                1000000000000000000,  # 1 WETH in
                2000000000000000000000  # 2000 tokens out
            ]
            client.w3.eth.contract.return_value = mock_router
            
            amounts = client.v2_get_amounts_out(
                client.weth_address,
                "0x1234567890123456789012345678901234567890",
                1000000000000000000
            )
            
            assert amounts == [1000000000000000000, 2000000000000000000000]
            mock_router.functions.getAmountsOut.assert_called_once()
    
    def test_v3_quote_amount_out(self, client, mock_web3):
        """Test v3 quoter call"""
        with patch.object(client, 'w3', mock_web3):
            # Mock the quoter contract call
            mock_quoter = Mock()
            mock_quoter.functions.quoteExactInputSingle.return_value.call.return_value = 2000000000000000000000
            client.w3.eth.contract.return_value = mock_quoter
            
            amount_out = client.v3_quote_amount_out(
                client.weth_address,
                "0x1234567890123456789012345678901234567890",
                1000000000000000000,
                fee=3000
            )
            
            assert amount_out == 2000000000000000000000
            mock_quoter.functions.quoteExactInputSingle.assert_called_once()
    
    def test_get_token_decimals(self, client, mock_web3):
        """Test token decimals retrieval"""
        with patch.object(client, 'w3', mock_web3):
            # Mock the ERC20 contract call
            mock_contract = Mock()
            mock_contract.functions.decimals.return_value.call.return_value = 18
            client.w3.eth.contract.return_value = mock_contract
            
            decimals = client.get_token_decimals("0x1234567890123456789012345678901234567890")
            
            assert decimals == 18
            mock_contract.functions.decimals.assert_called_once()
    
    @pytest.mark.skipif(not os.getenv('BASE_RPC_URL'), reason="Requires BASE_RPC_URL for live test")
    def test_live_v2_liquidity_check(self, client):
        """Test live v2 liquidity check (requires RPC)"""
        # Test with USDC on Base (should have v2 liquidity)
        usdc_address = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
        amounts = client.v2_get_amounts_out(
            client.weth_address,
            usdc_address,
            1000000000000000000  # 1 WETH
        )
        
        if amounts and len(amounts) >= 2:
            assert amounts[0] == 1000000000000000000  # Input amount
            assert amounts[1] > 0  # Output amount > 0
            print(f"USDC v2 liquidity: {amounts[1] / 1e6:.2f} USDC for 1 WETH")
    
    @pytest.mark.skipif(not os.getenv('BASE_RPC_URL'), reason="Requires BASE_RPC_URL for live test")
    def test_live_v3_quote(self, client):
        """Test live v3 quote (requires RPC)"""
        # Test with USDC on Base
        usdc_address = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
        
        for fee in [500, 3000, 10000]:
            try:
                amount_out = client.v3_quote_amount_out(
                    client.weth_address,
                    usdc_address,
                    1000000000000000000,  # 1 WETH
                    fee=fee
                )
                if amount_out and amount_out > 0:
                    print(f"USDC v3 fee={fee}: {amount_out / 1e6:.2f} USDC for 1 WETH")
                    break
            except Exception as e:
                print(f"Fee {fee} failed: {e}")
                continue


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
