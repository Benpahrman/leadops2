import React from 'react';

export default function TablePagination({
  currentPage,
  pageSize,
  totalRows,
  totalPages,
  setCurrentPage,
}) {
  const startIdx = totalRows === 0 ? 0 : (currentPage - 1) * pageSize + 1;
  const endIdx = Math.min(currentPage * pageSize, totalRows);

  return (
    <div className="pagination-bar">
      <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontFamily: 'var(--mono)' }}>
        Showing <b>{startIdx}–{endIdx}</b> of <b>{totalRows}</b> verified filings
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <button
          className="pagination-btn"
          onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
          disabled={currentPage === 1}
        >
          ← Prev
        </button>
        <span style={{ fontSize: '12px', color: '#fff', padding: '0 6px', fontFamily: 'var(--mono)' }}>
          {currentPage} / {totalPages}
        </span>
        <button
          className="pagination-btn"
          onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
          disabled={currentPage === totalPages}
        >
          Next →
        </button>
      </div>
    </div>
  );
}
