"""
Базовый абстрактный интерфейс робота.
И симулятор (MockRobot), и драйвер реального железа (RealRobot)
реализуют этот общий класс. Благодаря этому весь внешний код
(веб-пульт, API, алгоритмы студентов) работает одинаково в обоих режимах.
"""

from abc import ABC, abstractmethod
from schemas import FullTelemetryMessage, DriveCommand


class BaseRobot(ABC):
    @abstractmethod
    def set_drive_command(self, cmd: DriveCommand) -> None:
        """Отправка команды движения (линейная, угловая скорость, e-stop)"""
        pass

    @abstractmethod
    def get_full_telemetry(self) -> FullTelemetryMessage:
        """Получение полного пакета телеметрии со всех сенсоров"""
        pass

    @abstractmethod
    def trigger_emergency_stop(self) -> None:
        """Аварийная остановка моторов (E-Stop)"""
        pass

    @abstractmethod
    def reset_emergency_stop(self) -> None:
        """Сброс аварийной остановки"""
        pass
