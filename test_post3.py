import os
os.environ['ENV'] = 'test'
os.environ['ALLOW_DEV_ADMIN'] = 'true'

from agents.routes.portal import select_fields
import agents.routes.portal as portal_module

# Monkey patch to add debug
original_select_fields = select_fields

async def debug_select_fields(*args, **kwargs):
    print(f'DEBUG ENDPOINT: args={args}, kwargs={kwargs}')
    return await original_select_fields(*args, **kwargs)

portal_module.select_fields = debug_select_fields

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
client = TestClient(app)

headers = {'X-CSRF-Token': 'csrf-dev_admin', 'Content-Type': 'application/json'}
body = '{"fields": ["col_a", "col_b"]}'
res = client.post(f'/api/sandbox/{slug}/fields', content=body, headers=headers)
print(f'POST Status: {res.status_code}')
print(f'POST Response: {res.text}')