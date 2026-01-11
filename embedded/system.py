# embedded/system.py
from __future__ import annotations

import random

from gpiozero.pins.pigpio import PiGPIOFactory
from typing import Dict
from queue import Queue

from embedded.modules.motors import Motor, ServoConfig
from shared.protocol import (
    Command, Event, Log,
    EnableMotor, SetMotorAngle, SetMotorOffset,
    StartScan, StopScan,
    MotorState, ScanProgress , PointState
)


def clap(_max, val) -> float:
    return max(0.0, min(_max, val))


class System:
    def __init__(self, event_q: "Queue[Event]"):
        self.event_Queue = event_q
        self.factory = PiGPIOFactory()

        self.motors: Dict[str, Motor] = {
            "x": Motor(ServoConfig(pin=17), self.factory),
            "y": Motor(ServoConfig(pin=27), self.factory),
        }

        self.is_scanning = False
        self.max_step = 2
        self.max_scan_angle_deg_X = 40 / self.max_step
        self.max_scan_angle_deg_Y = 40  / self.max_step
        self.current_X = 0
        self.current_Y = 0
        self.Finished_firstNode =True
        self.move_axis_y = False

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
        if  self.is_scanning:
            self.scan_mode()



    def scan_mode(self):

        if self.is_scanning and not self.motors["x"].testMode and not self.motors["y"].testMode:
            temp_disant_list = []
            point = PointState(x=0, y=0, distant=0)
            self.event_Queue.put(Log("Scan started."))
            # get two or three distant numbers and get the average if index one and index are the same just use the common one
            for _ in range(3):
                # get the distant
                get_Distant = random.randint(10, 400)
                point.update(distance=get_Distant)
                temp_disant_list.append(point.distant)

                # check if the array has two items then check if they're the same if they're the same use that value as the distant
                if len(temp_disant_list) == 2:
                    if temp_disant_list[0] == temp_disant_list[1]:
                        print("[]: filter distant is the same for two items")
                        point.update(distant=get_Distant)
                        break
            else:
                # get the average distance of the three-point to create a true distance
                point.update(distant=sum(temp_disant_list) / 3)

            # Store the X and Y coordinates and the distant
            point.update(x=self.motors["x"].get_angle() * 2, y=self.motors["y"].get_angle() * 2)

            # move the X and Y coordinate by its step
            self.current_X += 1
            self.motors["x"].set_angle(clap(self.max_scan_angle_deg_X,
                                            self.motors["x"].get_angle() + (self.max_step * self.flip_axis_x())))

            # make sure when the X is at the last step move down, and when it reaches the final step and the scan
            if not self.Finished_firstNode:
                if not self.current_Y == self.max_scan_angle_deg_Y:
                    if self.move_axis_y:
                        self.current_Y += 1
                        self.motors["y"].set_angle(self.motors["y"].get_angle() - self.max_step)
                else:
                    self.is_scanning = False
            # after completing a point stort the point in an array

            self.Finished_firstNode = False

    def flip_axis_x(self) -> int:
           if self.Finished_firstNode:
               self.move_axis_y = False
               return 1
           else:
               if self.current_X == 0:
                   self.move_axis_y = True
                   return 1
               elif self.current_X == self.max_scan_angle_deg_X:
                   self.move_axis_y = True
                   return -1
               else:
                   self.move_axis_y = False
                   return 1

    def publish_motor(self, axis: str) -> None:
        m = self.motors[axis]
        self.event_Queue.put(MotorState(
            axis=axis,
            angle_deg=m.get_angle(),
            offset_deg=m.get_offset(),
            enabled=m.enabled,
        ))
