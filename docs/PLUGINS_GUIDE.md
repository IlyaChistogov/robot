# 🛠️ Руководство по разработке плагинов и добавлению новых датчиков

В данном руководстве подробно описано:
1. **Как писать алгоритмические плагины на Python** (автономная навигация, компьютерное зрение).
2. **Как создавать визуальные плагины для веб-пульта на React** (новые виджеты, графики, кнопки).
3. **Техпроцесс (ТП): сквозное добавление нового датчика в робота** (от схемы подключения до отображения на экране).

---

## 1. Студенческие плагины на Python (Алгоритмы)

Все прикладные алгоритмы студентов размещаются в папке [`plugins/`](file:///c:/Users/ilyac/robot/plugins/).  
Студенту не нужно настраивать COM-порты, потоки или протоколы — вся работа идет через библиотеку `RobotClient`.

### Базовый шаблон студенческого плагина (`plugins/my_algorithm.py`):
```python
import sys
import os
import time

# Подключаем клиентскую библиотеку робота
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
from robot_client import RobotClient

def main():
    # 1. Подключаемся к роботу (к моку или реальному)
    robot = RobotClient("http://localhost:5000")
    print("Подключение к платформе...")

    try:
        status = robot.get_status()
        print(f"Робот готов! Напряжение АКБ: {status['battery']['voltage']} В")

        while True:
            # 2. Считываем данные с датчиков
            telemetry = robot.get_telemetry()
            front_distance = robot.get_front_distance()
            lidar_ranges = robot.get_lidar_ranges() # 360 лучей

            # 3. Прикладная логика студента:
            if front_distance < 0.5:
                print("Препятствие близко! Поворачиваем направо...")
                robot.drive(linear=0.0, angular=-1.0)
            else:
                print("Путь свободен! Едем вперед.")
                robot.drive(linear=0.4, angular=0.0)

            time.sleep(0.1) # Частота цикла 10 Гц

    except KeyboardInterrupt:
        print("\nОстановка алгоритма пользователем.")
    finally:
        robot.stop() # Обязательно останавливаем моторы при выходе

if __name__ == "__main__":
    main()
```

---

## 2. Плагины для веб-пульта оператора на React

Веб-пульт использует реестр плагинов-виджетов. Каждый виджет изолирован и не ломает остальной интерфейс при ошибках.

### Пошаговый процесс создания нового виджета:

#### Шаг 1. Создайте файл виджета
В папке `frontend/src/plugins/` создайте подпапку для вашего плагина, например `gas_sensor/GasSensorWidget.jsx`:

```jsx
import React from 'react';
import { Flame } from 'lucide-react'; // Любая иконка из lucide-react
import { useRobot } from '../../core/RobotContext';

export const GasSensorWidget = () => {
  // Хук useRobot дает доступ к телеметрии и командам
  const { telemetry, sendCustomCommand } = useRobot();

  // Допустим, мы считываем данные нового датчика из телеметрии
  const gasLevel = telemetry.gas_sensor?.ppm || 120;

  const handleVentilation = async () => {
    // Отправка команды на робота
    await sendCustomCommand('/api/relay', { relay_id: 2, state: true });
    alert('Вентиляция включена!');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
      <div style={{ fontSize: '18px', fontWeight: 700, color: gasLevel > 300 ? '#f85149' : '#3fb950' }}>
        Концентрация газа: {gasLevel} PPM
      </div>
      <button
        onClick={handleVentilation}
        style={{
          backgroundColor: '#58a6ff',
          color: '#000',
          border: 'none',
          padding: '8px',
          borderRadius: '6px',
          cursor: 'pointer',
          fontWeight: 600
        }}
      >
        Включить вытяжку (Реле 2)
      </button>
    </div>
  );
};

// Экспорт манифеста плагина
export const GasSensorPlugin = {
  id: 'gas-sensor',             // Уникальный ID плагина
  name: 'Датчик утечки газа',   // Название карточки на экране
  icon: Flame,                  // Иконка
  colSpan: 1,                   // Ширина: 1 или 2 колонки
  component: GasSensorWidget    // Сам React-компонент
};
```

#### Шаг 2. Зарегистрируйте плагин в [`frontend/src/plugins/index.js`](file:///c:/Users/ilyac/robot/frontend/src/plugins/index.js)
Откройте файл `index.js` и добавьте две строчки:

```javascript
// 1. Импортируем манифест нового плагина:
import { GasSensorPlugin } from './gas_sensor/GasSensorWidget';

export const PLUGINS = [
  CameraPlugin,
  LidarPlugin,
  ControlsPlugin,
  BatteryPlugin,
  ImuPlugin,
  RelaysPlugin,
  StudentTemplatePlugin,
  GasSensorPlugin // 2. Добавляем в массив!
];
```
*Готово! Новый виджет автоматически появится на экране пульта с возможностью сворачивания и включения/выключения через меню «Плагины».*

---

## 3. Техпроцесс (ТП): Добавление нового физического датчика в систему

Если студенты подключили к роботу новый физический датчик (например, датчик температуры и влажности DHT22, ультразвуковой парктроник или манипулятор-клешню), добавление проходит по следующему стандартному техпроцессу:

```
┌────────────────────────┐      ┌────────────────────────┐      ┌────────────────────────┐
│   1. Микроконтроллер   │ ───► │  2. Бэкенд (Python)    │ ───► │   3. Веб-пульт (React) │
│ (Arduino / ESP32 / Pi) │ UART │ schemas.py + server.py │  SSE │    Новый React-виджет  │
└────────────────────────┘      └────────────────────────┘      └────────────────────────┘
```

### Шаг 1. Железо и прошивка микроконтроллера
1. Подключите датчик к свободным пинам микроконтроллера (I2C / SPI / АЦП).
2. В цикле опроса добавьте значение датчика в пакет телеметрии, отправляемый по UART в Raspberry Pi:
   ```json
   {"temp_c": 24.5, "humidity": 45}
   ```

### Шаг 2. Обновление схемы данных в [`backend/schemas.py`](file:///c:/Users/ilyac/robot/backend/schemas.py)
Добавьте новый класс данных:
```python
@dataclass
class ClimateTelemetry:
    temperature_c: float = 24.0
    humidity_pct: float = 45.0
```
И добавьте поле в `FullTelemetryMessage`:
```python
@dataclass
class FullTelemetryMessage:
    ...
    climate: ClimateTelemetry # Новое поле
```

### Шаг 3. Добавление в симулятор [`backend/mock_robot.py`](file:///c:/Users/ilyac/robot/backend/mock_robot.py)
Чтобы датчик работал и в мок-режиме, добавьте генерацию значений:
```python
def _get_climate_telemetry(self) -> ClimateTelemetry:
    return ClimateTelemetry(
        temperature_c=round(24.0 + random.uniform(-0.5, 0.5), 1),
        humidity_pct=round(45.0 + random.uniform(-1.0, 1.0), 1)
    )
```

### Шаг 4. Отображение на веб-пульте
Создайте виджет плагина (как описано в разделе 2 выше) — и данные нового датчика начнут отображаться на дашборде в реальном времени!
