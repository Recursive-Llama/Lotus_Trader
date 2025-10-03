"""
Pure view-model builders for trader notifications.

No formatting or IO here; only derive values used by notifiers.
"""

from __future__ import annotations

from typing import Optional, Dict, Any


def _get_price_info(price_oracle, chain: str, contract: str) -> Optional[Dict[str, Any]]:
    try:
        if chain == 'bsc':
            return price_oracle.price_bsc(contract)
        if chain == 'base':
            return price_oracle.price_base(contract)
        if chain == 'ethereum':
            return price_oracle.price_eth(contract)
        if chain == 'solana':
            return price_oracle.price_solana(contract)
        return None
    except Exception:
        return None


async def build_sell_view(
    *,
    position: Dict[str, Any],
    tokens_sold: float,
    sell_price_native: float,
    chain: str,
    contract: str,
    price_oracle,
    get_native_usd_rate,
) -> Dict[str, Any]:
    native_usd_rate = await get_native_usd_rate(chain)
    if native_usd_rate and native_usd_rate > 0:
        sell_price_usd = sell_price_native * native_usd_rate
        tokens_sold_value_usd = tokens_sold * sell_price_usd
    else:
        tokens_sold_value_usd = tokens_sold * sell_price_native

    remaining_tokens = (position.get('total_quantity', 0) or 0) - tokens_sold

    position_value = None
    if remaining_tokens > 0:
        price_info = _get_price_info(price_oracle, chain, contract)
        if price_info and 'price_usd' in price_info and price_info['price_usd']:
            position_value = remaining_tokens * float(price_info['price_usd'])

    return {
        'tokens_sold_value_usd': tokens_sold_value_usd,
        'remaining_tokens': remaining_tokens,
        'position_value': position_value,
        'total_pnl_pct': position.get('total_pnl_pct', 0),
        'total_profit_usd': position.get('total_pnl_usd'),
    }


async def build_buy_view(
    *,
    amount_native: float,
    chain: str,
    get_native_usd_rate,
) -> Dict[str, Any]:
    native_usd_rate = await get_native_usd_rate(chain)
    amount_usd = amount_native * native_usd_rate if native_usd_rate and native_usd_rate > 0 else None
    return {'amount_usd': amount_usd}


async def build_trend_entry_view(
    *,
    amount_native: float,
    chain: str,
    get_native_usd_rate,
) -> Dict[str, Any]:
    native_usd_rate = await get_native_usd_rate(chain)
    amount_usd = amount_native * native_usd_rate if native_usd_rate and native_usd_rate > 0 else None
    return {'amount_usd': amount_usd}


async def build_trend_exit_view(
    *,
    profit_usd: Optional[float],
    chain: str,
    get_native_usd_rate,
) -> Dict[str, Any]:
    profit_native = None
    if profit_usd is not None and chain in ('bsc', 'base', 'ethereum'):
        native_usd_rate = await get_native_usd_rate(chain)
        if native_usd_rate and native_usd_rate > 0:
            profit_native = profit_usd / native_usd_rate
    return {'profit_native': profit_native}


