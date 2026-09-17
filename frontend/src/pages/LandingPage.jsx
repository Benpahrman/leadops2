import React from 'react';
import HeroSection from '../components/landing/HeroSection';
import LivePipelineInspector from '../components/landing/LivePipelineInspector';
import VerticalPlaybooks from '../components/landing/VerticalPlaybooks';
import FeaturesGrid from '../components/landing/FeaturesGrid';
import ComplianceTrustSection from '../components/landing/ComplianceTrustSection';
import RoiCalculator from '../components/landing/RoiCalculator';
import PricingCards from '../components/landing/PricingCards';

export default function LandingPage() {
  return (
    <main>
      <HeroSection />
      <LivePipelineInspector />
      <VerticalPlaybooks />
      <FeaturesGrid />
      <ComplianceTrustSection />
      <RoiCalculator />
      <PricingCards />
    </main>
  );
}
