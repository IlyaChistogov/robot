"""
HTTP и Streaming сервер телеметрии мобильного робота (Flask).
Работает как с виртуальным симулятором (MockRobot), так и с реальным шасси (RealRobot).

Предоставляет:
- GET  /api/status        — состояние системы и батареи
- GET  /api/telemetry     — текущий снимок всех датчиков (лидар, IMU, одометрия)
- POST /api/drive         — отправка команд скорости { linear, angular }
- POST /api/stop          — мгновенная аварийная остановка (E-Stop)
- GET  /api/stream        — живой поток телеметрии (Server-Sent Events, 10 Гц)
- GET  /video_feed        — видеопоток (MJPEG stream: синтетический вид с курсовой камеры)
"""

import json
import time
import cv2
import numpy as np
from flask import Flask, jsonify, request, Response
from schemas import DriveCommand
from mock_robot import MockRobot
import config

try:
    from real_robot import RealRobot
except ImportError:
    RealRobot = None

app = Flask(__name__)

# Выбор реализации робота по конфигу
if config.ROBOT_MODE == "real" and RealRobot is not None:
    print("==================================================")
    print("  РОБОТ: Режим REAL (Физическое шасси)")
    print(f"  Порт моторов: {config.MOTOR_SERIAL_PORT}")
    print(f"  Порт лидара:   {config.LIDAR_SERIAL_PORT}")
    print("==================================================")
    robot = RealRobot()
else:
    print("==================================================")
    print("  РОБОТ: Режим MOCK (Симулятор платформы)")
    print("==================================================")
    robot = MockRobot()


@app.after_request
def enable_cors(response):
    """Разрешаем запросы от фронтенда (React / Vite) с любого порта"""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.route("/api/status", methods=["GET"])
def get_status():
    telemetry = robot.get_full_telemetry()
    return jsonify({
        "status": telemetry.status.__dict__,
        "battery": telemetry.battery.__dict__
    })


@app.route("/api/telemetry", methods=["GET"])
def get_telemetry():
    telemetry = robot.get_full_telemetry()
    return jsonify(telemetry.to_dict())


@app.route("/api/drive", methods=["POST", "OPTIONS"])
def drive():
    if request.method == "OPTIONS":
        return "", 200

    data = request.get_json(force=True, silent=True) or {}
    linear = float(data.get("linear", 0.0))
    angular = float(data.get("angular", 0.0))
    e_stop = data.get("emergency_stop", None)

    cmd = DriveCommand(linear=linear, angular=angular, emergency_stop=e_stop)
    robot.set_drive_command(cmd)

    return jsonify({"success": True, "linear": linear, "angular": angular})


@app.route("/api/stop", methods=["POST", "OPTIONS"])
def stop():
    if request.method == "OPTIONS":
        return "", 200

    robot.trigger_emergency_stop()
    return jsonify({"success": True, "emergency_stop": True})


@app.route("/api/reset_stop", methods=["POST", "OPTIONS"])
def reset_stop():
    if request.method == "OPTIONS":
        return "", 200

    robot.reset_emergency_stop()
    return jsonify({"success": True, "emergency_stop": False})


@app.route("/api/stream")
def telemetry_stream():
    """Server-Sent Events (SSE) поток телеметрии с частотой 10 Гц"""
    def event_stream():
        while True:
            telemetry = robot.get_full_telemetry()
            payload = json.dumps(telemetry.to_dict())
            yield f"data: {payload}\n\n"
            time.sleep(0.1)

    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


def generate_camera_frame():
    """Генерация видеопотока (реальная камера или синтетическая эмуляция)"""
    real_cap = None
    if config.ROBOT_MODE == "real":
        try:
            real_cap = cv2.VideoCapture(config.CAMERA_INDEX)
            real_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            real_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
        except Exception as e:
            print(f"[Камера] Ошибка открытия камеры {config.CAMERA_INDEX}: {e}")

    while True:
        telemetry = robot.get_full_telemetry()
        img = None

        if real_cap and real_cap.isOpened():
            ret, frame = real_cap.read()
            if ret:
                img = frame

        # Если реальной камеры нет или мы в режиме мока — генерируем виртуальный вид
        if img is None:
            img = np.zeros((360, 640, 3), dtype=np.uint8)
            cv2.rectangle(img, (0, 0), (640, 180), (35, 30, 30), -1)   # Верх
            cv2.rectangle(img, (0, 180), (640, 360), (45, 55, 45), -1) # Пол

            pitch_offset = int(telemetry.imu.pitch * 300)
            horizon_y = 180 + pitch_offset
            cv2.line(img, (0, horizon_y), (640, horizon_y), (80, 120, 80), 2)
            cv2.line(img, (300, 180), (340, 180), (0, 255, 0), 1)
            cv2.line(img, (320, 160), (320, 200), (0, 255, 0), 1)

        # Оверлей телеметрии (HUD)
        mode_text = "REAL HARDWARE" if config.ROBOT_MODE == "real" else "MOCK SIMULATOR"
        cv2.putText(img, f"CAM: {mode_text}", (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 200), 2)
        cv2.putText(img, f"BAT: {telemetry.battery.voltage}V ({telemetry.battery.percentage}%)  CURR: {telemetry.battery.current_amps}A",
                    (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        cv2.putText(img, f"SPEED: {telemetry.pose.linear_velocity} m/s  YAW: {telemetry.pose.yaw} rad",
                    (20, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(img, f"FRONT DIST: {telemetry.lidar.ranges[0]:.2f} m",
                    (20, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1)

        if telemetry.status.emergency_stop:
            cv2.putText(img, "EMERGENCY STOP ACTIVE", (160, 220),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 3)

        _, buffer = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 75])
        frame_bytes = buffer.tobytes()

        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")
        time.sleep(0.066)


@app.route("/video_feed")
def video_feed():
    """MJPEG видеопоток для вывода на веб-пульт"""
    return Response(
        generate_camera_frame(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


if __name__ == "__main__":
    print("==================================================")
    print("  РОБОТ: Сервер телеметрии и управления запущен   ")
    print("  Режим: MOCK (VNH2SP30 + RPLIDAR A1M8 + 12V АКБ) ")
    print("  Порт:  http://127.0.0.1:5000                   ")
    print("==================================================")
    app.run(host="0.0.0.0", port=5000, threaded=True)
