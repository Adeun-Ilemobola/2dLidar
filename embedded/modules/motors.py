# embedded/modules/motor.py

from typing import Optional
from gpiozero import AngularServo
from gpiozero.pins.lgpio import LGPIOFactory

import board
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo

from dataclasses import dataclass


@dataclass
class ServoConfig:
     channel: int
     address: int = 0x40
     frequency: int = 50

    # signal tuning (microseconds)
     min_pulse_us: int = 500
     max_pulse_us: int = 2500

    # physical safety clamp
     min_angle_deg: float = 0.0
     max_angle_deg: float = 180.0

     deadband_deg: float = 0.2  # minimum change to apply

class Motor:
    def __init__(self, cfg: ServoConfig) -> None:
        self.cfg = cfg

        # Hardware handles
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.pca = PCA9685(self.i2c, address=self.cfg.address)
        self.pca.frequency = self.cfg.frequency
        self.pwm_channel = self.pca.channels[self.cfg.channel]

        self.Servo :Optional[servo.Servo] = None

        self.enabled: bool = False
        self.testMode: bool = False
        self.offset_deg: float = self.cfg.max_angle_deg / 2 
        self.angle_deg: float = 0.0
        self.last_physical: float | None = None

    # ---------- public API ----------
    def enable(self, activate: bool) -> None:
       
       if activate and not self.enabled:
            # Create the Servo object once when enabling
            self.Servo = servo.Servo(
                self.pwm_channel,
                min_pulse=self.cfg.min_pulse_us,
                max_pulse=self.cfg.max_pulse_us,
                actuation_range=self.cfg.max_angle_deg,  # angle range exposed to .angle
            )
            self.enabled = True
            self.apply_to_hardware(force=True)
        

       elif (not activate) and self.enabled:
            self.enabled = False
            self.last_physical = None

            self.pwm_channel.duty_cycle = 0
            self.Servo = None
            

    def get_angle(self) -> float:
        return self.angle_deg

    def set_angle(self, angle_deg: float) -> None:
         if not self.enabled and self.Servo is not None:
            return
        

         # keep physical in range
         min_logical = self.cfg.min_angle_deg - self.offset_deg
         max_logical = self.cfg.max_angle_deg - self.offset_deg
         self.angle_deg = max(min_logical, min(angle_deg, max_logical))
         self.apply_to_hardware()
         print(f"[DRV] set_angle: requested={angle_deg}, logical={self.angle_deg}, offset={self.offset_deg}, physical={self.last_physical}")

    def get_offset(self) -> float:
        return self.offset_deg

    def set_offset(self, offset_deg: float) -> None:
        print(f"[DRV] set_offset: requested={offset_deg}, current_offset={self.offset_deg}, current_physical={self.last_physical}")
         # keep offset in range
        self.offset_deg = offset_deg
        if self.enabled:
           
            self.apply_to_hardware(force=True)

    # ---------- helpers ----------
    def apply_to_hardware(self, force: bool = False) -> None:
        # real angle = requested + offset
        physical_deg = self.clamp_physical(self.angle_deg + self.offset_deg)
        if (not force) and (self.last_physical is not None):
            if abs(physical_deg - self.last_physical) < self.cfg.deadband_deg:
                return
        self.Servo.angle = physical_deg 
        self.last_physical = physical_deg

    def angle_to_pulse_us(self, angle_deg: float) -> int:
        ratio = angle_deg * (self.cfg.max_pulse_us / self.cfg.max_angle_deg)
        return int(ratio + self.cfg.min_pulse_us)

    def pulse_us_to_angle(self, pulse_us: int) -> float:
        pulse = pulse_us - self.cfg.min_pulse_us
        ratio = (self.cfg.max_angle_deg / self.cfg.max_pulse_us)
        return float(ratio * pulse)

    def clamp_physical(self, physical: float) -> float:
        return max(self.cfg.min_angle_deg, min(physical, self.cfg.max_angle_deg))
   