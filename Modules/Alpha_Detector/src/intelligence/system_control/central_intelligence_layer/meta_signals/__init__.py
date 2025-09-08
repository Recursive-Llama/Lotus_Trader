"""
Meta-Signal System - CIL Signal Generation
Generates higher-order meta-signals from cross-agent patterns and timing
"""

from .meta_signal_generator import MetaSignalGenerator, MetaSignal
from .confluence_detector import ConfluenceDetector, ConfluenceEvent
from .lead_lag_predictor import LeadLagPredictor, LeadLagRelationship
from .transfer_hit_detector import TransferHitDetector, TransferHit

__all__ = [
    'MetaSignalGenerator',
    'MetaSignal',
    'ConfluenceDetector', 
    'ConfluenceEvent',
    'LeadLagPredictor',
    'LeadLagRelationship',
    'TransferHitDetector',
    'TransferHit'
]

