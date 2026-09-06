"""LeadOps Production Scraper Catalog & Dataset Repository Service.

Indexes, catalogs, and provides fast search and access to all client scraper
source code, extracted datasets (JSON/CSV), execution stats, and QA verification.
"""

import csv
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("scraper_catalog")

BASE_DIR = Path(__file__).resolve().parent.parent
BUILD_ARTIFACTS_DIR = BASE_DIR / "build_artifacts"
CATALOG_JSON_PATH = BUILD_ARTIFACTS_DIR / "scrapers_catalog.json"
CATALOG_MD_PATH = BUILD_ARTIFACTS_DIR / "SCRAPERS_INDEX.md"
CATALOG_CSV_PATH = BUILD_ARTIFACTS_DIR / "scrapers_catalog.csv"


def load_json(path: Path) -> Optional[Any]:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def inspect_lead_artifact(folder: Path) -> Optional[Dict[str, Any]]:
    if not folder.is_dir():
        return None

    lead_id = folder.name
    ai_trace = folder / "ai-log-trace"
    src_scraper = folder / "src" / "scraper" / "portal_scraper.py"
    entry_file = folder / "entry.py"
    output_dir = folder / "output"
    latest_json = output_dir / "latest.json"
    latest_csv = output_dir / "latest.csv"
    initial_sample_json = ai_trace / "01_initial_sample.json"
    scout_intel_json = ai_trace / "01_scout_intelligence.json"
    qa_cert_json = ai_trace / "qa_insurance_certificate.json"
    memory_json = folder / "memory.json"
    qualification_json = ai_trace / "01_qualification_breakdown.json"

    company_name = ""
    portal_name = ""
    portal_url = ""
    commercial_pain = ""

    intel = load_json(scout_intel_json)
    if intel and isinstance(intel, dict):
        company_name = intel.get("company_name", "")
        portal_info = intel.get("target_portal", {})
        if isinstance(portal_info, dict):
            portal_name = portal_info.get("name", "")
            portal_url = portal_info.get("url", "")
        commercial_pain = intel.get("commercial_pain_point", "")

    if not company_name:
        mem = load_json(memory_json)
        if mem and isinstance(mem, dict):
            company_name = mem.get("company_name", "")
            portal_name = portal_name or mem.get("target_portal_name", "")
            portal_url = portal_url or mem.get("target_portal_url", "")

    if not company_name:
        parts = lead_id.replace("lead-", "").split("-")
        clean_parts = [p for p in parts if not p.isdigit()]
        company_name = " ".join(clean_parts).title() or lead_id

    has_scraper_code = src_scraper.exists()
    scraper_size = src_scraper.stat().st_size if has_scraper_code else 0
    has_entry = entry_file.exists()

    has_output = False
    output_records_count = 0
    sample_fields: List[str] = []
    primary_output_path = ""
    output_type = "None"

    if latest_json.exists():
        data = load_json(latest_json)
        if isinstance(data, list):
            output_records_count = len(data)
            has_output = True
            primary_output_path = str(latest_json.relative_to(BASE_DIR))
            output_type = "Executed JSON"
            if data and isinstance(data[0], dict):
                sample_fields = list(data[0].keys())[:8]

    if not has_output and initial_sample_json.exists():
        data = load_json(initial_sample_json)
        if isinstance(data, list):
            output_records_count = len(data)
            has_output = True
            primary_output_path = str(initial_sample_json.relative_to(BASE_DIR))
            output_type = "Scout Sample JSON"
            if data and isinstance(data[0], dict):
                sample_fields = list(data[0].keys())[:8]

    qa_score = None
    qa_status = "Pending"
    qa_cert = load_json(qa_cert_json)
    if qa_cert and isinstance(qa_cert, dict):
        qa_score = qa_cert.get("score") or qa_cert.get("qa_score")
        qa_status = "PASSED (100%)" if qa_score == 100 else f"Scored: {qa_score}"
    elif has_scraper_code and has_output:
        qa_status = "Ready"

    qual_score = None
    qual_data = load_json(qualification_json)
    if qual_data and isinstance(qual_data, dict):
        qual_score = qual_data.get("qualification_score") or qual_data.get("score")

    mtime = folder.stat().st_mtime
    updated_str = datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

    return {
        "lead_id": lead_id,
        "company_name": company_name,
        "portal_name": portal_name,
        "portal_url": portal_url,
        "commercial_pain": commercial_pain,
        "has_scraper_code": has_scraper_code,
        "scraper_code_path": str(src_scraper.relative_to(BASE_DIR)) if has_scraper_code else "",
        "scraper_size_bytes": scraper_size,
        "entry_path": str(entry_file.relative_to(BASE_DIR)) if has_entry else "",
        "has_output_data": has_output,
        "output_records_count": output_records_count,
        "output_type": output_type,
        "primary_output_path": primary_output_path,
        "latest_csv_path": str(latest_csv.relative_to(BASE_DIR)) if latest_csv.exists() else "",
        "sample_fields": sample_fields,
        "qa_status": qa_status,
        "qa_score": qa_score,
        "qualification_score": qual_score,
        "folder_path": str(folder.relative_to(BASE_DIR)),
        "updated_at": updated_str,
    }


def build_catalog() -> List[Dict[str, Any]]:
    if not BUILD_ARTIFACTS_DIR.exists():
        BUILD_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        return []

    entries = []
    for item in sorted(BUILD_ARTIFACTS_DIR.iterdir()):
        if item.is_dir() and (item.name.startswith("lead-") or item.name == "demo-lead" or (item / "src").exists()):
            record = inspect_lead_artifact(item)
            if record:
                entries.append(record)

    entries.sort(key=lambda x: (not x["has_scraper_code"], not x["has_output_data"], x["company_name"]))
    return entries


def write_catalog_files(catalog: List[Dict[str, Any]]) -> None:
    try:
        with open(CATALOG_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(catalog, f, indent=2)

        lines = [
            "# LeadOps Production Scrapers & Datasets Catalog",
            "",
            f"> **Total Cataloged Scrapers:** {len(catalog)} | **With Runnable Code:** {sum(1 for c in catalog if c['has_scraper_code'])} | **With Extracted Output:** {sum(1 for c in catalog if c['has_output_data'])}",
            f"> *Last Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}*",
            "",
            "| Company / Organization | Target Portal | Scraper Code | Output Records | Status | Lead Folder |",
            "| :--- | :--- | :---: | :---: | :---: | :--- |",
        ]

        for c in catalog:
            code_link = f"[`portal_scraper.py`]({c['scraper_code_path']})" if c["has_scraper_code"] else "❌"
            output_str = f"✅ **{c['output_records_count']} rows**" if c["has_output_data"] else "—"
            portal_str = f"[{c['portal_name'] or c['portal_url'][:30]}]({c['portal_url']})" if c["portal_url"] else (c["portal_name"] or "—")
            folder_link = f"[`{c['lead_id']}`]({c['folder_path']})"
            lines.append(f"| **{c['company_name']}** | {portal_str} | {code_link} | {output_str} | `{c['qa_status']}` | {folder_link} |")

        lines.append("")
        with open(CATALOG_MD_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        if catalog:
            with open(CATALOG_CSV_PATH, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "lead_id", "company_name", "portal_name", "portal_url",
                        "has_scraper_code", "output_records_count", "qa_status",
                        "scraper_code_path", "primary_output_path", "updated_at"
                    ],
                    extrasaction="ignore"
                )
                writer.writeheader()
                writer.writerows(catalog)
    except Exception as e:
        logger.error(f"Error saving catalog files: {e}")


def get_catalog(refresh: bool = False) -> List[Dict[str, Any]]:
    if not refresh and CATALOG_JSON_PATH.exists():
        data = load_json(CATALOG_JSON_PATH)
        if isinstance(data, list) and data:
            return data
    catalog = build_catalog()
    write_catalog_files(catalog)
    return catalog


def search_catalog(query: str, catalog: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    if catalog is None:
        catalog = get_catalog()
    q = query.strip().lower()
    if not q:
        return catalog
    return [
        c for c in catalog
        if q in c["company_name"].lower()
        or q in c["lead_id"].lower()
        or q in c["portal_name"].lower()
        or q in c["portal_url"].lower()
        or q in c["commercial_pain"].lower()
    ]


def get_scraper_source_code(lead_id: str) -> Optional[str]:
    lead_dir = BUILD_ARTIFACTS_DIR / lead_id
    src_file = lead_dir / "src" / "scraper" / "portal_scraper.py"
    if src_file.exists():
        return src_file.read_text(encoding="utf-8", errors="replace")
    entry_file = lead_dir / "entry.py"
    if entry_file.exists():
        return entry_file.read_text(encoding="utf-8", errors="replace")
    return None


def get_scraper_output_data(lead_id: str) -> Optional[List[Dict[str, Any]]]:
    lead_dir = BUILD_ARTIFACTS_DIR / lead_id
    latest_json = lead_dir / "output" / "latest.json"
    if latest_json.exists():
        data = load_json(latest_json)
        if isinstance(data, list):
            return data
    sample_json = lead_dir / "ai-log-trace" / "01_initial_sample.json"
    if sample_json.exists():
        data = load_json(sample_json)
        if isinstance(data, list):
            return data
    return None


def execute_scraper_on_demand(lead_id: str) -> Dict[str, Any]:
    lead_dir = BUILD_ARTIFACTS_DIR / lead_id
    if not lead_dir.exists():
        return {"ok": False, "error": f"Lead directory not found: {lead_id}"}

    entry_file = lead_dir / "entry.py"
    output_dir = lead_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    latest_json = output_dir / "latest.json"
    latest_csv = output_dir / "latest.csv"

    if entry_file.exists():
        try:
            cmd = [sys.executable, str(entry_file)]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(lead_dir),
            )
            data = load_json(latest_json) if latest_json.exists() else None
            rows_count = len(data) if isinstance(data, list) else 0
            # Refresh this item in the catalog
            get_catalog(refresh=True)
            return {
                "ok": proc.returncode == 0,
                "lead_id": lead_id,
                "rows_extracted": rows_count,
                "stdout": proc.stdout[-1000:],
                "stderr": proc.stderr[-1000:],
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "Execution timed out (60s limit)"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # If no entry.py, return initial sample
    sample_data = get_scraper_output_data(lead_id)
    return {
        "ok": True,
        "lead_id": lead_id,
        "rows_extracted": len(sample_data or []),
        "message": "Returned verified scout extraction sample data.",
    }
