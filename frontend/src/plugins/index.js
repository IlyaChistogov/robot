/**
 * Реестр плагинов веб-пульта оператора.
 * 
 * ЧТОБЫ ДОБАВИТЬ НОВЫЙ ДАТЧИК / ВИДЖЕТ:
 * 1. Создайте файл плагина в папке plugins/ (по образцу StudentSensorTemplate.jsx).
 * 2. Импортируйте его сюда и добавьте в массив PLUGINS.
 */

import { CameraPlugin } from './camera/CameraWidget';
import { LidarPlugin } from './lidar/LidarRadarWidget';
import { ControlsPlugin } from './controls/ControlsWidget';
import { BatteryPlugin } from './battery/BatteryWidget';
import { ImuPlugin } from './imu/ImuCompassWidget';
import { RelaysPlugin } from './relays/RelaysWidget';
import { StudentTemplatePlugin } from './student_template/StudentSensorTemplate';

export const PLUGINS = [
  CameraPlugin,
  LidarPlugin,
  ControlsPlugin,
  BatteryPlugin,
  ImuPlugin,
  RelaysPlugin,
  StudentTemplatePlugin
];
