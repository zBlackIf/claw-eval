import time
from mpython import *

LASER_PIN = 0
PHOTO_PIN = 1
laser_pin = MPythonPin(LASER_PIN, PinMode.OUT)
photo_pin = MPythonPin(PHOTO_PIN, PinMode.ANALOG)
WHEEL_DIAMETER_MM = 49.52
SLIT_COUNT = 12
WHEEL_CIRCUMFERENCE_MM = 3.1415926 * WHEEL_DIAMETER_MM
DISTANCE_PER_SLIT_MM = WHEEL_CIRCUMFERENCE_MM / SLIT_COUNT

laser_pin.write_digital(1)

oled.fill(0)
oled.DispChar("传感器特性测试", 10, 0)
oled.DispChar("按下A键开始", 20, 32)
oled.show()

def collect_sensor_data():
    static_data = []
    for i in range(100):
        voltage = photo_pin.read_analog()
        timestamp = time.ticks_ms()
        static_data.append((timestamp, voltage))
        time.sleep_ms(1)
    static_voltages = [v for _, v in static_data]
    static_avg = sum(static_voltages) / len(static_voltages)
    return static_avg

def main():
    while True:
        if button_a.value() == 0:
            time.sleep_ms(20)
            if button_a.value() == 0:
                avg = collect_sensor_data()
                oled.fill(0)
                oled.DispChar("电压: {:.0f}".format(avg), 5, 32)
                oled.show()
                while button_a.value() == 0:
                    time.sleep_ms(10)
        time.sleep_ms(10)

if __name__ == "__main__":
    main()
