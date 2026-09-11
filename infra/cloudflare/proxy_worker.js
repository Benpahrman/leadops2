/**
 * Cloudflare Edge Worker Proxy for LeadOps Swarm
 * 
 * Proxies HTTP/HTTPS requests through Cloudflare's global edge consumer network.
 * Bypasses Azure datacenter IP bans and Cloudflare anti-bot blocks on government portals.
 * Free tier: 100,000 requests per day with zero credit card required.
 */

export default {
  async fetch(request, env, ctx) {
    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, HEAD, POST, OPTIONS",
      "Access-Control-Allow-Headers": "*",
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
    }

    const urlObj = new URL(request.url);
    let targetUrl = urlObj.searchParams.get("url");

    // Support POST JSON payload
    let customHeaders = {};
    let customMethod = "GET";
    let customBody = null;

    if (request.method === "POST" && !targetUrl) {
      try {
        const bodyJson = await request.json();
        targetUrl = bodyJson.url;
        customHeaders = bodyJson.headers || {};
        customMethod = bodyJson.method || "GET";
        customBody = bodyJson.body || null;
      } catch (e) {
        return new Response(JSON.stringify({ error: "Invalid JSON request body" }), {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" }
        });
      }
    }

    if (!targetUrl) {
      return new Response(JSON.stringify({
        status: "active",
        service: "LeadOps Cloudflare Edge Proxy",
        usage: "GET /?url=https://example.com OR POST { url: 'https://example.com' }"
      }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" }
      });
    }

    try {
      const headers = new Headers();
      headers.set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36");
      headers.set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8");
      headers.set("Accept-Language", "en-US,en;q=0.9");

      // Merge custom headers
      for (const [key, value] of Object.entries(customHeaders)) {
        if (!["host", "connection", "content-length"].includes(key.toLowerCase())) {
          headers.set(key, value);
        }
      }

      const fetchOptions = {
        method: customMethod,
        headers: headers,
        redirect: "follow",
      };

      if (customBody && customMethod !== "GET" && customMethod !== "HEAD") {
        fetchOptions.body = customBody;
      }

      const response = await fetch(targetUrl, fetchOptions);
      const newResponseHeaders = new Headers(response.headers);
      for (const [k, v] of Object.entries(corsHeaders)) {
        newResponseHeaders.set(k, v);
      }

      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: newResponseHeaders
      });

    } catch (err) {
      return new Response(JSON.stringify({
        error: "Edge fetch failure",
        message: err.message,
        target_url: targetUrl
      }), {
        status: 502,
        headers: { ...corsHeaders, "Content-Type": "application/json" }
      });
    }
  }
};
