# embedded/modules/motor.py

from dataclasses import dataclass
from typing import Optional

import board
import busio
from adafruit_motor import servo
from adafruit_pca9685 import PCA9685


@dataclass
class ServoConfig:
    channel: int
    address: int = 0x40
    frequency: int = 50

    # Signal tuning
    min_pulse_us: int = 500
    max_pulse_us: int = 2500

    # Physical safety clamp
    min_angle_deg: float = 0.0
    max_angle_deg: float = 180.0

    deadband_deg: float = 0.2


class Motor:
    def __init__(self, cfg: ServoConfig) -> None:
        self.cfg = cfg

        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.pca = PCA9685(self.i2c, address=self.cfg.address)
        self.pca.frequency = self.cfg.frequency
        self.pwm_channel = self.pca.channels[self.cfg.channel]

        self.servo: Optional[servo.Servo] = None

        self.enabled = False
        self.offset_deg = self.cfg.max_angle_deg / 2
        self.angle_deg = 0.0
        self.last_physical: float | None = None

    def enable(self, activate: bool) -> None:
        """Enable or disable the servo output."""
        if activate and not self.enabled:
            self.servo = servo.Servo(
                self.pwm_channel,
                min_pulse=self.cfg.min_pulse_us,
                max_pulse=self.cfg.max_pulse_us,
                actuation_range=self.cfg.max_angle_deg,
            )
            self.enabled = True
            self.apply_to_hardware(force=True)
            return

        if not activate and self.enabled:
            self.enabled = False
            self.last_physical = None
            self.pwm_channel.duty_cycle = 0
            self.servo = None

    def get_angle(self) -> float:
        return self.angle_deg

    def set_angle(self, angle_deg: float) -> None:
        """Set logical angle relative to the current offset."""
        if not self.enabled or self.servo is None:
            return

        min_logical = self.cfg.min_angle_deg - self.offset_deg
        max_logical = self.cfg.max_angle_deg - self.offset_deg
        self.angle_deg = max(min_logical, min(angle_deg, max_logical))

        self.apply_to_hardware()
        # print(
        #     f"[DRV] set_angle: requested={angle_deg}, logical={self.angle_deg}, "
        #     f"offset={self.offset_deg}, physical={self.last_physical}"
        # )

    def get_offset(self) -> float:
        return self.offset_deg

    def get_physical_angle(self) -> float:
        return self.clamp_physical(self.angle_deg + self.offset_deg)

    def set_offset(self, offset_deg: float) -> None:
        """Update offset and reapply current logical angle."""
        self.offset_deg = self.clamp_physical(offset_deg)

        # print(
        #     f"[DRV] set_offset: requested={offset_deg}, "
        #     f"applied_offset={self.offset_deg}, current_physical={self.last_physical}"
        # )

        if self.enabled and self.servo is not None:
            self.apply_to_hardware(force=True)

    def apply_to_hardware(self, force: bool = False) -> None:
        """Apply logical angle + offset to the actual servo."""
        if not self.enabled or self.servo is None:
            return

        physical_deg = self.clamp_physical(self.angle_deg + self.offset_deg)

        if not force and self.last_physical is not None:
            if abs(physical_deg - self.last_physical) < self.cfg.deadband_deg:
                return

        self.servo.angle = physical_deg
        self.last_physical = physical_deg

    def clamp_physical(self, physical_deg: float) -> float:
        return max(self.cfg.min_angle_deg, min(physical_deg, self.cfg.max_angle_deg))