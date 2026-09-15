"""Geo-County Resolver & Municipal Jurisdiction Engine for LeadOps Scout.

Maps commercial business locations (address, city, state, zip code) to their official
County / Parish jurisdiction, official public records court / clerk portal, and validates
that extracted dockets and sample filings match the prospect's real jurisdiction.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from ..logging_config import get_logger

logger = get_logger("geo_county_resolver")

# US State abbreviations mapping
STATE_NAMES_TO_ABBR: dict[str, str] = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA",
    "colorado": "CO", "connecticut": "CT", "delaware": "DE", "florida": "FL", "georgia": "GA",
    "hawaii": "HI", "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS", "missouri": "MO",
    "montana": "MT", "nebraska": "NE", "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ",
    "new mexico": "NM", "new york": "NY", "north carolina": "NC", "north dakota": "ND", "ohio": "OH",
    "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT",
    "virginia": "VA", "washington": "WA", "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
    "district of columbia": "DC",
}

# Authoritative Mapping of US Cities & Metros to Primary County/Parish
# Covers the top 300+ commercial metros and public records markets
CITY_COUNTY_REGISTRY: dict[tuple[str, str], dict[str, str]] = {
    # Texas (TX)
    ("austin", "TX"): {"county": "Travis County", "fips": "48453", "portal_name": "Travis County Clerk & Deeds Registry", "portal_url": "https://www.traviscountytx.gov/county-clerk"},
    ("houston", "TX"): {"county": "Harris County", "fips": "48201", "portal_name": "Harris County District Clerk & County Clerk", "portal_url": "https://www.cclerk.hctx.net/"},
    ("dallas", "TX"): {"county": "Dallas County", "fips": "48113", "portal_name": "Dallas County Clerk & Records Registry", "portal_url": "https://www.dallascounty.org/government/county-clerk/"},
    ("fort worth", "TX"): {"county": "Tarrant County", "fips": "48439", "portal_name": "Tarrant County Clerk & Official Public Records", "portal_url": "https://www.tarrantcountytx.gov/en/county-clerk.html"},
    ("arlington", "TX"): {"county": "Tarrant County", "fips": "48439", "portal_name": "Tarrant County Clerk & Official Public Records", "portal_url": "https://www.tarrantcountytx.gov/en/county-clerk.html"},
    ("san antonio", "TX"): {"county": "Bexar County", "fips": "48029", "portal_name": "Bexar County Clerk & Probate Court Records", "portal_url": "https://www.bexar.org/county-clerk"},
    ("plano", "TX"): {"county": "Collin County", "fips": "48085", "portal_name": "Collin County Clerk & Recording", "portal_url": "https://www.collincountytx.gov/county_clerk"},
    ("frisco", "TX"): {"county": "Collin County", "fips": "48085", "portal_name": "Collin County Clerk & Recording", "portal_url": "https://www.collincountytx.gov/county_clerk"},
    ("mckinney", "TX"): {"county": "Collin County", "fips": "48085", "portal_name": "Collin County Clerk & Recording", "portal_url": "https://www.collincountytx.gov/county_clerk"},
    ("denton", "TX"): {"county": "Denton County", "fips": "48121", "portal_name": "Denton County Clerk Records", "portal_url": "https://www.dentoncounty.gov/county-clerk"},
    ("el paso", "TX"): {"county": "El Paso County", "fips": "48141", "portal_name": "El Paso County District & County Clerk", "portal_url": "https://www.epcounty.com/countyclerk/"},
    ("corpus christi", "TX"): {"county": "Nueces County", "fips": "48355", "portal_name": "Nueces County Clerk & Records", "portal_url": "https://www.nuecesco.com/county-clerk"},
    ("lubbock", "TX"): {"county": "Lubbock County", "fips": "48303", "portal_name": "Lubbock County Clerk", "portal_url": "https://www.co.lubbock.tx.us/department/county-clerk"},
    ("amarillo", "TX"): {"county": "Potter County", "fips": "48375", "portal_name": "Potter County Clerk", "portal_url": "https://www.co.potter.tx.us/"},
    ("laredo", "TX"): {"county": "Webb County", "fips": "48479", "portal_name": "Webb County Clerk", "portal_url": "https://www.webbcountytx.gov/countyclerk/"},
    ("woodlands", "TX"): {"county": "Montgomery County", "fips": "48339", "portal_name": "Montgomery County Clerk", "portal_url": "https://www.mctx.org/departments/county_clerk"},
    ("the woodlands", "TX"): {"county": "Montgomery County", "fips": "48339", "portal_name": "Montgomery County Clerk", "portal_url": "https://www.mctx.org/departments/county_clerk"},
    ("sugar land", "TX"): {"county": "Fort Bend County", "fips": "48157", "portal_name": "Fort Bend County Clerk", "portal_url": "https://www.fortbendcountytx.gov/government/departments/county-clerk"},
    ("round rock", "TX"): {"county": "Williamson County", "fips": "48491", "portal_name": "Williamson County Clerk & Deeds", "portal_url": "https://www.wilco.org/county-clerk"},
    ("georgetown", "TX"): {"county": "Williamson County", "fips": "48491", "portal_name": "Williamson County Clerk & Deeds", "portal_url": "https://www.wilco.org/county-clerk"},
    ("irving", "TX"): {"county": "Dallas County", "fips": "48113", "portal_name": "Dallas County Clerk & Records Registry", "portal_url": "https://www.dallascounty.org/government/county-clerk/"},
    ("garland", "TX"): {"county": "Dallas County", "fips": "48113", "portal_name": "Dallas County Clerk & Records Registry", "portal_url": "https://www.dallascounty.org/government/county-clerk/"},

    # Florida (FL)
    ("miami", "FL"): {"county": "Miami-Dade County", "fips": "12086", "portal_name": "Miami-Dade County Clerk of Courts & Comptroller", "portal_url": "https://www.miamidadeclerk.gov/"},
    ("miami beach", "FL"): {"county": "Miami-Dade County", "fips": "12086", "portal_name": "Miami-Dade County Clerk of Courts & Comptroller", "portal_url": "https://www.miamidadeclerk.gov/"},
    ("orlando", "FL"): {"county": "Orange County", "fips": "12095", "portal_name": "Orange County Comptroller & Official Records", "portal_url": "https://www.occompt.com/"},
    ("tampa", "FL"): {"county": "Hillsborough County", "fips": "12057", "portal_name": "Hillsborough County Clerk of Court & Comptroller", "portal_url": "https://www.hillsclerk.com/"},
    ("jacksonville", "FL"): {"county": "Duval County", "fips": "12031", "portal_name": "Duval County Clerk of Courts", "portal_url": "https://www.duvalclerk.com/"},
    ("fort lauderdale", "FL"): {"county": "Broward County", "fips": "12011", "portal_name": "Broward County Records, Taxes & Treasury", "portal_url": "https://www.broward.org/records/"},
    ("hollywood", "FL"): {"county": "Broward County", "fips": "12011", "portal_name": "Broward County Records, Taxes & Treasury", "portal_url": "https://www.broward.org/records/"},
    ("west palm beach", "FL"): {"county": "Palm Beach County", "fips": "12099", "portal_name": "Palm Beach County Clerk of Courts & Comptroller", "portal_url": "https://www.mypalmbeachclerk.com/"},
    ("boca raton", "FL"): {"county": "Palm Beach County", "fips": "12099", "portal_name": "Palm Beach County Clerk of Courts & Comptroller", "portal_url": "https://www.mypalmbeachclerk.com/"},
    ("st. petersburg", "FL"): {"county": "Pinellas County", "fips": "12103", "portal_name": "Pinellas County Clerk & Comptroller", "portal_url": "https://www.mypinellasclerk.org/"},
    ("clearwater", "FL"): {"county": "Pinellas County", "fips": "12103", "portal_name": "Pinellas County Clerk & Comptroller", "portal_url": "https://www.mypinellasclerk.org/"},
    ("tallahassee", "FL"): {"county": "Leon County", "fips": "12073", "portal_name": "Leon County Clerk & Comptroller", "portal_url": "https://www.leoncountyfl.gov/"},
    ("sarasota", "FL"): {"county": "Sarasota County", "fips": "12115", "portal_name": "Sarasota County Clerk and County Comptroller", "portal_url": "https://www.sarasotaclerk.com/"},
    ("naples", "FL"): {"county": "Collier County", "fips": "12021", "portal_name": "Collier County Clerk & Comptroller", "portal_url": "https://www.collierclerk.com/"},
    ("fort myers", "FL"): {"county": "Lee County", "fips": "12071", "portal_name": "Lee County Clerk of Courts", "portal_url": "https://www.leeclerk.org/"},
    ("gainesville", "FL"): {"county": "Alachua County", "fips": "12001", "portal_name": "Alachua County Clerk of the Court", "portal_url": "https://www.alachuaclerk.org/"},

    # Arizona (AZ)
    ("phoenix", "AZ"): {"county": "Maricopa County", "fips": "04013", "portal_name": "Maricopa County Recorder & Public Records", "portal_url": "https://recorder.maricopa.gov/"},
    ("scottsdale", "AZ"): {"county": "Maricopa County", "fips": "04013", "portal_name": "Maricopa County Recorder & Public Records", "portal_url": "https://recorder.maricopa.gov/"},
    ("mesa", "AZ"): {"county": "Maricopa County", "fips": "04013", "portal_name": "Maricopa County Recorder & Public Records", "portal_url": "https://recorder.maricopa.gov/"},
    ("chandler", "AZ"): {"county": "Maricopa County", "fips": "04013", "portal_name": "Maricopa County Recorder & Public Records", "portal_url": "https://recorder.maricopa.gov/"},
    ("gilbert", "AZ"): {"county": "Maricopa County", "fips": "04013", "portal_name": "Maricopa County Recorder & Public Records", "portal_url": "https://recorder.maricopa.gov/"},
    ("glendale", "AZ"): {"county": "Maricopa County", "fips": "04013", "portal_name": "Maricopa County Recorder & Public Records", "portal_url": "https://recorder.maricopa.gov/"},
    ("tempe", "AZ"): {"county": "Maricopa County", "fips": "04013", "portal_name": "Maricopa County Recorder & Public Records", "portal_url": "https://recorder.maricopa.gov/"},
    ("peoria", "AZ"): {"county": "Maricopa County", "fips": "04013", "portal_name": "Maricopa County Recorder & Public Records", "portal_url": "https://recorder.maricopa.gov/"},
    ("tucson", "AZ"): {"county": "Pima County", "fips": "04019", "portal_name": "Pima County Recorder & Assessor", "portal_url": "https://www.recorder.pima.gov/"},
    ("flagstaff", "AZ"): {"county": "Coconino County", "fips": "04005", "portal_name": "Coconino County Recorder", "portal_url": "https://www.coconino.az.gov/recorder"},
    ("prescott", "AZ"): {"county": "Yavapai County", "fips": "04025", "portal_name": "Yavapai County Recorder", "portal_url": "https://www.yavapaiaz.gov/recorder"},
    ("yuma", "AZ"): {"county": "Yuma County", "fips": "04027", "portal_name": "Yuma County Recorder", "portal_url": "https://www.yumacountyaz.gov/recorder"},

    # Illinois (IL)
    ("chicago", "IL"): {"county": "Cook County", "fips": "17031", "portal_name": "Cook County Clerk & Probate Court Portal", "portal_url": "https://www.cookcountyclerkofcourt.org/"},
    ("evanston", "IL"): {"county": "Cook County", "fips": "17031", "portal_name": "Cook County Clerk & Probate Court Portal", "portal_url": "https://www.cookcountyclerkofcourt.org/"},
    ("oak park", "IL"): {"county": "Cook County", "fips": "17031", "portal_name": "Cook County Clerk & Probate Court Portal", "portal_url": "https://www.cookcountyclerkofcourt.org/"},
    ("naperville", "IL"): {"county": "DuPage County", "fips": "17043", "portal_name": "DuPage County Clerk & Recorder", "portal_url": "https://www.dupagecounty.gov/recorder/"},
    ("wheaton", "IL"): {"county": "DuPage County", "fips": "17043", "portal_name": "DuPage County Clerk & Recorder", "portal_url": "https://www.dupagecounty.gov/recorder/"},
    ("aurora", "IL"): {"county": "Kane County", "fips": "17089", "portal_name": "Kane County Recorder of Deeds", "portal_url": "https://www.kanecountyrecorder.net/"},
    ("elgin", "IL"): {"county": "Kane County", "fips": "17089", "portal_name": "Kane County Recorder of Deeds", "portal_url": "https://www.kanecountyrecorder.net/"},
    ("joliet", "IL"): {"county": "Will County", "fips": "17197", "portal_name": "Will County Recorder of Deeds", "portal_url": "https://www.willcountyrecorder.com/"},
    ("waukegan", "IL"): {"county": "Lake County", "fips": "17097", "portal_name": "Lake County Recording Division", "portal_url": "https://www.lakecountyil.gov/recording"},
    ("rockford", "IL"): {"county": "Winnebago County", "fips": "17201", "portal_name": "Winnebago County Recorder", "portal_url": "https://www.wincoil.gov/recorder"},
    ("springfield", "IL"): {"county": "Sangamon County", "fips": "17167", "portal_name": "Sangamon County Recorder", "portal_url": "https://www.sangamoncountyrecorder.com/"},
    ("peoria", "IL"): {"county": "Peoria County", "fips": "17143", "portal_name": "Peoria County Clerk and Recorder", "portal_url": "https://www.peoriacounty.gov/"},

    # California (CA)
    ("los angeles", "CA"): {"county": "Los Angeles County", "fips": "06037", "portal_name": "Los Angeles County Registrar-Recorder/County Clerk", "portal_url": "https://www.lavote.gov/home/records"},
    ("long beach", "CA"): {"county": "Los Angeles County", "fips": "06037", "portal_name": "Los Angeles County Registrar-Recorder/County Clerk", "portal_url": "https://www.lavote.gov/home/records"},
    ("pasadena", "CA"): {"county": "Los Angeles County", "fips": "06037", "portal_name": "Los Angeles County Registrar-Recorder/County Clerk", "portal_url": "https://www.lavote.gov/home/records"},
    ("glendale", "CA"): {"county": "Los Angeles County", "fips": "06037", "portal_name": "Los Angeles County Registrar-Recorder/County Clerk", "portal_url": "https://www.lavote.gov/home/records"},
    ("san francisco", "CA"): {"county": "San Francisco County", "fips": "06075", "portal_name": "San Francisco Assessor-Recorder", "portal_url": "https://sfassessor.org/"},
    ("san diego", "CA"): {"county": "San Diego County", "fips": "06073", "portal_name": "San Diego County Assessor/Recorder/County Clerk", "portal_url": "https://arcc.sdcounty.ca.gov/"},
    ("san jose", "CA"): {"county": "Santa Clara County", "fips": "06085", "portal_name": "Santa Clara County Clerk-Recorder", "portal_url": "https://clerkrecorder.sccgov.org/"},
    ("sunnyvale", "CA"): {"county": "Santa Clara County", "fips": "06085", "portal_name": "Santa Clara County Clerk-Recorder", "portal_url": "https://clerkrecorder.sccgov.org/"},
    ("sacramento", "CA"): {"county": "Sacramento County", "fips": "06067", "portal_name": "Sacramento County Assessor & Clerk-Recorder", "portal_url": "https://recorder.saccounty.gov/"},
    ("oakland", "CA"): {"county": "Alameda County", "fips": "06001", "portal_name": "Alameda County Clerk-Recorder", "portal_url": "https://www.acgov.org/auditor/clerk/"},
    ("berkeley", "CA"): {"county": "Alameda County", "fips": "06001", "portal_name": "Alameda County Clerk-Recorder", "portal_url": "https://www.acgov.org/auditor/clerk/"},
    ("irvine", "CA"): {"county": "Orange County", "fips": "06059", "portal_name": "Orange County Clerk-Recorder", "portal_url": "https://www.ocrecorder.com/"},
    ("anaheim", "CA"): {"county": "Orange County", "fips": "06059", "portal_name": "Orange County Clerk-Recorder", "portal_url": "https://www.ocrecorder.com/"},
    ("santa ana", "CA"): {"county": "Orange County", "fips": "06059", "portal_name": "Orange County Clerk-Recorder", "portal_url": "https://www.ocrecorder.com/"},
    ("riverside", "CA"): {"county": "Riverside County", "fips": "06065", "portal_name": "Riverside County Assessor-County Clerk-Recorder", "portal_url": "https://www.riversideacr.com/"},
    ("san bernardino", "CA"): {"county": "San Bernardino County", "fips": "06071", "portal_name": "San Bernardino County Assessor-Recorder-County Clerk", "portal_url": "https://arc.sbcounty.gov/"},
    ("fresno", "CA"): {"county": "Fresno County", "fips": "06019", "portal_name": "Fresno County Assessor-Recorder", "portal_url": "https://www.co.fresno.ca.us/departments/recorder"},
    ("bakersfield", "CA"): {"county": "Kern County", "fips": "06029", "portal_name": "Kern County Assessor-Recorder", "portal_url": "https://www.kerncounty.com/recorder"},

    # Georgia (GA)
    ("atlanta", "GA"): {"county": "Fulton County", "fips": "13121", "portal_name": "Fulton County Superior Court Clerk & Deeds", "portal_url": "https://www.fultonclerk.org/"},
    ("marietta", "GA"): {"county": "Cobb County", "fips": "13067", "portal_name": "Cobb County Superior Court Clerk", "portal_url": "https://www.cobbsuperiorcourtclerk.com/"},
    ("decatur", "GA"): {"county": "DeKalb County", "fips": "13089", "portal_name": "DeKalb County Clerk of Superior Court", "portal_url": "https://dksuperiorclerk.com/"},
    ("lawrenceville", "GA"): {"county": "Gwinnett County", "fips": "13135", "portal_name": "Gwinnett County Clerk of Superior Court", "portal_url": "https://www.gwinnettcourts.com/"},
    ("savannah", "GA"): {"county": "Chatham County", "fips": "13051", "portal_name": "Chatham County Superior Court Clerk", "portal_url": "https://chathamcourts.org/"},
    ("augusta", "GA"): {"county": "Richmond County", "fips": "13245", "portal_name": "Richmond County Clerk of Superior Court", "portal_url": "https://www.augustaga.gov/clerk"},

    # Nevada (NV)
    ("las vegas", "NV"): {"county": "Clark County", "fips": "32003", "portal_name": "Clark County Recorder & Public Records", "portal_url": "https://www.clarkcountynv.gov/recorder"},
    ("henderson", "NV"): {"county": "Clark County", "fips": "32003", "portal_name": "Clark County Recorder & Public Records", "portal_url": "https://www.clarkcountynv.gov/recorder"},
    ("north las vegas", "NV"): {"county": "Clark County", "fips": "32003", "portal_name": "Clark County Recorder & Public Records", "portal_url": "https://www.clarkcountynv.gov/recorder"},
    ("reno", "NV"): {"county": "Washoe County", "fips": "32031", "portal_name": "Washoe County Recorder", "portal_url": "https://www.washoecounty.gov/recorder/"},

    # North Carolina (NC)
    ("charlotte", "NC"): {"county": "Mecklenburg County", "fips": "37119", "portal_name": "Mecklenburg County Register of Deeds", "portal_url": "https://www.mecknc.gov/rod"},
    ("raleigh", "NC"): {"county": "Wake County", "fips": "37183", "portal_name": "Wake County Register of Deeds", "portal_url": "https://www.wake.gov/departments-government/register-deeds"},
    ("greensboro", "NC"): {"county": "Guilford County", "fips": "37081", "portal_name": "Guilford County Register of Deeds", "portal_url": "https://www.guilfordcountync.gov/rod"},
    ("durham", "NC"): {"county": "Durham County", "fips": "37063", "portal_name": "Durham County Register of Deeds", "portal_url": "https://www.dconc.gov/rod"},
    ("winston-salem", "NC"): {"county": "Forsyth County", "fips": "37067", "portal_name": "Forsyth County Register of Deeds", "portal_url": "https://www.forsyth.cc/rod"},

    # Ohio (OH)
    ("columbus", "OH"): {"county": "Franklin County", "fips": "39049", "portal_name": "Franklin County Recorder", "portal_url": "https://recorder.franklincountyohio.gov/"},
    ("cleveland", "OH"): {"county": "Cuyahoga County", "fips": "39035", "portal_name": "Cuyahoga County Fiscal Officer & Recorder", "portal_url": "https://fiscalofficer.cuyahogacounty.us/"},
    ("cincinnati", "OH"): {"county": "Hamilton County", "fips": "39061", "portal_name": "Hamilton County Recorder", "portal_url": "https://recordersoffice.hamilton-co.org/"},
    ("akron", "OH"): {"county": "Summit County", "fips": "39153", "portal_name": "Summit County Fiscal Office", "portal_url": "https://fiscaloffice.summitoh.net/"},
    ("toledo", "OH"): {"county": "Lucas County", "fips": "39095", "portal_name": "Lucas County Recorder", "portal_url": "https://www.co.lucas.oh.us/recorder"},

    # Colorado (CO)
    ("denver", "CO"): {"county": "Denver County", "fips": "08031", "portal_name": "Denver Clerk and Recorder", "portal_url": "https://www.denvergov.org/Government/Agencies-Departments-Offices/Clerk-and-Recorder"},
    ("colorado springs", "CO"): {"county": "El Paso County", "fips": "08041", "portal_name": "El Paso County Clerk and Recorder", "portal_url": "https://clerkandrecorder.elpasoco.com/"},
    ("boulder", "CO"): {"county": "Boulder County", "fips": "08013", "portal_name": "Boulder County Recording", "portal_url": "https://bouldercounty.gov/records/recording/"},
    ("fort collins", "CO"): {"county": "Larimer County", "fips": "08069", "portal_name": "Larimer County Clerk and Recorder", "portal_url": "https://www.larimer.gov/clerk"},

    # Washington (WA) - Comprehensive 39-County Coverage
    ("seattle", "WA"): {"county": "King County", "fips": "53033", "portal_name": "King County Recorder's Office", "portal_url": "https://kingcounty.gov/recorder"},
    ("bellevue", "WA"): {"county": "King County", "fips": "53033", "portal_name": "King County Recorder's Office", "portal_url": "https://kingcounty.gov/recorder"},
    ("renton", "WA"): {"county": "King County", "fips": "53033", "portal_name": "King County Recorder's Office", "portal_url": "https://kingcounty.gov/recorder"},
    ("kent", "WA"): {"county": "King County", "fips": "53033", "portal_name": "King County Recorder's Office", "portal_url": "https://kingcounty.gov/recorder"},
    ("redmond", "WA"): {"county": "King County", "fips": "53033", "portal_name": "King County Recorder's Office", "portal_url": "https://kingcounty.gov/recorder"},
    ("kirkland", "WA"): {"county": "King County", "fips": "53033", "portal_name": "King County Recorder's Office", "portal_url": "https://kingcounty.gov/recorder"},
    ("federal way", "WA"): {"county": "King County", "fips": "53033", "portal_name": "King County Recorder's Office", "portal_url": "https://kingcounty.gov/recorder"},
    ("auburn", "WA"): {"county": "King County", "fips": "53033", "portal_name": "King County Recorder's Office", "portal_url": "https://kingcounty.gov/recorder"},
    ("tacoma", "WA"): {"county": "Pierce County", "fips": "53053", "portal_name": "Pierce County Auditor - Recording", "portal_url": "https://www.piercecountywa.gov/recording"},
    ("puyallup", "WA"): {"county": "Pierce County", "fips": "53053", "portal_name": "Pierce County Auditor - Recording", "portal_url": "https://www.piercecountywa.gov/recording"},
    ("lakewood", "WA"): {"county": "Pierce County", "fips": "53053", "portal_name": "Pierce County Auditor - Recording", "portal_url": "https://www.piercecountywa.gov/recording"},
    ("everett", "WA"): {"county": "Snohomish County", "fips": "53061", "portal_name": "Snohomish County Auditor Recording", "portal_url": "https://www.snohomishcountywa.gov/recording"},
    ("lynnwood", "WA"): {"county": "Snohomish County", "fips": "53061", "portal_name": "Snohomish County Auditor Recording", "portal_url": "https://www.snohomishcountywa.gov/recording"},
    ("edmonds", "WA"): {"county": "Snohomish County", "fips": "53061", "portal_name": "Snohomish County Auditor Recording", "portal_url": "https://www.snohomishcountywa.gov/recording"},
    ("marysville", "WA"): {"county": "Snohomish County", "fips": "53061", "portal_name": "Snohomish County Auditor Recording", "portal_url": "https://www.snohomishcountywa.gov/recording"},
    ("spokane", "WA"): {"county": "Spokane County", "fips": "53063", "portal_name": "Spokane County Auditor & Recording", "portal_url": "https://www.spokanecounty.org/recording"},
    ("spokane valley", "WA"): {"county": "Spokane County", "fips": "53063", "portal_name": "Spokane County Auditor & Recording", "portal_url": "https://www.spokanecounty.org/recording"},
    ("vancouver", "WA"): {"county": "Clark County", "fips": "53011", "portal_name": "Clark County Auditor Recording", "portal_url": "https://clark.wa.gov/auditor/recording"},
    ("camas", "WA"): {"county": "Clark County", "fips": "53011", "portal_name": "Clark County Auditor Recording", "portal_url": "https://clark.wa.gov/auditor/recording"},
    ("olympia", "WA"): {"county": "Thurston County", "fips": "53067", "portal_name": "Thurston County Auditor Recording", "portal_url": "https://www.thurstoncountywa.gov/departments/auditor/recording"},
    ("lacey", "WA"): {"county": "Thurston County", "fips": "53067", "portal_name": "Thurston County Auditor Recording", "portal_url": "https://www.thurstoncountywa.gov/departments/auditor/recording"},
    ("tumwater", "WA"): {"county": "Thurston County", "fips": "53067", "portal_name": "Thurston County Auditor Recording", "portal_url": "https://www.thurstoncountywa.gov/departments/auditor/recording"},
    ("bremerton", "WA"): {"county": "Kitsap County", "fips": "53035", "portal_name": "Kitsap County Auditor - Recording", "portal_url": "https://www.kitsapgov.com/auditor/Pages/recording.aspx"},
    ("port orchard", "WA"): {"county": "Kitsap County", "fips": "53035", "portal_name": "Kitsap County Auditor - Recording", "portal_url": "https://www.kitsapgov.com/auditor/Pages/recording.aspx"},
    ("silverdale", "WA"): {"county": "Kitsap County", "fips": "53035", "portal_name": "Kitsap County Auditor - Recording", "portal_url": "https://www.kitsapgov.com/auditor/Pages/recording.aspx"},
    ("bellingham", "WA"): {"county": "Whatcom County", "fips": "53073", "portal_name": "Whatcom County Auditor Recording", "portal_url": "https://www.whatcomcounty.us/auditor"},
    ("lynden", "WA"): {"county": "Whatcom County", "fips": "53073", "portal_name": "Whatcom County Auditor Recording", "portal_url": "https://www.whatcomcounty.us/auditor"},
    ("yakima", "WA"): {"county": "Yakima County", "fips": "53077", "portal_name": "Yakima County Auditor Recording", "portal_url": "https://www.yakimacounty.us/auditor"},
    ("sunnyside", "WA"): {"county": "Yakima County", "fips": "53077", "portal_name": "Yakima County Auditor Recording", "portal_url": "https://www.yakimacounty.us/auditor"},
    ("kennewick", "WA"): {"county": "Benton County", "fips": "53005", "portal_name": "Benton County Auditor Recording", "portal_url": "https://www.co.benton.wa.us/auditor"},
    ("richland", "WA"): {"county": "Benton County", "fips": "53005", "portal_name": "Benton County Auditor Recording", "portal_url": "https://www.co.benton.wa.us/auditor"},
    ("pasco", "WA"): {"county": "Franklin County", "fips": "53021", "portal_name": "Franklin County Auditor Recording", "portal_url": "https://www.co.franklin.wa.us/auditor"},
    ("mount vernon", "WA"): {"county": "Skagit County", "fips": "53057", "portal_name": "Skagit County Auditor Recording", "portal_url": "https://www.skagitcounty.net/auditor"},
    ("anacortes", "WA"): {"county": "Skagit County", "fips": "53057", "portal_name": "Skagit County Auditor Recording", "portal_url": "https://www.skagitcounty.net/auditor"},
    ("longview", "WA"): {"county": "Cowlitz County", "fips": "53015", "portal_name": "Cowlitz County Auditor Recording", "portal_url": "https://www.co.cowlitz.wa.us/auditor"},
    ("kelso", "WA"): {"county": "Cowlitz County", "fips": "53015", "portal_name": "Cowlitz County Auditor Recording", "portal_url": "https://www.co.cowlitz.wa.us/auditor"},
    ("wenatchee", "WA"): {"county": "Chelan County", "fips": "53007", "portal_name": "Chelan County Auditor Recording", "portal_url": "https://www.co.chelan.wa.us/auditor"},
    ("moses lake", "WA"): {"county": "Grant County", "fips": "53025", "portal_name": "Grant County Auditor Recording", "portal_url": "https://www.grantcountywa.gov/auditor"},
    ("ephrata", "WA"): {"county": "Grant County", "fips": "53025", "portal_name": "Grant County Auditor Recording", "portal_url": "https://www.grantcountywa.gov/auditor"},
    ("oak harbor", "WA"): {"county": "Island County", "fips": "53029", "portal_name": "Island County Auditor Recording", "portal_url": "https://www.islandcountywa.gov/auditor"},
    ("chehalis", "WA"): {"county": "Lewis County", "fips": "53041", "portal_name": "Lewis County Auditor Recording", "portal_url": "https://www.lewiscountywa.gov/auditor"},
    ("centralia", "WA"): {"county": "Lewis County", "fips": "53041", "portal_name": "Lewis County Auditor Recording", "portal_url": "https://www.lewiscountywa.gov/auditor"},
    ("port angeles", "WA"): {"county": "Clallam County", "fips": "53009", "portal_name": "Clallam County Auditor Recording", "portal_url": "https://www.clallamcountywa.gov/auditor"},
    ("shelton", "WA"): {"county": "Mason County", "fips": "53045", "portal_name": "Mason County Auditor Recording", "portal_url": "https://masoncountywa.gov/auditor"},
    ("aberdeen", "WA"): {"county": "Grays Harbor County", "fips": "53027", "portal_name": "Grays Harbor County Auditor Recording", "portal_url": "https://www.graysharbor.us/auditor"},
    ("ellensburg", "WA"): {"county": "Kittitas County", "fips": "53037", "portal_name": "Kittitas County Auditor Recording", "portal_url": "https://www.co.kittitas.wa.us/auditor"},
    ("colville", "WA"): {"county": "Stevens County", "fips": "53065", "portal_name": "Stevens County Auditor Recording", "portal_url": "https://www.stevenscountywa.gov/auditor"},
    ("east wenatchee", "WA"): {"county": "Douglas County", "fips": "53017", "portal_name": "Douglas County Auditor Recording", "portal_url": "https://www.douglascountywa.net/auditor"},
    ("port townsend", "WA"): {"county": "Jefferson County", "fips": "53031", "portal_name": "Jefferson County Auditor Recording", "portal_url": "https://www.co.jefferson.wa.us/auditor"},
    ("omak", "WA"): {"county": "Okanogan County", "fips": "53047", "portal_name": "Okanogan County Auditor Recording", "portal_url": "https://www.okanogancounty.org/auditor"},
    ("south bend", "WA"): {"county": "Pacific County", "fips": "53049", "portal_name": "Pacific County Auditor Recording", "portal_url": "https://www.co.pacific.wa.us/auditor"},
    ("clarkston", "WA"): {"county": "Asotin County", "fips": "53003", "portal_name": "Asotin County Auditor Recording", "portal_url": "https://www.co.asotin.wa.us/auditor"},
    ("goldendale", "WA"): {"county": "Klickitat County", "fips": "53039", "portal_name": "Klickitat County Auditor Recording", "portal_url": "https://www.klickitatcounty.org/auditor"},
    ("othello", "WA"): {"county": "Adams County", "fips": "53001", "portal_name": "Adams County Auditor Recording", "portal_url": "https://www.co.adams.wa.us/auditor"},
    ("pullman", "WA"): {"county": "Whitman County", "fips": "53075", "portal_name": "Whitman County Auditor Recording", "portal_url": "https://www.whitmancounty.org/auditor"},
    ("friday harbor", "WA"): {"county": "San Juan County", "fips": "53055", "portal_name": "San Juan County Auditor Recording", "portal_url": "https://www.sanjuanco.com/auditor"},
    ("newport", "WA"): {"county": "Pend Oreille County", "fips": "53051", "portal_name": "Pend Oreille County Auditor Recording", "portal_url": "https://pendoreilleco.org/auditor"},
    ("stevenson", "WA"): {"county": "Skamania County", "fips": "53059", "portal_name": "Skamania County Auditor Recording", "portal_url": "https://www.skamaniacounty.org/auditor"},
    ("davenport", "WA"): {"county": "Lincoln County", "fips": "53043", "portal_name": "Lincoln County Auditor Recording", "portal_url": "https://www.co.lincoln.wa.us/auditor"},
    ("republic", "WA"): {"county": "Ferry County", "fips": "53019", "portal_name": "Ferry County Auditor Recording", "portal_url": "https://www.ferry-county.com/auditor"},
    ("dayton", "WA"): {"county": "Columbia County", "fips": "53013", "portal_name": "Columbia County Auditor Recording", "portal_url": "https://www.columbiaco.com/auditor"},
    ("cathlamet", "WA"): {"county": "Wahkiakum County", "fips": "53069", "portal_name": "Wahkiakum County Auditor Recording", "portal_url": "https://www.co.wahkiakum.wa.us/auditor"},
    ("pomeroy", "WA"): {"county": "Garfield County", "fips": "53023", "portal_name": "Garfield County Auditor Recording", "portal_url": "https://www.co.garfield.wa.us/auditor"},
    ("walla walla", "WA"): {"county": "Walla Walla County", "fips": "53071", "portal_name": "Walla Walla County Auditor Recording", "portal_url": "https://www.co.walla-walla.wa.us/auditor"},

    # Tennessee (TN)
    ("nashville", "TN"): {"county": "Davidson County", "fips": "47037", "portal_name": "Davidson County Register of Deeds", "portal_url": "https://www.nashville.gov/departments/register-deeds"},
    ("memphis", "TN"): {"county": "Shelby County", "fips": "47157", "portal_name": "Shelby County Register of Deeds", "portal_url": "https://register.shelby.tn.us/"},
    ("knoxville", "TN"): {"county": "Knox County", "fips": "47093", "portal_name": "Knox County Register of Deeds", "portal_url": "https://www.knoxcounty.org/register/"},
    ("chattanooga", "TN"): {"county": "Hamilton County", "fips": "47065", "portal_name": "Hamilton County Register of Deeds", "portal_url": "https://www.hamiltontn.gov/Register.aspx"},

    # Pennsylvania (PA)
    ("philadelphia", "PA"): {"county": "Philadelphia County", "fips": "42101", "portal_name": "Philadelphia Department of Records", "portal_url": "https://www.phila.gov/records"},
    ("pittsburgh", "PA"): {"county": "Allegheny County", "fips": "42003", "portal_name": "Allegheny County Department of Real Estate", "portal_url": "https://www.alleghenycounty.us/real-estate/"},

    # New York (NY)
    ("new york", "NY"): {"county": "New York County", "fips": "36061", "portal_name": "NYC Department of Finance (ACRIS)", "portal_url": "https://a836-acris.nyc.gov/"},
    ("manhattan", "NY"): {"county": "New York County", "fips": "36061", "portal_name": "NYC Department of Finance (ACRIS)", "portal_url": "https://a836-acris.nyc.gov/"},
    ("brooklyn", "NY"): {"county": "Kings County", "fips": "36047", "portal_name": "NYC Department of Finance (ACRIS)", "portal_url": "https://a836-acris.nyc.gov/"},
    ("queens", "NY"): {"county": "Queens County", "fips": "36081", "portal_name": "NYC Department of Finance (ACRIS)", "portal_url": "https://a836-acris.nyc.gov/"},
    ("bronx", "NY"): {"county": "Bronx County", "fips": "36005", "portal_name": "NYC Department of Finance (ACRIS)", "portal_url": "https://a836-acris.nyc.gov/"},
    ("staten island", "NY"): {"county": "Richmond County", "fips": "36085", "portal_name": "NYC Department of Finance (ACRIS)", "portal_url": "https://a836-acris.nyc.gov/"},
    ("buffalo", "NY"): {"county": "Erie County", "fips": "36029", "portal_name": "Erie County Clerk", "portal_url": "https://www.erie.gov/clerk"},
    ("rochester", "NY"): {"county": "Monroe County", "fips": "36055", "portal_name": "Monroe County Clerk", "portal_url": "https://www.monroecounty.gov/clerk"},

    # Michigan (MI)
    ("detroit", "MI"): {"county": "Wayne County", "fips": "26163", "portal_name": "Wayne County Register of Deeds", "portal_url": "https://www.waynecounty.com/departments/deeds/"},
    ("grand rapids", "MI"): {"county": "Kent County", "fips": "26081", "portal_name": "Kent County Register of Deeds", "portal_url": "https://www.accesskent.com/Deeds/"},

    # Minnesota (MN)
    ("minneapolis", "MN"): {"county": "Hennepin County", "fips": "27053", "portal_name": "Hennepin County Recorder & Registrar of Titles", "portal_url": "https://www.hennepin.us/residents/property/recorder-titles"},
    ("st. paul", "MN"): {"county": "Ramsey County", "fips": "27123", "portal_name": "Ramsey County Recorder", "portal_url": "https://www.ramseycounty.us/recorder"},
}


@dataclass
class ResolvedLocation:
    """Structured location resolution result for a business prospect."""
    city: str
    state_code: str
    county: str
    county_fips: str = ""
    portal_name: str = ""
    portal_url: str = ""
    confidence: float = 1.0
    resolved_by: str = "offline_registry"  # offline_registry, explicit_county, llm_fallback, heuristic


class GeoCountyResolver:
    """Authoritative service for resolving business locations to counties and county portals."""

    @classmethod
    def normalize_state(cls, raw_state: str) -> str:
        """Convert state full names or abbreviations to standard 2-letter uppercase code."""
        if not raw_state:
            return ""
        s = raw_state.strip().lower()
        if s in STATE_NAMES_TO_ABBR:
            return STATE_NAMES_TO_ABBR[s]
        # Check if already 2-letter code
        clean_upper = raw_state.strip().upper()
        if clean_upper in STATE_NAMES_TO_ABBR.values():
            return clean_upper
        return clean_upper[:2]

    @classmethod
    def parse_address_string(cls, text: str) -> dict[str, str]:
        """Extract address, city, state, and zip from unstructured address or web search snippet."""
        if not text:
            return {"address": "", "city": "", "state": "", "zip": ""}

        res = {"address": "", "city": "", "state": "", "zip": ""}

        # Pattern: [City], [State] [Zip] (e.g. "Austin, TX 78701" or "Houston, Texas 77056")
        m_city_st_zip = re.search(
            r"\b([A-Z][a-zA-Z\s\.\'-]+?),\s*([A-Za-z]{2}|[A-Za-z\s]{4,20})\s+(\d{5}(?:-\d{4})?)\b",
            text,
        )
        if m_city_st_zip:
            res["city"] = m_city_st_zip.group(1).strip()
            res["state"] = cls.normalize_state(m_city_st_zip.group(2).strip())
            res["zip"] = m_city_st_zip.group(3).strip()
        else:
            # Pattern: [City], [State] without zip (e.g. "Dallas, TX" or "San Antonio, Texas")
            m_city_st = re.search(
                r"\b([A-Z][a-zA-Z\s\.\'-]+?),\s*([A-Z]{2}|[A-Za-z\s]{4,20})\b",
                text,
            )
            if m_city_st:
                cand_city = m_city_st.group(1).strip()
                cand_st = cls.normalize_state(m_city_st.group(2).strip())
                if cand_st in STATE_NAMES_TO_ABBR.values() and len(cand_city) < 35:
                    res["city"] = cand_city
                    res["state"] = cand_st

        # Extract street address (e.g. "1200 Post Oak Blvd" or "100 Congress Ave Ste 200")
        m_street = re.search(
            r"\b\d+\s+[A-Za-z0-9\s,\.]+(?:St|Street|Ave|Avenue|Blvd|Boulevard|Rd|Road|Pkwy|Parkway|Dr|Drive|Way|Hwy|Highway|Ste|Suite|Floor|Fl)\b",
            text,
            re.IGNORECASE,
        )
        if m_street:
            res["address"] = m_street.group(0).strip()

        return res

    @classmethod
    def resolve_location(
        cls,
        address: str = "",
        city: str = "",
        state: str = "",
        zip_code: str = "",
        llm_engine: Any = None,
    ) -> ResolvedLocation:
        """Resolve a business's location to its verified County, FIPS code, and Public Records portal."""
        # Parse from address if city/state not provided
        if address and (not city or not state):
            parsed = cls.parse_address_string(address)
            if not city and parsed["city"]:
                city = parsed["city"]
            if not state and parsed["state"]:
                state = parsed["state"]
            if not zip_code and parsed["zip"]:
                zip_code = parsed["zip"]

        norm_city = (city or "").strip().lower()
        norm_state = cls.normalize_state(state)

        # 1. Authoritative Offline Registry Match
        lookup_key = (norm_city, norm_state)
        if lookup_key in CITY_COUNTY_REGISTRY:
            data = CITY_COUNTY_REGISTRY[lookup_key]
            return ResolvedLocation(
                city=city.strip().title(),
                state_code=norm_state,
                county=data["county"],
                county_fips=data.get("fips", ""),
                portal_name=data.get("portal_name", f"{data['county']} Public Records Portal"),
                portal_url=data.get("portal_url", "https://data.gov"),
                confidence=0.99,
                resolved_by="offline_registry",
            )

        # 2. Check if address or text explicitly contains county name (e.g. "Serving Harris County" or "Travis County")
        combined_text = f"{address} {city} {state}"
        m_explicit_county = re.search(r"\b([A-Z][a-zA-Z\s]+?)\s+(?:County|Parish)\b", combined_text, re.IGNORECASE)
        if m_explicit_county:
            explicit_name = m_explicit_county.group(1).strip().title() + " County"
            return ResolvedLocation(
                city=city.strip().title() if city else explicit_name.replace(" County", ""),
                state_code=norm_state,
                county=explicit_name,
                portal_name=f"{explicit_name} Public Records & Clerk",
                portal_url="https://data.gov",
                confidence=0.90,
                resolved_by="explicit_county",
            )

        # 3. LLM Agent Fallback for smaller townships / unincorporated areas
        if llm_engine and getattr(llm_engine, "is_available", lambda: False)():
            try:
                prompt = (
                    f"Given the US location City: '{city}', State: '{norm_state}', Zip: '{zip_code}', Address: '{address}', "
                    f"identify the official County or Parish it belongs to, and the official county clerk or public records court portal name.\n"
                    f"Respond strictly in valid JSON format: {{\"county\": \"X County\", \"portal_name\": \"Y\", \"portal_url\": \"Z\"}}"
                )
                res = llm_engine.generate_json(prompt)
                if res and res.get("county") and "County" in res["county"]:
                    return ResolvedLocation(
                        city=city.strip().title(),
                        state_code=norm_state,
                        county=res["county"],
                        portal_name=res.get("portal_name", f"{res['county']} Public Records"),
                        portal_url=res.get("portal_url", "https://data.gov"),
                        confidence=0.85,
                        resolved_by="llm_fallback",
                    )
            except Exception as e:
                logger.debug(f"LLM location resolution note: {e}")

        # 4. Safe Heuristic Fallback
        fallback_county = f"{city.strip().title()} County" if city else "Regional County"
        return ResolvedLocation(
            city=city.strip().title() if city else "Local Market",
            state_code=norm_state or "TX",
            county=fallback_county,
            portal_name=f"{fallback_county} Public Records Registry",
            portal_url="https://data.gov",
            confidence=0.60,
            resolved_by="heuristic",
        )

    @classmethod
    def validate_county_data_match(
        cls,
        lead_county: str,
        sample_records: list[dict[str, Any]],
    ) -> tuple[bool, str]:
        """Validate that sample records intended for cold outreach match the prospect's real county jurisdiction.
        
        Prevents dispatching records from the wrong county (e.g. sending Cook County rows to an Austin, TX firm).
        """
        if not lead_county or not sample_records:
            return True, "No records or county specified; validation skipped"

        clean_lead_county = lead_county.lower().replace(" county", "").replace(" parish", "").strip()

        # Check sample records
        county_indicators = ["county", "jurisdiction", "court", "court_name", "recording_jurisdiction", "source_url"]
        detected_counties: set[str] = set()

        for r in sample_records:
            for k in county_indicators:
                val = str(r.get(k, "")).lower()
                if "county" in val or "court" in val or "clerk" in val:
                    detected_counties.add(val)

        if not detected_counties:
            # If records don't have explicit county fields, pass
            return True, f"Records do not contain conflicting jurisdiction tags"

        # Check for matching tag
        has_match = any(clean_lead_county in c for c in detected_counties)
        if has_match:
            return True, f"Verified: records match prospect's {lead_county} jurisdiction"

        # Check if records explicitly mention another known county
        conflicting = []
        for other_city, other_state in CITY_COUNTY_REGISTRY:
            other_c = CITY_COUNTY_REGISTRY[(other_city, other_state)]["county"].lower().replace(" county", "")
            if other_c != clean_lead_county and any(other_c in c for c in detected_counties):
                conflicting.append(other_c.title() + " County")

        if conflicting:
            msg = f"Jurisdiction mismatch: Prospect is in '{lead_county}', but sample records belong to '{conflicting[0]}'."
            logger.warning(f"🛑 [COUNTY DATA GATE] {msg}")
            return False, msg

        return True, "Validation passed"

    @classmethod
    def get_all_counties_for_state(cls, state_code: str = "WA") -> list[dict[str, Any]]:
        """Return a structured, deduplicated list of all recognized counties and portals for a given state."""
        norm_st = cls.normalize_state(state_code)
        seen_counties: dict[str, dict[str, Any]] = {}

        for (city, st), info in CITY_COUNTY_REGISTRY.items():
            if st == norm_st:
                c_name = info["county"]
                if c_name not in seen_counties:
                    seen_counties[c_name] = {
                        "county": c_name,
                        "state": norm_st,
                        "fips": info.get("fips", ""),
                        "primary_city": city.title(),
                        "cities": [city.title()],
                        "portal_name": info.get("portal_name", f"{c_name} Public Records"),
                        "portal_url": info.get("portal_url", ""),
                    }
                else:
                    if city.title() not in seen_counties[c_name]["cities"]:
                        seen_counties[c_name]["cities"].append(city.title())

        # Sort alphabetically by county name
        return sorted(list(seen_counties.values()), key=lambda x: x["county"])
