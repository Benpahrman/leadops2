"""Optional Ollama configuration for local Antigravity testing."""

import os

from google.antigravity import Agent, CapabilitiesConfig, LocalOpenAIAgentConfig, types

from workers.leadops_tools import (
    create_build_plan,
    evaluate_build_evidence,
    prepare_confirmation_intake,
    prepare_provisioning_plan,
    publish_sandbox_candidate,
    record_research_evidence,
)
from workers.web_search import search_web
from workers.environment import load_local_environment


DEFAULT_OLLAMA_MODEL = "gemma4:12b"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11435/v1"
load_local_environment()


def create_local_coordinator(model: str | None = None) -> Agent:
    """Create a local coordinator with an optional Ollama model override."""
    config = LocalOpenAIAgentConfig(
        model=model or os.getenv("LEADOPS_OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL),
        base_url=os.getenv("LEADOPS_OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL),
        system_instructions=(
            "You coordinate LeadOps locally for development. Delegate research, "
            "confirmation-first intake, planning, provisioning, and evidence-based "
            "QA. Never send email, collect payment, create cloud resources, or "
            "bypass access controls. Keep QA independent from the Builder Team."
        ),
        tools=[
            record_research_evidence,
            search_web,
            publish_sandbox_candidate,
            prepare_confirmation_intake,
            prepare_provisioning_plan,
            create_build_plan,
            evaluate_build_evidence,
        ],
        capabilities=CapabilitiesConfig(
            enabled_tools=[types.BuiltinTools.SEARCH_WEB],
        ),
        subagents=[
            types.SubagentConfig(
                name="scout",
                description="Researches approved prospects and records evidence.",
            ),
            types.SubagentConfig(
                name="intake",
                description="Creates confirmation-first intake forms.",
            ),
            types.SubagentConfig(
                name="planner",
                description="Creates testable build plans.",
            ),
            types.SubagentConfig(
                name="qa_gatekeeper",
                description="Independently evaluates build evidence.",
            ),
        ],
    )
    return Agent(config)


def create_local_intake(model: str | None = None) -> Agent:
    """Create a lightweight Intake agent for fast Ollama smoke tests."""
    config = LocalOpenAIAgentConfig(
        model=model or os.getenv("LEADOPS_OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL),
        base_url=os.getenv("LEADOPS_OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL),
        system_instructions=(
            "You are Intake for LeadOps. Use prepare_confirmation_intake to turn "
            "Scout research into a concise, editable confirmation form. Show each "
            "assumption with its source and confidence. Ask for corrections inline, "
            "defer optional questions, and never present guesses as confirmed."
        ),
        tools=[prepare_confirmation_intake],
    )
    return Agent(config)