"""
Drone Interface - Tello drone wrapper.

Provides clean interface for drone control and image capture.
"""

import time
import numpy as np
from typing import Optional, Dict, Any

from djitellopy import Tello, TelloException
from .config import Config
from .utils import logger


class DroneInterface:
    """
    Wrapper for DJI Tello drone control.

    Handles connection, camera capture, and command execution.
    """

    def __init__(self, host: Optional[str] = None):
        """
        Initialize drone interface.

        Args:
            host: Tello IP address (uses Config if not provided)
        """
        self.host = host or Config.TELLO_IP
        self.tello: Optional[Tello] = None
        self.connected = False
        self.streaming = False

        logger.info(f"Drone interface created for host: {self.host}")

    def connect(self) -> bool:
        """
        Connect to Tello drone.

        Returns:
            True if connection successful

        Raises:
            TelloException: If connection fails
        """
        try:
            logger.info(f"Connecting to Tello at {self.host}...")

            self.tello = Tello(host=self.host)
            self.tello.connect()
            self.tello.streamon()

            # Wait for video stream to stabilize
            time.sleep(2)

            # Get initial state to verify connection
            _ = self.tello.get_height()
            _ = self.tello.get_battery()

            self.connected = True
            self.streaming = True

            battery = self.tello.get_battery()
            logger.info(f"Connected to Tello. Battery: {battery}%")

            return True

        except TelloException as e:
            logger.error(f"Failed to connect to Tello: {e}")
            raise

    def disconnect(self) -> None:
        """Disconnect from drone safely."""
        if self.tello:
            try:
                if self.tello.is_flying:
                    logger.warning("Drone still flying, landing...")
                    self.land()
                if self.streaming:
                    self.tello.streamoff()
                self.tello.end()
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
            finally:
                self.connected = False
                self.streaming = False
                logger.info("Disconnected from Tello")

    def capture_frame(self) -> np.ndarray:
        """
        Capture current camera frame.

        Returns:
            RGB image as numpy array (no horizontal flip)

        Raises:
            RuntimeError: If not connected or frame capture fails
        """
        if not self.connected or not self.tello:
            raise RuntimeError("Not connected to drone")

        try:
            # Get frame from background frame reader
            frame = self.tello.get_frame_read().frame

            if frame is None or frame.size == 0:
                raise RuntimeError("Failed to capture frame")

            # Frame is already RGB (converted in djitellopy), no flip needed
            logger.debug(f"Captured frame: {frame.shape}")

            return frame

        except Exception as e:
            logger.error(f"Frame capture failed: {e}")
            raise

    def get_state(self) -> Dict[str, Any]:
        """
        Get current drone state.

        Returns:
            Dictionary with state information
        """
        if not self.connected or not self.tello:
            return {}

        try:
            state = {
                "height": self.tello.get_height(),
                "battery": self.tello.get_battery(),
                "temperature": self.tello.get_temperature(),
                "pitch": self.tello.get_pitch(),
                "roll": self.tello.get_roll(),
                "yaw": self.tello.get_yaw(),
                "speed_x": self.tello.get_speed_x(),
                "speed_y": self.tello.get_speed_y(),
                "speed_z": self.tello.get_speed_z(),
                "is_flying": self.tello.is_flying,
            }
            logger.debug(f"Drone state: height={state['height']}cm, battery={state['battery']}%")
            return state

        except TelloException as e:
            logger.error(f"Failed to get state: {e}")
            return {}

    # Movement commands

    def takeoff(self) -> bool:
        """Execute takeoff command."""
        if not self.connected or not self.tello:
            raise RuntimeError("Not connected to drone")

        logger.info("Executing: takeoff")
        try:
            self.tello.takeoff()
            time.sleep(0.5)  # Wait for takeoff to complete
            return True
        except TelloException as e:
            logger.error(f"Takeoff failed: {e}")
            return False

    def land(self) -> bool:
        """Execute land command."""
        if not self.connected or not self.tello:
            raise RuntimeError("Not connected to drone")

        logger.info("Executing: land")
        try:
            self.tello.land()
            time.sleep(0.5)  # Wait for landing to complete
            return True
        except TelloException as e:
            logger.error(f"Landing failed: {e}")
            return False

    def move_up(self, distance: int, speed: Optional[int] = None) -> bool:
        """Move upward."""
        if not self.connected or not self.tello:
            raise RuntimeError("Not connected to drone")

        logger.info(f"Executing: move_up {distance}cm")
        try:
            if speed:
                self.tello.set_speed(speed)
            self.tello.move_up(distance)
            return True
        except TelloException as e:
            logger.error(f"Move up failed: {e}")
            return False

    def move_down(self, distance: int, speed: Optional[int] = None) -> bool:
        """Move downward."""
        if not self.connected or not self.tello:
            raise RuntimeError("Not connected to drone")

        logger.info(f"Executing: move_down {distance}cm")
        try:
            if speed:
                self.tello.set_speed(speed)
            self.tello.move_down(distance)
            return True
        except TelloException as e:
            logger.error(f"Move down failed: {e}")
            return False

    def move_forward(self, distance: int, speed: Optional[int] = None) -> bool:
        """Move forward."""
        if not self.connected or not self.tello:
            raise RuntimeError("Not connected to drone")

        logger.info(f"Executing: move_forward {distance}cm")
        try:
            if speed:
                self.tello.set_speed(speed)
            self.tello.move_forward(distance)
            return True
        except TelloException as e:
            logger.error(f"Move forward failed: {e}")
            return False

    def move_back(self, distance: int, speed: Optional[int] = None) -> bool:
        """Move backward."""
        if not self.connected or not self.tello:
            raise RuntimeError("Not connected to drone")

        logger.info(f"Executing: move_back {distance}cm")
        try:
            if speed:
                self.tello.set_speed(speed)
            self.tello.move_back(distance)
            return True
        except TelloException as e:
            logger.error(f"Move back failed: {e}")
            return False

    def move_left(self, distance: int, speed: Optional[int] = None) -> bool:
        """Move left."""
        if not self.connected or not self.tello:
            raise RuntimeError("Not connected to drone")

        logger.info(f"Executing: move_left {distance}cm")
        try:
            if speed:
                self.tello.set_speed(speed)
            self.tello.move_left(distance)
            return True
        except TelloException as e:
            logger.error(f"Move left failed: {e}")
            return False

    def move_right(self, distance: int, speed: Optional[int] = None) -> bool:
        """Move right."""
        if not self.connected or not self.tello:
            raise RuntimeError("Not connected to drone")

        logger.info(f"Executing: move_right {distance}cm")
        try:
            if speed:
                self.tello.set_speed(speed)
            self.tello.move_right(distance)
            return True
        except TelloException as e:
            logger.error(f"Move right failed: {e}")
            return False

    def rotate_clockwise(self, degrees: int) -> bool:
        """Rotate clockwise."""
        if not self.connected or not self.tello:
            raise RuntimeError("Not connected to drone")

        logger.info(f"Executing: rotate_clockwise {degrees}°")
        try:
            self.tello.rotate_clockwise(degrees)
            return True
        except TelloException as e:
            logger.error(f"Rotate clockwise failed: {e}")
            return False

    def rotate_counter_clockwise(self, degrees: int) -> bool:
        """Rotate counter-clockwise."""
        if not self.connected or not self.tello:
            raise RuntimeError("Not connected to drone")

        logger.info(f"Executing: rotate_counter_clockwise {degrees}°")
        try:
            self.tello.rotate_counter_clockwise(degrees)
            return True
        except TelloException as e:
            logger.error(f"Rotate counter-clockwise failed: {e}")
            return False

    def emergency_stop(self) -> None:
        """Emergency stop - stop all motors immediately."""
        if self.tello:
            logger.warning("EMERGENCY STOP activated")
            try:
                self.tello.emergency()
            except Exception as e:
                logger.error(f"Emergency stop failed: {e}")

    def execute_command(self, command: Dict[str, Any]) -> bool:
        """
        Execute a command dictionary.

        Args:
            command: Command dict with 'action' and optional parameters

        Returns:
            True if successful

        Raises:
            ValueError: If command is invalid
        """
        action = command.get("action")
        if not action:
            raise ValueError("Command missing 'action'")

        distance = command.get("distance")
        speed = command.get("speed")
        direction = command.get("direction")

        # Execute based on action type
        if action == "takeoff":
            return self.takeoff()
        elif action == "land":
            return self.land()
        elif action == "up":
            return self.move_up(distance, speed)
        elif action == "down":
            return self.move_down(distance, speed)
        elif action == "forward":
            return self.move_forward(distance, speed)
        elif action == "back":
            return self.move_back(distance, speed)
        elif action == "left":
            return self.move_left(distance, speed)
        elif action == "right":
            return self.move_right(distance, speed)
        elif action == "rotate_cw":
            return self.rotate_clockwise(direction or 90)
        elif action == "rotate_ccw":
            return self.rotate_counter_clockwise(direction or 90)
        else:
            raise ValueError(f"Unknown action: {action}")
