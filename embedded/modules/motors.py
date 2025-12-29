# embedded/modules/motor.py
from __future__ import annotations
from dataclasses import dataclass

@dataclass
class ServoConfig:
    pin: int
    min_pulse_us: int = 500 / 1000000
    max_pulse_us: int = 2500 / 1000000
    max_angle_deg: float = 270.0


class Motor:
    def __init__(self, cfg: ServoConfig, pi) -> None:
        self.cfg = cfg
        self.PI = pi

        self._enabled: bool = False
        self._offset_deg: float = 0.0
        self._angle_deg: float = 0.0

    # ---------- public API ----------
    def enable(self, enabled: bool) -> None:
        self._enabled = enabled
        if enabled:
            self._apply_to_hardware()
        else:
           self.set_angle(0)


    def get_angle(self) -> float:
        return self._angle_deg

    def set_angle(self, angle_deg: float) -> None:
        self._angle_deg = self._clamp_angle(angle_deg)
        print(f"[DRV] angle_deg={angle_deg}")
        if self._enabled:
            self._apply_to_hardware()

    def get_offset(self) -> float:
        return self._offset_deg

    def set_offset(self, offset_deg: float) -> None:
        print(f"[DRV] offset_deg={offset_deg}")

        self._offset_deg = offset_deg
        if self._enabled:
            self._apply_to_hardware()

    # ---------- helpers ----------
    def _apply_to_hardware(self) -> None:
        # real angle = requested + offset
        physical_deg = self._clamp_angle(self._angle_deg + self._offset_deg)
        pulse = self._angle_to_pulse_us(physical_deg)
        self.PI.write_pulse_us(self.cfg.pin, pulse)

    def _angle_to_pulse_us(self, angle_deg: float) -> int:
        ratio = angle_deg *  (self.cfg.max_pulse_us / self.cfg.max_angle_deg)
        return int(ratio + self.cfg.min_pulse_us)

    def _pulse_us_to_angle(self, pulse_us: int) -> float:
        pulse = pulse_us- self.cfg.min_pulse_us
        ratio = (self.cfg.max_angle_deg /self.cfg.max_pulse_us )
        return float(ratio * pulse)

    def _clamp_angle(self, a: float) -> float:
        return max(0.0, min(a, self.cfg.max_angle_deg))
