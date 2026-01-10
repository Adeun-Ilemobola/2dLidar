# shared/protocol.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Union, Optional

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

Command = Union[EnableMotor, SetMotorAngle, SetMotorOffset, StartScan, StopScan]

# ---------- Events (embedded -> UI) ----------
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
    current: int
    total: int

Event = Union[MotorState, Log, ScanProgress]
