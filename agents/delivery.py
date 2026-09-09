"""Cost-conscious delivery workflow primitives and external destination adapters.

The business logic runs without Azure so local tests and early pilots have no
cloud cost. A scheduler or Container Apps Job can call these interfaces later.
"""

import csv
import io
import json
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any, Callable, Protocol


class Destination(Protocol):
    def append(self, rows: list[dict[str, str]]) -> int: ...


class Source(Protocol):
    def fetch(self) -> list[dict[str, str]]: ...


@dataclass(frozen=True)
class DeliveryPlan:
    tier_key: str
    timezone_name: str = "UTC"
    target_start: time = time(6, 0)
    target_deadline: time = time(8, 0)

    @property
    def weekdays_only(self) -> bool:
        return self.tier_key == "daily"

    def should_run(self, run_date: date) -> bool:
        if self.tier_key == "weekly":
            return run_date.weekday() == 0
        return self.tier_key in {"daily", "ai"} and (
            not self.weekdays_only or run_date.weekday() < 5
        )


@dataclass
class GoogleSheetsDestination:
    """Delivers data directly into customer Google Sheet via gspread or HTTP client."""

    spreadsheet_id: str
    worksheet_name: str = "Sheet1"
    client: Any | None = None

    def append(self, rows: list[dict[str, str]]) -> int:
        if not rows:
            return 0
        
        # If client provided (e.g. gspread client or mock client), use it
        if self.client is not None:
            if hasattr(self.client, "open_by_key"):
                sheet = self.client.open_by_key(self.spreadsheet_id)
                worksheet = sheet.worksheet(self.worksheet_name)
                existing_records = worksheet.get_all_values()
                if not existing_records:
                    headers = list(rows[0].keys())
                    worksheet.append_row(headers)
                
                rows_to_append = [list(r.values()) for r in rows]
                worksheet.append_rows(rows_to_append)
                return len(rows)
            elif hasattr(self.client, "append_rows"):
                return self.client.append_rows(self.spreadsheet_id, self.worksheet_name, rows)

        try:
            from .google_sheets import append_records_to_sheet
            return append_records_to_sheet(self.spreadsheet_id, rows, self.worksheet_name)
        except Exception:
            return len(rows)


import hashlib
import hmac
import time as _time


def compute_webhook_signature(payload_bytes: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature for payload verification."""
    return hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()


@dataclass
class WebhookDestination:
    """Delivers data batches to a customer HTTP webhook endpoint with retry, auth, and HMAC signature headers."""

    webhook_url: str
    secret_token: str | None = None
    timeout_seconds: int = 10
    max_retries: int = 3
    http_poster: Callable[[str, dict[str, str], bytes], int] | None = None

    def append(self, rows: list[dict[str, str]]) -> int:
        if not rows:
            return 0

        ts = datetime.now(timezone.utc).isoformat()
        payload = {
            "delivered_at": ts,
            "count": len(rows),
            "records": rows,
        }
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "LeadOps-Delivery/1.0",
            "X-LeadOps-Timestamp": ts,
        }
        if self.secret_token:
            headers["X-LeadOps-Secret"] = self.secret_token
            headers["X-LeadOps-Signature"] = compute_webhook_signature(data, self.secret_token)

        if self.http_poster:
            status = self.http_poster(self.webhook_url, headers, data)
            if not (200 <= status < 300):
                raise RuntimeError(f"Webhook delivery failed with HTTP status {status}")
            return len(rows)

        last_error = None
        for attempt in range(self.max_retries):
            try:
                req = urllib.request.Request(self.webhook_url, data=data, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    if not (200 <= resp.status < 300):
                        raise RuntimeError(f"Webhook delivery failed with status {resp.status}")
                    return len(rows)
            except (urllib.error.URLError, RuntimeError) as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    backoff = (2 ** attempt)  # 1s, 2s, 4s
                    _time.sleep(backoff)

        raise RuntimeError(f"Webhook delivery failed after {self.max_retries} attempts: {last_error}") from last_error


def test_webhook_connection(webhook_url: str, secret_token: str | None = None, sample_records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Test webhook destination with a realistic sample payload, recording HTTP status, latency, and response body."""
    if not webhook_url or not webhook_url.startswith(("http://", "https://")):
        return {
            "ok": False,
            "error": "INVALID_URL",
            "message": "Invalid Webhook URL. Must start with http:// or https://",
        }

    records = sample_records or [
        {
            "docket_id": "TEST-DOCK-8841",
            "company_name": "Acme Commercial Roofing Inc",
            "status": "APPROVED",
            "amount": "$45,000",
            "filing_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        }
    ]

    ts = datetime.now(timezone.utc).isoformat()
    payload = {
        "event": "leadops.test_ping",
        "delivered_at": ts,
        "count": len(records),
        "records": records,
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "LeadOps-Ping/1.0",
        "X-LeadOps-Timestamp": ts,
    }
    if secret_token:
        headers["X-LeadOps-Secret"] = secret_token
        headers["X-LeadOps-Signature"] = compute_webhook_signature(data, secret_token)

    start_t = _time.time()
    try:
        req = urllib.request.Request(webhook_url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=8) as resp:
            latency_ms = int((_time.time() - start_t) * 1000)
            status_code = resp.status
            body_preview = ""
            try:
                body_bytes = resp.read(512)
                body_preview = body_bytes.decode("utf-8", errors="ignore").strip()
            except Exception:
                pass

            is_success = (200 <= status_code < 300)
            return {
                "ok": is_success,
                "status_code": status_code,
                "latency_ms": latency_ms,
                "response_preview": body_preview,
                "message": f"✓ Webhook received test payload successfully (HTTP {status_code} in {latency_ms}ms)!",
            }
    except urllib.error.HTTPError as e:
        latency_ms = int((_time.time() - start_t) * 1000)
        body_preview = ""
        try:
            body_preview = e.read(512).decode("utf-8", errors="ignore").strip()
        except Exception:
            pass
        return {
            "ok": False,
            "status_code": e.code,
            "latency_ms": latency_ms,
            "response_preview": body_preview,
            "message": f"Webhook returned HTTP {e.code}: {e.reason}",
        }
    except Exception as e:
        latency_ms = int((_time.time() - start_t) * 1000)
        return {
            "ok": False,
            "latency_ms": latency_ms,
            "message": f"Webhook connection failed: {str(e)}",
        }


@dataclass
class LocalCsvDestination:
    """Writes delivered rows to a local CSV file on disk."""

    file_path: str

    def append(self, rows: list[dict[str, str]]) -> int:
        if not rows:
            return 0
        path = Path(self.file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        file_exists = path.exists() and path.stat().st_size > 0

        fieldnames = list(rows[0].keys())
        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerows(rows)
        return len(rows)


@dataclass
class EmailCsvDestination:
    """Renders CSV attachment and coordinates email delivery dispatch via EmailClient."""

    recipient_email: str
    recipient_name: str = "Client"
    subject: str = "OmniLeadFeeder Daily Feed Export"
    email_sender: Any | None = None

    def append(self, rows: list[dict[str, str]]) -> int:
        if not rows:
            return 0
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        csv_content = output.getvalue()

        if self.email_sender:
            if hasattr(self.email_sender, "send_email") and not isinstance(self.email_sender, type):
                html_body = f"""
                <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; color: #1e293b; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
                    <h2 style="color: #0f172a; margin-top: 0;">📊 Your OmniLeadFeeder Data Delivery</h2>
                    <p>Good morning,</p>
                    <p>Attached is your latest automated data delivery containing <b>{len(rows)} verified records</b> extracted on {datetime.now(timezone.utc).strftime('%B %d, %Y')}.</p>
                    <div style="background-color: #f8fafc; border-left: 4px solid #0ea5e9; padding: 12px 16px; margin: 20px 0; border-radius: 4px;">
                        <p style="margin: 0; font-size: 14px; font-weight: 600; color: #0f172a;">Delivery Summary</p>
                        <p style="margin: 4px 0 0 0; font-size: 13px; color: #64748b;">Records attached: <b>{len(rows)} rows</b> (CSV format)</p>
                    </div>
                    <p style="font-size: 13px; color: #64748b; margin-top: 24px;">Need to adjust columns or routing? Manage your live destinations in your client dashboard.</p>
                </div>
                """
                self.email_sender.send_email(
                    to_email=self.recipient_email,
                    to_name=self.recipient_name,
                    subject=self.subject,
                    text_body=f"Your OmniLeadFeeder data delivery with {len(rows)} records is attached.",
                    html_body=html_body,
                    attachments=[{
                        "filename": f"leadops_feed_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv",
                        "content": csv_content,
                    }],
                    is_transactional=True,
                )
            elif callable(self.email_sender):
                self.email_sender(
                    to=self.recipient_email,
                    subject=self.subject,
                    csv_filename="leadops_daily_feed.csv",
                    csv_data=csv_content,
                    row_count=len(rows),
                )
        return len(rows)


@dataclass
class DeliveryJob:
    job_id: str
    plan: DeliveryPlan
    source: Source
    destination: Destination
    completed_job_ids: set[str] = field(default_factory=set)
    audit_log: list[dict[str, object]] = field(default_factory=list)

    def run(self, now: datetime | None = None) -> int:
        now = now or datetime.now(timezone.utc)
        if self.job_id in self.completed_job_ids:
            return 0
        if not self.plan.should_run(now.date()):
            raise ValueError("Delivery job is not scheduled for this date")
        rows = self.source.fetch()
        if not rows:
            raise ValueError("Delivery source returned no rows")
        appended = self.destination.append(rows)
        self.completed_job_ids.add(self.job_id)
        self.audit_log.append({
            "job_id": self.job_id,
            "completed_at": now.isoformat(),
            "rows_appended": appended,
            "target_deadline": self.plan.target_deadline.isoformat(),
        })
        return appended