# LeadOps Lifecycle

## Commercial contract

| Offer | Price | Billing | Delivery | Field limit |
| --- | ---: | --- | --- | ---: |
| Weekly Sync | $250 | Monthly PayPal subscription | 1x weekly | 15 |
| Daily Sync | $500 | Monthly PayPal subscription | 5x weekly | 15 |
| AI / Heavy Extraction | $850 | Monthly PayPal subscription | Daily | 25 |
| Full Buyout | $1,500 | One-time PayPal payment | Client-owned | 25 |

Setup work is billed 50% before development and 50% after QA preview approval. A recurring service subscription starts only after the final setup payment is confirmed. The buyout has no automatic subscription.

## States

`PROSPECTING` -> `REVIEW` -> `PITCH_PENDING_APPROVAL` -> `OUTREACH_SENT` -> `CONVERSATIONAL_INTAKE` -> `SOW_GENERATED` -> `DEPOSIT_PAID` -> `DEV_BUILDING` -> `ESCROW_PREVIEW` -> `FINAL_PAID` -> `DELIVERED` -> `WARRANTY_ACTIVE` -> `WARRANTY_EXPIRED`.

`ARCHIVED` is a terminal state available from any active state when a lead opts out, is rejected, or is closed.

## Gates and triggers

- Outreach requires human approval and an opt-out check.
- `deposit.paid` must be received from a verified PayPal webhook before provisioning and development begin.
- QA must be at least 95%, and the escrow preview must contain exactly 25 rows.
- Build execution follows `Planner -> Dev Lead -> Builder Team -> QA Gatekeeper`. Dev Lead creates role-owned work items, and the Builder Team submits evidence for each role. The QA Gatekeeper is independent and computes its score from that evidence; failed QA returns concrete feedback to Planner for another iteration and cannot unlock escrow.
- `final.paid` or `buyout.paid` must be received from a verified PayPal webhook before delivery.
- The final balance order is available only after `ESCROW_PREVIEW`; creating that order does not mark payment complete.
- Webhook routing resolves PayPal invoice/custom metadata to a known lead before signature verification and lifecycle mutation; unknown lead IDs are rejected.
- `subscription.active` is accepted only after delivery and never for a buyout.
- Capture webhooks must carry `custom_id` set to `deposit`, `final`, or `buyout`; unknown payment purposes are rejected.
- The `Deploy Feed` action creates a server-side PayPal Checkout order only after SOW generation. The order carries `custom_id=deposit` or `custom_id=buyout`; browser approval is not payment confirmation.
- After delivery, the selected recurring tier uses its configured PayPal plan ID. Subscription preparation is not activation; only a verified PayPal subscription webhook may set the subscription active. The Full Buyout has no recurring plan.
- Delivery runs through the Azure 6:00 AM schedule and targets completion by 8:00 AM.
- The initial low-cost deployment may use a scheduled GitHub Actions workflow or Azure Functions Consumption timer calling the same delivery contract; no always-on worker is required.
- Verified deposit payment creates an auditable provisioning plan. Azure is the default production provider; DigitalOcean may host staging while the system is being tested. Cloud adapters must receive secrets from a secret manager and must not embed credentials in job definitions.
- The Day-7 warranty offer can activate the $250/month Drift Shield subscription after confirmed PayPal subscription activation.

## Prefilled intake experience

The intake page is a confirmation flow, not a blank form. Scout supplies the initial assumptions for business type, jurisdiction, portal, portal URL, suggested fields, recommended plan, and delivery destination. Each assumption is editable and displays its research source and confidence.

The primary action should be a simple confirmation such as **Looks right, continue**. Corrections should be available inline. Keep optional details collapsed until the prospect confirms the core assumptions, and ask only for information that research could not establish. Never present an uncertain research guess as a confirmed customer requirement.

## Failure handling

Failed jobs are retried with an idempotency key and then placed in a dead-letter queue for operator review. A CAPTCHA, WAF, authentication wall, or prohibited source access pauses the workflow; the system does not attempt to bypass it. Payment redirects are informational only. Webhook verification and replay protection are mandatory.

Every state change, portal interaction, payment event, worker result, source URL, retrieval time, QA score, and delivery acknowledgement is audit logged.