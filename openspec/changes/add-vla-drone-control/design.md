# Design Document - VLA Drone Control System

## Context

The VLA (Vision-Language-Action) system extends the existing gesture-controlled drone project with natural language understanding capabilities. While gesture control requires pre-programmed mappings, VLA enables flexible, intent-based control using a vision-language model.

**Stakeholders:**
- Project maintainers extending drone capabilities
- Users wanting intuitive drone control without memorizing gestures
- Researchers experimenting with VLMs for robotics

**Constraints:**
- Must use existing `djitellopy` library for drone control
- Must use Qwen3_vl via Alibaba DashScope API
- Standalone system - no dependencies on gesture control code
- Tello hardware limitations (max speed 100cm/s, range ~10m)

## Goals / Non-Goals

### Goals
1. Enable natural language drone control in Chinese and English
2. Implement closed-loop visual feedback for robust execution
3. Provide modular architecture for easy VLM swapping
4. Ensure safety with user confirmation for dangerous commands
5. Support both simple ("takeoff") and complex ("land on the table") commands

### Non-Goals
- Real-time video streaming to user (not required for control)
- Voice input (text-only in v1)
- Multi-drone swarm control
- Autonomous exploration without user commands
- Gesture + VLA hybrid control (future enhancement)

## Decisions

### Decision 1: Standalone Architecture
**Choice:** VLA system as independent module in `VLA/` folder

**Rationale:**
- Clear separation of concerns - VLA is fundamentally different from gesture control
- No risk of breaking existing gesture control functionality
- Easier to test and develop independently
- Can coexist with gesture control system for users to choose

**Alternatives considered:**
- *Integrated approach*: Modify gesture control to add VLA mode
  - Rejected: Would increase complexity of existing stable code
  - Rejected: Risk of introducing bugs to working system
- *Plugin architecture*: VLA as plugin to gesture control
  - Rejected: Over-engineering for initial implementation
  - Could be future enhancement if needed

### Decision 2: JSON Command Format
**Choice:** Structured JSON output from VLM: `[{"action":"up","distance":50,"speed":30}]`

**Rationale:**
- Machine-readable, easy to parse with standard libraries
- Type-safe - can validate against schema
- Supports complex command sequences in single response
- Clear error messages when parsing fails
- VLMs handle JSON format reliably with proper prompting

**JSON Schema:**
```json
{
  "commands": [
    {
      "action": "takeoff|land|up|down|forward|back|left|right|rotate_cw|rotate_ccw",
      "distance": "number (cm, optional for takeoff/land)",
      "speed": "number (cm/s, optional, default 30)",
      "direction": "number (degrees, for rotate only)"
    }
  ]
}
```

**Alternatives considered:**
- *Plain text*: "up 50, forward 100"
  - Rejected: Fragile parsing, ambiguous commands
- *Python code execution*: VLM generates Python
  - Rejected: Security risk, hard to sandbox
- *Custom DSL*: Domain-specific language
  - Rejected: Reinventing the wheel, JSON is standard

### Decision 3: Closed-Loop Feedback After Each Action
**Choice:** Capture new image after each action, feed back to VLM for verification

**Rationale:**
- Detects execution failures (e.g., obstacle blocked movement)
- Allows VLM to adjust subsequent commands based on actual state
- Prevents error accumulation from open-loop execution
- Critical for safety in physical systems

**Flow:**
```
1. User: "Land on the table"
2. VLM + Image → Commands: [{"action":"down","distance":50}]
3. Execute: move_down(50)
4. Capture new image
5. VLM + New Image → Verify: "Table still below"
6. If verified → Continue or Complete
7. If failed → Replan: "Need to move forward first"
```

**Alternatives considered:**
- *Open-loop*: Execute all commands without feedback
  - Rejected: Too unsafe for physical system
- *Periodic checkpoints*: Every N commands
  - Rejected: Less safe, errors compound between checkpoints
- *Continuous streaming*: Real-time video analysis
  - Rejected: Too expensive (API costs), high latency

### Decision 4: Safety Layer with User Confirmation
**Choice:** Pre-execution validation + confirmation for dangerous commands

**Dangerous command criteria:**
- Height > 150cm
- Distance > 200cm in single command
- Battery < 20%
- Commands near detected obstacles (from VLM vision)
- Landing without clear visual confirmation of safe surface

**Rationale:**
- VLMs can hallucinate or misinterpret scenes
- Hardware limits prevent collision in some cases
- User maintains ultimate control
- Graduated approach: warn first, then require confirmation

**Alternatives considered:**
- *Hard limits*: Reject commands exceeding thresholds
  - Rejected: Too restrictive, prevents valid use cases
- *Post-execution monitoring*: Stop when unsafe
  - Rejected: Too late, damage already done
- *Full autonomy*: No user oversight
  - Rejected: Unacceptable safety risk

### Decision 5: Modular VLM Interface
**Choice:** Abstract VLM engine behind interface class

**Architecture:**
```python
class VLMEngine(ABC):
    @abstractmethod
    def generate_commands(self, image: np.ndarray, user_command: str) -> List[Command]:
        pass

class Qwen3VLEngine(VLMEngine):
    def generate_commands(self, image, user_command):
        # Qwen3_vl implementation
```

**Rationale:**
- Easy to swap VLMs (GPT-4V, Claude, local models)
- Testable with mock VLMs
- Clear separation of concerns
- Future-proof for new VLM releases

**Alternatives considered:**
- *Direct Qwen calls*: Inline VLM calls
  - Rejected: Hard to test, impossible to swap models
- *Multiple VLMs*: Vote/ensemble approach
  - Rejected: Overkill for v1, 3x API costs
  - Could be future enhancement

## Risks / Trade-offs

### Risk 1: VLM Misinterpretation
**Risk:** VLM misunderstands scene or command, generates dangerous actions

**Mitigation:**
- System prompt emphasizes safety and hesitation
- Safety layer validates all commands before execution
- User confirmation for high-risk operations
- Closed-loop feedback catches execution errors

### Risk 2: API Latency
**Risk:** Delay between command and execution affects responsiveness

**Trade-off:**
- Accept 2-5 second latency for VLM reasoning
- Benefit: Natural language understanding worth the delay
- Not real-time control system, so acceptable

**Mitigation:**
- Show "Thinking..." status to user
- Cache common command patterns (future)

### Risk 3: API Cost
**Risk:** Repeated VLM calls become expensive

**Trade-off:**
- Cost vs. capability - VLA provides unique value
- Estimate: ~10 calls per complex command sequence

**Mitigation:**
- Use thinking budget to reduce redundant calls
- Consider local models for simple commands (future)
- User option to disable closed-loop for cost saving

### Risk 4: Network Dependency
**Risk:** Requires internet for VLM API, fails offline

**Mitigation:**
- Clear error messages when API unreachable
- Emergency drone landing on connection loss
- Future: Local fallback VLM option

### Risk 5: Tello Hardware Limits
**Risk:** VLM generates commands exceeding Tello capabilities

**Mitigation:**
- System prompt includes Tello constraints
- Safety layer validates against hardware limits
- Command parser clamps values to valid ranges

## Module Structure

```
VLA/
├── __init__.py              # Package initialization
├── config.py                # Configuration (API keys, constants)
├── main.py                  # Entry point, CLI interface
├── vla_controller.py        # Main orchestration loop
├── vlm_engine.py            # VLM abstraction + Qwen3_vl implementation
├── drone_interface.py       # Tello drone wrapper
├── command_parser.py        # JSON command parsing and validation
├── safety.py                # Safety checks and user prompts
└── utils/
    ├── image_utils.py       # Image encoding/decoding
    └── logging.py           # Logging configuration
```

## Migration Plan

### Phase 1: Core Infrastructure (Week 1)
1. Create module structure
2. Implement VLM engine with Qwen3_vl
3. Test VLM integration without drone

### Phase 2: Drone Integration (Week 2)
1. Implement drone interface
2. Build command parser
3. Test basic movements with VLM commands

### Phase 3: Safety & Feedback (Week 3)
1. Implement safety layer
2. Add closed-loop feedback
3. User confirmation dialogs

### Phase 4: Polish & Testing (Week 4)
1. Integration testing
2. Error handling improvements
3. Documentation and examples

### Rollback Plan
- Delete `VLA/` folder - no changes to existing code
- No database migrations or external state to clean up

## Open Questions

### Q1: Should we support command history for context?
**Status:** Unresolved
**Options:**
- Yes: VLM sees previous commands for better context
- No: Each command is independent

**Recommendation:** Start with no history, add if needed based on testing

### Q2: How to handle VLM timeout/failure?
**Status:** Unresolved
**Options:**
- Retry with exponential backoff
- Ask user to rephrase command
- Fallback to manual control mode

**Recommendation:** Implement all three with escalation

### Q3: Should we expose raw Tello commands?
**Status:** Unresolved
**Options:**
- Yes: Advanced users can bypass VLM
- No: VLA is the only interface

**Recommendation:** No for v1 - keep focus on VLA experience

### Q4: Image format for VLM?
**Status:** Unresolved
**Options:**
- Base64 encoded (no external dependencies)
- Upload to URL (requires storage)
- Direct file path (local only)

**Recommendation:** Base64 for portability, URL fallback for large images

### Q5: Multilingual support?
**Status:** Unresolved
**Options:**
- Chinese + English only
- Any language via VLM auto-detection
- User-specified language preference

**Recommendation:** Let VLM handle detection, document Chinese/English support
