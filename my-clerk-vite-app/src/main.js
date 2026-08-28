/**
 * LeadOps Data Portal - Accessible Frontend
 * 
 * Accessibility features:
 * - Semantic HTML5 landmarks (header, nav, main, section, article, aside)
 * - ARIA roles, labels, and live regions
 * - Proper heading hierarchy (h1-h4)
 * - Focus management and visible focus indicators
 * - Keyboard navigation support
 * - Color contrast ratios meeting WCAG AA
 * - Screen reader announcements for dynamic content
 */

import { Clerk } from "@clerk/clerk-js";
import "./style.css";

const publishableKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

if (!publishableKey) {
  throw new Error(
    "Missing VITE_CLERK_PUBLISHABLE_KEY. Please verify .env.local exists with your key."
  );
}

const clerk = new Clerk(publishableKey);

// Super Admin Emails ONLY (Founder view)
const ADMIN_EMAILS = ["pahrmancb@gmail.com", "pharmancb@gmail.com"];

const apiBaseUrl = import.meta.env.VITE_API_URL;

if (!apiBaseUrl) {
  throw new Error(
    "Missing VITE_API_URL. Please verify .env.local exists with your API URL."
  );
}

// Screen reader announcer for dynamic content
function createAriaLiveRegion() {
  const region = document.createElement("div");
  region.setAttribute("role", "status");
  region.setAttribute("aria-live", "polite");
  region.setAttribute("aria-atomic", "true");
  region.className = "sr-only";
  region.style.cssText = "position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0;";
  document.body.appendChild(region);
  return region;
}

const ariaLiveRegion = createAriaLiveRegion();

function announce(message) {
  ariaLiveRegion.textContent = "";
  // Small delay to ensure screen readers pick up the change
  setTimeout(() => {
    ariaLiveRegion.textContent = message;
  }, 100);
}

async function getHeaders(includeCsrf = false) {
  const headers = {};
  if (clerk && clerk.session) {
    const token = await clerk.session.getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
      if (includeCsrf) {
        const payload = JSON.parse(atob(token.split('.')[1]));
        headers["X-CSRF-Token"] = `csrf-${payload.sub}`;
      }
    }
  }
  return headers;
}

function escapeHtml(str) {
  const apos = String.fromCharCode(39);
  return String(str ?? '')
    .replace(/&/g, '&')
    .replace(/</g, '<')
    .replace(/>/g, '>')
    .replace(/"/g, '"')
    .replace(new RegExp(apos, 'g'), '&apos;');
}

// URL Parameter slug support: ?slug=...
const urlParams = new URLSearchParams(window.location.search);
let activeSlug = urlParams.get("slug") || "pahrman-asset-intelligence-lead-pahrman-intel-1787854118";
let allCompanies = [];
let activeSandbox = {
  slug: activeSlug,
  company_name: "Pahrman Asset Intelligence",
  contact_email: "benpahrman@gmail.com",
  jurisdiction: "Harris County, TX (Houston)",
  source_url: "https://www.cclerk.hctx.net/Applications/WebSearch/CourtSearch.aspx?CaseType=Probate",
  tier: "Daily Sync",
  deposit_paid: false,
  deposit_amount: 250.00,
  next_payment_due: false,
  next_payment_amount: 250.00,
  next_payment_purpose: "Milestone #2 ($250.00) & Activate Recurring Monthly Sync ($500/mo)",
  subscription_active: false,
  subscription_plan: "Daily Sync ($500.00/mo)",
  qa_score: null,
  state: "REVIEW",
  preview_rows: 25,
  sample: [],
};

async function loadAllCompanies() {
  try {
    const headers = await getHeaders();
    const res = await fetch(`${apiBaseUrl}/api/admin/all-companies`, { headers });
    if (res.ok) {
      const data = await res.json();
      allCompanies = data.companies || [];
    }
  } catch (e) {
    console.log("Could not load all companies:", e);
  }
}

async function loadUserLead(email) {
  try {
    const headers = await getHeaders();
    const res = await fetch(`${apiBaseUrl}/api/portal/my-lead?email=${encodeURIComponent(email)}`, { headers });
    if (res.ok) {
      activeSandbox = await res.json();
      activeSlug = activeSandbox.slug;
    }
  } catch (e) {
    console.log("Could not fetch user lead:", e);
  }
}

async function fetchSandboxData(slug) {
  try {
    const headers = await getHeaders();
    const res = await fetch(`${apiBaseUrl}/api/sandbox/${slug}`, { headers });
    if (res.ok) {
      activeSandbox = await res.json();
      activeSlug = slug;
    }
  } catch (e) {
    console.log("Using cached sandbox state", e);
  }
}

function getStateBadge(state) {
  const badges = {
    "REVIEW": { text: "Under Review", color: "#f59e0b", bg: "#451a03" },
    "CONVERSATIONAL_INTAKE": { text: "Intake", color: "#38bdf8", bg: "#1e3a5f" },
    "SOW_GENERATED": { text: "SOW Ready", color: "#38bdf8", bg: "#1e3a5f" },
    "DEPOSIT_PAID": { text: "Deposit Paid", color: "#6ee7b7", bg: "#064e3b" },
    "DEV_BUILDING": { text: "Building", color: "#7dd3fc", bg: "#1e3a5f" },
    "ESCROW_PREVIEW": { text: "Escrow Preview", color: "#fcd34d", bg: "#451a03" },
    "FINAL_PAID": { text: "Final Paid", color: "#6ee7b7", bg: "#064e3b" },
    "DELIVERED": { text: "Delivered", color: "#6ee7b7", bg: "#064e3b" },
    "WARRANTY_ACTIVE": { text: "Warranty Active", color: "#c4b5fd", bg: "#3b1f6b" },
  };
  return badges[state] || { text: state, color: "#94a3b8", bg: "#1e293b" };
}

function getPaymentStatusClass(paid) {
  return paid ? "payment-status-paid" : "payment-status-pending";
}

async function renderUI() {
  const app = document.getElementById("app");
  if (!app) return;

  const currentOrigin = window.location.origin;

  if (clerk.user) {
    const primaryEmail = (clerk.user.primaryEmailAddress?.emailAddress || "").toLowerCase().trim();
    const isFounder = ADMIN_EMAILS.includes(primaryEmail) || primaryEmail.includes("pahrmancb");

    if (isFounder) {
      await loadAllCompanies();
      await fetchSandboxData(activeSlug);
    } else {
      await loadUserLead(primaryEmail);
    }

    const clientPortalUrl = `${apiBaseUrl}/p/${activeSandbox.slug}`;
    const stateBadge = getStateBadge(activeSandbox.state);

    app.innerHTML = `
      <div id="app-wrapper">
        <!-- Skip link for keyboard users -->
        <a href="#main-content" class="skip-link">Skip to main content</a>

        <header class="site-header" role="banner">
          <div class="header-content">
            <div class="header-left">
              <h1 class="site-title">
                ${isFounder ? 'LeadOps Mission Control' : `Data Feed Portal: ${escapeHtml(activeSandbox.company_name)}`}
              </h1>
              <span class="user-role-badge ${isFounder ? 'role-admin' : 'role-client'}" aria-label="${isFounder ? 'Founder / Admin access' : 'Client account'}">
                ${isFounder ? '👑 Founder / Admin' : 'Client Account'}
              </span>
            </div>
            <p class="user-info" aria-live="polite">
              ${isFounder 
                ? `Logged in as Founder: <strong>${escapeHtml(primaryEmail)}</strong> • <span class="highlight">Global View Across All Companies</span>` 
                : `Logged in as: <strong>${escapeHtml(primaryEmail)}</strong> • Company: <strong>${escapeHtml(activeSandbox.company_name)}</strong>`}
            </p>
            <nav class="header-actions" aria-label="User actions">
              <div id="user-button" aria-label="User menu"></div>
              <button id="sign-out-btn" class="btn btn-secondary" aria-label="Sign out of LeadOps">
                Sign Out
              </button>
            </nav>
          </div>
        </header>

        <main id="main-content" role="main" tabindex="-1">
          ${isFounder ? `
            <!-- Founder-Only Multi-Company Switcher -->
            <section aria-labelledby="companies-heading" class="companies-section">
              <div class="section-header">
                <h2 id="companies-heading" class="section-title">
                  🏢 Active Client Accounts (<span id="company-count">${allCompanies.length || 1}</span>)
                </h2>
                <p class="section-subtitle" id="active-company-label">
                  Managing: <strong>${escapeHtml(activeSandbox.company_name)}</strong>
                </p>
              </div>
              <div class="quick-actions" role="group" aria-label="Quick actions">
                <button id="copy-portal-link-btn" class="btn btn-primary" aria-label="Copy client portal link to clipboard">
                  📋 Copy Client Portal Link
                </button>
                <button id="copy-email-btn" class="btn btn-accent" aria-label="Copy outreach email to clipboard">
                  📧 Copy Outreach Email
                </button>
                <a href="${clientPortalUrl}" target="_blank" rel="noopener" class="btn btn-outline" aria-label="Open public portal in new tab">
                  Open Public Portal ↗
                </a>
              </div>
              <div class="company-switcher" role="listbox" aria-label="Select active company" aria-activedescendant="">
                ${allCompanies.length > 0 ? allCompanies.map(c => {
                  const cStateBadge = getStateBadge(c.state);
                  const isActive = c.slug === activeSlug;
                  return `
                    <button 
                      class="company-switch-btn ${isActive ? 'active' : ''}" 
                      data-slug="${c.slug}"
                      role="option"
                      aria-selected="${isActive}"
                      aria-label="${escapeHtml(c.company_name)} - ${c.deposit_paid ? 'Deposit paid' : (c.state === 'REVIEW' ? 'Under review' : 'Building')}"
                      style="background: ${isActive ? cStateBadge.bg : '#27272a'}; border-color: ${isActive ? cStateBadge.color : '#3f3f46'};"
                    >
                      ${escapeHtml(c.company_name)} [${c.deposit_paid ? '✓ $250 Deposit' : (c.state === 'REVIEW' ? 'Reviewing' : 'Building')}]
                    </button>
                  `;
                }).join('') : `
                  <button 
                    class="company-switch-btn active" 
                    data-slug="${activeSlug}"
                    role="option"
                    aria-selected="true"
                    style="background: ${stateBadge.bg}; border-color: ${stateBadge.color};"
                  >
                    ${escapeHtml(activeSandbox.company_name)}
                  </button>
                `}
              </div>
            </section>
          ` : ''}

          <!-- Escrow & Build Milestones Tracker -->
          <section aria-labelledby="milestones-heading" class="milestones-section">
            <header class="section-header">
              <h2 id="milestones-heading" class="section-title">
                Escrow & Build Milestones: <strong>${escapeHtml(activeSandbox.company_name)}</strong>
              </h2>
              <p class="section-subtitle">Two-Payment Escrow Guarantee</p>
            </header>
            <div class="milestones-grid" role="list" aria-label="Payment milestones">
              <!-- Milestone 1: Deposit -->
              <article class="milestone-card ${getPaymentStatusClass(activeSandbox.deposit_paid)}" role="listitem" aria-labelledby="milestone1-title">
                <header>
                  <span class="milestone-label">MILESTONE 1</span>
                  <h3 id="milestone1-title" class="milestone-title">Deposit ($250.00)</h3>
                </header>
                <div class="milestone-status" aria-live="polite">
                  ${activeSandbox.deposit_paid 
                    ? '<span class="status-paid">✓ Paid & Verified</span>' 
                    : '<span class="status-pending">⚡ Awaiting Initial Deposit</span>'}
                </div>
              </article>

              <!-- Milestone 2: Dev Swarm & QA -->
              <article class="milestone-card" role="listitem" aria-labelledby="milestone2-title">
                <header>
                  <span class="milestone-label">MILESTONE 2 (BUILD)</span>
                  <h3 id="milestone2-title" class="milestone-title">Dev Swarm & QA</h3>
                </header>
                <div class="milestone-status" aria-live="polite">
                  ${activeSandbox.qa_score 
                    ? `QA Score: <strong>${activeSandbox.qa_score}%</strong> (Certified)` 
                    : 'Launches immediately upon deposit'}
                </div>
              </article>

              <!-- Milestone 3: Final Payment & Subscription -->
              <article class="milestone-card ${activeSandbox.next_payment_due ? 'payment-due' : (activeSandbox.final_paid ? 'payment-status-paid' : '')}" role="listitem" aria-labelledby="milestone3-title">
                <header>
                  <span class="milestone-label">MILESTONE 3 (DELIVERY)</span>
                  <h3 id="milestone3-title" class="milestone-title">Final Payment ($250.00)</h3>
                </header>
                <div class="milestone-status" aria-live="polite">
                  ${activeSandbox.next_payment_due 
                    ? '⚡ Due to Release Feed' 
                    : (activeSandbox.final_paid ? '✓ Paid & Active' : 'Locked until build complete')}
                </div>
              </article>
            </div>
          </section>

          ${!activeSandbox.deposit_paid ? `
            <!-- Deposit Action Card -->
            <section aria-labelledby="deposit-action-heading" class="action-card action-deposit">
              <header>
                <h2 id="deposit-action-heading" class="action-title">Lock in Milestone #1 Deposit ($250.00)</h2>
                <p class="action-description">Paying deposit immediately triggers the Autonomous Dev Swarm to author and verify your custom extraction feed.</p>
              </header>
              <div class="action-buttons" role="group" aria-label="Deposit payment options">
                <a href="${clientPortalUrl}" target="_blank" rel="noopener" class="btn btn-success btn-lg" aria-label="Pay $250.00 via PayPal public checkout">
                  Pay $250.00 via PayPal (Public Checkout)
                </a>
                <button id="simulate-deposit-btn" class="btn btn-outline btn-lg" aria-label="Simulate deposit and trigger dev swarm build (test mode)">
                  ⚡ [Test] Simulate Deposit & Trigger Build
                </button>
              </div>
            </section>
          ` : (activeSandbox.next_payment_due ? `
            <!-- Final Payment Action Card -->
            <section aria-labelledby="final-action-heading" class="action-card action-final">
              <header>
                <h2 id="final-action-heading" class="action-title">Scraper Built & Certified (100% QA Score)</h2>
                <p class="action-description">Release deliverables and start your automated sync subscription.</p>
              </header>
              <div class="action-buttons">
                <a href="${clientPortalUrl}" target="_blank" rel="noopener" class="btn btn-accent btn-lg" aria-label="Complete final payment of $250.00 via PayPal">
                  Complete Final Payment ($250.00) via PayPal
                </a>
              </div>
            </section>
          ` : '')}

          <!-- Company Details Card -->
          <section aria-labelledby="details-heading" class="details-section">
            <header class="section-header">
              <h2 id="details-heading" class="section-title">Client Profile & Target Portal</h2>
              <span class="registry-badge">Registry: ${escapeHtml(activeSandbox.jurisdiction)}</span>
            </header>
            <dl class="details-list">
              <div class="detail-item">
                <dt>Company</dt>
                <dd>${escapeHtml(activeSandbox.company_name)}</dd>
              </div>
              <div class="detail-item">
                <dt>Contact Email</dt>
                <dd>${escapeHtml(activeSandbox.contact_email)}</dd>
              </div>
              <div class="detail-item">
                <dt>Target Public Records</dt>
                <dd>
                  <a href="${encodeURI(activeSandbox.source_url)}" target="_blank" rel="noopener" aria-label="Open ${escapeHtml(activeSandbox.source_url)} in new tab">
                    ${escapeHtml(activeSandbox.source_url)} ↗
                  </a>
                </dd>
              </div>
              <div class="detail-item">
                <dt>Assigned Delivery Tier</dt>
                <dd>${escapeHtml(activeSandbox.subscription_plan)}</dd>
              </div>
              ${activeSandbox.qa_score ? `
                <div class="detail-item">
                  <dt>QA Certification Score</dt>
                  <dd><strong>${activeSandbox.qa_score}%</strong> (Escrow ${activeSandbox.qa_score >= 95 ? 'Ready' : 'Pending'})</dd>
                </div>
              ` : ''}
              ${activeSandbox.preview_rows ? `
                <div class="detail-item">
                  <dt>Sample Preview Rows</dt>
                  <dd>${activeSandbox.preview_rows} rows</dd>
                </div>
              ` : ''}
            </dl>
          </section>

          ${isFounder && allCompanies.length > 1 ? `
            <!-- Founder Analytics Summary -->
            <section aria-labelledby="analytics-heading" class="analytics-section">
              <h2 id="analytics-heading" class="section-title">Portfolio Overview</h2>
              <div class="analytics-grid" role="list">
                <article class="analytics-card" role="listitem">
                  <span class="analytics-value">${allCompanies.length}</span>
                  <span class="analytics-label">Total Companies</span>
                </article>
                <article class="analytics-card" role="listitem">
                  <span class="analytics-value">${allCompanies.filter(c => c.deposit_paid).length}</span>
                  <span class="analytics-label">Deposits Paid</span>
                </article>
                <article class="analytics-card" role="listitem">
                  <span class="analytics-value">${allCompanies.filter(c => c.final_paid).length}</span>
                  <span class="analytics-label">Final Payments</span>
                </article>
                <article class="analytics-card" role="listitem">
                  <span class="analytics-value">${allCompanies.filter(c => c.subscription_active).length}</span>
                  <span class="analytics-label">Active Subscriptions</span>
                </article>
              </div>
            </section>
          ` : ''}
        </main>

        <footer class="site-footer" role="contentinfo">
          <p>LeadOps Data Portal • Autonomous Record Extraction</p>
        </footer>
      </div>
    `;

    // Focus management - move focus to main content on render
    const mainContent = document.getElementById("main-content");
    if (mainContent) {
      mainContent.focus({ preventScroll: true });
    }

    // Copy Handlers with accessible feedback
    const copyPortalBtn = document.getElementById("copy-portal-link-btn");
    if (copyPortalBtn) {
      copyPortalBtn.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(clientPortalUrl);
          copyPortalBtn.setAttribute("aria-label", "Link copied to clipboard");
          copyPortalBtn.innerText = "✓ Copied Link!";
          announce("Client portal link copied to clipboard");
          setTimeout(() => {
            copyPortalBtn.setAttribute("aria-label", "Copy client portal link to clipboard");
            copyPortalBtn.innerText = "📋 Copy Client Portal Link";
          }, 2000);
        } catch (e) {
          announce("Failed to copy link");
        }
      });
    }

    const copyEmailBtn = document.getElementById("copy-email-btn");
    if (copyEmailBtn) {
      copyEmailBtn.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(`Subject: ${outreachSubject}\n\n${outreachBody}`);
          copyEmailBtn.setAttribute("aria-label", "Email copied to clipboard");
          copyEmailBtn.innerText = "✓ Copied Email!";
          announce("Outreach email copied to clipboard");
          setTimeout(() => {
            copyEmailBtn.setAttribute("aria-label", "Copy outreach email to clipboard");
            copyEmailBtn.innerText = "📧 Copy Outreach Email";
          }, 2000);
        } catch (e) {
          announce("Failed to copy email");
        }
      });
    }

    // Switcher Event Handlers with keyboard support
    document.querySelectorAll(".company-switch-btn").forEach(btn => {
      // Click handler
      btn.addEventListener("click", async (e) => {
        const targetSlug = e.currentTarget.getAttribute("data-slug");
        if (targetSlug) {
          activeSlug = targetSlug;
          announce(`Switched to ${e.currentTarget.textContent.trim()}`);
          await renderUI();
        }
      });

      // Keyboard handler
      btn.addEventListener("keydown", async (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          btn.click();
        }
      });
    });

    // Simulate Deposit Handler
    const simDepositBtn = document.getElementById("simulate-deposit-btn");
    if (simDepositBtn) {
      simDepositBtn.addEventListener("click", async () => {
        simDepositBtn.disabled = true;
        simDepositBtn.setAttribute("aria-busy", "true");
        simDepositBtn.innerText = "Triggering Dev Swarm...";
        announce("Starting dev swarm build");
        try {
          const headers = await getHeaders(true);
          await fetch(`${apiBaseUrl}/api/sandbox/${activeSandbox.slug}/pay-deposit`, { 
            method: "POST",
            headers
          });
          announce("Deposit simulated, dev swarm triggered");
          window.location.href = clientPortalUrl;
        } catch (e) {
          announce("Error triggering dev swarm");
          window.location.href = clientPortalUrl;
        }
      });

      // Keyboard handler
      simDepositBtn.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          simDepositBtn.click();
        }
      });
    }

    // User Button
    const userButtonDiv = document.getElementById("user-button");
    if (userButtonDiv) {
      try {
        clerk.mountUserButton(userButtonDiv, { afterSignOutUrl: currentOrigin });
      } catch (err) {}
    }

    // Sign Out
    const signOutBtn = document.getElementById("sign-out-btn");
    if (signOutBtn) {
      signOutBtn.addEventListener("click", async () => {
        try {
          await clerk.signOut({ redirectUrl: currentOrigin });
        } catch (e) {
          window.location.reload();
        }
      });
    }

  } else {
    // Public Landing Page & Auth Box
    app.innerHTML = `
      <div id="app-wrapper">
        <a href="#main-content" class="skip-link">Skip to main content</a>
        
        <main id="main-content" role="main" tabindex="-1" class="landing-page">
          <header class="landing-header">
            <h1>LeadOps Data Portal</h1>
            <p class="landing-tagline">
              Sign in to access your company's live custom record sandbox, 
              approve data schemas, or manage your recurring automated filings feed.
            </p>
          </header>
          
          <section aria-labelledby="signin-heading" class="auth-section">
            <h2 id="signin-heading" class="visually-hidden">Sign In</h2>
            <div id="clerk-auth-container" role="region" aria-label="Clerk authentication"></div>
          </section>
          
          <footer class="landing-footer">
            <p>LeadOps • Autonomous Record Extraction</p>
          </footer>
        </main>
      </div>
    `;

    const authContainer = document.getElementById("clerk-auth-container");
    if (authContainer) {
      try {
        clerk.mountSignIn(authContainer, {
          fallbackRedirectUrl: currentOrigin,
          forceRedirectUrl: currentOrigin,
          signUpFallbackRedirectUrl: currentOrigin,
          signUpForceRedirectUrl: currentOrigin,
          routing: "virtual",
        });
      } catch (err) {}
    }
  }
}

// Initialize Clerk
await clerk.load();
clerk.addListener(() => renderUI());
renderUI();