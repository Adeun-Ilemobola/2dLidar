# embedded/system.py
from __future__ import annotations
import time
from typing import Dict, List
from queue import Queue

from shared.config import scanRange

from embedded.modules.motors import Motor, ServoConfig
from embedded.modules.vl53l1x_sensor import VL53L1XSensor, VL53L1XConfig
from shared.protocol import (
    CalibrationResult,
    Command,
    Event,
    Log,
    EnableMotor,
    sendMinMaxResult,
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
    clearZone ,
    startCalibration,
    stopCalibration

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

        # Find max and min range tracking
        self.calibration_mode = "stop"  # "stop" or "start"
        self.calibration_axis = "x"     # "x" or "y"
        self.calibration_range: Dict[str, List[PointState]] = {
            "x":[],
            "y":[]
        }
        self.Calibration_spike  ={
            "x":[0.0, 0.0],
            "y":[0.0, 0.0]
        }
    
        self.calibration_max_cycle = 5
        self.calibration_cycle_count = 0
        
        
        self.disamtTime = Timer(duration_s=0.03)  # 30ms between continuous readings

        self.configure_all()

    def configure_all(self) -> None:
        """Home the system on startup."""
        self.motors["x"].enable(True)
        self.motors["y"].enable(True)

        # Center / home
        self.motors["x"].set_angle(0)
        self.motors["y"].set_angle(0)
        self.motors["x"].set_offset(self.scanRangeMas.Axis_X["uiLimit"]["max"] / 2)
        self.motors["y"].set_offset(self.scanRangeMas.Axis_Y["uiLimit"]["max"] / 2) 

        # Min/Max mode starts with a fresh state, so we can call it here to set initial tracking values

        self.publish_motor("x")
        self.publish_motor("y")
        self.event_Queue.put(Log("System configured."))



    def tick(self) -> None:
        self.lidar.tick()

        self.Calibration_mode()

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
        
        
        
   
        
    def cal_Calibration_mode(self):
        print("Processing calibration data for axis:", self.calibration_axis)
       
        getarry = self.calibration_range[self.calibration_axis]
        if len(getarry) < 5:
            self.event_Queue.put(Log(f"No data collected for calibration on axis {self.calibration_axis}."))
            return
        tol = 40
        window_size = 3
        start_Point = None
        end_Point = None
             
        for i in range(1 ,len(getarry) - window_size ):
            prev = getarry[i - 1]
            curr = getarry[i]

            if start_Point is None:
                dif_prev = abs(curr.distant - prev.distant)

                #
                matches = [abs(getarry[i + j].distant - prev.distant) > tol for j in range(1, window_size + 1)]
            
                if dif_prev > tol and sum(matches) >= 2:
                    start_Point = curr
                    angle = curr.x if self.calibration_axis == "x" else curr.y
                    self.event_Queue.put(Log(f"Start edge detected at angle: {angle}"))
            elif end_Point is None:
                dif_prev = abs(curr.distant - prev.distant)
                matches = [abs(getarry[i + j].distant - curr.distant) <= tol for j in range(1, window_size + 1)]

            

                if dif_prev > tol and sum(matches) >= 2:
                    end_Point = curr
                    angle = curr.x if self.calibration_axis == "x" else curr.y
                    self.event_Queue.put(Log(f"End edge detected at angle: {angle}"))
                    break
        # --- Validation Logic ---
        if not start_Point or not end_Point:
            dists = [p.distant for p in getarry]
            self.event_Queue.put(Log(f"Calibration Failed. Axis {self.calibration_axis} range: {min(dists):.1f} to {max(dists):.1f}"))
            return
        

        start_angle = start_Point.x if self.calibration_axis == "x" else start_Point.y
        end_angle = end_Point.x if self.calibration_axis == "x" else end_Point.y
        low_angle, high_angle = sorted([start_angle, end_angle])

        print(f"Detected edges at angles: {low_angle}, {high_angle} for axis {self.calibration_axis}")

        if abs(high_angle - low_angle) < 1.0: # Minimum expected aperture width in degrees
            self.event_Queue.put(Log(f"Calibration error: Detected aperture on {self.calibration_axis} is too narrow."))
            return
        
        self.Calibration_spike[self.calibration_axis] = [low_angle, high_angle]

        if self.calibration_axis == "y":
            print(f"Calibration complete. X axis spike angles: {self.Calibration_spike['x']}, Y axis spike angles: {self.Calibration_spike['y']}")
            self.event_Queue.put(sendMinMaxResult(
                X=self.Calibration_spike["x"],
                Y=self.Calibration_spike["y"]
            ))



    def Calibration_mode(self):
        if self.calibration_mode != "start":
            return
        if self.calibration_cycle_count >= self.calibration_max_cycle:
            self.calibration_mode = "stop"
            self.calibration_cycle_count = 0
            msg = " next is Y axis" if self.calibration_axis == "x" else "All done!"
            self.event_Queue.put(
            Log(f"Calibration completed for axis {self.calibration_axis}.{msg}")
)
            if self.calibration_axis == "x":
                midpoint = (self.Calibration_spike["x"][0] + self.Calibration_spike["x"][1]) / 2
                self.motors["x"].set_offset(midpoint)   
                self.calibration_axis = "y"
                self.calibration_mode = "start"
            else:
                midpoint = (self.Calibration_spike["y"][0] + self.Calibration_spike["y"][1]) / 2
                self.motors["y"].set_offset(midpoint)
                self.calibration_mode = "stop"
                self.calibration_cycle_count = 0
                self.event_Queue.put(CalibrationResult(
                    success=True,
                    status="finished", # UI now knows to unlock buttons
                    message="System fully calibrated and homed."
                ))

            return

        m = self.motors[self.calibration_axis]
        current_angle = float(m.get_offset())
        rang = self.pump_lidar()

        if rang is not None:
            self.calibration_range[self.calibration_axis].append(PointState(
                x=current_angle if self.calibration_axis == "x" else 0.0,
                y=current_angle if self.calibration_axis == "y" else 0.0,
                distant=rang
            ))

        step_deg = 1.0
        dir = -1 if self.calibration_axis == "x" else 1  # X goes negative, Y goes positive
        next_angle = current_angle + (step_deg * dir)

        m.set_offset(next_angle)
        self.publish_motor(self.calibration_axis)
        if self.calibration_axis == "x":
            if next_angle <= 0.0:  # Completed a full cycle
                self.calibration_cycle_count += 1
                m.set_offset(self.scanRangeMas.Axis_X["uiLimit"]["max"] / 2)  # Reset to center
                self.cal_Calibration_mode()
                if self.calibration_cycle_count < self.calibration_max_cycle:
                    self.calibration_range[self.calibration_axis] = []  # Clear data for next cycle
              
        else:
            # Check for completion
            if next_angle >= 170.0:
                self.calibration_cycle_count += 1
                m.set_offset(64.6)  # Reset to start
                self.cal_Calibration_mode()
                if self.calibration_cycle_count < self.calibration_max_cycle:
                    self.calibration_range[self.calibration_axis] = []  # Clear data for next cycle
                  
               
        




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
        match cmd:
            case EnableMotor():
                data = cmd
                m = self.motors[data.axis]
                m.enable(data.enabled)
                self.publish_motor(data.axis)
                return

            case SetMotorAngle():
                data = cmd
                m = self.motors[data.axis]
                m.set_angle(data.angle_deg)
                self.publish_motor(data.axis)
                return

            case SetMotorOffset():
                data = cmd
                m = self.motors[data.axis]
                m.set_offset(data.offset_deg)
                self.publish_motor(data.axis)
                return

            case StartScan():
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

                # Move to start position
                self.motors["x"].set_angle(self.scan_x)
                self.motors["y"].set_angle(self.scan_y)
                self.publish_motor("x")
                self.publish_motor("y")
                return
            
            case StopScan():
                self.is_scanning = False
                self.timer_av = False
                self.scan_start_time = None
                self.event_Queue.put(ScanProgress(current=0, total=self.scanRangeMas.avg_scan_time, start=False))
                self.event_Queue.put(Log("Scan stopped."))
                return
            
            case callRange():
                self.getRamge = True
                return
            case setStepSize():
                data = cmd
                if (
                    data.step_size <= 0
                    or data.step_size > (self.scan_range_x[1] - self.scan_range_x[0])
                    or data.step_size > 5
                ):
                    self.event_Queue.put(
                        Log(f"Invalid step size: {data.step_size}. Must be positive and within scan range.")
                    )
                    return
                self.step_size = data.step_size 
                return
            case continuous_mode():
                data = cmd
                # Stop scan/minmax when continuous mode is enabled
                if data.continuous_mode:
                    self.is_scanning = False
                    self.test_MinMax = "stop"
                    self.getRamge = False
                    self.prev_Rangging = None
                    self.lidar.reset()
                    self.disamtTime.reset()
                self.is_continuous_mode = data.continuous_mode
                return
            case startCalibration():
                # reset any ongoing modes that could interfere with calibration
                self.is_scanning = False
                self.is_continuous_mode = False
                self.test_MinMax = "stop"
                self.getRamge = False
                self.prev_Rangging = None
                self.lidar.reset()
                self.disamtTime.reset()

              
                # reset scan state
                self.calibration_axis = "x"
                self.calibration_range = {"x": [], "y": []}
                self.Calibration_spike ={
                    "x": [0, 0 ],
                    "y": [0, 0 ]
                }
                self.calibration_cycle_count = 0



                self.calibration_mode = "start"
                self.event_Queue.put(CalibrationResult(
                    success=True,
                    status="started", 
                    message="Calibration sequence initiated."
                 ))
                return
            
            case stopCalibration():
                self.calibration_mode = "stop"
                self.event_Queue.put(CalibrationResult(
                    success=False,
                    status="failed",
                    message=f"Calibration stopped."
                ))
                return
            case findMinMax():
                data = cmd
                if data.action == "start":
                    self.test_MinMax = "start"
                    self.getRamge = False
                    self.prev_Rangging = None
                    self.lidar.reset()
                    self.disamtTime.reset()
                elif data.action == "stop":
                    self.test_MinMax = "stop"
                    self.getRamge = False
                    self.prev_Rangging = None
                    self.lidar.reset()
                    self.disamtTime.reset()
                return
            case ScanLimits():
                data = cmd
                self.limit_scam["X"]["min"] = data.X[0]
                self.limit_scam["X"]["max"] = data.X[1]
                self.limit_scam["Y"]["min"] = data.Y[0]
                self.limit_scam["Y"]["max"] = data.Y[1]  
                return
            case clearZone():
                self.limit_scam = {
                    "X":{
                        "min": self.scanRangeMas.range_X_max[0],
                        "max": self.scanRangeMas.range_X_max[1]
                    },
                    "Y":{
                        "min": self.scanRangeMas.range_Y_max[0],
                        "max": self.scanRangeMas.range_Y_max[1] 
                    }
                }
                return
            case _:
                self.event_Queue.put(Log(f"Unknown command: {cmd}"))


