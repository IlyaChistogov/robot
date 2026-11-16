import React, { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

export const WidgetCard = ({ title, icon: Icon, badge, children, colSpan = 1, minHeight }) => {
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <div
      style={{
        gridColumn: `span ${colSpan}`,
        backgroundColor: 'var(--bg-card)',
        border: '1px solid var(--border-color)',
        borderRadius: '12px',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
        transition: 'border-color 0.2s'
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 16px',
          borderBottom: isCollapsed ? 'none' : '1px solid var(--border-color)',
          backgroundColor: 'var(--bg-secondary)',
          userSelect: 'none'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {Icon && <Icon size={18} color="var(--accent-cyan)" />}
          <span style={{ fontWeight: 600, fontSize: '14px', letterSpacing: '0.5px' }}>{title}</span>
          {badge && (
            <span
              style={{
                fontSize: '11px',
                padding: '2px 8px',
                borderRadius: '10px',
                backgroundColor: 'rgba(88, 166, 255, 0.15)',
                color: 'var(--accent-cyan)',
                fontFamily: 'var(--font-mono)'
              }}
            >
              {badge}
            </span>
          )}
        </div>
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center'
          }}
        >
          {isCollapsed ? <ChevronDown size={18} /> : <ChevronUp size={18} />}
        </button>
      </div>

      {!isCollapsed && (
        <div
          style={{
            padding: '16px',
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            minHeight: minHeight || 'auto'
          }}
        >
          {children}
        </div>
      )}
    </div>
  );
};
