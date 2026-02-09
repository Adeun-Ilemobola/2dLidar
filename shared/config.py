

from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class scanRange:
    maxX:  float =23.0
    maxY: float = 23.0
    min_distance: float = 2.0
    max_distance: float = 400.0
    avg_scan_time: float = 366.0  # in seconds
    range_X_max: tuple[float, float] = (-35.0, 35.0)
    range_Y_Max: tuple[float, float] = (-35.0, 35.0)

@dataclass(frozen=True, slots=True)
class SystemConfig:
    tick_ms: int = 10  # 20 milliseconds per tick