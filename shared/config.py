

from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class scanRange:
    maxX: float
    maxY: float
    min_distance: float = 2.0
    max_distance: float = 400.0
    avg_scan_time: float = 366.0  # in seconds
    range_X_max: tuple[float, float] = (-35.0, 35.0)
    range_Y_Max: tuple[float, float] = (-35.0, 35.0)

@dataclass(frozen=True, slots=True)
class SystemConfig:
    tick_ms: float = (15)/1000  # 20 milliseconds per tick