import React from 'react';

export default function FleetWarmupRoadmap({
  warmupCycle,
  inboxes = [],
  handleStartWarmup,
  startingWarmup = false,
  handleDispatchWarmupBatch,
  dispatchingWarmup = false,
  handleRunWarmupMonitoring,
  monitoringWarmup = false,
}) {
  const schedule = warmupCycle?.schedule || [
    { stage: 1, name: 'Stage 1: Initial Peer Warmup', days: 'Days 1–4', daily_volume: '3–5/day', composition: '100% Peer Warm-up', jitter: '300–600s delay', active: true, completed: false },
    { stage: 2, name: 'Stage 2: Gradual Step Up', days: 'Days 5–8', daily_volume: '8–12/day', composition: '100% Peer Warm-up', jitter: '240–480s delay', active: false, completed: false },
    { stage: 3, name: 'Stage 3: Pre-Outreach Baseline', days: 'Days 9–14', daily_volume: '15–20/day', composition: '100% Peer Warm-up', jitter: '180–360s delay', active: false, completed: false },
    { stage: 4, name: 'Stage 4: Initial Live Outbound', days: 'Days 15–21', daily_volume: '25/day', composition: '5 Cold + 20 Warm-up', jitter: '180–420s delay', active: false, completed: false },
    { stage: 5, name: 'Stage 5: Production Expansion', days: 'Days 22–30', daily_volume: '35/day', composition: '15 Cold + 20 Warm-up', jitter: '180–420s delay', active: false, completed: false },
    { stage: 6, name: 'Stage 6: Steady State Velocity', days: 'Day 31+', daily_volume: '40–50/day', composition: '30 Cold + 15–20 Warmup', jitter: 'Continuous Warm-up', active: false, completed: false },
  ];

  return (
    <div
      style={{
        background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.85) 100%)',
        border: '1px solid rgba(56, 189, 248, 0.35)',
        borderRadius: 'var(--radius-md)',
        padding: '24px',
        marginBottom: '24px',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.36), 0 0 16px rgba(56, 189, 248, 0.1)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px', marginBottom: '20px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
            <div
              style={{
                width: '42px',
                height: '42px',
                borderRadius: '10px',
                background: 'rgba(56, 189, 248, 0.2)',
                border: '1px solid rgba(56, 189, 248, 0.5)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '20px',
              }}
            >
              🔥
            </div>
            <div>
              <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#fff', margin: 0 }}>
                31-Day Domain Warmup &amp; Capacity Roadmap
              </h3>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                Current Stage: <span style={{ color: 'var(--cyan)', fontWeight: 700 }}>{warmupCycle?.current_stage_name || 'Stage 1: Initial Peer Warmup (Days 1–4)'}</span> • Day {warmupCycle?.days_elapsed || 1} of 31
              </div>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
          <button
            className="btn btn-primary"
            style={{
              fontSize: '12px',
              padding: '6px 14px',
              background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
              border: '1px solid #fbbf24',
              boxShadow: '0 0 10px rgba(245, 158, 11, 0.3)',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
            }}
            onClick={handleStartWarmup}
            disabled={startingWarmup}
            title="Sync and initialize Day 1 warmup timestamp for all sending inboxes"
          >
            <span>🔥</span>
            <span>{startingWarmup ? '⏳ Starting...' : 'Start / Re-sync Warmup'}</span>
          </button>

          <button
            className="btn btn-secondary"
            style={{
              fontSize: '12px',
              padding: '6px 12px',
              borderColor: '#38bdf8',
              color: '#38bdf8',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
            }}
            onClick={() => handleDispatchWarmupBatch(3)}
            disabled={dispatchingWarmup}
            title="Immediately dispatch a batch of 3 peer warmup emails across available inboxes"
          >
            <span>⚡</span>
            <span>{dispatchingWarmup ? '⏳ Dispatching...' : 'Run Warmup Batch (3)'}</span>
          </button>

          <button
            className="btn btn-outline"
            style={{
              fontSize: '12px',
              padding: '6px 12px',
              borderColor: '#a78bfa',
              color: '#c4b5fd',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
            }}
            onClick={handleRunWarmupMonitoring}
            disabled={monitoringWarmup}
            title="Scan peer receiver inboxes for unspam, star, and reply actions"
          >
            <span>🛡️</span>
            <span>{monitoringWarmup ? '⏳ Scanning...' : 'Scan Receivers'}</span>
          </button>
        </div>
      </div>

      {/* Visual Progress Bar */}
      <div style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px' }}>
          <span>Warmup Progression: <b style={{ color: '#fff' }}>Day {warmupCycle?.days_elapsed || 1} / 31</b></span>
          <span style={{ color: 'var(--cyan)', fontWeight: 700 }}>{Math.min(100, Math.round(((warmupCycle?.days_elapsed || 1) / 31) * 100))}% Completed</span>
        </div>
        <div style={{ width: '100%', height: '10px', background: 'rgba(255, 255, 255, 0.08)', borderRadius: '6px', overflow: 'hidden', position: 'relative' }}>
          <div
            style={{
              height: '100%',
              width: `${Math.min(100, Math.max(3, (((warmupCycle?.days_elapsed || 1) / 31) * 100)))}%`,
              background: 'linear-gradient(90deg, #10b981 0%, #0ea5e9 60%, #6366f1 100%)',
              borderRadius: '6px',
              transition: 'width 0.6s ease',
              boxShadow: '0 0 12px rgba(14, 165, 233, 0.5)',
            }}
          />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: 'var(--text-dim)', marginTop: '6px' }}>
          <span>Day 1 (3–5/day)</span>
          <span>Day 5 (8–12/day)</span>
          <span>Day 9 (15–20/day)</span>
          <span>Day 15 (25/day + Live)</span>
          <span>Day 22 (35/day)</span>
          <span>Day 31+ (50/day Steady)</span>
        </div>
      </div>

      {/* 6-Stage Domain Warmup Roadmap Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px', marginBottom: '20px' }}>
        {schedule.map((stg) => {
          const isActive = stg.active;
          const isCompleted = stg.completed;
          return (
            <div
              key={stg.stage || stg.name}
              style={{
                padding: '14px 16px',
                borderRadius: '8px',
                background: isActive
                  ? 'rgba(56, 189, 248, 0.12)'
                  : isCompleted
                  ? 'rgba(16, 185, 129, 0.08)'
                  : 'rgba(15, 23, 42, 0.6)',
                border: isActive
                  ? '2px solid var(--cyan)'
                  : isCompleted
                  ? '1px solid rgba(16, 185, 129, 0.4)'
                  : '1px solid #1e3355',
                boxShadow: isActive ? '0 0 16px rgba(56, 189, 248, 0.2)' : 'none',
                position: 'relative',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                <span style={{ fontSize: '11px', fontWeight: 800, color: isActive ? 'var(--cyan)' : isCompleted ? 'var(--green)' : 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  {stg.days}
                </span>
                <span
                  style={{
                    fontSize: '9px',
                    fontWeight: 800,
                    padding: '1px 6px',
                    borderRadius: '4px',
                    background: isActive ? 'rgba(56, 189, 248, 0.25)' : isCompleted ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255, 255, 255, 0.06)',
                    color: isActive ? 'var(--cyan)' : isCompleted ? 'var(--green)' : 'var(--text-dim)',
                  }}
                >
                  {isActive ? '⚡ ACTIVE' : isCompleted ? '✓ DONE' : '⏳ QUEUED'}
                </span>
              </div>
              <div style={{ fontSize: '14px', fontWeight: 800, color: isActive ? 'var(--cyan)' : '#fff', marginBottom: '2px' }}>
                {stg.daily_volume} ({stg.name})
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', lineHeight: 1.3 }}>
                <b>Composition:</b> {stg.composition}
              </div>
              <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginTop: '3px' }}>
                ⏱️ {stg.jitter}
              </div>
            </div>
          );
        })}
      </div>

      {/* Per-Inbox Warmup Allocation Breakdown */}
      <div style={{ background: 'rgba(15, 23, 42, 0.7)', border: '1px solid #1e3355', borderRadius: '8px', padding: '16px' }}>
        <div style={{ fontSize: '12px', fontWeight: 700, color: '#fff', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span>📬 Live Inbox Warmup Allocation</span>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 400 }}>
            (Quota automatically enforced by WarmupManager in auto_outreach.py)
          </span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '10px' }}>
          {inboxes.map((ib) => {
            const dailyLimit = ib.daily_limit || (warmupCycle?.per_inbox_daily_limit || 5);
            const sentToday = ib.sent_today || 0;
            const pct = Math.min(100, Math.round((sentToday / (dailyLimit || 1)) * 100));
            const isOlf = ib.provider === 'olfmailer' || ib.email_address?.includes('olfmailer');
            return (
              <div
                key={ib.inbox_id}
                style={{
                  background: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: '6px',
                  padding: '10px 12px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <span style={{ fontSize: '12px', fontWeight: 700, color: '#fff' }}>
                    {isOlf ? '🚀 ' : '✉️ '}{ib.email_address}
                  </span>
                  <span style={{ fontSize: '10px', color: 'var(--cyan)', fontWeight: 700 }}>
                    {sentToday} / {dailyLimit} sent
                  </span>
                </div>
                <div style={{ width: '100%', height: '4px', background: 'rgba(255, 255, 255, 0.1)', borderRadius: '2px', overflow: 'hidden' }}>
                  <div
                    style={{
                      width: `${pct}%`,
                      height: '100%',
                      background: pct >= 100 ? '#fbbf24' : 'var(--green)',
                      borderRadius: '2px',
                    }}
                  />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: 'var(--text-dim)', marginTop: '4px' }}>
                  <span>{ib.from_name || 'Alex | OmniLeadFeeder'}</span>
                  <span>{dailyLimit - sentToday} remaining</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
