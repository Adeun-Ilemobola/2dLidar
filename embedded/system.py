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
    MotorState, ScanProgress , PointState, continuous_mode, getRange , callRange , setStepSize ,findMinMax
)



def clamp(_max, val) -> float:
    return max(0.0, min(_max, val))
def clamp_range(min_val, val, max_val) -> float:
    return max(min_val, min(max_val, val))


class System:
    def __init__(self, event_q: "Queue[Event]" , scanRange_mas: scanRange):
        self.event_Queue = event_q
        self.scanRangeMas = scanRange_mas

       

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
        self.rangeMax = float("-inf")
        self.rangeMin = float("inf")
        self.min_max_X_angle = [-1.0, -1.0]
        self.min_max_Y_angle = [-1.0, -1.0]
        self.cycle_count = 0
        self.test_direction = 1



        self.configure_all()

    def configure_all(self) -> None:
        """Home the system on startup."""
        self.motors["x"].enable(True)
        self.motors["y"].enable(True)
        
        # # Center the motors
        self.motors["x"].set_angle(0)
        self.motors["y"].set_angle(0)
        self.motors["x"].set_offset(0)
        self.motors["y"].set_offset(self.scanRangeMas.Y_Min_Max[0])
        self.publish_motor("x")
        self.publish_motor("y")
       

        self.event_Queue.put(Log("System configured."))

    
    def tick(self) -> None:
        """Called repeatedly by the worker thread."""
        self.lidar.tick()

        if self.test_MinMax == "start":
            self.find_min_max_mode()
            return


     

        if self.is_continuous_mode: 
             print("-------continuous mode-------")
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
            print("------scan mode-----")
            if self.timer_av == False:
                self.timer_av = True
                self.event_Queue.put(ScanProgress(current=0, total=self.scanRangeMas.avg_scan_time, start =True))
                self.scan_start_time = time.perf_counter()

            self.scan_mode()
            return

        if self.getRamge:
            print("------get range----")
           
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
        if self.test_MinMax != "start":
            return

        m = self.motors[self.test_axis]
        current_angle = m.get_offset()
        rang = self.continuous_mode()

        axis_min_max = self.min_max_Y_angle if self.test_axis == "y" else self.min_max_X_angle

        clip_angle_max = 77 if self.test_axis == "x" else self.scanRangeMas.Y_Min_Max[1]
        clip_angle_min = 0 if self.test_axis == "x" else self.scanRangeMas.Y_Min_Max[0]

    # Safe validity check
        is_valid_now = (rang is not None) and (rang > 16.0)

    # Edge handling
        if current_angle >= clip_angle_max:
            self.test_direction = -1
            self.cycle_count += 1

        if self.cycle_count >= self.max_cycle:
            self.test_MinMax = "stop"
            self.cycle_count = 0

            self.event_Queue.put(Log(f"Min-Max test completed for axis {self.test_axis}."))
            self.event_Queue.put(MinMaxResult(
                max_angle=axis_min_max[1],
                min_angle=axis_min_max[0],
                distant=rang if rang is not None else 0.0,
                axis=self.test_axis,
                status="Done"
            ))

            # Reset tracking values
            self.min_max_X_angle = [-1.0, -1.0]
            self.min_max_Y_angle = [-1.0, -1.0]

            # Normal mode defaults (make sure your test-start code reinitializes these!)
            self.rangeMax = 400
            self.rangeMin = 1.50

            # Reset offsets to visual center-ish
            xOffset = 79
            yOffset = 124.1
            m.set_offset(xOffset if self.test_axis == "x" else yOffset)
            return

        elif current_angle <= clip_angle_min:
            self.test_direction = 1
            self.cycle_count += 1

    # Only update min/max if the reading is valid
        if is_valid_now:
            self.event_Queue.put(Log(
            f"""
    Axis {self.test_axis}
    range is {rang}.
    ----------------------
    Min angle is {axis_min_max[0]}.
    Max angle is {axis_min_max[1]}.
    ----------------------
    max range is {self.rangeMax}
    min range is {self.rangeMin}
    ----------------------
    current angle is {current_angle}
    direction is {self.test_direction}
    ----------------------
    max cycle is {self.max_cycle}
    cycle count is {self.cycle_count}
    ----------------------
    """
            ))

        if self.test_axis == "x":
            if rang > self.rangeMax:
                self.rangeMax = rang
                self.min_max_X_angle[1] = current_angle

            # Track smallest VALID range
            if rang < self.rangeMin:
                self.rangeMin = rang
                self.min_max_X_angle[0] = current_angle

        else:  # y axis
            if rang > self.rangeMax:
                self.rangeMax = rang
                self.min_max_Y_angle[1] = current_angle

            # Track smallest VALID range
            if rang < self.rangeMin:
                self.rangeMin = rang
                self.min_max_Y_angle[0] = current_angle

        self.event_Queue.put(MinMaxResult(
            max_angle=axis_min_max[1],
            min_angle=axis_min_max[0],
            distant=rang,
            axis=self.test_axis,
            status="in progress"
        ))

    # ALWAYS move motor (even when reading is invalid)
        next_angle = current_angle + (1 * self.test_direction)

        if self.test_axis == "y":
            next_angle = min(self.scanRangeMas.Y_Min_Max[1], max(self.scanRangeMas.Y_Min_Max[0], next_angle))
        else:
            next_angle = min(77, max(0, next_angle))

        m.set_offset(next_angle)
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
        elif isinstance(cmd, findMinMax):
            if cmd.action == "start":
                self.test_MinMax = "start"
                self.test_axis = cmd.axis
                self.event_Queue.put(Log("Find Min Max started."))
            elif cmd.action == "stop":
                self.test_MinMax = "stop"
                self.test_axis = cmd.axis
                self.event_Queue.put(Log("Find Min Max stopped."))
        else:
            self.event_Queue.put(Log(f"Unknown command: {cmd!r}"))

    # ---------- helpers ----------
    

