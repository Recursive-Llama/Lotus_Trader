"""
Trader Lowcap (TDL)

Specialized execution for social lowcap trades.
Implements three-way entry and progressive exit strategies.
Learns from execution outcomes and venue performance.
"""

from .trader_lowcap import TraderLowcap

__all__ = ['TraderLowcap']
