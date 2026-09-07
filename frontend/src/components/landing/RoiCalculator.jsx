import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';

export default function RoiCalculator() {
  const navigate = useNavigate();
  const [hoursPerWeek, setHoursPerWeek] = useState(12);
  const [hourlyWage, setHourlyWage] = useState(45);

  const metrics = useMemo(() => {
    const monthlyHours = Math.round(hoursPerWeek * 4.33);
    const annualHours = hoursPerWeek * 52;
    const manualMonthlyCost = Math.round(monthlyHours * hourlyWage);
    const manualAnnualCost = manualMonthlyCost * 12;

    const leadopsMonthlyCost = 495; // Average Daily Sync Plan
    const leadopsAnnualCost = leadopsMonthlyCost * 12 + 250; // Setup deposit included

    const netMonthlySavings = Math.max(0, manualMonthlyCost - leadopsMonthlyCost);
    const netAnnualSavings = Math.max(0, manualAnnualCost - leadopsAnnualCost);
    const roiMultiplier = manualMonthlyCost > 0 ? (manualMonthlyCost / leadopsMonthlyCost).toFixed(1) : '1.0';

    return {
      monthlyHours,
      annualHours,
      manualMonthlyCost,
      manualAnnualCost,
      netMonthlySavings,
      netAnnualSavings,
      roiMultiplier,
    };
  }, [hoursPerWeek, hourlyWage]);

  return (
    <section id="roi-calculator" style={{ padding: '60px 0', background: 'var(--bg-surface)' }}>
      <div className="container" style={{ maxWidth: '960px' }}>
        <div style={{ textAlign: 'center', marginBottom: '36px' }}>
          <span style={{ color: 'var(--cyan)', fontFamily: 'var(--mono)', fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '1px' }}>
            Interactive Savings Model
          </span>
          <h2 style={{ fontSize: '32px', fontWeight: 800, color: '#fff', marginTop: '6px' }}>
            How Much Time &amp; Payroll Are You Wasting on Manual Lookups?
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '15px', marginTop: '8px' }}>
            Adjust the sliders below to see your team's real projected time reclaimed and dollar savings.
          </p>
        </div>

        <div className="card" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '36px', padding: '32px' }}>
          {/* Sliders Side */}
          <div>
            <div style={{ marginBottom: '28px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <label style={{ fontSize: '13px', fontWeight: 700, color: '#fff' }}>Weekly Hours Spent on Portal Searches</label>
                <span style={{ color: 'var(--cyan)', fontFamily: 'var(--mono)', fontWeight: 800, fontSize: '16px' }}>
                  {hoursPerWeek} hrs / week
                </span>
              </div>
              <input
                type="range"
                min="2"
                max="40"
                step="1"
                value={hoursPerWeek}
                onChange={(e) => setHoursPerWeek(Number(e.target.value))}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
                <span>2 hrs (Quick check)</span>
                <span>20 hrs (Part-time)</span>
                <span>40 hrs (Full-time staff)</span>
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <label style={{ fontSize: '13px', fontWeight: 700, color: '#fff' }}>Loaded Hourly Wage (Paralegal / Scout / Ops)</label>
                <span style={{ color: 'var(--green)', fontFamily: 'var(--mono)', fontWeight: 800, fontSize: '16px' }}>
                  ${hourlyWage} / hr
                </span>
              </div>
              <input
                type="range"
                min="25"
                max="120"
                step="5"
                value={hourlyWage}
                onChange={(e) => setHourlyWage(Number(e.target.value))}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
                <span>$25/hr (Data entry)</span>
                <span>$50/hr (Senior scout)</span>
                <span>$100/hr+ (Partner/Exec)</span>
              </div>
            </div>

            <div style={{ marginTop: '32px', padding: '16px', background: 'var(--card-alt)', borderRadius: '8px', border: '1px solid var(--border)' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                💡 <b>The Automation Dividend:</b> Instead of paying employees to navigate clunky government search forms, our 7-agent dev swarm extracts and validates every row automatically at 6:00 AM UTC.
              </div>
            </div>
          </div>

          {/* Realized ROI Results Side */}
          <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', background: 'var(--card-alt)', borderRadius: '12px', border: '1px solid var(--border-light)', padding: '24px' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-muted)' }}>PROJECTED SAVINGS</span>
                <span style={{ background: 'var(--green-glow)', color: 'var(--green)', padding: '4px 10px', borderRadius: '6px', fontSize: '12px', fontWeight: 800, fontFamily: 'var(--mono)' }}>
                  {metrics.roiMultiplier}x ROI
                </span>
              </div>

              <div style={{ marginBottom: '20px' }}>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Net Annual Dollar Savings:</div>
                <div style={{ fontSize: '36px', fontWeight: 800, color: 'var(--green)', fontFamily: 'var(--mono)', letterSpacing: '-0.5px' }}>
                  ${metrics.netAnnualSavings.toLocaleString()}
                  <span style={{ fontSize: '14px', color: 'var(--text-muted)', fontWeight: 500 }}> / year</span>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', borderTop: '1px solid var(--border)', paddingTop: '16px' }}>
                <div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Staff Time Reclaimed:</div>
                  <div style={{ fontSize: '18px', fontWeight: 700, color: '#fff', fontFamily: 'var(--mono)' }}>
                    {metrics.annualHours} hrs/yr
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Monthly Labor Saved:</div>
                  <div style={{ fontSize: '18px', fontWeight: 700, color: '#fff', fontFamily: 'var(--mono)' }}>
                    ${metrics.netMonthlySavings.toLocaleString()}/mo
                  </div>
                </div>
              </div>
            </div>

            <button
              className="btn btn-primary"
              style={{ width: '100%', padding: '12px', fontSize: '14px', marginTop: '24px' }}
              onClick={() => navigate('/p/lead-apex-roofing')}
            >
              Lock in These Savings in Sandbox ➔
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
