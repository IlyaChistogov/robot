import React, { useState } from 'react';
import { Video, Grid, AlertCircle, RefreshCw } from 'lucide-react';
import { useRobot } from '../../core/RobotContext';

export const CameraWidget = () => {
  const { isConnected } = useRobot();
  const [selectedCam, setSelectedCam] = useState('0'); // '0', '2', '4', '6' или 'grid'
  const [streamKey, setStreamKey] = useState(Date.now());
  const [streamError, setStreamError] = useState(false);

  const cameras = [
    { id: '0', label: '1. Передняя' },
    { id: '2', label: '2. Правая' },
    { id: '4', label: '3. Левая' },
    { id: '6', label: '4. Задняя' },
    { id: 'grid', label: 'Сетка 2×2' }
  ];

  const handleSelectCam = (camId) => {
    setSelectedCam(camId);
    setStreamError(false);
    setStreamKey(Date.now());
  };

  const streamUrl = `/video_feed?cam=${selectedCam}&_t=${streamKey}`;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', width: '100%', height: '100%' }}>
      {/* Селектор камер кругового обзора */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
        {cameras.map((c) => (
          <button
            key={c.id}
            onClick={() => handleSelectCam(c.id)}
            style={{
              padding: '4px 10px',
              borderRadius: '6px',
              fontSize: '11px',
              fontFamily: 'var(--font-mono)',
              fontWeight: 600,
              cursor: 'pointer',
              border: '1px solid var(--border-color)',
              backgroundColor: selectedCam === c.id ? 'var(--accent-cyan)' : 'var(--bg-secondary)',
              color: selectedCam === c.id ? '#000' : 'var(--text-primary)',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              transition: 'all 0.15s'
            }}
          >
            {c.id === 'grid' && <Grid size={12} />}
            <span>{c.label}</span>
          </button>
        ))}

        <button
          onClick={() => { setStreamError(false); setStreamKey(Date.now()); }}
          style={{
            marginLeft: 'auto',
            padding: '4px 8px',
            borderRadius: '6px',
            fontSize: '11px',
            border: '1px solid var(--border-color)',
            backgroundColor: 'var(--bg-secondary)',
            color: 'var(--text-secondary)',
            cursor: 'pointer'
          }}
          title="Переподключить видеопоток"
        >
          <RefreshCw size={12} />
        </button>
      </div>

      {/* Окно видеопотока */}
      <div
        style={{
          position: 'relative',
          width: '100%',
          minHeight: '260px',
          backgroundColor: '#000',
          borderRadius: '8px',
          overflow: 'hidden',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}
      >
        {isConnected && !streamError ? (
          <img
            src={streamUrl}
            alt="Видеопоток"
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
            <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)' }}>Эндпоинт: {streamUrl}</span>
          </div>
        )}

        {/* Бейдж выбранной камеры */}
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
          {selectedCam === 'grid' ? 'QUAD VIEW (4 CAM)' : `CAM /dev/video${selectedCam}`}
        </div>
      </div>
    </div>
  );
};

export const CameraPlugin = {
  id: 'camera',
  name: 'Круговой обзор (4 камеры)',
  icon: Video,
  colSpan: 2,
  component: CameraWidget
};
