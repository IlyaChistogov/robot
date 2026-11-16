# 📂 Структура проекта и назначение файлов

В данном документе описана архитектура программной платформы мобильного робота, назначение каждого файла и их взаимодействие.

---

## 🏗️ Общая архитектура системы

Платформа построена по принципу **единого интерфейса** (`BaseRobot`). Это позволяет разрабатывать код в режиме симулятора (`MockRobot`), а затем без изменения клиентского кода и веб-пульта переключиться на реальный робот (`RealRobot`).

```
                    ┌───────────────────────────────┐
                    │    Веб-пульт оператора (UI)   │
                    │      Студенческие скрипты     │
                    └───────────────┬───────────────┘
                                    │ HTTP / SSE / MJPEG
                    ┌───────────────▼───────────────┐
                    │       backend/server.py       │
                    │   (REST API + Video Stream)   │
                    └───────────────┬───────────────┘
                                    │ Вызовы методов BaseRobot
                    ┌───────────────▼───────────────┐
                    │      backend/base_robot.py    │
                    │     (Абстрактный интерфейс)   │
                    └───────▲───────────────▲───────┘
                            │               │
       ┌────────────────────┴──┐         ┌──┴──────────────────┐
       │ backend/mock_robot.py │         │ backend/real_robot  │
       │ (Виртуальная физика,  │         │  (Будущий драйвер   │
       │  RPLidar, VNH2SP30,   │         │  Serial/UART к      │
       │  АКБ 12В, комната)    │         │  Raspberry Pi)      │
       └───────────────────────┘         └─────────────────────┘
```

---

## 📁 Подробное описание файлов

### 1. `backend/` — Серверная часть и ядро управления

* **[`backend/schemas.py`](file:///c:/Users/ilyac/robot/backend/schemas.py)**
  * **Назначение:** Единый контракт данных (Data Contract).
  * **Что делает:** Описывает структуры всех входящих команд и исходящей телеметрии с использованием Python `dataclasses` (без сторонних зависимостей).
  * **Ключевые модели:**
    * `BatteryTelemetry`: Напряжение (10.8В – 12.8В), процент заряда, ток (А), флаг разряда.
    * `MotorTelemetry`: ШИМ каналов VNH2SP30 (-255..255), токи плеч моста по датчикам CS, тики энкодеров колес, температура драйвера.
    * `ImuTelemetry`: Углы ориентации (roll, pitch, yaw), угловая скорость и линейные ускорения с шумом движения.
    * `PoseTelemetry`: Координаты $X, Y$, курс и текущие скорости робота (одометрия).
    * `LidarScan`: Скан лидара RPLIDAR A1M8 (360 лучей от 0.15 м до 12.0 м с качеством сигнала).
    * `DriveCommand`: Входящая команда управления (`linear`, `angular`, `emergency_stop`).

* **[`backend/base_robot.py`](file:///c:/Users/ilyac/robot/backend/base_robot.py)**
  * **Назначение:** Базовый абстрактный класс (`BaseRobot`).
  * **Что делает:** Задает обязательный интерфейс для любого источника данных робота:
    * `set_drive_command(cmd)` — передача скоростей моторам;
    * `get_full_telemetry()` — получение полного слепка датчиков;
    * `trigger_emergency_stop()` — аппаратная/программная аварийная остановка;
    * `reset_emergency_stop()` — снятие блокировки аварийного останова.

* **[`backend/mock_robot.py`](file:///c:/Users/ilyac/robot/backend/mock_robot.py)**
  * **Назначение:** Программный симулятор робота (Mock Engine).
  * **Что делает:** Имитирует поведение физического робота на компьютере:
    * Моделирует двухколесную дифференциальную кинематику (колея 46 см, колеса 25 см).
    * Имитирует инерцию мощных червячных DC-моторов (плавный разгон с ограничением ускорения).
    * Моделирует свинцово-кислотный автомобильный аккумулятор 12В: ток покоя 1.5А (Raspberry Pi + лидар) вырастает до 10–12А под нагрузкой, вызывая реальную просадку напряжения по закону Ома ($V = \mathcal{E} - I \cdot R_{\text{вн}}$).
    * Реализует 2D-raycasting для лидара RPLIDAR A1M8 в виртуальной комнате 10х10 м с колоннами и препятствиями с учетом слепой зоны 15 см и погрешности измерения.
    * Содержит сторожевой таймер (Watchdog): при отсутствии команд управления более 1 секунды робот автоматически останавливается.

* **[`backend/real_robot.py`](file:///c:/Users/ilyac/robot/backend/real_robot.py)**
  * **Назначение:** Драйвер физического робота для Raspberry Pi.
  * **Что делает:**
    * Обменивается данными по Serial (115200 бод) с микроконтроллером VNH2SP30: отправляет ШИМ `M <l> <r>`, считывает реальные тики энкодеров и напряжение АКБ;
    * Считывает реальное 360-градусное облако точек с лидара Slamtec RPLIDAR A1M8 через USB-UART;
    * Захватывает реальное видео с курсовой камеры через OpenCV (`cv2.VideoCapture`).

* **[`backend/config.py`](file:///c:/Users/ilyac/robot/backend/config.py)**
  * **Назначение:** Конфигурационный файл переключения режимов.
  * **Что делает:** Позволяет менять `ROBOT_MODE = "mock"` на `"real"`, задавать COM/tty порты контроллера моторов и лидара.

* **[`backend/server.py`](file:///c:/Users/ilyac/robot/backend/server.py)**
  * **Назначение:** Сетевой шлюз и API-сервер (Flask).
  * **Что делает:** Предоставляет внешним клиентам (веб-пульту на React, мобильным приложениям, студенческим скриптам) доступ к роботу:
    * `GET /api/status` — быстрый опрос статуса и батареи;
    * `GET /api/telemetry` — снимок всех сенсоров в формате JSON;
    * `POST /api/drive` — отправка линейной и угловой скорости;
    * `POST /api/stop` — экстренная остановка (E-Stop);
    * `POST /api/reset_stop` — сброс аварийного останова;
    * `GET /api/stream` — высокоскоростной поток телеметрии Server-Sent Events (SSE, 10 Гц) для плавной отрисовки в браузере без накладных расходов;
    * `GET /video_feed` — видеопоток MJPEG курсовой камеры с наложением приборной панели (HUD) поверх изображения.

* **[`backend/robot_client.py`](file:///c:/Users/ilyac/robot/backend/robot_client.py)**
  * **Назначение:** Клиентская библиотека (Python SDK) для студентов.
  * **Что делает:** Позволяет студентам подключаться к роботу и управлять им за 3 строчки кода без необходимости вручную формировать HTTP-запросы:
    * `robot.get_telemetry()`, `robot.drive(linear, angular)`, `robot.stop()`, `robot.get_front_distance()`.

* **[`backend/test_mock.py`](file:///c:/Users/ilyac/robot/backend/test_mock.py)**
  * **Назначение:** Автоматический тест физики и симуляции мок-робота.
  * **Что делает:** Проверяет разгон моторов, просадку аккумулятора, пересчет лучей лидара и корректность одометрии.

* **[`backend/test_server.py`](file:///c:/Users/ilyac/robot/backend/test_server.py)**
  * **Назначение:** Модульный тест API-сервера Flask.
  * **Что делает:** Тестирует все HTTP-эндпоинты (`/api/status`, `/api/telemetry`, `/api/drive`, `/api/stop`).

---

### 2. `frontend/` — Веб-пульт оператора на React (Модульная плагинная архитектура)

Веб-пульт построен на **React + Vite**. Каждый датчик, видеопоток или элемент управления вынесен в независимый плагин-виджет (`frontend/src/plugins/`).

* **[`frontend/package.json`](file:///c:/Users/ilyac/robot/frontend/package.json)** — Конфигурация зависимостей веб-пульта (React 18, Lucide-React, Vite).
* **[`frontend/vite.config.js`](file:///c:/Users/ilyac/robot/frontend/vite.config.js)** — Настройка сборщика и автоматический прокси `/api` и `/video_feed` на бэкенд (порт 5000).
* **[`frontend/src/core/RobotContext.jsx`](file:///c:/Users/ilyac/robot/frontend/src/core/RobotContext.jsx)**:
  * Ядро взаимодействия с роботом.
  * Получает телеметрию через Server-Sent Events (SSE 10 Гц).
  * Предоставляет хук `useRobot()` с методами:
    * `telemetry`: данные всех датчиков (АКБ, лидар, IMU, одометрия, сонары);
    * `drive(linear, angular)`: отправка скоростей;
    * `triggerEmergencyStop()`, `resetEmergencyStop()`: аварийный останов;
    * `sendCustomCommand(endpoint, payload)`: отправка команд на любые кастомные датчики студентов;
    * `activePluginIds`, `togglePlugin(id)`: включение/выключение виджетов в интерфейсе.
* **[`frontend/src/components/Header.jsx`](file:///c:/Users/ilyac/robot/frontend/src/components/Header.jsx)** — Шапка пульта со статусом связи (Online/Offline), напряжением 12В АКБ, кнопкой экстренного останова «СТОП (SPACE)» и меню включения/отключения плагинов.
* **[`frontend/src/components/WidgetCard.jsx`](file:///c:/Users/ilyac/robot/frontend/src/components/WidgetCard.jsx)** — Универсальная карточка-контейнер для любого плагина (заголовок, иконка, статус, сворачивание).
* **[`frontend/src/plugins/index.js`](file:///c:/Users/ilyac/robot/frontend/src/plugins/index.js)** — Главный реестр плагинов. Чтобы подключить новый виджет, достаточно добавить 1 строчку в этот список!

#### Встроенные плагины:
* **[`frontend/src/plugins/camera/CameraWidget.jsx`](file:///c:/Users/ilyac/robot/frontend/src/plugins/camera/CameraWidget.jsx)** — Виджет курсовой камеры (MJPEG видеопоток, прицел, индикация FPS).
* **[`frontend/src/plugins/lidar/LidarRadarWidget.jsx`](file:///c:/Users/ilyac/robot/frontend/src/plugins/lidar/LidarRadarWidget.jsx)** — Интерактивный круговой радар RPLIDAR A1M8 на HTML5 Canvas (360° облако точек, кольца дальности 1-6 м, подсветка опасной дистанции).
* **[`frontend/src/plugins/controls/ControlsWidget.jsx`](file:///c:/Users/ilyac/robot/frontend/src/plugins/controls/ControlsWidget.jsx)** — Управление движением с клавиатуры (клавиши WASD и стрелки) + сенсорные кнопки + переключатель мощности ШИМ.
* **[`frontend/src/plugins/battery/BatteryWidget.jsx`](file:///c:/Users/ilyac/robot/frontend/src/plugins/battery/BatteryWidget.jsx)** — Панель автомобильного аккумулятора 12В (индикатор напряжения, процент емкости, суммарный ток всей системы, ШИМ и температура драйвера VNH2SP30).
* **[`frontend/src/plugins/imu/ImuCompassWidget.jsx`](file:///c:/Users/ilyac/robot/frontend/src/plugins/imu/ImuCompassWidget.jsx)** — Индикатор курса (компас), тангажа, крена и текущих координат одометрии.
* **[`frontend/src/plugins/relays/RelaysWidget.jsx`](file:///c:/Users/ilyac/robot/frontend/src/plugins/relays/RelaysWidget.jsx)** — Управление 8-канальным блоком силовых реле (свет, сирена, питание лидара, сервоприводы).
* **[`frontend/src/plugins/student_template/StudentSensorTemplate.jsx`](file:///c:/Users/ilyac/robot/frontend/src/plugins/student_template/StudentSensorTemplate.jsx)** — Шаблон для студентов: пример создания собственного виджета датчика и кнопок управления за 20 строк кода.

---

### 3. `firmware/` — Прошивка микроконтроллеров шасси

* **[`firmware/motor_controller/motor_controller.ino`](file:///c:/Users/ilyac/robot/firmware/motor_controller/motor_controller.ino)**
  * **Назначение:** Прошивка C++ / Arduino для платы управления моторами VNH2SP30 (Monster Moto Shield).
  * **Что делает:**
    * Генерирует ШИМ и управляет направлением вращения мощных DC-моторов по командам из Serial `M <l> <r>`;
    * Считывает импульсы с оптических энкодеров колес по аппаратным прерываниям;
    * Измеряет напряжение 12В автомобильного аккумулятора через аналоговый делитель на пине A0;
    * Измеряет токи моторов по выводам CS;
    * Реализует аппаратный аварийный таймер (Watchdog 500 мс): если управляющие пакеты от Raspberry Pi перестали поступать — моторы автоматически отключаются;
    * Управляет переключением блока силовых реле по командам `R <id> <state>`.

---

### 4. `plugins/` — Студенческие плагины и алгоритмы

* **[`plugins/avoid_obstacles.py`](file:///c:/Users/ilyac/robot/plugins/avoid_obstacles.py)**
  * **Назначение:** Эталонный пример студенческого автономного плагина.
  * **Что делает:** Считывает показания луча лидара прямо по курсу; если до препятствия менее 0.6 м — поворачивает в сторону, если менее 0.3 м — дает задний ход, если путь чист — едет вперед.

---

### 5. Документация и запуск

* **[`docs/API.md`](file:///c:/Users/ilyac/robot/docs/API.md)** — Полная спецификация REST API, SSE-потока телеметрии и видеопотока.
* **[`docs/PLUGINS_GUIDE.md`](file:///c:/Users/ilyac/robot/docs/PLUGINS_GUIDE.md)** — Руководство для студентов по созданию плагинов и сквозной техпроцесс (ТП) добавления новых датчиков.
* **[`start.bat`](file:///c:/Users/ilyac/robot/start.bat)** — Запуск всей системы (бэкенд + веб-пульт + открытие браузера) в 1 клик для Windows.
* **[`start.sh`](file:///c:/Users/ilyac/robot/start.sh)** — Скрипт запуска для Linux и Raspberry Pi.
* **[`README.md`](file:///c:/Users/ilyac/robot/README.md)** — Главное описание проекта, цели, задачи платформы и критерии валидации.
* **[`STRUCTURE.md`](file:///c:/Users/ilyac/robot/STRUCTURE.md)** — Данный файл с полной картой компонентов и их назначением.
* **[`.gitignore`](file:///c:/Users/ilyac/robot/.gitignore)** — Список исключений для Git.
