import json
import shutil
import tempfile
import unittest
from pathlib import Path

from agents.audit_vault import AuditVault, TERMS_VERSION
from agents.domain import Lead, State


class AuditVaultTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.vault = AuditVault(base_dir=self.temp_dir)
        self.lead_id = "test-lead-acme-corp"
        self.company = "Acme Corp Commercial Intelligence"
        self.email = "procurement@acmecorp.com"

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_record_terms_acceptance_creates_cryptographic_hash_and_saves_payload(self):
        """Test recording clickwrap SOW and Terms of Service with client IP and User-Agent."""
        agreement = self.vault.record_terms_acceptance(
            lead_id=self.lead_id,
            company_name=self.company,
            contact_email=self.email,
            ip_address="198.51.100.42",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0",
            target_url="https://portal.publicrecords.org/cases",
            selected_fields=["case_number", "filing_date", "plaintiff", "status"],
            tier_key="daily",
            deposit_amount_usd=250.00,
        )

        self.assertEqual(agreement["lead_id"], self.lead_id)
        self.assertEqual(agreement["ip_address"], "198.51.100.42")
        self.assertEqual(agreement["terms_version"], TERMS_VERSION)
        self.assertTrue(agreement["clickwrap_accepted"])
        self.assertIn("contract_sha256", agreement)
        self.assertEqual(len(agreement["contract_sha256"]), 64)

        # Verify disk persistence
        retrieved = self.vault.get_terms_acceptance(self.lead_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["contract_sha256"], agreement["contract_sha256"])

    def test_record_communication_logs_inbound_and_outbound(self):
        """Test recording communication events in chronological audit log."""
        out_msg = self.vault.record_communication(
            lead_id=self.lead_id,
            direction="OUTBOUND",
            channel="EMAIL",
            sender="Alex @ LeadOps <alex@leadops.co>",
            recipient=self.email,
            subject="Deposit Confirmed: Dev Swarm Initialized",
            body_summary="Your $250.00 setup deposit is secured in escrow.",
            status="DELIVERED",
        )
        self.assertEqual(out_msg["entry_id"], "COMM-0001")
        self.assertEqual(out_msg["direction"], "OUTBOUND")

        in_msg = self.vault.record_communication(
            lead_id=self.lead_id,
            direction="INBOUND",
            channel="EMAIL",
            sender=self.email,
            recipient="Alex @ LeadOps <alex@leadops.co>",
            subject="Re: Deposit Confirmed",
            body_summary="Looks great, please proceed with daily 8am delivery.",
            status="RECEIVED",
        )
        self.assertEqual(in_msg["entry_id"], "COMM-0002")

        history = self.vault.get_communications_log(self.lead_id)
        self.assertEqual(len(history), 2)

    def test_record_payment_event(self):
        """Test recording PayPal financial transaction details."""
        pay = self.vault.record_payment_event(
            lead_id=self.lead_id,
            provider="PAYPAL",
            transaction_id="TXN-987654321",
            order_id="ORDER-123456",
            amount_usd=250.00,
            currency="USD",
            status="COMPLETED",
            payer_email=self.email,
            payer_name=self.company,
            payment_type="50% Milestone Setup Deposit",
        )
        self.assertEqual(pay["payment_id"], "PAY-0001")
        self.assertEqual(pay["amount_usd"], 250.00)
        self.assertTrue(pay["escrow_locked"])

        records = self.vault.get_payment_records(self.lead_id)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["transaction_id"], "TXN-987654321")

    def test_record_delivery_receipt_with_sha256_hash(self):
        """Test recording proof-of-delivery receipts with SHA-256 payload integrity."""
        receipt = self.vault.record_delivery_receipt(
            lead_id=self.lead_id,
            run_id="RUN-20260907-0800",
            rows_delivered=150,
            destination_type="GOOGLE_SHEETS",
            destination_target="https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
            data_sha256="abc123def4567890123456789012345678901234567890123456789012345678",
            qa_score=100.0,
            sample_keys=["case_number", "status"],
            notes="Morning batch delivered on schedule at 8:00 AM",
        )
        self.assertEqual(receipt["receipt_id"], "DELIV-0001")
        self.assertEqual(receipt["rows_delivered"], 150)
        self.assertEqual(receipt["status"], "CONFIRMED_DELIVERED")

        ledger = self.vault.get_deliveries_ledger(self.lead_id)
        self.assertEqual(len(ledger), 1)

    def test_generate_chargeback_defense_dossier_compiles_evidence_package(self):
        """Test that generate_chargeback_defense_dossier produces Markdown and HTML dispute packages."""
        # 1. Terms
        self.vault.record_terms_acceptance(
            lead_id=self.lead_id,
            company_name=self.company,
            contact_email=self.email,
            ip_address="198.51.100.42",
            user_agent="Chrome 124 on Windows",
            target_url="https://portal.publicrecords.org/cases",
            selected_fields=["case_number", "status"],
        )
        # 2. Communication
        self.vault.record_communication(
            lead_id=self.lead_id,
            direction="OUTBOUND",
            channel="EMAIL",
            sender="alex@leadops.co",
            recipient=self.email,
            subject="Deposit Confirmation",
            body_summary="Milestone deposit confirmed.",
        )
        # 3. Payment
        self.vault.record_payment_event(
            lead_id=self.lead_id,
            provider="PAYPAL",
            transaction_id="TXN-PAYPAL-999",
            order_id="ORD-999",
            amount_usd=250.00,
            status="COMPLETED",
        )
        # 4. Swarm work
        self.vault.record_swarm_work_event(
            lead_id=self.lead_id,
            agent_role="OUTSIDE_QA",
            action="Ground-Truth Live Parity Verification",
            status="PASSED",
            details="Verified 100% data match against live target site.",
        )
        # 5. Delivery
        self.vault.record_delivery_receipt(
            lead_id=self.lead_id,
            run_id="RUN-INITIAL",
            rows_delivered=25,
            destination_type="ESCROW_PREVIEW",
            destination_target=f"/dashboard/{self.lead_id}",
            qa_score=100.0,
        )

        dossier = self.vault.generate_chargeback_defense_dossier(self.lead_id)

        self.assertIn("markdown_path", dossier)
        self.assertIn("html_path", dossier)
        self.assertTrue(Path(dossier["markdown_path"]).exists())
        self.assertTrue(Path(dossier["html_path"]).exists())

        md_content = Path(dossier["markdown_path"]).read_text(encoding="utf-8")
        self.assertIn("OFFICIAL DISPUTE DEFENSE DOSSIER", md_content)
        self.assertIn(self.company, md_content)
        self.assertIn("198.51.100.42", md_content)
        self.assertIn("TXN-PAYPAL-999", md_content)
        self.assertIn("OUTSIDE_QA", md_content)
        self.assertIn("FORMAL STATEMENT OF AUTHENTICITY", md_content)

        html_content = Path(dossier["html_path"]).read_text(encoding="utf-8")
        self.assertIn("<title>Chargeback Dispute Defense Dossier", html_content)
        self.assertIn("Print / Save as PDF for Dispute", html_content)


if __name__ == "__main__":
    unittest.main()
