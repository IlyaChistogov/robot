"""
Пример студенческого плагина: «Автономный объезд препятствий по лидару».
Демонстрирует работу с API робота:
1. Подключается к роботу (моку или реальному)
2. В цикле считывает расстояние с лидара RPLIDAR A1M8
3. Если впереди препятствие ближе 0.6 метра — притормаживает и поворачивает
4. Если путь свободен — плавно едет вперед
"""

import sys
import os
import time

# Добавляем путь к клиентской библиотеке
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
from robot_client import RobotClient


def run_avoidance_algorithm():
    robot = RobotClient("http://127.0.0.1:5000")
    print("=== Запуск студенческого алгоритма объезда препятствий ===")
    print("Подключение к платформе...")

    try:
        status = robot.get_status()
        print(f"Робот на связи! Батарея: {status['battery']['voltage']}V")
    except Exception as e:
        print(f"Ошибка подключения к серверу: {e}")
        print("Убедитесь, что запущен 'python backend/server.py'")
        return

    SAFE_DISTANCE_M = 0.6  # Безопасная дистанция до стены
    CRITICAL_DISTANCE_M = 0.3 # Дистанция экстренной остановки

    try:
        for step in range(30): # Тестовый прогон на 30 шагов
            front_dist = robot.get_front_distance()
            telemetry = robot.get_telemetry()
            pos = telemetry["pose"]

            print(f"[Шаг {step+1:02d}] Позиция (x={pos['x']:.2f}, y={pos['y']:.2f}), Дистанция впереди: {front_dist:.2f} м", end=" -> ")

            if front_dist < CRITICAL_DISTANCE_M:
                print("ОПАСНОСТЬ! Задний ход и резкий разворот!")
                robot.drive(linear=-0.2, angular=1.0)
            elif front_dist < SAFE_DISTANCE_M:
                print("Препятствие близко! Поворот вправо...")
                robot.drive(linear=0.0, angular=-0.8)
            else:
                print("Путь свободен, движение вперед.")
                robot.drive(linear=0.4, angular=0.0)

            time.sleep(0.2)

    except KeyboardInterrupt:
        print("\nОстановка студентом.")
    finally:
        robot.stop()
        print("Робот остановлен.")


if __name__ == "__main__":
    run_avoidance_algorithm()
