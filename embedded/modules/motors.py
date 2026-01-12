# embedded/modules/motor.py

from gpiozero import AngularServo
from gpiozero.pins.pigpio import PiGPIOFactory
from dataclasses import dataclass


@dataclass
class ServoConfig:
    pin: int
    min_pulse_us: int = 500
    max_pulse_us: int = 2500
    max_angle_deg: float = 270.0
    min_angle_deg: float = 0.0


class Motor:
    def __init__(self, cfg: ServoConfig, factory: PiGPIOFactory) -> None:
        self.cfg = cfg
        self.Servo = AngularServo(
            pin=cfg.pin,
            min_angle=cfg.min_angle_deg,
            max_angle=cfg.max_angle_deg,
            min_pulse_width=cfg.min_pulse_us / 1_000_000,
            max_pulse_width=cfg.max_pulse_us / 1_000_000,
            pin_factory=factory,
        )

        self.enabled: bool = False
        self.testMode: bool = False
        self.offset_deg: float = self.cfg.max_angle_deg / 2
        self.angle_deg: float = 0.0

    # ---------- public API ----------
    def enable(self, activate: bool) -> None:
        if activate:
            self.testMode = True
            self.enabled = activate
            self.apply_to_hardware()
            self.angle_deg = self.cfg.max_angle_deg / 3
            self.apply_to_hardware()
            self.angle_deg = self.cfg.max_angle_deg
            self.apply_to_hardware()
            self.angle_deg = self.cfg.min_angle_deg
            self.apply_to_hardware()
            self.testMode = False

    def get_angle(self) -> float:
        return self.angle_deg

    def set_angle(self, angle_deg: float) -> None:
        print(f"[DRV] angle_deg={angle_deg}")
        if self.enabled:
            self.angle_deg = angle_deg
            self.apply_to_hardware()

    def get_offset(self) -> float:
        return self.offset_deg

    def set_offset(self, offset_deg: float) -> None:
        print(f"[DRV] offset_deg={offset_deg}")
        if self.enabled:
            self.offset_deg = offset_deg
            self.apply_to_hardware()

    # ---------- helpers ----------
    def apply_to_hardware(self) -> None:
        # real angle = requested + offset
        physical_deg = self.clamp_angle(self.angle_deg + self.offset_deg)
        pulse = self.angle_to_pulse_us(physical_deg)
        self.Servo.angle = pulse / 1_000_000

    def angle_to_pulse_us(self, angle_deg: float) -> int:
        ratio = angle_deg * (self.cfg.max_pulse_us / self.cfg.max_angle_deg)
        return int(ratio + self.cfg.min_pulse_us)

    def pulse_us_to_angle(self, pulse_us: int) -> float:
        pulse = pulse_us - self.cfg.min_pulse_us
        ratio = (self.cfg.max_angle_deg / self.cfg.max_pulse_us)
        return float(ratio * pulse)

    def clamp_angle(self, a: float) -> float:
        return max(0.0, min(a, self.cfg.max_angle_deg))
