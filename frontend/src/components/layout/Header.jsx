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
          <div className="brand-icon">⚡</div>
          <span className="brand-title">OmniLeadFeeder</span>
          <span className="live-badge">
            <span className="live-dot"></span>
            LIVE FEEDS
          </span>
        </div>

        <nav className="nav-links">
          <Link to="/" className="nav-link">Platform</Link>
          <a href="/#roi-calculator" className="nav-link">ROI Calculator</a>
          <Link to="/p/lead-apex-roofing" className="nav-link">Sample Sandbox</Link>
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
