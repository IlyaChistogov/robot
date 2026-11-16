"""
Драйвер физического робота (RealRobot).
Реализует BaseRobot для работы с реальным оборудованием:
- Контроллер VNH2SP30 по Serial (UART)
- Лидар Slamtec RPLIDAR A1M8 по USB-UART
- Курсовая камера через OpenCV
"""

import time
import math
import threading
from typing import List, Optional
import cv2

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

try:
    import serial
except ImportError:
    serial = None


class RealRobot(BaseRobot):
    def __init__(self):
        self.is_emergency_stop = False
        self.motors_enabled = True

        # Кинематика шасси
        self.wheel_radius_m = 0.125
        self.track_width_m = 0.46
        self.max_linear_speed = 1.0
        self.ticks_per_meter = 1000

        # Состояние одометрии
        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0
        self.linear_vel = 0.0
        self.angular_vel = 0.0

        # Состояние батареи и моторов
        self.voltage = 12.6
        self.current_amps = 1.5
        self.left_pwm = 0
        self.right_pwm = 0
        self.left_ticks = 0
        self.right_ticks = 0
        self.left_current = 0.0
        self.right_current = 0.0

        # Буфер лидара (360 лучей)
        self.lidar_ranges = [12.0] * 360
        self.lidar_intensities = [0] * 360
        self.lidar_lock = threading.Lock()

        # Потоки чтения оборудования
        self.serial_conn = None
        self.running = True

        self._init_serial()
        self._init_lidar()

    def _init_serial(self):
        """Подключение к микроконтроллеру моторов VNH2SP30 по Serial"""
        if serial is None:
            print("[RealRobot] Библиотека pyserial не установлена!")
            return

        try:
            self.serial_conn = serial.Serial(
                config.MOTOR_SERIAL_PORT,
                config.MOTOR_BAUDRATE,
                timeout=0.1
            )
            print(f"[RealRobot] Контроллер моторов подключен на {config.MOTOR_SERIAL_PORT}")
            # Запуск фонового потока чтения телеметрии
            self.serial_thread = threading.Thread(target=self._read_serial_loop, daemon=True)
            self.serial_thread.start()
        except Exception as e:
            print(f"[RealRobot] Внимание: не удалось открыть {config.MOTOR_SERIAL_PORT}: {e}")

    def _read_serial_loop(self):
        """Чтение телеметрии от микроконтроллера: T <v_bat> <ticks_l> <ticks_r> <cur_l> <cur_r>"""
        last_l_ticks = 0
        last_r_ticks = 0
        last_time = time.time()

        while self.running and self.serial_conn:
            try:
                line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                if line.startswith("T "):
                    parts = line.split()
                    if len(parts) >= 6:
                        self.voltage = float(parts[1])
                        self.left_ticks = int(parts[2])
                        self.right_ticks = int(parts[3])
                        self.left_current = float(parts[4])
                        self.right_current = float(parts[5])
                        self.current_amps = 1.5 + self.left_current + self.right_current

                        # Расчет одометрии
                        now = time.time()
                        dt = now - last_time
                        if dt > 0.01:
                            dl = (self.left_ticks - last_l_ticks) / self.ticks_per_meter
                            dr = (self.right_ticks - last_r_ticks) / self.ticks_per_meter
                            dist = (dl + dr) / 2.0
                            d_yaw = (dr - dl) / self.track_width_m

                            self.yaw = (self.yaw + d_yaw + math.pi) % (2 * math.pi) - math.pi
                            self.x += dist * math.cos(self.yaw)
                            self.y += dist * math.sin(self.yaw)

                            self.linear_vel = dist / dt
                            self.angular_vel = d_yaw / dt

                            last_l_ticks = self.left_ticks
                            last_r_ticks = self.right_ticks
                            last_time = now
            except Exception:
                time.sleep(0.05)

    def _init_lidar(self):
        """Подключение к Slamtec RPLIDAR A1M8 через встроенный парсер протокола"""
        try:
            self.lidar = RPLidarA1Driver(port=config.LIDAR_SERIAL_PORT, baudrate=config.LIDAR_BAUDRATE)
            self.lidar.start()
            print(f"[RealRobot] RPLIDAR A1M8 успешно подключен на {config.LIDAR_SERIAL_PORT}")
            self.lidar_thread = threading.Thread(target=self._lidar_scan_loop, daemon=True)
            self.lidar_thread.start()
        except Exception as e:
            print(f"[RealRobot] Лидар A1M8 не инициализирован ({e}). Ожидание подключения...")

    def _lidar_scan_loop(self):
        """Фоновый сбор 360-градусного скана с RPLIDAR A1M8"""
        while self.running:
            try:
                ranges = self.lidar.get_360_ranges()
                with self.lidar_lock:
                    self.lidar_ranges = ranges
                time.sleep(0.1)
            except Exception as e:
                time.sleep(0.5)

    def set_drive_command(self, cmd: DriveCommand) -> None:
        """Перевод скоростей (v, w) в ШИМ VNH2SP30 и отправка в Serial"""
        if cmd.emergency_stop is not None:
            self.is_emergency_stop = cmd.emergency_stop

        if self.is_emergency_stop:
            self.trigger_emergency_stop()
            return

        # Дифференциальная кинематика
        v_left = cmd.linear - (cmd.angular * self.track_width_m / 2.0)
        v_right = cmd.linear + (cmd.angular * self.track_width_m / 2.0)

        # Конвертация в ШИМ (-255..+255)
        self.left_pwm = int(max(-255, min(255, (v_left / self.max_linear_speed) * 255)))
        self.right_pwm = int(max(-255, min(255, (v_right / self.max_linear_speed) * 255)))

        if self.serial_conn and self.serial_conn.is_open:
            cmd_str = f"M {self.left_pwm} {self.right_pwm}\n"
            try:
                self.serial_conn.write(cmd_str.encode('ascii'))
            except Exception as e:
                print(f"[RealRobot] Ошибка отправки команды: {e}")

    def trigger_emergency_stop(self) -> None:
        """Экстренная остановка моторов (E-Stop)"""
        self.is_emergency_stop = True
        self.left_pwm = 0
        self.right_pwm = 0
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.write(b"STOP\n")
            except Exception:
                pass

    def reset_emergency_stop(self) -> None:
        self.is_emergency_stop = False

    def get_full_telemetry(self) -> FullTelemetryMessage:
        pct = max(0.0, min(100.0, ((self.voltage - 10.8) / (12.7 - 10.8)) * 100.0))

        with self.lidar_lock:
            current_ranges = list(self.lidar_ranges)
            current_intensities = list(self.lidar_intensities)

        front_center = current_ranges[0]
        front_left = current_ranges[30]
        front_right = current_ranges[330]

        return FullTelemetryMessage(
            timestamp=time.time(),
            battery=BatteryTelemetry(
                voltage=round(self.voltage, 2),
                percentage=round(pct, 1),
                current_amps=round(self.current_amps, 2),
                is_low=self.voltage < 11.2
            ),
            motors=MotorTelemetry(
                left_pwm=self.left_pwm,
                right_pwm=self.right_pwm,
                left_current_amps=self.left_current,
                right_current_amps=self.right_current,
                left_encoder_ticks=self.left_ticks,
                right_encoder_ticks=self.right_ticks
            ),
            imu=ImuTelemetry(
                yaw=round(self.yaw, 3),
                gyro_z=round(self.angular_vel, 3),
                accel_x=round(self.linear_vel, 3)
            ),
            pose=PoseTelemetry(
                x=round(self.x, 3),
                y=round(self.y, 3),
                yaw=round(self.yaw, 3),
                linear_velocity=round(self.linear_vel, 2),
                angular_velocity=round(self.angular_vel, 2)
            ),
            lidar=LidarScan(
                ranges=current_ranges,
                intensities=current_intensities
            ),
            ultrasonic=UltrasonicSensors(
                front_center_m=front_center,
                front_left_m=front_left,
                front_right_m=front_right
            ),
            status=RobotStatus(
                mode="real",
                emergency_stop=self.is_emergency_stop,
                motors_enabled=self.motors_enabled and not self.is_emergency_stop,
                connection_alive=self.serial_conn is not None and self.serial_conn.is_open
            )
        )
