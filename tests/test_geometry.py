import math
import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
from geometry import Pose, normalize_angle, integrate_unicycle, deg_to_rad, rad_to_deg


def test_normalize_angle():
    assert abs(normalize_angle(0.0)) < 1e-6
    assert abs(normalize_angle(math.pi) - math.pi) < 1e-6
    assert abs(normalize_angle(3 * math.pi) - math.pi) < 1e-6
    assert abs(normalize_angle(-3 * math.pi) - math.pi) < 1e-6
    assert abs(normalize_angle(2 * math.pi)) < 1e-6


def test_pose_distance_and_diff():
    p1 = Pose(0.0, 0.0, 0.0)
    p2 = Pose(3.0, 4.0, math.pi / 2)
    assert abs(p1.distance_to(p2) - 5.0) < 1e-6
    assert abs(p1.angle_diff_to(math.pi / 2) - math.pi / 2) < 1e-6


def test_integrate_unicycle_straight():
    p0 = Pose(0.0, 0.0, 0.0)
    p1 = integrate_unicycle(p0, linear=1.0, angular=0.0, dt=1.0)
    assert abs(p1.x - 1.0) < 1e-6
    assert abs(p1.y) < 1e-6
    assert abs(p1.theta) < 1e-6


def test_integrate_unicycle_circle():
    # Движение со скоростью v=1, w=pi/2 в течение 2 секунд -> полуокружность радиуса 2/pi
    p0 = Pose(0.0, 0.0, 0.0)
    # За 1 секунду повернется на 90 градусов (pi/2)
    p1 = integrate_unicycle(p0, linear=math.pi / 2, angular=math.pi / 2, dt=1.0)
    assert abs(p1.theta - math.pi / 2) < 1e-5
    # За 4 секунды полный круг
    p4 = integrate_unicycle(p0, linear=1.0, angular=math.pi / 2, dt=4.0)
    assert abs(p4.x - p0.x) < 1e-5
    assert abs(p4.y - p0.y) < 1e-5
    assert abs(p4.theta - p0.theta) < 1e-5
