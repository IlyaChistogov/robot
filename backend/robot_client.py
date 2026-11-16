"""
Клиентская библиотека (SDK) для студентов.
Позволяет управлять роботом и получать показания сенсоров в несколько строк кода
как в режиме симулятора (мока), так и на реальном роботе.
"""

import requests
import json
import time
from typing import Optional, Callable


class RobotClient:
    def __init__(self, host: str = "http://127.0.0.1:5000"):
        self.host = host.rstrip("/")

    def get_status(self) -> dict:
        """Получить статус робота и батареи"""
        resp = requests.get(f"{self.host}/api/status", timeout=2)
        resp.raise_for_status()
        return resp.json()

    def get_telemetry(self) -> dict:
        """Получить полный снимок данных всех датчиков (лидар, IMU, моторы, одометрия)"""
        resp = requests.get(f"{self.host}/api/telemetry", timeout=2)
        resp.raise_for_status()
        return resp.json()

    def drive(self, linear: float, angular: float = 0.0) -> bool:
        """
        Отправить команду скорости:
        - linear: линейная скорость вперед/назад в м/с (-1.0 .. 1.0)
        - angular: угловая скорость поворота в рад/с (-2.0 .. 2.0)
        """
        payload = {"linear": float(linear), "angular": float(angular)}
        resp = requests.post(f"{self.host}/api/drive", json=payload, timeout=2)
        return resp.status_code == 200

    def stop(self) -> bool:
        """Мгновенно остановить моторы"""
        return self.drive(linear=0.0, angular=0.0)

    def emergency_stop(self) -> bool:
        """Активировать аварийный стоп (E-Stop)"""
        resp = requests.post(f"{self.host}/api/stop", timeout=2)
        return resp.status_code == 200

    def reset_emergency_stop(self) -> bool:
        """Сбросить аварийный стоп"""
        resp = requests.post(f"{self.host}/api/reset_stop", timeout=2)
        return resp.status_code == 200

    def get_lidar_ranges(self) -> list:
        """Получить 360 лучей расстояний лидара RPLIDAR A1M8 (в метрах)"""
        t = self.get_telemetry()
        return t.get("lidar", {}).get("ranges", [])

    def get_front_distance(self) -> float:
        """Получить дистанцию до ближайшего препятствия строго впереди (луч 0°)"""
        ranges = self.get_lidar_ranges()
        return ranges[0] if ranges else 999.0


# Пример студенческого скрипта автономного объезда препятствий
if __name__ == "__main__":
    robot = RobotClient("http://127.0.0.1:5000")
    print("Подключение к роботу...")
    try:
        status = robot.get_status()
        print(f"Подключено! Статус батареи: {status['battery']['voltage']}V ({status['battery']['percentage']}%)")
    except Exception as e:
        print(f"Сервер не запущен: {e}")
        print("Сначала запустите: python server.py")
