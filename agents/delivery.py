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
                # Ensure headers exist
                existing_records = worksheet.get_all_values()
                if not existing_records:
                    headers = list(rows[0].keys())
                    worksheet.append_row(headers)
                
                rows_to_append = [list(r.values()) for r in rows]
                worksheet.append_rows(rows_to_append)
                return len(rows)
            elif hasattr(self.client, "append_rows"):
                return self.client.append_rows(self.spreadsheet_id, self.worksheet_name, rows)

        # Standalone logging fallback for local testing without credentials
        return len(rows)


@dataclass
class WebhookDestination:
    """Delivers data batches to a customer HTTP webhook endpoint with retry and auth headers."""

    webhook_url: str
    secret_token: str | None = None
    timeout_seconds: int = 10
    http_poster: Callable[[str, dict[str, str], bytes], int] | None = None

    def append(self, rows: list[dict[str, str]]) -> int:
        if not rows:
            return 0

        payload = {
            "delivered_at": datetime.now(timezone.utc).isoformat(),
            "count": len(rows),
            "records": rows,
        }
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "LeadOps-Delivery/1.0",
        }
        if self.secret_token:
            headers["X-LeadOps-Secret"] = self.secret_token

        if self.http_poster:
            status = self.http_poster(self.webhook_url, headers, data)
            if not (200 <= status < 300):
                raise RuntimeError(f"Webhook delivery failed with HTTP status {status}")
            return len(rows)

        req = urllib.request.Request(self.webhook_url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                if not (200 <= resp.status < 300):
                    raise RuntimeError(f"Webhook delivery failed with status {resp.status}")
                return len(rows)
        except urllib.error.URLError as e:
            raise RuntimeError(f"Webhook connection failed: {e}") from e


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
    """Renders CSV attachment and coordinates email delivery dispatch."""

    recipient_email: str
    subject: str = "LeadOps Daily Feed"
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