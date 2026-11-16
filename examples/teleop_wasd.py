"""
Управление роботом с клавиатуры в терминале (teleop_wasd.py).
Работает как в Windows, так и в Linux/macOS (через SSH на Raspberry Pi).

Управление:
  W / Стрелка Вверх    — Вперед
  S / Стрелка Вниз     — Назад
  A / Стрелка Влево    — Поворот влево
  D / Стрелка Вправо   — Поворот вправо
  Пробел               — Остановка
  E                    — Аварийный стоп (E-STOP)
  R                    — Сброс аварийного стопа
  Q / Ctrl+C           — Выход
"""

import sys
import os
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
from robot_client import RobotClient

# Кроссплатформенное считывание одиночного нажатия клавиши
if os.name == "nt":
    import msvcrt

    def get_char():
        ch = msvcrt.getch()
        if ch in (b"\x00", b"\xe0"):  # спецклавиши (стрелки)
            ch2 = msvcrt.getch()
            return f"KEY_{ord(ch2)}"
        try:
            return ch.decode("utf-8", errors="ignore").lower()
        except Exception:
            return ""
else:
    import select
    import termios
    import tty

    def get_char():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
            if rlist:
                ch = sys.stdin.read(1)
                return ch.lower()
            return ""
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def main():
    print("==================================================")
    print("      Управление роботом с клавиатуры (WASD)      ")
    print("==================================================")
    print("  W/S      — Вперед / Назад                       ")
  # A/D      — Влево / Вправо
    print("  Пробел   — Стоп                                 ")
    print("  E        — АВАРИЙНЫЙ СТОП                       ")
    print("  R        — Сброс аварийного стопа               ")
    print("  Q        — Выход                                ")
    print("==================================================")

    with RobotClient("http://127.0.0.1:5000") as robot:
        try:
            status = robot.get_status()
            print(f"Подключено! Режим: {status.get('mode', 'mock').upper()}")
        except Exception as e:
            print(f"Ошибка подключения: {e}")
            return

        lin_speed = 0.4
        ang_speed = 1.0

        current_lin = 0.0
        current_ang = 0.0

        try:
            while True:
                char = get_char()
                if not char:
                    time.sleep(0.05)
                    continue

                if char in ("q", "\x03"):  # q или Ctrl+C
                    break
                elif char in ("w", "key_72"):
                    current_lin = lin_speed
                    current_ang = 0.0
                    print("▲ Вперед", flush=True)
                elif char in ("s", "key_80"):
                    current_lin = -lin_speed
                    current_ang = 0.0
                    print("▼ Назад", flush=True)
                elif char in ("a", "key_75"):
                    current_lin = 0.0
                    current_ang = ang_speed
                    print("◄ Влево", flush=True)
                elif char in ("d", "key_77"):
                    current_lin = 0.0
                    current_ang = -ang_speed
                    print("► Вправо", flush=True)
                elif char == " ":
                    current_lin = 0.0
                    current_ang = 0.0
                    robot.stop()
                    print("⏹ Стоп", flush=True)
                elif char == "e":
                    robot.emergency_stop()
                    print("⛔ АВАРИЙНЫЙ СТОП!", flush=True)
                    continue
                elif char == "r":
                    robot.reset_emergency_stop()
                    print("✓ Сброс блокировки E-Stop", flush=True)
                    continue

                robot.drive(current_lin, current_ang)
                time.sleep(0.05)

        except KeyboardInterrupt:
            pass
        finally:
            robot.stop()
            print("\nУправление завершено. Робот остановлен.")


if __name__ == "__main__":
    main()
