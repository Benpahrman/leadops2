# LeadOps E2E Tests

Playwright-based end-to-end tests for the LeadOps application.

## Test Structure

```
tests_e2e/
├── conftest.py          # Playwright fixtures and configuration
├── pytest.ini           # Pytest configuration
├── run_e2e.py           # Test runner script
├── test_smoke.py        # Smoke tests (infrastructure verification)
├── test_auth.py         # Authentication flow tests
├── test_payments.py     # Payment flow tests
└── test_dev_swarm.py    # Dev swarm build tests
```

## Prerequisites

1. **Running services:**
   - API server on `http://127.0.0.1:8000` (or set `E2E_BASE_URL`)
   - Frontend (Vite) on `http://127.0.0.1:5173` (or set `E2E_FRONTEND_URL`)

2. **Environment variables:**
   ```bash
   # Required for auth tests
   export E2E_CLERK_EMAIL="test@example.com"
   export E2E_CLERK_PASSWORD="testpassword123"
   
   # Optional for admin tests
   export E2E_ADMIN_EMAIL="admin@example.com"
   export E2E_ADMIN_PASSWORD="adminpassword123"
   ```

3. **Playwright browsers:**
   ```bash
   playwright install chromium
   ```

## Running Tests

### All E2E tests
```bash
cd tests_e2e
python run_e2e.py
```

### Specific test file
```bash
python run_e2e.py --test test_auth.py
```

### Headed mode (visible browser)
```bash
python run_e2e.py --headed
```

### Debug mode (slow motion)
```bash
python run_e2e.py --debug
```

### Custom URLs
```bash
python run_e2e.py --base-url http://localhost:8000 --frontend-url http://localhost:5173
```

## Test Categories

| File | Marker | Description |
|------|--------|-------------|
| `test_smoke.py` | `e2e` | Infrastructure verification |
| `test_auth.py` | `e2e, auth` | Sign-in, sign-up, sign-out, protected routes |
| `test_payments.py` | `e2e, payments` | Deposit, final payment, webhooks |
| `test_dev_swarm.py` | `e2e, dev_swarm` | Build progress, artifacts, QA |

## Running by Marker

```bash
# Run only auth tests
pytest -m auth

# Run only payment tests
pytest -m payments

# Run only dev swarm tests
pytest -m dev_swarm
```

## CI/CD Integration

For GitHub Actions:

```yaml
- name: Install Playwright
  run: |
    pip install playwright pytest-playwright
    playwright install chromium

- name: Start services
  run: |
    # Start API server
    uvicorn agents.api:create_app --host 0.0.0.0 --port 8000 &
    # Start frontend
    cd my-clerk-vite-app && npm run dev &

- name: Run E2E tests
  run: |
    cd tests_e2e
    python run_e2e.py
  env:
    E2E_CLERK_EMAIL: ${{ secrets.E2E_CLERK_EMAIL }}
    E2E_CLERK_PASSWORD: ${{ secrets.E2E_CLERK_PASSWORD }}
```

## Writing New Tests

1. Create a new `test_*.py` file
2. Use the fixtures from `conftest.py`:
   - `page` - Unauthenticated page
   - `authenticated_page` - Pre-authenticated page
   - `base_url` - API base URL
   - `frontend_url` - Frontend URL
3. Mark with `@pytest.mark.e2e` and appropriate category marker

## Best Practices

1. **Use data-testid attributes** for reliable selectors
2. **Wait for network idle** after navigation
3. **Use explicit waits** instead of sleep
4. **Clean up state** between tests (handled by fixture)
5. **Skip gracefully** when features aren't available