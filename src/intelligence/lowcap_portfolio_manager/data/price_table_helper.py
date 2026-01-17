"""
Simple helper to get the correct price data table name based on chain and book_id.

This avoids hardcoding table names throughout the codebase.
"""


def get_price_table_name(token_chain: str, book_id: str = None) -> str:
    """
    Get the price data table name for a given chain and book_id.
    
    Args:
        token_chain: Chain/venue identifier (e.g., "solana", "hyperliquid")
        book_id: Optional book identifier (e.g., "perps", "onchain_crypto", "stock_perps")
    
    Returns:
        Table name string (e.g., "lowcap_price_data_ohlc", "hyperliquid_price_data_ohlc")
    """
    chain_lower = token_chain.lower() if token_chain else ""
    
    # Hyperliquid uses its own table
    if chain_lower == "hyperliquid":
        return "hyperliquid_price_data_ohlc"
    
    # Default: lowcap_price_data_ohlc (Solana, Ethereum, Base, BSC, etc.)
    return "lowcap_price_data_ohlc"

