"""
Hyperliquid Symbol to CoinGecko ID Mapping

Static mapping for looking up market cap data from CoinGecko.
This maps HL perp symbols to the underlying token's CoinGecko ID.

Usage:
    from hl_coingecko_mapping import HL_TO_COINGECKO, get_coingecko_id
    
    cg_id = get_coingecko_id("BTC")  # Returns "bitcoin"
    cg_id = get_coingecko_id("kPEPE")  # Returns "pepe" (1000x version)
"""

# Hyperliquid symbol -> CoinGecko ID
# Manually curated for accuracy
HL_TO_COINGECKO = {
    # ===== Major Cryptocurrencies =====
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "DOGE": "dogecoin",
    "ADA": "cardano",
    "DOT": "polkadot",
    "AVAX": "avalanche-2",
    "LINK": "chainlink",
    "LTC": "litecoin",
    "BCH": "bitcoin-cash",
    "ATOM": "cosmos",
    "XLM": "stellar",
    "XMR": "monero",
    "ETC": "ethereum-classic",
    "NEAR": "near",
    "FIL": "filecoin",
    "INJ": "injective-protocol",
    "ICP": "internet-computer",
    "TRX": "tron",
    "HBAR": "hedera-hashgraph",
    
    # ===== Layer 2 / Alt L1 =====
    "ARB": "arbitrum",
    "OP": "optimism",
    "SUI": "sui",
    "APT": "aptos",
    "SEI": "sei-network",
    "TIA": "celestia",
    "TAO": "bittensor",
    "STX": "blockstack",
    "TON": "the-open-network",
    "KAS": "kaspa",
    "MNT": "mantle",
    "STRK": "starknet",
    "ZETA": "zetachain",
    "DYM": "dymension",
    "BLAST": "blast",
    "MANTA": "manta-network",
    "ZK": "zksync",
    "SCR": "scroll",
    "BERA": "berachain-bera",
    "LINEA": "linea",
    "MOVE": "movement",
    "INIT": "initia",
    
    # ===== DeFi =====
    "AAVE": "aave",
    "UNI": "uniswap",
    "LDO": "lido-dao",
    "CRV": "curve-dao-token",
    "SNX": "havven",
    "COMP": "compound-governance-token",
    "GMX": "gmx",
    "SUSHI": "sushi",
    "CAKE": "pancakeswap-token",
    "PENDLE": "pendle",
    "DYDX": "dydx-chain",
    "RUNE": "thorchain",
    "ENA": "ethena",
    "ETHFI": "ether-fi",
    "EIGEN": "eigenlayer",
    "ONDO": "ondo-finance",
    "MORPHO": "morpho",
    "ZRO": "layerzero",
    "MAV": "maverick-protocol",
    "REZ": "renzo",
    "AERO": "aerodrome-finance",
    
    # ===== Infrastructure =====
    "RENDER": "render-token",
    "FET": "fetch-ai",
    "AR": "arweave",
    "IMX": "immutable-x",
    "ENS": "ethereum-name-service",
    "PYTH": "pyth-network",
    "GAS": "gas",
    "ORDI": "ordinals",
    
    # ===== Gaming / Metaverse =====
    "GALA": "gala",
    "SAND": "the-sandbox",
    "APE": "apecoin",
    "BLUR": "blur",
    "YGG": "yield-guild-games",
    "BIGTIME": "big-time",
    "MAVIA": "heroes-of-mavia",
    
    # ===== Memecoins =====
    "WIF": "dogwifcoin",
    "BONK": "bonk",
    "PEPE": "pepe",
    "FLOKI": "floki",
    "SHIB": "shiba-inu",
    "MEME": "memecoin",
    "POPCAT": "popcat",
    "MEW": "cat-in-a-dogs-world",
    "BOME": "book-of-meme",
    "TRUMP": "official-trump",
    "PNUT": "peanut-the-squirrel",
    "GOAT": "goatseus-maximus",
    "SPX": "spx6900",
    "MOODENG": "moo-deng",
    "FARTCOIN": "fartcoin",
    "BRETT": "based-brett",
    "TURBO": "turbo",
    "MELANIA": "melania-meme",
    "CHILLGUY": "chill-guy",
    
    # ===== AI / Agents =====
    "VIRTUAL": "virtual-protocol",
    "AIXBT": "aixbt",
    "ZEREBRO": "zerebro",
    "GRIFFAIN": "griffain",
    "GOAT": "goatseus-maximus",
    
    # ===== Hyperliquid Native =====
    "HYPE": "hyperliquid",
    "PURR": "purr-2",
    
    # ===== Solana Ecosystem =====
    "JTO": "jito-governance-token",
    "JUP": "jupiter-exchange-solana",
    "TNSR": "tensor",
    "GRASS": "grass",
    "LAYER": "solayer",
    "KAITO": "kaito",
    
    # ===== Other L1s =====
    "NEO": "neo",
    "IOTA": "iota",
    "ZEC": "zcash",
    "ALGO": "algorand",
    "MINA": "mina-protocol",
    "CELO": "celo",
    "CFX": "conflux-token",
    "ZEN": "zencash",
    "BSV": "bitcoin-cash-sv",
    
    # ===== Misc =====
    "RSR": "reserve-rights-token",
    "FTT": "ftx-token",
    "GMT": "stepn",
    "WLD": "worldcoin-wld",
    "HMSTR": "hamster-kombat",
    "NOT": "notcoin",
    "PENGU": "pudgy-penguins",
    "VVV": "venice-token",
    "PEOPLE": "constitutiondao",
    "USTC": "terrausd",
    "TRB": "tellor",
    "UMA": "uma",
    "SAGA": "saga-2",
    "POLYX": "polymesh",
    "BIO": "bio-protocol",
    "MERL": "merlin-chain",
    "USUAL": "usual",
    "IP": "story-2",
    "ANIME": "animecoin",
    "PAXG": "pax-gold",
    "ARK": "ark",
    
    # ===== Additional tokens =====
    "0G": "zero-gravity",
    "2Z": "doublezero",
    "ALT": "altlayer",
    "BANANA": "banana-gun",
    "OM": "mantra-dao",
    "POL": "polygon-ecosystem-token",
    "SUPER": "superfarm",
    "W": "wormhole",
    "IO": "io",  # io.net - was io-net
    "SKY": "skycoin",  # Or remove if not traded
    "DOOD": "doodles",
    "ZORA": "zora",
    "XAI": "xai-blockchain",
    
    # ===== Remaining tokens (user-provided) =====
    "ACE": "endurance",  # Fusionist game token
    "APEX": "apex-token",
    "ASTER": "aster-2",
    "AVNT": "avantis",
    "BABY": "babylon",
    "CC": "canton",
    "FOGO": "fogo",
    "HEMI": "hemi",
    "HYPER": "hyperlane",
    "LIT": "lighter",
    "ME": "magic-eden",
    "MEGA": "megaeth",
    "MET": "meteora",
    "MON": "monad",
    "NIL": "nillion",
    "NXPC": "nexpace",
    "PROMPT": "wayfinder",
    "PROVE": "succinct",
    "PUMP": "pump-fun",
    "RESOLV": "resolv",
    "S": "sonic",
    "SOPH": "sophon",
    "STABLE": "stable-2",
    "STBL": "stbl",
    "SYRUP": "syrup",  # Maple Finance
    "TST": "test-2",
    "VINE": "vine",
    "WCT": "connect-token-wct",  # WalletConnect Token
    "WLFI": "world-liberty-financial",
    "XPL": "plasma",
    "YZY": "yzy",
    
    # ===== 1000x Versions (k-prefix) =====
    # These map to the same underlying token
    "kBONK": "bonk",
    "kPEPE": "pepe",
    "kFLOKI": "floki",
    "kSHIB": "shiba-inu",
    "kLUNC": "terra-luna",
    "kNEIRO": "neiro-3",
}


def get_coingecko_id(hl_symbol: str) -> str | None:
    """
    Get CoinGecko ID for a Hyperliquid symbol.
    
    Args:
        hl_symbol: Hyperliquid symbol (e.g., "BTC", "kPEPE")
        
    Returns:
        CoinGecko ID or None if not mapped
    """
    return HL_TO_COINGECKO.get(hl_symbol)


def get_all_coingecko_ids() -> list[str]:
    """Get all unique CoinGecko IDs for batch API calls."""
    return list(set(HL_TO_COINGECKO.values()))


def get_unmapped_symbols(hl_symbols: list[str]) -> list[str]:
    """Get HL symbols that don't have a CoinGecko mapping."""
    return [s for s in hl_symbols if s not in HL_TO_COINGECKO]
