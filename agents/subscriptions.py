"""Recurring LeadOps plan metadata for PayPal subscription activation."""

import os
from dataclasses import dataclass

from .domain import BUYOUT, TIERS, Lead, State


@dataclass(frozen=True)
class SubscriptionPlan:
    tier_key: str
    name: str
    amount_cents: int
    paypal_plan_id: str


def subscription_plan(tier_key: str) -> SubscriptionPlan:
    """Return recurring plan metadata; reject the one-time buyout."""
    if tier_key == "buyout":
        raise ValueError(f"{BUYOUT.name} does not have recurring billing")
    try:
        tier = TIERS[tier_key]
    except KeyError as error:
        raise ValueError(f"Unknown subscription tier: {tier_key}") from error
    plan_id = os.getenv(f"PAYPAL_PLAN_ID_{tier_key.upper()}", "")
    return SubscriptionPlan(tier_key, tier.name, tier.price_cents, plan_id)


def subscription_activation(lead: Lead) -> dict[str, str]:
    """Prepare activation data after delivery; do not claim activation."""
    if lead.state != State.DELIVERED:
        raise ValueError("Subscription activation requires delivered work")
    plan = subscription_plan(lead.tier_key)
    if not plan.paypal_plan_id:
        raise ValueError(f"Missing PayPal plan ID for {lead.tier_key}")
    return {
        "lead_id": lead.lead_id,
        "paypal_plan_id": plan.paypal_plan_id,
        "tier": plan.name,
        "amount": f"{plan.amount_cents / 100:.2f}",
        "activation_confirmed": "false",
    }