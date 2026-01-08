# embedded/system.py

from gpiozero.pins.pigpio import PiGPIOFactory
from embedded.bus import EventBus
from embedded.modules.motors import Motor , ServoConfig
from shared.protocol import Command, EnableMotor ,MotorAngleState
from typing import List

class System:
    def __init__(self, bus: EventBus) -> None:
        self.bus = bus
        self.factory = PiGPIOFactory()
        self.isScaning = False
        self.motors = {
            "x": Motor(ServoConfig(pin=17), self.factory),
            "y": Motor(ServoConfig(pin=27), self.factory),
        }
        self.configure_all()

    def configure_all(self) -> None:
        self.motors["x"].enable(True)
        self.motors["y"].enable(True)

        pass

    def mainLoop(self) -> None:
        if not self.isScaning:
            return
        AverageDistance: List[float] = []
        while True:
            if not self.isScaning:
                break
    #         collect and store 2 to 3 scans of the sensor in a for loop
    #          then move the X coordinates by the step value of 2°
    #           after reaching the maximum degrees for the X axis keep the last X axis, then move the Y axis


    def handle(self, cmd: Command) -> None:
        """Single entry point for UI commands."""
        if isinstance(cmd, MotorAngleState):
            self.motors[cmd.axis].enable(True)
            self.bus.publish(
                MotorAngleState(
                    cmd.axis,
                    cmd.angle_deg,
                    cmd.offset_deg,
                    cmd.enabled,
                )
            )
            return
        #
        # if isinstance(cmd, SetMotorRPM):
        #     motor = self.motors.set_rpm(cmd.axis, cmd.rpm)
        #     msg = "RPM set" if motor.enabled else "Motor disabled (RPM ignored)"
        #     self.bus.publish(MotorState(axis=cmd.axis, enabled=motor.enabled, rpm=motor.rpm, message=msg))
        #     return
        #
       # If you add new command types, handle them above.
        raise ValueError(f"Unknown command: {cmd}")
