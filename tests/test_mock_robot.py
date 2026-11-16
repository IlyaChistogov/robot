import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
from mock_robot import MockRobot
from schemas import DriveCommand


def test_mock_robot_initial_state():
    robot = MockRobot()
    telemetry = robot.get_full_telemetry()
    assert telemetry.status.emergency_stop is False
    assert telemetry.battery.voltage > 12.0
    assert telemetry.battery.percentage > 90.0
    assert len(telemetry.lidar.ranges) == 360


def test_mock_robot_drive_and_e_stop():
    robot = MockRobot()
    robot.set_drive_command(DriveCommand(linear=0.5, angular=0.0))
    robot.update()
    t = robot.get_full_telemetry()
    assert t.status.emergency_stop is False

    # Активация E-Stop
    robot.trigger_emergency_stop()
    robot.update()
    t_stop = robot.get_full_telemetry()
    assert t_stop.status.emergency_stop is True
    assert t_stop.pose.linear_velocity == 0.0

    # Сброс E-Stop
    robot.reset_emergency_stop()
    t_reset = robot.get_full_telemetry()
    assert t_reset.status.emergency_stop is False


def test_mock_robot_lidar_ranges():
    robot = MockRobot()
    t = robot.get_full_telemetry()
    ranges = t.lidar.ranges
    assert len(ranges) == 360
    # В комнате 10x10 робот по центру (0,0) видит стены на расстоянии ~5м
    assert 4.0 < ranges[0] < 6.0
