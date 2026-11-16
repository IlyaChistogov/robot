# 📡 Спецификация программного интерфейса (Robot API)

Данный документ содержит полное описание API платформы мобильного робота.  
API доступно как в режиме симулятора (`MOCK`), так и при работе с реальным шасси (`REAL`).

---

## 🌐 Базовый URL
По умолчанию сервер доступен по адресу:
```
http://localhost:5000
```
*(При работе с Raspberry Pi по Wi-Fi замените `localhost` на IP-адрес робота в локальной сети, например `http://192.168.1.100:5000`)*.

---

## 📋 Список HTTP-эндпоинтов

### 1. `GET /api/status`
Быстрая проверка доступности робота и состояния питания.

* **Метод:** `GET`
* **Заголовки ответа:** `Content-Type: application/json`
* **Пример ответа (200 OK):**
```json
{
  "battery": {
    "voltage": 12.59,
    "percentage": 97.4,
    "current_amps": 1.48,
    "is_low": false
  },
  "status": {
    "mode": "mock",
    "emergency_stop": false,
    "motors_enabled": true,
    "connection_alive": true
  }
}
```

---

### 2. `GET /api/telemetry`
Полный мгновенный снимок показаний всех сенсоров робота.

* **Метод:** `GET`
* **Пример ответа (200 OK):**
```json
{
  "timestamp": 1731754800.123,
  "battery": {
    "voltage": 12.59,
    "percentage": 97.4,
    "current_amps": 1.48,
    "is_low": false
  },
  "motors": {
    "left_pwm": 0,
    "right_pwm": 0,
    "left_current_amps": 0.0,
    "right_current_amps": 0.0,
    "left_encoder_ticks": 1420,
    "right_encoder_ticks": 1422,
    "driver_temperature_c": 28.5
  },
  "imu": {
    "roll": 0.0012,
    "pitch": -0.0021,
    "yaw": 0.145,
    "gyro_z": 0.0,
    "accel_x": 0.02,
    "accel_y": -0.01
  },
  "pose": {
    "x": 0.25,
    "y": 0.10,
    "yaw": 0.145,
    "linear_velocity": 0.0,
    "angular_velocity": 0.0
  },
  "lidar": {
    "angle_min": 0.0,
    "angle_max": 6.283185,
    "angle_increment": 0.017453,
    "range_min": 0.15,
    "range_max": 12.0,
    "ranges": [4.98, 4.97, 4.95, "... 360 значений в метрах ..."],
    "intensities": [47, 47, 46, "... качество отражения ..."]
  },
  "ultrasonic": {
    "front_center_m": 4.98,
    "front_left_m": 4.95,
    "front_right_m": 4.96
  },
  "status": {
    "mode": "mock",
    "emergency_stop": false,
    "motors_enabled": true,
    "connection_alive": true
  }
}
```

---

### 3. `POST /api/drive`
Отправка команды движения на контроллер моторов VNH2SP30.

* **Метод:** `POST`
* **Заголовки запроса:** `Content-Type: application/json`
* **Тело запроса:**
```json
{
  "linear": 0.5,       // Линейная скорость в м/с (от -1.0 до 1.0)
  "angular": 0.2       // Угловая скорость в рад/с (от -2.0 до 2.0, поворот влево > 0)
}
```
* **Пример ответа (200 OK):**
```json
{
  "success": true,
  "linear": 0.5,
  "angular": 0.2
}
```
> **Внимание:** В системе работает сторожевой таймер (Watchdog). Если робот не получает новую команду движения в течение 1 секунды, моторы автоматически останавливаются.

---

### 4. `POST /api/stop`
Мгновенная аварийная остановка (E-Stop).

* **Метод:** `POST`
* **Тело запроса:** `{}` (пустое)
* **Пример ответа (200 OK):**
```json
{
  "success": true,
  "emergency_stop": true
}
```
*При активном E-Stop моторы обесточены, а последующие команды движения игнорируются до сброса.*

---

### 5. `POST /api/reset_stop`
Снятие блокировки аварийной остановки.

* **Метод:** `POST`
* **Пример ответа (200 OK):**
```json
{
  "success": true,
  "emergency_stop": false
}
```

---

### 6. `GET /api/stream` (Живой поток телеметрии)
Потоковая передача телеметрии по протоколу **Server-Sent Events (SSE)** с частотой 10 Гц.

* **Метод:** `GET`
* **Заголовки ответа:** `Content-Type: text/event-stream`
* **Использование в JavaScript / React:**
```javascript
const evtSource = new EventSource("http://localhost:5000/api/stream");
evtSource.onmessage = (event) => {
  const telemetry = JSON.parse(event.data);
  console.log("Дистанция впереди:", telemetry.lidar.ranges[0]);
};
```

---

### 7. `GET /video_feed` (Видеопоток)
Трансляция видео с курсовой камеры в формате **MJPEG** (Motion JPEG).

* **Метод:** `GET`
* **Заголовки ответа:** `Content-Type: multipart/x-mixed-replace; boundary=frame`
* **Использование в HTML / React:**
```html
<img src="http://localhost:5000/video_feed" alt="Камера робота" />
```

---

## 🐍 Использование через Python SDK (`robot_client.py`)

Студентам не требуется вручную отправлять HTTP-запросы — для этого есть готовый класс `RobotClient`:

```python
from robot_client import RobotClient

# Подключение
robot = RobotClient("http://localhost:5000")

# Получение данных
status = robot.get_status()
print(f"Заряд аккумулятора: {status['battery']['voltage']} В")

dist = robot.get_front_distance()
print(f"Препятствие впереди: {dist:.2f} м")

# Управление
robot.drive(linear=0.4, angular=0.0) # Вперед со скоростью 0.4 м/с
robot.stop()                         # Плавная остановка
robot.emergency_stop()               # Аварийный E-Stop
```
