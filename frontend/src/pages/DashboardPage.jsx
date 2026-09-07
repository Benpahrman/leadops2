import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useUser, useAuth, useClerk } from '@clerk/clerk-react';
import { fetchDashboard, claimAccount } from '../services/api';
import { useToast } from '../context/ToastContext';

import FeedDeliveriesTab from '../components/dashboard/FeedDeliveriesTab';
import SchemaFieldsTab from '../components/dashboard/SchemaFieldsTab';
import IntegrationsTab from '../components/dashboard/IntegrationsTab';
import BuyoutTab from '../components/dashboard/BuyoutTab';
import ReferralTab from '../components/dashboard/ReferralTab';

export default function DashboardPage() {
  const { leadId: paramLeadId } = useParams();
  const navigate = useNavigate();
  const { user, isSignedIn } = useUser();
  const { getToken } = useAuth();
  const { openSignIn } = useClerk();
  const { showToast } = useToast();

  // Determine active lead ID
  const [activeLeadId, setActiveLeadId] = useState(() => {
    if (paramLeadId) return paramLeadId;
    const stored = localStorage.getItem('leadops_active_lead_id');
    return stored || 'primary-feed';
  });

  const [dashState, setDashState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('feeds');
  const [isGuestPreview, setIsGuestPreview] = useState(false);

  // Sync route param with activeLeadId
  useEffect(() => {
    if (paramLeadId && paramLeadId !== activeLeadId) {
      setActiveLeadId(paramLeadId);
      localStorage.setItem('leadops_active_lead_id', paramLeadId);
    }
  }, [paramLeadId]);

  // Load dashboard data
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      let token = '';
      if (isSignedIn) {
        token = await getToken();
      }
      const data = await fetchDashboard(activeLeadId, token);
      setDashState(data);
    } catch (err) {
      console.error('Dashboard load error:', err);
      showToast(`Notice loading dashboard: ${err.message}`, 'warning');
    } finally {
      setLoading(false);
    }
  }, [activeLeadId, isSignedIn, getToken, showToast]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Bind Clerk account to Lead on sign in
  useEffect(() => {
    const bindAccount = async () => {
      if (isSignedIn && user && activeLeadId && activeLeadId !== 'primary-feed') {
        try {
          const token = await getToken();
          const email = user.primaryEmailAddress?.emailAddress || '';
          await claimAccount({
            userId: user.id,
            leadId: activeLeadId,
            email,
            token,
          });
          console.log(`[AUTH] Bound user ${user.id} (${email}) to lead ${activeLeadId}`);
        } catch (err) {
          console.warn('Account claim notice:', err);
        }
      }
    };
    bindAccount();
  }, [isSignedIn, user, activeLeadId, getToken]);

  const companyName = dashState?.company_name || activeLeadId.replace('lead-', '').replace(/-/g, ' ').toUpperCase();

  const handleOpenInvoice = () => {
    window.open(`/api/dashboard/${activeLeadId}/invoice`, '_blank');
  };

  return (
    <main style={{ padding: '30px 0 80px' }}>
      <div className="container">
        {/* Top Header Row */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', marginBottom: '24px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
              <span className="brand-icon" style={{ width: '26px', height: '26px', fontSize: '13px' }}>⚡</span>
              <h1 style={{ fontSize: '22px', fontWeight: 800, color: '#fff' }}>
                {companyName} Feed Console
              </h1>
              <span className="badge-tag badge-cyan">{activeLeadId}</span>
            </div>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
              ● Live Stream Active • Automated Daily Deliveries at 06:00 AM UTC
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <button className="btn btn-outline" style={{ borderColor: 'var(--cyan)', color: 'var(--cyan)' }} onClick={handleOpenInvoice}>
              📄 Invoice &amp; Receipt
            </button>
            <button
              className="btn btn-outline"
              onClick={() => navigate(`/p/${dashState?.slug || activeLeadId}`)}
            >
              View Sandbox
            </button>
          </div>
        </div>

        {/* Clerk Auth Gate Banner (If not signed in and not in guest preview) */}
        {!isSignedIn && !isGuestPreview && (
          <div className="card" style={{ marginBottom: '24px', background: 'linear-gradient(135deg, rgba(56, 189, 248, 0.1), rgba(168, 85, 247, 0.1))', border: '1px solid var(--border-highlight)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
              <div>
                <div style={{ fontSize: '15px', fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span>🔒</span> Secure Your Account with Passwordless Sign-In
                </div>
                <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Sign in with your email to bind your company feed and access your dashboard from any device or phone without remembering passwords.
                </div>
              </div>

              <div style={{ display: 'flex', gap: '10px' }}>
                <button
                  className="btn btn-primary"
                  onClick={() => openSignIn()}
                >
                  Sign In with Email OTP
                </button>
                <button
                  className="btn btn-outline"
                  onClick={() => setIsGuestPreview(true)}
                >
                  Continue in Preview Mode
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Tab Navigation */}
        <div className="tab-list" style={{ marginBottom: '24px' }}>
          <button
            className={`tab-button ${activeTab === 'feeds' ? 'active' : ''}`}
            onClick={() => setActiveTab('feeds')}
          >
            📊 Production Feed &amp; Deliveries
          </button>
          <button
            className={`tab-button ${activeTab === 'schema' ? 'active' : ''}`}
            onClick={() => setActiveTab('schema')}
          >
            ⚙️ Schema Fields &amp; Quotas
          </button>
          <button
            className={`tab-button ${activeTab === 'integrations' ? 'active' : ''}`}
            onClick={() => setActiveTab('integrations')}
          >
            🚀 Google Sheets &amp; Webhooks
          </button>
          <button
            className={`tab-button ${activeTab === 'buyout' ? 'active' : ''}`}
            onClick={() => setActiveTab('buyout')}
          >
            📦 Code Buyout (.zip)
          </button>
          <button
            className={`tab-button ${activeTab === 'referral' ? 'active' : ''}`}
            onClick={() => setActiveTab('referral')}
          >
            🎁 Refer &amp; Earn ($100)
          </button>
        </div>

        {/* Tab Contents */}
        {loading ? (
          <div style={{ padding: '60px 0', textAlign: 'center' }}>
            <div style={{ fontSize: '32px', animation: 'spin 1.5s linear infinite', display: 'inline-block' }}>⚡</div>
            <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginTop: '12px' }}>
              Loading live feed telemetry and destination settings...
            </p>
          </div>
        ) : (
          <>
            {activeTab === 'feeds' && (
              <FeedDeliveriesTab
                leadId={activeLeadId}
                dashState={dashState}
                onRefresh={loadData}
              />
            )}

            {activeTab === 'schema' && (
              <SchemaFieldsTab
                leadId={activeLeadId}
                dashState={dashState}
                onRefresh={loadData}
              />
            )}

            {activeTab === 'integrations' && (
              <IntegrationsTab
                leadId={activeLeadId}
                dashState={dashState}
                onRefresh={loadData}
              />
            )}

            {activeTab === 'buyout' && (
              <BuyoutTab
                leadId={activeLeadId}
                dashState={dashState}
              />
            )}

            {activeTab === 'referral' && (
              <ReferralTab
                leadId={activeLeadId}
                dashState={dashState}
              />
            )}
          </>
        )}
      </div>
    </main>
  );
}
