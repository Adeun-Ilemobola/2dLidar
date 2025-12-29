# embedded/system.py
# This is your "master class" / orchestrator.
# It owns modules (motors, sensors, lidar...) and handles commands from UI.

from __future__ import annotations
from embedded.bus import EventBus
from embedded.modules.motors import Motor , ServoConfig
from shared.protocol import Command, EnableMotor ,MotorAngleState


class System:
    def __init__(self, bus: EventBus) -> None:
        self.bus = bus
        self.Pi = any()
        self.motors = {
            "x": Motor(ServoConfig(pin=17), self.Pi),
            "y": Motor(ServoConfig(pin=27), self.Pi),
        }

    def configure_all(self) -> None:
        self.motors["x"].enable(True)
        self.motors["y"].enable(True)

        pass

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
