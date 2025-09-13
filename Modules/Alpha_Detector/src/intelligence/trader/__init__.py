"""
Trader Intelligence Module

Elegant, focused Trader that executes approved trading decisions from DM
and manages the complete execution lifecycle. Integrates with the centralized
learning system for continuous improvement.

Key Features:
- Execute approved trading decisions
- Position management and P&L tracking
- Venue selection and execution optimization
- Performance monitoring and feedback
- Context injection from learning system
- Module-specific resonance scoring
"""

from .trader import Trader, ExecutionStatus, VenueType

__all__ = [
    'Trader',
    'ExecutionStatus',
    'VenueType'
]