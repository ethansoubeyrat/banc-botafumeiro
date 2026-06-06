# coding:UTF-8
from gpiozero import Servo
from gpiozero.pins.pigpio import PiGPIOFactory
from time import sleep

# Motor instance
class Servomotor:
    def __init__(self):
        self.factory = PiGPIOFactory()
        self.servo = Servo(
            18,                          # BCM pin number (BOARD pin 12 = BCM 18)
            min_pulse_width=0.5/1000,   # 0.5ms for 0°
            max_pulse_width=2.5/1000,   # 2.5ms for 180°
            pin_factory=self.factory
        )

    # Set function to calculate servo position (-1 to 1) from angle (0 to 180)
    # 0° = -1, 90° = 0, 180° = 1
    def angle_to_position(self, angle):
        if angle > 180 or angle < 0:
            return False
        return (angle / 90) - 1

# Test:
#motor = Servomotor()
#motor.servo.value = motor.angle_to_position(90)
#sleep(1)
#motor.servo.value = motor.angle_to_position(180)
#sleep(1)
#motor.servo.value = motor.angle_to_position(0)
#sleep(1)
#motor.servo.close()