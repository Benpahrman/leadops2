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
        showToast(`Alex AI discovered ${data.suggestions.length} relevant schema fields!`, 'success');
      } else {
        showToast('All standard public records fields are already enabled!', 'info');
      }
    } catch (err) {
      showToast('Could not query AI schema suggester.', 'warning');
    } finally {
      setLoadingAi(false);
    }
  };

  const addField = (field) => {
    onAddField(field);
    setAiSuggestions((prev) => prev.filter((s) => s.field_name !== field));
    showToast(`Added '${field.replace(/_/g, ' ')}' to your feed schema!`, 'success');
  };

  const getFieldIcon = (field) => {
    const f = field.toLowerCase();
    if (f.includes('number') || f.includes('id') || f.includes('case') || f.includes('permit')) return '#️⃣';
    if (f.includes('date') || f.includes('time') || f.includes('posted')) return '📅';
    if (f.includes('primary') || f.includes('debtor') || f.includes('company') || f.includes('contractor')) return '🏢';
    if (f.includes('secondary') || f.includes('owner') || f.includes('party') || f.includes('applicant')) return '👤';
    if (f.includes('amount') || f.includes('value') || f.includes('valuation') || f.includes('bid') || f.includes('price')) return '💲';
    if (f.includes('address') || f.includes('city') || f.includes('jurisdiction') || f.includes('county') || f.includes('location')) return '📍';
    return '📋';
  };

  return (
    <div className="card" style={{ marginTop: '24px', background: 'rgba(15, 23, 42, 0.7)', border: '1px solid #1e2e4a' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px', marginBottom: '18px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#fff', letterSpacing: '-0.3px' }}>
              Active Extraction Schema Pipeline
            </h3>
            <span className="badge-tag badge-cyan">
              {activeFields.length} Columns Active
            </span>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
            These attributes will be automatically mapped and delivered to your daily Google Sheet and Webhook destination.
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
          {loadingAi ? '⚡ Analyzing DOM...' : '✨ Alex AI Column Suggestions'}
        </button>
      </div>

      {/* Field Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '10px' }}>
        {activeFields.map((f) => (
          <div
            key={f}
            onClick={() => onToggleField && onToggleField(f)}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '10px 14px',
              borderRadius: '8px',
              background: 'rgba(56, 189, 248, 0.08)',
              border: '1px solid rgba(56, 189, 248, 0.3)',
              cursor: 'pointer',
              transition: 'all 0.15s',
            }}
            title="Click to toggle column export"
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
              <span style={{ fontSize: '14px' }}>{getFieldIcon(f)}</span>
              <span style={{ fontSize: '12px', fontWeight: 700, color: '#fff', textTransform: 'capitalize', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
                {f.replace(/_/g, ' ')}
              </span>
            </div>
            <span style={{ color: 'var(--green)', fontSize: '12px', fontWeight: 800 }}>✓</span>
          </div>
        ))}
      </div>

      {/* AI Suggestions Box */}
      {aiSuggestions.length > 0 && (
        <div style={{ marginTop: '20px', padding: '16px', background: 'rgba(168, 85, 247, 0.06)', borderRadius: '10px', border: '1px solid rgba(168, 85, 247, 0.3)' }}>
          <div style={{ fontSize: '12px', fontWeight: 700, color: '#d8b4fe', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span>✨ Alex AI Discovered Additional Attributes in Portal DOM:</span>
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
                }}
                onClick={() => addField(s.field_name)}
                title={s.description || ''}
              >
                + {s.label || s.field_name.replace(/_/g, ' ')}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
