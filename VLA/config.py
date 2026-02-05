"""
Configuration management for VLA system.

Loads settings from environment variables and provides defaults.
"""

import os
from typing import Optional


class Config:
    """Configuration settings for VLA drone control system."""

    # API Configuration
    QWEN_VL_API_KEY: str = os.getenv(
        "QWEN_VL_API_KEY",
        "sk-6e7e3ba45ec64824badf6d741ef6de0f"  # Default from Qwen_VL.py
    )
    QWEN_VL_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    QWEN_VL_MODEL: str = "qwen3-vl-plus"

    # API Behavior
    API_TIMEOUT: int = 30  # seconds
    MAX_RETRIES: int = 3
    ENABLE_THINKING: bool = True
    THINKING_BUDGET: int = 81920  # max tokens for reasoning

    # Drone Configuration
    TELLO_IP: str = os.getenv("TELLO_IP", "192.168.10.1")
    TELLO_PORT: int = 8889
    VS_UDP_PORT: int = 11111

    # Safety Thresholds
    MAX_HEIGHT: int = 150  # cm - requires confirmation if exceeded
    MAX_DISTANCE: int = 200  # cm - requires confirmation if exceeded
    BATTERY_THRESHOLD: int = 20  # % - prevent takeoff if below

    # Hardware Limits (Tello constraints)
    MAX_SPEED: int = 100  # cm/s
    MIN_DISTANCE: int = 20  # cm
    MAX_DISTANCE_HARD: int = 500  # cm - absolute hardware limit
    MAX_ROTATION: int = 360  # degrees

    # Camera Settings
    CAMERA_WIDTH: int = 640
    CAMERA_HEIGHT: int = 480

    # System Behavior
    ENABLE_CLOSED_LOOP: bool = True  # Capture images after each action
    SHOW_CAMERA_PREVIEW: bool = False  # Show OpenCV window
    DEBUG_MODE: bool = False  # Verbose logging

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = "vla.log"

    @classmethod
    def validate(cls) -> bool:
        """Validate configuration settings."""
        if not cls.QWEN_VL_API_KEY:
            raise ValueError(
                "QWEN_VL_API_KEY not set. "
                "Please set the QWEN_VL_API_KEY environment variable."
            )
        return True

    @classmethod
    def display(cls) -> str:
        """Display current configuration."""
        return f"""
VLA Configuration:
==================
API Key: {cls.QWEN_VL_API_KEY[:10]}...
Model: {cls.QWEN_VL_MODEL}
Drone IP: {cls.TELLO_IP}
Max Height: {cls.MAX_HEIGHT} cm
Max Distance: {cls.MAX_DISTANCE} cm
Battery Threshold: {cls.BATTERY_THRESHOLD}%
Closed-Loop Feedback: {cls.ENABLE_CLOSED_LOOP}
Debug Mode: {cls.DEBUG_MODE}
"""
