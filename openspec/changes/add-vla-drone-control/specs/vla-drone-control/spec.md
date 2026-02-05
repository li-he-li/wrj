# Spec: VLA Drone Control System

## ADDED Requirements

### Requirement: Natural Language Command Interface
The system SHALL accept natural language commands in Chinese or English and convert them into executable drone control sequences.

#### Scenario: Simple command execution
- **WHEN** user provides command "起飞" or "takeoff"
- **THEN** system sends command and image to VLM
- **AND** VLM returns JSON command sequence for takeoff
- **AND** drone executes takeoff successfully

#### Scenario: Complex spatial command
- **WHEN** user provides command "停在前面的桌子上" (land on the table in front)
- **THEN** system captures current drone camera image
- **AND** sends image + command to VLM
- **AND** VLM reasons about visual context
- **AND** generates command sequence (e.g., forward, down, land)
- **AND** executes commands sequentially with feedback

#### Scenario: Unsupported language
- **WHEN** user provides command in unsupported language
- **THEN** system returns error message
- **AND** suggests using Chinese or English

### Requirement: VLM Integration
The system SHALL integrate with Qwen3_vl vision-language model for command generation and visual reasoning.

#### Scenario: VLM command generation
- **WHEN** system sends image + user command to VLM
- **THEN** VLM analyzes visual context
- **AND** generates JSON-formatted command sequence
- **AND** response includes action type, distance, and speed parameters

#### Scenario: VLM thinking mode
- **WHEN** VLM processes complex command
- **THEN** system enables thinking mode
- **AND** displays reasoning process to user
- **AND** reasoning helps verify VLM understanding

#### Scenario: VLM API failure
- **WHEN** VLM API call fails or times out
- **THEN** system catches exception
- **AND** retries with exponential backoff (max 3 attempts)
- **AND** displays clear error message to user
- **AND** suggests rephrasing command or checking network

### Requirement: JSON Command Parsing
The system SHALL parse VLM-generated JSON commands into structured drone control objects.

#### Scenario: Valid command parsing
- **WHEN** VLM returns `{"commands": [{"action": "up", "distance": 50, "speed": 30}]}`
- **THEN** system validates JSON structure
- **AND** extracts action, distance, and speed parameters
- **AND** creates executable command objects

#### Scenario: Invalid JSON format
- **WHEN** VLM returns malformed or invalid JSON
- **THEN** system detects parsing error
- **AND** requests VLM to regenerate with corrected format
- **AND** if retry fails, asks user to rephrase command

#### Scenario: Unknown action type
- **WHEN** VLM returns action not in supported set (takeoff, land, up, down, etc.)
- **THEN** system rejects command
- **AND** displays list of valid actions
- **AND** prompts user to clarify intent

### Requirement: Drone Interface
The system SHALL provide a modular interface to Tello drone for control and image capture.

#### Scenario: Camera frame capture
- **WHEN** system requests current camera frame
- **THEN** drone captures RGB image (no horizontal flip)
- **AND** returns image as numpy array
- **AND** image format compatible with VLM input

#### Scenario: Movement command execution
- **WHEN** system executes command `{"action": "forward", "distance": 100}`
- **THEN** drone calls `move_forward(100)` method
- **AND** waits for command completion
- **AND** returns success/failure status

#### Scenario: Connection initialization
- **WHEN** system starts
- **THEN** connects to Tello at default IP (192.168.10.1)
- **AND** enables video streaming
- **AND** verifies connection with state query
- **AND** displays connection status to user

#### Scenario: Emergency stop
- **WHEN** user triggers emergency stop (Ctrl+C or 'q' key)
- **THEN** system immediately sends land command
- **AND** closes drone connection gracefully
- **AND** releases camera resources

### Requirement: Closed-Loop Feedback
The system SHALL capture new images after each action and feed back to VLM for verification and re-planning.

#### Scenario: Successful execution verification
- **WHEN** drone completes movement command
- **THEN** system captures new camera image
- **AND** sends new image to VLM with execution status
- **AND** VLM verifies expected outcome
- **AND** proceeds to next command or completes sequence

#### Scenario: Execution failure detection
- **WHEN** VLM analyzes post-action image
- **AND** determines action did not achieve expected result (e.g., obstacle blocked movement)
- **THEN** VLM generates adjusted command sequence
- **AND** system executes new commands
- **AND** logs reasoning for user review

#### Scenario: User disables feedback
- **WHEN** user provides command with flag like "--no-feedback"
- **THEN** system executes all commands without intermediate verification
- **AND** displays warning about reduced safety
- **AND** captures final image after sequence completion

### Requirement: Safety Layer
The system SHALL validate all commands and require user confirmation for dangerous operations.

#### Scenario: Dangerous command detection
- **WHEN** VLM generates command exceeding safety thresholds (height > 150cm, distance > 200cm)
- **THEN** system displays warning with command details
- **AND** prompts user: "Execute this command? (y/n)"
- **AND** executes only if user confirms
- **AND** cancels sequence if user declines

#### Scenario: Battery threshold
- **WHEN** drone battery < 20%
- **THEN** system prevents new takeoff commands
- **AND** suggests immediate landing
- **AND** overrides pending commands to land safely

#### Scenario: Hardware limit enforcement
- **WHEN** VLM generates command exceeding hardware limits (distance > 500cm)
- **THEN** system clamps values to valid range
- **AND** logs adjustment for user transparency
- **AND** executes clamped command

#### Scenario: Obstacle detection
- **WHEN** VLM detects obstacle in planned path
- **THEN** system warns user about collision risk
- **AND** requests confirmation before proceeding
- **AND** suggests alternative commands if available

### Requirement: Modular Architecture
The system SHALL be organized in `VLA/` folder with modular, independently testable components.

#### Scenario: Module structure
- **WHEN** examining VLA folder
- **THEN** contains `vlm_engine.py` for VLM abstraction
- **AND** contains `drone_interface.py` for drone control
- **AND** contains `command_parser.py` for JSON parsing
- **AND** contains `safety.py` for validation logic
- **AND** contains `vla_controller.py` for main orchestration
- **AND** contains `main.py` as entry point

#### Scenario: VLM abstraction
- **WHEN** importing VLM engine
- **THEN** `VLMEngine` is abstract base class
- **AND** `Qwen3VLEngine` implements interface
- **AND** easy to add new VLM implementations (e.g., `GPT4VEngine`)
- **AND** no direct VLM API calls outside engine module

#### Scenario: Independent testing
- **WHEN** testing VLM module
- **THEN** can test with mock drone interface
- **AND** can test VLM without real hardware
- **AND** can test safety layer independently
- **AND** unit tests cover edge cases

### Requirement: User Interface
The system SHALL provide command-line interface for natural language interaction.

#### Scenario: Interactive mode
- **WHEN** user runs `python -m VLA.main`
- **THEN** system displays welcome message and instructions
- **AND** prompts for natural language command
- **AND** shows "Thinking..." status during VLM processing
- **AND** displays generated command sequence for confirmation
- **AND** shows execution progress with current action
- **AND** displays completion status

#### Scenario: Command history
- **WHEN** user executes multiple commands
- **THEN** system maintains session history
- **AND** displays recent commands on request
- **AND** allows repeating previous commands

#### Scenario: Help and documentation
- **WHEN** user runs with `--help` flag
- **THEN** system displays usage examples
- **AND** shows supported command types
- **AND** lists safety thresholds
- **AND** provides troubleshooting tips

### Requirement: Error Handling
The system SHALL handle errors gracefully with clear user feedback.

#### Scenario: VLM timeout
- **WHEN** VLM API call exceeds 30 second timeout
- **THEN** system displays timeout error
- **AND** suggests checking network connection
- **AND** offers option to retry or cancel

#### Scenario: Drone disconnection
- **WHEN** drone connection lost during execution
- **THEN** system catches connection error
- **AND** attempts emergency landing if airborne
- **AND** displays clear error message
- **AND** exits gracefully

#### Scenario: Invalid command format
- **WHEN** VLM returns unparseable response
- **THEN** system displays error with VLM output
- **AND** requests VLM to regenerate with specific format instructions
- **AND** if regeneration fails, asks user to rephrase command

### Requirement: Configuration Management
The system SHALL load configuration from environment variables and config files.

#### Scenario: API key configuration
- **WHEN** system initializes
- **THEN** reads Qwen_VL_API_KEY from environment variable
- **AND** falls back to config file if env var not set
- **AND** displays error if API key missing

#### Scenario: Drone connection settings
- **WHEN** system initializes drone connection
- **THEN** reads TELLO_IP from config (default: 192.168.10.1)
- **AND** reads TELLO_PORT from config (default: 8889)
- **AND** allows override via command-line arguments

#### Scenario: Safety threshold configuration
- **WHEN** system loads safety settings
- **THEN** reads MAX_HEIGHT from config (default: 150cm)
- **AND** reads MAX_DISTANCE from config (default: 200cm)
- **AND** reads BATTERY_THRESHOLD from config (default: 20%)
- **AND** applies configured thresholds to all safety checks

### Requirement: Logging and Debugging
The system SHALL provide detailed logging for debugging and monitoring.

#### Scenario: Operation logging
- **WHEN** system executes commands
- **THEN** logs user input with timestamp
- **AND** logs VLM prompts and responses (truncated)
- **AND** logs parsed command sequences
- **AND** logs drone command execution
- **AND** logs safety check results

#### Scenario: Debug mode
- **WHEN** user runs with `--debug` flag
- **THEN** enables verbose logging to console
- **AND** displays full VLM responses
- **AND** shows internal state transitions
- **AND** logs performance metrics (latency, API calls)

#### Scenario: Error logs
- **WHEN** system encounters error
- **THEN** logs full error traceback
- **AND** includes contextual information (command, image, state)
- **AND** saves logs to file for later analysis
