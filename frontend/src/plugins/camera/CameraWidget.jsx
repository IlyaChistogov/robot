import React, { useState } from 'react';
import { Video, Maximize2, AlertCircle } from 'lucide-react';
import { useRobot } from '../../core/RobotContext';

export const CameraWidget = () => {
  const { isConnected, telemetry } = useRobot();
  const [streamError, setStreamError] = useState(false);

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', minHeight: '260px', backgroundColor: '#000', borderRadius: '8px', overflow: 'hidden' }}>
      {/* MJPEG Видеопоток с курсовой камеры */}
      {isConnected && !streamError ? (
        <img
          src="/video_feed"
          alt="Поток с камеры робота"
          onError={() => setStreamError(true)}
          style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }}
        />
      ) : (
        <div
          style={{
            height: '260px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--text-secondary)',
            gap: '8px'
          }}
        >
          <AlertCircle size={32} color="var(--accent-yellow)" />
          <span>{isConnected ? 'Ожидание видеопотока...' : 'Сервер робота не подключен'}</span>
          <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)' }}>Эндпоинт: /video_feed</span>
        </div>
      )}

      {/* Оверлей прицела */}
      <div
        style={{
          position: 'absolute',
          top: '10px',
          right: '10px',
          backgroundColor: 'rgba(0,0,0,0.6)',
          padding: '4px 8px',
          borderRadius: '4px',
          fontSize: '11px',
          fontFamily: 'var(--font-mono)',
          color: '#00ffcc'
        }}
      >
        RPLIDAR CAM • 15 FPS
      </div>
    </div>
  );
};

export const CameraPlugin = {
  id: 'camera',
  name: 'Курсовая камера',
  icon: Video,
  colSpan: 2,
  component: CameraWidget
};
