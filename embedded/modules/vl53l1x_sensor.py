from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

def filter3(a: float, b: float, c: float, tol: float = 5) -> float:
    if abs(a - b) <= tol:
        return (a + b) / 2
    if abs(a - c) <= tol:
        return (a + c) / 2
    if abs(b - c) <= tol:
        return (b + c) / 2
    return sorted([a, b, c])[1]

@dataclass
class VL53L1XConfig:
    i2c_address: int = 0x29
    tol_mm: float = 3.0

class VL53L1XSensor:
    def __init__(self, cfg: VL53L1XConfig):
        self.cfg = cfg
        self.sensor = None
        self.collecting = False
        self.samples: list[float] = []
        self.readyMm: Optional[float] = None
        self.start()

    def start(self) -> None:
        try:
            import board
            import busio
            import adafruit_vl53l1x

            i2c = busio.I2C(board.SCL, board.SDA)
            self.sensor = adafruit_vl53l1x.VL53L1X(i2c, address=self.cfg.i2c_address)

           
            if hasattr(self.sensor, "start_ranging"):
                self.sensor.start_ranging()

        except Exception as e:
            print(f"VL53L1XSensor start error: {e!r}")
            self.sensor = None

    def request(self) -> None:
        """Ask for one filtered measurement (3 samples)."""
        if self.sensor is None:
            return
        self.collecting = True
        self.samples = []
        self.readyMm = None

    def tick(self) -> None:
        """Call once per System tick; advances sampling state machine."""
        if self.sensor is None:
            return

        if not self.collecting:
            return

        # Only read when a fresh measurement is ready (prevents duplicates)
        if hasattr(self.sensor, "data_ready") and not self.sensor.data_ready:
            return

        try:
            mm = float(self.sensor.distance)
        except Exception as e:
            print(f"VL53L1X read error: {e!r}")
            return

        if mm <= 0:
            return

        self.samples.append(mm)

        # Clear interrupt / schedule next reading (driver-dependent)
        if hasattr(self.sensor, "clear_interrupt"):
            try:
                self.sensor.clear_interrupt()
            except Exception:
                pass

        if len(self.samples) >= 3:
            self.collecting = False
            a, b, c = self.samples[:3]
            self.readyMm = filter3(a, b, c, tol=self.cfg.tol_mm)

    def take(self) -> Optional[float]:
        """Consume result once it is ready."""
        v = self.readyMm
        self.readyMm = None
        return v

    def reset(self) -> None:
        self.collecting = False
        self.samples = []
        self.readyMm = None
