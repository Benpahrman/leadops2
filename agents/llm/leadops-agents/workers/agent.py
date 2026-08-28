import os

# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from google.antigravity import Agent, CapabilitiesConfig, LocalAgentConfig, types

from workers.leadops_tools import (
    prepare_confirmation_intake,
    create_build_plan,
    assign_builder_team,
    collect_team_evidence,
    create_team_work_items,
    evaluate_qa_gate,
    evaluate_build_evidence,
    prepare_provisioning_plan,
    publish_sandbox_candidate,
    record_research_evidence,
)
from workers.web_search import search_web
from workers.environment import load_local_environment


MODEL = "gemini-3.7-flash"
load_local_environment()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


scout_config = LocalAgentConfig(
    model=MODEL,
    api_key=GEMINI_API_KEY,
    vertex=False,
    system_instructions=(
        "You are Scout, the LeadOps research agent. Find evidence-backed B2B "
        "prospects in approved sources and prepare a tailored sandbox candidate. "
        "Use record_research_evidence only for facts supported by the supplied "
        "source. Never invent contacts, scrape restricted data, bypass CAPTCHA, "
        "WAF, or access controls, or send outreach. Preserve uncertainty and "
        "require customer confirmation."
    ),
    tools=[search_web, record_research_evidence, publish_sandbox_candidate],
    capabilities=CapabilitiesConfig(
        enabled_tools=[types.BuiltinTools.SEARCH_WEB],
    ),
)


intake_config = LocalAgentConfig(
    model=MODEL,
    api_key=GEMINI_API_KEY,
    vertex=False,
    system_instructions=(
        "You are Intake, the LeadOps requirements agent. Reduce customer effort "
        "by turning Scout research into a confirmation-first form. Use "
        "prepare_confirmation_intake. Present assumptions as editable, show their "
        "source and confidence, ask for corrections inline, and defer optional "
        "questions. Never present guesses as confirmed requirements and never "
        "approve pricing or payment."
    ),
    tools=[prepare_confirmation_intake],
    capabilities=CapabilitiesConfig(
        enabled_tools=[
            types.BuiltinTools.SEARCH_WEB,
        ]
    )
)


provisioning_config = LocalAgentConfig(
    model=MODEL,
    api_key=GEMINI_API_KEY,
    vertex=False,
    system_instructions=(
        "You are Provisioning, the LeadOps paid-project handoff agent. Use "
        "prepare_provisioning_plan only after a verified deposit event. Azure is "
        "the default production provider and DigitalOcean is staging-only. "
        "Prepare plans but never create cloud resources, expose secrets, or "
        "start work without the required approval."
    ),
    tools=[prepare_provisioning_plan],
)


planner_config = LocalAgentConfig(
    model=MODEL,
    api_key=GEMINI_API_KEY,
    vertex=False,
    system_instructions=(
        "You are Planner. Convert an approved scope into small, testable build "
        "objectives and acceptance criteria. Use create_build_plan. Keep plans "
        "bounded by the purchased tier and route the current plan to Dev Lead."
    ),
    tools=[create_build_plan],
)


dev_lead_config = LocalAgentConfig(
    model=MODEL,
    api_key=GEMINI_API_KEY,
    vertex=False,
    system_instructions=(
        "You are Dev Lead. Coordinate the Builder Team against the current plan. "
        "Assign work, track dependencies, and return a complete build artifact "
        "to the independent QA Gatekeeper. Do not approve your own work or bypass "
        "the QA gate."
    ),
)


builder_team_config = LocalAgentConfig(
    model=MODEL,
    api_key=GEMINI_API_KEY,
    vertex=False,
    system_instructions=(
        "You coordinate the Builder Team. Delegate only to Network Engineer, "
        "Frontend DOM Specialist, Systems Architect, and Junior Developer. "
        "Implement only the current Dev Lead plan and report evidence for each "
        "acceptance criterion. Do not change scope, declare QA success, or publish "
        "delivery. QA is outside your team."
    ),
    tools=[assign_builder_team, create_team_work_items, collect_team_evidence],
    subagents=[
        types.SubagentConfig(
            name="network_engineer",
            description="Handles network, access, rate limits, and permitted source connectivity.",
        ),
        types.SubagentConfig(
            name="frontend_dom_specialist",
            description="Maps customer portal structure and DOM extraction rules.",
        ),
        types.SubagentConfig(
            name="systems_architect",
            description="Owns contracts, runtime design, and integration boundaries.",
        ),
        types.SubagentConfig(
            name="junior_developer",
            description="Implements bounded tasks and tests under senior guidance.",
        ),
    ],
)


qa_gatekeeper_config = LocalAgentConfig(
    model=MODEL,
    api_key=GEMINI_API_KEY,
    vertex=False,
    system_instructions=(
        "You are the independent QA Gatekeeper. Evaluate the Builder Team output "
        "against acceptance criteria using evaluate_qa_gate. You are outside the "
        "Builder Team and must not repair its work. A score below 95 routes the "
        "work back to Planner with concrete feedback; 95 or higher unlocks escrow."
    ),
    tools=[evaluate_build_evidence, evaluate_qa_gate],
)


coordinator_config = LocalAgentConfig(
    model=MODEL,
    api_key=GEMINI_API_KEY,
    vertex=False,
    system_instructions=(
        "You coordinate LeadOps prospect onboarding. Delegate research to Scout "
        "and customer requirement confirmation to Intake. Preserve evidence, "
        "uncertainty, and approval boundaries. Never send email, collect payment, "
        "or mark a lead paid without a verified provider event."
    ),
    subagents=[
        types.SubagentConfig(
            name="scout",
            description="Researches approved prospects and records evidence.",
        ),
        types.SubagentConfig(
            name="intake",
            description="Creates confirmation-first intake forms from research.",
        ),
        types.SubagentConfig(
            name="provisioning",
            description="Prepares paid-project cloud handoff plans.",
        ),
        types.SubagentConfig(
            name="planner",
            description="Creates testable objectives and acceptance criteria.",
        ),
        types.SubagentConfig(
            name="dev_lead",
            description="Coordinates the Builder Team without approving its work.",
        ),
        types.SubagentConfig(
            name="builder_team",
            description="Implements the current plan and reports evidence.",
        ),
        types.SubagentConfig(
            name="qa_gatekeeper",
            description="Independently gates escrow at a 95 percent threshold.",
        ),
    ],
)


scout_agent = Agent(scout_config)
intake_agent = Agent(intake_config)
provisioning_agent = Agent(provisioning_config)
planner_agent = Agent(planner_config)
dev_lead_agent = Agent(dev_lead_config)
builder_team_agent = Agent(builder_team_config)
qa_gatekeeper_agent = Agent(qa_gatekeeper_config)
root_agent = Agent(coordinator_config)
