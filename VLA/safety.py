"""
Safety Layer - Validate commands and ensure safe operation.

Implements safety checks and user confirmation for dangerous commands.
"""

import sys
from typing import List, Dict, Any, Optional
from .config import Config
from .utils import logger


class SafetyCheck:
    """Result of a safety check."""

    def __init__(
        self,
        safe: bool,
        reason: str = "",
        requires_confirmation: bool = False,
        can_adjust: bool = False
    ):
        self.safe = safe
        self.reason = reason
        self.requires_confirmation = requires_confirmation
        self.can_adjust = can_adjust


class SafetyLayer:
    """
    Safety validation for drone commands.

    Checks commands against safety thresholds and requests user confirmation
    for potentially dangerous operations.
    """

    def __init__(self, auto_confirm: bool = False):
        """
        Initialize safety layer.

        Args:
            auto_confirm: If True, skip confirmation prompts (for testing)
        """
        self.auto_confirm = auto_confirm
        self.max_height = Config.MAX_HEIGHT
        self.max_distance = Config.MAX_DISTANCE
        self.battery_threshold = Config.BATTERY_THRESHOLD
        logger.info(
            f"Safety layer initialized: max_height={self.max_height}cm, "
            f"max_distance={self.max_distance}cm, battery_threshold={self.battery_threshold}%"
        )

    def check_battery(self, battery_level: int) -> SafetyCheck:
        """
        Check if battery level is safe for operation.

        Args:
            battery_level: Current battery percentage

        Returns:
            SafetyCheck result
        """
        if battery_level < self.battery_threshold:
            return SafetyCheck(
                safe=False,
                reason=f"Battery critically low ({battery_level}% < {self.battery_threshold}%)",
                requires_confirmation=False
            )

        if battery_level < self.battery_threshold + 10:
            return SafetyCheck(
                safe=True,
                reason=f"Battery low ({battery_level}%)",
                requires_confirmation=True
            )

        return SafetyCheck(safe=True, reason=f"Battery OK ({battery_level}%)")

    def check_command(self, command: Dict[str, Any], current_state: Dict[str, Any]) -> SafetyCheck:
        """
        Check if a single command is safe.

        Args:
            command: Command dictionary
            current_state: Current drone state

        Returns:
            SafetyCheck result
        """
        action = command.get("action")
        distance = command.get("distance", 0)
        direction = command.get("direction", 0)
        current_height = current_state.get("height", 0)

        # Check takeoff safety
        if action == "takeoff":
            battery = current_state.get("battery", 100)
            battery_check = self.check_battery(battery)
            if not battery_check.safe:
                return battery_check

        # Check height limits
        if action in ["up"]:
            projected_height = current_height + distance
            if projected_height > self.max_height:
                return SafetyCheck(
                    safe=True,
                    reason=f"Height would exceed {self.max_height}cm (projected: {projected_height}cm)",
                    requires_confirmation=True,
                    can_adjust=True
                )

        # Check distance limits
        if action in ["forward", "back", "left", "right"]:
            if distance > self.max_distance:
                return SafetyCheck(
                    safe=True,
                    reason=f"Distance exceeds {self.max_distance}cm ({distance}cm)",
                    requires_confirmation=True,
                    can_adjust=True
                )

        # Check rotation limits
        if action in ["rotate_cw", "rotate_ccw"]:
            if direction > 180:
                return SafetyCheck(
                    safe=True,
                    reason=f"Large rotation ({direction}°)",
                    requires_confirmation=True
                )

        # Check landing safety
        if action == "land":
            if current_height > 100:
                return SafetyCheck(
                    safe=True,
                    reason=f"Landing from height ({current_height}cm)",
                    requires_confirmation=True
                )

        return SafetyCheck(safe=True, reason="Command within safety limits")

    def check_command_sequence(
        self,
        commands: List[Dict[str, Any]],
        current_state: Dict[str, Any]
    ) -> List[SafetyCheck]:
        """
        Check all commands in a sequence.

        Args:
            commands: List of command dictionaries
            current_state: Current drone state

        Returns:
            List of SafetyCheck results
        """
        checks = []
        simulated_state = current_state.copy()

        for cmd in commands:
            check = self.check_command(cmd, simulated_state)
            checks.append(check)

            # Update simulated state
            action = cmd.get("action")
            if action == "takeoff":
                simulated_state["is_flying"] = True
            elif action == "land":
                simulated_state["is_flying"] = False
                simulated_state["height"] = 0
            elif "distance" in cmd:
                simulated_state["height"] = simulated_state.get("height", 0) + cmd["distance"]

        return checks

    def request_confirmation(self, check: SafetyCheck, command: Dict[str, Any]) -> bool:
        """
        Request user confirmation for a command.

        Args:
            check: SafetyCheck result
            command: Command requiring confirmation

        Returns:
            True if user confirms, False otherwise
        """
        if self.auto_confirm:
            return True

        print("\n" + "=" * 60)
        print("⚠️  SAFETY WARNING")
        print("=" * 60)
        print(f"Reason: {check.reason}")
        print(f"Command: {command}")
        print("=" * 60)

        while True:
            response = input("Execute this command? (y/n): ").strip().lower()
            if response in ["y", "yes"]:
                return True
            elif response in ["n", "no"]:
                return False
            else:
                print("Please enter 'y' or 'n'")

    def request_sequence_confirmation(
        self,
        commands: List[Dict[str, Any]],
        checks: List[SafetyCheck]
    ) -> bool:
        """
        Request confirmation for entire command sequence.

        Args:
            commands: List of commands
            checks: List of safety checks

        Returns:
            True if user confirms, False otherwise
        """
        if self.auto_confirm:
            return True

        # Check if any commands require confirmation
        needs_confirmation = any(c.requires_confirmation for c in checks)

        if not needs_confirmation:
            return True

        print("\n" + "=" * 60)
        print("⚠️  COMMAND SEQUENCE REVIEW")
        print("=" * 60)

        for i, (cmd, check) in enumerate(zip(commands, checks), 1):
            status = "✓" if check.safe else "⚠️"
            print(f"\n{status} Command {i}: {cmd}")
            if check.requires_confirmation:
                print(f"  ⚠️  {check.reason}")

        print("=" * 60)

        while True:
            response = input("\nExecute sequence? (y/n): ").strip().lower()
            if response in ["y", "yes"]:
                return True
            elif response in ["n", "no"]:
                return False
            else:
                print("Please enter 'y' or 'n'")

    def adjust_command(self, command: Dict[str, Any], check: SafetyCheck) -> Dict[str, Any]:
        """
        Adjust command parameters to be within safety limits.

        Args:
            command: Original command
            check: Safety check result

        Returns:
            Adjusted command dictionary
        """
        adjusted = command.copy()

        if check.can_adjust:
            if "distance" in command:
                adjusted["distance"] = min(command["distance"], self.max_distance)

        return adjusted
