from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Optional  , List
import time


def filter3(a: float, b: float, c: float, tol: float = 5) -> float:
    # any two close -> average them, else median
    if abs(a - b) <= tol:
        return (a + b) / 2
    if abs(a - c) <= tol:
        return (a + c) / 2
    if abs(b - c) <= tol:
        return (b + c) / 2
    return sorted([a, b, c])[1]

@dataclass
class VL53L1XConfig:
    i2c_bus: int = 1
    i2c_address: int = 0x29


class VL53L1XSensor:
    def __init__(self,cfg: VL53L1XConfig, ):
        self.cfg = cfg
        self.sensor = None
        self.collecting = False
        self.samples: list[float] = []
        self.readyMm: Optional[float] = None


    def start(self) -> None:
        import board
        import busio
        import adafruit_vl53l1x

        i2c = busio.I2C(board.SCL, board.SDA)
        self.sensor = adafruit_vl53l1x.VL53L1X(i2c)


    def readOnceMm(self) -> Optional[float]:
        if self.sensor is None:
            return None
        try:
            mm = float(self.sensor.distance)
            return None if mm <= 0 else mm
        except Exception:
            return None


    def request(self) -> None:
        # “Start collecting exactly 3 readings”
        self.collecting = True
        self.samples = []
        self.readyMm = None


    def tick(self) -> None:
        """
        Called FROM System.tick().
        It tries to take ONE reading per call and stores progress.
        """
        if not self.collecting:
            print("sensor not collect mode")
            return

        v = self.readOnceMm()
        if v is None:
            print("sensor reading error try again next System tick")
            return  # try again next System tick

        self.samples.append(v)

        if len(self.samples) == 3:
            self.collecting = False
            self.readyMm = filter3(self.samples[0], self.samples[1], self.samples[2], tol=5)


    def take(self) -> Optional[int]:
        # returns result once
        v = self.readyMm
        self.readyMm = None
        return v
