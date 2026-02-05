# Change: Add Vision-Language-Action (VLA) Drone Control System

## Why

The current gesture control system requires predefined gesture-to-command mappings, limiting flexibility. Users can only execute commands that are pre-programmed into the system. A VLA system powered by Qwen3_vl will enable natural language control of the drone, allowing users to issue arbitrary commands like "land on the table in front" without requiring code changes or new gesture training.

## What Changes

- **NEW**: Standalone VLA system in `VLA/` folder with modular architecture
- **NEW**: Vision-Language-Action pipeline using Qwen3_vl as the reasoning engine
- **NEW**: Natural language command interface for drone control
- **NEW**: JSON-based command format for structured drone control sequences
- **NEW**: Closed-loop feedback system with image capture after each action
- **NEW**: Safety layer requiring user confirmation for dangerous commands

## Impact

- Affected capabilities: New capability (no existing specs affected)
- Affected code:
  - `VLA/` - New folder with complete VLA system
  - References existing `djitellopy/` for drone control
  - References existing `Qwen_VL.py` for VLM integration pattern
  - No modifications to existing gesture control system

## Technical Approach

The VLA system will:
1. Capture initial drone camera frame (RGB, no flip - like gesture control)
2. Send user's natural language command + current image to Qwen3_vl
3. VLM reasons and outputs JSON command sequence (e.g., `[{"action":"up","distance":50}]`)
4. System executes commands one-by-one
5. After each action, capture new image and verify execution
6. Re-plan with VLM if needed based on new visual state
7. Apply safety checks before executing dangerous commands

## Success Criteria

- User can control drone using natural language in Chinese or English
- VLM correctly interprets visual context (e.g., "land on the table")
- Drone executes safe movement sequences without collision
- System handles VLM failures gracefully with error recovery
- Modular design allows easy extension with new VLM models
