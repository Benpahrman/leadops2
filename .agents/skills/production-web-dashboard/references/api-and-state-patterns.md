# Real Data API Integration & Reactive State Patterns

This guide provides tested patterns for connecting modular dashboard components to live backend endpoints, FastAPI services, and authentication layers.

---

## 1. Production API Client Implementation

```javascript
/**
 * Modular API client with automated Clerk JWT injection, timeout handling, and exponential backoff retry.
 */
class ProductionApiClient {
  constructor(options = {}) {
    this.baseUrl = options.baseUrl || '';
    this.defaultTimeoutMs = options.timeoutMs || 10000;
  }

  async getHeaders(customHeaders = {}) {
    const headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...customHeaders
    };

    // Inject Clerk token if Clerk is initialized and user is signed in
    if (window.Clerk && window.Clerk.session) {
      try {
        const token = await window.Clerk.session.getToken();
        if (token) {
          headers['Authorization'] = `Bearer ${token}`;
        }
      } catch (err) {
        console.warn('Failed to retrieve Clerk session token', err);
      }
    }

    return headers;
  }

  async request(endpoint, { method = 'GET', body = null, headers = {}, timeout = this.defaultTimeoutMs } = {}, retries = 2) {
    const url = `${this.baseUrl}${endpoint}`;
    const reqHeaders = await this.getHeaders(headers);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    const fetchConfig = {
      method,
      headers: reqHeaders,
      signal: controller.signal
    };

    if (body) {
      fetchConfig.body = typeof body === 'string' ? body : JSON.stringify(body);
    }

    try {
      const response = await fetch(url, fetchConfig);
      clearTimeout(timeoutId);

      if (!response.ok) {
        let errorDetail = `HTTP ${response.status} ${response.statusText}`;
        try {
          const errJson = await response.json();
          errorDetail = errJson.detail || errJson.message || errorDetail;
        } catch (_) {}
        const error = new Error(errorDetail);
        error.status = response.status;
        throw error;
      }

      // If empty response or 204
      if (response.status === 204) return null;
      return await response.json();
    } catch (err) {
      clearTimeout(timeoutId);

      // Auto-retry on network failure or 5xx server errors for GET requests
      const isRetryable = method === 'GET' && (!err.status || err.status >= 500);
      if (retries > 0 && isRetryable) {
        const delay = (3 - retries) * 750;
        await new Promise(r => setTimeout(r, delay));
        return this.request(endpoint, { method, body, headers, timeout }, retries - 1);
      }

      throw err;
    }
  }

  get(endpoint, options) { return this.request(endpoint, { ...options, method: 'GET' }); }
  post(endpoint, body, options) { return this.request(endpoint, { ...options, method: 'POST', body }); }
  put(endpoint, body, options) { return this.request(endpoint, { ...options, method: 'PUT', body }); }
  delete(endpoint, options) { return this.request(endpoint, { ...options, method: 'DELETE' }); }
}

window.api = new ProductionApiClient();
```

---

## 2. Live Polling Engine with Tab Visibility & Backoff

Avoid hammering the server when the user tabs away, and automatically scale down poll frequency when errors occur.

```javascript
class LivePollEngine {
  constructor(fetchFn, intervalMs = 10000, options = {}) {
    this.fetchFn = fetchFn;
    this.intervalMs = intervalMs;
    this.errorCount = 0;
    this.timerId = null;
    this.isRunning = false;
    this.onSuccess = options.onSuccess || (() => {});
    this.onError = options.onError || (() => {});

    // Listen to visibility state
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        this.pause();
      } else if (this.isRunning) {
        this.executePoll(); // Poll immediately upon focus
      }
    });
  }

  start() {
    this.isRunning = true;
    this.executePoll();
  }

  pause() {
    if (this.timerId) {
      clearTimeout(this.timerId);
      this.timerId = null;
    }
  }

  stop() {
    this.isRunning = false;
    this.pause();
  }

  async executePoll() {
    this.pause();
    if (!this.isRunning || document.hidden) return;

    try {
      const data = await this.fetchFn();
      this.errorCount = 0;
      this.onSuccess(data);
    } catch (err) {
      this.errorCount++;
      this.onError(err);
    }

    // Exponential backoff if consecutive errors occur
    const nextDelay = this.errorCount > 0
      ? Math.min(this.intervalMs * Math.pow(1.5, this.errorCount), 60000)
      : this.intervalMs;

    this.timerId = setTimeout(() => this.executePoll(), nextDelay);
  }
}
```

---

## 3. Server-Sent Events (SSE) / Real-Time Telemetry Stream

```javascript
class TelemetryStreamClient {
  constructor(streamUrl, onMessage, onError) {
    this.streamUrl = streamUrl;
    this.onMessage = onMessage;
    this.onError = onError;
    this.eventSource = null;
  }

  connect() {
    if (this.eventSource) this.eventSource.close();

    this.eventSource = new EventSource(this.streamUrl);

    this.eventSource.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        this.onMessage(payload);
      } catch (err) {
        this.onMessage({ raw: event.data });
      }
    };

    this.eventSource.onerror = (err) => {
      if (this.onError) this.onError(err);
      this.eventSource.close();
      // Auto-reconnect after 5 seconds
      setTimeout(() => this.connect(), 5000);
    };
  }

  disconnect() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }
}
```
