"""
Pure domain helpers for Trader Lowcap V2.

No I/O. These functions operate on provided values and return results.
"""

from __future__ import annotations

from typing import Tuple


def compute_position_value_native(total_quantity: float, current_price_native: float) -> float:
    if total_quantity <= 0 or current_price_native <= 0:
        return 0.0
    return float(total_quantity) * float(current_price_native)


def compute_total_pnl_native(
    total_extracted_native: float,
    current_position_value_native: float,
    total_investment_native: float,
) -> float:
    return float(total_extracted_native) + float(current_position_value_native) - float(total_investment_native)


def convert_native_to_usd(native_amount: float, native_usd_rate: float) -> float:
    if native_usd_rate <= 0:
        return 0.0
    return float(native_amount) * float(native_usd_rate)


def compute_total_pnl_pct(total_pnl_native: float, total_investment_native: float) -> float:
    if total_investment_native <= 0:
        return 0.0
    return (float(total_pnl_native) / float(total_investment_native)) * 100.0


