import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
from rplidar_driver import parse_measurement


def test_parse_measurement_valid():
    # Собираем валидный 5-байтный пакет Slamtec A1:
    # b0: new_scan=True (bit 0 = 1), inv_new_scan=False (bit 1 = 0), quality=15 (bits 2..7 -> 15 << 2)
    # b1: check_bit=1 (bit 0 = 1), angle_q6 lower 7 bits (bits 1..7 -> (angle_q6 & 0x7F) << 1)
    # b2: angle_q6 upper 8 bits (angle_q6 >> 7)
    # b3, b4: distance_mm * 4 (distance_q2)
    b0 = (15 << 2) | 0x01
    angle_deg = 90.0
    angle_q6 = int(round(angle_deg * 64.0)) & 0x7FFF
    b1 = ((angle_q6 & 0x7F) << 1) | 0x01
    b2 = (angle_q6 >> 7) & 0xFF
    raw_dist = int(round(1.5 * 1000.0 * 4.0))
    b3 = raw_dist & 0xFF
    b4 = (raw_dist >> 8) & 0xFF

    data = bytes([b0, b1, b2, b3, b4])
    parsed = parse_measurement(data)
    assert parsed is not None
    new_scan, quality, angle, dist = parsed
    assert new_scan is True
    assert quality == 15
    assert abs(angle - 90.0) < 0.1
    assert abs(dist - 1.5) < 0.01


def test_parse_measurement_invalid_checkbit():
    # Check-бит (bit 0 байта 1) равен 0 -> должен вернуть None
    # b0: new_scan=1, inv=0 (0x01)
    # b1: check_bit=0 (0x00)
    data = bytes([0x01, 0x00, 0x00, 0x00, 0x00])
    assert parse_measurement(data) is None


def test_parse_measurement_invalid_scan_flags():
    # Если new_scan == inv_new_scan -> должен вернуть None
    data = bytes([0x03, 0x01, 0x00, 0x00, 0x00])
    assert parse_measurement(data) is None
