import React, { useState } from 'react';
import { ToggleLeft, ToggleRight, Power } from 'lucide-react';
import { useRobot } from '../../core/RobotContext';

export const RelaysWidget = () => {
  const { sendCustomCommand } = useRobot();
  const [relays, setRelays] = useState({
    1: { name: 'Питание лидара', state: true },
    2: { name: 'Головной свет', state: false },
    3: { name: 'Звуковой сигнал', state: false },
    4: { name: 'Доп. датчики', state: true },
    5: { name: 'Реле 5 (AUX)', state: false },
    6: { name: 'Реле 6 (AUX)', state: false }
  });

  const toggleRelay = async (id) => {
    const nextState = !relays[id].state;
    setRelays((prev) => ({
      ...prev,
      [id]: { ...prev[id], state: nextState }
    }));

    // Отправляем команду на бэкенд через универсальный метод
    await sendCustomCommand('/api/relay', { relay_id: id, state: nextState });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
        Блок силовых реле (8 каналов):
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
        {Object.entries(relays).map(([id, r]) => (
          <button
            key={id}
            onClick={() => toggleRelay(id)}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '8px 10px',
              borderRadius: '6px',
              border: '1px solid var(--border-color)',
              backgroundColor: r.state ? 'rgba(63, 185, 80, 0.15)' : 'var(--bg-secondary)',
              color: r.state ? 'var(--accent-green)' : 'var(--text-secondary)',
              cursor: 'pointer',
              fontSize: '12px',
              fontFamily: 'var(--font-mono)'
            }}
          >
            <span>{r.name}</span>
            {r.state ? <ToggleRight size={18} /> : <ToggleLeft size={18} />}
          </button>
        ))}
      </div>
    </div>
  );
};

export const RelaysPlugin = {
  id: 'relays',
  name: 'Блок реле (Силовая плата)',
  icon: Power,
  colSpan: 1,
  component: RelaysWidget
};
