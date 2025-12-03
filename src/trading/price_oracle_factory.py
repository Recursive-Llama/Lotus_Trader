#!/usr/bin/env python3
"""
Price Oracle Factory

Creates PriceOracle instances independent of TraderLowcapSimpleV2.
Extracted to allow removal of legacy trader system.
"""

import os
import logging
from typing import Optional
from intelligence.trader_lowcap.price_oracle import PriceOracle

logger = logging.getLogger(__name__)


def create_price_oracle() -> PriceOracle:
    """
    Create a PriceOracle instance with chain clients.
    
    This factory function extracts PriceOracle initialization from TraderLowcapSimpleV2
    to allow independent usage.
    
    Returns:
        PriceOracle instance configured with available chain clients
    """
    # Initialize chain clients if possible
    bsc_client = None
    base_client = None
    eth_client = None
    
    try:
        from trading.evm_uniswap_client import EvmUniswapClient
        
        # BSC client
        bsc_pk = (
            os.getenv('BSC_WALLET_PRIVATE_KEY')
            or os.getenv('ETHEREUM_WALLET_PRIVATE_KEY')
            or os.getenv('ETH_WALLET_PRIVATE_KEY')
        )
        bsc_rpc = os.getenv('BSC_RPC_URL', 'https://bsc-dataseed.binance.org')
        if bsc_pk:
            bsc_client = EvmUniswapClient(chain='bsc', rpc_url=bsc_rpc, private_key=bsc_pk)
            logger.info("BSC client initialized for PriceOracle")
        else:
            logger.debug("BSC client not available (no private key)")
        
        # Base client
        base_pk = (
            os.getenv('BASE_WALLET_PRIVATE_KEY')
            or os.getenv('ETHEREUM_WALLET_PRIVATE_KEY')
            or os.getenv('ETH_WALLET_PRIVATE_KEY')
        )
        base_rpc = os.getenv('BASE_RPC_URL', 'https://mainnet.base.org')
        if base_pk:
            base_client = EvmUniswapClient(chain='base', rpc_url=base_rpc, private_key=base_pk)
            logger.info("Base client initialized for PriceOracle")
        else:
            logger.debug("Base client not available (no private key)")
        
        # Ethereum client
        eth_pk = (
            os.getenv('ETHEREUM_WALLET_PRIVATE_KEY')
            or os.getenv('ETH_WALLET_PRIVATE_KEY')
        )
        eth_rpc = os.getenv('ETH_RPC_URL', 'https://eth.llamarpc.com')
        if eth_pk:
            from trading.evm_uniswap_client_eth import EthUniswapClient as EthClient
            eth_client = EthClient(rpc_url=eth_rpc, private_key=eth_pk)
            logger.info("Ethereum client initialized for PriceOracle")
        else:
            logger.debug("Ethereum client not available (no private key)")
            
    except Exception as e:
        logger.warning(f"Error initializing chain clients for PriceOracle: {e}")
        logger.info("PriceOracle will work with DexScreener API only (no on-chain queries)")
    
    # Create PriceOracle (works with or without chain clients)
    # PriceOracle uses DexScreener API primarily, chain clients are optional
    price_oracle = PriceOracle(
        bsc_client=bsc_client,
        base_client=base_client,
        eth_client=eth_client
    )
    
    logger.info("PriceOracle created successfully")
    return price_oracle

