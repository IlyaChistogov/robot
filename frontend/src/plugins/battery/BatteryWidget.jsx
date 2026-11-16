import React from 'react';
import { BatteryCharging, Cpu, Thermometer, Gauge } from 'lucide-react';
import { useRobot } from '../../core/RobotContext';

export const BatteryWidget = () => {
  const { telemetry } = useRobot();
  const bat = telemetry.battery || { voltage: 12.6, percentage: 95, current_amps: 1.5, is_low: false };
  const motors = telemetry.motors || { left_pwm: 0, right_pwm: 0, driver_temperature_c: 25 };

  const getVoltageColor = (v) => {
    if (v < 11.2) return 'var(--accent-red)';
    if (v < 12.0) return 'var(--accent-yellow)';
    return 'var(--accent-green)';
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', fontFamily: 'var(--font-mono)' }}>
      {/* Свинцовый аккумулятор 12В */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', fontSize: '13px' }}>
          <span style={{ color: 'var(--text-secondary)' }}>АКБ 12В (Pb-Acid):</span>
          <strong style={{ color: getVoltageColor(bat.voltage) }}>
            {bat.voltage?.toFixed(2)} В ({bat.percentage?.toFixed(1)}%)
          </strong>
        </div>
        {/* Прогресс-бар заряда */}
        <div style={{ width: '100%', height: '8px', backgroundColor: 'var(--bg-secondary)', borderRadius: '4px', overflow: 'hidden' }}>
          <div
            style={{
              width: `${Math.min(100, Math.max(0, bat.percentage))}%`,
              height: '100%',
              backgroundColor: getVoltageColor(bat.voltage),
              transition: 'width 0.3s ease'
            }}
          />
        </div>
      </div>

      {/* Ток и мощность */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
        <div style={{ backgroundColor: 'var(--bg-secondary)', padding: '10px', borderRadius: '8px' }}>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>ТОК СИСТЕМЫ</div>
          <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--accent-cyan)' }}>
            {bat.current_amps?.toFixed(2)} А
          </div>
          <div style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>
            {(bat.voltage * bat.current_amps)?.toFixed(1)} Вт
          </div>
        </div>

        <div style={{ backgroundColor: 'var(--bg-secondary)', padding: '10px', borderRadius: '8px' }}>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>VNH2SP30 ТЕМП.</div>
          <div style={{ fontSize: '18px', fontWeight: 700, color: motors.driver_temperature_c > 65 ? 'var(--accent-red)' : '#f0f6fc' }}>
            {motors.driver_temperature_c?.toFixed(1)} °C
          </div>
          <div style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>H-мост драйвера</div>
        </div>
      </div>

      {/* Мониторинг ШИМ моторов VNH2SP30 */}
      <div style={{ fontSize: '12px' }}>
        <div style={{ color: 'var(--text-secondary)', marginBottom: '4px' }}>ШИМ МОТОРОВ:</div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>ЛЕВЫЙ: <strong>{motors.left_pwm}</strong></span>
          <span>ПРАВЫЙ: <strong>{motors.right_pwm}</strong></span>
        </div>
      </div>
    </div>
  );
};

export const BatteryPlugin = {
  id: 'battery',
  name: 'Питание и драйвер VNH2SP30',
  icon: BatteryCharging,
  colSpan: 1,
  component: BatteryWidget
};
