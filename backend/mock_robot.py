"""
Модель виртуального робота (Mock Robot Simulator).
Реалистично моделирует:
- Двухканальный H-мост VNH2SP30 и кинематику 2 ведущих колес
- Автомобильный свинцово-кислотный аккумулятор 12В (просадка под нагрузкой)
- Лидар Slamtec RPLIDAR A1M8 (расчет лучей raycasting в виртуальной комнате 10х10м с препятствиями)
- Показания IMU (рыскание, ускорение, вибрация при движении)
- Энкодеры колес и ультразвуковые датчики
"""

import math
import random
import time
from typing import List, Tuple
from schemas import (
    BatteryTelemetry,
    MotorTelemetry,
    ImuTelemetry,
    PoseTelemetry,
    LidarScan,
    UltrasonicSensors,
    RobotStatus,
    FullTelemetryMessage,
    DriveCommand
)
from base_robot import BaseRobot
from geometry import Pose, integrate_unicycle


class MockRobot(BaseRobot):
    def __init__(self):
        # Параметры шасси (по фото платформы)
        self.wheel_radius_m = 0.125       # Радиус колес ~12.5 см (диаметр 25 см)
        self.track_width_m = 0.46         # Колея ~46 см
        self.max_linear_speed = 1.0       # Максимальная скорость м/с
        self.max_angular_speed = 2.0      # Максимальная угловая скорость рад/с
        self.encoder_ticks_per_meter = 1000  # Разрешение энкодера (импульсов на метр)

        # Состояние одометрии (в метрах и радианах)
        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0                    # Угол курса (-pi..pi)
        self.current_linear_vel = 0.0     # Текущая линейная скорость
        self.current_angular_vel = 0.0    # Текущая угловая скорость

        # Целевые скорости (из команд)
        self.target_linear_vel = 0.0
        self.target_angular_vel = 0.0

        # Состояние приводов и энкодеров
        self.left_pwm = 0
        self.right_pwm = 0
        self.left_ticks = 0
        self.right_ticks = 0
        self.driver_temp = 28.0           # Температура VNH2SP30

        # Автомобильный аккумулятор 12В (свинцово-кислотный)
        self.battery_capacity_ah = 60.0   # 60 А*ч
        self.open_circuit_voltage = 12.65 # ЭДС разомкнутой цепи (100% ~ 12.7V, 0% ~ 10.8V)
        self.internal_resistance = 0.04   # Внутреннее сопротивление АКБ (Ом)

        # Статус
        self.is_emergency_stop = False
        self.motors_enabled = True
        self.last_update_time = time.time()
        self.last_cmd_time = time.time()
        self.watchdog_timeout = 1.0       # Если 1 сек нет команд - стоп

        # Виртуальная комната (препятствия для RPLidar A1M8)
        # Отрезки стен [ (x1, y1, x2, y2), ... ]
        self.walls: List[Tuple[float, float, float, float]] = [
            # Внешние стены комнаты 10x10 м (от -5 до +5)
            (-5.0, -5.0, 5.0, -5.0),
            (5.0, -5.0, 5.0, 5.0),
            (5.0, 5.0, -5.0, 5.0),
            (-5.0, 5.0, -5.0, -5.0),
            # Колонны и внутренние препятствия
            (-1.5, -1.5, -0.5, -1.5),
            (-0.5, -1.5, -0.5, -0.5),
            (-0.5, -0.5, -1.5, -0.5),
            (-1.5, -0.5, -1.5, -1.5),

            (2.0, 1.0, 3.5, 1.0),
            (3.5, 1.0, 3.5, 2.5),
            (3.5, 2.5, 2.0, 2.5),
            (2.0, 2.5, 2.0, 1.0),

            (-2.5, 2.0, -1.0, 3.5),
        ]

    def set_drive_command(self, cmd: DriveCommand):
        """Прием команды движения от пульта или алгоритма"""
        self.last_cmd_time = time.time()
        if cmd.emergency_stop is not None:
            self.is_emergency_stop = cmd.emergency_stop

        if self.is_emergency_stop:
            self.target_linear_vel = 0.0
            self.target_angular_vel = 0.0
            return

        self.target_linear_vel = max(-self.max_linear_speed, min(self.max_linear_speed, cmd.linear))
        self.target_angular_vel = max(-self.max_angular_speed, min(self.max_angular_speed, cmd.angular))

    def trigger_emergency_stop(self) -> None:
        """Аварийная остановка моторов (E-Stop)"""
        self.is_emergency_stop = True
        self.target_linear_vel = 0.0
        self.target_angular_vel = 0.0
        self.current_linear_vel = 0.0
        self.current_angular_vel = 0.0
        self.left_pwm = 0
        self.right_pwm = 0

    def reset_emergency_stop(self) -> None:
        """Сброс аварийной остановки"""
        self.is_emergency_stop = False

    def update(self):
        """Один такт симуляции физики"""
        now = time.time()
        dt = now - self.last_update_time
        if dt <= 0.0:
            return
        self.last_update_time = now

        # Сторожевой таймер (Watchdog): обрыв связи останавливает робота
        if now - self.last_cmd_time > self.watchdog_timeout:
            self.target_linear_vel = 0.0
            self.target_angular_vel = 0.0

        # Моделирование инерции мощных червячных моторов (плавный разгон)
        acceleration_rate = 1.5 * dt  # м/с^2
        angular_accel_rate = 3.0 * dt # рад/с^2

        if self.is_emergency_stop:
            # Мгновенная блокировка H-моста при E-Stop
            self.current_linear_vel = 0.0
            self.current_angular_vel = 0.0
        else:
            # Линейное приближение к целевой скорости
            d_lin = self.target_linear_vel - self.current_linear_vel
            if abs(d_lin) < acceleration_rate:
                self.current_linear_vel = self.target_linear_vel
            else:
                self.current_linear_vel += math.copysign(acceleration_rate, d_lin)

            d_ang = self.target_angular_vel - self.current_angular_vel
            if abs(d_ang) < angular_accel_rate:
                self.current_angular_vel = self.target_angular_vel
            else:
                self.current_angular_vel += math.copysign(angular_accel_rate, d_ang)

        # Расчет скоростей левого и правого колес (дифференциальная кинематика)
        v_left = self.current_linear_vel - (self.current_angular_vel * self.track_width_m / 2.0)
        v_right = self.current_linear_vel + (self.current_angular_vel * self.track_width_m / 2.0)

        # Расчет ШИМ для VNH2SP30 (-255..+255)
        self.left_pwm = int(max(-255, min(255, (v_left / self.max_linear_speed) * 255)))
        self.right_pwm = int(max(-255, min(255, (v_right / self.max_linear_speed) * 255)))

        # Обновление одометрии (точное дуговое интегрирование unicycle)
        current_pose = Pose(self.x, self.y, self.yaw)
        new_pose = integrate_unicycle(current_pose, self.current_linear_vel, self.current_angular_vel, dt)
        self.x, self.y, self.yaw = new_pose.x, new_pose.y, new_pose.theta

        # Наращивание тиков энкодеров
        self.left_ticks += int(v_left * dt * self.encoder_ticks_per_meter)
        self.right_ticks += int(v_right * dt * self.encoder_ticks_per_meter)

        # Нагрев драйвера моторов под током
        total_motor_effort = (abs(self.left_pwm) + abs(self.right_pwm)) / 510.0
        self.driver_temp += (total_motor_effort * 2.5 - (self.driver_temp - 25.0) * 0.05) * dt

        # Медленный естественный разряд батареи при работе
        self.open_circuit_voltage -= 0.00002 * dt

    def _get_battery_telemetry(self) -> BatteryTelemetry:
        """Моделирование свинцового 12В аккумулятора с просадкой под нагрузкой"""
        # Ток потребления электроники (Raspberry Pi, лидар, датчики) ~ 1.5 А
        base_current = 1.5
        # Ток DC-моторов пропорционален ШИМ
        motor_current = (abs(self.left_pwm) / 255.0 + abs(self.right_pwm) / 255.0) * 8.0
        total_current = base_current + motor_current + random.uniform(-0.1, 0.1)

        # Просадка напряжения V = E - I * R_int
        loaded_voltage = self.open_circuit_voltage - (total_current * self.internal_resistance)
        loaded_voltage = max(10.0, min(13.2, loaded_voltage))

        # Расчет процента емкости (12.7V = 100%, 10.8V = 0%)
        pct = max(0.0, min(100.0, ((self.open_circuit_voltage - 10.8) / (12.7 - 10.8)) * 100.0))

        return BatteryTelemetry(
            voltage=round(loaded_voltage, 2),
            percentage=round(pct, 1),
            current_amps=round(total_current, 2),
            is_low=loaded_voltage < 11.2
        )

    def _get_imu_telemetry(self) -> ImuTelemetry:
        """Показания IMU с физическим шумом и вибрацией от моторов"""
        is_moving = abs(self.current_linear_vel) > 0.01 or abs(self.current_angular_vel) > 0.01
        vibration = 0.02 if is_moving else 0.002

        roll = random.gauss(0.0, vibration)
        # Наклон вперед/назад при ускорении
        accel_x = (self.target_linear_vel - self.current_linear_vel) * 2.0
        pitch = accel_x * 0.03 + random.gauss(0.0, vibration)

        return ImuTelemetry(
            roll=round(roll, 4),
            pitch=round(pitch, 4),
            yaw=round(self.yaw, 4),
            gyro_z=round(self.current_angular_vel + random.gauss(0.0, 0.01), 4),
            accel_x=round(accel_x + random.gauss(0.0, 0.05), 3),
            accel_y=round(random.gauss(0.0, 0.05), 3)
        )

    def _ray_wall_intersect(self, ox: float, oy: float, angle: float, wall: Tuple[float, float, float, float]) -> float:
        """Пересечение луча (ox, oy, angle) с отрезком стены (x1, y1, x2, y2)"""
        x1, y1, x2, y2 = wall
        dx = math.cos(angle)
        dy = math.sin(angle)

        denom = (y2 - y1) * dx - (x2 - x1) * dy
        if abs(denom) < 1e-9:
            return 999.0

        t = ((x2 - x1) * (oy - y1) - (y2 - y1) * (ox - x1)) / denom
        u = (dx * (oy - y1) - dy * (ox - x1)) / denom

        if t > 0.0 and 0.0 <= u <= 1.0:
            return t
        return 999.0

    def _get_lidar_scan(self) -> LidarScan:
        """Эмуляция сканирования Slamtec RPLIDAR A1M8 (360 лучей, 0.15 - 12м)"""
        ranges: List[float] = []
        intensities: List[int] = []

        ox, oy = self.x, self.y
        base_yaw = self.yaw

        for deg in range(360):
            rad = math.radians(deg)
            world_angle = base_yaw + rad

            min_dist = 12.0  # RPLidar A1 max range
            for wall in self.walls:
                dist = self._ray_wall_intersect(ox, oy, world_angle, wall)
                if dist < min_dist:
                    min_dist = dist

            # Добавляем аппаратный шум A1M8 (~1-2 см)
            if min_dist < 12.0:
                dist_with_noise = min_dist + random.gauss(0.0, 0.015)
                # Ограничение по минимальной зоне слепоты лидара (15 см)
                dist_final = max(0.15, min(12.0, dist_with_noise))
                intensity = int(min(47, max(15, 47 - dist_final * 2.5)))
            else:
                dist_final = 12.0
                intensity = 0

            ranges.append(round(dist_final, 3))
            intensities.append(intensity)

        return LidarScan(
            ranges=ranges,
            intensities=intensities
        )

    def get_full_telemetry(self) -> FullTelemetryMessage:
        """Сборка полного пакета телеметрии"""
        self.update()

        lidar = self._get_lidar_scan()
        # Быстрые данные по фронтальным дальномерам из скана лидара
        # луч 0 - центр, луч 30 - слева, луч 330 (-30) - справа
        front_center = lidar.ranges[0]
        front_left = lidar.ranges[30]
        front_right = lidar.ranges[330]

        return FullTelemetryMessage(
            timestamp=time.time(),
            battery=self._get_battery_telemetry(),
            motors=MotorTelemetry(
                left_pwm=self.left_pwm,
                right_pwm=self.right_pwm,
                left_current_amps=round((abs(self.left_pwm) / 255.0) * 8.0, 2),
                right_current_amps=round((abs(self.right_pwm) / 255.0) * 8.0, 2),
                left_encoder_ticks=self.left_ticks,
                right_encoder_ticks=self.right_ticks,
                driver_temperature_c=round(self.driver_temp, 1)
            ),
            imu=self._get_imu_telemetry(),
            pose=PoseTelemetry(
                x=round(self.x, 3),
                y=round(self.y, 3),
                yaw=round(self.yaw, 3),
                linear_velocity=round(self.current_linear_vel, 2),
                angular_velocity=round(self.current_angular_vel, 2)
            ),
            lidar=lidar,
            ultrasonic=UltrasonicSensors(
                front_center_m=front_center,
                front_left_m=front_left,
                front_right_m=front_right
            ),
            status=RobotStatus(
                mode="mock",
                emergency_stop=self.is_emergency_stop,
                motors_enabled=self.motors_enabled and not self.is_emergency_stop,
                connection_alive=True
            )
        )
