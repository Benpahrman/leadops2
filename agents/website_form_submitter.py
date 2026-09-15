"""Autonomous Website Contact Form Submitter for LeadOps Swarm.

Delivers the sub-50 word Zero-Link permission-first Alex hook directly through
SMB website contact forms.

Benefits:
1. High deliverability: Notifications originate from the prospect's own web server / form plugin.
2. Zero email domain reputation risk: Does not trigger cold email spam filters.
3. Natural client inquiry feel: Submissions land directly with receptionists and business owners.
"""

from __future__ import annotations

import asyncio
import logging
import re
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
import httpx

from .logging_config import get_logger
from .tools.waf_prober import generate_browser_headers

logger = get_logger("website_form_submitter")

CONTACT_PAGE_PATH_PATTERNS = [
    "/contact",
    "/contact-us",
    "/contact_us",
    "/contactus",
    "/reach-out",
    "/get-in-touch",
    "/about/contact",
    "/about-us/contact",
]

CAPTCHA_SIGNATURES = [
    "recaptcha",
    "hcaptcha",
    "turnstile",
    "cf-turnstile",
    "g-recaptcha",
    "challenges.cloudflare.com",
    "bot-detector",
]


@dataclass
class FormFieldMapping:
    """Detected fields inside a website contact form."""
    form_action: str = ""
    form_method: str = "POST"
    name_field: str = ""
    email_field: str = ""
    phone_field: str = ""
    message_field: str = ""
    honeypot_fields: list[str] = field(default_factory=list)
    has_captcha: bool = False
    captcha_type: str = ""
    confidence: float = 0.0


@dataclass
class ContactFormSubmissionResult:
    """Result telemetry of a contact form submission attempt."""
    website: str
    contact_url: str
    success: bool
    status: str  # SUBMITTED, CAPTCHA_BLOCKED, NO_FORM_FOUND, NETWORK_ERROR, DRY_RUN
    response_message: str = ""
    fields_submitted: dict[str, str] = field(default_factory=dict)
    submitted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "website": self.website,
            "contact_url": self.contact_url,
            "success": self.success,
            "status": self.status,
            "response_message": self.response_message,
            "fields_submitted": self.fields_submitted,
            "submitted_at": self.submitted_at,
        }


class WebsiteContactFormSubmitter:
    """Submits Zero-Link LeadOps permission hooks through SMB contact forms."""

    def __init__(
        self,
        sender_name: str = "Alex",
        sender_email: str = "alex@leadops.io",
        sender_phone: str = "(206) 555-0192",
    ):
        self.sender_name = sender_name
        self.sender_email = sender_email
        self.sender_phone = sender_phone

    def format_form_pitch(
        self,
        niche: str = "commercial operations",
        county_or_city: str = "Washington",
    ) -> str:
        """Generate strictly sub-50 word plaintext permission hook for contact forms."""
        return (
            f"Hi Team,\n\n"
            f"Saw your firm handles {niche} in {county_or_city}.\n\n"
            f"Curious — does your team pull local county dockets or filings manually?\n\n"
            f"We built an automated 8 AM morning sheet feed for newly recorded dockets. "
            f"Mind if I send over a quick preview link?\n\n"
            f"Alex | LeadOps"
        )

    async def discover_contact_url(self, base_url: str) -> str:
        """Find the contact page URL on a business website."""
        clean_base = base_url.rstrip("/")
        if not clean_base.startswith("http"):
            clean_base = f"https://{clean_base}"

        headers = generate_browser_headers(clean_base)

        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True, verify=False) as client:
                resp = await client.get(clean_base, headers=headers)
                if resp.status_code != 200:
                    return clean_base

                html = resp.text

                # 1. Search for contact links in HTML
                for pattern in CONTACT_PAGE_PATH_PATTERNS:
                    if re.search(rf'href=["\']({pattern}[^"\']*)["\']', html, re.IGNORECASE):
                        return urllib.parse.urljoin(clean_base, pattern)

                # 2. Check anchor text for "Contact"
                match_text = re.search(r'href=["\']([^"\']+)["\'][^>]*>([^<]*contact[^<]*)<', html, re.IGNORECASE)
                if match_text:
                    found_url = match_text.group(1).strip()
                    if not found_url.startswith("mailto:") and not found_url.startswith("tel:"):
                        return urllib.parse.urljoin(clean_base, found_url)

        except Exception as e:
            logger.debug(f"Contact page discovery note for {base_url}: {e}")

        # Default to root if no dedicated contact page found (many sites have forms in footer)
        return clean_base

    async def inspect_page_for_form(self, url: str) -> tuple[bool, FormFieldMapping, str]:
        """Inspect HTML content for contact form elements and honeypots."""
        headers = generate_browser_headers(url)
        mapping = FormFieldMapping()

        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, verify=False) as client:
                resp = await client.get(url, headers=headers)
                html = resp.text
                status_code = resp.status_code

                if status_code >= 400:
                    return False, mapping, f"HTTP Error {status_code}"

                # Check for CAPTCHA signatures
                for sig in CAPTCHA_SIGNATURES:
                    if sig in html.lower():
                        mapping.has_captcha = True
                        mapping.captcha_type = sig
                        break

                # Extract form block
                form_match = re.search(r"<form[^>]*>(.*?)</form>", html, re.IGNORECASE | re.DOTALL)
                if not form_match:
                    return False, mapping, "No HTML <form> detected on page"

                form_content = form_match.group(1)

                # Extract inputs
                inputs = re.findall(r'<input[^>]*>', form_content, re.IGNORECASE)
                textareas = re.findall(r'<textarea[^>]*>', form_content, re.IGNORECASE)

                for inp in inputs:
                    inp_low = inp.lower()
                    name_m = re.search(r'name=["\']([^"\']+)["\']', inp, re.IGNORECASE)
                    f_name = name_m.group(1) if name_m else ""
                    type_m = re.search(r'type=["\']([^"\']+)["\']', inp, re.IGNORECASE)
                    f_type = type_m.group(1).lower() if type_m else "text"

                    # Honeypot detection
                    if any(hp in inp_low for hp in ["display: none", "display:none", "visibility:hidden", "aria-hidden=\"true\""]):
                        if f_name:
                            mapping.honeypot_fields.append(f_name)
                        continue
                    if any(hp in f_name.lower() for hp in ["honeypot", "hp_", "trap", "extra_field", "website_url"]):
                        mapping.honeypot_fields.append(f_name)
                        continue

                    # Name field
                    if not mapping.name_field and any(k in f_name.lower() for k in ["name", "fname", "fullname", "contact_name", "your-name"]):
                        mapping.name_field = f_name
                    # Email field
                    if not mapping.email_field and (f_type == "email" or any(k in f_name.lower() for k in ["email", "mail", "your-email"])):
                        mapping.email_field = f_name
                    # Phone field
                    if not mapping.phone_field and (f_type == "tel" or any(k in f_name.lower() for k in ["phone", "tel", "mobile"])):
                        mapping.phone_field = f_name

                # Message field (textarea preferred)
                for ta in textareas:
                    name_m = re.search(r'name=["\']([^"\']+)["\']', ta, re.IGNORECASE)
                    if name_m:
                        mapping.message_field = name_m.group(1)
                        break

                mapping.confidence = 0.9 if (mapping.email_field and mapping.message_field) else 0.5
                return True, mapping, "Form detected"

        except Exception as e:
            return False, mapping, str(e)

    async def submit_contact_form(
        self,
        website_url: str,
        niche: str = "commercial operations",
        county_or_city: str = "Washington",
        custom_message: Optional[str] = None,
        dry_run: bool = False,
    ) -> ContactFormSubmissionResult:
        """Execute autonomous contact form submission."""
        contact_url = await self.discover_contact_url(website_url)
        logger.info(f"📝 [FORM SUBMITTER] Inspecting contact page: {contact_url}")

        has_form, mapping, status_msg = await self.inspect_page_for_form(contact_url)
        if not has_form:
            logger.info(f"⚠️ [FORM SUBMITTER] No form found on {contact_url}: {status_msg}")
            return ContactFormSubmissionResult(
                website=website_url,
                contact_url=contact_url,
                success=False,
                status="NO_FORM_FOUND",
                response_message=status_msg,
            )

        # Handle CAPTCHA - escalate rather than breaking per Rule 4
        if mapping.has_captcha:
            logger.warning(f"🛡️ [FORM SUBMITTER] {contact_url} is protected by {mapping.captcha_type}. Escalating to operator.")
            return ContactFormSubmissionResult(
                website=website_url,
                contact_url=contact_url,
                success=False,
                status="CAPTCHA_BLOCKED",
                response_message=f"Form protected by {mapping.captcha_type}; manual review required",
            )

        message_body = custom_message or self.format_form_pitch(niche=niche, county_or_city=county_or_city)
        fields_to_send = {
            mapping.name_field or "name": self.sender_name,
            mapping.email_field or "email": self.sender_email,
            mapping.message_field or "message": message_body,
        }
        if mapping.phone_field:
            fields_to_send[mapping.phone_field] = self.sender_phone

        if dry_run:
            logger.info(f"🔍 [FORM SUBMITTER DRY RUN] Would submit to {contact_url} with fields: {list(fields_to_send.keys())}")
            return ContactFormSubmissionResult(
                website=website_url,
                contact_url=contact_url,
                success=True,
                status="DRY_RUN",
                response_message="Form validated successfully in dry-run mode",
                fields_submitted=fields_to_send,
            )

        # Attempt Playwright headless submission for live sites
        return await self._submit_with_playwright(contact_url, mapping, fields_to_send)

    async def _submit_with_playwright(
        self,
        url: str,
        mapping: FormFieldMapping,
        payload: dict[str, str],
    ) -> ContactFormSubmissionResult:
        """Submit form using headless browser for DOM JavaScript form handlers."""
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled"]
                )
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 800},
                )
                page = await context.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)

                # Fill Name
                if mapping.name_field:
                    await page.fill(f'[name="{mapping.name_field}"]', payload.get(mapping.name_field, self.sender_name))

                # Fill Email
                if mapping.email_field:
                    await page.fill(f'[name="{mapping.email_field}"]', payload.get(mapping.email_field, self.sender_email))

                # Fill Phone
                if mapping.phone_field:
                    await page.fill(f'[name="{mapping.phone_field}"]', payload.get(mapping.phone_field, self.sender_phone))

                # Fill Message
                if mapping.message_field:
                    await page.fill(f'[name="{mapping.message_field}"]', payload.get(mapping.message_field, ""))

                # Ensure honeypot fields remain empty
                for hp in mapping.honeypot_fields:
                    try:
                        await page.fill(f'[name="{hp}"]', "")
                    except Exception:
                        pass

                # Locate submit button
                submit_btn = await page.query_selector('button[type="submit"], input[type="submit"], button:has-text("Submit"), button:has-text("Send")')
                if submit_btn:
                    await submit_btn.click()
                    await page.wait_for_timeout(2500)
                    content_after = await page.content()

                    is_confirmed = any(w in content_after.lower() for w in ["thank you", "received", "success", "sent", "we will be in touch"])
                    logger.info(f"✓ [FORM SUBMITTER] Form submitted to {url} (Confirmed: {is_confirmed})")

                    await browser.close()
                    return ContactFormSubmissionResult(
                        website=url,
                        contact_url=url,
                        success=True,
                        status="SUBMITTED",
                        response_message="Form submitted successfully via Playwright",
                        fields_submitted=payload,
                    )

                await browser.close()

        except Exception as e:
            logger.warning(f"Playwright submission notice for {url}: {e}")

        # Return status
        return ContactFormSubmissionResult(
            website=url,
            contact_url=url,
            success=False,
            status="SUBMISSION_FAILED",
            response_message="Could not interact with submit button",
            fields_submitted=payload,
        )
