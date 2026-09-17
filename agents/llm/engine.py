"""
agents/llm/engine.py - Full LLMAgentEngine composition class.
Inherits base client and all specialist agent mixins for a unified interface.
"""
from .client import LLMClientBase
from .buyer_gate import BuyerGateMixin, is_disallowed_buyer, DISALLOWED_BUYER_DOMAINS, DISALLOWED_BUYER_KEYWORDS
from .dev_swarm import DevSwarmMixin
from .scout_agents import ScoutAgentsMixin
from .customer_agents import CustomerAgentsMixin


class LLMAgentEngine(
    LLMClientBase,
    BuyerGateMixin,
    DevSwarmMixin,
    ScoutAgentsMixin,
    CustomerAgentsMixin,
):
    """
    Manages LLM completions for Scout, Dev Swarm specialists, Alex Chat,
    QA Gatekeeper, and Retainer operations.
    """
    pass
