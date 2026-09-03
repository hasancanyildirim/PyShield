"""
AI-QA Shield - Campaign Module.

Provides the campaign execution engine and orchestration interfaces for running
structured security test campaigns against target AI systems.
"""

from .campaign_runner import run_campaign
from .integration import run_and_store_campaign, validate_demo_contract

__all__ = [
    "run_campaign",
    "run_and_store_campaign",
    "validate_demo_contract",
]
