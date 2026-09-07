import React from 'react';
import HeroSection from '../components/landing/HeroSection';
import FeaturesGrid from '../components/landing/FeaturesGrid';
import RoiCalculator from '../components/landing/RoiCalculator';
import PricingCards from '../components/landing/PricingCards';

export default function LandingPage() {
  return (
    <main>
      <HeroSection />
      <FeaturesGrid />
      <RoiCalculator />
      <PricingCards />
    </main>
  );
}
