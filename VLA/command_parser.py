"""
Command Parser - Parse and validate JSON commands.

Handles validation of VLM-generated commands and drone method mapping.
"""

import json
from typing import List, Dict, Any, Optional
from .vlm_engine import Command
from .config import Config
from .utils import logger


class CommandValidationError(Exception):
    """Raised when command validation fails."""
    pass


class CommandParser:
    """
    Parse and validate drone commands.

    Converts VLM Command objects to executable dictionaries with validation.
    """

    # Valid actions and their parameter requirements
    ACTION_REQUIREMENTS = {
        "takeoff": {"needs_distance": False, "needs_direction": False},
        "land": {"needs_distance": False, "needs_direction": False},
        "up": {"needs_distance": True, "needs_direction": False},
        "down": {"needs_distance": True, "needs_direction": False},
        "forward": {"needs_distance": True, "needs_direction": False},
        "back": {"needs_distance": True, "needs_direction": False},
        "left": {"needs_distance": True, "needs_direction": False},
        "right": {"needs_distance": True, "needs_direction": False},
        "rotate_cw": {"needs_distance": False, "needs_direction": True},
        "rotate_ccw": {"needs_distance": False, "needs_direction": True},
    }

    def __init__(self):
        """Initialize command parser."""
        self.max_distance = Config.MAX_DISTANCE_HARD
        self.max_speed = Config.MAX_SPEED
        self.max_rotation = Config.MAX_ROTATION
        self.min_distance = Config.MIN_DISTANCE

    def validate_command(self, command: Command) -> Command:
        """
        Validate and clamp command parameters.

        Args:
            command: Command object to validate

        Returns:
            Validated Command with clamped values

        Raises:
            CommandValidationError: If command is invalid
        """
        # Check action is valid
        if command.action not in self.ACTION_REQUIREMENTS:
            raise CommandValidationError(f"Unknown action: {command.action}")

        reqs = self.ACTION_REQUIREMENTS[command.action]

        # Validate distance
        if reqs["needs_distance"]:
            if command.distance is None:
                # Apply default distance
                command.distance = 50
                logger.debug(f"No distance specified, using default: {command.distance}cm")

            # Clamp distance to hardware limits
            if command.distance < self.min_distance:
                logger.warning(f"Distance {command.distance}cm below minimum, clamping to {self.min_distance}cm")
                command.distance = self.min_distance
            elif command.distance > self.max_distance:
                logger.warning(f"Distance {command.distance}cm above maximum, clamping to {self.max_distance}cm")
                command.distance = self.max_distance

        # Validate direction (rotation)
        if reqs["needs_direction"]:
            if command.direction is None:
                command.direction = 90
                logger.debug(f"No direction specified, using default: {command.direction}°")

            if command.direction < 1 or command.direction > self.max_rotation:
                logger.warning(f"Direction {command.direction}° out of range, clamping to {self.max_rotation}°")
                command.direction = min(max(command.direction, 1), self.max_rotation)

        # Validate and clamp speed
        if command.speed is not None:
            if command.speed < 1:
                command.speed = 1
            elif command.speed > self.max_speed:
                logger.warning(f"Speed {command.speed}cm/s above maximum, clamping to {self.max_speed}cm/s")
                command.speed = self.max_speed

        return command

    def parse_commands(self, commands: List[Command]) -> List[Dict[str, Any]]:
        """
        Parse list of Command objects to executable dictionaries.

        Args:
            commands: List of Command objects

        Returns:
            List of validated command dictionaries

        Raises:
            CommandValidationError: If any command is invalid
        """
        parsed = []

        for i, cmd in enumerate(commands):
            try:
                # Validate and clamp command
                validated = self.validate_command(cmd)

                # Convert to dictionary
                cmd_dict = validated.to_dict()
                parsed.append(cmd_dict)

                logger.debug(f"Parsed command {i+1}/{len(commands)}: {cmd_dict}")

            except CommandValidationError as e:
                logger.error(f"Command {i+1} validation failed: {e}")
                raise

        return parsed

    def parse_json(self, json_str: str) -> List[Dict[str, Any]]:
        """
        Parse JSON string to command dictionaries.

        Args:
            json_str: JSON string with commands array

        Returns:
            List of validated command dictionaries

        Raises:
            CommandValidationError: If JSON is invalid or commands fail validation
        """
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise CommandValidationError(f"Invalid JSON: {e}")

        if "commands" not in data:
            raise CommandValidationError("JSON missing 'commands' key")

        # Convert to Command objects
        commands = []
        for cmd_data in data["commands"]:
            cmd = Command(
                action=cmd_data.get("action"),
                distance=cmd_data.get("distance"),
                speed=cmd_data.get("speed"),
                direction=cmd_data.get("direction")
            )
            commands.append(cmd)

        # Validate and parse
        return self.parse_commands(commands)

    def format_commands_for_display(self, commands: List[Dict[str, Any]]) -> str:
        """
        Format commands for user display.

        Args:
            commands: List of command dictionaries

        Returns:
            Formatted string
        """
        lines = ["Command Sequence:"]
        for i, cmd in enumerate(commands, 1):
            action = cmd["action"]
            params = []
            if "distance" in cmd:
                params.append(f"{cmd['distance']}cm")
            if "speed" in cmd:
                params.append(f"@{cmd['speed']}cm/s")
            if "direction" in cmd:
                params.append(f"{cmd['direction']}°")

            params_str = ", ".join(params) if params else ""
            lines.append(f"  {i}. {action}{': ' + params_str if params_str else ''}")

        return "\n".join(lines)
