"""
Файл конфигурации платформы робота.
Позволяет переключаться между мок-режимом (симулятором) и реальным роботом.
"""

import os

# Режим работы: 'mock' (симулятор на ПК) или 'real' (на физическом роботе с Raspberry Pi)
ROBOT_MODE = os.getenv("ROBOT_MODE", "mock").lower()

# Порт подключения к микроконтроллеру моторов VNH2SP30
# В Linux/Raspberry Pi: '/dev/ttyUSB0' или '/dev/ttyACM0'
# В Windows: 'COM3', 'COM4'
MOTOR_SERIAL_PORT = os.getenv("MOTOR_SERIAL_PORT", "/dev/ttyUSB0")
MOTOR_BAUDRATE = 115200

# Порт подключения лидара Slamtec RPLIDAR A1M8
# В Linux/Raspberry Pi: '/dev/ttyUSB1'
# В Windows: 'COM5'
LIDAR_SERIAL_PORT = os.getenv("LIDAR_SERIAL_PORT", "/dev/ttyUSB1")
LIDAR_BAUDRATE = 115200

# Индекс курсовой камеры (0 - встроенная веб-камера или первая USB-камера)
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))

# Сетевые настройки
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 5000
