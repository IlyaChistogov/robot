import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Gamepad2, ArrowUp, ArrowDown, ArrowLeft, ArrowRight, StopCircle, AlertOctagon, RotateCcw } from 'lucide-react';
import { useRobot } from '../../core/RobotContext';

export const ControlsWidget = () => {
  const { drive, triggerEmergencyStop, resetEmergencyStop, telemetry, isConnected } = useRobot();
  const [speedMultiplier, setSpeedMultiplier] = useState(0.6); // 60% по умолчанию
  const [activeDirection, setActiveDirection] = useState({ up: false, down: false, left: false, right: false });
  const isMoving = useRef(false);

  const isEStop = Boolean(telemetry?.status?.emergency_stop);

  // Универсальный маппинг клавиш (ENG + RUS + KeyCode + Стрелки)
  const mapKeyToDir = (e) => {
    const k = e.key ? e.key.toLowerCase() : '';
    const code = e.code || '';

    if (code === 'KeyW' || k === 'w' || k === 'ц' || code === 'ArrowUp' || k === 'arrowup') return 'up';
    if (code === 'KeyS' || k === 's' || k === 'ы' || code === 'ArrowDown' || k === 'arrowdown') return 'down';
    if (code === 'KeyA' || k === 'a' || k === 'ф' || code === 'ArrowLeft' || k === 'arrowleft') return 'left';
    if (code === 'KeyD' || k === 'd' || k === 'в' || code === 'ArrowRight' || k === 'arrowright') return 'right';
    return null;
  };

  // Обработка клавиатуры
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Игнорируем ввод, если фокус в текстовом поле
      if (['INPUT', 'TEXTAREA'].includes(e.target.tagName)) return;

      const dir = mapKeyToDir(e);
      if (dir) {
        e.preventDefault();
        setActiveDirection((prev) => (prev[dir] ? prev : { ...prev, [dir]: true }));
        return;
      }

      // Пробел или E — экстренный стоп
      if (e.key === ' ' || e.code === 'Space' || e.code === 'KeyE' || e.key.toLowerCase() === 'e' || e.key.toLowerCase() === 'у') {
        e.preventDefault();
        triggerEmergencyStop();
        return;
      }

      // R — сброс блокировки
      if (e.code === 'KeyR' || e.key.toLowerCase() === 'r' || e.key.toLowerCase() === 'к') {
        e.preventDefault();
        resetEmergencyStop();
        return;
      }
    };

    const handleKeyUp = (e) => {
      if (['INPUT', 'TEXTAREA'].includes(e.target.tagName)) return;
      const dir = mapKeyToDir(e);
      if (dir) {
        setActiveDirection((prev) => ({ ...prev, [dir]: false }));
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, [triggerEmergencyStop, resetEmergencyStop]);

  // Периодический цикл отправки скоростей (20 Гц)
  useEffect(() => {
    const interval = setInterval(() => {
      if (isEStop) {
        isMoving.current = false;
        return;
      }

      let linear = 0.0;
      let angular = 0.0;

      if (activeDirection.up && !activeDirection.down) linear = 1.0 * speedMultiplier;
      if (activeDirection.down && !activeDirection.up) linear = -0.7 * speedMultiplier;
      if (activeDirection.left && !activeDirection.right) angular = 1.6 * speedMultiplier;
      if (activeDirection.right && !activeDirection.left) angular = -1.6 * speedMultiplier;

      if (linear !== 0 || angular !== 0) {
        isMoving.current = true;
        drive(linear, angular);
      } else if (isMoving.current) {
        // Остановка при отпускании всех кнопок
        isMoving.current = false;
        drive(0.0, 0.0);
      }
    }, 50);

    return () => clearInterval(interval);
  }, [activeDirection, speedMultiplier, drive, isEStop]);

  // Управление с экранных кнопок (мышь и тачскрин с удержанием)
  const startHold = (dir) => {
    setActiveDirection((prev) => ({ ...prev, [dir]: true }));
  };

  const endHold = (dir) => {
    setActiveDirection((prev) => ({ ...prev, [dir]: false }));
  };

  const handleStopClick = () => {
    setActiveDirection({ up: false, down: false, left: false, right: false });
    drive(0.0, 0.0);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '14px', width: '100%' }}>
      {/* Баннер аварийной блокировки */}
      {isEStop && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '8px',
            width: '100%',
            padding: '8px 12px',
            borderRadius: '8px',
            backgroundColor: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid var(--accent-red)',
            color: 'var(--accent-red)',
            fontSize: '12px'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600 }}>
            <AlertOctagon size={16} />
            <span>АКТИВЕН E-STOP (МОТОРЫ ЗАБЛОКИРОВАНЫ)</span>
          </div>
          <button
            onClick={resetEmergencyStop}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              backgroundColor: 'var(--accent-green)',
              color: '#fff',
              border: 'none',
              padding: '4px 10px',
              borderRadius: '6px',
              fontSize: '11px',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            <RotateCcw size={12} />
            Снять
          </button>
        </div>
      )}

      {/* Клавиши пульта */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 56px)', gap: '8px', justifyContent: 'center' }}>
        <div />
        <button
          onMouseDown={() => startHold('up')}
          onMouseUp={() => endHold('up')}
          onMouseLeave={() => endHold('up')}
          onTouchStart={(e) => { e.preventDefault(); startHold('up'); }}
          onTouchEnd={(e) => { e.preventDefault(); endHold('up'); }}
          style={{
            ...btnStyle,
            backgroundColor: activeDirection.up ? 'var(--accent-cyan)' : 'var(--bg-secondary)',
            color: activeDirection.up ? '#000' : 'var(--text-primary)'
          }}
          title="Вперед (W / ↑)"
        >
          <ArrowUp size={22} />
        </button>
        <div />

        <button
          onMouseDown={() => startHold('left')}
          onMouseUp={() => endHold('left')}
          onMouseLeave={() => endHold('left')}
          onTouchStart={(e) => { e.preventDefault(); startHold('left'); }}
          onTouchEnd={(e) => { e.preventDefault(); endHold('left'); }}
          style={{
            ...btnStyle,
            backgroundColor: activeDirection.left ? 'var(--accent-cyan)' : 'var(--bg-secondary)',
            color: activeDirection.left ? '#000' : 'var(--text-primary)'
          }}
          title="Влево (A / ←)"
        >
          <ArrowLeft size={22} />
        </button>

        <button
          onClick={handleStopClick}
          style={{ ...btnStyle, backgroundColor: '#21262d', color: 'var(--accent-red)' }}
          title="Стоп (Пробел)"
        >
          <StopCircle size={22} />
        </button>

        <button
          onMouseDown={() => startHold('right')}
          onMouseUp={() => endHold('right')}
          onMouseLeave={() => endHold('right')}
          onTouchStart={(e) => { e.preventDefault(); startHold('right'); }}
          onTouchEnd={(e) => { e.preventDefault(); endHold('right'); }}
          style={{
            ...btnStyle,
            backgroundColor: activeDirection.right ? 'var(--accent-cyan)' : 'var(--bg-secondary)',
            color: activeDirection.right ? '#000' : 'var(--text-primary)'
          }}
          title="Вправо (D / →)"
        >
          <ArrowRight size={22} />
        </button>

        <div />
        <button
          onMouseDown={() => startHold('down')}
          onMouseUp={() => endHold('down')}
          onMouseLeave={() => endHold('down')}
          onTouchStart={(e) => { e.preventDefault(); startHold('down'); }}
          onTouchEnd={(e) => { e.preventDefault(); endHold('down'); }}
          style={{
            ...btnStyle,
            backgroundColor: activeDirection.down ? 'var(--accent-cyan)' : 'var(--bg-secondary)',
            color: activeDirection.down ? '#000' : 'var(--text-primary)'
          }}
          title="Назад (S / ↓)"
        >
          <ArrowDown size={22} />
        </button>
        <div />
      </div>

      <div style={{ fontSize: '11px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', textAlign: 'center' }}>
        Клавиши: [W, A, S, D] (RUS/ENG) или стрелки | Пробел: E-Stop | R: Сброс
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
