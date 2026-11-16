import React from 'react';
import { Compass, Navigation } from 'lucide-react';
import { useRobot } from '../../core/RobotContext';

export const ImuCompassWidget = () => {
  const { telemetry } = useRobot();
  const imu = telemetry.imu || { yaw: 0, pitch: 0, roll: 0, gyro_z: 0 };
  const pose = telemetry.pose || { x: 0, y: 0 };

  const yawDeg = Math.round((imu.yaw * 180) / Math.PI);
  const pitchDeg = Math.round((imu.pitch * 180) / Math.PI);
  const rollDeg = Math.round((imu.roll * 180) / Math.PI);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '14px', fontFamily: 'var(--font-mono)' }}>
      {/* Компас курса */}
      <div style={{ position: 'relative', width: '120px', height: '120px' }}>
        <div
          style={{
            width: '100%',
            height: '100%',
            borderRadius: '50%',
            border: '2px solid var(--border-color)',
            backgroundColor: 'var(--bg-secondary)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            position: 'relative'
          }}
        >
          <span style={{ position: 'absolute', top: '4px', fontSize: '10px', color: 'var(--accent-red)', fontWeight: 700 }}>N</span>
          <span style={{ position: 'absolute', right: '6px', fontSize: '10px', color: 'var(--text-secondary)' }}>E</span>
          <span style={{ position: 'absolute', bottom: '4px', fontSize: '10px', color: 'var(--text-secondary)' }}>S</span>
          <span style={{ position: 'absolute', left: '6px', fontSize: '10px', color: 'var(--text-secondary)' }}>W</span>

          {/* Стрелка компаса */}
          <div
            style={{
              transform: `rotate(${yawDeg}deg)`,
              transition: 'transform 0.1s linear',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center'
            }}
          >
            <Navigation size={38} color="var(--accent-cyan)" fill="var(--accent-cyan)" />
          </div>
        </div>
      </div>

      {/* Углы наклона и одометрия */}
      <div style={{ width: '100%', display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', textAlign: 'center', fontSize: '12px' }}>
        <div style={{ backgroundColor: 'var(--bg-secondary)', padding: '6px', borderRadius: '6px' }}>
          <div style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>КУРС (YAW)</div>
          <strong>{yawDeg}°</strong>
        </div>
        <div style={{ backgroundColor: 'var(--bg-secondary)', padding: '6px', borderRadius: '6px' }}>
          <div style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>ТАНГАЖ</div>
          <strong>{pitchDeg}°</strong>
        </div>
        <div style={{ backgroundColor: 'var(--bg-secondary)', padding: '6px', borderRadius: '6px' }}>
          <div style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>КРЕН</div>
          <strong>{rollDeg}°</strong>
        </div>
      </div>

      <div style={{ fontSize: '11px', color: 'var(--text-secondary)', textAlign: 'center' }}>
        Одометрия: X = {pose.x?.toFixed(2)} м, Y = {pose.y?.toFixed(2)} м
      </div>
    </div>
  );
};

export const ImuPlugin = {
  id: 'imu',
  name: 'Ориентация (IMU / Компас)',
  icon: Compass,
  colSpan: 1,
  component: ImuCompassWidget
};
