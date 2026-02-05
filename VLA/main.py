"""
VLA Main Entry Point

Command-line interface for VLA drone control system.
"""

import sys
import argparse
from typing import Optional

from .config import Config
from .vla_controller import VLAController
from .vlm_engine import Qwen3VLEngine, MockVLMEngine
from .utils import logger


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="VLA Drone Control - Natural language drone control with Qwen3_vl",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m VLA.main                    # Run with real drone
  python -m VLA.main --mock             # Run with mock VLM (testing)
  python -m VLA.main --debug            # Enable debug mode
  python -m VLA.main --auto-confirm     # Skip safety confirmations
  python -m VLA.main --host 192.168.10.2  # Use custom drone IP

Commands:
  After starting, enter natural language commands:
    - 起飞
    - 前进50厘米
    - 停在前面的桌子上
    - land on the table
    - quit
        """
    )

    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Tello drone IP address (default: 192.168.10.1)"
    )

    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock VLM engine (for testing without API)"
    )

    parser.add_argument(
        "--auto-confirm",
        action="store_true",
        help="Skip safety confirmation prompts (use with caution)"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with verbose logging"
    )

    parser.add_argument(
        "--no-closed-loop",
        action="store_true",
        help="Disable closed-loop feedback (faster but less safe)"
    )

    parser.add_argument(
        "--config",
        action="store_true",
        help="Display current configuration and exit"
    )

    return parser.parse_args()


def display_welcome():
    """Display welcome message."""
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   VLA Drone Control System                                ║
║   Vision-Language-Action with Qwen3_vl                    ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """)


def display_config():
    """Display current configuration."""
    print(Config.display())
    sys.exit(0)


def main():
    """Main entry point."""
    args = parse_arguments()

    # Update config based on arguments
    if args.debug:
        Config.DEBUG_MODE = True
        Config.LOG_LEVEL = "DEBUG"

    if args.no_closed_loop:
        Config.ENABLE_CLOSED_LOOP = False

    # Display config if requested
    if args.config:
        display_config()

    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)

    # Setup logging
    global logger
    from .utils import setup_logger
    logger = setup_logger(level=Config.LOG_LEVEL, verbose=args.debug)

    # Display welcome
    display_welcome()

    # Create VLM engine
    if args.mock:
        print("🔧 Using mock VLM engine (testing mode)")
        vlm = MockVLMEngine()
    else:
        print("🧠 Using Qwen3_vl engine")
        try:
            vlm = Qwen3VLEngine()
        except Exception as e:
            print(f"❌ Failed to initialize VLM engine: {e}")
            sys.exit(1)

    # Create controller
    controller = VLAController(
        vlm_engine=vlm,
        drone_host=args.host,
        auto_confirm=args.auto_confirm
    )

    try:
        # Connect to drone
        print("🚀 Connecting to drone...")
        if not controller.connect():
            print("❌ Failed to connect to drone")
            sys.exit(1)

        # Run interactive loop
        controller.run_interactive()

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        logger.exception("Fatal error in main")
        sys.exit(1)

    finally:
        # Always disconnect
        print("🔌 Disconnecting...")
        controller.disconnect()
        print("✓ Shutdown complete")


if __name__ == "__main__":
    main()
