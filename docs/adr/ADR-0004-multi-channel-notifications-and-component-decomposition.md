# ADR-0004: Multi-Channel Notifications Architecture & React Component Decomposition

* **Status:** Accepted
* **Date:** 2026-09-16
* **Deciders:** LeadOps Core Engineering Team, Swarm Architect
* **Consulted:** DevOps, Frontend Lead, QA Gatekeeper
* **Informed:** Swarm Operators

---

##  Context & Problem Statement

As LeadOps expanded to autonomous swarm execution, two critical architectural monoliths introduced significant maintenance friction and cognitive overload:

1. **Backend Notification Monolith (`agents/notifications.py`, 1,533 LOC)**:
   - Contained settings, rich Discord embed generators, Telegram bot handlers, and event dispatch logic within a single file.
   - Handled mission-critical business alerts (deal intake, $99 sprint deposits, QA verification releases, 24-hour SLA breaches, deliverability audits) with tight coupling.
   - Was imported across 11 core modules, making modifications risky without strong architectural boundaries.

2. **Frontend Admin Page Monolith (`frontend/src/pages/AdminPage.jsx`, 3,154 LOC)**:
   - Contained over 1,000 lines of inline JSX modals (AI scoring radar, dataset inspector, audit trail, founder QA override, swarm progress telemetry, SpamAssassin reports) mixed with page layout and data fetching logic.
   - Hindered reusability, testing, and component lifecycle profiling.

---

## Decision Drivers

* **Zero Breaking Changes**: Must maintain 100% backward compatibility for all existing callers across the backend and frontend.
* **Separation of Concerns**: Separate channel-specific message encoding (Discord embeds vs. Telegram Markdown) from business event triggers.
* **Component-Level Modularity**: Encapsulate interactive modals into dedicated, testable React components.
* **Strict Test Parity**: Ensure zero regressions across existing test harnesses (`test_notifications_and_quality_gate.py`, `test_email_module.py`, `test_admin_ops.py`, Vite build).

---

## Considered Alternatives

1. **Keep monolithic files**: Maintain single files to minimize directory count.
   - *Rejected*: Exceeds the 400-line modularity threshold, creates Git merge conflicts, and slows down automated audits.
2. **Break backward compatibility**: Rename imports directly across all 11 caller files.
   - *Rejected*: Violates [ADR-0002](file:///c:/Users/ben/Documents/leadops2/docs/adr/ADR-0002-strangler-fig-modularization-protocol.md) Strangler Fig protocol; high regression risk.

---

## Decision Outcome

Adopt a two-pronged modularization strategy:

### 1. Backend: Domain Package `agents/notifications/`
* Deconstruct `agents/notifications.py` into a cohesive domain package:
  * `settings.py`: `NotificationSettings` configuration and environment resolution.
  * `discord.py`: `DiscordNotifier` class and embed generation.
  * `telegram.py`: `TelegramNotifier` class and HTML/Markdown messaging.
  * `manager.py`: `NotificationManager` thread-safe dispatching and event telemetry.
  * `__init__.py`: Barrel facade exporting `NotificationManager`, `NotificationSettings`, `DiscordNotifier`, `TelegramNotifier`, and the global `notification_manager` singleton.

### 2. Frontend: Dedicated Modal Components `frontend/src/pages/admin/modals/`
* Extract inline modal JSX from `AdminPage.jsx` into standalone components:
  * `CodeViewerModal.jsx`: Python scraper source inspector.
  * `DatasetRecordsModal.jsx`: Extracted records table and JSON export.
  * `AuditTrailModal.jsx`: Immutable event timeline and actor history.
  * `QAOverrideModal.jsx`: Founder QA release override dialog.
  * `SwarmProgressModal.jsx`: Real-time build telemetry and logs.
  * `LeadScoringModal.jsx`: 7-factor BDR weighted opportunity radar and Alex objection playbook.
  * `SpamReportModal.jsx`: SpamAssassin 4-vector deliverability breakdown.
  * `index.js`: Clean barrel export.

---

## Consequences & Trade-offs

### Positive Consequences
* **Line Count Reduction**: `frontend/src/pages/AdminPage.jsx` dropped from 3,154 LOC to 2,129 LOC (-1,025 LOC).
* **Isolation**: Discord and Telegram transport layers can be modified, mocked, or extended without touching core business event routines.
* **Reusability**: Extracted modals can now be embedded in other operational views (e.g., customer support dashboard, pipeline review) with zero duplication.
* **Test Parity**: 100% of existing tests pass (`44 passed in 92.90s`), and Vite build compiles in <1s.

### Negative Consequences / Trade-offs
* Additional files to navigate in `frontend/src/pages/admin/modals/` and `agents/notifications/`.

---

## Verification & Validation

1. **Unit & Integration Tests**:
   - `pytest tests/test_notifications_and_quality_gate.py tests/test_email_module.py -q` $\rightarrow$ 100% passed.
   - `pytest tests/test_admin_ops.py tests/test_deliverability_audit.py -q` $\rightarrow$ 100% passed.
2. **Frontend Production Build**:
   - `npm run build` in `frontend/` $\rightarrow$ 155 modules transformed, 0 errors.
