"""
HTTP, Streaming и Web сервер мобильного робота (Flask).
Работает как в режиме симулятора (MockRobot), так и с реальным шасси (RealRobot).

Предоставляет:
- GET  /api/status        — состояние системы и батареи
- GET  /api/telemetry     — текущий снимок всех датчиков (лидар, IMU, одометрия)
- POST /api/drive         — отправка команд скорости { linear, angular }
- POST /api/stop          — мгновенная остановка
- POST /api/reset_stop    — сброс аварийного стопа
- GET  /api/stream        — живой поток телеметрии (Server-Sent Events, 10 Гц)
- GET  /video_feed, /camera — MJPEG видеопоток (с камеры или синтетический вид)
- GET  /                  — раздача собранного React веб-пульта (Single Port Mode)
"""

import os
import sys
import json
import time
import threading
import argparse
import cv2
import numpy as np
from flask import Flask, jsonify, request, Response, send_from_directory
from schemas import DriveCommand
from mock_robot import MockRobot
import config

try:
    from real_robot import RealRobot
except ImportError:
    RealRobot = None

# Парсинг аргументов командной строки
parser = argparse.ArgumentParser(description="Robot Telemetry & Web Server")
parser.add_argument("--real", action="store_true", help="Запуск в режиме реального робота")
parser.add_argument("--mock", action="store_true", help="Запуск в режиме мок-симулятора")
parser.add_argument("--port", type=int, default=5000, help="Порт сервера (по умолчанию 5000)")
parser.add_argument("--host", type=str, default="0.0.0.0", help="Хост сервера")
parser.add_argument("--static", type=str, default=None, help="Каталог собранного веб-пульта")
cli_args, _ = parser.parse_known_args()

# Определение режима работы
mode = config.ROBOT_MODE
if cli_args.real:
    mode = "real"
elif cli_args.mock:
    mode = "mock"

# Путь к собранному фронтенду (Single Port Production Mode)
if cli_args.static:
    STATIC_DIR = os.path.abspath(cli_args.static)
else:
    STATIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))

app = Flask(__name__)

# Инициализация робота
if mode == "real" and RealRobot is not None:
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
    """Разрешаем CORS запросы от любого интерфейса"""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


# -------------------------------------------------------------
# REST API
# -------------------------------------------------------------
@app.route("/api/status", methods=["GET"])
def get_status():
    telemetry = robot.get_full_telemetry()
    return jsonify({
        "status": telemetry.status.__dict__,
        "battery": telemetry.battery.__dict__,
        "mode": "real" if mode == "real" else "mock"
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
    """Server-Sent Events (SSE) поток телеметрии (10 Гц)"""
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


# -------------------------------------------------------------
# Видеопоток (MJPEG)
# -------------------------------------------------------------
def generate_camera_frame():
    real_cap = None
    if mode == "real":
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

        if img is None:
            # Синтетический вид от первого лица
            img = np.zeros((360, 640, 3), dtype=np.uint8)
            cv2.rectangle(img, (0, 0), (640, 180), (35, 30, 30), -1)   # Небо/потолок
            cv2.rectangle(img, (0, 180), (640, 360), (45, 55, 45), -1) # Пол

            pitch_offset = int(telemetry.imu.pitch * 300)
            horizon_y = max(50, min(310, 180 + pitch_offset))
            cv2.line(img, (0, horizon_y), (640, horizon_y), (80, 120, 80), 2)
            cv2.line(img, (300, 180), (340, 180), (0, 255, 0), 1)
            cv2.line(img, (320, 160), (320, 200), (0, 255, 0), 1)

        # Оверлей телеметрии (HUD)
        mode_text = "REAL HARDWARE" if mode == "real" else "MOCK SIMULATOR"
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
@app.route("/camera")
def video_feed():
    """MJPEG видеопоток для вывода на веб-пульт"""
    return Response(
        generate_camera_frame(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


# -------------------------------------------------------------
# Раздача веб-пульта оператора (Single Port Mode)
# -------------------------------------------------------------
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_web_ui(path):
    if path.startswith("api/") or path in ("video_feed", "camera"):
        return jsonify({"error": "Endpoint not found"}), 404

    target_file = os.path.join(STATIC_DIR, path)
    if path != "" and os.path.isfile(target_file):
        return send_from_directory(STATIC_DIR, path)

    index_html = os.path.join(STATIC_DIR, "index.html")
    if os.path.isfile(index_html):
        return send_from_directory(STATIC_DIR, "index.html")

    # Fallback страница, если сборка еще не произведена
    return """
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><title>Robot Server</title></head>
    <body style="font-family: sans-serif; background: #111; color: #eee; padding: 40px;">
        <h2>🤖 Платформа мобильного робота: Сервер запущен</h2>
        <p>Сервер телеметрии и видеопотока успешно работает на порту 5000.</p>
        <ul>
            <li>Телеметрия: <a href="/api/status" style="color:#4df">/api/status</a></li>
            <li>Снимок датчиков: <a href="/api/telemetry" style="color:#4df">/api/telemetry</a></li>
            <li>Видеопоток: <a href="/camera" style="color:#4df">/camera</a></li>
        </ul>
        <p>Для запуска веб-пульта: запустите <code>start.bat</code> или соберите фронтенд: <code>cd frontend && npm run build</code>.</p>
    </body>
    </html>
    """, 200


if __name__ == "__main__":
    print("==================================================")
    print(f"  РОБОТ: Сервер телеметрии и управления запущен")
    print(f"  Режим:  {'REAL (Аппаратный)' if mode == 'real' else 'MOCK (Симулятор)'}")
    print(f"  Статика Web UI: {STATIC_DIR if os.path.isdir(STATIC_DIR) else 'Не собрана (Vite dev режим)'}")
    print(f"  Адрес:  http://127.0.0.1:{cli_args.port}")
    print("==================================================")
    app.run(host=cli_args.host, port=cli_args.port, threaded=True)
