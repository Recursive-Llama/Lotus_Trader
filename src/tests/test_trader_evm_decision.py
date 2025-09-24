#!/usr/bin/env python3
"""
Test Trader EVM Decision Integration
"""

import pytest
import os
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from decimal import Decimal

# Add src to path
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intelligence.trader_lowcap.trader_lowcap_simple_v2 import TraderLowcapSimpleV2
from trading.evm_uniswap_client import EvmUniswapClient
from trading.evm_uniswap_client_eth import EthUniswapClient


class MockSupabaseManager:
    """Mock Supabase manager for testing"""
    
    def __init__(self):
        self.positions = {}
        self.strands = []
    
    def table(self, table_name):
        """Mock table access"""
        if table_name == 'lowcap_positions':
            return MockTable(self.positions)
        elif table_name == 'decision_lowcap_strands':
            return MockTable(self.strands)
        return MockTable({})
    
    def client(self):
        """Mock client access"""
        return self


class MockTable:
    """Mock table operations"""
    
    def __init__(self, data):
        self.data = data
    
    def insert(self, record):
        """Mock insert"""
        if isinstance(record, dict):
            record['id'] = len(self.data) + 1
            self.data[record.get('position_id', f"pos_{len(self.data)}")] = record
        return MockResponse(record)
    
    def update(self, updates):
        """Mock update"""
        return MockResponse(updates)
    
    def select(self, columns="*"):
        """Mock select"""
        return MockQuery(self.data.values())
    
    def eq(self, column, value):
        """Mock equality filter"""
        return MockQuery([v for v in self.data.values() if v.get(column) == value])


class MockQuery:
    """Mock query operations"""
    
    def __init__(self, data):
        self.data = list(data)
    
    def execute(self):
        """Mock execute"""
        return MockResponse(self.data)
    
    def eq(self, column, value):
        """Mock equality filter"""
        filtered = [v for v in self.data if v.get(column) == value]
        return MockQuery(filtered)


class MockResponse:
    """Mock response"""
    
    def __init__(self, data):
        self.data = data


class TestTraderEvmDecision:
    """Test trader EVM decision integration"""
    
    @pytest.fixture
    def mock_supabase(self):
        """Create mock Supabase manager"""
        return MockSupabaseManager()
    
    @pytest.fixture
    def trader(self, mock_supabase):
        """Create trader instance"""
        with patch.dict(os.environ, {
            'HELIUS_API_KEY': 'test_key',
            'SOL_WALLET_PRIVATE_KEY': 'test_sol_key',
            'ETH_WALLET_PRIVATE_KEY': 'test_eth_key',
            'BASE_RPC_URL': 'https://test.base.rpc',
            'ETH_RPC_URL': 'https://test.eth.rpc'
        }):
            trader = TraderLowcapSimpleV2(mock_supabase)
            # Mock the clients to avoid RPC connection issues
            trader.base_client = Mock()
            trader.eth_client = Mock()
            # Add required attributes
            trader.base_client.weth_address = '0x4200000000000000000000000000000000000006'
            trader.eth_client.weth_address = '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'
            return trader
    
    @pytest.fixture
    def base_decision(self):
        """Create Base decision strand"""
        return {
            'id': 'test_base_decision',
            'content': {
                'action': 'approve',
                'curator_id': 'test_curator',
                'ticker': 'AVNT',
                'contract': '0x696F9436B67233384889472Cd7cD58A6fB5DF4f1',
                'chain': 'base',
                'allocation_pct': 1.0,
                'curator_confidence': 0.85
            },
            'status': 'approved',
            'created_at': '2024-01-01T00:00:00Z'
        }
    
    @pytest.fixture
    def eth_decision(self):
        """Create Ethereum decision strand"""
        return {
            'id': 'test_eth_decision',
            'content': {
                'action': 'approve',
                'curator_id': 'test_curator',
                'ticker': 'XMW',
                'contract': '0x391cF4b21F557c935C7f670218Ef42C21bd8d686',
                'chain': 'ethereum',
                'allocation_pct': 1.0,
                'curator_confidence': 0.85
            },
            'status': 'approved',
            'created_at': '2024-01-01T00:00:00Z'
        }
    
    def test_trader_initialization(self, trader):
        """Test trader initializes correctly"""
        assert trader.supabase_manager is not None
        assert trader.jupiter_client is not None
        assert trader.wallet_manager is not None
        assert trader.base_client is not None
        assert trader.eth_client is not None
    
    @pytest.mark.asyncio
    async def test_base_decision_processing(self, trader, mock_supabase, base_decision):
        """Test Base decision processing"""
        # Mock the clients to avoid real RPC calls
        with patch.object(trader.base_client, 'v2_get_amounts_out') as mock_v2, \
             patch.object(trader.base_client, 'v3_quote_amount_out') as mock_v3, \
             patch.object(trader.base_client, 'get_token_decimals') as mock_decimals, \
             patch.object(trader, '_execute_entry') as mock_execute:
            
            # Mock successful v2 liquidity check
            mock_v2.return_value = [1000000000000000000, 2000000000000000000000]  # 1 WETH -> 2000 tokens
            mock_decimals.return_value = 18
            mock_execute.return_value = True
            
            # Process the decision
            result = await trader.execute_decision(base_decision)
            
            # Verify position was created
            assert len(mock_supabase.positions) == 1
            position = list(mock_supabase.positions.values())[0]
            assert position['token_ticker'] == 'AVNT'
            assert position['token_contract'] == '0x696F9436B67233384889472Cd7cD58A6fB5DF4f1'
            assert position['token_chain'] == 'base'
            
            # Verify v2 was tried first
            mock_v2.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_eth_decision_processing(self, trader, mock_supabase, eth_decision):
        """Test Ethereum decision processing"""
        # Mock the clients to avoid real RPC calls
        with patch.object(trader.eth_client, 'v2_get_amounts_out') as mock_v2, \
             patch.object(trader.eth_client, 'v3_quote_amount_out') as mock_v3, \
             patch.object(trader.eth_client, 'get_token_decimals') as mock_decimals, \
             patch.object(trader, '_execute_entry') as mock_execute:
            
            # Mock successful v2 liquidity check
            mock_v2.return_value = [1000000000000000000, 2000000000000000000000]  # 1 WETH -> 2000 tokens
            mock_decimals.return_value = 18
            mock_execute.return_value = True
            
            # Process the decision
            result = await trader.execute_decision(eth_decision)
            
            # Verify position was created
            assert len(mock_supabase.positions) == 1
            position = list(mock_supabase.positions.values())[0]
            assert position['token_ticker'] == 'XMW'
            assert position['token_contract'] == '0x391cF4b21F557c935C7f670218Ef42C21bd8d686'
            assert position['token_chain'] == 'ethereum'
            
            # Verify v2 was tried first
            mock_v2.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_v2_fallback_to_v3(self, trader, mock_supabase, base_decision):
        """Test v2 fallback to v3 when v2 has no liquidity"""
        with patch.object(trader.base_client, 'v2_get_amounts_out') as mock_v2, \
             patch.object(trader.base_client, 'v3_quote_amount_out') as mock_v3, \
             patch.object(trader.base_client, 'get_token_decimals') as mock_decimals, \
             patch.object(trader, '_execute_entry') as mock_execute:
            
            # Mock v2 failure, v3 success
            mock_v2.side_effect = Exception("No liquidity")
            mock_v3.return_value = 2000000000000000000000  # 2000 tokens
            mock_decimals.return_value = 18
            mock_execute.return_value = True
            
            # Process the decision
            result = await trader.execute_decision(base_decision)
            
            # Verify v2 was tried first, then v3
            mock_v2.assert_called_once()
            mock_v3.assert_called()
    
    @pytest.mark.asyncio
    async def test_price_calculation(self, trader):
        """Test price calculation logic"""
        token_data = {
            'ticker': 'TEST',
            'contract': '0x1234567890123456789012345678901234567890',
            'chain': 'base'
        }
        
        with patch.object(trader.base_client, 'v2_get_amounts_out') as mock_v2, \
             patch.object(trader.base_client, 'get_token_decimals') as mock_decimals:
            
            # Mock v2 response: 1 WETH -> 2000 tokens
            mock_v2.return_value = [1000000000000000000, 2000000000000000000000]
            mock_decimals.return_value = 18
            
            price = await trader._get_current_price(token_data)
            
            # Price should be 0.001 ETH / (2000 tokens / 10^18) = 0.001 / 0.002 = 0.5 ETH per token
            expected_price = 0.001 / (2000000000000000000000 / 1e18)
            assert abs(price - expected_price) < 1e-10
    
    @pytest.mark.skipif(not os.getenv('BASE_RPC_URL') or not os.getenv('ETH_RPC_URL'), 
                        reason="Requires RPC URLs for live test")
    @pytest.mark.asyncio
    async def test_live_decision_processing(self, trader, mock_supabase):
        """Test live decision processing with real RPC calls"""
        # This test requires real RPC access and will be skipped in CI
        base_decision = {
            'id': 'live_base_test',
            'curator_id': 'test_curator',
            'ticker': 'AVNT',
            'contract': '0x696F9436B67233384889472Cd7cD58A6fB5DF4f1',
            'chain': 'base',
            'allocation_pct': 0.1,  # Small allocation for testing
            'curator_confidence': 0.85,
            'status': 'approved',
            'created_at': '2024-01-01T00:00:00Z'
        }
        
        with patch.object(trader, '_execute_entry') as mock_execute:
            mock_execute.return_value = True  # Skip actual execution
            
            result = await trader.execute_decision(base_decision)
            
            # Should create position and get price
            assert len(mock_supabase.positions) == 1
            position = list(mock_supabase.positions.values())[0]
            assert position['token_ticker'] == 'AVNT'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
