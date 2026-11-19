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
try:
    import cv2
except ImportError:
    cv2 = None
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
    print("  РОБОТ: Режим REAL (Сенсоры: Лидар A1M8 + 4 Камеры)")
    if getattr(config, "MOCK_MOTORS", True):
        print("  Моторы: MOCK (симуляция движения)")
    else:
        print("  Моторы: REAL (Raspberry Pi 5 GPIO VNH2SP30)")
    print(f"  Порт лидара:   {config.LIDAR_SERIAL_PORT}")
    print(f"  Камеры:        /dev/video{getattr(config, 'CAMERA_INDICES', [0, 2, 4, 6])}")
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


@app.route("/api/relay", methods=["POST", "OPTIONS"])
def relay_control():
    """Управление блоком силовых реле"""
    if request.method == "OPTIONS":
        return "", 200

    data = request.get_json(force=True, silent=True) or {}
    relay_id = data.get("relay_id")
    state = data.get("state")
    print(f"[Реле] Канал {relay_id}: {'ВКЛ' if state else 'ВЫКЛ'}")
    return jsonify({"success": True, "relay_id": relay_id, "state": state})


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
# Видеопоток (MJPEG) с поддержкой 4 камер кругового обзора
# -------------------------------------------------------------
camera_caps = {}
camera_lock = threading.Lock()


def release_other_cameras(keep_idx: int):
    """Освобождает неиспользуемые камеры, чтобы не перегружать шину USB 2.0 хаба"""
    with camera_lock:
        to_del = []
        for idx, cap in list(camera_caps.items()):
            if idx != keep_idx and cap is not None:
                try:
                    cap.release()
                    print(f"[Камера] Освобождено устройство /dev/video{idx} (освобождение шины USB)")
                except Exception:
                    pass
                to_del.append(idx)
        for idx in to_del:
            camera_caps.pop(idx, None)


def get_camera_cap(cam_idx: int, width: int = 640, height: int = 480, fps: int = 15):
    with camera_lock:
        if cam_idx not in camera_caps or camera_caps[cam_idx] is None:
            try:
                # В Linux/Raspberry Pi используем V4L2 бэкенд
                cap = cv2.VideoCapture(cam_idx, cv2.CAP_V4L2)
                if not cap or not cap.isOpened():
                    cap = cv2.VideoCapture(cam_idx)

                if cap and cap.isOpened():
                    # Критично для хаба: запрашиваем аппаратный MJPEG с камеры,
                    # чтобы не забивать шину USB 2.0 (480 Мбит/с на все 4 камеры)
                    fourcc = cv2.VideoWriter_fourcc(*'MJPG')
                    cap.set(cv2.CAP_PROP_FOURCC, fourcc)
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                    cap.set(cv2.CAP_PROP_FPS, fps)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                    # Прогревочный кадр
                    time.sleep(0.08)
                    ret, _ = cap.read()
                    camera_caps[cam_idx] = cap
                    print(f"[Камера] Устройство /dev/video{cam_idx} успешно открыто (MJPEG {width}x{height}@{fps}fps, ret={ret})")
                else:
                    camera_caps[cam_idx] = None
                    print(f"[Камера] Не удалось открыть устройство /dev/video{cam_idx}")
            except Exception as e:
                print(f"[Камера] Ошибка открытия /dev/video{cam_idx}: {e}")
                camera_caps[cam_idx] = None
        return camera_caps.get(cam_idx)


def read_cam_frame(cam_idx: int, label: str = ""):
    """Считывает кадр с камеры для сетки 2х2 в экономичном режиме (320x240 @ 10fps)"""
    cap = get_camera_cap(cam_idx, width=320, height=240, fps=10) if mode == "real" else None
    frame = None
    if cap and cap.isOpened():
        ret, raw_frame = cap.read()
        if ret and raw_frame is not None:
            frame = cv2.resize(raw_frame, (320, 180))

    if frame is None:
        frame = np.zeros((180, 320, 3), dtype=np.uint8)
        cv2.rectangle(frame, (0, 0), (320, 90), (35, 30, 30), -1)
        cv2.rectangle(frame, (0, 90), (320, 180), (45, 55, 45), -1)
        cv2.putText(frame, f"CAM {cam_idx}: NO SIGNAL", (20, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 255), 1)

    if label:
        cv2.rectangle(frame, (0, 0), (320, 24), (0, 0, 0), -1)
        cv2.putText(frame, label, (8, 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 200), 1)
    return frame


def generate_camera_frame(cam_param: str = "0"):
    if cv2 is None:
        while True:
            time.sleep(1.0)
            yield (b"--frame\r\nContent-Type: text/plain\r\n\r\nOpenCV not installed\r\n")

    cam_indices = getattr(config, "CAMERA_INDICES", [0, 2, 4, 6])

    while True:
        telemetry = robot.get_full_telemetry()

        if cam_param == "grid":
            # Режим 2х2 мультивид
            labels = ["1. ПЕРЕДНЯЯ (video0)", "2. ПРАВАЯ (video2)", "3. ЛЕВАЯ (video4)", "4. ЗАДНЯЯ (video6)"]
            frames = []
            for i, c_idx in enumerate(cam_indices[:4]):
                lbl = labels[i] if i < len(labels) else f"CAM {c_idx}"
                frames.append(read_cam_frame(c_idx, lbl))

            # Если камер меньше 4, дополняем пустыми
            while len(frames) < 4:
                frames.append(read_cam_frame(99, f"CAM {len(frames)+1}"))

            row1 = np.hstack([frames[0], frames[1]])
            row2 = np.hstack([frames[2], frames[3]])
            img = np.vstack([row1, row2])
        else:
            # Одиночная камера
            try:
                target_idx = int(cam_param)
            except ValueError:
                target_idx = config.CAMERA_INDEX

            # Освобождаем остальные камеры, чтобы текущая получила 100% полосы USB хаба
            release_other_cameras(target_idx)

            cap = get_camera_cap(target_idx, width=640, height=480, fps=15) if mode == "real" else None
            img = None
            if cap and cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    img = frame

            if img is None:
                img = np.zeros((360, 640, 3), dtype=np.uint8)
                cv2.rectangle(img, (0, 0), (640, 180), (35, 30, 30), -1)
                cv2.rectangle(img, (0, 180), (640, 360), (45, 55, 45), -1)

                pitch_offset = int(telemetry.imu.pitch * 300)
                horizon_y = max(50, min(310, 180 + pitch_offset))
                cv2.line(img, (0, horizon_y), (640, horizon_y), (80, 120, 80), 2)
                cv2.line(img, (300, 180), (340, 180), (0, 255, 0), 1)
                cv2.line(img, (320, 160), (320, 200), (0, 255, 0), 1)

            # Оверлей телеметрии (HUD)
            mode_text = f"CAM {target_idx}: REAL" if mode == "real" else f"CAM {target_idx}: MOCK"
            cv2.putText(img, mode_text, (20, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 200), 2)
            cv2.putText(img, f"BAT: {telemetry.battery.voltage}V ({telemetry.battery.percentage}%)  CURR: {telemetry.battery.current_amps}A",
                        (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            cv2.putText(img, f"FRONT DIST: {telemetry.lidar.ranges[0]:.2f} m",
                        (20, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1)

        if telemetry.status.emergency_stop:
            cv2.putText(img, "EMERGENCY STOP ACTIVE", (160, 220),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 3)

        _, buffer = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 70])
        frame_bytes = buffer.tobytes()

        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")
        time.sleep(0.066)


@app.route("/video_feed")
@app.route("/camera")
def video_feed():
    """MJPEG видеопоток с поддержкой выбора камеры ?cam=0|2|4|6|grid"""
    cam_param = request.args.get("cam", str(config.CAMERA_INDEX)).lower()
    return Response(
        generate_camera_frame(cam_param),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/api/cameras", methods=["GET"])
def get_cameras_list():
    """Список всех доступных камер кругового обзора"""
    cam_indices = getattr(config, "CAMERA_INDICES", [0, 2, 4, 6])
    names = ["1. Передняя", "2. Правая", "3. Левая", "4. Задняя"]
    cams = []
    for i, idx in enumerate(cam_indices):
        name = names[i] if i < len(names) else f"Камера {i+1}"
        cams.append({
            "id": idx,
            "device": f"/dev/video{idx}",
            "name": name
        })
    return jsonify({"cameras": cams, "grid_supported": True})


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
