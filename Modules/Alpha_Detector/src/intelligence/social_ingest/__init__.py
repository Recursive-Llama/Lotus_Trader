"""
Social Ingest Module

Real-time social media scraping and token extraction for social lowcap intelligence.
Uses LLM for information extraction and Birdeye/Helix for token verification.
"""

from .social_ingest_basic import SocialIngestModule

__all__ = ['SocialIngestModule']
