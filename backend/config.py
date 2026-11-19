"""
Файл конфигурации платформы робота.
Настроен для прямого управления с Raspberry Pi 5 (или симуляции на ПК).
"""

import os

# Режим работы: 'mock' (симулятор на ПК) или 'real' (на физическом роботе с Raspberry Pi 5)
ROBOT_MODE = os.getenv("ROBOT_MODE", "mock").lower()

# ============================================================
# Настройки Raspberry Pi 5: Прямое подключение VNH2SP30 к GPIO
# (BCM нумерация 40-пинового разъема Raspberry Pi 5)
# ============================================================
PIN_LEFT_PWM = int(os.getenv("PIN_LEFT_PWM", "12"))   # Аппаратный ШИМ GPIO12
PIN_LEFT_INA = int(os.getenv("PIN_LEFT_INA", "17"))   # Направление INA
PIN_LEFT_INB = int(os.getenv("PIN_LEFT_INB", "27"))   # Направление INB

PIN_RIGHT_PWM = int(os.getenv("PIN_RIGHT_PWM", "13")) # Аппаратный ШИМ GPIO13
PIN_RIGHT_INA = int(os.getenv("PIN_RIGHT_INA", "22")) # Направление INA
PIN_RIGHT_INB = int(os.getenv("PIN_RIGHT_INB", "23")) # Направление INB

# Пины датчиков скорости (энкодеров)
PIN_ENC_LEFT_A = int(os.getenv("PIN_ENC_LEFT_A", "24"))
PIN_ENC_LEFT_B = int(os.getenv("PIN_ENC_LEFT_B", "25"))
PIN_ENC_RIGHT_A = int(os.getenv("PIN_ENC_RIGHT_A", "5"))
PIN_ENC_RIGHT_B = int(os.getenv("PIN_ENC_RIGHT_B", "6"))

# Частота ШИМ для VNH2SP30 (в Гц, по умолчанию 10 кГц)
PWM_FREQUENCY_HZ = int(os.getenv("PWM_FREQUENCY_HZ", "10000"))

# ============================================================
# Лидар Slamtec RPLIDAR A1M8 на Raspberry Pi 5
# ============================================================
# Подключение по USB: '/dev/ttyUSB0' (Linux) или к UART GPIO14/15: '/dev/serial0'
LIDAR_SERIAL_PORT = os.getenv("LIDAR_SERIAL_PORT", "/dev/ttyUSB0")
LIDAR_BAUDRATE = 115200

# ============================================================
# Камеры (4 USB-камеры кругового обзора через хаб)
# ============================================================
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))
CAMERA_INDICES = [0, 2, 4, 6]  # Индексы видеопотоков 4 камер в /dev/video*

# Сетевые настройки
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 5000
