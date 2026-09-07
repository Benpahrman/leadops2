import React from 'react';
import ReactDOM from 'react-dom/client';
import { ClerkProvider } from '@clerk/clerk-react';
import App from './App';
import './styles.css';

const clerkPubKey = (typeof window !== 'undefined' && window.__CLERK_PUBLISHABLE_KEY__)
  || import.meta.env.VITE_CLERK_PUBLISHABLE_KEY
  || 'pk_test_ZmluZXItdG91Y2FuLTk2OTIuY2xlcmsuYWNjb3VudHMuZGV2JA';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ClerkProvider publishableKey={clerkPubKey} afterSignOutUrl="/">
      <App />
    </ClerkProvider>
  </React.StrictMode>
);
