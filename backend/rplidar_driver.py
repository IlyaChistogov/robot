"""
Драйвер лидара Slamtec RPLIDAR A1M8 по UART/Serial.
Не требует сторонних библиотек кроме pyserial.
Реализует парсинг бинарного протокола Slamtec:
- Синхробайты 0xA5, 0x5A
- Управление питанием мотора через DTR (CP2102)
- Потоковое чтение 5-байтных пакетов измерений
- Формирование 360-градусного массива расстояний (1 луч на градус)
"""

from __future__ import annotations
import threading
import time
from typing import Optional, List, Tuple

try:
    import serial
except ImportError:
    serial = None

_CMD_SCAN = 0x20
_CMD_STOP = 0x25
_SYNC = 0xA5


def parse_measurement(data: bytes) -> Optional[Tuple[bool, int, float, float]]:
    """
    Разбор 5-байтного пакета измерения Slamtec RPLIDAR A1.
    Байт 0: [quality (6 бит), !S (1 бит), S (1 бит)]
    Байт 1: [angle_q6[6:0] (7 бит), check_bit=1 (1 бит)]
    Байт 2: [angle_q6[14:7] (8 бит)]
    Байт 3: [distance_q2[7:0] (8 бит)]
    Байт 4: [distance_q2[15:8] (8 бит)]
    Возвращает (new_scan, quality, angle_deg, distance_m) или None при ошибке.
    """
    if len(data) < 5:
        return None

    b0 = data[0]
    b1 = data[1]
    b2 = data[2]
    b3 = data[3]
    b4 = data[4]

    new_scan = bool(b0 & 0x01)
    inv_new_scan = bool((b0 >> 1) & 0x01)
    if new_scan == inv_new_scan:
        return None  # Флаги нового скана обязаны быть инверсными

    check_bit = b1 & 0x01
    if check_bit != 1:
        return None  # Check-бит (бит 0 байта 1) обязан быть равен 1

    quality = b0 >> 2
    angle_q6 = (b1 >> 1) | (b2 << 7)
    angle_deg = angle_q6 / 64.0
    distance_m = (b3 | (b4 << 8)) / 4.0 / 1000.0
    return (new_scan, quality, angle_deg, distance_m)


class RPLidarA1Driver:
    """
    Драйвер лидара RPLIDAR A1M8.
    Фоновый поток считывает точки, а метод get_360_ranges() возвращает 360 расстояний.
    """
    def __init__(
        self,
        port: str = "/dev/ttyUSB0",
        baudrate: int = 115200,
        max_distance: float = 12.0,
        min_quality: int = 2,
        serial_obj=None
    ):
        self.max_range = max_distance
        self.min_quality = min_quality
        self.port = port
        self.baudrate = baudrate

        if serial is None and serial_obj is None:
            raise RuntimeError("Для работы с реальным лидаром требуется pyserial: pip install pyserial")

        self._ser = serial_obj if serial_obj is not None else serial.Serial(
            port, baudrate, timeout=0.1, dsrdtr=False, rtscts=False
        )

        self._lock = threading.Lock()
        self._rx = bytearray()
        self._current_points: List[Tuple[float, float]] = []
        self._latest_points: List[Tuple[float, float]] = []
        self._ranges_360: List[float] = [12.0] * 360
        self._running = False
        self._reader: Optional[threading.Thread] = None

        # Включаем питание мотора на адаптере CP2102 (DTR=False)
        self.start_motor()

        # Очистка буфера порта
        try:
            self._send(_CMD_STOP)
            time.sleep(0.05)
            self._ser.reset_input_buffer()
        except Exception:
            pass

    def start_motor(self):
        """Включает мотор лидара через DTR сигнал CP2102."""
        if self._ser is not None:
            try:
                self._ser.dtr = False
                self._ser.rts = False
            except Exception:
                pass

    def stop_motor(self):
        """Останавливает мотор лидара через DTR сигнал CP2102."""
        if self._ser is not None:
            try:
                self._ser.dtr = True
                self._ser.rts = True
            except Exception:
                pass

    def _send(self, cmd: int):
        self._ser.write(bytes([_SYNC, cmd]))

    def start(self):
        if self._running:
            return

        # 1. Запуск мотора
        self.start_motor()
        # 2. Даем время мотору раскрутиться до рабочей скорости (~5-10 Гц)
        time.sleep(0.5)

        self._ser.reset_input_buffer()
        self._send(_CMD_SCAN)

        # Ожидаем ответный дескриптор пакета (7 байт): A5 5A 05 00 00 40 81
        desc = self._ser.read(7)
        if len(desc) < 7 or desc[0] != _SYNC or desc[1] != 0x5A:
            # Попробуем еще одну попытку после короткой паузы
            time.sleep(0.1)
            desc = self._ser.read(7)
            if len(desc) < 7 or desc[0] != _SYNC or desc[1] != 0x5A:
                raise RuntimeError(f"RPLIDAR на порту {self.port} не ответил на команду SCAN.")

        self._running = True
        self._reader = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader.start()

    def stop(self):
        self._running = False
        if self._reader:
            self._reader.join(timeout=1.0)
            self._reader = None
        try:
            self._send(_CMD_STOP)
            time.sleep(0.02)
        except Exception:
            pass
        self.stop_motor()

    def _reader_loop(self):
        while self._running:
            try:
                chunk = self._ser.read(512)
            except Exception:
                break

            if not chunk:
                continue

            with self._lock:
                self._rx += chunk
                # Ограничиваем буфер, чтобы данные не запаздывали
                if len(self._rx) > 4096:
                    del self._rx[:len(self._rx) - 4096]

                while len(self._rx) >= 5:
                    parsed = parse_measurement(bytes(self._rx[:5]))
                    if parsed is None:
                        del self._rx[0]
                        continue

                    del self._rx[:5]
                    new_scan, quality, angle, dist = parsed

                    if new_scan:
                        if self._current_points:
                            self._latest_points = self._current_points
                        self._current_points = []

                    if quality >= self.min_quality and 0.1 <= dist <= self.max_range:
                        self._current_points.append((angle, dist))
                        deg = int(round(angle)) % 360
                        self._ranges_360[deg] = round(dist, 3)

    def get_360_ranges(self) -> List[float]:
        """
        Возвращает актуальный 360-градусный массив дальностей в метрах.
        Каждый градус обновляется непрерывно по мере поступления лучей от лидара.
        """
        with self._lock:
            return list(self._ranges_360)

    def close(self):
        self.stop()
        try:
            self._ser.close()
        except Exception:
            pass
