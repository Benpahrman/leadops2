import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ToastProvider } from './context/ToastContext';
import Header from './components/layout/Header';
import Footer from './components/layout/Footer';
import ChatWidget from './components/common/ChatWidget';

import LandingPage from './pages/LandingPage';
import SandboxPage from './pages/SandboxPage';
import DashboardPage from './pages/DashboardPage';
import AdminPage from './pages/AdminPage';
import TermsPage from './pages/TermsPage';
import PrivacyPage from './pages/PrivacyPage';
import CheckoutSuccessPage from './pages/CheckoutSuccessPage';
import CheckoutCancelPage from './pages/CheckoutCancelPage';

export default function App() {
  return (
    <ToastProvider>
      <BrowserRouter>
        <div className="app-shell">
          <Header />
          <Routes>
            <Route path="/" element={<LandingPage />} />
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
          <ChatWidget />
          <Footer />
        </div>
      </BrowserRouter>
    </ToastProvider>
  );
}
