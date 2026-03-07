

from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class scanRange:
    maxX:  float =23.0
    maxY: float = 23.0
    min_distance: float = .8
    max_distance: float = 400.0
    avg_scan_time: float = 44.7 # in seconds
    range_X_max: tuple[float, float] = (-45, 45.0)
    range_Y_Max: tuple[float, float] = (-37, 40)
    Y_Min_Max: tuple[float, float] = (72, 165)
    X_Min_Max: tuple[float,  float] = (-1, -1)

    Axis_X = {
        "defaultScanRange":{
            "min": -55.0,
            "max": 55.0
        },
        "startMax":23.0,
        "uiLimit":{
            "min": 0,
            "max": 180
        }
    }
    Axis_Y = {
        "defaultScanRange":{
            "min": -37.0,
            "max": 40.0
        },
        "startMax":23.0,
        "uiLimit":{
            "min": 72,
            "max": 165
        }
    }

    

@dataclass(frozen=True, slots=True)
class SystemConfig:
    tick_ms: int = 15  # 20 milliseconds per tick