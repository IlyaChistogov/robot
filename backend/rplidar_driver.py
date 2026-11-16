"""
Драйвер лидара Slamtec RPLIDAR A1M8 по UART/Serial.
Не требует сторонних библиотек кроме pyserial.
Реализует парсинг бинарного протокола Slamtec:
- Синхробайты 0xA5, 0x5A
- Запуск/остановка вращения мотора
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
    Возвращает (new_scan, quality, angle_deg, distance_m) или None при ошибке check-бита.
    """
    if len(data) < 5:
        return None
    if not (data[1] & 0x80):
        return None  # Check-бит обязан быть равен 1

    new_scan = bool(data[0] & 0x01)
    quality = (data[0] >> 2) & 0x3F
    angle_q6 = (data[2] << 7) | (data[1] & 0x7F)
    angle_deg = angle_q6 / 64.0
    distance_m = ((data[4] << 8) | data[3]) * 0.25 / 1000.0
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
            port, baudrate, timeout=0.05, dsrdtr=False, rtscts=False
        )

        self._lock = threading.Lock()
        self._rx = bytearray()
        self._current_points: List[Tuple[float, float]] = []
        self._latest_points: List[Tuple[float, float]] = []
        self._running = False
        self._reader: Optional[threading.Thread] = None

        # Очистка буфера порта
        self._send(_CMD_STOP)
        time.sleep(0.02)
        self._ser.reset_input_buffer()

    def _send(self, cmd: int):
        self._ser.write(bytes([_SYNC, cmd]))

    def start(self):
        if self._running:
            return
        self._send(_CMD_SCAN)
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
        except Exception:
            pass

    def _reader_loop(self):
        aligned = False
        while self._running:
            try:
                chunk = self._ser.read(512)
            except Exception:
                break

            if not chunk:
                continue

            with self._lock:
                self._rx += chunk
                if len(self._rx) > 20000:
                    del self._rx[:len(self._rx) - 20000]

                while len(self._rx) >= 5:
                    parsed = parse_measurement(bytes(self._rx[:5]))
                    if parsed is None or (not aligned and parsed[1] == 0):
                        del self._rx[0]
                        aligned = False
                        continue

                    aligned = True
                    del self._rx[:5]
                    new_scan, quality, angle, dist = parsed

                    if new_scan:
                        if self._current_points:
                            self._latest_points = self._current_points
                        self._current_points = []

                    if quality >= self.min_quality and 0.1 <= dist <= self.max_range:
                        self._current_points.append((angle, dist))

    def get_360_ranges(self) -> List[float]:
        """
        Возвращает 360 лучей (индекс = градус от 0 до 359).
        Если в градусе не было измерений, используется 999.0 (нет препятствия).
        """
        ranges = [999.0] * 360
        with self._lock:
            points = list(self._latest_points)

        for angle, dist in points:
            deg = int(round(angle)) % 360
            if dist < ranges[deg]:
                ranges[deg] = round(dist, 3)

        return ranges

    def close(self):
        self.stop()
        try:
            self._ser.close()
        except Exception:
            pass
