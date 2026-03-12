
import RPi.GPIO as GPIO

class Buzzer:
    def __init__(self, pin):
        self.pin = pin
        GPIO.setmode(GPIO.BCM)
        self.pwm = GPIO.PWM(self.pin, 100)
        self.pwm.start(0)

    def on(self, frequency=1000):
        for i in range(3):
            self.pwm.ChangeDutyCycle(100)
            self.pwm.ChangeFrequency(frequency)
            self.pwm.ChangeDutyCycle(0)
       

    def off(self):
        self.pwm.ChangeDutyCycle(0)
    def cleanup(self):
        self.pwm.stop()
        GPIO.cleanup(self.pin)