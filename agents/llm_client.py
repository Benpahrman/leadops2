"""
agents/llm_client.py - Backward-compatible facade for agents.llm package.
See ADR-0002 (Strangler Fig Modularization Protocol).

Decomposed into:
  - agents.llm.buyer_gate: Qualification gates and disallowed domains
  - agents.llm.client: LLMClientBase and core inference gateway
  - agents.llm.dev_swarm: DevSwarmMixin specialist roles
  - agents.llm.scout_agents: ScoutAgentsMixin discovery & classification
  - agents.llm.customer_agents: CustomerAgentsMixin client-facing workflows
  - agents.llm.engine: Unified LLMAgentEngine
"""
from agents.llm import (
    LLMAgentEngine,
    is_disallowed_buyer,
    DISALLOWED_BUYER_DOMAINS,
    DISALLOWED_BUYER_KEYWORDS,
    BuyerGateMixin,
    LLMClientBase,
    DevSwarmMixin,
    ScoutAgentsMixin,
    CustomerAgentsMixin,
)

__all__ = [
    "LLMAgentEngine",
    "is_disallowed_buyer",
    "DISALLOWED_BUYER_DOMAINS",
    "DISALLOWED_BUYER_KEYWORDS",
    "BuyerGateMixin",
    "LLMClientBase",
    "DevSwarmMixin",
    "ScoutAgentsMixin",
    "CustomerAgentsMixin",
]
