# Платформа мобильного робота

[![CI](https://github.com/IlyaChistogov/robot/actions/workflows/ci.yml/badge.svg)](https://github.com/IlyaChistogov/robot/actions/workflows/ci.yml)

Базовая программно-аппаратная платформа мобильного робота для студенческих исследований:
управление шасси, комплекс сенсоров (лидар 360°, камера, IMU, АКБ), симулятор мок-режима для разработки без железа, многомодульный веб-пульт оператора на React и удобный Python SDK с примитивами перемещения для прикладных алгоритмов.

---

## 🚀 Быстрый старт

### 1. Запуск платформы на компьютере (Симулятор + Веб-пульт)

В терминале проекта (PowerShell):
```powershell
.\start.bat
# или
.\start.ps1
```
Скрипт запустит сервер и автоматически откроет веб-пульт оператора в браузере по адресу `http://localhost:5173`.

### 2. Запуск в режиме Single-Port (Production / на роботе)
Бэкенд умеет самостоятельно раздавать собранный React Web UI:
```bash
python backend/server.py
# -> Весь веб-пульт и API доступны на едином порту: http://localhost:5000
```

---

## 💡 Python SDK в трёх строках

```python
from robot_client import connect

with connect() as robot:
    robot.move(1.0)       # 1 метр вперед по одометрии
    robot.turn(90.0)      # поворот на 90° влево
    ranges = robot.scan() # 360 лучей лидара RPLIDAR A1M8
```

---

## 📂 Структура репозитория

```
├── backend/                  # Серверная часть и драйверы
│   ├── base_robot.py         # Единый абстрактный контракт (BaseRobot)
│   ├── mock_robot.py         # Физический симулятор (комната, VNH2SP30, RPLIDAR, АКБ)
│   ├── real_robot.py         # Аппаратный драйвер реального робота
│   ├── rplidar_driver.py     # Парсер бинарного протокола Slamtec RPLIDAR A1M8
│   ├── geometry.py           # Кинематика одометрии (модель unicycle, дуговое интегрирование)
│   ├── server.py             # Сервер телеметрии (REST, SSE, MJPEG, раздача Web UI)
│   ├── schemas.py            # Строгие модели данных телеметрии (dataclasses)
│   ├── robot_client.py       # Студенческий SDK (move, turn, scan, drive)
│   └── config.py             # Конфигурация портов и режимов
├── frontend/                 # Веб-пульт оператора (React + Vite + Tailwind)
│   ├── src/components/       # Хедер, карточки виджетов
│   └── src/plugins/          # Модули: джойстик/WASD, радар лидара, камера, АКБ, IMU, реле
├── examples/                 # Примеры студенческих алгоритмов
│   ├── drive_square.py       # Проезд квадрата 1х1 м и калибровка одометрии
│   ├── avoid_obstacles.py    # Интеллектуальный автопилот объезда стен
│   └── teleop_wasd.py        # Управление роботом с клавиатуры в терминале / по SSH
├── firmware/                 # Прошивка контроллера шасси
│   └── motor_controller/     # C++/Arduino скетч VNH2SP30 (ШИМ 20 кГц, энкодеры, Watchdog)
├── docs/                     # Документация
│   ├── API.md                # Спецификация REST и SSE API
│   └── PLUGINS_GUIDE.md      # Руководство по разработке новых виджетов
├── tests/                    # Набор автотестов (pytest)
└── .github/workflows/ci.yml  # GitHub Actions CI
```

---

## 🧪 Запуск автотестов

```bash
pytest tests/ -v
```
Все 9 ключевых тестов геометрии, симулятора и протокола лидара выполняются за ~0.2 секунды.
