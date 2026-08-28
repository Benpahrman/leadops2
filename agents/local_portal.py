"""Dependency-free local portal demo for LeadOps development."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from .domain import Lead
from .portal import PortalService
from .progress import ProgressStatus
from .scout_pipeline import ScoutPortalPipeline


def create_demo_portal() -> tuple[PortalService, str]:
    portal = PortalService()
    lead = Lead("demo-lead", "daily")
    slug = portal.publish_sandbox(
        lead,
        "Acme Research",
        [
            {"case_number": "A-100", "filing_date": "2026-08-26", "county": "Cook"},
            {"case_number": "A-101", "filing_date": "2026-08-27", "county": "Cook"},
        ],
        "https://example.gov/cases",
    )
    portal.publish_build_progress(slug, "planner", ProgressStatus.COMPLETE, "Research assumptions are ready to confirm")
    return portal, slug


def _intake_payload(portal: PortalService, slug: str) -> dict[str, Any]:
    sandbox = portal.get_sandbox(slug)
    return {
        "slug": slug,
        "state": sandbox.lead.state.value,
        "tier": sandbox.lead.tier.name,
        "source_url": sandbox.source_url,
        "sample": sandbox.rows,
        "selected_fields": sandbox.lead.selected_fields,
        "progress": portal.build_progress(slug),
    }


class PortalHandler(BaseHTTPRequestHandler):
    portal, demo_slug = create_demo_portal()
    scout_pipeline = ScoutPortalPipeline(portal)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        target_slug = None
        if path == "/":
            target_slug = self.demo_slug
        elif path.startswith("/p/"):
            target_slug = path[3:].rstrip("/")

        if target_slug:
            try:
                sandbox = self.portal.get_sandbox(target_slug)
                company_title = target_slug.rsplit("-", 1)[0].replace("-", " ").title()
                html = _HTML.replace("__SLUG__", target_slug).replace("Acme Research", company_title)
                html = html.replace("</main>", _CHECKOUT_PANEL + "</main>")
                html = html.replace("</body>", _CHECKOUT_SCRIPT + "</body>")
                self._send_html(html)
                return
            except KeyError:
                self._send_json({"error": f"Sandbox not found: {target_slug}"}, 404)
                return

        prefix = "/api/sandbox/"
        if path.startswith(prefix):
            slug = path[len(prefix):].rstrip("/")
            try:
                self._send_json(_intake_payload(self.portal, slug))
            except KeyError:
                self._send_json({"error": "sandbox not found"}, 404)
            return
        self._send_json({"error": "not found"}, 404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/scout/candidate":
            try:
                body = self._read_json()
                candidate = self.scout_pipeline.publish_candidate(
                    body["company_name"],
                    body["lead_id"],
                    body["evidence"],
                    body["source_url"],
                    body["sample_rows"],
                    body["research"],
                    body.get("tier_key", "weekly"),
                )
                self._send_json({
                    "lead_id": candidate.lead_id,
                    "slug": candidate.slug,
                    "source_url": candidate.source_url,
                    "intake": {
                        "slug": candidate.intake.slug,
                        "assumptions": [assumption.__dict__ for assumption in candidate.intake.assumptions],
                    },
                })
            except (KeyError, TypeError, ValueError) as error:
                self._send_json({"error": str(error)}, 400)
            return
        prefix = "/api/sandbox/"
        if not path.startswith(prefix):
            self._send_json({"error": "not found"}, 404)
            return
        parts = path[len(prefix):].strip("/").split("/")
        if len(parts) != 2:
            self._send_json({"error": "not found"}, 404)
            return
        slug, action = parts
        try:
            body = self._read_json()
            if action == "events":
                self.portal.record_interaction(slug, body["event"])
            elif action == "fields":
                self.portal.select_fields(slug, body["fields"])
            elif action == "scope":
                self.portal.approve_scope(slug)
            elif action == "checkout":
                self._send_json(self.portal.request_checkout(slug))
                return
            else:
                self._send_json({"error": "unsupported action"}, 400)
                return
            self._send_json(_intake_payload(self.portal, slug))
        except (KeyError, TypeError, ValueError) as error:
            self._send_json({"error": str(error)}, 400)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length))

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_html(self, html: str) -> None:
        encoded = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: object) -> None:
        return


def run(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = ThreadingHTTPServer((host, port), PortalHandler)
    print(f"LeadOps portal: http://{host}:{port}/")
    server.serve_forever()


_CHECKOUT_PANEL = """<section><h2>Deploy</h2><div class="panel"><p id="checkout-status" class="muted">Approve the assumptions before preparing checkout.</p><button class="button" onclick="prepareCheckout()">Deploy Feed</button></div></section>"""

_CHECKOUT_SCRIPT = """<script>async function prepareCheckout(){const status=document.getElementById('checkout-status');try{await fetch('/api/sandbox/'+slug+'/scope',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});const response=await fetch('/api/sandbox/'+slug+'/checkout',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});const result=await response.json();if(!response.ok)throw new Error(result.error);status.textContent='PayPal '+result.payment_kind+' ready: $'+(result.amount_cents/100).toFixed(2)+' (sandbox order creation boundary)';}catch(error){status.textContent=error.message}}</script>"""

_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>LeadOps Sandbox</title><style>
:root{font-family:Georgia,serif;color:#15251f;background:#edf2ec}body{margin:0}main{max-width:900px;margin:0 auto;padding:40px 20px}header{display:flex;justify-content:space-between;align-items:end;border-bottom:2px solid #15251f;padding-bottom:18px}h1{font-size:42px;margin:0}h2{font-size:22px;margin-top:34px}.eyebrow{font:12px monospace;letter-spacing:2px;text-transform:uppercase;color:#64776d}.panel{background:#fff;border:1px solid #c5d0c8;padding:22px;margin-top:18px;box-shadow:6px 6px 0 #d7e0d8}.assumption{display:grid;grid-template-columns:180px 1fr auto;gap:12px;border-bottom:1px solid #e2e8e3;padding:12px 0}.assumption:last-child{border:0}.label{font-weight:bold}.confidence{font:12px monospace;color:#8a4a20}.sample{width:100%;border-collapse:collapse;background:#fff}.sample th,.sample td{text-align:left;padding:12px;border-bottom:1px solid #dce5de}.sample th{background:#24483b;color:#fff}.progress{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}.step{padding:14px 8px;background:#e4ebe5;border-top:4px solid #a6b8aa;font:12px monospace}.step.COMPLETE{border-color:#c26b34;background:#fff3e9}.step.ACTIVE{border-color:#24483b}.button{background:#c26b34;color:#fff;border:0;padding:13px 18px;font-weight:bold;cursor:pointer}.muted{color:#64776d}@media(max-width:650px){h1{font-size:32px}.assumption{grid-template-columns:1fr}.progress{grid-template-columns:1fr 1fr}}
</style></head><body><main><header><div><div class="eyebrow">LeadOps / tailored sandbox</div><h1>Acme Research</h1></div><div class="eyebrow">__SLUG__</div></header><section><h2>We did the research first.</h2><p class="muted">Review these assumptions, correct anything inline, and continue when they look right.</p><div id="intake" class="panel">Loading sandbox...</div></section><section><h2>Sample data</h2><div class="panel"><table class="sample" id="sample"></table><p><button class="button" onclick="exportSample()">Export free CSV</button></p></div></section><section><h2>Build progress</h2><div class="panel"><div class="progress" id="progress"></div></div></section></main><script>
const slug='__SLUG__';let data;
async function load(){data=await (await fetch('/api/sandbox/'+slug)).json();document.getElementById('intake').innerHTML='<div>'+[['Business type','Probate research'],['Jurisdiction','Cook County, IL'],['Likely portal','Cook County Probate'],['Recommended plan',data.tier],['Delivery','5x weekly']].map(x=>'<div class="assumption"><span class="label">'+x[0]+'</span><span>'+x[1]+'</span><span class="confidence">CONFIRM</span></div>').join('')+'<p><button class="button" onclick="confirmFields()">Looks right, continue</button></p>';let cols=Object.keys(data.sample[0]);document.getElementById('sample').innerHTML='<tr>'+cols.map(x=>'<th>'+x+'</th>').join('')+'</tr>'+data.sample.map(r=>'<tr>'+cols.map(x=>'<td>'+r[x]+'</td>').join('')+'</tr>').join('');document.getElementById('progress').innerHTML=data.progress.map(x=>'<div class="step '+x.status+'"><b>'+x.role+'</b><br>'+x.status+'<br><span class="muted">'+x.message+'</span></div>').join('')}
async function confirmFields(){await fetch('/api/sandbox/'+slug+'/fields',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({fields:['case_number','filing_date','county']})});load()}function exportSample(){let csv=Object.keys(data.sample[0]).join(',')+'\\n'+data.sample.map(r=>Object.values(r).join(',')).join('\\n');let a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));a.download=slug+'.csv';a.click()}load();</script></body></html>"""

run()