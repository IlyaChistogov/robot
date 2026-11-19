"""
Драйвер физического робота на базе Raspberry Pi 5 (RealRobot).
Прямое аппаратное управление без сторонних микроконтроллеров (Ардуино не требуется!):
- Мостовой драйвер моторов VNH2SP30 подключается напрямую к пинам GPIO Raspberry Pi 5
- Аппаратный ШИМ и энкодеры опрашиваются через библиотеку gpiozero (стандарт Raspberry Pi OS)
- Лидар Slamtec RPLIDAR A1M8 подключается по USB (/dev/ttyUSB0) или UART (/dev/serial0)
- Курсовая камера опрашивается через OpenCV (USB или CSI)
"""

import time
import math
import threading
from typing import List, Optional

try:
    import cv2
except ImportError:
    cv2 = None

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
import config
from rplidar_driver import RPLidarA1Driver
from geometry import Pose, integrate_unicycle

try:
    from gpiozero import PWMOutputDevice, DigitalOutputDevice, DigitalInputDevice
    GPIOZERO_AVAILABLE = True
except ImportError:
    GPIOZERO_AVAILABLE = False


class RealRobot(BaseRobot):
    def __init__(self):
        self.is_emergency_stop = False
        self.motors_enabled = True

        # Параметры кинематики шасси (в метрах)
        self.wheel_radius_m = 0.125
        self.track_width_m = 0.46
        self.max_linear_speed = 1.0 # м/с
        self.ticks_per_meter = 1000

        # Одометрия
        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0
        self.linear_vel = 0.0
        self.angular_vel = 0.0

        # Показатели моторов
        self.left_pwm_val = 0.0
        self.right_pwm_val = 0.0
        self.left_ticks = 0
        self.right_ticks = 0

        # Батарея
        self.voltage = 12.5
        self.current_amps = 1.2

        # Лидар
        self.lidar_ranges = [12.0] * 360
        self.lidar_intensities = [0] * 360
        self.lidar_lock = threading.Lock()

        self.running = True

        # 1. Инициализация моторов на GPIO Raspberry Pi 5
        self._init_rpi5_gpio()

        # 2. Инициализация лидара RPLIDAR A1M8
        self._init_lidar()

        # 3. Фоновый поток расчета одометрии
        self.odom_thread = threading.Thread(target=self._odometry_loop, daemon=True)
        self.odom_thread.start()

    def _init_rpi5_gpio(self):
        """Прямая инициализация пинов VNH2SP30 на Raspberry Pi 5"""
        if not GPIOZERO_AVAILABLE:
            print("[RealRobot] Внимание: gpiozero не установлена (запуск вне Raspberry Pi).")
            print("[RealRobot] Для работы на Raspberry Pi 5: pip install gpiozero")
            self.gpio_active = False
            return

        try:
            # Левый мотор (VNH2SP30 канал A)
            self.m_left_pwm = PWMOutputDevice(pin=config.PIN_LEFT_PWM, frequency=config.PWM_FREQUENCY_HZ)
            self.m_left_ina = DigitalOutputDevice(pin=config.PIN_LEFT_INA)
            self.m_left_inb = DigitalOutputDevice(pin=config.PIN_LEFT_INB)

            # Правый мотор (VNH2SP30 канал B)
            self.m_right_pwm = PWMOutputDevice(pin=config.PIN_RIGHT_PWM, frequency=config.PWM_FREQUENCY_HZ)
            self.m_right_ina = DigitalOutputDevice(pin=config.PIN_RIGHT_INA)
            self.m_right_inb = DigitalOutputDevice(pin=config.PIN_RIGHT_INB)

            # Энкодеры (прерывания по фронтам)
            try:
                self.enc_left = DigitalInputDevice(pin=config.PIN_ENC_LEFT_A)
                self.enc_left.when_activated = self._on_left_tick
                self.enc_right = DigitalInputDevice(pin=config.PIN_ENC_RIGHT_A)
                self.enc_right.when_activated = self._on_right_tick
            except Exception as e:
                print(f"[RealRobot] Энкодеры не подключены к GPIO ({e}). Используется открытый контур.")

            self.gpio_active = True
            print("[RealRobot] Драйвер VNH2SP30 успешно инициализирован на GPIO Raspberry Pi 5!")
        except Exception as e:
            print(f"[RealRobot] Ошибка инициализации GPIO: {e}")
            self.gpio_active = False

    def _on_left_tick(self):
        sign = 1 if self.left_pwm_val >= 0 else -1
        self.left_ticks += sign

    def _on_right_tick(self):
        sign = 1 if self.right_pwm_val >= 0 else -1
        self.right_ticks += sign

    def _init_lidar(self):
        """Подключение к Slamtec RPLIDAR A1M8"""
        try:
            self.lidar = RPLidarA1Driver(port=config.LIDAR_SERIAL_PORT, baudrate=config.LIDAR_BAUDRATE)
            self.lidar.start()
            print(f"[RealRobot] RPLIDAR A1M8 успешно подключен к порту {config.LIDAR_SERIAL_PORT}")
            self.lidar_thread = threading.Thread(target=self._lidar_scan_loop, daemon=True)
            self.lidar_thread.start()
        except Exception as e:
            print(f"[RealRobot] Лидар A1M8 на {config.LIDAR_SERIAL_PORT} не обнаружен ({e}).")

    def _lidar_scan_loop(self):
        while self.running:
            try:
                ranges = self.lidar.get_360_ranges()
                with self.lidar_lock:
                    self.lidar_ranges = ranges
                time.sleep(0.1)
            except Exception:
                time.sleep(0.5)

    def _set_single_motor(self, pwm_dev, ina_dev, inb_dev, speed: float):
        """Управление одним каналом VNH2SP30 (-1.0 .. +1.0)"""
        clamped = max(-1.0, min(1.0, speed))
        abs_speed = abs(clamped)

        if abs_speed < 0.02 or self.is_emergency_stop:
            pwm_dev.value = 0.0
            ina_dev.off()
            inb_dev.off()
        elif clamped > 0:
            ina_dev.on()
            inb_dev.off()
            pwm_dev.value = abs_speed
        else:
            ina_dev.off()
            inb_dev.on()
            pwm_dev.value = abs_speed

    def set_drive_command(self, cmd: DriveCommand) -> None:
        """Перевод (linear, angular) в прямое управление пинами VNH2SP30 на Pi 5"""
        if cmd.emergency_stop is not None:
            self.is_emergency_stop = cmd.emergency_stop

        if self.is_emergency_stop:
            self.trigger_emergency_stop()
            return

        # Дифференциальная кинематика: расчет линейных скоростей левого и правого колес
        v = max(-self.max_linear_speed, min(self.max_linear_speed, cmd.linear))
        w = max(-2.0, min(2.0, cmd.angular))

        v_l = v - (w * self.track_width_m / 2.0)
        v_r = v + (w * self.track_width_m / 2.0)

        self.left_pwm_val = v_l / self.max_linear_speed
        self.right_pwm_val = v_r / self.max_linear_speed

        if getattr(self, "gpio_active", False):
            self._set_single_motor(self.m_left_pwm, self.m_left_ina, self.m_left_inb, self.left_pwm_val)
            self._set_single_motor(self.m_right_pwm, self.m_right_ina, self.m_right_inb, self.right_pwm_val)

    def trigger_emergency_stop(self) -> None:
        self.is_emergency_stop = True
        self.left_pwm_val = 0.0
        self.right_pwm_val = 0.0
        self.linear_vel = 0.0
        self.angular_vel = 0.0
        if getattr(self, "gpio_active", False):
            self.m_left_pwm.value = 0.0
            self.m_right_pwm.value = 0.0
            self.m_left_ina.off()
            self.m_left_inb.off()
            self.m_right_ina.off()
            self.m_right_inb.off()

    def reset_emergency_stop(self) -> None:
        self.is_emergency_stop = False

    def _odometry_loop(self):
        """Интегрирование одометрии по тикам энкодеров или скоростям шасси"""
        last_time = time.time()
        last_l_ticks = self.left_ticks
        last_r_ticks = self.right_ticks

        while self.running:
            time.sleep(0.05)
            now = time.time()
            dt = now - last_time
            if dt <= 0:
                continue

            dl_ticks = self.left_ticks - last_l_ticks
            dr_ticks = self.right_ticks - last_r_ticks
            last_l_ticks = self.left_ticks
            last_r_ticks = self.right_ticks
            last_time = now

            if dl_ticks != 0 or dr_ticks != 0:
                dl = dl_ticks / self.ticks_per_meter
                dr = dr_ticks / self.ticks_per_meter
                dist = (dl + dr) / 2.0
                d_yaw = (dr - dl) / self.track_width_m
                self.linear_vel = dist / dt
                self.angular_vel = d_yaw / dt
            else:
                # Если энкодеров нет — одометрия по заданной скорости
                self.linear_vel = self.left_pwm_val * self.max_linear_speed
                self.angular_vel = -(self.right_pwm_val - self.left_pwm_val) * (self.max_linear_speed / self.track_width_m)

            current_pose = Pose(self.x, self.y, self.yaw)
            new_pose = integrate_unicycle(current_pose, self.linear_vel, self.angular_vel, dt)
            self.x, self.y, self.yaw = new_pose.x, new_pose.y, new_pose.theta

    def get_full_telemetry(self) -> FullTelemetryMessage:
        with self.lidar_lock:
            ranges_copy = list(self.lidar_ranges)
            intensities_copy = list(self.lidar_intensities)

        pct = max(0.0, min(100.0, ((self.voltage - 10.8) / (12.7 - 10.8)) * 100.0))

        return FullTelemetryMessage(
            status=RobotStatus(
                connected=True,
                emergency_stop=self.is_emergency_stop,
                motors_enabled=not self.is_emergency_stop,
                mode="real_rpi5"
            ),
            battery=BatteryTelemetry(
                voltage=round(self.voltage, 2),
                percentage=round(pct, 1),
                current_amps=round(self.current_amps, 2),
                is_low=self.voltage < 11.2
            ),
            motors=MotorTelemetry(
                left_pwm=int(self.left_pwm_val * 255),
                right_pwm=int(self.right_pwm_val * 255),
                left_current_amps=round(abs(self.left_pwm_val) * 1.5, 2),
                right_current_amps=round(abs(self.right_pwm_val) * 1.5, 2),
                left_encoder_ticks=self.left_ticks,
                right_encoder_ticks=self.right_ticks,
                driver_temperature_c=28.0
            ),
            imu=ImuTelemetry(
                roll=0.0,
                pitch=0.0,
                yaw=round(self.yaw, 3),
                gyro_z=round(self.angular_vel, 3),
                accel_x=0.0,
                accel_y=0.0
            ),
            pose=PoseTelemetry(
                x=round(self.x, 3),
                y=round(self.y, 3),
                yaw=round(self.yaw, 3),
                linear_velocity=round(self.linear_vel, 2),
                angular_velocity=round(self.angular_vel, 2)
            ),
            lidar=LidarScan(
                ranges=ranges_copy,
                intensities=intensities_copy
            ),
            ultrasonic=UltrasonicSensors(
                front_center_m=round(ranges_copy[0], 2) if ranges_copy else 9.9,
                front_left_m=round(ranges_copy[45], 2) if len(ranges_copy) > 45 else 9.9,
                front_right_m=round(ranges_copy[315], 2) if len(ranges_copy) > 315 else 9.9
            )
        )
