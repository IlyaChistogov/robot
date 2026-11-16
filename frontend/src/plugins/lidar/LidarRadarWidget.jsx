import React, { useRef, useEffect, useState } from 'react';
import { Radio } from 'lucide-react';
import { useRobot } from '../../core/RobotContext';

export const LidarRadarWidget = () => {
  const { telemetry } = useRobot();
  const canvasRef = useRef(null);
  const [scaleDistance, setScaleDistance] = useState(6.0); // Масштаб радара (метры)

  const lidar = telemetry.lidar || { ranges: [] };
  const frontDist = lidar.ranges ? lidar.ranges[0] : 0;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    const centerX = width / 2;
    const centerY = height / 2;
    const maxRadius = Math.min(centerX, centerY) - 15;

    // Очистка
    ctx.clearRect(0, 0, width, height);

    // Рисуем круговую сетку дальности (1м, 2м, 3м...)
    ctx.strokeStyle = '#30363d';
    ctx.lineWidth = 1;

    const rings = [1.0, 2.0, 4.0, 6.0];
    rings.forEach((r) => {
      if (r <= scaleDistance) {
        const radiusPx = (r / scaleDistance) * maxRadius;
        ctx.beginPath();
        ctx.arc(centerX, centerY, radiusPx, 0, 2 * Math.PI);
        ctx.stroke();

        ctx.fillStyle = '#8b949e';
        ctx.font = '10px JetBrains Mono';
        ctx.fillText(`${r}м`, centerX + 4, centerY - radiusPx + 10);
      }
    });

    // Оси креста (0°, 90°, 180°, 270°)
    ctx.beginPath();
    ctx.moveTo(centerX, centerY - maxRadius);
    ctx.lineTo(centerX, centerY + maxRadius);
    ctx.moveTo(centerX - maxRadius, centerY);
    ctx.lineTo(centerX + maxRadius, centerY);
    ctx.stroke();

    // Силуэт робота по центру
    ctx.fillStyle = '#58a6ff';
    ctx.beginPath();
    ctx.arc(centerX, centerY, 6, 0, 2 * Math.PI);
    ctx.fill();

    // Стрелка курса робота
    ctx.strokeStyle = '#58a6ff';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(centerX, centerY);
    ctx.lineTo(centerX, centerY - 16);
    ctx.stroke();

    // Отрисовка 360 лучей RPLIDAR A1M8
    if (lidar.ranges && lidar.ranges.length > 0) {
      const numPoints = lidar.ranges.length;
      for (let i = 0; i < numPoints; i++) {
        const dist = lidar.ranges[i];
        if (dist < 0.15 || dist > 12.0) continue; // Отсекаем шум

        const angleRad = (i * 2 * Math.PI) / numPoints - Math.PI / 2; // 0 градусов строго сверху
        const distPx = (dist / scaleDistance) * maxRadius;

        if (distPx <= maxRadius) {
          const px = centerX + distPx * Math.cos(angleRad);
          const py = centerY + distPx * Math.sin(angleRad);

          // Цвет точки зависит от близости к роботу
          if (dist < 0.5) {
            ctx.fillStyle = '#f85149'; // Опасно близко (<0.5м)
          } else if (dist < 1.2) {
            ctx.fillStyle = '#d29922'; // Предупреждение
          } else {
            ctx.fillStyle = '#3fb950'; // Норма
          }

          ctx.beginPath();
          ctx.arc(px, py, 2.5, 0, 2 * Math.PI);
          ctx.fill();
        }
      }
    }
  }, [lidar, scaleDistance]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
      <div style={{ position: 'relative' }}>
        <canvas
          ref={canvasRef}
          width={300}
          height={300}
          style={{ backgroundColor: '#0d1117', borderRadius: '50%', border: '1px solid var(--border-color)' }}
        />
        {/* Метка дистанции прямо */}
        <div
          style={{
            position: 'absolute',
            bottom: '10px',
            left: '50%',
            transform: 'translateX(-50%)',
            backgroundColor: 'rgba(22, 27, 34, 0.85)',
            border: '1px solid var(--border-color)',
            padding: '3px 10px',
            borderRadius: '12px',
            fontSize: '11px',
            fontFamily: 'var(--font-mono)',
            whiteSpace: 'nowrap'
          }}
        >
          ВПЕРЕДИ: <strong style={{ color: frontDist < 0.6 ? '#f85149' : '#3fb950' }}>{frontDist ? frontDist.toFixed(2) : '--'} м</strong>
        </div>
      </div>

      {/* Переключатель масштаба */}
      <div style={{ display: 'flex', gap: '8px', fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
        <span>Масштаб:</span>
        {[3.0, 6.0, 10.0].map((m) => (
          <button
            key={m}
            onClick={() => setScaleDistance(m)}
            style={{
              background: scaleDistance === m ? 'var(--accent-cyan)' : 'var(--bg-secondary)',
              color: scaleDistance === m ? '#000' : 'var(--text-secondary)',
              border: '1px solid var(--border-color)',
              padding: '2px 6px',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            {m}м
          </button>
        ))}
      </div>
    </div>
  );
};

export const LidarPlugin = {
  id: 'lidar',
  name: 'Лидар RPLIDAR A1',
  icon: Radio,
  colSpan: 1,
  component: LidarRadarWidget
};
