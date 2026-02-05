# VLA - Vision-Language-Action Drone Control

Natural language drone control system using Qwen3_vl vision-language model.

## Overview

The VLA system enables you to control a DJI Tello drone using natural language commands in Chinese or English. Simply tell the drone what to do like "停在前面的桌子上" (land on the table in front), and the system will:

1. Capture the current camera view
2. Send your command + image to Qwen3_vl
3. Generate a sequence of drone commands
4. Execute commands with safety checks
5. Provide visual feedback after each action

## Features

- 🧠 **Natural Language Understanding** - Chinese and English commands
- 🎯 **Visual Context Awareness** - VLM understands the drone's environment
- 🛡️ **Safety Layer** - Confirmation prompts for dangerous operations
- 🔄 **Closed-Loop Feedback** - Verifies execution after each action
- 🔧 **Modular Design** - Easy to extend with new VLMs

## Installation

```bash
# Install dependencies
pip install openai djitellopy opencv-python numpy pillow

# Set API key (optional, uses default from Qwen_VL.py)
export QWEN_VL_API_KEY="your-api-key"
```

## Usage

### Basic Usage

```bash
# Run with real drone
python -m VLA.main

# Run with mock VLM (testing without API)
python -m VLA.main --mock

# Enable debug mode
python -m VLA.main --debug

# Skip safety confirmations (use with caution!)
python -m VLA.main --auto-confirm
```

### Example Commands

After starting, enter commands in natural language:

```
>>> 起飞
>>> 前进50厘米
>>> 上升30厘米
>>> 停在前面的桌子上
>>> land on the table
>>> rotate left 90 degrees
>>> quit
```

## Module Structure

```
VLA/
├── __init__.py              # Package initialization
├── config.py                # Configuration settings
├── main.py                  # CLI entry point
├── vla_controller.py        # Main orchestration
├── vlm_engine.py            # VLM abstraction (Qwen3_vl)
├── drone_interface.py       # Tello drone wrapper
├── command_parser.py        # JSON command parsing
├── safety.py                # Safety validation
└── utils/
    ├── image_utils.py       # Image encoding/decoding
    └── logging.py           # Logging setup
```

## Configuration

Configuration is managed through environment variables and `config.py`:

```python
# API Settings
QWEN_VL_API_KEY = "sk-..."          # Default from Qwen_VL.py
QWEN_VL_MODEL = "qwen3-vl-plus"

# Safety Thresholds
MAX_HEIGHT = 150                    # cm - requires confirmation
MAX_DISTANCE = 200                  # cm - requires confirmation
BATTERY_THRESHOLD = 20              # % - prevent takeoff

# System Behavior
ENABLE_CLOSED_LOOP = True           # Feedback after each action
DEBUG_MODE = False                  # Verbose logging
```

## Command Format

The VLM generates JSON commands in this format:

```json
{
  "commands": [
    {"action": "takeoff"},
    {"action": "up", "distance": 50, "speed": 30},
    {"action": "forward", "distance": 100, "speed": 30},
    {"action": "land"}
  ]
}
```

### Valid Actions

| Action | Description | Parameters |
|--------|-------------|------------|
| `takeoff` | Take off from ground | none |
| `land` | Land on the ground | none |
| `up` / `down` | Vertical movement | distance (cm), speed (cm/s) |
| `forward` / `back` | Forward/backward | distance (cm), speed (cm/s) |
| `left` / `right` | Lateral movement | distance (cm), speed (cm/s) |
| `rotate_cw` / `rotate_ccw` | Rotation | direction (degrees) |

## Safety Features

- **Battery Check**: Prevents takeoff if battery < 20%
- **Height Limits**: Warns if exceeding 150cm
- **Distance Limits**: Warns if movement > 200cm
- **User Confirmation**: Prompts for dangerous commands
- **Emergency Stop**: Ctrl+C to land immediately

## Development

### Testing with Mock VLM

```python
from VLA import VLAController, MockVLMEngine

# Create controller with mock VLM
vlm = MockVLMEngine()
controller = VLAController(vlm_engine=vlm, auto_confirm=True)

# Connect and test
controller.connect()
success, message = controller.process_command("takeoff")
```

### Adding New VLMs

```python
from VLA.vlm_engine import VLMEngine

class CustomVLM(VLMEngine):
    def generate_commands(self, image, user_command, context=None):
        # Your implementation
        return commands, reasoning
```

## Troubleshooting

### Connection Issues

```
❌ Failed to connect to drone
```

- Ensure Tello is powered on
- Connect to Tello's WiFi (TELLO-XXXXXX)
- Check IP address: `--host 192.168.10.1`

### API Issues

```
❌ Failed to initialize VLM engine
```

- Check API key: `export QWEN_VL_API_KEY="..."`
- Verify internet connection
- Check API status at [DashScope](https://dashscope.aliyuncs.com)

### Command Parsing

```
⚠️ 1/3 commands executed
```

- Check debug logs: `--debug`
- Verify VLM response format
- Ensure JSON is valid

## License

This project is part of the drone control system.

## See Also

- [gesture control.py](../gesture%20control.py) - Gesture-based drone control
- [Qwen_VL.py](../Qwen_VL.py) - Qwen VL examples
- [技术文档.md](../技术文档.md) - Project documentation (Chinese)
