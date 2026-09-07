"""Vendor-neutral lifecycle and pricing rules for LeadOps."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class State(str, Enum):
    PROSPECTING = "PROSPECTING"
    REVIEW = "REVIEW"
    PITCH_PENDING_APPROVAL = "PITCH_PENDING_APPROVAL"
    OUTREACH_SENT = "OUTREACH_SENT"
    CONVERSATIONAL_INTAKE = "CONVERSATIONAL_INTAKE"
    SOW_GENERATED = "SOW_GENERATED"
    DEPOSIT_PAID = "DEPOSIT_PAID"
    DEV_BUILDING = "DEV_BUILDING"
    BLOCKED_NEEDS_REVIEW = "BLOCKED_NEEDS_REVIEW"
    ESCROW_PREVIEW = "ESCROW_PREVIEW"
    FINAL_PAID = "FINAL_PAID"
    DELIVERED = "DELIVERED"
    WARRANTY_ACTIVE = "WARRANTY_ACTIVE"
    WARRANTY_EXPIRED = "WARRANTY_EXPIRED"
    WARRANTY_RENEWAL = "WARRANTY_RENEWAL"
    ARCHIVED = "ARCHIVED"


class PaymentEvent(str, Enum):
    DEPOSIT_PAID = "deposit.paid"
    FINAL_PAID = "final.paid"
    SUBSCRIPTION_ACTIVE = "subscription.active"
    BUYOUT_PAID = "buyout.paid"


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


ALLOWED_TRANSITIONS = {
    State.PROSPECTING: {State.REVIEW, State.PITCH_PENDING_APPROVAL, State.BLOCKED_NEEDS_REVIEW, State.ARCHIVED},
    State.REVIEW: {State.PITCH_PENDING_APPROVAL, State.CONVERSATIONAL_INTAKE, State.BLOCKED_NEEDS_REVIEW, State.ARCHIVED},
    State.PITCH_PENDING_APPROVAL: {State.OUTREACH_SENT, State.ARCHIVED},
    State.OUTREACH_SENT: {State.CONVERSATIONAL_INTAKE, State.ARCHIVED},
    State.CONVERSATIONAL_INTAKE: {State.SOW_GENERATED, State.ARCHIVED},
    State.SOW_GENERATED: {State.DEPOSIT_PAID, State.ARCHIVED},
    State.DEPOSIT_PAID: {State.DEV_BUILDING, State.ARCHIVED},
    State.DEV_BUILDING: {State.ESCROW_PREVIEW, State.BLOCKED_NEEDS_REVIEW, State.ARCHIVED},
    State.BLOCKED_NEEDS_REVIEW: {State.DEV_BUILDING, State.REVIEW, State.ARCHIVED},
    State.ESCROW_PREVIEW: {State.FINAL_PAID, State.DEV_BUILDING, State.ARCHIVED},
    State.FINAL_PAID: {State.DELIVERED, State.ARCHIVED},
    State.DELIVERED: {State.WARRANTY_ACTIVE, State.ARCHIVED},
    State.WARRANTY_ACTIVE: {State.WARRANTY_EXPIRED, State.ARCHIVED},
    State.WARRANTY_EXPIRED: {State.WARRANTY_RENEWAL, State.ARCHIVED},
    State.WARRANTY_RENEWAL: {State.WARRANTY_ACTIVE, State.ARCHIVED},
    State.ARCHIVED: set(),
}


class InvalidTransition(ValueError):
    """Raised when a lifecycle transition violates the domain contract."""


@dataclass
class Lead:
    lead_id: str
    tier_key: str
    state: State = State.PROSPECTING
    selected_fields: list[str] = field(default_factory=list)
    qa_score: float | None = None
    preview_rows: int = 0
    deposit_paid: bool = False
    final_paid: bool = False
    subscription_active: bool = False
    buyout_paid: bool = False
    audit_log: list[dict[str, str]] = field(default_factory=list)
    company_name: str = ""
    contact_name: str = ""
    contact_role: str = ""
    contact_email: str = ""
    contact_phone: str = ""
    decision_maker_linkedin: str = ""
    target_portal_name: str = ""
    estimated_monthly_records: int = 500
    source_url: str = ""
    jurisdiction: str = ""
    slug: str = ""
    outreach_subject: str = ""
    outreach_body: str = ""
    repo_url: str = ""
    niche: str = ""
    delivery_count: int = 0
    last_login_at: str = ""
    created_at: str = ""
    upsell_sent: bool = False
    referral_sent: bool = False
    winback_stage: int = 0  # 0=not started, 1/2/3=email sent, 4=completed
    heartbeat_count: int = 0
    referred_by: str = ""
    claimed_by: str = ""
    is_paused: bool = False
    paused_until: str = ""
    paypal_vault_id: str = ""
    subscription_id: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        now_str = datetime.now(timezone.utc).isoformat()
        if not self.created_at:
            self.created_at = now_str
        if not self.updated_at:
            self.updated_at = now_str
        raw = (self.tier_key or "").strip().lower()
        if raw in TIER_ALIASES:
            self.tier_key = TIER_ALIASES[raw]
        elif raw in TIERS or raw == "buyout":
            self.tier_key = raw
        elif not self.tier_key:
            self.tier_key = "weekly"

    @property
    def tier(self) -> Tier:
        raw = (self.tier_key or "").strip().lower()
        if raw in ("buyout", "full_buyout", "full buyout", "client-owned"):
            return BUYOUT
        if raw in TIERS:
            return TIERS[raw]
        if raw in TIER_ALIASES:
            return TIERS[TIER_ALIASES[raw]]
        return TIERS["weekly"]

    def transition(self, target: State, reason: str) -> None:
        previous_state = self.state
        if target not in ALLOWED_TRANSITIONS[self.state]:
            raise InvalidTransition(f"{self.state.value} -> {target.value} is not allowed")
        if target == State.ESCROW_PREVIEW:
            if self.qa_score is None or self.qa_score < 95:
                raise InvalidTransition("QA score must be at least 95 before escrow preview")
            if self.preview_rows != 25:
                raise InvalidTransition("Escrow preview must contain exactly 25 rows")
        if target == State.DELIVERED and not self.final_paid and not self.buyout_paid:
            raise InvalidTransition("Final payment or buyout payment is required before delivery")
        self.state = target
        self.audit_log.append({
            "from": previous_state.value,
            "to": target.value,
            "reason": reason,
            "at": datetime.now(timezone.utc).isoformat(),
        })

    def record_payment(self, event: PaymentEvent) -> None:
        if event == PaymentEvent.DEPOSIT_PAID:
            self.deposit_paid = True
            self.transition(State.DEPOSIT_PAID, event.value)
        elif event == PaymentEvent.FINAL_PAID:
            self.final_paid = True
            self.transition(State.FINAL_PAID, event.value)
        elif event == PaymentEvent.SUBSCRIPTION_ACTIVE:
            if self.tier_key == "buyout":
                raise InvalidTransition("Buyout customers do not receive a service subscription")
            if self.state != State.DELIVERED:
                raise InvalidTransition("Subscription starts after delivery")
            self.subscription_active = True
        elif event == PaymentEvent.BUYOUT_PAID:
            self.buyout_paid = True
            if self.state == State.ESCROW_PREVIEW:
                self.transition(State.FINAL_PAID, event.value)

    def select_fields(self, fields: list[str]) -> None:
        if not fields or len(fields) > self.tier.max_fields:
            raise ValueError(f"{self.tier.name} supports 1-{self.tier.max_fields} fields")
        self.selected_fields = list(dict.fromkeys(fields))