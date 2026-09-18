"""Strategic Outbound Playbooks & Campaign Blueprints for LeadOps.

Contains production-ready copy templates, LinkedIn connection formulas,
referral amplification engines, and channel-specific hooks for:
1. County Filing Party Sequence (Proof-first, docket-specific)
2. State Bar Attorney Sequence (Practice-area targeted)
3. Secretary of State New Entity Launch Sequence (Operational onboarding)
4. Local Title & Escrow Agency Sequence (City/County regional dominance)
5. LinkedIn Manual Outreach Habit (10/day curiosity formula)
6. Referral Amplification Engine (Delivery #3 trigger)
"""

from typing import Any


def format_county_filing_pitch(
    contact_name: str,
    company_name: str,
    portal_name: str,
    case_number: str,
    sandbox_url: str,
) -> dict[str, str]:
    """Generate sub-50-word curiosity outreach hook referencing their exact docket filing."""
    clean_first = contact_name.split()[0] if contact_name and contact_name != "Operations Director" else "Team"
    case_mention = f"matter #{case_number}" if case_number else "recent court dockets"
    short_portal = portal_name.split()[0].lower()

    subject = f"{short_portal} filings for {company_name.split()[0]}"
    body = (
        f"Hi {clean_first},\n\n"
        f"Saw your firm filed {case_mention} in {portal_name}.\n\n"
        f"Curious — does your staff still pull new daily dockets manually? "
        f"We built an automated feed that extracts newly posted filings every morning at 8 AM.\n\n"
        f"Live preview for your team:\n"
        f"{sandbox_url}\n\n"
        f"Worth a quick look?\n"
        f"Alex | LeadOps Automation Engineering"
    )
    return {"subject": subject, "body": body}


def format_state_bar_pitch(
    contact_name: str,
    firm_name: str,
    practice_area: str,
    bar_name: str,
    portal_name: str,
    sandbox_url: str,
) -> dict[str, str]:
    """Generate practice-area targeted pitch for State Bar directory attorneys."""
    clean_first = contact_name.split()[0] if contact_name else "Counsel"
    short_practice = practice_area.split()[0].lower()

    subject = f"{short_practice} docket feeds for {firm_name.split()[0]}"
    body = (
        f"Hi {clean_first},\n\n"
        f"Saw your practice listed with {bar_name} focusing on {practice_area}.\n\n"
        f"Curious — how does your team track newly filed petitions and asset recordings in {portal_name}? "
        f"We build automated feeds that deliver newly indexed filings directly to your team each morning.\n\n"
        f"Here is an interactive preview configured for your jurisdiction:\n"
        f"{sandbox_url}\n\n"
        f"Worth a 2-minute look?\n"
        f"Alex | LeadOps Automation Engineering"
    )
    return {"subject": subject, "body": body}


def format_sos_new_business_pitch(
    contact_name: str,
    company_name: str,
    entity_type: str,
    state: str,
    portal_name: str,
    sandbox_url: str,
) -> dict[str, str]:
    """Generate operational onboarding pitch for newly registered commercial businesses."""
    clean_first = contact_name.split()[0] if contact_name and contact_name != "Operations Director" else "Team"

    subject = f"{entity_type.lower()} records feed for {company_name.split()[0]}"
    body = (
        f"Hi {clean_first},\n\n"
        f"Saw {company_name} registered for {entity_type} operations in {state}.\n\n"
        f"Curious — as you ramp up operations, does your team plan to pull public property and lien records from {portal_name} manually? "
        f"We build automated feeds that deliver newly filed dockets straight to your pipeline daily at 8 AM.\n\n"
        f"Interactive preview for your jurisdiction:\n"
        f"{sandbox_url}\n\n"
        f"Worth a quick look as you set up operations?\n"
        f"Alex | LeadOps Automation Engineering"
    )
    return {"subject": subject, "body": body}


def format_linkedin_connection_note(
    contact_name: str,
    niche: str,
    county_or_portal: str,
) -> str:
    """Generate sub-300-character non-salesy LinkedIn connection request."""
    clean_first = contact_name.split()[0] if contact_name else "there"
    return (
        f"Hey {clean_first}, curious — does your team still pull {county_or_portal} "
        f"records manually? Building an automated morning docket feed for {niche} firms and "
        f"wanted to connect."
    )


def format_referral_amplification_ask(
    client_name: str,
    client_company: str,
    state_or_metro: str,
    shareable_sandbox_url: str,
) -> dict[str, str]:
    """Generate delivery #3 referral ask with specific tangible incentive."""
    clean_first = client_name.split()[0] if client_name else "there"
    subject = f"Quick question about other title offices in {state_or_metro}"
    body = (
        f"Hi {clean_first},\n\n"
        f"Your automated data feed has been running smoothly across the last 3 scheduled deliveries.\n\n"
        f"Quick favor — know another title company or estate firm in {state_or_metro} that still spends hours "
        f"pulling public dockets manually?\n\n"
        f"If you introduce us, we'll credit a **free month of daily data feeds** to your account for every team that signs on.\n\n"
        f"You can forward them this link to check out how it works:\n"
        f"{shareable_sandbox_url}\n\n"
        f"Appreciate you,\n"
        f"Alex | LeadOps Automation Engineering"
    )
    return {"subject": subject, "body": body}
