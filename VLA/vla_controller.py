"""
VLA Controller - Main orchestration logic.

Coordinates VLM, drone, parser, and safety modules.
"""

import time
from typing import List, Dict, Any, Optional
import numpy as np

from .vlm_engine import VLMEngine, Qwen3VLEngine, Command
from .drone_interface import DroneInterface
from .command_parser import CommandParser
from .safety import SafetyLayer
from .config import Config
from .utils import logger


class VLAController:
    """
    Main controller for Vision-Language-Action drone control.

    Orchestrates the VLA pipeline:
    1. Capture image
    2. Send to VLM with user command
    3. Parse and validate commands
    4. Check safety
    5. Execute with feedback loop
    """

    def __init__(
        self,
        vlm_engine: Optional[VLMEngine] = None,
        drone_host: Optional[str] = None,
        auto_confirm: bool = False
    ):
        """
        Initialize VLA controller.

        Args:
            vlm_engine: VLM engine instance (creates Qwen3_vl if not provided)
            drone_host: Tello IP address
            auto_confirm: Skip safety confirmations (for testing)
        """
        self.vlm = vlm_engine or Qwen3VLEngine()
        self.drone = DroneInterface(host=drone_host)
        self.parser = CommandParser()
        self.safety = SafetyLayer(auto_confirm=auto_confirm)

        self.command_history: List[Dict[str, Any]] = []
        self.running = False

        logger.info("VLA Controller initialized")

    def connect(self) -> bool:
        """
        Connect to drone and initialize systems.

        Returns:
            True if connection successful
        """
        try:
            self.drone.connect()
            logger.info("VLA Controller ready")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize VLA controller: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from drone and cleanup."""
        self.running = False
        self.drone.disconnect()
        logger.info("VLA Controller disconnected")

    def capture_context(self) -> tuple[np.ndarray, Dict[str, Any]]:
        """
        Capture current visual context and drone state.

        Returns:
            Tuple of (image, state_dict)
        """
        image = self.drone.capture_frame()
        state = self.drone.get_state()
        return image, state

    def generate_commands(
        self,
        image: np.ndarray,
        user_command: str,
        context: Optional[str] = None
    ) -> tuple[List[Command], str]:
        """
        Generate commands from image and user input.

        Args:
            image: Current camera image
            user_command: Natural language command
            context: Optional additional context

        Returns:
            Tuple of (commands, reasoning)
        """
        logger.info(f"Generating commands for: {user_command}")

        try:
            commands, reasoning = self.vlm.generate_commands(image, user_command, context)
            logger.info(f"Generated {len(commands)} commands")
            logger.debug(f"Reasoning: {reasoning[:200]}...")

            return commands, reasoning

        except Exception as e:
            logger.error(f"Command generation failed: {e}")
            raise

    def validate_and_plan(
        self,
        commands: List[Command],
        current_state: Dict[str, Any]
    ) -> tuple[List[Dict[str, Any]], bool]:
        """
        Validate commands and create execution plan.

        Args:
            commands: List of Command objects
            current_state: Current drone state

        Returns:
            Tuple of (parsed_commands, all_safe)
        """
        # Parse commands
        try:
            parsed = self.parser.parse_commands(commands)
        except Exception as e:
            logger.error(f"Command parsing failed: {e}")
            raise

        # Safety checks
        checks = self.safety.check_command_sequence(parsed, current_state)

        # Check if all commands are safe
        all_safe = all(c.safe for c in checks)

        # Request confirmation if needed
        if not all_safe or any(c.requires_confirmation for c in checks):
            confirmed = self.safety.request_sequence_confirmation(parsed, checks)
            if not confirmed:
                logger.info("User cancelled command sequence")
                return [], False

        return parsed, True

    def execute_command(
        self,
        command: Dict[str, Any],
        current_state: Dict[str, Any]
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Execute a single drone command.

        Args:
            command: Command dictionary
            current_state: Current drone state

        Returns:
            Tuple of (success, new_state)
        """
        action = command.get("action")

        try:
            logger.info(f"Executing: {action}")

            # Pre-command safety check
            check = self.safety.check_command(command, current_state)
            if not check.safe:
                logger.error(f"Command unsafe: {check.reason}")
                return False, current_state

            if check.requires_confirmation:
                confirmed = self.safety.request_confirmation(check, command)
                if not confirmed:
                    logger.info(f"User cancelled: {action}")
                    return False, current_state

            # Execute command
            success = self.drone.execute_command(command)

            if success:
                # Get new state
                new_state = self.drone.get_state()
                logger.info(f"Command {action} completed successfully")
                return True, new_state
            else:
                logger.warning(f"Command {action} failed")
                return False, current_state

        except Exception as e:
            logger.error(f"Command execution error: {e}")
            return False, current_state

    def execute_with_feedback(
        self,
        commands: List[Dict[str, Any]],
        initial_state: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Execute commands with closed-loop feedback.

        Args:
            commands: List of command dictionaries
            initial_state: Initial drone state

        Returns:
            List of executed command results
        """
        results = []
        current_state = initial_state.copy()
        context = ""

        for i, command in enumerate(commands):
            logger.info(f"Executing command {i+1}/{len(commands)}: {command}")

            # Execute command
            success, new_state = self.execute_command(command, current_state)

            result = {
                "command": command,
                "success": success,
                "state_before": current_state,
                "state_after": new_state if success else current_state
            }
            results.append(result)

            if not success:
                logger.warning(f"Command {i+1} failed, stopping sequence")
                break

            current_state = new_state

            # Closed-loop feedback
            if Config.ENABLE_CLOSED_LOOP and i < len(commands) - 1:
                try:
                    # Capture new image
                    new_image, _ = self.capture_context()

                    # Verify execution and possibly replan
                    if self.should_replan(result, new_image):
                        logger.info("Replanning based on feedback...")

                        # Generate new commands for remaining actions
                        remaining_commands = commands[i+1:]
                        if remaining_commands:
                            # Create context from what we've done
                            context = f"Already executed: {[c['action'] for c in commands[:i+1]]}"

                            # For now, continue with remaining commands
                            # In future, we could send new image to VLM for replanning
                            logger.debug("Continuing with remaining commands")

                except Exception as e:
                    logger.error(f"Feedback loop failed: {e}")
                    # Continue without feedback
                    pass

        return results

    def should_replan(self, result: Dict[str, Any], new_image: np.ndarray) -> bool:
        """
        Determine if we should replan based on execution result.

        Args:
            result: Command execution result
            new_image: New camera image

        Returns:
            True if replanning is needed
        """
        # For now, simple heuristic: replan if command failed
        # In future, could use VLM to analyze new_image
        return not result["success"]

    def process_command(
        self,
        user_command: str,
        context: Optional[str] = None
    ) -> tuple[bool, str]:
        """
        Process a natural language command end-to-end.

        Args:
            user_command: Natural language command
            context: Optional additional context

        Returns:
            Tuple of (success, message)
        """
        try:
            # Capture initial context
            logger.info("Capturing initial context...")
            image, state = self.capture_context()
            logger.info(f"Current state: height={state.get('height', 0)}cm, battery={state.get('battery', 0)}%")

            # Generate commands
            print("\n🧠 Thinking...")
            commands, reasoning = self.generate_commands(image, user_command, context)

            if not commands:
                return False, "No commands generated"

            # Display reasoning
            if reasoning and Config.DEBUG_MODE:
                print(f"\n📝 Reasoning:\n{reasoning}\n")

            # Validate and plan
            parsed_commands, approved = self.validate_and_plan(commands, state)

            if not approved or not parsed_commands:
                return False, "Commands rejected by safety checks"

            # Display command sequence
            print(f"\n{self.parser.format_commands_for_display(parsed_commands)}\n")

            # Execute with feedback
            results = self.execute_with_feedback(parsed_commands, state)

            # Summary
            success_count = sum(1 for r in results if r["success"])
            total_count = len(results)

            if success_count == total_count:
                message = f"✓ All {total_count} commands executed successfully"
                return True, message
            else:
                message = f"⚠ {success_count}/{total_count} commands executed"
                return False, message

        except Exception as e:
            logger.error(f"Command processing failed: {e}")
            return False, f"Error: {e}"

    def run_interactive(self) -> None:
        """Run interactive command loop."""
        self.running = True

        print("\n" + "=" * 60)
        print("VLA Drone Control System")
        print("=" * 60)
        print("Enter natural language commands (or 'quit' to exit)")
        print("Examples:")
        print("  - 起飞")
        print("  - 前进50厘米")
        print("  - 停在前面的桌子上")
        print("=" * 60 + "\n")

        while self.running:
            try:
                # Get user input
                user_input = input(">>> ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ["quit", "exit", "q"]:
                    print("\nShutting down...")
                    break

                # Process command
                success, message = self.process_command(user_input)

                print(f"\n{message}\n")

            except KeyboardInterrupt:
                print("\n\nInterrupted by user")
                break
            except Exception as e:
                print(f"\nError: {e}\n")
                logger.exception("Unexpected error in interactive loop")
