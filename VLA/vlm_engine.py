"""
VLM Engine - Vision-Language Model integration.

Provides abstraction layer for vision-language models with Qwen3_vl implementation.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import json
import numpy as np
from openai import OpenAI

from .config import Config
from .utils import encode_image_to_base64, create_image_url, logger


class Command:
    """Represents a drone command with parameters."""

    def __init__(
        self,
        action: str,
        distance: Optional[int] = None,
        speed: Optional[int] = None,
        direction: Optional[int] = None
    ):
        self.action = action
        self.distance = distance
        self.speed = speed
        self.direction = direction

    def to_dict(self) -> Dict[str, Any]:
        """Convert command to dictionary."""
        result = {"action": self.action}
        if self.distance is not None:
            result["distance"] = self.distance
        if self.speed is not None:
            result["speed"] = self.speed
        if self.direction is not None:
            result["direction"] = self.direction
        return result

    def __repr__(self) -> str:
        return f"Command({self.to_dict()})"


class VLMEngine(ABC):
    """Abstract base class for VLM engines."""

    @abstractmethod
    def generate_commands(
        self,
        image: np.ndarray,
        user_command: str,
        context: Optional[str] = None
    ) -> tuple[List[Command], str]:
        """
        Generate drone commands from image and user input.

        Args:
            image: RGB image as numpy array
            user_command: Natural language command
            context: Optional additional context

        Returns:
            Tuple of (command_list, reasoning_text)
        """
        pass


class Qwen3VLEngine(VLMEngine):
    """
    Qwen3_vl implementation of VLM engine.

    Uses Alibaba DashScope API for vision-language understanding.
    """

    # Valid drone actions
    VALID_ACTIONS = {
        "takeoff", "land",
        "up", "down", "forward", "back", "left", "right",
        "rotate_cw", "rotate_ccw"
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Qwen3_vl client.

        Args:
            api_key: API key (uses Config if not provided)
        """
        self.api_key = api_key or Config.QWEN_VL_API_KEY
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=Config.QWEN_VL_BASE_URL
        )
        self.model = Config.QWEN_VL_MODEL
        logger.info(f"Initialized Qwen3_vl engine with model: {self.model}")

    def _build_system_prompt(self) -> str:
        """Build system prompt with context and constraints."""
        return f"""You are a drone flight control system. You must output JSON commands for a DJI Tello drone.

VALID ACTIONS:
- takeoff: Take off from ground (no distance needed)
- land: Land on the ground (no distance needed)
- up: Move upward (distance in cm, 20-500)
- down: Move downward (distance in cm, 20-500)
- forward: Move forward (distance in cm, 20-500)
- back: Move backward (distance in cm, 20-500)
- left: Move left (distance in cm, 20-500)
- right: Move right (distance in cm, 20-500)
- rotate_cw: Rotate clockwise (direction in degrees, 1-360)
- rotate_ccw: Rotate counter-clockwise (direction in degrees, 1-360)

HARDWARE CONSTRAINTS:
- Maximum distance: 500cm per command
- Maximum speed: 100cm/s
- Minimum distance: 20cm for movement commands
- Maximum rotation: 360 degrees

SAFETY RULES:
- Prefer smaller, safer movements over large ones
- Break complex commands into multiple safe steps
- Always consider obstacles and environment
- If you're unsure, ask for clarification
- Default speed: 30cm/s if not specified

OUTPUT FORMAT:
Return ONLY valid JSON in this exact format:
{{
  "commands": [
    {{"action": "takeoff"}},
    {{"action": "up", "distance": 50, "speed": 30}},
    {{"action": "land"}}
  ]
}}

Do not include any text outside the JSON. The JSON must be parseable.
"""

    def _build_user_prompt(
        self,
        user_command: str,
        image_base64: str,
        context: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Build user prompt with image and command."""
        prompt_text = user_command
        if context:
            prompt_text = f"Context: {context}\n\nCommand: {user_command}"

        return [
            {
                "type": "image_url",
                "image_url": {
                    "url": create_image_url(image_base64)
                }
            },
            {
                "type": "text",
                "text": prompt_text
            }
        ]

    def _parse_vlm_response(self, response_text: str) -> tuple[List[Command], str]:
        """
        Parse VLM response into commands and reasoning.

        Args:
            response_text: Raw response from VLM

        Returns:
            Tuple of (command_list, reasoning)

        Raises:
            ValueError: If response cannot be parsed
        """
        reasoning = ""
        commands = []

        # Extract reasoning if present (content after last ```json block)
        if "```json" in response_text:
            parts = response_text.split("```json")
            if len(parts) > 1:
                json_part = parts[1].split("```")[0].strip()
                reasoning = parts[0].strip()
                if len(parts) > 2:
                    reasoning += "\n" + parts[2].strip()
            response_text = json_part
        else:
            # Try to extract JSON from the response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_part = response_text[start_idx:end_idx]
                reasoning = response_text[:start_idx].strip() + " " + response_text[end_idx:].strip()
                response_text = json_part

        # Parse JSON
        try:
            data = json.loads(response_text.strip())
        except json.JSONDecodeError as e:
            # Try to fix common JSON issues
            cleaned = response_text.strip()
            if not cleaned.startswith('{'):
                cleaned = '{' + cleaned
            if not cleaned.endswith('}'):
                cleaned = cleaned + '}'
            try:
                data = json.loads(cleaned)
            except:
                raise ValueError(f"Failed to parse VLM response as JSON: {e}\n\nResponse: {response_text[:500]}")

        # Extract commands
        if "commands" not in data:
            raise ValueError(f"Response missing 'commands' key: {data}")

        for cmd_data in data["commands"]:
            action = cmd_data.get("action")
            if not action:
                continue

            if action not in self.VALID_ACTIONS:
                logger.warning(f"Unknown action '{action}', skipping")

            command = Command(
                action=action,
                distance=cmd_data.get("distance"),
                speed=cmd_data.get("speed"),
                direction=cmd_data.get("direction")
            )
            commands.append(command)

        return commands, reasoning

    def generate_commands(
        self,
        image: np.ndarray,
        user_command: str,
        context: Optional[str] = None
    ) -> tuple[List[Command], str]:
        """
        Generate drone commands from image and user input.

        Args:
            image: RGB image as numpy array
            user_command: Natural language command
            context: Optional additional context

        Returns:
            Tuple of (command_list, reasoning_text)

        Raises:
            ValueError: If VLM response is invalid
            Exception: If API call fails
        """
        # Encode image
        image_base64 = encode_image_to_base64(image)
        logger.debug(f"Encoded image ({image.shape}) to base64")

        # Build messages
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {
                "role": "user",
                "content": self._build_user_prompt(user_command, image_base64, context)
            }
        ]

        # Call VLM API
        try:
            logger.info(f"Calling Qwen3_vl API with command: {user_command[:50]}...")

            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=False,
                extra_body={
                    "enable_thinking": Config.ENABLE_THINKING,
                    "thinking_budget": Config.THINKING_BUDGET
                },
                timeout=Config.API_TIMEOUT
            )

            # Extract response
            response_text = completion.choices[0].message.content
            logger.debug(f"VLM response: {response_text[:200]}...")

            # Parse into commands
            commands, reasoning = self._parse_vlm_response(response_text)

            logger.info(f"Generated {len(commands)} commands")
            for i, cmd in enumerate(commands):
                logger.debug(f"  Command {i+1}: {cmd}")

            return commands, reasoning

        except Exception as e:
            logger.error(f"VLM API call failed: {e}")
            raise Exception(f"Failed to get commands from VLM: {e}")


class MockVLMEngine(VLMEngine):
    """Mock VLM engine for testing without API."""

    def generate_commands(
        self,
        image: np.ndarray,
        user_command: str,
        context: Optional[str] = None
    ) -> tuple[List[Command], str]:
        """Generate mock commands based on simple keyword matching."""
        logger.debug(f"Mock VLM processing: {user_command}")

        commands = []
        reasoning = f"Mock reasoning for: {user_command}"

        # Simple keyword matching
        if "起飞" in user_command or "takeoff" in user_command.lower():
            commands.append(Command("takeoff"))
        elif "降落" in user_command or "land" in user_command.lower():
            commands.append(Command("land"))
        else:
            # Default mock behavior
            commands.append(Command("takeoff"))
            commands.append(Command("up", distance=50, speed=30))

        return commands, reasoning
