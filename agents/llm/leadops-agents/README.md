# LeadOps Agents

Role-based LeadOps LLM agents using the Google Antigravity SDK.

## Agents

- `scout`: researches approved prospects and records evidence-backed assumptions.
- `intake`: turns Scout research into an editable, confirmation-first form.
- `provisioning`: prepares an approved, deposit-confirmed Azure or DigitalOcean handoff plan.
- Builder Team: Network Engineer, Frontend DOM Specialist, Systems Architect, and Junior Developer, coordinated by Dev Lead.
- QA Gatekeeper: independent reviewer outside the Builder Team; failures return to Planner.
- `leadops_coordinator`: delegates onboarding work while preserving approval boundaries.

Tools are in `workers/leadops_tools.py`. They validate inputs and return structured results; agents do not mutate payment or lifecycle state directly, preserve uncertainty, and stop on restricted access rather than bypassing controls.

The Ollama/local profile also exposes `workers/web_search.py`, a bounded public-search tool for development. It returns at most 10 URLs, uses a 10-second timeout, marks every result for separate source verification, and fails closed when the provider returns a challenge or no parseable results.

Scout can prepare a portal candidate with `publish_sandbox_candidate()`. The result includes a stable `/p/{slug}` path, source URL, sample rows, and explicit read-only/customer-confirmation flags. The real portal service remains responsible for storing and serving the sandbox.

## Setup

Requires Python 3.11-3.13 and `uv`.

Configure `GEMINI_API_KEY` using a secret manager or local `.env` file. Create a key at [Google AI Studio](https://aistudio.google.com/app/api-keys). `python-dotenv` loads the agent project `.env` and workspace-root `.env` automatically; values are never logged.

```powershell
uv sync
```

For no-cost local testing, run Ollama and pull a model:

```powershell
ollama pull gemma4:12b
```

Use `create_local_coordinator()` from `workers/local_agent.py`. The default model is `gemma4:12b`. For the Docker setup exposing host port `11435`, it connects to `http://localhost:11435/v1` through Antigravity's `LocalOpenAIAgentConfig`, with optional overrides using `LEADOPS_OLLAMA_MODEL` and `LEADOPS_OLLAMA_BASE_URL`.

For faster local smoke tests, use an installed smaller model such as `qwen3b-large:latest`:

```python
create_local_coordinator(model="qwen3b-large:latest")
```

Use Gemma for the quality profile and the smaller model for quick iteration; both use the same tools and agent responsibilities.

For the fastest behavior test, use `create_local_intake(model="qwen3b-large:latest")` so only the Intake agent runs without coordinator delegation.

For a fast connectivity/model smoke test that avoids Antigravity session overhead:

```powershell
@'
from workers.ollama_smoke import chat_with_ollama
print(chat_with_ollama("Reply with exactly LOCAL_OLLAMA_OK", model="qwen3b-large:latest").content)
'@ | uv run python -
```

Use the direct runner for endpoint checks. Use Antigravity factories for real agent/tool orchestration; the latter may take longer with local 12B models.

## Tests

```powershell
uv run pytest tests/unit -q
```

These tests validate tool contracts only. Model behavior should be evaluated with representative Scout and Intake conversations after credentials are configured.

## Runtime boundary

The LLM runtime is Google Antigravity. Production workflow orchestration remains Azure Logic Apps and Azure Container Apps Jobs. PayPal, portal, lifecycle, and delivery actions must remain behind verified, auditable tools.

Do not deploy until PayPal webhook verification, portal authentication, audit logging, and approval gates are complete.
