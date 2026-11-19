"""
Схемы и структуры данных телеметрии и команд мобильного робота.
Соответствуют реальному оборудованию:
- Лидар: Slamtec RPLIDAR A1M8 (0.15м - 12.0м, 360 градусов)
- Драйвер: Dual VNH2SP30 H-Bridge (PWM -255..255, токовый сенсор)
- Батарея: 12V Car Battery (Pb-Acid, 10.8V - 12.8V)
- Привод: Дифференциальный (2 ведущих колеса с энкодерами)

Использует встроенный модуль dataclasses (zero-dependency, работает в любом Python 3.7+).
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional
import time


@dataclass
class BatteryTelemetry:
    """Телеметрия свинцово-кислотного автомобильного аккумулятора 12В"""
    voltage: float           # Текущее напряжение в вольтах (10.8V - 12.8V)
    percentage: float        # Процент заряда аккумулятора (0-100%)
    current_amps: float = 0.0 # Потребляемый ток всей системой (Амперы)
    is_low: bool = False     # Флаг критического разряда (< 11.2V)


@dataclass
class MotorTelemetry:
    """Телеметрия приводов и драйвера VNH2SP30"""
    left_pwm: int = 0                  # ШИМ левого мотора (-255..255)
    right_pwm: int = 0                 # ШИМ правого мотора (-255..255)
    left_current_amps: float = 0.0     # Ток левого H-моста по датчику CS (А)
    right_current_amps: float = 0.0    # Ток правого H-моста по датчику CS (А)
    left_encoder_ticks: int = 0        # Тики энкодера левого колеса
    right_encoder_ticks: int = 0       # Тики энкодера правого колеса
    driver_temperature_c: float = 25.0 # Температура чипов VNH2SP30 (°C)


@dataclass
class ImuTelemetry:
    """Телеметрия ориентации (гироскоп/акселерометр)"""
    roll: float = 0.0    # Крен в радианах
    pitch: float = 0.0   # Тангаж в радианах
    yaw: float = 0.0     # Рыскание (курс) в радианах [-pi..pi]
    gyro_z: float = 0.0  # Угловая скорость поворота (рад/с)
    accel_x: float = 0.0 # Продольное ускорение (м/с^2)
    accel_y: float = 0.0 # Поперечное ускорение (м/с^2)


@dataclass
class PoseTelemetry:
    """Одометрия робота в локальной системе координат"""
    x: float = 0.0
    y: float = 0.0
    yaw: float = 0.0
    linear_velocity: float = 0.0
    angular_velocity: float = 0.0


@dataclass
class LidarScan:
    """Скан RPLIDAR A1M8 (360 лучей)"""
    ranges: List[float]
    intensities: Optional[List[int]] = None
    timestamp: float = field(default_factory=time.time)
    angle_min: float = 0.0           # Начальный угол (0 рад)
    angle_max: float = 6.283185      # Конечный угол (2*pi рад = 360°)
    angle_increment: float = 0.017453# Шаг 1 градус
    range_min: float = 0.15          # Минимальная дистанция RPLidar A1 (0.15 м)
    range_max: float = 12.0          # Максимальная дистанция RPLidar A1 (12.0 м)


@dataclass
class UltrasonicSensors:
    """Дополнительные датчики препятствий (HC-SR04 / индуктивные)"""
    front_center_m: float = 2.0
    front_left_m: float = 2.0
    front_right_m: float = 2.0


@dataclass
class RobotStatus:
    """Общий статус платформы"""
    mode: str = "mock"
    emergency_stop: bool = False
    motors_enabled: bool = True
    connection_alive: bool = True
    connected: bool = True


@dataclass
class FullTelemetryMessage:
    """Полный пакет телеметрии, отправляемый в веб-пульт и плагины"""
    battery: BatteryTelemetry
    motors: MotorTelemetry
    imu: ImuTelemetry
    pose: PoseTelemetry
    lidar: LidarScan
    ultrasonic: UltrasonicSensors
    status: RobotStatus
    timestamp: float = field(default_factory=time.time)

    def to_dict(self):
        return asdict(self)


@dataclass
class DriveCommand:
    """Входящая команда управления движением"""
    linear: float = 0.0          # Линейная скорость, м/с (-1.5..1.5)
    angular: float = 0.0         # Угловая скорость, рад/с (-3.0..3.0)
    emergency_stop: Optional[bool] = None
