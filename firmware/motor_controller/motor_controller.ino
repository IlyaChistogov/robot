/*
  Прошивка низкоуровневого контроллера шасси мобильного робота.
  Платформа: Arduino Mega / Uno / Nano / ESP32.
  
  Аппаратная часть:
  1. Двухканальный H-мост VNH2SP30 (Monster Moto Shield).
  2. Два мощных DC-мотора с энкодерами на валу (оптопары).
  3. Делитель напряжения для автомобильного аккумулятора 12В (вход A0).
  4. Блок силовых реле (пины 10, 11, 12, 13).
  
  Протокол обмена с Raspberry Pi (Serial 115200 бод):
  - Прием команд:
      "M <left_pwm> <right_pwm>\n"  -> Установка ШИМ моторов (-255..+255)
      "STOP\n"                      -> Экстренная остановка
      "R <id> <state>\n"            -> Управление реле (R 1 1 / R 1 0)
  - Отправка телеметрии (20 Гц):
      "T <voltage> <left_ticks> <right_ticks> <left_current> <right_current>\n"
  
  Безопасность:
  - Watchdog (сторожевой таймер): при отсутствии команд более 500 мс
    моторы автоматически обесточиваются.
*/

// =================== РАСПИНОВКА VNH2SP30 ===================
// Левый мотор (Motor 1)
const int PIN_M1_PWM = 5;
const int PIN_M1_INA = 7;
const int PIN_M1_INB = 8;
const int PIN_M1_CS  = A2; // Датчик тока

// Правый мотор (Motor 2)
const int PIN_M2_PWM = 6;
const int PIN_M2_INA = 4;
const int PIN_M2_INB = 9;
const int PIN_M2_CS  = A3; // Датчик тока

// =================== ЭНКОДЕРЫ КОЛЕС ===================
const int PIN_ENC_LEFT  = 2; // Прерывание INT0
const int PIN_ENC_RIGHT = 3; // Прерывание INT1

volatile long left_encoder_ticks = 0;
volatile long right_encoder_ticks = 0;

// =================== ДЕЛИТЕЛЬ НАПРЯЖЕНИЯ 12В АКБ ===================
// Схема: Аккумулятор (+) -> R1 (100 кОм) -> Pin A0 -> R2 (20 кОм) -> GND
const int PIN_BATTERY_ADC = A0;
const float VOLTAGE_DIVIDER_RATIO = (100.0 + 20.0) / 20.0; // Коэффициент 6.0
const float ADC_VREF = 5.0; // Опорное напряжение АЦП

// =================== БЛОК РЕЛЕ ===================
const int RELAY_PINS[4] = {10, 11, 12, 13};

// =================== СТОРОЖЕВОЙ ТАЙМЕР (WATCHDOG) ===================
unsigned long last_command_time = 0;
const unsigned long WATCHDOG_TIMEOUT_MS = 500; // 500 мс

unsigned long last_telemetry_time = 0;
const unsigned long TELEMETRY_INTERVAL_MS = 50; // 20 Гц

// Прерывания для подсчета тиков энкодеров
void isr_left_encoder() {
  left_encoder_ticks++;
}

void isr_right_encoder() {
  right_encoder_ticks++;
}

void set_motor_left(int pwm) {
  pwm = constrain(pwm, -255, 255);
  if (pwm > 0) {
    digitalWrite(PIN_M1_INA, HIGH);
    digitalWrite(PIN_M1_INB, LOW);
    analogWrite(PIN_M1_PWM, pwm);
  } else if (pwm < 0) {
    digitalWrite(PIN_M1_INA, LOW);
    digitalWrite(PIN_M1_INB, HIGH);
    analogWrite(PIN_M1_PWM, -pwm);
  } else {
    digitalWrite(PIN_M1_INA, LOW);
    digitalWrite(PIN_M1_INB, LOW);
    analogWrite(PIN_M1_PWM, 0);
  }
}

void set_motor_right(int pwm) {
  pwm = constrain(pwm, -255, 255);
  if (pwm > 0) {
    digitalWrite(PIN_M2_INA, HIGH);
    digitalWrite(PIN_M2_INB, LOW);
    analogWrite(PIN_M2_PWM, pwm);
  } else if (pwm < 0) {
    digitalWrite(PIN_M2_INA, LOW);
    digitalWrite(PIN_M2_INB, HIGH);
    analogWrite(PIN_M2_PWM, -pwm);
  } else {
    digitalWrite(PIN_M2_INA, LOW);
    digitalWrite(PIN_M2_INB, LOW);
    analogWrite(PIN_M2_PWM, 0);
  }
}

void stop_all_motors() {
  set_motor_left(0);
  set_motor_right(0);
}

float read_battery_voltage() {
  int raw = analogRead(PIN_BATTERY_ADC);
  float v_pin = (raw * ADC_VREF) / 1023.0;
  return v_pin * VOLTAGE_DIVIDER_RATIO;
}

float read_motor_current(int cs_pin) {
  // Чувствительность VNH2SP30: примерно 0.13 В на 1 Ампер
  int raw = analogRead(cs_pin);
  float v = (raw * ADC_VREF) / 1023.0;
  return v / 0.13;
}

void setup() {
  Serial.begin(115200);

  // Настройка пинов VNH2SP30
  pinMode(PIN_M1_PWM, OUTPUT);
  pinMode(PIN_M1_INA, OUTPUT);
  pinMode(PIN_M1_INB, OUTPUT);
  pinMode(PIN_M2_PWM, OUTPUT);
  pinMode(PIN_M2_INA, OUTPUT);
  pinMode(PIN_M2_INB, OUTPUT);

  // Настройка энкодеров
  pinMode(PIN_ENC_LEFT, INPUT_PULLUP);
  pinMode(PIN_ENC_RIGHT, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PIN_ENC_LEFT), isr_left_encoder, RISING);
  attachInterrupt(digitalPinToInterrupt(PIN_ENC_RIGHT), isr_right_encoder, RISING);

  // Настройка реле
  for (int i = 0; i < 4; i++) {
    pinMode(RELAY_PINS[i], OUTPUT);
    digitalWrite(RELAY_PINS[i], HIGH); // Большинство реле выключены при HIGH
  }

  stop_all_motors();
  last_command_time = millis();
}

void loop() {
  unsigned long now = millis();

  // 1. Проверка сторожевого таймера (Watchdog)
  if (now - last_command_time > WATCHDOG_TIMEOUT_MS) {
    stop_all_motors();
  }

  // 2. Обработка команд из Serial от Raspberry Pi
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd.startsWith("M ")) {
      // Формат: "M <left_pwm> <right_pwm>"
      int spaceIdx = cmd.indexOf(' ', 2);
      if (spaceIdx > 0) {
        int leftPwm = cmd.substring(2, spaceIdx).toInt();
        int rightPwm = cmd.substring(spaceIdx + 1).toInt();
        set_motor_left(leftPwm);
        set_motor_right(rightPwm);
        last_command_time = now;
      }
    } else if (cmd == "STOP") {
      stop_all_motors();
      last_command_time = 0; // Блокировка
    } else if (cmd.startsWith("R ")) {
      // Формат: "R <id 1..4> <state 0/1>"
      int id = cmd.substring(2, 3).toInt();
      int state = cmd.substring(4).toInt();
      if (id >= 1 && id <= 4) {
        // Реле обычно срабатывают от LOW
        digitalWrite(RELAY_PINS[id - 1], state == 1 ? LOW : HIGH);
      }
    }
  }

  // 3. Отправка телеметрии на Raspberry Pi (20 Гц)
  if (now - last_telemetry_time >= TELEMETRY_INTERVAL_MS) {
    last_telemetry_time = now;

    float v_bat = read_battery_voltage();
    float cur_l = read_motor_current(PIN_M1_CS);
    float cur_r = read_motor_current(PIN_M2_CS);

    // Вывод телеметрии: T <напряжение> <тики_L> <тики_R> <ток_L> <ток_R>
    Serial.print("T ");
    Serial.print(v_bat, 2);
    Serial.print(" ");
    Serial.print(left_encoder_ticks);
    Serial.print(" ");
    Serial.print(right_encoder_ticks);
    Serial.print(" ");
    Serial.print(cur_l, 2);
    Serial.print(" ");
    Serial.println(cur_r, 2);
  }
}
