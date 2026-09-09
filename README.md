 # LeadOps

LeadOps automates the path from a tailored prospect sandbox to recurring data delivery or a full source-code buyout.

## Current implementation

The initial domain slice is vendor-neutral and already enforces:

- Weekly Sync: $250/month, one delivery per week, maximum 15 fields
- Daily Sync: $500/month, five deliveries per week, maximum 15 fields
- AI / Heavy Extraction: $850/month, daily delivery, maximum 25 fields
- Full Buyout: $1,500 one-time payment, no automatic subscription
- 50% setup deposit before development and 50% final setup payment after QA preview
- QA score of at least 95% and exactly 25 preview rows before escrow
- Verified payment events before provisioning or delivery
- Idempotent payment webhook processing
- Prospect sandbox slugs, interaction events, field selection, and CSV export
- PayPal checkout metadata generated only after an approved SOW
- PayPal webhook verification and replay-safe event dispatch

See [docs/lead-lifecycle.md](docs/lead-lifecycle.md) and [docs/lead-schema.json](docs/lead-schema.json) for the domain contract.

The Azure deployment boundary, done/not-done status, release gates, and operating process are documented in [docs/azure-readiness-and-operating-model.md](docs/azure-readiness-and-operating-model.md). The current gate is conditional for staging preparation and no-go for production until the live Azure checks in that document are evidenced.

## Run tests

```powershell
python -m unittest discover -s tests -v
```

The portal service currently lives in [agents/portal.py](agents/portal.py) and is framework-neutral so it can be connected to the eventual web API. PayPal verification is implemented in [agents/paypal.py](agents/paypal.py); it requires server-side PayPal client credentials and a webhook ID, which are intentionally not stored in this repository. The next integration slice is Azure Logic Apps/Container Apps Jobs adapters.

The files in `agents/` currently provide domain services and tools. The LLM workers themselves are defined separately by role, instructions, typed tools, escalation rules, and durable task state. See [agents/README.md](agents/README.md) for the agent boundary and responsibilities.

The first real LLM implementation is scaffolded at [agents/llm/leadops-agents](agents/llm/leadops-agents): Scout records evidence-backed research, Intake creates the prefilled confirmation form, and the coordinator delegates between them. Run its deterministic tests with `uv run --project agents/llm/leadops-agents pytest agents/llm/leadops-agents/tests/unit -q`.

The build loop is implemented in [agents/build_loop.py](agents/build_loop.py): Planner -> Dev Lead -> Builder Team -> independent QA Gatekeeper. QA failures route back to planning; only a score of 95 or higher unlocks escrow.

Docker Ollama connectivity is available through [workers/ollama_smoke.py](agents/llm/leadops-agents/workers/ollama_smoke.py), using host port `11435`. The direct runner is the fast local smoke path; Antigravity remains the full agent orchestration path.

Server-side PayPal Checkout order creation is implemented in [agents/paypal_checkout.py](agents/paypal_checkout.py). It creates a 50% setup order with an explicit `deposit` or `buyout` purpose; it never marks the lead paid. Only a verified PayPal webhook can do that.

After QA reaches escrow, `create_final_order()` creates the remaining 50% balance order with `custom_id=final`. Delivery remains locked until the verified `final.paid` webhook advances the lead.

PayPal settings are loaded from environment variables through [agents/paypal_config.py](agents/paypal_config.py). Copy `.env.example` to `.env` only after rotating the exposed sandbox secret; `.env` is ignored by Git. Sandbox mode uses `https://api-m.sandbox.paypal.com`.

Recurring billing metadata is defined in [agents/subscriptions.py](agents/subscriptions.py). Configure `PAYPAL_PLAN_ID_WEEKLY`, `PAYPAL_PLAN_ID_DAILY`, and `PAYPAL_PLAN_ID_AI` with PayPal sandbox plan IDs. The module prepares activation only after delivery and never treats preparation as confirmed billing.

The standard-library PayPal transport is [agents/paypal_http.py](agents/paypal_http.py). It can be passed to `PayPalCheckout.from_environment()` or `PayPalWebhookAdapter.from_environment()` and does not log authorization headers.

Webhook routing is implemented in [agents/paypal_webhook.py](agents/paypal_webhook.py). It resolves `setup-{lead_id}`, `final-{lead_id}`, or `lead:{lead_id}` metadata to a known lead before allowing the verified event to mutate lifecycle state.

The local portal's **Deploy Feed** action now calls scope approval and the checkout boundary. Without PayPal credentials it remains a safe metadata dry run; real PayPal JS capture is the next credential-dependent step.

The Scout-to-portal handoff is implemented in [agents/scout_pipeline.py](agents/scout_pipeline.py). It requires the sample source URL to appear in Scout evidence before publishing a sandbox and prefilled intake form.

The local API accepts the same handoff at `POST /api/scout/candidate` and returns the generated slug and intake assumptions. It is intended for local integration testing; production will add authentication and durable storage.

The free local Builder Team runner is [agents/job_runner.py](agents/job_runner.py). It executes specialist handlers and produces a QA handoff manifest without creating cloud resources.

The complete local build orchestration is [agents/workflow.py](agents/workflow.py): verified deposit, planning, Dev Lead coordination, specialist execution, artifact handoff, independent QA, and escrow/replan routing.

Customer-safe build progress is represented by [agents/progress.py](agents/progress.py), which can feed the portal progress bar without leaking agent internals.

Run the local browser demo with:

```powershell
python -c "from agents.local_portal import run; run()"
```

Then open `http://127.0.0.1:8765/`. The demo includes the seeded sandbox, confirmation-first intake, sample data, CSV export, and progress API.

Delivery logic is implemented without cloud dependencies in [agents/delivery.py](agents/delivery.py). Keep early pilots inexpensive by using a local or single managed database, a free-tier destination, and a scheduled GitHub Actions workflow or Azure Functions Consumption timer. Move to Azure Logic Apps and Container Apps Jobs only when volume, reliability, or compliance requires them; both can still scale down, but neither should be assumed free.

Cloud placement is represented by [agents/provisioning.py](agents/provisioning.py): Azure is the default production provider for using your student credits, while DigitalOcean is staging-only until production controls are approved. Provisioning creates a plan but does not create cloud resources or expose secrets.

Cloud Antigravity agents use `GEMINI_API_KEY` from the environment. Add the replacement key locally after creating one at [Google AI Studio](https://aistudio.google.com/app/api-keys); never paste it into source files or commit it.

