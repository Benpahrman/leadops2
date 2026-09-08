import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { SignedIn, SignedOut, UserButton, useClerk } from '@clerk/clerk-react';

export default function Header() {
  const navigate = useNavigate();
  const { openSignIn } = useClerk();

  const handlePortalClick = () => {
    const storedLead = localStorage.getItem('leadops_active_lead_id');
    if (storedLead && storedLead !== 'primary-feed') {
      navigate(`/dashboard/${storedLead}`);
    } else {
      navigate('/dashboard');
    }
  };

  return (
    <header className="site-header">
      <div className="container header-inner">
        <div className="brand-wrap" onClick={() => navigate('/')}>
          <div className="brand-icon" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--primary)' }}>
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
            </svg>
          </div>
          <span className="brand-title">OmniLeadFeeder</span>
          <span className="live-badge">
            <span className="live-dot"></span>
            LIVE FEEDS
          </span>
        </div>

        <nav className="nav-links">
          <Link to="/" className="nav-link">Platform</Link>
          <Link to="/get-started" className="nav-link" style={{ color: 'var(--cyan)', fontWeight: 600 }}>Build Pipeline</Link>
          <Link to="/p/lead-apex-roofing" className="nav-link">Sample Sandbox</Link>
          <a href="/#roi-calculator" className="nav-link">ROI Calculator</a>
          <a href="/#pricing" className="nav-link">Pricing</a>
        </nav>

        <div className="header-actions">
          <button
            className="btn btn-outline"
            style={{ borderColor: 'var(--cyan)', color: 'var(--cyan)' }}
            onClick={handlePortalClick}
          >
            Client Portal ➔
          </button>

          <SignedOut>
            <button
              className="btn btn-primary"
              onClick={() => openSignIn()}
            >
              Sign In
            </button>
          </SignedOut>

          <SignedIn>
            <UserButton afterSignOutUrl="/" />
          </SignedIn>
        </div>
      </div>
    </header>
  );
}
