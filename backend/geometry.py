"""
Геометрия мобильного робота: позы на плоскости и кинематика одометрии.
"""

from __future__ import annotations
import math
from dataclasses import dataclass


def normalize_angle(angle: float) -> float:
    """Переводит угол в диапазон (-pi, pi]."""
    while angle > math.pi:
        angle -= 2.0 * math.pi
    while angle <= -math.pi:
        angle += 2.0 * math.pi
    return angle


def deg_to_rad(deg: float) -> float:
    return math.radians(deg)


def rad_to_deg(rad: float) -> float:
    return math.degrees(rad)


@dataclass
class Pose:
    """
    Поза робота на плоскости: x, y в метрах, theta в радианах.
    theta = 0 — вдоль оси X, против часовой стрелки.
    """
    x: float = 0.0
    y: float = 0.0
    theta: float = 0.0

    def copy(self) -> Pose:
        return Pose(self.x, self.y, self.theta)

    def distance_to(self, other: Pose) -> float:
        return math.hypot(other.x - self.x, other.y - self.y)

    def angle_diff_to(self, target_theta: float) -> float:
        """Минимальная разница углов в диапазоне (-pi, pi]."""
        return normalize_angle(target_theta - self.theta)

    def as_dict(self) -> dict:
        return {
            "x": round(self.x, 4),
            "y": round(self.y, 4),
            "theta": round(self.theta, 4),
            "yaw_deg": round(math.degrees(self.theta), 2)
        }


def integrate_unicycle(pose: Pose, linear: float, angular: float, dt: float) -> Pose:
    """
    Интегрирование движения unicycle (линейная скорость v, угловая w) за шаг времени dt.
    Для угловой скорости w != 0 используется точное дуговое решение.
    """
    if dt <= 0.0:
        return pose.copy()

    if abs(angular) < 1e-7:
        # Прямолинейное перемещение
        return Pose(
            pose.x + linear * dt * math.cos(pose.theta),
            pose.y + linear * dt * math.sin(pose.theta),
            normalize_angle(pose.theta)
        )

    # Точное дуговое перемещение
    radius = linear / angular
    dtheta = angular * dt
    new_theta = normalize_angle(pose.theta + dtheta)
    new_x = pose.x + radius * (math.sin(pose.theta + dtheta) - math.sin(pose.theta))
    new_y = pose.y - radius * (math.cos(pose.theta + dtheta) - math.cos(pose.theta))
    return Pose(new_x, new_y, new_theta)
