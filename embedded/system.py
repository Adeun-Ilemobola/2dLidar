# embedded/system.py
from __future__ import annotations
from gpiozero.pins.pigpio import PiGPIOFactory
from typing import Dict
from queue import Queue

from embedded.modules.motors import Motor, ServoConfig
from shared.protocol import (
    Command, Event, Log,
    EnableMotor, SetMotorAngle, SetMotorOffset,
    StartScan, StopScan,
    MotorState, ScanProgress
)

class System:
    def __init__(self, event_q: "Queue[Event]"):
        self.event_Queue = event_q
        self.factory = PiGPIOFactory()

        self.motors: Dict[str, Motor] = {
            "x": Motor(ServoConfig(pin=17), self.factory),
            "y": Motor(ServoConfig(pin=27), self.factory),
        }

        self.is_scanning = False
        self.max_scan_angle_deg_X = 40
        self.max_scan_angle_deg_Y = 40


        self.configure_all()

    def configure_all(self) -> None:
        self.motors["x"].enable(True)
        self.motors["y"].enable(True)
        self.event_Queue.put(Log("System configured."))

    def handle(self, cmd: Command) -> None:
        if isinstance(cmd, EnableMotor):
            m = self.motors[cmd.axis]
            m.enable(cmd.enabled)
            self.publish_motor(cmd.axis)

        elif isinstance(cmd, SetMotorAngle):
            m = self.motors[cmd.axis]
            m.set_angle(cmd.angle_deg)
            self.publish_motor(cmd.axis)

        elif isinstance(cmd, SetMotorOffset):
            m = self.motors[cmd.axis]
            m.set_offset(cmd.offset_deg)
            self.publish_motor(cmd.axis)

        elif isinstance(cmd, StartScan):
            self.is_scanning = True
            self.event_Queue.put(Log("Scan started."))

        elif isinstance(cmd, StopScan):
            self.is_scanning = False
            self.event_Queue.put(Log("Scan stopped."))

        else:
            self.event_Queue.put(Log(f"Unknown command: {cmd!r}"))

    def tick(self) -> None:
        """Called repeatedly by the worker thread."""
        if not self.is_scanning:
            return
        if not self.motors["x"].testMode and not self.motors["y"].testMode:
            return

        if self.is_scanning:
            self.event_Queue.put(Log("Scan started."))




    def publish_motor(self, axis: str) -> None:
        m = self.motors[axis]
        self.event_Queue.put(MotorState(
            axis=axis,
            angle_deg=m.get_angle(),
            offset_deg=m.get_offset(),
            enabled=m.enabled,
        ))
