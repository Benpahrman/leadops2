"""
agents/llm/buyer_gate.py - Gatekeeper and heuristic filters for disallowed buyers.
Prevents prospecting municipal agencies, courts, or enterprise tech giants that build in-house.
"""
from typing import Set

DISALLOWED_BUYER_DOMAINS: Set[str] = {
    ".gov", ".mil", ".fed.us", ".state.us", "austintexas.gov", "hctx.net", "state.tx.us",
    "cookcountyclerkofcourt.org", "cookcountycourt.com", "occompt.com", "tmb.state.tx.us",
    "sam.gov", "usps.gov", "irs.gov", "court.gov",
    "dictionary.cambridge.org", "merriam-webster.com", "wikipedia.org", "wiktionary.org",
    "investopedia.com", "thefreedictionary.com", "britannica.com", "collinsdictionary.com",
    "dictionary.com",
    # Big tech giants & massive software corporations (build in-house solutions)
    "google.com", "alphabet.com", "microsoft.com", "apple.com", "amazon.com", "meta.com", "facebook.com",
    "oracle.com", "ibm.com", "salesforce.com", "intel.com", "cisco.com", "adobe.com", "netflix.com",
    "uber.com", "lyft.com", "twitter.com", "x.com", "airbnb.com", "stripe.com", "palantir.com",
    "snowflake.com", "databricks.com", "sap.com", "workday.com", "servicenow.com", "intuit.com",
    "atlassian.com",
    # Mega conglomerates & Fortune 50 multinationals
    "accenture.com", "deloitte.com", "mckinsey.com", "kpmg.com", "ey.com", "pwc.com",
    "boeing.com", "lockheedmartin.com", "raytheon.com", "ge.com", "walmart.com", "target.com",
    "costco.com", "homedepot.com", "jpmorgan.com", "chase.com", "goldmansachs.com",
    "bankofamerica.com", "wellsfargo.com", "citi.com", "citigroup.com", "morganstanley.com",
    "pnc.com", "berkshirehathaway.com", "tesla.com"
}

DISALLOWED_BUYER_KEYWORDS: Set[str] = {
    "city of", "county of", "state of", "town of", "village of", "borough of", "commonwealth of",
    "department of", "dept of", "division of", "bureau of", "board of", "commission of",
    "district court", "circuit court", "municipal court", "probate court", "clerk of court",
    "county clerk", "district clerk", "tax assessor", "sheriff", "police department", "fire department",
    "secretary of state", "open data", "public records office", "government", "municipality",
    "school district", "isd", "university of",
    "definition", "meaning of", "synonyms of", "pronunciation of",
    # Enterprise & Big Tech Giants (likely have in-house data/scraping engineering teams)
    "google", "alphabet", "microsoft", "apple inc", "amazon.com", "meta platforms", "facebook inc",
    "oracle corp", "ibm corp", "salesforce", "intel corp", "cisco systems", "adobe inc", "netflix",
    "uber technologies", "lyft inc", "palantir", "snowflake inc", "databricks", "sap se", "workday",
    "servicenow", "atlassian", "accenture", "deloitte", "mckinsey", "kpmg", "ernst & young", "pwc",
    "pricewaterhousecoopers", "boeing", "lockheed martin", "raytheon", "general electric", "walmart",
    "target corp", "jpmorgan chase", "goldman sachs", "bank of america", "wells fargo", "citigroup",
    "morgan stanley", "berkshire hathaway", "pnc bank", "pnc financial"
}


def is_disallowed_buyer(company_name: str = "", domain: str = "", email: str = "") -> bool:
    """Return True if entity is a government agency, court, municipality, or non-commercial source."""
    name_l = (company_name or "").lower().strip()
    dom_l = (domain or "").lower().strip()
    email_l = (email or "").lower().strip()

    if any(dom_l.endswith(d) or f"{d}/" in dom_l or f"@{d}" in email_l or email_l.endswith(d) for d in [".gov", ".mil", ".fed.us", ".state.us"]):
        return True

    for kw in DISALLOWED_BUYER_KEYWORDS:
        if kw in name_l or kw in dom_l:
            return True

    for dom in DISALLOWED_BUYER_DOMAINS:
        if dom in dom_l or dom in email_l:
            return True

    return False


class BuyerGateMixin:
    """Mixin for buyer qualification gating."""

    @staticmethod
    def is_disallowed_buyer(company_name: str = "", domain: str = "", email: str = "") -> bool:
        return is_disallowed_buyer(company_name, domain, email)
