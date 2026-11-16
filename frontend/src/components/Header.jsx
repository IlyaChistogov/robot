import React, { useState } from 'react';
import { useRobot } from '../core/RobotContext';
import { ShieldAlert, Zap, Wifi, WifiOff, Layers, RotateCcw } from 'lucide-react';

export const Header = ({ availablePlugins }) => {
  const { telemetry, isConnected, triggerEmergencyStop, resetEmergencyStop, activePluginIds, togglePlugin } = useRobot();
  const [showPluginMenu, setShowPluginMenu] = useState(false);

  const isStop = telemetry.status?.emergency_stop;
  const bat = telemetry.battery;

  return (
    <header
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 24px',
        backgroundColor: 'var(--bg-secondary)',
        borderBottom: '1px solid var(--border-color)',
        position: 'sticky',
        top: 0,
        zIndex: 100
      }}
    >
      {/* Логотип и статус связи */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              width: '12px',
              height: '12px',
              borderRadius: '50%',
              backgroundColor: isConnected ? 'var(--accent-green)' : 'var(--accent-red)',
              boxShadow: isConnected ? '0 0 10px var(--accent-green)' : '0 0 10px var(--accent-red)'
            }}
          />
          <h1 style={{ fontSize: '18px', fontWeight: 700, letterSpacing: '0.5px' }}>
            ROBOT<span style={{ color: 'var(--accent-cyan)' }}>.CONTROL</span>
          </h1>
        </div>

        <span
          style={{
            fontSize: '12px',
            padding: '3px 8px',
            borderRadius: '6px',
            backgroundColor: 'var(--bg-card)',
            color: 'var(--text-secondary)',
            fontFamily: 'var(--font-mono)'
          }}
        >
          РЕЖИМ: {telemetry.status?.mode?.toUpperCase() || 'MOCK'}
        </span>
      </div>

      {/* Быстрая статистика: АКБ 12В, Ток */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontFamily: 'var(--font-mono)' }}>
          <Zap size={16} color={bat?.is_low ? 'var(--accent-red)' : 'var(--accent-green)'} />
          <span style={{ fontWeight: 600 }}>{bat?.voltage?.toFixed(1)}V</span>
          <span style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>({bat?.percentage?.toFixed(0)}%)</span>
          <span style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>{bat?.current_amps?.toFixed(1)}A</span>
        </div>

        {/* Меню управления плагинами */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => setShowPluginMenu(!showPluginMenu)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: 'var(--bg-card)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border-color)',
              padding: '6px 12px',
              borderRadius: '8px',
              fontSize: '13px',
              cursor: 'pointer'
            }}
          >
            <Layers size={16} color="var(--accent-cyan)" />
            <span>Плагины ({activePluginIds.length})</span>
          </button>

          {showPluginMenu && (
            <div
              style={{
                position: 'absolute',
                top: '40px',
                right: 0,
                width: '260px',
                backgroundColor: 'var(--bg-card)',
                border: '1px solid var(--border-color)',
                borderRadius: '8px',
                padding: '12px',
                boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
                zIndex: 200
              }}
            >
              <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px' }}>
                АКТИВНЫЕ ВИДЖЕТЫ / ПЛАГИНЫ:
              </div>
              {availablePlugins.map((plugin) => (
                <label
                  key={plugin.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '6px 0',
                    fontSize: '13px',
                    cursor: 'pointer'
                  }}
                >
                  <input
                    type="checkbox"
                    checked={activePluginIds.includes(plugin.id)}
                    onChange={() => togglePlugin(plugin.id)}
                  />
                  <span>{plugin.name}</span>
                </label>
              ))}
            </div>
          )}
        </div>

        {/* Кнопка экстренного останова */}
        {isStop ? (
          <button
            onClick={resetEmergencyStop}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              backgroundColor: 'var(--accent-green)',
              color: '#fff',
              border: 'none',
              padding: '8px 16px',
              borderRadius: '8px',
              fontWeight: 700,
              fontSize: '14px',
              cursor: 'pointer',
              boxShadow: '0 0 15px rgba(63, 185, 80, 0.4)'
            }}
          >
            <RotateCcw size={18} />
            СБРОС E-STOP
          </button>
        ) : (
          <button
            onClick={triggerEmergencyStop}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              backgroundColor: 'var(--accent-red)',
              color: '#fff',
              border: 'none',
              padding: '8px 18px',
              borderRadius: '8px',
              fontWeight: 700,
              fontSize: '14px',
              cursor: 'pointer',
              boxShadow: '0 0 15px rgba(248, 81, 73, 0.4)'
            }}
          >
            <ShieldAlert size={18} />
            СТОП (SPACE)
          </button>
        )}
      </div>
    </header>
  );
};
