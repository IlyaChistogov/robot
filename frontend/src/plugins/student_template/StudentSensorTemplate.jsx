import React, { useState } from 'react';
import { Sparkles, Send } from 'lucide-react';
import { useRobot } from '../../core/RobotContext';

/**
 * =====================================================================
 * ШАБЛОН ПЛАГИНА ДЛЯ СТУДЕНТОВ
 * =====================================================================
 * Чтобы создать свой собственный плагин для пульта:
 * 1. Скопируйте этот файл под новым именем (например MySensorWidget.jsx).
 * 2. Напишите свой React-компонент, используя хук useRobot().
 * 3. Экспортируйте объект манифеста плагина внизу файла.
 * 4. Зарегистрируйте плагин в src/plugins/index.js одной строкой!
 */

export const StudentSensorWidget = () => {
  // Получаем доступ ко всем датчикам и командам робота
  const { telemetry, sendCustomCommand } = useRobot();
  const [customInput, setCustomInput] = useState('');
  const [lastResponse, setLastResponse] = useState(null);

  const handleSendToStudentBackend = async () => {
    // Студент может отправить команду в свой бэкенд-эндпоинт
    const res = await sendCustomCommand('/api/student_action', { message: customInput });
    setLastResponse(JSON.stringify(res));
  };

  const us = telemetry.ultrasonic || { front_center_m: 2.0 };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '12px' }}>
      <p style={{ color: 'var(--text-secondary)' }}>
        Пример студенческого плагина. Демонстрирует чтение показаний сонара и отправку кастомной команды:
      </p>

      <div style={{ padding: '8px', backgroundColor: 'var(--bg-secondary)', borderRadius: '6px' }}>
        <strong>УЗ-сонар спереди:</strong>{' '}
        <span style={{ color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)' }}>
          {us.front_center_m ? `${us.front_center_m.toFixed(2)} м` : 'Опрос...'}
        </span>
      </div>

      <div style={{ display: 'flex', gap: '6px' }}>
        <input
          type="text"
          placeholder="Параметр для вашего алгоритма..."
          value={customInput}
          onChange={(e) => setCustomInput(e.target.value)}
          style={{
            flex: 1,
            backgroundColor: 'var(--bg-secondary)',
            border: '1px solid var(--border-color)',
            color: '#fff',
            padding: '6px 10px',
            borderRadius: '6px',
            fontSize: '12px'
          }}
        />
        <button
          onClick={handleSendToStudentBackend}
          style={{
            backgroundColor: 'var(--accent-cyan)',
            color: '#000',
            border: 'none',
            padding: '6px 12px',
            borderRadius: '6px',
            cursor: 'pointer',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '4px'
          }}
        >
          <Send size={14} />
          Тест
        </button>
      </div>

      {lastResponse && (
        <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--accent-green)' }}>
          Ответ: {lastResponse}
        </div>
      )}
    </div>
  );
};

// Экспорт манифеста студенческого плагина
export const StudentTemplatePlugin = {
  id: 'student-demo',
  name: 'Студенческий плагин (Demo)',
  icon: Sparkles,
  colSpan: 1,
  component: StudentSensorWidget
};
