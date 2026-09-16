"""Run live 4-vector Deliverability Suite audit and output formatted scorecard."""

import json
from dataclasses import asdict
from agents.email.deliverability_suite import get_deliverability_suite


def main():
    suite = get_deliverability_suite("olfmailer.com")
    report = suite.run_full_audit()

    print("\n" + "=" * 60)
    print("🛡️  ENTERPRISE DELIVERABILITY & INBOX PLACEMENT SCORECARD")
    print("=" * 60)
    print(f"Domain:              {report.domain}")
    print(f"Composite Health:    {report.composite_score}% [{report.tier}]")
    print(f"Audited At:          {report.audited_at}")
    print("-" * 60)
    print("VECTOR 1: DNS & AUTHENTICATION MATRIX")
    print(f"  • SPF Record:      {report.dns_vector.spf_status} ({report.dns_vector.spf_lookup_count}/10 lookups)")
    print(f"  • DKIM Status:     {report.dns_vector.dkim_status} ({report.dns_vector.dkim_details})")
    print(f"  • DMARC Policy:    {report.dns_vector.dmarc_status} (Policy: {report.dns_vector.dmarc_policy})")
    print(f"  • MX Exchanger:    {report.dns_vector.mx_status} ({', '.join(report.dns_vector.mx_records[:2])})")
    print("-" * 60)
    print("VECTOR 2: GLOBAL RBL / DNSBL REPUTATION (12 PROVIDERS)")
    print(f"  • Listed Count:    {report.rbl_vector.listed_count} / {report.rbl_vector.total_scanned}")
    print(f"  • Status:          {report.rbl_vector.status} ({report.rbl_vector.details})")
    print("-" * 60)
    print("VECTOR 3: AI COPY & ZERO-LINK SPAM INSPECTOR")
    print(f"  • Zero-Link Pass:  {report.content_vector.zero_link_passed} ({report.content_vector.link_count} links)")
    print(f"  • Word Count:      {report.content_vector.word_count} words (35-55 optimal)")
    print(f"  • Spam Penalty:    {report.content_vector.spam_score} pts")
    print(f"  • Reading Grade:   {report.content_vector.reading_grade}")
    print("-" * 60)
    print("VECTOR 4: PROVIDER PLACEMENT & EGRESS")
    print(f"  • Google:          {report.placement_vector.google_status}")
    print(f"  • Microsoft 365:   {report.placement_vector.microsoft_status}")
    print(f"  • Azure ACS Egress:{report.placement_vector.acs_port443_status}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
