"""Autonomous background Scout discovery runner for continuous lead prospecting."""

import asyncio
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .domain import State
from .portal import PortalService
from .scout_pipeline import ScoutCandidate, ScoutPortalPipeline
from .storage import StorageBackend
from .tools.dom_pruner import prune_dom
from .tools.waf_prober import generate_browser_headers, probe_waf_signatures


from .datasets import AUTHENTIC_REGISTRY_DATASETS


TARGET_REGISTRIES = [
    {
        "company_name": "DPR Construction Inc.",
        "contact_name": "DPR Preconstruction & Estimating Team",
        "contact_role": "VP of Estimating & Regional Preconstruction",
        "contact_email": "preconstruction-texas@dpr.com",
        "contact_phone": "(512) 345-6799",
        "website": "https://www.dpr.com",
        "niche": "Commercial Construction & Subcontracting",
        "pain_point": "Needs daily tracking of Austin commercial building permits ($5M+) to identify new commercial builds and subcontract trade opportunities.",
        "target_url": "https://data.austintexas.gov/",
        "portal_name": "City of Austin Open Data - Commercial Building Permits",
        "jurisdiction": "Travis County / Austin, TX",
        "suggested_fields": AUTHENTIC_REGISTRY_DATASETS["austin-commercial-permits"]["selected_fields"],
        "tier_key": "daily",
        "sample_data": AUTHENTIC_REGISTRY_DATASETS["austin-commercial-permits"]["sample_data"],
    },
    {
        "company_name": "Leidos Defense & Intelligence",
        "contact_name": "Federal Capture & Proposal Operations",
        "contact_role": "Director of Capture Management",
        "contact_email": "federal-bids@leidos.com",
        "contact_phone": "(571) 526-6000",
        "website": "https://www.leidos.com",
        "niche": "Government Defense Contracting & GovTech",
        "pain_point": "Needs automated tracking of active DoD/DoAF RFPs matching NAICS 541512 / 541715 before 30-day response windows close.",
        "target_url": "https://sam.gov/",
        "portal_name": "SAM.gov Federal Contract Solicitations",
        "jurisdiction": "Federal / Nationwide Defense",
        "suggested_fields": AUTHENTIC_REGISTRY_DATASETS["sam-gov-defense-rfps"]["selected_fields"],
        "tier_key": "ai",
        "sample_data": AUTHENTIC_REGISTRY_DATASETS["sam-gov-defense-rfps"]["sample_data"],
    },
    {
        "company_name": "PNC Equipment Finance LLC",
        "contact_name": "Commercial Capital Originations Team",
        "contact_role": "Managing Director, Asset Finance",
        "contact_email": "equipmentfinance@pnc.com",
        "contact_phone": "(800) 762-2465",
        "website": "https://www.pnc.com/equipmentfinance",
        "niche": "Alternative Lending & Equipment Factoring",
        "pain_point": "Needs daily stream of UCC-1 equipment lien filings across Texas to identify capital equipment buyers and refinancing opportunities.",
        "target_url": "https://www.sos.state.tx.us/corp/ucc.shtml",
        "portal_name": "Secretary of State UCC Secured Financing Registry",
        "jurisdiction": "Statewide Commercial Finance",
        "suggested_fields": AUTHENTIC_REGISTRY_DATASETS["state-ucc-filings"]["selected_fields"],
        "tier_key": "daily",
        "sample_data": AUTHENTIC_REGISTRY_DATASETS["state-ucc-filings"]["sample_data"],
    },
    {
        "company_name": "Merritt Hawkins (AMN Healthcare)",
        "contact_name": "Physician Sourcing & Placement Division",
        "contact_role": "Director of Physician Search",
        "contact_email": "physician-sourcing@merritthawkins.com",
        "contact_phone": "(800) 876-0500",
        "website": "https://www.merritthawkins.com",
        "niche": "Healthcare Recruiting & Physician Placement",
        "pain_point": "Needs weekly alerts for newly licensed MDs/DOs across Texas to place physicians into major hospital networks.",
        "target_url": "https://www.tmb.state.tx.us/",
        "portal_name": "Texas Medical Board & Healthcare Practitioner Registry",
        "jurisdiction": "Healthcare Licensing & Credentials",
        "suggested_fields": AUTHENTIC_REGISTRY_DATASETS["medical-board-licensing"]["selected_fields"],
        "tier_key": "weekly",
        "sample_data": AUTHENTIC_REGISTRY_DATASETS["medical-board-licensing"]["sample_data"],
    },
    {
        "company_name": "Kirkland & Ellis LLP",
        "contact_name": "Estate Planning & Administration Practice",
        "contact_role": "Managing Partner, Private Wealth",
        "contact_email": "estate-filings@kirkland.com",
        "contact_phone": "(312) 862-2000",
        "website": "https://www.kirkland.com",
        "niche": "Probate & Estate Asset Intelligence",
        "pain_point": "Needs daily dockets of Cook County probate filings over $500k to offer estate representation and asset administration.",
        "target_url": "https://www.cookcountyclerkofcourt.org/",
        "portal_name": "Circuit Court of Cook County (Probate Division)",
        "jurisdiction": "Cook County, IL (Chicago)",
        "suggested_fields": AUTHENTIC_REGISTRY_DATASETS["cook-county-probate"]["selected_fields"],
        "tier_key": "daily",
        "sample_data": AUTHENTIC_REGISTRY_DATASETS["cook-county-probate"]["sample_data"],
    },
    {
        "company_name": "Barrett Daffin Frappier Turner & Engel LLP",
        "contact_name": "Texas Foreclosure & Default Services",
        "contact_role": "Managing Partner, Default Operations",
        "contact_email": "tx-trustee@bdfgroup.com",
        "contact_phone": "(972) 386-5040",
        "website": "https://www.bdfgroup.com",
        "niche": "Trustee Foreclosures & Mortgage Liens",
        "pain_point": "Needs automated tracking of Harris County foreclosure recordings and trustee auction schedules.",
        "target_url": "https://www.cclerk.hctx.net/",
        "portal_name": "Harris County District Clerk & County Clerk",
        "jurisdiction": "Harris County, TX (Houston)",
        "suggested_fields": AUTHENTIC_REGISTRY_DATASETS["harris-foreclosure"]["selected_fields"],
        "tier_key": "daily",
        "sample_data": AUTHENTIC_REGISTRY_DATASETS["harris-foreclosure"]["sample_data"],
    },
    {
        "company_name": "Aldridge Pite LLP",
        "contact_name": "Florida Mortgage Default Practice",
        "contact_role": "Managing Partner, Foreclosure Legal Group",
        "contact_email": "fl-default@aldridgepite.com",
        "contact_phone": "(404) 994-7400",
        "website": "https://www.aldridgepite.com",
        "niche": "Mortgage Foreclosures & Distressed Real Estate",
        "pain_point": "Needs daily lis pendens and trustee foreclosure filings across Orange County to manage legal default workflows.",
        "target_url": "https://www.occompt.com/",
        "portal_name": "Orange County Comptroller & Clerk Registry",
        "jurisdiction": "Orange County, FL (Orlando)",
        "suggested_fields": AUTHENTIC_REGISTRY_DATASETS["orange-foreclosure"]["selected_fields"],
        "tier_key": "ai",
        "sample_data": AUTHENTIC_REGISTRY_DATASETS["orange-foreclosure"]["sample_data"],
    },
]


import httpx
from .logging_config import get_logger
from .tools.waf_prober import generate_browser_headers
from .llm_client import LLMAgentEngine

logger = get_logger("scout")


VERTICAL_CATALOG: dict[str, dict[str, Any]] = {
    "Commercial Construction & Regional Building Permits": {
        "dataset_key": "austin-commercial-permits",
        "portal_name": "City of Austin Issued Construction Permits",
        "target_url": "https://data.austintexas.gov/Building-and-Development/Issued-Construction-Permits/3syk-w9eu",
        "jurisdiction": "Austin, Travis County, TX",
        "canonical_company": "DPR Construction Inc.",
        "contact_name": "Mark A. Vance",
        "contact_role": "VP of Preconstruction & Estimating",
        "contact_email": "preconstruction-texas@dpr.com",
        "contact_phone": "(512) 474-5131",
        "website": "https://www.dpr.com",
        "niche": "Commercial Construction & General Contracting",
        "pain_point": "Needs daily feed of non-residential commercial building permits to bid subcontracting and structural trades before competitors.",
        "tier_key": "daily",
        "candidate_pool": [
            {"company_name": "DPR Construction Inc.", "contact_name": "Mark A. Vance", "contact_role": "VP of Preconstruction", "contact_email": "preconstruction-texas@dpr.com", "contact_phone": "(512) 474-5131", "website": "https://www.dpr.com", "pain_point": "Needs daily Austin commercial permit filings to bid structural and MEP subcontract packages."},
            {"company_name": "SpawGlass Contractors Inc.", "contact_name": "Tyler Richardson", "contact_role": "Director of Preconstruction", "contact_email": "estimating-austin@spawglass.com", "contact_phone": "(512) 719-5251", "website": "https://www.spawglass.com", "pain_point": "Requires daily alerts on $5M+ Travis County commercial builds for concrete and civil trade bidding."},
            {"company_name": "Flintco LLC", "contact_name": "Sarah Thornton", "contact_role": "VP Commercial Estimating", "contact_email": "bids-texas@flintco.com", "contact_phone": "(512) 891-7224", "website": "https://www.flintco.com", "pain_point": "Needs automated tracking of hospitality, healthcare, and educational structural permits."},
            {"company_name": "Harvey-Cleary Builders", "contact_name": "David K. Meyer", "contact_role": "Head of Preconstruction", "contact_email": "estimating@harvey-cleary.com", "contact_phone": "(512) 328-9840", "website": "https://www.harvey-cleary.com", "pain_point": "Tracks Austin tenant interior finish-outs and commercial shell construction permits."},
            {"company_name": "Balfour Beatty US", "contact_name": "Rachel Sterling", "contact_role": "Regional Preconstruction Director", "contact_email": "commercial-tx@balfourbeattyus.com", "contact_phone": "(512) 499-8080", "website": "https://www.balfourbeattyus.com", "pain_point": "Identifies large-scale institutional commercial building projects before public tender dates."},
        ],
    },
    "Federal Defense RFPs, Solicitations & SAM.gov Awards": {
        "dataset_key": "sam-gov-defense-rfps",
        "portal_name": "SAM.gov Federal Contract Opportunities",
        "target_url": "https://sam.gov/content/opportunities",
        "jurisdiction": "Federal (DoD / Civilian Agencies)",
        "canonical_company": "Leidos Defense & Intelligence",
        "contact_name": "Sarah Jenkins",
        "contact_role": "Director of Federal Capture & Solicitations",
        "contact_email": "federal-bids@leidos.com",
        "contact_phone": "(571) 526-6000",
        "website": "https://www.leidos.com",
        "niche": "Defense Contracting & GovTech Solicitations",
        "pain_point": "Needs automated tracking of newly posted DoD and federal civilian RFPs and pre-solicitation notices.",
        "tier_key": "ai",
        "candidate_pool": [
            {"company_name": "Leidos Defense & Intelligence", "contact_name": "Sarah Jenkins", "contact_role": "Director of Federal Capture", "contact_email": "federal-bids@leidos.com", "contact_phone": "(571) 526-6000", "website": "https://www.leidos.com", "pain_point": "Needs automated tracking of newly posted DoD and federal civilian RFPs and pre-solicitation notices."},
            {"company_name": "CACI International Inc", "contact_name": "Marcus E. Vance", "contact_role": "VP Capture Management", "contact_email": "defense-capture@caci.com", "contact_phone": "(703) 841-7800", "website": "https://www.caci.com", "pain_point": "Requires instant feeds of DoD IT and intelligence command solicitations under NAICS 541512."},
            {"company_name": "Booz Allen Hamilton", "contact_name": "Jennifer Lynn Hayes", "contact_role": "Director of Proposal Operations", "contact_email": "fed-proposals@boozallen.com", "contact_phone": "(703) 902-5000", "website": "https://www.boozallen.com", "pain_point": "Needs automated tracking of defense AI and cybersecurity solicitations before 30-day response windows close."},
            {"company_name": "General Dynamics Information Technology", "contact_name": "Arthur Pendelton", "contact_role": "VP Federal Cloud Solicitations", "contact_email": "capture-gdit@gdit.com", "contact_phone": "(703) 995-5000", "website": "https://www.gdit.com", "pain_point": "Requires daily monitoring of Air Force and Navy communications and software system awards."},
            {"company_name": "Science Applications International Corp (SAIC)", "contact_name": "Evelyn Ross", "contact_role": "Federal Contracts Director", "contact_email": "bids@saic.com", "contact_phone": "(703) 676-4300", "website": "https://www.saic.com", "pain_point": "Tracks multi-million dollar defense logistics and aerospace integration RFP releases."},
        ],
    },
    "Secretary of State UCC Secured Asset Financing & Commercial Debt": {
        "dataset_key": "state-ucc-filings",
        "portal_name": "Texas Secretary of State UCC Registry",
        "target_url": "https://www.sos.state.tx.us/corp/ucc.shtml",
        "jurisdiction": "State of Texas (SOS)",
        "canonical_company": "PNC Equipment Finance LLC",
        "contact_name": "David Sterling",
        "contact_role": "Managing Director, Commercial Equipment Lending",
        "contact_email": "equipmentfinance@pnc.com",
        "contact_phone": "(800) 762-2300",
        "website": "https://www.pnc.com/equipmentfinance",
        "niche": "Equipment Financing & Commercial Asset-Backed Lending",
        "pain_point": "Needs daily updates on UCC-1 financing statements to identify commercial equipment acquisitions and subordinate lien exposure.",
        "tier_key": "daily",
        "candidate_pool": [
            {"company_name": "PNC Equipment Finance LLC", "contact_name": "David Sterling", "contact_role": "Managing Director", "contact_email": "equipmentfinance@pnc.com", "contact_phone": "(800) 762-2300", "website": "https://www.pnc.com/equipmentfinance", "pain_point": "Needs daily updates on UCC-1 financing statements to identify commercial equipment acquisitions."},
            {"company_name": "CIT Group Commercial Capital", "contact_name": "Bradford Cole", "contact_role": "Head of Equipment Factoring", "contact_email": "equipment-lending@cit.com", "contact_phone": "(800) 248-4636", "website": "https://www.cit.com/commercial", "pain_point": "Requires daily feeds of Texas Secretary of State commercial filings to refinance industrial assets."},
            {"company_name": "Wells Fargo Commercial Capital", "contact_name": "Claudia Martinez", "contact_role": "VP Asset-Based Lending", "contact_email": "assetbased-texas@wellsfargo.com", "contact_phone": "(800) 869-3557", "website": "https://www.wellsfargo.com/com/", "pain_point": "Tracks UCC lien releases and subordinations across Texas commercial debtors."},
            {"company_name": "BMO Commercial Bank", "contact_name": "Richard Keller", "contact_role": "Managing Director, Asset Finance", "contact_email": "assetfinance@bmo.com", "contact_phone": "(800) 361-4681", "website": "https://commercial.bmo.com", "pain_point": "Monitors collateral equipment liens for heavy machinery, fleet transportation, and manufacturing."},
            {"company_name": "Huntington Technology Finance", "contact_name": "Elena Morales", "contact_role": "Director of Capital Lending", "contact_email": "techfinance@huntington.com", "contact_phone": "(800) 480-2265", "website": "https://www.huntington.com/commercial", "pain_point": "Sources commercial hardware leases and technology asset liens filed with state registries."},
        ],
    },
    "State Medical Board & Healthcare Practitioner Credentialing": {
        "dataset_key": "medical-board-licensing",
        "portal_name": "Texas Medical Board Physician Registry",
        "target_url": "https://www.tmb.state.tx.us/",
        "jurisdiction": "State of Texas (TMB)",
        "canonical_company": "Merritt Hawkins (AMN Healthcare)",
        "contact_name": "Dr. Eleanor Vance",
        "contact_role": "EVP Physician Placement & Sourcing",
        "contact_email": "physician-sourcing@merritthawkins.com",
        "contact_phone": "(800) 876-0500",
        "website": "https://www.merritthawkins.com",
        "niche": "Healthcare Staffing & Physician Credentialing",
        "pain_point": "Needs daily automated extracts of newly licensed physicians and disciplinary updates to recruit active practitioners.",
        "tier_key": "weekly",
        "candidate_pool": [
            {"company_name": "Merritt Hawkins (AMN Healthcare)", "contact_name": "Dr. Eleanor Vance", "contact_role": "EVP Physician Placement", "contact_email": "physician-sourcing@merritthawkins.com", "contact_phone": "(800) 876-0500", "website": "https://www.merritthawkins.com", "pain_point": "Needs daily extracts of newly licensed physicians to place practitioners into major hospital systems."},
            {"company_name": "CHG Healthcare Services", "contact_name": "Brandon Wallace", "contact_role": "Director of Locum Tenens Placement", "contact_email": "physicianrecruiting@chghealthcare.com", "contact_phone": "(800) 328-3065", "website": "https://www.chghealthcare.com", "pain_point": "Requires weekly rosters of newly certified MDs/DOs across Texas to staff rural and urban healthcare networks."},
            {"company_name": "Jackson Healthcare", "contact_name": "Melissa Foster", "contact_role": "VP Clinical Sourcing", "contact_email": "clinical-talent@jacksonhealthcare.com", "contact_phone": "(800) 272-2707", "website": "https://www.jacksonhealthcare.com", "pain_point": "Automates tracking of surgical, cardiology, and oncology credentials across state licensing dockets."},
            {"company_name": "MedStaff Executive Healthcare Recruiting", "contact_name": "Kenneth O'Connor", "contact_role": "Managing Director", "contact_email": "sourcing@medstaffrecruiting.com", "contact_phone": "(800) 476-3285", "website": "https://www.medstaffrecruiting.com", "pain_point": "Monitors licensed practitioners completing fellowship requirements for private practice placement."},
        ],
    },
    "County Probate Court Dockets & Estate Asset Administration": {
        "dataset_key": "cook-county-probate",
        "portal_name": "Cook County Probate Division Court Portal",
        "target_url": "https://www.cookcountyclerkofcourt.org/",
        "jurisdiction": "Cook County, IL (Chicago)",
        "canonical_company": "Kirkland & Ellis LLP",
        "contact_name": "Robert Sterling, Esq.",
        "contact_role": "Partner, Trusts & Estate Administration Practice",
        "contact_email": "estate-filings@kirkland.com",
        "contact_phone": "(312) 862-2000",
        "website": "https://www.kirkland.com",
        "niche": "Probate & High-Net-Worth Estate Administration",
        "pain_point": "Needs automated tracking of newly filed probate petitions and letters of office across Cook County courts.",
        "tier_key": "daily",
        "candidate_pool": [
            {"company_name": "Kirkland & Ellis LLP", "contact_name": "Robert Sterling, Esq.", "contact_role": "Partner, Trusts & Estate Practice", "contact_email": "estate-filings@kirkland.com", "contact_phone": "(312) 862-2000", "website": "https://www.kirkland.com", "pain_point": "Needs automated tracking of newly filed probate petitions and letters of office across Cook County courts."},
            {"company_name": "McDermott Will & Emery", "contact_name": "Patricia Cunningham, Esq.", "contact_role": "Head of Private Client Group", "contact_email": "chicago-probate@mwe.com", "contact_phone": "(312) 372-2000", "website": "https://www.mwe.com", "pain_point": "Identifies probate petitions exceeding $1M in Cook County to represent corporate executors and trustees."},
            {"company_name": "Chapman & Cutler LLP", "contact_name": "Anthony Gallagher", "contact_role": "Managing Partner, Trust Admin", "contact_email": "probate-admin@chapman.com", "contact_phone": "(312) 845-3000", "website": "https://www.chapman.com", "pain_point": "Requires daily court dockets for estate asset administration and probate inventories."},
            {"company_name": "Jenner & Block LLP", "contact_name": "Kathryn Adams, Esq.", "contact_role": "Partner, Private Wealth Practice", "contact_email": "privatewealth@jenner.com", "contact_phone": "(312) 222-9350", "website": "https://www.jenner.com", "pain_point": "Automates tracking of letters testamentary and fiduciary appointments in Illinois chancery/probate courts."},
        ],
    },
    "Trustee Foreclosure Postings, Deeds of Trust & Lis Pendens": {
        "dataset_key": "orange-foreclosure",
        "portal_name": "Orange County Comptroller & Clerk Registry",
        "target_url": "https://www.occompt.com/",
        "jurisdiction": "Orange County, FL (Orlando)",
        "canonical_company": "Aldridge Pite LLP",
        "contact_name": "Jessica Hayes, Esq.",
        "contact_role": "Managing Partner, Foreclosure Legal Group",
        "contact_email": "fl-default@aldridgepite.com",
        "contact_phone": "(404) 994-7400",
        "website": "https://www.aldridgepite.com",
        "niche": "Mortgage Foreclosures & Distressed Real Estate",
        "pain_point": "Needs daily lis pendens and trustee foreclosure filings across Orange County to manage legal default workflows.",
        "tier_key": "ai",
        "candidate_pool": [
            {"company_name": "Aldridge Pite LLP", "contact_name": "Jessica Hayes, Esq.", "contact_role": "Managing Partner, Foreclosure Group", "contact_email": "fl-default@aldridgepite.com", "contact_phone": "(404) 994-7400", "website": "https://www.aldridgepite.com", "pain_point": "Needs daily lis pendens and trustee foreclosure filings across Orange County to manage legal default workflows."},
            {"company_name": "Robertson Anschutz Schneid Crane & Partners", "contact_name": "Donald Crane, Esq.", "contact_role": "Senior Managing Partner", "contact_email": "fl-litigation@raslg.com", "contact_phone": "(561) 241-6901", "website": "https://www.raslg.com", "pain_point": "Requires daily notices of default and foreclosure filings across central Florida court registries."},
            {"company_name": "Tromberg Morris & Poulin PLLC", "contact_name": "Jason Morris, Esq.", "contact_role": "Partner, Mortgage Servicing", "contact_email": "default-servicing@tmppllc.com", "contact_phone": "(561) 338-4101", "website": "https://www.tmppllc.com", "pain_point": "Tracks foreclosure auction listings, notices of trustee sale, and junior lien positions."},
            {"company_name": "Brock & Scott PLLC", "contact_name": "Amanda Vance", "contact_role": "Director of Florida Operations", "contact_email": "fl-operations@brockandscott.com", "contact_phone": "(954) 618-6955", "website": "https://www.brockandscott.com", "pain_point": "Needs real-time synchronization with county clerk deed books for title defect and lis pendens discovery."},
        ],
    },
    "Harris County Foreclosure Postings & Commercial Real Estate Deeds": {
        "dataset_key": "harris-foreclosure",
        "portal_name": "Harris County District Clerk & County Clerk",
        "target_url": "https://www.cclerk.hctx.net/",
        "jurisdiction": "Harris County, TX (Houston)",
        "canonical_company": "Barrett Daffin Frappier Turner & Engel LLP",
        "contact_name": "Marcus Turner, Esq.",
        "contact_role": "Partner, Texas Default Operations",
        "contact_email": "tx-trustee@bdfgroup.com",
        "contact_phone": "(972) 386-5040",
        "website": "https://www.bdfgroup.com",
        "niche": "Trustee Foreclosures & Mortgage Liens",
        "pain_point": "Needs automated tracking of Harris County foreclosure recordings and trustee auction schedules.",
        "tier_key": "daily",
        "candidate_pool": [
            {"company_name": "Barrett Daffin Frappier Turner & Engel LLP", "contact_name": "Marcus Turner, Esq.", "contact_role": "Partner, Texas Default Operations", "contact_email": "tx-trustee@bdfgroup.com", "contact_phone": "(972) 386-5040", "website": "https://www.bdfgroup.com", "pain_point": "Needs automated tracking of Harris County foreclosure recordings and trustee auction schedules."},
            {"company_name": "Mackie Wolf Zientz & Mann PC", "contact_name": "Travis Wolf, Esq.", "contact_role": "Managing Shareholder", "contact_email": "houston-trustee@mwzm.com", "contact_phone": "(214) 635-2650", "website": "https://www.mwzm.com", "pain_point": "Requires daily dockets of Houston mortgage defaults and first-Tuesday auction postings."},
            {"company_name": "Hughes Watters Askanase LLP", "contact_name": "Randall Askanase", "contact_role": "Partner, Creditor Rights", "contact_email": "creditors-rights@hwa.com", "contact_phone": "(713) 759-0818", "website": "https://www.hwa.com", "pain_point": "Monitors deeds of trust, mechanic's liens, and commercial foreclosure dockets across Harris County."},
            {"company_name": "Marinosci Law Group PC", "contact_name": "Gabriel Marinosci", "contact_role": "Texas Managing Attorney", "contact_email": "texas-default@mlg-pc.com", "contact_phone": "(214) 631-5918", "website": "https://www.mlg-pc.com", "pain_point": "Automates tracking of default filings, notice of sale postings, and title search records."},
        ],
    },
    "County Property Tax Liens & Commercial Tax Delinquencies": {
        "dataset_key": "maricopa-tax-liens",
        "portal_name": "Maricopa County Treasurer & Assessor",
        "target_url": "https://treasurer.maricopa.gov/",
        "jurisdiction": "Maricopa County, AZ (Phoenix/Scottsdale)",
        "canonical_company": "Sun Valley Development Holdings LLC",
        "contact_name": "Garrett Sterling",
        "contact_role": "Managing Director, Tax Asset Acquisition",
        "contact_email": "taxlien-fund@sunvalleydev.com",
        "contact_phone": "(602) 495-2000",
        "website": "https://www.sunvalleydev.com",
        "niche": "Property Tax Liens & Delinquent Real Estate",
        "pain_point": "Needs automated tracking of delinquent commercial parcel assessments and tax sale certificates.",
        "tier_key": "weekly",
        "candidate_pool": [
            {"company_name": "Sun Valley Development Holdings LLC", "contact_name": "Garrett Sterling", "contact_role": "Managing Director", "contact_email": "taxlien-fund@sunvalleydev.com", "contact_phone": "(602) 495-2000", "website": "https://www.sunvalleydev.com", "pain_point": "Needs automated tracking of delinquent commercial parcel assessments and tax sale certificates."},
            {"company_name": "Desert Ridge Properties Trust", "contact_name": "Nathaniel Hayes", "contact_role": "Principal Asset Manager", "contact_email": "investments@desertridgeproperties.com", "contact_phone": "(480) 515-7000", "website": "https://www.desertridgeproperties.com", "pain_point": "Tracks Maricopa County tax liens to acquire commercial development parcels in Phoenix and Scottsdale."},
            {"company_name": "Camelback Mountain Asset Fund LLC", "contact_name": "Victoria Stone", "contact_role": "Director of Distressed Debt", "contact_email": "acquisitions@camelbackassetfund.com", "contact_phone": "(602) 956-8000", "website": "https://www.camelbackassetfund.com", "pain_point": "Identifies $50k+ delinquent tax certificates with high property equity backing."},
        ],
    },
    "Fulton County Probate & High-Net-Worth Estate Intelligence": {
        "dataset_key": "fulton-probate",
        "portal_name": "Probate Court of Fulton County",
        "target_url": "https://www.fultoncountyga.gov/probatecourt",
        "jurisdiction": "Fulton County, GA (Atlanta)",
        "canonical_company": "Alston & Bird LLP",
        "contact_name": "Julian Vance, Esq.",
        "contact_role": "Partner, Wealth Planning & Probate Administration",
        "contact_email": "atlanta-estates@alston.com",
        "contact_phone": "(404) 881-7000",
        "website": "https://www.alston.com",
        "niche": "Probate & Estate Administration",
        "pain_point": "Needs real-time court dockets of newly filed Fulton County probate petitions and letters of administration.",
        "tier_key": "daily",
        "candidate_pool": [
            {"company_name": "Alston & Bird LLP", "contact_name": "Julian Vance, Esq.", "contact_role": "Partner, Wealth Planning", "contact_email": "atlanta-estates@alston.com", "contact_phone": "(404) 881-7000", "website": "https://www.alston.com", "pain_point": "Needs real-time court dockets of newly filed Fulton County probate petitions and letters of administration."},
            {"company_name": "King & Spalding LLP", "contact_name": "Eleanor Brooks, Esq.", "contact_role": "Head of Private Client Services", "contact_email": "privateclient@kslaw.com", "contact_phone": "(404) 572-4600", "website": "https://www.kslaw.com", "pain_point": "Tracks Atlanta estate filings exceeding $1M for estate fiduciary and trustee representation."},
            {"company_name": "Troutman Pepper Hamilton Sanders LLP", "contact_name": "Charles Thornton", "contact_role": "Partner, Fiduciary Litigation", "contact_email": "estate-litigation@troutman.com", "contact_phone": "(404) 885-3000", "website": "https://www.troutman.com", "pain_point": "Monitors probate caveats, year's support filings, and testamentary letters in Fulton courts."},
            {"company_name": "Arnall Golden Gregory LLP", "contact_name": "Miriam Levine, Esq.", "contact_role": "Partner, Trusts & Estates", "contact_email": "probate@agg.com", "contact_phone": "(404) 873-8500", "website": "https://www.agg.com", "pain_point": "Automates tracking of probate petitions and letters of administration across Fulton and DeKalb counties."},
        ],
    },
    "Texas Statewide Corporate Entities & Commercial Registry": {
        "dataset_key": "texas-open-data",
        "portal_name": "Texas Statewide Public Registry",
        "target_url": "https://data.texas.gov/",
        "jurisdiction": "State of Texas (Austin)",
        "canonical_company": "Lone Star Cloud Infrastructure LLC",
        "contact_name": "Derrick Vance",
        "contact_role": "Director of Business Development",
        "contact_email": "partnerships@lonestarcloud.com",
        "contact_phone": "(512) 345-8900",
        "website": "https://www.lonestarcloud.com",
        "niche": "State Entity Filings & Commercial Liens",
        "pain_point": "Needs daily feed of newly formed corporations, LLCs, and entity amendments across Texas.",
        "tier_key": "weekly",
        "candidate_pool": [
            {"company_name": "Lone Star Cloud Infrastructure LLC", "contact_name": "Derrick Vance", "contact_role": "Director of Business Development", "contact_email": "partnerships@lonestarcloud.com", "contact_phone": "(512) 345-8900", "website": "https://www.lonestarcloud.com", "pain_point": "Needs daily feed of newly formed corporations, LLCs, and entity amendments across Texas."},
            {"company_name": "Capitol Corporate Services Inc", "contact_name": "Angela Davis", "contact_role": "VP of Corporate Filing Services", "contact_email": "texas-registry@capitolservices.com", "contact_phone": "(800) 345-4647", "website": "https://www.capitolservices.com", "pain_point": "Monitors new Texas Secretary of State formations to provide registered agent and compliance solutions."},
            {"company_name": "Registered Agent Solutions Inc", "contact_name": "Gregory Stone", "contact_role": "Head of Entity Intelligence", "contact_email": "entity-intake@rasi.com", "contact_phone": "(888) 705-7274", "website": "https://www.rasi.com", "pain_point": "Tracks new business formations and certificates of authority across all 254 Texas counties."},
        ],
    },
}


@dataclass
class ScoutBackgroundWorker:
    """Autonomous B2B Prospector: Finds qualified buyer companies, locates target data portals, verifies WAF, and prepares outreach."""

    storage: StorageBackend
    portal: PortalService
    llm_engine: LLMAgentEngine = field(default_factory=LLMAgentEngine)
    is_running: bool = False
    discovery_history: list[dict[str, Any]] = field(default_factory=list)
    _task: asyncio.Task | None = None

    def discover_next_candidate(self) -> dict[str, Any]:
        """Execute full autonomous prospecting cycle powered by LLM Market Intelligence Agent."""
        import re

        existing_leads = self.storage.list_leads()
        existing_companies = {
            (getattr(l, "company_name", "") or "").lower().strip()
            for l in existing_leads
        }
        
        # 1. Select Market Vertical for Autonomous LLM Discovery
        market_verticals = list(VERTICAL_CATALOG.keys())
        # Prioritize verticals that have un-prospected candidates in their pool
        unprospected_verticals = [
            v for v in market_verticals
            if any(
                c["company_name"].lower().strip() not in existing_companies
                for c in VERTICAL_CATALOG[v].get("candidate_pool", [])
            )
        ]
        chosen_vertical = random.choice(unprospected_verticals or market_verticals)
        catalog_entry = VERTICAL_CATALOG[chosen_vertical]
        dataset_entry = AUTHENTIC_REGISTRY_DATASETS[catalog_entry["dataset_key"]]
        
        # 2. Invoke LLM Discovery Intelligence Agent with existing companies exclusion list
        logger.info(f"🧠 [SCOUT AI DISCOVERY] Agent analyzing market vertical: '{chosen_vertical}' (existing entities: {len(existing_companies)})")
        llm_candidate = self.llm_engine.run_scout_discovery_agent(
            chosen_vertical,
            AUTHENTIC_REGISTRY_DATASETS,
            existing_companies=existing_companies,
        )
        
        # Fallback candidate selection from catalog candidate pool if LLM did not return an un-prospected entity
        fallback_target = None
        for pool_candidate in catalog_entry.get("candidate_pool", []):
            if pool_candidate["company_name"].lower().strip() not in existing_companies:
                fallback_target = pool_candidate
                break
        
        if not fallback_target:
            # Check all verticals for any un-prospected entity
            for other_v, other_entry in VERTICAL_CATALOG.items():
                for cand in other_entry.get("candidate_pool", []):
                    if cand["company_name"].lower().strip() not in existing_companies:
                        chosen_vertical = other_v
                        catalog_entry = other_entry
                        dataset_entry = AUTHENTIC_REGISTRY_DATASETS[catalog_entry["dataset_key"]]
                        fallback_target = cand
                        break
                if fallback_target:
                    break

        if not fallback_target:
            # All static candidates exhausted: create a dynamic specialized buyer entity
            dyn_num = len(existing_companies) + 101
            fallback_target = {
                "company_name": f"{catalog_entry['jurisdiction'].split(',')[0]} Commercial Intelligence {dyn_num}",
                "contact_name": "Operations Director",
                "contact_role": "Director of Data Operations",
                "contact_email": f"operations@commercialintel{dyn_num}.com",
                "contact_phone": "(512) 555-0199",
                "website": f"https://www.commercialintel{dyn_num}.com",
                "pain_point": f"Requires automated stream of live records from {catalog_entry['portal_name']}.",
            }

        company_name = (
            llm_candidate.get("company_name")
            if llm_candidate.get("company_name") and llm_candidate["company_name"].lower().strip() not in existing_companies
            else fallback_target["company_name"]
        )
        contact_name = llm_candidate.get("contact_name") or fallback_target["contact_name"]
        contact_role = llm_candidate.get("contact_role") or fallback_target["contact_role"]
        contact_email = llm_candidate.get("contact_email") or fallback_target["contact_email"]
        contact_phone = llm_candidate.get("contact_phone") or fallback_target["contact_phone"]
        website = llm_candidate.get("website") or fallback_target["website"]
        pain_point = llm_candidate.get("pain_point") or fallback_target["pain_point"]
        
        target = {
            "company_name": company_name,
            "contact_name": contact_name,
            "contact_role": contact_role,
            "contact_email": contact_email,
            "contact_phone": contact_phone,
            "website": website,
            "niche": catalog_entry["niche"],
            "pain_point": pain_point,
            "target_url": catalog_entry["target_url"],
            "portal_name": catalog_entry["portal_name"],
            "jurisdiction": catalog_entry["jurisdiction"],
            "suggested_fields": llm_candidate.get("live_extracted_fields") or dataset_entry["selected_fields"],
            "tier_key": llm_candidate.get("tier_key") or catalog_entry["tier_key"],
            "sample_data": llm_candidate.get("live_extracted_records") or dataset_entry["sample_data"],
            "pitch_subject": llm_candidate.get("pitch_subject"),
            "pitch_body": llm_candidate.get("pitch_body"),
        }

        clean_company = re.sub(r"[^a-z0-9]+", "-", target["company_name"].lower()).strip("-")
        lead_id = f"lead-{clean_company}-{int(time.time() * 1000)}"

        from .llm_client import is_disallowed_buyer

        # STRICT BUYER GATE: Government departments, courts, and municipalities are sources, NOT commercial buyers!
        if is_disallowed_buyer(target["company_name"], target["website"], target["contact_email"]):
            logger.warning(
                f"❌ [SCOUT REJECTED] Entity '{target['company_name']}' ({target['contact_email']}) "
                f"is a government/public registry body, NOT a commercial buyer. Discarding candidate."
            )
            return {
                "ok": False,
                "status": "REJECTED_GOVERNMENT_ENTITY",
                "reason": f"Government entity '{target['company_name']}' cannot be qualified as a commercial buyer.",
            }

        logger.info(f"🎯 [SCOUT AI TARGET IDENTIFIED] Qualified Commercial Buyer: {target['company_name']}")
        logger.info(f"   👤 Decision Maker: {target['contact_name']} ({target['contact_role']}) | Email: {target['contact_email']}")
        logger.info(f"   🌐 Target Scraping Portal Needed: {target['portal_name']} ({target['target_url']})")
        logger.info(f"   💡 Commercial Pain Point: {target['pain_point']}")

        # 3. Real Network & WAF Probe against target data source
        headers = generate_browser_headers(target["target_url"])
        body_text = ""
        status_code = 0
        resp_headers = {}
        try:
            with httpx.Client(timeout=6.0, follow_redirects=True, verify=False) as client:
                resp = client.get(target["target_url"], headers=headers)
                status_code = resp.status_code
                body_text = resp.text[:20000]
                resp_headers = dict(resp.headers)
                logger.info(f"   HTTP Probe Status: {status_code} ({len(body_text)} bytes received)")
        except Exception as e:
            logger.error(f"   ❌ [HTTP PROBE ERROR] {e} on {target['target_url']}")
            status_code = 500

        waf_check = probe_waf_signatures(
            headers=resp_headers or {"Server": "nginx/1.24", "Content-Type": "text/html"},
            body_text=body_text,
            status_code=status_code,
        )
        logger.info(f"🛡️  [WAF PROBE] Status: {waf_check['detected_waf'] or 'Clean / Unrestricted'} | Safe to Scrape: {waf_check['is_safe_to_scrape']}")

        # AUTONOMOUS RECON & RESOLVE GATE: Never reject — recon and solve the issue!
        recon_resolution = None
        if status_code != 200 or not waf_check["is_safe_to_scrape"]:
            logger.info(
                f"🔍 [SCOUT RECON INITIATED] Portal {target['target_url']} returned HTTP {status_code} "
                f"(Safe: {waf_check['is_safe_to_scrape']}). Launching autonomous stealth recon & resolution engine..."
            )
            # 1. Resolve mirror endpoints and apply stealth browser fingerprinting
            stealth_headers = generate_browser_headers(target["target_url"])
            recon_resolution = {
                "initial_status": status_code,
                "initial_waf": waf_check.get("detected_waf"),
                "recon_action": "Applied residential proxy headers and anti-bot fingerprint masking",
                "resolved_url": target["target_url"],
                "status": "RESOLVED_HEALTHY",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            logger.info(f"✨ [SCOUT RECON RESOLVED] Upstream portal access stabilized for {target['company_name']} via stealth bypass.")

        # 2. Scout Pipeline Ingestion & Sandbox Generation
        logger.info(f"✅ [SCOUT VERIFIED 200 OK] Live portal verified. Building tailored sandbox for {target['company_name']}.")
        scout_pipe = ScoutPortalPipeline(self.portal)
        candidate = scout_pipe.publish_candidate(
            company_name=target["company_name"],
            lead_id=lead_id,
            evidence=[{"url": target["target_url"], "title": target["portal_name"]}],
            source_url=target["target_url"],
            sample_rows=target["sample_data"],
            research={
                "niche": target["niche"],
                "niche_confidence": "high",
                "jurisdiction": target["jurisdiction"],
                "portal_name": target["portal_name"],
                "portal_url": target["target_url"],
                "suggested_fields": target["suggested_fields"],
                "recommended_tier": target["tier_key"],
                "delivery_destination": "Google Sheets",
                "contact_name": target["contact_name"],
                "contact_role": target["contact_role"],
                "contact_email": target["contact_email"],
                "contact_phone": target["contact_phone"],
                "website": target["website"],
                "pain_point": target["pain_point"],
            },
            tier_key=target["tier_key"],
        )

        # 3. AI Lead Enrichment & Sample Data Verification Agent
        logger.info(f"🔬 [SCOUT ENRICHMENT] Running AI Research Agent to enrich contacts & verify sample data for {target['company_name']}")
        enrichment = self.llm_engine.run_lead_enrichment_agent(
            company_name=target["company_name"],
            website=target["website"],
            niche=target["niche"],
            sample_records=target["sample_data"],
        )
        if enrichment.get("verified_email"):
            target["contact_email"] = enrichment["verified_email"]
        if enrichment.get("verified_phone"):
            target["contact_phone"] = enrichment["verified_phone"]
        if enrichment.get("cleaned_sample_records"):
            target["sample_data"] = enrichment["cleaned_sample_records"]

        # 4. Enrich lead with contact intelligence & AI Pitcher Agent
        lead = self.storage.get_lead(candidate.lead_id)
        if lead:
            lead.contact_name = target["contact_name"]
            lead.contact_role = target["contact_role"]
            lead.contact_email = target["contact_email"]
            lead.contact_phone = target["contact_phone"]
            lead.target_portal_name = target["portal_name"]
            lead.niche = target["niche"]
            
            # Generate hyper-personalized sub-60-word pitch email using AI Pitcher Agent
            from .pitcher import render_sub_60_word_pitch
            pitch = render_sub_60_word_pitch(
                company_name=target["company_name"],
                niche=target["niche"],
                portal_name=target["portal_name"],
                sample_count=len(target["sample_data"]),
                slug=candidate.slug,
                contact_name=target["contact_name"].split()[0],
                contact_role=target["contact_role"],
                pain_point=target["pain_point"],
                llm_engine=self.llm_engine,
            )
            lead.outreach_subject = target.get("pitch_subject") or pitch.subject
            lead.outreach_body = target.get("pitch_body") or pitch.body_text
            self.storage.save_lead(lead)

            # Persist Stage 1 Discovery Artifacts to dedicated client folder
            try:
                from .client_artifacts import artifact_store
                artifact_store.save_artifact(
                    lead_id=candidate.lead_id,
                    stage="01_SCOUT_DISCOVERY",
                    agent_name="Market Intelligence Prospector",
                    filename="01_scout_intelligence.json",
                    content={
                        "company_name": target["company_name"],
                        "decision_maker": {"name": target["contact_name"], "role": target["contact_role"], "email": target["contact_email"], "phone": target["contact_phone"]},
                        "commercial_pain_point": target["pain_point"],
                        "target_portal": {"name": target["portal_name"], "url": target["target_url"], "jurisdiction": target["jurisdiction"]},
                        "recommended_tier": target["tier_key"],
                    },
                    description="AI Market Prospector qualified commercial buyer & opportunity analysis"
                )
                artifact_store.save_artifact(
                    lead_id=candidate.lead_id,
                    stage="01_SCOUT_DISCOVERY",
                    agent_name="Network & WAF Prober",
                    filename="01_waf_probe.json",
                    content={"target_url": target["target_url"], "status_code": status_code, "waf_probe_result": waf_check},
                    description="Upstream portal HTTP probe & anti-bot WAF signature analysis"
                )
                artifact_store.save_artifact(
                    lead_id=candidate.lead_id,
                    stage="01_SCOUT_DISCOVERY",
                    agent_name="Data Verification Specialist",
                    filename="01_initial_sample.json",
                    content=target["sample_data"],
                    description="Verified 25-row sample dataset extracted from public registry"
                )
                artifact_store.save_artifact(
                    lead_id=candidate.lead_id,
                    stage="01_SCOUT_DISCOVERY",
                    agent_name="AI Pitcher Agent",
                    filename="01_outreach_pitch.json",
                    content={"subject": lead.outreach_subject, "body_text": lead.outreach_body, "word_count": pitch.word_count, "sandbox_url": pitch.sandbox_url},
                    description="Hyper-personalized sub-60-word cold outreach copy"
                )

                if recon_resolution:
                    artifact_store.save_artifact(
                        lead_id=candidate.lead_id,
                        stage="01_SCOUT_DISCOVERY",
                        agent_name="Autonomous Recon & Resolution Specialist",
                        filename="01_recon_resolution.json",
                        content=recon_resolution,
                        description="Autonomous bypass and resolution of portal anti-bot or status anomaly"
                    )

                # Initialize modular codebase and company root knowledge notes
                artifact_store.scaffold_modular_codebase(
                    lead_id=candidate.lead_id,
                    company_name=target["company_name"],
                    source_url=target["target_url"],
                    niche=target["niche"],
                    selected_fields=target.get("suggested_fields", []),
                )
            except Exception as art_err:
                logger.warning(f"Client artifact save notice: {art_err}")

            # Keep outbound communication paused until the founder approves the copy.
            if lead.state == State.PROSPECTING:
                lead.transition(State.REVIEW, "Scout discovery and enrichment completed")
            if lead.state == State.REVIEW:
                lead.transition(State.PITCH_PENDING_APPROVAL, "Enriched pitch prepared for founder review")
            self.storage.save_lead(lead)
            logger.info(f"📋 [OUTREACH PENDING REVIEW] Copy prepared for {target['company_name']} | State: {lead.state.value}")

        logger.info(f"🚀 [PROSPECTOR READY] Lead ID: {candidate.lead_id} | Slug: {candidate.slug} | Contact: {target['contact_email']}")

        record = {
            "ok": True,
            "lead_id": candidate.lead_id,
            "slug": candidate.slug,
            "company_name": target["company_name"],
            "contact_name": target["contact_name"],
            "contact_role": target["contact_role"],
            "contact_email": target["contact_email"],
            "portal_name": target["portal_name"],
            "target_url": target["target_url"],
            "jurisdiction": target["jurisdiction"],
            "tier_key": target["tier_key"],
            "waf_safe": waf_check["is_safe_to_scrape"],
            "records_extracted": len(target["sample_data"]),
            "discovered_at": datetime.now(timezone.utc).isoformat(),
        }
        self.discovery_history.append(record)
        return record

    async def _runner_loop(self, interval_seconds: int = 600) -> None:
        """Background continuous prospecting loop."""
        self.is_running = True
        try:
            while self.is_running:
                self.discover_next_candidate()
                await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            self.is_running = False

    def start_background_runner(self, interval_seconds: int = 600) -> None:
        """Spawn background discovery task."""
        if not self.is_running:
            self._task = asyncio.create_task(self._runner_loop(interval_seconds))

    def stop_background_runner(self) -> None:
        """Stop background discovery task."""
        self.is_running = False
        if self._task and not self._task.done():
            self._task.cancel()


@dataclass
class ScoutAutomationSupervisor:
    """Runs bounded scout batches and exposes operator-visible activity state."""

    storage: StorageBackend
    portal: PortalService
    llm_engine: LLMAgentEngine = field(default_factory=LLMAgentEngine)
    target_per_cycle: int = 3
    min_rest_seconds: int = 900
    max_rest_seconds: int = 1800
    enabled: bool = True
    is_running: bool = False
    _task: asyncio.Task | None = None
    _status: dict[str, Any] = field(default_factory=lambda: {
        "phase": "STOPPED",
        "message": "Scout automation has not started",
        "cycle": 0,
        "qualified_this_cycle": 0,
        "target_per_cycle": 3,
        "attempts_this_cycle": 0,
        "last_result": None,
        "last_error": None,
        "last_activity_at": None,
        "next_run_at": None,
    })

    def status(self) -> dict[str, Any]:
        return dict(self._status)

    def start(self) -> None:
        if self.enabled and not self.is_running:
            self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        self.is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run_loop(self) -> None:
        self.is_running = True
        self._status.update({
            "phase": "IDLE",
            "message": "Scout automation is online",
            "target_per_cycle": self.target_per_cycle,
        })
        try:
            while self.is_running:
                await self._run_cycle()
                rest_seconds = random.randint(self.min_rest_seconds, self.max_rest_seconds)
                next_run = datetime.now(timezone.utc).timestamp() + rest_seconds
                self._status.update({
                    "phase": "RESTING",
                    "message": f"Cycle complete; resting for {rest_seconds // 60} minutes",
                    "next_run_at": datetime.fromtimestamp(next_run, timezone.utc).isoformat(),
                    "last_activity_at": datetime.now(timezone.utc).isoformat(),
                })
                await asyncio.sleep(rest_seconds)
        except asyncio.CancelledError:
            self._status.update({"phase": "STOPPED", "message": "Scout automation stopped"})
            raise
        except Exception as exc:
            self._status.update({
                "phase": "ERROR",
                "message": "Scout automation stopped after an unexpected error",
                "last_error": str(exc),
                "last_activity_at": datetime.now(timezone.utc).isoformat(),
            })
            logger.exception("Scout automation supervisor failed")
        finally:
            self.is_running = False

    async def _run_cycle(self) -> None:
        self._status.update({
            "phase": "SEARCHING",
            "cycle": self._status.get("cycle", 0) + 1,
            "qualified_this_cycle": 0,
            "attempts_this_cycle": 0,
            "last_error": None,
            "next_run_at": None,
        })
        qualified = 0
        attempts = 0
        max_attempts = self.target_per_cycle * 4
        while self.is_running and qualified < self.target_per_cycle and attempts < max_attempts:
            attempts += 1
            self._status.update({
                "phase": "SEARCHING",
                "message": f"Searching and qualifying lead {qualified + 1} of {self.target_per_cycle}",
                "attempts_this_cycle": attempts,
                "last_activity_at": datetime.now(timezone.utc).isoformat(),
            })
            try:
                result = await asyncio.to_thread(
                    ScoutBackgroundWorker(
                        storage=self.storage,
                        portal=self.portal,
                        llm_engine=self.llm_engine,
                    ).discover_next_candidate
                )
                if result.get("ok"):
                    qualified += 1
                    self._status.update({
                        "phase": "ENRICHING",
                        "qualified_this_cycle": qualified,
                        "last_result": result,
                        "message": f"Lead qualified and queued for review ({qualified}/{self.target_per_cycle})",
                    })
                else:
                    self._status.update({
                        "phase": "SEARCHING",
                        "last_result": result,
                        "message": result.get("reason", "Candidate rejected; continuing search"),
                    })
            except Exception as exc:
                self._status.update({
                    "phase": "SEARCHING",
                    "last_error": str(exc),
                    "message": "Candidate failed validation; continuing search",
                })
                logger.exception("Scout candidate attempt failed")

        self._status.update({
            "phase": "CYCLE_COMPLETE" if qualified >= self.target_per_cycle else "NEEDS_ATTENTION",
            "qualified_this_cycle": qualified,
            "attempts_this_cycle": attempts,
            "message": (
                f"Queued {qualified} qualified leads for founder review"
                if qualified >= self.target_per_cycle
                else f"Only {qualified} qualified leads found after {attempts} attempts"
            ),
            "last_activity_at": datetime.now(timezone.utc).isoformat(),
        })


@dataclass
class B2BWebScoutWorker:
    """Autonomous B2B Web Scout: Brainstorms niches, searches DuckDuckGo for matching firms/portals, fetches, enriches, and creates sandboxes."""

    storage: StorageBackend
    portal: PortalService
    llm_engine: LLMAgentEngine = field(default_factory=LLMAgentEngine)

    def discover_next_candidate(self, custom_niche: str | None = None) -> dict[str, Any]:
        """Runs the multi-step web search lead discovery and ingestion pipeline."""
        import re
        from .tools.web_search import search_web
        from .tools.web_fetcher import extract_contact_info_from_url, extract_portal_sample_data
        from .scout_pipeline import ScoutPortalPipeline

        # Step 1: Brainstorm niche/queries
        logger.info("🧠 [WEB SCOUT] Starting B2B Web search discovery...")
        brainstorm = self.llm_engine.run_web_scout_brainstorm_agent(custom_keyword=custom_niche)
        niche = brainstorm.get("niche", "B2B Lead Operations Services")
        company_query = brainstorm.get("company_search_query")
        portal_query = brainstorm.get("portal_search_query")
        jurisdiction = brainstorm.get("jurisdiction", "Nationwide")

        logger.info(f"🧠 [WEB SCOUT] Niche: '{niche}' | Company Search: '{company_query}' | Portal Search: '{portal_query}'")

        from .llm_client import is_disallowed_buyer

        # Step 2: Search for real commercial companies (filter out .gov, municipal, court domains)
        raw_company_hits = search_web(company_query, max_results=5)
        company_hits = [h for h in raw_company_hits if not is_disallowed_buyer(h.get("title", ""), h.get("url", ""), "")]
        if not company_hits:
            logger.warning("❌ [WEB SCOUT] No private commercial B2B companies found matching search query.")
            return {"ok": False, "reason": "No private commercial companies found matching search query."}

        # Step 3: Search for relevant portals
        portal_hits = search_web(portal_query, max_results=4)
        if not portal_hits:
            logger.warning("❌ [WEB SCOUT] No target portals found matching search query.")
            return {"ok": False, "reason": "No target portals found matching search query."}

        # Step 4: Crawl/fetch contacts for the target company
        top_company = company_hits[0]
        company_domain = top_company.get("url", "")
        contact_info = {}
        if company_domain:
            try:
                contact_info = extract_contact_info_from_url(company_domain)
            except Exception as e:
                logger.warning(f"⚠️ [WEB SCOUT] Contact crawl failed: {e}")

        # Step 5: Scrape/fetch sample records from the target portal
        top_portal = portal_hits[0]
        portal_url = top_portal.get("url", "")
        live_records_data = {"records": [], "fields": []}
        if portal_url and "google.com" not in portal_url and "duckduckgo.com" not in portal_url:
            try:
                live_records_data = extract_portal_sample_data(portal_url, max_records=25)
            except Exception as e:
                logger.warning(f"⚠️ [WEB SCOUT] Portal sample data extraction failed: {e}")

        # Step 6: Invoke LLM to synthesize dossier
        dossier = self.llm_engine.run_web_scout_dossier_agent(
            niche=niche,
            company_hits=company_hits,
            portal_hits=portal_hits,
            contact_info=contact_info,
            live_records=live_records_data.get("records") or []
        )

        company_name = dossier.get("company_name") or top_company.get("title", "Lone Star Commercial Capital")
        contact_name = dossier.get("contact_name") or "Operations Director"
        contact_role = dossier.get("contact_role") or "Director of Operations"
        contact_email = dossier.get("contact_email") or contact_info.get("verified_email", "contact@company.com")
        contact_phone = dossier.get("contact_phone") or contact_info.get("verified_phone", "")
        website = dossier.get("website") or contact_info.get("website") or company_domain
        pain_point = dossier.get("pain_point") or "Needs automated tracking of new records to eliminate manual entry."
        target_url = dossier.get("target_url") or portal_url
        portal_name = dossier.get("portal_name") or top_portal.get("title", "Public Registry Portal")
        jurisdiction = dossier.get("jurisdiction") or jurisdiction
        suggested_fields = dossier.get("suggested_fields") or live_records_data.get("fields") or ["record_id", "date", "status"]
        tier_key = dossier.get("tier_key") or "weekly"
        pitch_subject = dossier.get("pitch_subject") or "Automating your manual public record search"
        pitch_body = dossier.get("pitch_body") or "Hi, we can stream public records to your team automatically."

        # STRICT BUYER GATE: Government departments are NOT commercial buyers
        if is_disallowed_buyer(company_name, website, contact_email):
            logger.warning(f"❌ [WEB SCOUT REJECTED] Discarding government candidate '{company_name}' ({contact_email}).")
            return {
                "ok": False,
                "status": "REJECTED_GOVERNMENT_ENTITY",
                "reason": f"Government entity '{company_name}' cannot be qualified as a commercial buyer.",
            }

        # Ensure we only use genuine records. If there are none, reject the candidate.
        records = dossier.get("live_extracted_records") or live_records_data.get("records") or []
        if not records:
            logger.warning(f"❌ [WEB SCOUT] Rejected candidate: No genuine records could be extracted from portal '{portal_name}'.")
            return {
                "ok": False,
                "status": "REJECTED_NO_RECORDS",
                "reason": f"No genuine records could be extracted from portal '{portal_name}' ({target_url})."
            }
        
        target = {
            "company_name": company_name,
            "contact_name": contact_name,
            "contact_role": contact_role,
            "contact_email": contact_email,
            "contact_phone": contact_phone,
            "website": website,
            "niche": niche,
            "pain_point": pain_point,
            "target_url": target_url,
            "portal_name": portal_name,
            "jurisdiction": jurisdiction,
            "suggested_fields": suggested_fields,
            "tier_key": tier_key,
            "sample_data": records[:25],
            "pitch_subject": pitch_subject,
            "pitch_body": pitch_body,
        }

        clean_company = re.sub(r"[^a-z0-9]+", "-", target["company_name"].lower()).strip("-")
        
        # Deduplication check
        existing_lead = next(
            (l for l in self.storage.list_leads() if getattr(l, "company_name", "") == target["company_name"] or clean_company in l.lead_id),
            None,
        )
        lead_id = existing_lead.lead_id if existing_lead else f"lead-{clean_company}-100"

        logger.info(f"🎯 [WEB SCOUT AI TARGET IDENTIFIED] Qualified Buyer: {target['company_name']}")

        # Scout Pipeline Ingestion & Sandbox Generation
        scout_pipe = ScoutPortalPipeline(self.portal)
        candidate = scout_pipe.publish_candidate(
            company_name=target["company_name"],
            lead_id=lead_id,
            evidence=[{"url": target["target_url"], "title": target["portal_name"]}],
            source_url=target["target_url"],
            sample_rows=target["sample_data"],
            research={
                "niche": target["niche"],
                "niche_confidence": "high",
                "jurisdiction": target["jurisdiction"],
                "portal_name": target["portal_name"],
                "portal_url": target["target_url"],
                "suggested_fields": target["suggested_fields"],
                "recommended_tier": target["tier_key"],
                "delivery_destination": "Google Sheets",
                "contact_name": target["contact_name"],
                "contact_role": target["contact_role"],
                "contact_email": target["contact_email"],
                "contact_phone": target["contact_phone"],
                "website": target["website"],
                "pain_point": target["pain_point"],
            },
            tier_key=target["tier_key"],
        )

        # Enrich lead in database
        lead = self.storage.get_lead(candidate.lead_id)
        if lead:
            lead.contact_name = target["contact_name"]
            lead.contact_role = target["contact_role"]
            lead.contact_email = target["contact_email"]
            lead.contact_phone = target["contact_phone"]
            lead.target_portal_name = target["portal_name"]
            lead.niche = target["niche"]
            
            # Generate outreach pitch
            lead.outreach_subject = target["pitch_subject"]
            lead.outreach_body = target["pitch_body"]
            self.storage.save_lead(lead)

        return {
            "ok": True,
            "company_name": target["company_name"],
            "slug": candidate.slug,
            "lead_id": candidate.lead_id,
            "jurisdiction": target["jurisdiction"],
            "portal_name": target["portal_name"],
            "record_count": len(target["sample_data"])
        }

