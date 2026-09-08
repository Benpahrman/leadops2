import React, { useState, useEffect, useMemo, useRef } from 'react';

export default function CommandPalette({
  isOpen,
  onClose,
  activeTab,
  onSelectTab,
  pipeline = [],
  onSelectLead,
  actions = [],
}) {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef(null);
  const listRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  const tabs = [
    { id: 'tab-deals', label: 'Go to Deals & Customers', tabKey: 'deals', icon: '📊', category: 'Navigation' },
    { id: 'tab-kanban', label: 'Go to Stage Kanban', tabKey: 'kanban', icon: '📌', category: 'Navigation' },
    { id: 'tab-swarm', label: 'Go to Dev Swarms & QA Gate', tabKey: 'swarm', icon: '🤖', category: 'Navigation' },
    { id: 'tab-accounting', label: 'Go to Accounting & Escrow Vault', tabKey: 'accounting', icon: '💰', category: 'Navigation' },
    { id: 'tab-scrapers', label: 'Go to Scrapers & Datasets', tabKey: 'scrapers', icon: '⚡', category: 'Navigation' },
    { id: 'tab-daily', label: 'Go to Automated Daily Feeds', tabKey: 'daily', icon: '📅', category: 'Navigation' },
  ];

  const items = useMemo(() => {
    const q = query.toLowerCase().trim();

    const filteredTabs = tabs
      .filter((t) => !q || t.label.toLowerCase().includes(q) || t.tabKey.toLowerCase().includes(q))
      .map((t) => ({
        ...t,
        type: 'tab',
        perform: () => {
          onSelectTab(t.tabKey);
          onClose();
        },
      }));

    const filteredActions = actions
      .filter((a) => !q || a.label.toLowerCase().includes(q))
      .map((a) => ({
        ...a,
        type: 'action',
        perform: () => {
          a.run();
          onClose();
        },
      }));

    const filteredLeads = pipeline
      .filter((l) => {
        if (!q) return false;
        const name = (l.company_name || '').toLowerCase();
        const contact = (l.contact_name || '').toLowerCase();
        const id = (l.id || '').toLowerCase();
        const jurisdiction = (l.jurisdiction || '').toLowerCase();
        return name.includes(q) || contact.includes(q) || id.includes(q) || jurisdiction.includes(q);
      })
      .slice(0, 8)
      .map((l) => ({
        id: `lead-${l.id}`,
        label: `${l.company_name || 'Unnamed Company'} (${l.state})`,
        subtitle: `${l.jurisdiction || 'Direct Lead'} • ID: ${l.id}`,
        icon: '🏢',
        category: 'Live Leads',
        type: 'lead',
        lead: l,
        perform: () => {
          onSelectLead?.(l);
          onClose();
        },
      }));

    return [...filteredTabs, ...filteredActions, ...filteredLeads];
  }, [query, tabs, actions, pipeline, onSelectTab, onSelectLead, onClose]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [items.length]);

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % (items.length || 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + items.length) % (items.length || 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (items[selectedIndex]) {
        items[selectedIndex].perform();
      }
    } else if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="admin-modal-overlay" onClick={onClose} style={{ alignItems: 'flex-start', paddingTop: '12vh' }}>
      <div
        className="admin-modal-content"
        style={{
          maxWidth: '640px',
          padding: 0,
          background: '#0c1527',
          border: '1px solid var(--border-light)',
          borderRadius: 'var(--radius-lg)',
          overflow: 'hidden',
          boxShadow: '0 24px 60px rgba(0, 0, 0, 0.8)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            padding: '16px 20px',
            borderBottom: '1px solid var(--border)',
            background: 'rgba(255, 255, 255, 0.02)',
          }}
        >
          <span style={{ fontSize: '18px', color: 'var(--text-dim)' }}>🔍</span>
          <input
            ref={inputRef}
            type="text"
            placeholder="Type a command, tab, or search live leads..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: '#fff',
              fontSize: '15px',
            }}
          />
          <kbd
            style={{
              fontSize: '10px',
              color: 'var(--text-dim)',
              background: 'rgba(255, 255, 255, 0.05)',
              padding: '3px 6px',
              borderRadius: '4px',
              border: '1px solid var(--border)',
            }}
          >
            ESC
          </kbd>
        </div>

        {/* Results List */}
        <div
          ref={listRef}
          style={{
            maxHeight: '380px',
            overflowY: 'auto',
            padding: '8px',
          }}
        >
          {items.length === 0 ? (
            <div style={{ padding: '32px 20px', textAlign: 'center', color: 'var(--text-dim)', fontSize: '13px' }}>
              No matching commands or leads found for "{query}"
            </div>
          ) : (
            items.map((item, idx) => {
              const isSelected = idx === selectedIndex;
              return (
                <div
                  key={item.id}
                  onClick={item.perform}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '10px 14px',
                    borderRadius: 'var(--radius-sm)',
                    background: isSelected ? 'rgba(56, 189, 248, 0.12)' : 'transparent',
                    border: `1px solid ${isSelected ? 'rgba(56, 189, 248, 0.3)' : 'transparent'}`,
                    cursor: 'pointer',
                    transition: 'background 0.1s ease',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span style={{ fontSize: '16px' }}>{item.icon}</span>
                    <div>
                      <div
                        style={{
                          fontSize: '13px',
                          fontWeight: isSelected ? 600 : 400,
                          color: isSelected ? '#fff' : 'var(--text)',
                        }}
                      >
                        {item.label}
                      </div>
                      {item.subtitle && (
                        <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '2px' }}>
                          {item.subtitle}
                        </div>
                      )}
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span
                      style={{
                        fontSize: '10px',
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px',
                        color: 'var(--text-dim)',
                        background: 'rgba(255, 255, 255, 0.04)',
                        padding: '2px 6px',
                        borderRadius: '4px',
                      }}
                    >
                      {item.category}
                    </span>
                    {isSelected && (
                      <span style={{ fontSize: '11px', color: 'var(--cyan)' }}>↵</span>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer shortcuts */}
        <div
          style={{
            padding: '10px 18px',
            borderTop: '1px solid var(--border)',
            background: 'rgba(0, 0, 0, 0.25)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '11px',
            color: 'var(--text-dim)',
          }}
        >
          <div style={{ display: 'flex', gap: '14px' }}>
            <span>↑↓ Navigate</span>
            <span>↵ Select</span>
            <span>ESC Close</span>
          </div>
          <div>
            <span>LeadOps Omnibar</span>
          </div>
        </div>
      </div>
    </div>
  );
}
