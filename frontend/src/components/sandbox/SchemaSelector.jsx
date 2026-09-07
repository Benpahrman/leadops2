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

  return (
    <div className="card" style={{ marginTop: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px', marginBottom: '16px' }}>
        <div>
          <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#fff' }}>
            Active Extraction Schema Fields
          </h3>
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
            Click any field to toggle whether it will be extracted into your daily delivery sheet.
          </p>
        </div>

        <button
          className="btn btn-outline"
          style={{ borderColor: 'var(--purple)', color: 'var(--purple)' }}
          onClick={handleSuggestAi}
          disabled={loadingAi}
        >
          {loadingAi ? '⚡ Analyzing DOM...' : '✨ Alex AI Column Suggestions'}
        </button>
      </div>

      {/* Field Pills */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
        {activeFields.map((f) => (
          <span
            key={f}
            className="field-pill active"
            onClick={() => onToggleField && onToggleField(f)}
          >
            ✓ {f.replace(/_/g, ' ')}
          </span>
        ))}
      </div>

      {/* AI Suggestions Box */}
      {aiSuggestions.length > 0 && (
        <div style={{ marginTop: '16px', padding: '14px', background: 'var(--card-alt)', borderRadius: '8px', border: '1px solid var(--purple)' }}>
          <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--purple)', marginBottom: '8px' }}>
            ✨ Recommended Columns for this County Registry:
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {aiSuggestions.map((s) => (
              <button
                key={s.field_name}
                className="btn btn-outline"
                style={{ fontSize: '11px', padding: '4px 10px', borderColor: 'var(--purple)' }}
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
