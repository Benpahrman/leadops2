import React, { useState } from 'react';
import { suggestColumns } from '../../services/api';
import { useToast } from '../../context/ToastContext';

export default function SchemaSelector({ slug, activeFields = [], onToggleField, onAddField }) {
  const { showToast } = useToast();
  const [aiSuggestions, setAiSuggestions] = useState([]);
  const [loadingAi, setLoadingAi] = useState(false);

  const handleSuggestAi = async () => {
    setLoadingAi(true);
    try {
      const data = await suggestColumns(slug);
      if (data.ok && data.suggestions && data.suggestions.length > 0) {
        setAiSuggestions(data.suggestions);
        showToast(`AI Pipeline Architect identified ${data.suggestions.length} candidate schema fields!`, 'success');
      } else {
        showToast('All standard public records fields are already enabled for this endpoint.', 'info');
      }
    } catch (err) {
      showToast('Could not query AI schema analyzer.', 'warning');
    } finally {
      setLoadingAi(false);
    }
  };

  const addField = (field) => {
    onAddField(field);
    setAiSuggestions((prev) => prev.filter((s) => s.field_name !== field));
    showToast(`Added '${field.replace(/_/g, ' ')}' to your data feed schema!`, 'success');
  };

  const getFieldMeta = (field) => {
    const f = field.toLowerCase();
    if (f.includes('number') || f.includes('id') || f.includes('case') || f.includes('permit')) {
      return { type: 'ID / VARCHAR', color: 'var(--cyan)' };
    }
    if (f.includes('date') || f.includes('time') || f.includes('posted')) {
      return { type: 'TIMESTAMP', color: 'var(--yellow)' };
    }
    if (f.includes('primary') || f.includes('debtor') || f.includes('company') || f.includes('contractor')) {
      return { type: 'ENTITY / TEXT', color: '#93c5fd' };
    }
    if (f.includes('secondary') || f.includes('owner') || f.includes('party') || f.includes('applicant')) {
      return { type: 'PARTY / TEXT', color: '#c4b5fd' };
    }
    if (f.includes('amount') || f.includes('value') || f.includes('valuation') || f.includes('bid') || f.includes('price')) {
      return { type: 'CURRENCY', color: 'var(--green)' };
    }
    if (f.includes('address') || f.includes('city') || f.includes('jurisdiction') || f.includes('county') || f.includes('location')) {
      return { type: 'GEOLOCATION', color: '#fca5a5' };
    }
    return { type: 'FIELD', color: 'var(--text-muted)' };
  };

  return (
    <div className="card" style={{ marginTop: '24px', background: 'rgba(15, 23, 42, 0.75)', border: '1px solid #1e3355' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px', marginBottom: '18px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#fff', letterSpacing: '-0.3px' }}>
              Extraction Schema &amp; Pipeline Mapping
            </h3>
            <span className="badge-tag badge-cyan">
              {activeFields.length} Attributes Active
            </span>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
            These attributes are parsed by the 7-agent extraction swarm and formatted for daily Google Sheets and Webhook dispatch.
          </p>
        </div>

        <button
          className="btn btn-outline"
          style={{
            borderColor: 'var(--purple)',
            color: '#d8b4fe',
            background: 'rgba(168, 85, 247, 0.08)',
            fontSize: '12px',
            padding: '8px 16px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
          }}
          onClick={handleSuggestAi}
          disabled={loadingAi}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
          </svg>
          <span>{loadingAi ? 'Analyzing Portal DOM...' : 'AI Schema Discovery'}</span>
        </button>
      </div>

      {/* Field Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(210px, 1fr))', gap: '10px' }}>
        {activeFields.map((f) => {
          const meta = getFieldMeta(f);
          return (
            <div
              key={f}
              onClick={() => onToggleField && onToggleField(f)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px 14px',
                borderRadius: '8px',
                background: 'rgba(56, 189, 248, 0.06)',
                border: '1px solid rgba(56, 189, 248, 0.25)',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
              title="Click to toggle column export"
            >
              <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', overflow: 'hidden' }}>
                <span style={{ fontSize: '13px', fontWeight: 700, color: '#fff', textTransform: 'capitalize', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
                  {f.replace(/_/g, ' ')}
                </span>
                <span className="data-type-pill" style={{ color: meta.color, width: 'fit-content' }}>
                  {meta.type}
                </span>
              </div>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--green)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            </div>
          );
        })}
      </div>

      {/* AI Suggestions Box */}
      {aiSuggestions.length > 0 && (
        <div style={{ marginTop: '20px', padding: '16px', background: 'rgba(168, 85, 247, 0.06)', borderRadius: '10px', border: '1px solid rgba(168, 85, 247, 0.3)' }}>
          <div style={{ fontSize: '12px', fontWeight: 700, color: '#d8b4fe', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span>AI Swarm Discovered Additional Portal Attributes:</span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {aiSuggestions.map((s) => (
              <button
                key={s.field_name}
                className="btn btn-outline"
                style={{
                  fontSize: '12px',
                  padding: '6px 12px',
                  borderColor: 'var(--purple)',
                  color: '#fff',
                  background: 'rgba(168, 85, 247, 0.12)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
                onClick={() => addField(s.field_name)}
                title={s.description || ''}
              >
                <span>+</span>
                <span>{s.label || s.field_name.replace(/_/g, ' ')}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

