"""Unified AI Specialist Tool Registry for LeadOps Autonomous Agents.

Defines schemas and execution handlers for Search, Page Fetch, Contact Extraction,
WAF Probing, and DOM Layout Parsing.
"""

import json
import logging
from typing import Any, Callable

from .web_search import search_web, search_company_intelligence, search_public_data_portals
from .web_fetcher import fetch_page_content, extract_contact_info_from_url, extract_portal_sample_data
from .waf_prober import probe_waf_signatures, generate_browser_headers
from .dom_pruner import prune_dom_tree

logger = logging.getLogger("tools.registry")

AI_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Perform a live web search for companies, public records, government portals, or leadership contacts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query string."},
                    "max_results": {"type": "integer", "description": "Maximum number of search results to return (default 5)."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_company_intelligence",
            "description": "Search and enrich corporate intelligence, headquarters location, and executive leadership for a business.",
            "parameters": {
                "type": "object",
                "properties": {
                    "company_name": {"type": "string", "description": "Legal or operating name of the target company."},
                    "domain_hint": {"type": "string", "description": "Optional website domain if known."},
                },
                "required": ["company_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_public_data_portals",
            "description": "Search for official state, county, or municipal open data portals, permit databases, or court dockets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "niche": {"type": "string", "description": "Data vertical (e.g. 'building permits', 'probate court', 'UCC liens')."},
                    "jurisdiction": {"type": "string", "description": "State, county, or municipality name."},
                },
                "required": ["niche", "jurisdiction"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_page_content",
            "description": "Fetch a live web page, extracting page title, description, body text, emails, and phone numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Target webpage URL to fetch."},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "extract_contact_info_from_url",
            "description": "Extract verified corporate contact emails and phone numbers from a company website.",
            "parameters": {
                "type": "object",
                "properties": {
                    "website_url": {"type": "string", "description": "Target company website URL."},
                },
                "required": ["website_url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "probe_waf_signatures",
            "description": "Probe a target website's HTTP headers and HTML body to detect Cloudflare, Akamai, or bot protection.",
            "parameters": {
                "type": "object",
                "properties": {
                    "headers": {"type": "object", "description": "HTTP response headers dict."},
                    "body_text": {"type": "string", "description": "HTTP response body text."},
                    "status_code": {"type": "integer", "description": "HTTP status code."},
                },
                "required": ["headers", "body_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "prune_dom_tree",
            "description": "Prune raw HTML into lightweight AST nodes and extract table data rows and columns.",
            "parameters": {
                "type": "object",
                "properties": {
                    "html": {"type": "string", "description": "Raw HTML string."},
                    "max_nodes": {"type": "integer", "description": "Maximum number of DOM nodes to return."},
                },
                "required": ["html"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "extract_portal_sample_data",
            "description": "Fetch live data portal URL and extract structured sample records directly from live HTML tables or JSON endpoints.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Target data portal URL to extract sample records from."},
                    "max_records": {"type": "integer", "description": "Maximum number of records to sample (default 25)."},
                },
                "required": ["url"],
            },
        },
    },
]


TOOL_HANDLERS: dict[str, Callable[..., Any]] = {
    "search_web": search_web,
    "search_company_intelligence": search_company_intelligence,
    "search_public_data_portals": search_public_data_portals,
    "fetch_page_content": fetch_page_content,
    "extract_contact_info_from_url": extract_contact_info_from_url,
    "extract_portal_sample_data": extract_portal_sample_data,
    "probe_waf_signatures": probe_waf_signatures,
    "prune_dom_tree": prune_dom_tree,
}


def execute_tool_call(tool_name: str, arguments: dict[str, Any]) -> Any:
    """Execute a registered specialist tool by name with arguments."""
    handler = TOOL_HANDLERS.get(tool_name)
    if not handler:
        logger.warning(f"Unknown AI tool requested: {tool_name}")
        return {"error": f"Unknown tool: {tool_name}"}
    
    logger.info(f"⚙️ [AI TOOL EXECUTE] Running tool: {tool_name} with args: {list(arguments.keys())}")
    try:
        return handler(**arguments)
    except Exception as e:
        logger.error(f"Error executing AI tool {tool_name}: {e}")
        return {"error": str(e)}
