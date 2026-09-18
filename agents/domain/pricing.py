"""Tier definitions, pricing constants, and aliases for LeadOps."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Tier:
    name: str
    price_cents: int
    cadence: str
    max_fields: int
    delivery: str
    recurring: bool = True


TIERS: dict[str, Tier] = {
    "weekly": Tier("Weekly Sync", 25_000, "monthly", 15, "1x weekly"),
    "daily": Tier("Daily Sync", 50_000, "monthly", 15, "5x weekly"),
    "ai": Tier("AI / Heavy Extraction", 85_000, "monthly", 25, "daily"),
}

BUYOUT = Tier("Full Buyout", 150_000, "one_time", 25, "client-owned", False)

TIER_ALIASES: dict[str, str] = {
    "a": "daily",
    "tier_a": "daily",
    "tier-a": "daily",
    "tier a": "daily",
    "tier 1": "daily",
    "b": "weekly",
    "tier_b": "weekly",
    "tier-b": "weekly",
    "tier b": "weekly",
    "tier 2": "weekly",
    "c": "weekly",
    "tier_c": "weekly",
    "tier-c": "weekly",
    "tier c": "weekly",
    "tier 3": "weekly",
    "standard": "weekly",
    "starter": "weekly",
    "basic": "weekly",
    "pro": "daily",
    "growth": "daily",
    "enterprise": "ai",
    "heavy": "ai",
}

__all__ = ["Tier", "TIERS", "BUYOUT", "TIER_ALIASES"]
