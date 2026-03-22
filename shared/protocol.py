# shared/protocol.py
from __future__ import annotations
from dataclasses import dataclass, fields
from typing import List, Literal, Union, Optional

Axis = Literal["x", "y"]

# ---------- Commands (UI -> embedded) ----------
@dataclass(frozen=True, slots=True)
class EnableMotor:
    axis: Axis
    enabled: bool

@dataclass(frozen=True, slots=True)
class SetMotorAngle:
    axis: Axis
    angle_deg: float

@dataclass(frozen=True, slots=True)
class SetMotorOffset:
    axis: Axis
    offset_deg: float

@dataclass(frozen=True, slots=True)
class StartScan:
    pass

@dataclass(frozen=True, slots=True)
class StopScan:
    pass

@dataclass(frozen=True, slots=True)
class  stopCommands:
   pass

@dataclass(frozen=True, slots=True)
class resumeCommands:
   pass

@dataclass(frozen=True, slots=True)
class callRange:
    pass

@dataclass(frozen=True, slots=True)
class setStepSize:
    step_size : float

@dataclass(frozen=True, slots=True)
class continuous_mode:
    continuous_mode : bool


#  commands to find the minimum maximum for each axis, the Y axis, and the X axis
@dataclass(frozen=True, slots=True)
class findMinMax:
    axis : Axis
    action : Literal["start", "stop"]


@dataclass(frozen=True, slots=True)
class ScanLimits:
   X: tuple[float, float]
   Y: tuple[float, float]

@dataclass(frozen=True, slots=True)
class clearZone:
   pass

@dataclass(frozen=True, slots=True)
class startCalibration:
   pass 


Command = Union[EnableMotor, SetMotorAngle, SetMotorOffset, StartScan, StopScan , stopCommands , resumeCommands , callRange, setStepSize , continuous_mode , findMinMax, ScanLimits, clearZone, startCalibration]

# ---------- Events (embedded -> UI) ----------

# result of finding of them minimum on maximum range for the axis
@dataclass(frozen=True, slots=True)
class MinMaxResult:
    axis : Axis
    min_angle : float
    max_angle : float
    distant : float
    status : Literal["Idle", "Scanning", "Error" ,"Done" , "in progress"]
    



@dataclass(frozen=True, slots=True)
class MotorState:
    axis: Axis
    angle_deg: float
    offset_deg: float
    enabled: bool

@dataclass(frozen=True, slots=True)
class Log:
    message: str

@dataclass(frozen=True, slots=True)
class ScanProgress:
    current: float
    total: float
    start :bool

@dataclass(frozen=True, slots=True)
class PointState:
    x: float
    y: float
    distant: float

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def reset(self):
        for f in fields(self):
            setattr(self, f.name, f.default)


@dataclass(frozen=True, slots=True)
class ScanAreaGrid:
    points: List[PointState]

@dataclass(frozen=True, slots=True)
class getRange:
    distance : float


@dataclass(frozen=True, slots=True)
class CalibrationResult:
    success: bool
    message: Optional[str] = None

Event = Union[MotorState, Log, ScanProgress , PointState , ScanAreaGrid , getRange , MinMaxResult, CalibrationResult]


# ---------- universal types ----------


