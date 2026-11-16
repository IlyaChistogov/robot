"""
Пример студенческого алгоритма: «Непрерывный автопилот объезда препятствий» (avoid_obstacles.py).

Логика:
1. Постоянно сканирует 3 сектора лидара:
   - Впереди (-25°..+25°)
   - Слева (+30°..+80°)
   - Справа (-80°..-30°)
2. Если впереди свободно (> 0.7 м) — едет вперед с максимальной крейсерской скоростью.
3. Если впереди препятствие:
   - Сравнивает свободное пространство слева и справа
   - Поворачивает в сторону с большим свободным расстоянием
4. Если препятствие критически близко (< 0.35 м) — делает реверс (задний ход) и экстренный разворот.
5. Работает бесконечно до нажатия Ctrl+C или кнопки E-STOP на пульте.
"""

import sys
import os
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
from robot_client import RobotClient


def main():
    print("==================================================")
    print("    Интеллектуальный автопилот объезда стен       ")
    print("      (Для остановки нажмите Ctrl + C)            ")
    print("==================================================")

    with RobotClient("http://127.0.0.1:5000") as robot:
        try:
            status = robot.get_status()
            print(f"Связь установлена. Режим: {status.get('mode', 'mock').upper()}")
            print(f"Батарея: {status['battery']['voltage']}V")
        except Exception as e:
            print(f"Ошибка подключения: {e}")
            return

        CRITICAL_DIST = 0.35  # Экстренное торможение и реверс (м)
        SLOWDOWN_DIST = 0.75  # Дистанция замедления и начала поворота (м)

        step_count = 0

        try:
            while True:
                step_count += 1
                # Считываем дистанции в трех ключевых секторах
                d_front = robot.sector_distance(center_deg=0.0, span_deg=45.0)
                d_left = robot.sector_distance(center_deg=60.0, span_deg=50.0)
                d_right = robot.sector_distance(center_deg=-60.0, span_deg=50.0)

                # Телеметрия позиции
                x, y, yaw = robot.get_pose()

                if d_front < CRITICAL_DIST:
                    # Опасность: препятствие в упор
                    print(f"[{step_count:04d}] ТУПИК! Впереди: {d_front:.2f}м | Сдаем назад и разворачиваемся")
                    robot.drive(linear=-0.25, angular=1.2)
                    time.sleep(0.4)
                elif d_front < SLOWDOWN_DIST:
                    # Препятствие впереди: выбираем более свободную сторону
                    if d_left >= d_right:
                        turn_dir = 1.0  # поворот влево
                        side_name = "ВЛЕВО"
                    else:
                        turn_dir = -1.0 # поворот вправо
                        side_name = "ВПРАВО"

                    print(f"[{step_count:04d}] Препятствие ({d_front:.2f}м) -> Отворот {side_name} (Л:{d_left:.2f}м, П:{d_right:.2f}м)")
                    robot.drive(linear=0.1, angular=turn_dir * 1.0)
                else:
                    # Путь свободен: плавное прямолинейное движение
                    if step_count % 5 == 0:
                        print(f"[{step_count:04d}] Путь свободен ({d_front:.2f}м) | Поза: X={x:.2f}, Y={y:.2f}, Курс={yaw:.1f}°")
                    robot.drive(linear=0.45, angular=0.0)

                time.sleep(0.1)

        except KeyboardInterrupt:
            print("\nАвтопилот остановлен оператором (Ctrl+C).")
        finally:
            robot.stop()
            print("Моторы отключены.")


if __name__ == "__main__":
    main()
