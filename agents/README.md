# Agents and Tools

An agent is an LLM-driven worker with a role, instructions, tools, and an explicit responsibility. A domain module or provider adapter is not an agent by itself.

## Agent roles

| Agent | Responsibility | Tools it may use |
| --- | --- | --- |
| Scout | Search the web for approved prospects and prepare evidence-backed sandbox candidates | Built-in web search, directory lookup, source inspection, sandbox publisher |
| Pitcher | Draft and send approved outreach and classify replies | Contact lookup, draft writer, approval queue, email provider |
| Intake | Turn Scout assumptions into a low-friction confirmation flow and prepare the scope/SOW | Portal events, prefilled intake form, field catalog, pricing rules, SOW generator |
| Provisioning | Start paid projects and create the engineering handoff | PayPal events, project/repository provisioner, secret reference store |
| Dev Lead | Plan and coordinate a feed implementation | Job launcher, task board, artifact store |
| Builder Team | Implement the current plan and report evidence | DOM inspection, repository, container build, test runner |
| QA Gatekeeper | Independently validate quality and publish the escrow preview | Fixture runner, validator, preview publisher |
| Delivery | Run scheduled syncs and report freshness | Destination writer, scheduler, health checks |
| Retainer Monitor | Detect failures and coordinate bounded repairs | Health checks, incident queue, repair job launcher |

## Tool boundary

The current modules are tools or shared domain services:

- `domain.py`: lifecycle state machine and pricing invariants
- `portal.py`: sandbox, interaction, field-selection, CSV, and checkout operations
- `payments.py`: idempotent application of already-verified payment events
- `job_runner.py`: local specialist execution and QA artifact handoff
- `progress.py`: customer-safe build status events

An LLM agent should call these through narrow tool functions. It must not mutate `Lead` fields directly, invent source evidence, bypass access controls, or mark a payment successful from a browser redirect.

Scout has the built-in Antigravity `SEARCH_WEB` capability enabled, plus a bounded local search tool for Ollama. Search results are leads for investigation, not confirmed facts: Scout must preserve source URLs, distinguish observed facts from assumptions, respect source terms and rate limits, and escalate blocked or restricted sources.

The Scout-to-portal pipeline verifies that the sample source is present in Scout evidence before creating a sandbox. This prevents an unverified URL or unrelated sample from reaching a prospect.

## Required agent shape

Each production agent should declare:

1. A single responsibility and allowed lifecycle states.
2. A system instruction defining its limits and escalation conditions.
3. Typed tools with input/output schemas and audit events.
4. Durable task status, retry and timeout behavior, and an idempotency key.
5. Human approval requirements for consequential actions.
6. A structured result that another agent or the workflow engine can validate.

The first Antigravity agent slice now lives in `llm/leadops-agents/`: `Scout`, `Intake`, and `Provisioning` use fake-safe typed tools, while `leadops_coordinator` delegates between them. The model provider remains replaceable and the business rules remain deterministic.

The Intake agent should prefer confirmation over interrogation: display research assumptions with evidence and confidence, request corrections inline, and defer optional questions until the core scope is accepted.

## Reactive build loop

The development workflow is a ReAct-style loop with explicit control points:

`Planner -> Dev Lead -> Builder Team -> QA Gatekeeper`

The Builder Team contains four specialists: Network Engineer, Frontend DOM Specialist, Systems Architect, and Junior Developer. Dev Lead creates role-owned work items and coordinates their evidence. The QA Gatekeeper is outside the Builder Team and computes its score from that evidence; the Builder Team does not enter its own score. A computed score below 95 routes concrete feedback to `Planner` and starts a new iteration. A score of 95 or higher is the only path to `ESCROW_READY`. The LLM may propose work, but the deterministic build-loop tool enforces the gate and prevents self-approval.

Specialist output is collected in an artifact manifest. The QA handoff includes role, artifact kind, checksum, and iteration, but not artifact content or secrets. QA receives the manifest only when all four Builder Team roles have submitted evidence.

The local execution boundary is [job_runner.py](job_runner.py). It runs the four specialist handlers, records job status, publishes customer-safe progress events, stops on the first failed role, and returns a QA-ready manifest only after every role succeeds. Azure or DigitalOcean adapters can invoke the same runner contract later.

Portal progress uses [progress.py](progress.py). It publishes ordered, customer-safe role/status messages for Planner, Dev Lead, specialists, and QA without exposing prompts, internal reasoning, secrets, or raw artifacts.