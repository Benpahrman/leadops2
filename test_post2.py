import os
os.environ['ENV'] = 'test'
os.environ['ALLOW_DEV_ADMIN'] = 'true'

from fastapi.testclient import TestClient
from agents.api import create_app
from agents.domain import Lead
from agents.portal import PortalService
from agents.storage import InMemoryStorageBackend

storage = InMemoryStorageBackend()
portal = PortalService(storage=storage)
lead = Lead('test-lead-1', 'weekly')
slug = portal.publish_sandbox(
    lead=lead,
    company_name='Test Company',
    rows=[{'col_a': 'val1', 'col_b': 'val2'}],
    source_url='https://portal.example.gov',
)

app = create_app(storage=storage, portal_svc=portal, api_token='valid-secret-token')

# Add debug middleware
@app.middleware('http')
async def debug_middleware(request, call_next):
    print(f'DEBUG MIDDLEWARE: {request.method} {request.url.path}')
    print(f'  Headers: {dict(request.headers)}')
    body = await request.body()
    print(f'  Body: {body}')
    # Need to recreate request with body
    async def receive():
        return {'type': 'http.request', 'body': body}
    request._receive = receive
    response = await call_next(request)
    return response

client = TestClient(app)
headers = {'X-CSRF-Token': 'csrf-dev_admin', 'Content-Type': 'application/json'}
body = '{"fields": ["col_a", "col_b"]}'
res = client.post(f'/api/sandbox/{slug}/fields', content=body, headers=headers)
print(f'POST Status: {res.status_code}')
print(f'POST Response: {res.text}')