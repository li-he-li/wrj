# Project Context

## Purpose
**Gesture-Controlled Drone System** - A computer vision project that uses hand gesture recognition to control a DJI Tello drone in real-time. The system detects hand gestures via YOLOv5 and translates them into flight commands, enabling intuitive drone control without manual remote operation.

## Tech Stack
- **Python 3.x** - Primary programming language
- **YOLOv5 (PyTorch)** - Real-time object detection for hand gesture recognition
- **OpenCV** - Image processing and video stream handling
- **djitellopy** - Tello drone SDK for flight control
- **PyTorch** - Deep learning framework for YOLO model inference
- **Threading/Multiprocessing** - Concurrent video processing and command execution
- **Qwen VL** - Vision-language model integration (experimental)

## Project Conventions

### Code Style
- **Language**: English for code, Chinese for inline comments (documentation in Chinese)
- **Naming**: CamelCase for classes (e.g., `TelloController`), snake_case for functions and variables
- **File organization**: Main control logic in root directory, YOLOv5 in `/yolov5` subdirectory
- **Type hints**: Not consistently used, but ctypes for shared memory structures

### Architecture Patterns
- **Multi-threaded design**: Separate threads for video processing and command execution
- **Producer-consumer pattern**: Queue-based command passing with deduplication
- **Event-driven**: Threading events for synchronization between video and command threads
- **Model inference**: Local torch.hub.load for YOLOv5 models

### Testing Strategy
- Manual testing with real Tello drone hardware
- Confidence threshold tuning (currently set to 0.7)
- Visual verification via OpenCV windows

### Git Workflow
- Main branch for stable code
- Experimental features in separate branches before merging
- Commit messages in English or Chinese (flexible)

## Domain Context

### Gesture Mapping (8 classes)
1. **takeoff** (握拳，拳心向前) - Fist forward → Takeoff
2. **forward** (手比1) - Number 1 gesture → Move forward 100cm
3. **back** (手比2) - Number 2 gesture → Move back 60cm
4. **left** (手比3) - Number 3 gesture → Move left 60cm
5. **right** (手比4) - Number 4 gesture → Move right 60cm
6. **up** (大拇哥) - Thumbs up → Move up 60cm
7. **down** (大拇哥向下) - Thumbs down → Move down 60cm
8. **landoff** (平掌，掌心向前) - Open palm forward → Land

### Key Implementation Details
- **Command deduplication**: 0.5 second cooldown prevents duplicate commands
- **Height check**: Takeoff only executed when height < 5cm
- **Queue management**: Single-item queue ensures only latest command is executed
- **Frame processing**: RGB to BGR conversion required for webcam input
- **Custom dataset**: 8-class gesture dataset hosted on Roboflow

## Important Constraints
- **Hardware dependency**: Requires DJI Tello drone connected via Wi-Fi (default IP: 192.168.10.1)
- **Real-time performance**: Detection loop includes 0.2s sleep between detections
- **Safety**: Height restrictions prevent takeoff when already airborne
- **Network latency**: Dependent on Wi-Fi connection stability for drone control
- **GPU recommended**: YOLOv5 inference benefits from CUDA acceleration

## External Dependencies
- **Roboflow dataset**: https://universe.roboflow.com/wrj-ac1k5/dataset-jejem/dataset/2
- **Tello SDK**: DJI Tello drone firmware API
- **Pre-trained model**: `weights/last_best.pt` (custom trained on gesture dataset)
- **Qwen VL API**: Alibaba DashScope API for vision-language tasks (API key in code - should be moved to environment variables)
