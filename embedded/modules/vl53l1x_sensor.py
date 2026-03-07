from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


def filter3(a: float, b: float, c: float, tol: float = 2.0) -> float:
    if abs(a - b) <= tol:
        return (a + b) / 2.0
    if abs(a - c) <= tol:
        return (a + c) / 2.0
    if abs(b - c) <= tol:
        return (b + c) / 2.0
    return sorted([a, b, c])[1]


@dataclass
class VL53L1XConfig:
    i2c_address: int = 0x29
    tol_mm: float = 3.0
    max_samples: int = 3
    max_none_reads: int = 20


class VL53L1XSensor:
    def __init__(self, cfg: VL53L1XConfig):
        self.cfg = cfg
        self.sensor = None

        # acquisition state
        self.collecting = False
        self.samples: list[float] = []
        self.readyMm: Optional[float] = None
        self.none_reads = 0

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
        """Begin collecting one filtered measurement."""
        if self.sensor is None:
            return

        # Do not restart a measurement if one is already in progress
        if self.collecting:
            return

        self.collecting = True
        self.samples = []
        self.readyMm = None
        self.none_reads = 0

    def tick(self) -> None:
        """Advance the measurement state machine by one step."""
        if self.sensor is None or not self.collecting:
            return

        # Read raw sensor value
        try:
            raw = self.sensor.distance
        except Exception as e:
            print(f"VL53L1X read error: {e!r}")
            return

        # Sensor not ready yet
        if raw is None:
            self.none_reads += 1

            # fail-safe: abandon this request if it never becomes valid
            if self.none_reads >= self.cfg.max_none_reads:
                print("VL53L1X warning: too many None reads, cancelling request")
                self.collecting = False
                self.samples = []
                self.readyMm = None
                self.none_reads = 0
            return

        # Valid raw reading arrived
        self.none_reads = 0

        try:
            mm = float(raw)
        except (TypeError, ValueError) as e:
            print(f"VL53L1X conversion error: raw={raw!r}, error={e!r}")
            return

        # Ignore impossible / invalid values
        if mm <= 0:
            return

        self.samples.append(mm)

        # Clear interrupt if supported by the driver
        if hasattr(self.sensor, "clear_interrupt"):
            try:
                self.sensor.clear_interrupt()
            except Exception:
                pass

        # Early accept if first 2 samples are close enough
        if len(self.samples) == 2:
            a, b = self.samples
            if abs(a - b) <= self.cfg.tol_mm:
                self.readyMm = (a + b) / 2.0
                self.collecting = False
                return

        # Accept filtered result once enough samples collected
        if len(self.samples) >= self.cfg.max_samples:
            if len(self.samples) >= 3:
                a, b, c = self.samples[:3]
                self.readyMm = filter3(a, b, c, tol=self.cfg.tol_mm)
            else:
                self.readyMm = sum(self.samples) / len(self.samples)

            self.collecting = False

    def take(self) -> Optional[float]:
        """Consume the ready result once."""
        value = self.readyMm
        self.readyMm = None
        return value

    def reset(self) -> None:
        """Clear all current acquisition state."""
        self.collecting = False
        self.samples = []
        self.readyMm = None
        self.none_reads = 0