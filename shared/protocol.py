# shared/protocol.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Union

Axis = Literal["x", "y"]

# Shared type used by BOTH UI and embedded
@dataclass(frozen=True, slots=True)
class Point:
    x: float
    y: float
    z: float
    is_void: bool = False

# -----------------
# Commands (UI -> System)
# -----------------
@dataclass(frozen=True, slots=True)
class MotorAngleState:
    axis: Axis
    angle_deg: float
    offset_deg: float
    enabled: bool

@dataclass(frozen=True, slots=True)
class EnableMotor:
    axis: Axis
    enabled: bool

Command = Union[MotorAngleState, EnableMotor]

# -----------------
# Events (System -> UI)
# -----------------



Event = Union[MotorAngleState , MotorAngleState]
