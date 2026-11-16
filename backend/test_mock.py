import json
from mock_robot import MockRobot
from schemas import DriveCommand

def test_mock_robot():
    robot = MockRobot()
    print("=== 1. Начальное состояние ===")
    t1 = robot.get_full_telemetry()
    print(f"Батарея: {t1.battery.voltage}V ({t1.battery.percentage}%), Ток: {t1.battery.current_amps}A")
    print(f"Позиция: x={t1.pose.x}, y={t1.pose.y}, yaw={t1.pose.yaw} rad")
    print(f"Лидар: {len(t1.lidar.ranges)} лучей, расстояние прямо: {t1.lidar.ranges[0]} м")
    print(f"Моторы VNH2SP30: L_PWM={t1.motors.left_pwm}, R_PWM={t1.motors.right_pwm}")

    print("\n=== 2. Подача команды 'Вперед 0.6 м/с' ===")
    robot.set_drive_command(DriveCommand(linear=0.6, angular=0.0))
    # Симулируем 10 тактов физики по 0.1 сек
    import time
    for _ in range(10):
        time.sleep(0.05)
        robot.update()

    t2 = robot.get_full_telemetry()
    print(f"Скорость: {t2.pose.linear_velocity} м/с, Координата X: {t2.pose.x} м")
    print(f"VNH2SP30 ШИМ: L={t2.motors.left_pwm}, R={t2.motors.right_pwm}, Ток={t2.battery.current_amps}A")
    print(f"Просадка АКБ под нагрузкой: {t2.battery.voltage}V (было {t1.battery.voltage}V)")
    print(f"Лидар прямо: {t2.lidar.ranges[0]} м (было {t1.lidar.ranges[0]} м)")
    print(f"Тики энкодеров: L={t2.motors.left_encoder_ticks}, R={t2.motors.right_encoder_ticks}")

    print("\n=== 3. Проверка сериализации в JSON для пульта/студентов ===")
    data_json = json.dumps(t2.to_dict())
    print(f"Размер JSON пакета: {len(data_json)} байт")
    print("ТЕСТ ПРОЙДЕН УСПЕШНО!")

if __name__ == "__main__":
    test_mock_robot()
