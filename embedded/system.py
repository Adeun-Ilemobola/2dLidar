# embedded/system.py
from __future__ import annotations

import random
from gpiozero import Device
from gpiozero.pins.lgpio import LGPIOFactory
from typing import Dict, List
from queue import Queue

from embedded.modules.motors import Motor, ServoConfig
from embedded.modules.vl53l1x_sensor import VL53L1XSensor , VL53L1XConfig
from shared.protocol import (
    Command, Event, Log,
    EnableMotor, ScanAreaGrid, SetMotorAngle, SetMotorOffset,
    StartScan, StopScan,
    MotorState, ScanProgress , PointState
)


def clamp(_max, val) -> float:
    return max(0.0, min(_max, val))
def clamp_range(min_val, val, max_val) -> float:
    return max(min_val, min(max_val, val))


class System:
    def __init__(self, event_q: "Queue[Event]"):
        self.event_Queue = event_q
        self.factory = LGPIOFactory()

        self.motors: Dict[str, Motor] = {
            "x": Motor(ServoConfig(pin=12), self.factory),
            "y": Motor(ServoConfig(pin=16), self.factory),
        }
        self.lidar =VL53L1XSensor(VL53L1XConfig())

        self.is_scanning = False
        self.step_size = 2
        self.scan_range_x = (-30.0, 30.0) 
        self.scan_range_y = (-20.0, 20.0)


        self.scan_x = 0.0
        self.scan_y = 0.0
        self.scan_direction = 1

        self.samples_point : List[PointState] = []
        self.point_grid : List[List[PointState]] = []



        # the test mode enables continuous movement for testing
        self.sleep_time_max_x = 2  # seconds
        self.sleep_time_max_y = 2.5  # seconds

        self.current_sleep_x = 0.0
        self.current_sleep_y = 0.0

        self.max_lap = 50
        self.current_lap = 0



        self.configure_all()

    def configure_all(self) -> None:
        """Home the system on startup."""
        self.motors["x"].enable(True)
        self.motors["y"].enable(True)
        
        # # Center the motors
        # self.motors["x"].set_angle(0)
        # self.motors["y"].set_angle(0)
        self.publish_motor("x")
        self.publish_motor("y")
       

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
            self.scan_x = self.scan_range_x[0]
            self.scan_y = self.scan_range_y[0]
            self.scan_direction = 1 
            self.event_Queue.put(Log("Scan started."))

        elif isinstance(cmd, StopScan):
            self.is_scanning = False
            self.event_Queue.put(Log("Scan stopped."))

        else:
            self.event_Queue.put(Log(f"Unknown command: {cmd!r}"))

    def tick(self) -> None:
        """Called repeatedly by the worker thread."""
        if  self.is_scanning:
            self.testScanMode()

    def testScanMode(self):

        if self.current_sleep_x < self.sleep_time_max_x:
            self.current_sleep_x += 0.07

            new_angle_x = clamp_range(
                -30.0 ,
                random.uniform(-30.0, 30.0),
                30.0
            )

            self.motors["x"].set_angle(new_angle_x)

        elif self.current_sleep_y < self.sleep_time_max_y:
            self.current_sleep_y += 0.07

            new_angle_y = clamp_range(
                -20.0 ,
                random.uniform(-20.0, 20.0),
                20.0
            )

            self.motors["y"].set_angle(new_angle_y)
        self.publish_motor("x")
        self.publish_motor("y")
        self.current_lap += 1
        if self.current_lap >= self.max_lap:
            self.current_lap = 0
            self.current_sleep_x = 0.0
            self.current_sleep_y = 0.0
            return


    def scan_mode(self):

        if self.is_scanning and not self.motors["x"].testMode and not self.motors["y"].testMode:
            self.event_Queue.put(Log("Scan started."))
            self.lidar.tick()

            if (not self.lidar.collecting) and (self.lidar.readyMm is None):
                self.lidar.request()
                return

            dist = self.lidar.take()
            if dist is None:
                return

            # get current motor angles
            current_x = self.motors["x"].get_angle()
            current_y = self.motors["y"].get_angle()

            # store the point
            self.samples_point.append(PointState(
                x=current_x,
                y=current_y,
                distant=dist
            ))

            # Calculate the next position
            next_x = self.scan_x + (self.step_size * self.scan_direction)

            # Check X Boundaries
            hit_right = (next_x >= self.scan_range_x[1])
            hit_left  = (next_x <= self.scan_range_x[0])

            if hit_right or hit_left:
            # We hit a wall: Time to move Y down and flip X direction
                self.scan_y += self.step_size
                self.scan_direction *= -1 # Flip direction
                self.point_grid.append(self.samples_point)
                self.samples_point = []  # Clear for next row
            # Clamp X to the edge so we don't overshoot
                self.scan_x = self.scan_range_x[1] if hit_right else self.scan_range_x[0]
            else:
            # Normal move
                self.scan_x = next_x
            

            # Check Y Boundaries
            if self.scan_y > self.scan_range_y[1]:
               self.is_scanning = False
               self.send_grid()
               self.event_Queue.put(Log("Scan Complete."))
               return
        
            self.motors["x"].set_angle(self.scan_x)
            self.motors["y"].set_angle(self.scan_y)
    
    def publish_motor(self, axis: str) -> None:
        m = self.motors[axis]
        self.event_Queue.put(MotorState(
            axis=axis,
            angle_deg=m.get_angle(),
            offset_deg=m.get_offset(),
            enabled=m.enabled,
        ))

    def send_grid(self) -> None:
        self.event_Queue.put(ScanAreaGrid(points=self.point_grid))
        self.point_grid = []  # Clear after sending
        #reinitialize for next scan
        self.scan_x = self.scan_range_x[0]
        self.scan_y = self.scan_range_y[0]
        self.scan_direction = 1
        self.motors["x"].set_angle(self.scan_x)
        self.motors["y"].set_angle(self.scan_y)
    
    # ---------- helpers ----------
    

