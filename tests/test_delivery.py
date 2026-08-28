import json
import unittest
from datetime import date, datetime, timezone

from agents.delivery import (
    DeliveryJob,
    DeliveryPlan,
    EmailCsvDestination,
    GoogleSheetsDestination,
    LocalCsvDestination,
    WebhookDestination,
)


class FakeSource:
    def fetch(self):
        return [{"case_number": "A-1"}, {"case_number": "A-2"}]


class FakeDestination:
    def __init__(self):
        self.rows = []

    def append(self, rows):
        self.rows.extend(rows)
        return len(rows)


class DeliveryTests(unittest.TestCase):
    def test_weekly_delivery_runs_on_monday_and_is_idempotent(self):
        destination = FakeDestination()
        job = DeliveryJob(
            "delivery-1",
            DeliveryPlan("weekly"),
            FakeSource(),
            destination,
        )
        monday = datetime(2026, 8, 24, 6, 0, tzinfo=timezone.utc)

        self.assertEqual(job.run(monday), 2)
        self.assertEqual(job.run(monday), 0)
        self.assertEqual(len(destination.rows), 2)

    def test_daily_delivery_skips_weekends(self):
        plan = DeliveryPlan("daily")
        self.assertTrue(plan.should_run(date(2026, 8, 24)))
        self.assertFalse(plan.should_run(date(2026, 8, 29)))

    def test_webhook_destination_invokes_http_poster(self):
        calls = []

        def mock_poster(url: str, headers: dict[str, str], body: bytes) -> int:
            calls.append({"url": url, "headers": headers, "body": json.loads(body.decode())})
            return 200

        dest = WebhookDestination(
            webhook_url="https://api.client.com/webhook",
            secret_token="secret-123",
            http_poster=mock_poster,
        )
        count = dest.append([{"id": "1", "name": "Item 1"}, {"id": "2", "name": "Item 2"}])
        self.assertEqual(count, 2)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["url"], "https://api.client.com/webhook")
        self.assertEqual(calls[0]["headers"]["X-LeadOps-Secret"], "secret-123")
        self.assertEqual(calls[0]["body"]["count"], 2)

    def test_local_csv_destination_writes_file(self):
        import tempfile
        import os
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "output.csv")
            dest = LocalCsvDestination(file_path=file_path)
            rows = [{"case": "100", "status": "filed"}, {"case": "101", "status": "closed"}]
            count = dest.append(rows)
            self.assertEqual(count, 2)
            self.assertTrue(os.path.exists(file_path))
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertIn("case,status", content)
                self.assertIn("100,filed", content)

    def test_email_csv_destination_renders_csv(self):
        dispatched = []

        def mock_sender(to, subject, csv_filename, csv_data, row_count):
            dispatched.append({"to": to, "subject": subject, "csv_data": csv_data, "row_count": row_count})

        dest = EmailCsvDestination(
            recipient_email="ops@acme.com",
            subject="Daily Leads",
            email_sender=mock_sender,
        )
        count = dest.append([{"col1": "val1", "col2": "val2"}])
        self.assertEqual(count, 1)
        self.assertEqual(len(dispatched), 1)
        self.assertEqual(dispatched[0]["to"], "ops@acme.com")
        self.assertIn("col1,col2", dispatched[0]["csv_data"])

    def test_google_sheets_destination_mock(self):
        class MockGSpreadWorksheet:
            def __init__(self):
                self.appended = []
            def get_all_values(self):
                return []
            def append_row(self, row):
                self.appended.append(row)
            def append_rows(self, rows):
                self.appended.extend(rows)

        class MockGSpreadSheet:
            def __init__(self, ws):
                self.ws = ws
            def worksheet(self, name):
                return self.ws

        class MockGSpreadClient:
            def __init__(self, ws):
                self.ws = ws
            def open_by_key(self, key):
                return MockGSpreadSheet(self.ws)

        ws = MockGSpreadWorksheet()
        client = MockGSpreadClient(ws)
        dest = GoogleSheetsDestination(spreadsheet_id="sheet-key-123", client=client)
        count = dest.append([{"lead": "L1", "status": "active"}, {"lead": "L2", "status": "new"}])
        self.assertEqual(count, 2)
        self.assertEqual(len(ws.appended), 3)  # header + 2 rows


if __name__ == "__main__":
    unittest.main()