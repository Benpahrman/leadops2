import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ToastProvider } from './context/ToastContext';
import Header from './components/layout/Header';
import Footer from './components/layout/Footer';
import ChatWidget from './components/common/ChatWidget';

import LandingPage from './pages/LandingPage';
import SandboxPage from './pages/SandboxPage';
import DashboardPage from './pages/DashboardPage';
import PipelineIntakePage from './pages/PipelineIntakePage';

// Lazy load large administrative and secondary pages
const AdminPage = lazy(() => import('./pages/AdminPage'));
const TermsPage = lazy(() => import('./pages/TermsPage'));
const PrivacyPage = lazy(() => import('./pages/PrivacyPage'));
const CheckoutSuccessPage = lazy(() => import('./pages/CheckoutSuccessPage'));
const CheckoutCancelPage = lazy(() => import('./pages/CheckoutCancelPage'));

export default function App() {
  return (
    <ToastProvider>
      <BrowserRouter>
        <div className="app-shell">
          <Header />
          <Suspense fallback={<div className="loading-container" style={{ minHeight: '60vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><div className="spinner"></div></div>}>
            <Routes>
              <Route path="/" element={<LandingPage />} />
              <Route path="/get-started" element={<PipelineIntakePage />} />
              <Route path="/build" element={<Navigate to="/get-started" replace />} />
              <Route path="/pipeline/new" element={<Navigate to="/get-started" replace />} />
              <Route path="/p/:slug" element={<SandboxPage />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/dashboard/:leadId" element={<DashboardPage />} />
              <Route path="/admin" element={<AdminPage />} />
              <Route path="/terms" element={<TermsPage />} />
              <Route path="/privacy" element={<PrivacyPage />} />
              <Route path="/checkout/success" element={<CheckoutSuccessPage />} />
              <Route path="/checkout/cancel" element={<CheckoutCancelPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
          <ChatWidget />
          <Footer />
        </div>
      </BrowserRouter>
    </ToastProvider>
  );
}
