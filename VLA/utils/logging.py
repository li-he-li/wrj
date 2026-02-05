"""
Logging configuration for VLA system.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = "VLA",
    level: str = "INFO",
    log_file: Optional[str] = None,
    verbose: bool = False
) -> logging.Logger:
    """
    Set up logger for VLA system.

    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
        verbose: Enable verbose console output

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)

    # File handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)

    # Formatter
    formatter = logging.Formatter(
        '[%(levelname)s] %(name)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


# Create default logger instance
logger = setup_logger()
