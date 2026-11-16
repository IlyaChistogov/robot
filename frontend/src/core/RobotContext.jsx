import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';

const RobotContext = createContext(null);

export const RobotProvider = ({ children }) => {
  const [telemetry, setTelemetry] = useState({
    battery: { voltage: 12.6, percentage: 95.0, current_amps: 1.5, is_low: false },
    motors: { left_pwm: 0, right_pwm: 0, left_current_amps: 0, right_current_amps: 0, left_encoder_ticks: 0, right_encoder_ticks: 0, driver_temperature_c: 25 },
    imu: { roll: 0, pitch: 0, yaw: 0, gyro_z: 0, accel_x: 0, accel_y: 0 },
    pose: { x: 0, y: 0, yaw: 0, linear_velocity: 0, angular_velocity: 0 },
    lidar: { ranges: new Array(360).fill(5.0), angle_min: 0, angle_max: 6.28, range_min: 0.15, range_max: 12.0 },
    ultrasonic: { front_center_m: 2.0, front_left_m: 2.0, front_right_m: 2.0 },
    status: { mode: 'connecting', emergency_stop: false, motors_enabled: true, connection_alive: false }
  });

  const [isConnected, setIsConnected] = useState(false);
  const [activePluginIds, setActivePluginIds] = useState([
    'camera',
    'lidar',
    'controls',
    'battery',
    'imu',
    'relays',
    'student-demo'
  ]);

  const lastCommandTime = useRef(0);

  // Подключение к потоку телеметрии Server-Sent Events
  useEffect(() => {
    let eventSource = null;
    let reconnectTimer = null;

    const connect = () => {
      try {
        eventSource = new EventSource('/api/stream');

        eventSource.onopen = () => {
          setIsConnected(true);
        };

        eventSource.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            setTelemetry(data);
            setIsConnected(true);
          } catch (e) {
            console.error('Ошибка парсинга телеметрии:', e);
          }
        };

        eventSource.onerror = () => {
          setIsConnected(false);
          eventSource.close();
          // Переподключение через 2 секунды
          reconnectTimer = setTimeout(connect, 2000);
        };
      } catch (err) {
        setIsConnected(false);
        reconnectTimer = setTimeout(connect, 2000);
      }
    };

    connect();

    return () => {
      if (eventSource) eventSource.close();
      if (reconnectTimer) clearTimeout(reconnectTimer);
    };
  }, []);

  // Отправка команд движения (с троттлингом ~20 Гц)
  const drive = useCallback(async (linear, angular) => {
    const now = Date.now();
    if (now - lastCommandTime.current < 45) return; // Троттлинг
    lastCommandTime.current = now;

    try {
      await fetch('/api/drive', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ linear, angular })
      });
    } catch (e) {
      console.warn('Ошибка отправки команды движения:', e);
    }
  }, []);

  // Экстренный стоп
  const triggerEmergencyStop = useCallback(async () => {
    try {
      await fetch('/api/stop', { method: 'POST' });
    } catch (e) {
      console.error('Ошибка E-Stop:', e);
    }
  }, []);

  // Сброс экстренного стопа
  const resetEmergencyStop = useCallback(async () => {
    try {
      await fetch('/api/reset_stop', { method: 'POST' });
    } catch (e) {
      console.error('Ошибка сброса E-Stop:', e);
    }
  }, []);

  // Универсальный метод для студенческих плагинов (отправка команд на любой эндпоинт)
  const sendCustomCommand = useCallback(async (endpoint, payload = {}) => {
    try {
      const resp = await fetch(endpoint.startsWith('/') ? endpoint : `/api/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      return await resp.json();
    } catch (e) {
      console.error(`Ошибка выполнения команды ${endpoint}:`, e);
      return { success: false, error: e.message };
    }
  }, []);

  const togglePlugin = useCallback((id) => {
    setActivePluginIds((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]
    );
  }, []);

  return (
    <RobotContext.Provider
      value={{
        telemetry,
        isConnected,
        drive,
        triggerEmergencyStop,
        resetEmergencyStop,
        sendCustomCommand,
        activePluginIds,
        togglePlugin
      }}
    >
      {children}
    </RobotContext.Provider>
  );
};

export const useRobot = () => {
  const context = useContext(RobotContext);
  if (!context) {
    throw new Error('useRobot должен использоваться внутри RobotProvider');
  }
  return context;
};
