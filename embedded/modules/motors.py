# embedded/modules/motor.py

from gpiozero import AngularServo
from gpiozero.pins.lgpio import LGPIOFactory
from dataclasses import dataclass


@dataclass
class ServoConfig:
    pin: int
    min_pulse_us: int = 1000
    max_pulse_us: int = 2000
    max_angle_deg: float = 180
    min_angle_deg: float = 0.0
    deadband_deg: float = 0.2 # minimum change to apply


class Motor:
    def __init__(self, cfg: ServoConfig, factory: LGPIOFactory) -> None:
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
        self.offset_deg: float = 0.0 
        self.angle_deg: float = 0.0
        self.last_physical: float | None = None

    # ---------- public API ----------
    def enable(self, activate: bool) -> None:
        if activate and not self.enabled:
            self.testMode = True
            if self.offset_deg == 0.0:
             self.offset_deg = 90.0
            self.apply_to_hardware(force=True)
        elif not activate and self.enabled:
            self.testMode = False
            self.Servo.detach()
            self.last_physical = None
            

    def get_angle(self) -> float:
        return self.angle_deg

    def set_angle(self, angle_deg: float) -> None:
         if not self.enabled:
            return

         # keep physical in range
         min_logical = self.cfg.min_angle_deg - self.offset_deg
         max_logical = self.cfg.max_angle_deg - self.offset_deg
         self.angle_deg = max(min_logical, min(angle_deg, max_logical))
         self.apply_to_hardware()

    def get_offset(self) -> float:
        return self.offset_deg

    def set_offset(self, offset_deg: float) -> None:
        print(f"[DRV] offset_deg={offset_deg}")
        if self.enabled:
            self.offset_deg = offset_deg
            self.apply_to_hardware()

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
