import os
import sys
from pathlib import Path
import dotenv

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
dotenv.load_dotenv()

from agents.email.client import EmailClient

def main():
    client = EmailClient()

    recipient = "benpahrman@gmail.com"
    subject = "Automated Record Feed for Pahrman Asset Intelligence [Interactive Sandbox Ready]"
    
    html = """
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #1e293b; line-height: 1.6;">
      <h2 style="color: #0f172a; margin-bottom: 12px;">Hi Ben,</h2>
      <p>We analyzed your public filings workflow from the <strong>Harris County Court Clerk Probate Search</strong>.</p>
      <p>Our autonomous scraper engine has built a live sample feed for <strong>Pahrman Asset Intelligence</strong>.</p>
      
      <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin: 20px 0;">
        <h4 style="margin: 0 0 8px 0; color: #0f172a;">Sample Extracted Filings (Harris County):</h4>
        <ul style="margin: 0; padding-left: 20px; font-size: 14px;">
          <li>Cause #546346: <em>ESTATE OF VLADYSLAV KHAIERLANAMOV</em> ($650,000.00)</li>
          <li>Cause #546344: <em>ESTATE OF BRUCE SIMON</em> ($1,200,000.00)</li>
          <li>Cause #546294: <em>ESTATE OF RUBY RODECK EHRLUND</em> ($480,000.00)</li>
        </ul>
      </div>

      <p style="margin-bottom: 24px;">
        <a href="http://127.0.0.1:8000/p/pahrman-asset-intelligence-lead-pahrman-intel-1787854118" 
           style="background: #c26b34; color: #ffffff; padding: 12px 24px; text-decoration: none; font-weight: bold; border-radius: 6px; display: inline-block;">
          View Live Data Preview & Sandbox &rarr;
        </a>
      </p>

      <p style="font-size: 14px; color: #64748b;">
        Once approved, you can lock in your 50% milestone deposit ($250.00) to deploy your custom daily automated sync.
      </p>

      <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;" />
      <p style="font-size: 13px; color: #94a3b8; margin: 0;">
        Best,<br />
        <strong>Alex</strong> | LeadOps Automation Engineering
      </p>
    </div>
    """

    text = """Hi Ben,

We analyzed your public filings workflow from Harris County Court Clerk Probate Search.
Our autonomous crawler has built a live sample feed for Pahrman Asset Intelligence.

Review your interactive data sandbox here:
http://127.0.0.1:8000/p/pahrman-asset-intelligence-lead-pahrman-intel-1787854118

Once you approve the schema, lock in your 50% milestone deposit ($250) to deploy your production feed.

Best,
Alex | LeadOps Automation Engineering"""

    print(f"Sending live email to {recipient} via native Gmail SMTP (Sender: {client.settings.from_email})...")

    res = client.send_email(
        to_email=recipient,
        to_name="Ben Pahrman",
        subject=subject,
        text_body=text,
        html_body=html,
    )
    print("Dispatch Result:", res)

if __name__ == "__main__":
    main()
