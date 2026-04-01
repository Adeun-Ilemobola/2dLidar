from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


def filter3(a: float, b: float, c: float, tol: float = 0.3) -> float:
    # values are in centimeters
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

    # Sensor tuning
    distance_mode: int = 2       # 1 = short, 2 = long
    timing_budget_ms: int = 33      # try 20 or 33 first
    roi_xy: tuple[int, int] = (11, 11) # (width, height) in pixels, max 16x16

    # Filtering / acquisition
    tol_cm: float = 0.4
    max_samples: int = 3
    max_not_ready_ticks: int = 40


class VL53L1XSensor:
    def __init__(self, cfg: VL53L1XConfig):
        self.cfg = cfg
        self.sensor = None

        self.collecting = False
        self.samples: list[float] = []
        self.readyCm: Optional[float] = None
        self.not_ready_ticks = 0

        self.start()

    def start(self) -> None:
        print("VL53L1X: starting")
        try:
            import board
            import busio
            import adafruit_vl53l1x

            i2c = busio.I2C(board.SCL, board.SDA)
            self.sensor = adafruit_vl53l1x.VL53L1X(i2c, address=self.cfg.i2c_address)
            print("VL53L1X: sensor object created")

            # Tune sensor before starting ranging
            self.sensor.distance_mode = self.cfg.distance_mode
            print("VL53L1X: set distance_mode")

            self.sensor.timing_budget = self.cfg.timing_budget_ms
            print("VL53L1X: set timing_budget")

            self.sensor.roi_xy = self.cfg.roi_xy
            print("VL53L1X: set roi_xy")


            if hasattr(self.sensor, "start_ranging"):
                self.sensor.start_ranging()
                print("VL53L1X: start_ranging called")

            print(
                f"VL53L1X started: mode={self.sensor.distance_mode}, "
                f"timing_budget={self.sensor.timing_budget}, roi={self.sensor.roi_xy}"
            )

        except Exception as e:
            print(f"VL53L1XSensor start error: {e!r}")
            self.sensor = None

    def request(self) -> None:
        pass

    def tick(self) -> None:
        if self.sensor is None :
            return

        try:
            if hasattr(self.sensor, "data_ready") and not self.sensor.data_ready:
                return
        except Exception as e:
            print(f"VL53L1X data_ready error: {e!r}")
            return

        raw = None
        try:
            raw = self.sensor.distance
            ##print(f"VL53L1X raw distance: {raw!r}")
        except Exception as e:
            print(f"VL53L1X read error: {e!r}")
        finally:
            # Always clear interrupt once data_ready was true,
            if hasattr(self.sensor, "clear_interrupt"):
                try:
                    self.sensor.clear_interrupt()
                except Exception as e:
                    print(f"VL53L1X clear_interrupt error: {e!r}")

        if raw is None:
            return

        try:
            cm = float(raw)
        except (TypeError, ValueError) as e:
            print(f"VL53L1X conversion error: raw={raw!r}, error={e!r}")
            return

        self.samples.append(cm)
        if len(self.samples) > self.cfg.max_samples:
            self.samples.pop(0)
            
        # Always assign readyCm! Use the filter if the buffer is full.
        if len(self.samples) == self.cfg.max_samples:
            self.readyCm = filter3(self.samples[0], self.samples[1], self.samples[2], self.cfg.tol_cm)
        else:
            self.readyCm = cm
            
            
                
    def take_cm(self) -> Optional[float]:
        value = self.readyCm
        self.readyCm = None
        return value

    def take_mm(self) -> Optional[float]:
        value = self.take_cm()
        return None if value is None else value * 10.0

    def reset(self) -> None:
        self.collecting = False
        self.samples = []
        self.readyCm = None
        self.not_ready_ticks = 0