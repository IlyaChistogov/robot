"""
Пример студенческого алгоритма: «Проезд квадрата и проверка одометрии» (drive_square.py).

Задача:
- Проехать квадрат 1.0 x 1.0 метр
- 4 раза: проехать 1.0 м вперед -> повернуться на 90° влево
- Сравнить начальные и конечные координаты (оценка накопленной ошибки одометрии)
"""

import sys
import os
import time

# Добавляем backend в sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
from robot_client import RobotClient


def main():
    print("==================================================")
    print("   Студенческий алгоритм: Проезд квадрата (1x1 м) ")
    print("==================================================")

    with RobotClient("http://127.0.0.1:5000") as robot:
        try:
            status = robot.get_status()
            print(f"Робот подключен! Режим: {status.get('mode', 'unknown').upper()}")
            print(f"Батарея: {status['battery']['voltage']}V ({status['battery']['percentage']}%)")
        except Exception as e:
            print(f"Ошибка подключения к серверу: {e}")
            print("Убедитесь, что запущен backend: python backend/server.py")
            return

        x0, y0, yaw0 = robot.get_pose()
        print(f"\nНачальная поза: X={x0:.3f} м, Y={y0:.3f} м, Yaw={yaw0:.1f}°")
        print("Начинаем движение по траектории квадрата...\n")

        SIDE_METERS = 1.0
        TURN_DEG = 90.0

        for side in range(1, 5):
            print(f"--- [Сторона {side}/4] ---")
            print(f"Движение вперед на {SIDE_METERS} м...")
            robot.move(distance_m=SIDE_METERS, speed=0.35, tolerance=0.03)

            x, y, yaw = robot.get_pose()
            print(f"Точка угла {side}: X={x:.3f} м, Y={y:.3f} м, Yaw={yaw:.1f}°")

            print(f"Поворот на {TURN_DEG}° влево...")
            robot.turn(angle_deg=TURN_DEG, speed=0.8, tolerance_deg=2.5)

            time.sleep(0.3)

        x_end, y_end, yaw_end = robot.get_pose()
        dx = x_end - x0
        dy = y_end - y0
        dist_error = (dx**2 + dy**2)**0.5
        yaw_error = abs(yaw_end - yaw0)
        while yaw_error > 180.0:
            yaw_error = abs(yaw_error - 360.0)

        print("\n==================================================")
        print("   Квадрат завершен! Результаты одометрии:        ")
        print(f"   Финальная поза:  X={x_end:.3f} м, Y={y_end:.3f} м, Yaw={yaw_end:.1f}°")
        print(f"   Ошибка возврата: {dist_error * 100:.1f} см")
        print(f"   Ошибка курса:    {yaw_error:.1f}°")
        print("==================================================")


if __name__ == "__main__":
    main()
