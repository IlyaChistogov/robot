import React, { useState, useEffect, useRef } from 'react';
import { Gamepad2, ArrowUp, ArrowDown, ArrowLeft, ArrowRight, StopCircle } from 'lucide-react';
import { useRobot } from '../../core/RobotContext';

export const ControlsWidget = () => {
  const { drive, triggerEmergencyStop } = useRobot();
  const [speedMultiplier, setSpeedMultiplier] = useState(0.6); // 60% по умолчанию
  const [activeKeys, setActiveKeys] = useState({});

  // Обработка клавиш клавиатуры (W, A, S, D, Пробел)
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (['w', 'a', 's', 'd', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', ' '].includes(e.key)) {
        e.preventDefault();
      }

      if (e.key === ' ') {
        triggerEmergencyStop();
        return;
      }

      setActiveKeys((prev) => ({ ...prev, [e.key.toLowerCase()]: true }));
    };

    const handleKeyUp = (e) => {
      setActiveKeys((prev) => {
        const next = { ...prev };
        delete next[e.key.toLowerCase()];
        return next;
      });
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, [triggerEmergencyStop]);

  // Периодическая отправка команд от клавиатуры
  useEffect(() => {
    const interval = setInterval(() => {
      let linear = 0.0;
      let angular = 0.0;

      const isW = activeKeys['w'] || activeKeys['arrowup'];
      const isS = activeKeys['s'] || activeKeys['arrowdown'];
      const isA = activeKeys['a'] || activeKeys['arrowleft'];
      const isD = activeKeys['d'] || activeKeys['arrowright'];

      if (isW && !isS) linear = 1.0 * speedMultiplier;
      if (isS && !isW) linear = -0.7 * speedMultiplier;
      if (isA && !isD) angular = 1.5 * speedMultiplier;
      if (isD && !isA) angular = -1.5 * speedMultiplier;

      if (linear !== 0 || angular !== 0) {
        drive(linear, angular);
      }
    }, 50);

    return () => clearInterval(interval);
  }, [activeKeys, speedMultiplier, drive]);

  // Сенсорное управление кнопками
  const sendStep = (lin, ang) => {
    drive(lin * speedMultiplier, ang * speedMultiplier);
  };

  const isBtnActive = (k) => activeKeys[k.toLowerCase()];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>
      {/* Клавиши пульта */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 56px)', gap: '8px', justifyContent: 'center' }}>
        <div />
        <button
          onMouseDown={() => sendStep(1.0, 0.0)}
          style={{
            ...btnStyle,
            backgroundColor: isBtnActive('w') ? 'var(--accent-cyan)' : 'var(--bg-secondary)',
            color: isBtnActive('w') ? '#000' : 'var(--text-primary)'
          }}
        >
          <ArrowUp size={22} />
        </button>
        <div />

        <button
          onMouseDown={() => sendStep(0.0, 1.5)}
          style={{
            ...btnStyle,
            backgroundColor: isBtnActive('a') ? 'var(--accent-cyan)' : 'var(--bg-secondary)',
            color: isBtnActive('a') ? '#000' : 'var(--text-primary)'
          }}
        >
          <ArrowLeft size={22} />
        </button>

        <button
          onClick={() => drive(0.0, 0.0)}
          style={{ ...btnStyle, backgroundColor: '#21262d', color: 'var(--accent-red)' }}
          title="Стоп"
        >
          <StopCircle size={22} />
        </button>

        <button
          onMouseDown={() => sendStep(0.0, -1.5)}
          style={{
            ...btnStyle,
            backgroundColor: isBtnActive('d') ? 'var(--accent-cyan)' : 'var(--bg-secondary)',
            color: isBtnActive('d') ? '#000' : 'var(--text-primary)'
          }}
        >
          <ArrowRight size={22} />
        </button>

        <div />
        <button
          onMouseDown={() => sendStep(-0.7, 0.0)}
          style={{
            ...btnStyle,
            backgroundColor: isBtnActive('s') ? 'var(--accent-cyan)' : 'var(--bg-secondary)',
            color: isBtnActive('s') ? '#000' : 'var(--text-primary)'
          }}
        >
          <ArrowDown size={22} />
        </button>
        <div />
      </div>

      <div style={{ fontSize: '11px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
        Управление: клавиши [W, A, S, D] или стрелки
      </div>

      {/* Ограничитель скорости (ШИМ) */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px' }}>
        <span>Мощность:</span>
        {[0.3, 0.6, 1.0].map((val) => (
          <button
            key={val}
            onClick={() => setSpeedMultiplier(val)}
            style={{
              padding: '4px 10px',
              borderRadius: '6px',
              border: '1px solid var(--border-color)',
              background: speedMultiplier === val ? 'var(--accent-cyan)' : 'var(--bg-secondary)',
              color: speedMultiplier === val ? '#000' : 'var(--text-primary)',
              cursor: 'pointer',
              fontFamily: 'var(--font-mono)',
              fontWeight: 600
            }}
          >
            {Math.round(val * 100)}%
          </button>
        ))}
      </div>
    </div>
  );
};

const btnStyle = {
  width: '56px',
  height: '56px',
  borderRadius: '10px',
  border: '1px solid var(--border-color)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  cursor: 'pointer',
  userSelect: 'none',
  transition: 'all 0.1s'
};

export const ControlsPlugin = {
  id: 'controls',
  name: 'Управление движением (WASD)',
  icon: Gamepad2,
  colSpan: 1,
  component: ControlsWidget
};
