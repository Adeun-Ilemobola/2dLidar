# embedded/system.py
from __future__ import annotations
import time
from typing import Dict, List
from queue import Queue

from shared.config import scanRange

from embedded.modules.motors import Motor, ServoConfig
from embedded.modules.vl53l1x_sensor import VL53L1XSensor, VL53L1XConfig
from shared.protocol import (
    Command,
    Event,
    Log,
    EnableMotor,
    MinMaxResult,
    ScanAreaGrid,
    SetMotorAngle,
    SetMotorOffset,
    StartScan,
    StopScan,
    MotorState,
    ScanProgress,
    PointState,
    continuous_mode,
    getRange,
    callRange,
    setStepSize,
    findMinMax,
    ScanLimits,
    clearZone

)
from shared.time import Timer


def clamp(_max, val) -> float:
    return max(0.0, min(_max, val))


def clamp_range(min_val, val, max_val) -> float:
    return max(min_val, min(max_val, val))


class System:
    def __init__(self, event_q: "Queue[Event]", scanRange_mas: scanRange):
        self.event_Queue = event_q
        self.scanRangeMas = scanRange_mas

        self.motors: Dict[str, Motor] = {
            "x": Motor(ServoConfig(channel=0)),
            "y": Motor(ServoConfig(channel=15)),
        }
        self.lidar = VL53L1XSensor(VL53L1XConfig())

        # General modes
        self.is_scanning = False
        self.is_continuous_mode = False
        self.getRamge = False  #

        # Scan config
        self.step_size = 2.0  # degrees
        self.scan_range_x = self.scanRangeMas.range_X_max
        self.scan_range_y = self.scanRangeMas.range_Y_Max
        self.limit_scam = {
            "X":{
                "min": self.scanRangeMas.range_X_max[0],
                "max": self.scanRangeMas.range_X_max[1]
            },
            "Y":{
                "min": self.scanRangeMas.Y_Min_Max[0],
                "max": self.scanRangeMas.Y_Min_Max[1]
            }
        }

        # Scan state
        self.Rangging =  self.pump_lidar()
        self.prev_Rangging = None

        self.scan_x = 0.0
        self.scan_y = 0.0
        self.scan_direction = 1

        self.samples_point: List[PointState] = []
        self.point_grid: List[List[PointState]] = []

        # Scan timing
        self.scan_start_time = None
        self.timer_av = False

        # Min/Max test mode state
        self.test_MinMax = "stop"       # "start" or "stop"
        self.test_axis = "x"            # "x" or "y"
        self.max_cycle = 5              # edge hits per axis
        self.rangeMax = float("-inf")
        self.rangeMin = float("inf")
        self.min_max_X_angle = [-1.0, -1.0]  # [min_angle, max_angle]
        self.min_max_Y_angle = [-1.0, -1.0]  # [min_angle, max_angle]
        self.cycle_count = 0
        self.test_direction = 1
        
        
        self.disamtTime = Timer(duration_s=0.03)  # 30ms between continuous readings

        self.configure_all()

    def configure_all(self) -> None:
        """Home the system on startup."""
        self.motors["x"].enable(True)
        self.motors["y"].enable(True)

        # Center / home
        self.motors["x"].set_angle(0)
        self.motors["y"].set_angle(0)
        self.motors["x"].set_offset(0)
        self.motors["y"].set_offset(self.scanRangeMas.Y_Min_Max[0])

        # Min/Max mode starts with a fresh state, so we can call it here to set initial tracking values

        self.publish_motor("x")
        self.publish_motor("y")
        self.event_Queue.put(Log("System configured."))



    def tick(self) -> None:
        self.lidar.tick()

        if self.test_MinMax == "start":
            self.find_min_max_mode()
            return

        if self.is_continuous_mode:
            self.handle_continuous_mode()
            return

        if self.is_scanning:
            if self.timer_av is False:
                self.timer_av = True
                self.event_Queue.put(
                    ScanProgress(current=0, total=self.scanRangeMas.avg_scan_time, start=True)
                )
                self.scan_start_time = time.perf_counter()

            self.scan_mode()
            return

        if self.getRamge:
            self.one_shot_range_mode()



    def handle_continuous_mode(self) -> None:
       
        reading = self.pump_lidar()

        if not self.disamtTime.running:
            self.disamtTime.start()

        if self.disamtTime.done():
            if reading is not None:
                if self.prev_Rangging is None or abs(reading - self.prev_Rangging) >= 0.6:
                    self.event_Queue.put(getRange(distance=reading))
                    self.prev_Rangging = reading

            self.disamtTime.reset()
            
            
            
    def pump_lidar(self) -> float | None:
        if not self.lidar.collecting and self.lidar.readyCm is None:
            self.lidar.request()
            return None

        reading = self.lidar.take_cm()
        if reading is None:
            return None

        self.lidar.reset()
        self.lidar.request()
        return reading
    
    
    def one_shot_range_mode(self) -> None:
        reading = self.pump_lidar()
        if reading is None:
            return

        self.event_Queue.put(getRange(distance=reading))
        self.getRamge = False
        self.event_Queue.put(Log("Range sent."))
        
        
        
        
    def find_min_max_mode(self):
        if self.test_MinMax != "start":
            return

        m = self.motors[self.test_axis]
        current_angle = float(m.get_offset())
        rang = self.pump_lidar()

        axis_min_max = self.min_max_Y_angle if self.test_axis == "y" else self.min_max_X_angle

        clip_angle_max = 77 if self.test_axis == "x" else self.scanRangeMas.Y_Min_Max[1]
        clip_angle_min = 0 if self.test_axis == "x" else self.scanRangeMas.Y_Min_Max[0]

        # Safe validity check
        is_valid_now = (rang is not None) and (rang > 16.0)

        # -----------------------------
        # Edge handling / sweep control
        # -----------------------------
        if current_angle >= clip_angle_max:
            self.test_direction = -1
            self.cycle_count += 1

            if self.cycle_count >= self.max_cycle:
                self.test_MinMax = "stop"
                self.cycle_count = 0

                self.event_Queue.put(Log(f"Min-Max test completed for axis {self.test_axis}."))
                self.event_Queue.put(
                    MinMaxResult(
                        max_angle=axis_min_max[1],
                        min_angle=axis_min_max[0],
                        distant=rang if rang is not None else 0.0,
                        axis=self.test_axis,
                        status="Done",
                    )
                )

                # Reset tracking values
                self.min_max_X_angle = [-1.0, -1.0]
                self.min_max_Y_angle = [-1.0, -1.0]

                # Restore your default/normal values
                self.rangeMax = 400
                self.rangeMin = 1.50

                # Reset offsets (your chosen "visual center-ish" values)
                xOffset = 79
                yOffset = 124.1
                m.set_offset(xOffset if self.test_axis == "x" else yOffset)
                self.publish_motor(self.test_axis)
                return

        elif current_angle <= clip_angle_min:
            self.test_direction = 1
            self.cycle_count += 1

        # -----------------------------
        # Update min/max only if valid
        # -----------------------------
        if is_valid_now:
            self.event_Queue.put(
                Log(
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
                )
            )

            # Track max range
            if rang > self.rangeMax:
                self.rangeMax = rang
                axis_min_max[1] = current_angle

            # Track min range
            if rang < self.rangeMin:
                self.rangeMin = rang
                axis_min_max[0] = current_angle

            self.event_Queue.put(
                MinMaxResult(
                    max_angle=axis_min_max[1],
                    min_angle=axis_min_max[0],
                    distant=rang,
                    axis=self.test_axis,
                    status="in progress",
                )
            )

        # -----------------------------
        # ALWAYS move motor
        # -----------------------------
        step_deg = 1.0
        next_angle = current_angle + (step_deg * self.test_direction)

        if self.test_axis == "y":
            next_angle = min(
                self.scanRangeMas.Y_Min_Max[1],
                max(self.scanRangeMas.Y_Min_Max[0], next_angle),
            )
        else:
            next_angle = min(77, max(0, next_angle))

        m.set_offset(next_angle)
        self.publish_motor(self.test_axis)






    def scan_mode(self):
        if self.is_scanning and not self.motors["x"].testMode and not self.motors["y"].testMode:
           

            dist_val = self.pump_lidar()
           
            if dist_val is None:
                return

            # Current motor angles
            current_x = self.motors["x"].get_angle()
            current_y = self.motors["y"].get_angle()

            # Store point in current row
            self.samples_point.append(PointState(
                x=current_x,
                y=current_y,
                distant=dist_val
            ))

            # Calculate next X
            next_x = self.scan_x + (self.step_size * self.scan_direction)

            hit_right = next_x >= self.limit_scam["X"]["max"]
            hit_left = next_x <= self.limit_scam["X"]["min"]

            if hit_right or hit_left:
                # Finish the current row before moving Y
                if self.samples_point:
                    # self.point_grid.append(self.samples_point)
                    # self.samples_point = []
                    pass

                # Move Y
                self.scan_y += self.step_size
                self.scan_direction *= -1

                # Clamp X to the edge
                self.scan_x = self.limit_scam["X"]["max"] if hit_right else self.limit_scam["X"]["min"]
            else:
                self.scan_x = next_x

            # Progress update
            self.event_Queue.put(
                ScanProgress(
                    current=time.perf_counter() - self.scan_start_time,
                    total=self.scanRangeMas.avg_scan_time,
                    start=True,
                )
            )

            # Check Y completion (use >= to avoid float/step mismatch issues)
            if self.scan_y >= self.limit_scam["Y"]["max"]:
                # If final row has points (edge cases), append it
                # if self.samples_point:
                #     self.point_grid.append(self.samples_point)
                #     self.samples_point = []

                elapsed = time.perf_counter() - self.scan_start_time
                self.is_scanning = False
                self.send_grid()
                self.event_Queue.put(Log(f"Scan Complete. Elapsed time: {elapsed:.2f}s"))
                return

            # Move motors to next scan position
            self.motors["x"].set_angle(self.scan_x)
            self.motors["y"].set_angle(self.scan_y)

    def publish_motor(self, axis: str) -> None:
        m = self.motors[axis]
        self.event_Queue.put(
            MotorState(
                axis=axis,
                angle_deg=m.get_angle(),
                offset_deg=m.get_offset(),
                enabled=m.enabled,
            )
        )

    def send_grid(self) -> None:
        self.event_Queue.put(ScanAreaGrid(points=self.samples_point))
        self.event_Queue.put(ScanProgress(current=0, total=self.scanRangeMas.avg_scan_time, start=False))

        self.samples_point = []
        self.point_grid = []

        # Reinitialize for next scan
        self.scan_x = self.scan_range_x[0]
        self.scan_y = self.scan_range_y[0]
        self.scan_start_time = None
        self.timer_av = False
        self.scan_direction = 1

        self.motors["x"].set_angle(self.scan_range_x[0])
        self.motors["y"].set_angle(self.scan_range_y[1])  # your original behavior
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
            # Stop other modes
            self.is_continuous_mode = False
            self.test_MinMax = "stop"

            # Reset scan state
            self.is_scanning = True
            self.scan_x = self.scan_range_x[0]
            self.scan_y = self.scan_range_y[0]
            self.scan_direction = 1
            self.samples_point = []
            self.point_grid = []
            self.scan_start_time = None
            self.timer_av = False
            
            
            self.getRamge = False
            self.lidar.reset()
            self.lidar.request()

            # Move to start position
            self.motors["x"].set_angle(self.scan_x)
            self.motors["y"].set_angle(self.scan_y)
            self.publish_motor("x")
            self.publish_motor("y")

            self.event_Queue.put(Log("Scan started."))

        elif isinstance(cmd, StopScan):
            self.is_scanning = False
            self.timer_av = False
            self.scan_start_time = None
            self.event_Queue.put(ScanProgress(current=0, total=self.scanRangeMas.avg_scan_time, start=False))
            self.event_Queue.put(Log("Scan stopped."))

        elif isinstance(cmd, callRange):
            self.getRamge = True
            self.event_Queue.put(Log("Range requested."))

        elif isinstance(cmd, setStepSize):
            if (
                cmd.step_size <= 0
                or cmd.step_size > (self.scan_range_x[1] - self.scan_range_x[0])
                or cmd.step_size > 5
            ):
                self.event_Queue.put(
                    Log(f"Invalid step size: {cmd.step_size}. Must be positive and within scan range.")
                )
                return

            self.step_size = cmd.step_size
            self.event_Queue.put(Log(f"Step size set to {self.step_size} degrees."))

        elif isinstance(cmd, continuous_mode):
            
            # Stop scan/minmax when continuous mode is enabled
            if cmd.continuous_mode:
                self.is_scanning = False
                self.test_MinMax = "stop"
                self.getRamge = False
                self.prev_Rangging = None
                self.lidar.reset()
                self.disamtTime.reset()

            self.is_continuous_mode = cmd.continuous_mode
            mode_str = "enabled" if self.is_continuous_mode else "disabled"
            self.event_Queue.put(Log(f"Continuous mode {mode_str}."))

        elif isinstance(cmd, findMinMax):
            if cmd.action == "start":
                # Stop other modes
                self.is_scanning = False
                self.is_continuous_mode = False
                
                self.getRamge = False
                self.lidar.reset()
                self.lidar.request()

                self.test_MinMax = "start"
                self.test_axis = cmd.axis

                # Initialize Min/Max tracking fresh
                self.cycle_count = 0
                self.test_direction = 1
                self.rangeMax = float("-inf")
                self.rangeMin = float("inf")
                self.min_max_X_angle = [-1.0, -1.0]
                self.min_max_Y_angle = [-1.0, -1.0]

                self.event_Queue.put(Log(f"Find Min Max started on axis {cmd.axis}."))

            elif cmd.action == "stop":
                self.test_MinMax = "stop"
                self.test_axis = cmd.axis
                self.event_Queue.put(Log(f"Find Min Max stopped on axis {cmd.axis}."))
        elif isinstance(cmd, ScanLimits):
            self.limit_scam["X"]["min"] = cmd.X[0]
            self.limit_scam["X"]["max"] = cmd.X[1]
            self.limit_scam["Y"]["min"] = cmd.Y[0]
            self.limit_scam["Y"]["max"] = cmd.Y[1]

            self.event_Queue.put(
                Log(
                    f"Scan limits updated. X: [{cmd.X[0]:.2f}, {cmd.X[1]:.2f}], Y: [{cmd.Y[0]:.2f}, {cmd.Y[1]:.2f}]"
                )
            )
        elif isinstance(cmd, clearZone):
            self.limit_scam = {
            "X":{
                "min": self.scanRangeMas.range_X_max[0],
                "max": self.scanRangeMas.range_X_max[1]
            },
            "Y":{
                "min": self.scanRangeMas.Y_Min_Max[0],
                "max": self.scanRangeMas.Y_Min_Max[1]
            }
        }
            self.event_Queue.put(Log("Scan limits reset to default."))
            
        else:
            self.event_Queue.put(Log(f"Unknown command: {cmd!r}"))