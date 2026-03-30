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
        self.step_size = 1  # degrees
        self.scan_range_x = self.scanRangeMas.Axis_X["systemLimit"]
        self.scan_range_y = self.scanRangeMas.Axis_Y["systemLimit"]
        self.limit_scam = {
            "X":{
                "min": self.scanRangeMas.Axis_X["systemLimit"]["min"],
                "max": self.scanRangeMas.Axis_X["systemLimit"]["max"]
            },
            "Y":{
                "min": self.scanRangeMas.Axis_Y["systemLimit"]["min"],
                "max": self.scanRangeMas.Axis_Y["systemLimit"]["max"]
            }
        }
        self.Y_FLAT = self.scanRangeMas.Axis_Y["uiLimit"]["max"] / 2

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


        # Find max and min range tracking
        self.calibration_mode = "stop"  # "stop" or "start"
        self.calibration_axis = "x"     # "x" or "y"
        self.calibration_range: Dict[str, List[PointState]] = {
            "x":[],
            "y":[]
        }
        self.calibration_spike  ={
            "x":[0.0, 0.0],
            "y":[0.0, 0.0]
        }
        self.calibration_results = {
            "x": [],
            "y": []
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
       
        points = self.calibration_range[self.calibration_axis]
        if len(points) < 8:  # Not enough data points to analyze
            self.event_Queue.put(Log(f"No data collected for calibration on axis {self.calibration_axis}."))
            return
        
        tol = 40  # Minimum distance change to consider as an edge, in cm
        window_size = 3  # Number of points to look back for edge detection
        start_Point = None # the point where we first detect a significant increase in distance (start of aperture)
        end_Point = None # the point where we first detect a significant decrease in distance (end of aperture)
             
        for i in range(1 ,len(points) - window_size ):
            prev = points[i - 1]
            curr = points[i]

            if start_Point is None:
                dif_prev = (curr.distant - prev.distant)
            
                if dif_prev > tol :
                    start_Point = prev
                    angle = prev.x if self.calibration_axis == "x" else prev.y
                    self.event_Queue.put(Log(f"Start edge detected at angle: {angle}"))
                    continue  # Look for end point after finding start
                
                
            if  start_Point is not None and end_Point is None:
                
                dif_prev = (curr.distant - prev.distant)

                if -dif_prev > tol :
                    end_Point = curr
                    angle = curr.x if self.calibration_axis == "x" else curr.y
                    self.event_Queue.put(Log(f"End edge detected at angle: {angle}"))
                    break
                
                
        self.calibration_range[self.calibration_axis] = []  # Clear data for next calibration run
        # --- Validation Logic ---
        if not start_Point or not end_Point:
            dists = [p.distant for p in points]
            self.event_Queue.put(Log(f"Calibration Failed. Axis {self.calibration_axis} range: {min(dists):.1f} to {max(dists):.1f}"))
            return
        

        start_angle = start_Point.x if self.calibration_axis == "x" else start_Point.y
        end_angle = end_Point.x if self.calibration_axis == "x" else end_Point.y
        low_angle, high_angle = sorted([start_angle, end_angle])
        
       

        if abs(high_angle - low_angle) < 1.0: # Minimum expected aperture width in degrees
            self.event_Queue.put(Log(f"Calibration error: Detected aperture on {self.calibration_axis} is too narrow."))
            return
        
        self.calibration_results[self.calibration_axis].append([low_angle, high_angle])
        self.calibration_spike[self.calibration_axis] = [low_angle, high_angle]

        print(f"Detected edges at angles: {low_angle}, {high_angle} for axis {self.calibration_axis}")

       



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
            results = self.calibration_results[self.calibration_axis]
            if not results:
                # fail axis and stop
                self.event_Queue.put(Log(f"Calibration failed for axis {self.calibration_axis}. No valid edges detected."))
                self.event_Queue.put(CalibrationResult(
                    success=False,
                    status="failed",
                    message=f"Calibration failed for axis {self.calibration_axis}. No valid edges detected."
                ))
                return
            
            avg_low = sum(r[0] for r in results) / len(results)
            avg_high = sum(r[1] for r in results) / len(results)
            self.calibration_spike[self.calibration_axis] = [avg_low, avg_high]
            midpoint = (avg_low + avg_high) / 2
            print(
                f"-----------------------{self.calibration_axis}-----------------------\n"
                f"Calibration cycle {self.calibration_cycle_count} complete for axis {self.calibration_axis}. "
                f"Avg edges at: {avg_low:.2f}, {avg_high:.2f}. Midpoint: {midpoint:.2f}",
                "--------------------------------------------------------------------------"
            )
            
            
            
            if self.calibration_axis == "x":
                self.motors["x"].set_offset(midpoint)   
                self.calibration_axis = "y"
                self.motors["y"].set_offset(0)  # Start Y at 0 to find the aperture
                self.calibration_mode = "start"
                
                
            elif self.calibration_axis == "y":
                y_low, y_high = self.calibration_spike["y"]
                self.motors["y"].set_offset(self.Y_FLAT)  # Set Y to flat position after calibration
                self.motors["y"].set_angle(0)  # Set Y to flat position after calibration
                self.motors["x"].set_angle(0)  # Set X to flat position after calibration

                # -------------------------------------------------------------

                self.calibration_mode = "stop"
                self.calibration_cycle_count = 0
                
              
                x_offset = self.motors["x"].get_offset()
                self.limit_scam["X"]["min"] = self.calibration_spike["x"][0] - x_offset
                self.limit_scam["X"]["max"] = self.calibration_spike["x"][1] - x_offset

                y_offset = self.motors["y"].get_offset()
                self.limit_scam["Y"]["min"] = y_low - y_offset
                self.limit_scam["Y"]["max"] = y_high - y_offset



                self.publish_motor("x")
                self.publish_motor("y")
                
                # Notify UI of the new "Plus/Minus" range
                self.event_Queue.put(sendMinMaxResult(
                   Xmin=self.limit_scam["X"]["min"],
                   Xmax=self.limit_scam["X"]["max"],
                   Ymin=self.limit_scam["Y"]["min"],
                   Ymax=self.limit_scam["Y"]["max"]
                ))

                self.event_Queue.put(CalibrationResult(
                    success=True,
                    status="finished",
                    message=f"Calibration completed for axis {self.calibration_axis}."
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
        direction = -1 if self.calibration_axis == "x" else 1  # X goes negative, Y goes positive
        next_angle = current_angle + (step_deg * direction)

        m.set_offset(next_angle)
        self.publish_motor(self.calibration_axis)
        if self.calibration_axis == "x":
            if next_angle <= 0.0:  # Completed a full cycle
                self.calibration_cycle_count += 1
                m.set_offset(self.scanRangeMas.Axis_X["uiLimit"]["max"] / 2)  # Reset to center
                self.cal_Calibration_mode()
               
              
        else:
            # Check for completion
            if next_angle >= 174.0:
                self.calibration_cycle_count += 1
                self.motors["y"].set_offset(0)  # Reset to start
                self.cal_Calibration_mode()
               
                  
               
        




    def scan_mode(self):
        if self.is_scanning and not self.motors["x"].testMode and not self.motors["y"].testMode:
           

            dist_val = self.pump_lidar()
            if dist_val is None:
                return

            # Current motor angles
            self.samples_point.append(PointState(
            x=self.scan_x,
            y=self.scan_y,
            distant=dist_val
        ))

            # Calculate next X
            next_x = self.scan_x + (self.step_size * self.scan_direction)

            hit_right = next_x >= self.limit_scam["X"]["max"]
            hit_left = next_x <= self.limit_scam["X"]["min"]

            if hit_right or hit_left:
                self.scan_y += self.step_size
                self.scan_direction *= -1

                # Clamp X to the edge
                # self.scan_x = self.limit_scam["X"]["max"] if hit_right else self.limit_scam["X"]["min"]
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
                elapsed = time.perf_counter() - self.scan_start_time
                self.is_scanning = False
                self.send_grid()
                self.event_Queue.put(Log(f"Scan Complete. Elapsed time: {elapsed:.2f}s"))
                return

            # Move motors to next scan position
            self.motors["x"].set_angle(self.scan_x)
            self.motors["y"].set_angle(self.scan_y)

            self.event_Queue.put(ScanProgress(
            current=time.perf_counter() - self.scan_start_time,
            total=self.scanRangeMas.avg_scan_time,
            start=True
        ))

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
        self.scan_x = self.limit_scam["X"]["min"]
        self.scan_y = self.limit_scam["Y"]["min"]
        
        self.motors["x"].set_angle(self.scan_x)
        self.motors["y"].set_angle(self.scan_y)
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


                self.is_scanning = True
                self.scan_x = self.limit_scam["X"]["min"] 
                self.scan_y = self.limit_scam["Y"]["min"]
                self.scan_direction = 1
                
                # Move to start position immediately
                self.motors["x"].set_angle(self.scan_x)
                self.motors["y"].set_angle(self.scan_y)
                self.publish_motor("x")
                self.publish_motor("y")

              
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
                    or data.step_size > (self.scan_range_x["max"] - self.scan_range_x["min"])
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
                
                self.is_scanning = False
                self.is_continuous_mode = False
                self.test_MinMax = "stop"
                self.getRamge = False
                self.prev_Rangging = None
                self.lidar.reset()
                self.disamtTime.reset()

                self.calibration_axis = "x"
                self.calibration_range = {"x": [], "y": []}
                self.calibration_spike = {
                    "x": [0.0, 0.0],
                    "y": [0.0, 0.0],
                }
                self.calibration_results = {
                    "x": [],
                    "y": []
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
                        "min": self.scanRangeMas.Axis_X["systemLimit"]["min"],
                        "max": self.scanRangeMas.Axis_X["systemLimit"]["max"]
                    },
                    "Y":{
                        "min": self.scanRangeMas.Axis_Y["systemLimit"]["min"],
                        "max": self.scanRangeMas.Axis_Y["systemLimit"]["max"] 
                    }
                }
                return
            case _:
                self.event_Queue.put(Log(f"Unknown command: {cmd}"))


