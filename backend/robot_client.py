"""
Клиентская библиотека (SDK) для студентов и прикладных алгоритмов.
Позволяет управлять роботом в 3 строки кода как в симуляторе (Mock), так и на реальном шасси.

Поддерживает:
- Прямое управление скоростями: robot.drive(linear, angular)
- Точные примитивы перемещения: robot.move(distance_m) и robot.turn(angle_deg)
- Получение телеметрии и сканов лидара: robot.scan(), robot.get_front_distance()
- Безопасный контекстный менеджер: with RobotClient() as robot: ...
"""

from __future__ import annotations
import math
import time
from typing import Optional, List, Tuple, Dict, Any
import requests


def normalize_angle_deg(angle: float) -> float:
    """Нормализует угол в градусах в диапазон (-180, 180]."""
    while angle > 180.0:
        angle -= 360.0
    while angle <= -180.0:
        angle += 360.0
    return angle


class RobotClient:
    def __init__(self, host: str = "http://127.0.0.1:5000", timeout: float = 2.0):
        self.host = host.rstrip("/")
        self.request_timeout = timeout

    def __enter__(self) -> "RobotClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.stop()
        except Exception:
            pass

    # -------------------------------------------------------------
    # Базовые запросы состояния
    # -------------------------------------------------------------
    def get_status(self) -> dict:
        """Получить статус робота, режим работы и параметры батареи."""
        resp = requests.get(f"{self.host}/api/status", timeout=self.request_timeout)
        resp.raise_for_status()
        return resp.json()

    def get_telemetry(self) -> dict:
        """Получить полный снимок телеметрии (моторы, одометрия, IMU, лидар, батарея)."""
        resp = requests.get(f"{self.host}/api/telemetry", timeout=self.request_timeout)
        resp.raise_for_status()
        return resp.json()

    def get_pose(self) -> Tuple[float, float, float]:
        """Возвращает текущую позу одометрии (x_m, y_m, yaw_deg)."""
        t = self.get_telemetry()
        pose = t.get("pose", {})
        x = pose.get("x", 0.0)
        y = pose.get("y", 0.0)
        yaw_rad = pose.get("yaw", 0.0)
        return x, y, math.degrees(yaw_rad)

    # -------------------------------------------------------------
    # Управление скоростью
    # -------------------------------------------------------------
    def drive(self, linear: float, angular: float = 0.0) -> bool:
        """
        Отправить непрерывную команду скорости:
        - linear: линейная скорость вперед/назад в м/с (-1.0 .. 1.0)
        - angular: угловая скорость вращения в рад/с (-2.0 .. 2.0)
        """
        payload = {"linear": float(linear), "angular": float(angular)}
        try:
            resp = requests.post(f"{self.host}/api/drive", json=payload, timeout=self.request_timeout)
            return resp.status_code == 200
        except Exception:
            return False

    def stop(self) -> bool:
        """Мгновенно остановить движение моторов."""
        return self.drive(linear=0.0, angular=0.0)

    def emergency_stop(self) -> bool:
        """Активировать аварийную блокировку моторов (E-Stop)."""
        try:
            resp = requests.post(f"{self.host}/api/stop", timeout=self.request_timeout)
            return resp.status_code == 200
        except Exception:
            return False

    def reset_emergency_stop(self) -> bool:
        """Снять аварийную блокировку."""
        try:
            resp = requests.post(f"{self.host}/api/reset_stop", timeout=self.request_timeout)
            return resp.status_code == 200
        except Exception:
            return False

    # -------------------------------------------------------------
    # Высокоуровневые команды движения (примитивы перемещения)
    # -------------------------------------------------------------
    def move(self, distance_m: float, speed: float = 0.3, tolerance: float = 0.02, timeout: float = 15.0) -> bool:
        """
        Проехать заданное расстояние в метрах по одометрии:
        - distance_m > 0: движение вперед, distance_m < 0: назад
        - speed: целевая скорость (м/с)
        - tolerance: допустимая погрешность остановки (метры)
        - timeout: максимальное время выполнения в секундах
        """
        if abs(distance_m) < tolerance:
            return True

        x0, y0, _ = self.get_pose()
        target_dist = abs(distance_m)
        direction = 1.0 if distance_m >= 0 else -1.0
        start_time = time.time()

        rate_hz = 20
        dt = 1.0 / rate_hz

        try:
            while time.time() - start_time < timeout:
                x, y, _ = self.get_pose()
                traveled = math.hypot(x - x0, y - y0)
                remaining = target_dist - traveled

                if remaining <= tolerance:
                    break

                # Плавное замедление перед финишем
                current_speed = min(speed, max(0.1, remaining * 1.5))
                self.drive(linear=direction * current_speed, angular=0.0)
                time.sleep(dt)

            self.stop()
            time.sleep(0.1)
            return True
        except Exception as e:
            self.stop()
            raise e

    def turn(self, angle_deg: float, speed: float = 0.8, tolerance_deg: float = 2.0, timeout: float = 12.0) -> bool:
        """
        Повернуться на заданный угол в градусах:
        - angle_deg > 0: поворот влево (против часовой стрелки)
        - angle_deg < 0: поворот вправо (по часовой стрелке)
        - speed: максимальная угловая скорость (рад/с)
        - tolerance_deg: допустимая погрешность угла
        """
        if abs(angle_deg) < tolerance_deg:
            return True

        _, _, start_yaw = self.get_pose()
        target_yaw = normalize_angle_deg(start_yaw + angle_deg)
        start_time = time.time()

        rate_hz = 20
        dt = 1.0 / rate_hz

        try:
            while time.time() - start_time < timeout:
                _, _, current_yaw = self.get_pose()
                error_deg = normalize_angle_deg(target_yaw - current_yaw)

                if abs(error_deg) <= tolerance_deg:
                    break

                direction = 1.0 if error_deg > 0 else -1.0
                error_rad = math.radians(abs(error_deg))
                # Пропорциональное замедление при подходе к целевому курсу
                current_w = min(speed, max(0.2, error_rad * 1.8))
                self.drive(linear=0.0, angular=direction * current_w)
                time.sleep(dt)

            self.stop()
            time.sleep(0.1)
            return True
        except Exception as e:
            self.stop()
            raise e

    # -------------------------------------------------------------
    # Лидар и дальнометрия
    # -------------------------------------------------------------
    def scan(self) -> List[float]:
        """Получить 360 лучей расстояний лидара RPLIDAR A1M8 (в метрах, 0..359°)."""
        t = self.get_telemetry()
        return t.get("lidar", {}).get("ranges", [999.0] * 360)

    def get_front_distance(self) -> float:
        """Расстояние до препятствия строго впереди (0°)."""
        ranges = self.scan()
        if not ranges:
            return 999.0
        # Усреднение трех лучей по центру для надежности (359, 0, 1)
        candidates = [ranges[0]]
        if len(ranges) > 1:
            candidates.append(ranges[1])
            candidates.append(ranges[-1])
        return min(candidates)

    def sector_distance(self, center_deg: float = 0.0, span_deg: float = 40.0) -> float:
        """
        Минимальное расстояние до препятствия в заданном секторе:
        - center_deg: центр сектора (0 — прямо, 90 — влево, -90 — вправо, 180 — назад)
        - span_deg: ширина сектора в градусах (+- span_deg/2)
        """
        ranges = self.scan()
        if not ranges or len(ranges) < 360:
            return 999.0

        half_span = span_deg / 2.0
        min_dist = 999.0

        for deg in range(360):
            # Переводим в диапазон -180..180 относительно центра
            diff = abs(normalize_angle_deg(deg - center_deg))
            if diff <= half_span:
                d = ranges[deg]
                if 0.05 < d < min_dist:
                    min_dist = d

        return min_dist


def connect(host: str = "http://127.0.0.1:5000") -> RobotClient:
    """Быстрая точка входа для студентов: robot = connect()"""
    return RobotClient(host=host)
