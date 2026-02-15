# embedded/system.py
from __future__ import annotations
from math import dist
import time
import random
from typing import Optional , Dict

from typing import List
from queue import Queue
from shared.config import scanRange
from shared.time import Timer



from embedded.modules.motors import Motor, ServoConfig
from embedded.modules.vl53l1x_sensor import VL53L1XSensor , VL53L1XConfig
from shared.protocol import (
    Command, Event, Log,
    EnableMotor, MinMaxResult, ScanAreaGrid, SetMotorAngle, SetMotorOffset,
    StartScan, StopScan,
    MotorState, ScanProgress , PointState, continuous_mode, getRange , callRange , setStepSize
)



def clamp(_max, val) -> float:
    return max(0.0, min(_max, val))
def clamp_range(min_val, val, max_val) -> float:
    return max(min_val, min(max_val, val))


class System:
    def __init__(self, event_q: "Queue[Event]"):
        self.event_Queue = event_q
        self.scanRangeMas = scanRange()

       

        self.motors: Dict[str, Motor] = {
            "x": Motor(ServoConfig(channel=3),),
            "y": Motor(ServoConfig(channel=15), ),
        }
        self.lidar =VL53L1XSensor(VL53L1XConfig())

        self.is_scanning = False
        self.is_continuous_mode = False
        self.step_size = 2 # degrees 2
        self.scan_range_x = self.scanRangeMas.range_X_max
        self.scan_range_y = self.scanRangeMas.range_Y_Max


        self.scan_x = 0.0
        self.scan_y = 0.0
        self.scan_direction = 1

        self.samples_point : List[PointState] = []
        self.point_grid : List[List[PointState]] = []



        

        self.getRamge = False


        self.scan_start_time = None
        self.timer_av = False

        #  axis test mode, mini marks
        self.min_max_X = [-1.0, -1.0]
        self.min_max_Y = [-1.0, -1.0]
        self.rangeMax = 400
        self.rangeMin = 7.1
        self.test_MinMax = "stop" # "start" or "stop"
        self.test_axis = "x" # "x" or "y"
        self.max_cycle = 5
        self.cycle_count = 0



        self.configure_all()

    def configure_all(self) -> None:
        """Home the system on startup."""
        self.motors["x"].enable(True)
        self.motors["y"].enable(True)
        
        # # Center the motors
        self.motors["x"].set_angle(self.scan_range_x[0])
        self.motors["y"].set_angle(self.scan_range_y[1])
        self.publish_motor("x")
        self.publish_motor("y")
       

        self.event_Queue.put(Log("System configured."))

    
    def tick(self) -> None:
        """Called repeatedly by the worker thread."""
        self.lidar.tick()

        self.find_min_max_mode()

        if self.is_continuous_mode: 
             if (not self.lidar.collecting) and (self.lidar.readyMm is None):
                    self.lidar.request()
                    return

             get_distand = self.lidar.take()
             if get_distand is None:
                return
             self.event_Queue.put(getRange(distance=get_distand))
             self.lidar.reset()
             return
            


        if  self.is_scanning:
            if self.timer_av == False:
                self.timer_av = True
                self.event_Queue.put(ScanProgress(current=0, total=self.scanRangeMas.avg_scan_time, start =True))
                self.scan_start_time = time.perf_counter()

            self.scan_mode()
            return

        if self.getRamge:
           
            if not self.lidar.collecting and self.lidar.readyMm is None:
                self.lidar.request()
            if not self.lidar.collecting and self.lidar.readyMm is not None:
                self.event_Queue.put(getRange(distance=self.lidar.readyMm))
                self.getRamge = False
                self.event_Queue.put(Log("Range sent."))
                self.lidar.reset()


    def continuous_mode(self,) -> float | None:
        if (not self.lidar.collecting) and (self.lidar.readyMm is None):
            self.lidar.request()
            return None
        get_distand = self.lidar.take()
        if get_distand is None:
            return None
        self.lidar.reset()
        return get_distand
        
    def find_min_max_mode(self):
        if self.test_MinMax == "start":
            m = self.motors[self.test_axis]
            current_angle = m.get_angle()
            Direction = 1 
            if (current_angle >= 180.0):
                self.cycle_count += 1
                if self.cycle_count >= self.max_cycle:
                    self.test_MinMax = "stop"
                    self.cycle_count = 0
                    self.event_Queue.put(Log(f"Min-Max test completed for axis {self.test_axis}."))
                    self.event_Queue.put(MinMaxResult(max_angle=self.min_max_X[1], min_angle=self.min_max_X[0], distant=self.rangeMax, axis=self.test_axis, status="Done"))
                    # rest all

                    self.min_max_X = [-1.0, -1.0]
                    self.rangeMax = 400
                    self.rangeMin = 7.1

                    self.min_max_Y = [-1.0, -1.0]
                    self.rangeMax = 400
                    self.rangeMin = 7.1


                    return
                Direction = -1
            elif (current_angle >= 0.0):
                Direction = 1
               
            rang = self.continuous_mode()
            if rang is not None: 
                if rang > 7.0: # ignore extremely small numbers
                    if  self.test_axis == "x":
                        if rang > self.rangeMax:
                            self.rangeMax = rang
                            self.min_max_X[1] = current_angle
                        if rang < self.rangeMin:
                            self.rangeMin = rang
                            self.min_max_X[0] = current_angle
                    if  self.test_axis == "y":
                        if rang > self.rangeMax:
                            self.rangeMax = rang
                            self.min_max_Y[1] = current_angle
                        if rang < self.rangeMin:
                            self.rangeMin = rang
                            self.min_max_Y[0] = current_angle
            else:
                self.test_MinMax = "stop"
                self.event_Queue.put(Log(f"Min-Max test VALIDATION FAILED for axis {self.test_axis}."))
                self.event_Queue.put(MinMaxResult(max_angle=self.min_max_X[1], min_angle=self.min_max_X[0], distant=self.rangeMax, axis=self.test_axis, status="Error"))
                # rest all

                self.min_max_X = [-1.0, -1.0]
                self.rangeMax = 400
                self.rangeMin = 7.1

                self.min_max_Y = [-1.0, -1.0]
                self.rangeMax = 400
                self.rangeMin = 7.1

                m.set_angle(current_angle + self.step_size * Direction)
                self.event_Queue.put(MinMaxResult(max_angle=self.min_max_X[1], min_angle=self.min_max_X[0], distant=self.rangeMax, axis=self.test_axis, status="in progress"))
                self.publish_motor(self.test_axis)
    def scan_mode(self):

        if self.is_scanning and not self.motors["x"].testMode and not self.motors["y"].testMode:
           
            if (not self.lidar.collecting) and (self.lidar.readyMm is None):
                self.lidar.request()
                return

            dist = self.lidar.take()
            if dist is None:
                return
            
            self.lidar.request()

            # get current motor angles
            current_x = self.motors["x"].get_angle()
            current_y = self.motors["y"].get_angle()

            # store the point
            self.samples_point.append(PointState(
                x=current_x,
                y=current_y,
                distant=dist
            ))
            self.point_grid.append(self.samples_point)
            # Calculate the next position
            next_x = self.scan_x + (self.step_size * self.scan_direction)

            # Check X Boundaries
            hit_right = (next_x >= self.scan_range_x[1])
            hit_left  = (next_x <= self.scan_range_x[0])

            if hit_right or hit_left:
            # We hit a wall: Time to move Y down and flip X direction
                self.scan_y += self.step_size
                self.scan_direction *= -1 # Flip direction
                self.samples_point = []  # Clear for next row
            # Clamp X to the edge so we don't overshoot
                self.scan_x = self.scan_range_x[1] if hit_right else self.scan_range_x[0]
            else:
            # Normal move
                self.scan_x = next_x
            # Publish progress
            self.event_Queue.put(ScanProgress(
                current=time.perf_counter() - self.scan_start_time,
                total= self.scanRangeMas.avg_scan_time,
                start = True
            ))
           

            # Check Y Boundaries
            if self.scan_y == self.scan_range_y[1]:
               elapsed = time.perf_counter() - self.scan_start_time
               self.is_scanning = False
               self.send_grid()
               self.event_Queue.put(Log(f"Scan Complete. Elapsed time: {elapsed:.2f}s"))
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
        # self.event_Queue.put(ScanProgress(current=0, total=self.scanRangeMas.avg_scan_time, start=False))
        self.samples_point = []  # Clear after sending
        self.point_grid = []  # Clear after sending
        #reinitialize for next scan
        self.scan_x = self.scan_range_x[0]
        self.scan_y = self.scan_range_y[0]
        self.scan_start_time = None
        self.timer_av = False
        self.scan_direction = 1
        self.motors["x"].set_angle(self.scan_range_x[0])
        self.motors["y"].set_angle(self.scan_range_y[1])
        self.publish_motor("x")
        self.publish_motor("y")
    
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
        
        elif isinstance(cmd, callRange):
            self.getRamge = True
            self.event_Queue.put(Log("Range requested."))
        elif isinstance(cmd, setStepSize):
            if cmd.step_size <=0 or cmd.step_size > (self.scan_range_x[1] - self.scan_range_x[0]) or cmd.step_size > 5:
                self.event_Queue.put(Log(f"Invalid step size: {cmd.step_size}. Must be positive and within scan range."))
                return
            self.step_size = cmd.step_size
            self.event_Queue.put(Log(f"Step size set to {self.step_size} degrees."))
        elif isinstance(cmd, continuous_mode):
            self.is_continuous_mode = cmd.continuous_mode
            mode_str = "enabled" if self.is_continuous_mode else "disabled"
            self.event_Queue.put(Log(f"Continuous mode {mode_str}."))
        else:
            self.event_Queue.put(Log(f"Unknown command: {cmd!r}"))

    # ---------- helpers ----------
    

