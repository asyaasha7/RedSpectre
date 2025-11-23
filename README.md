# Swarm Securiy

An AI-powered Solidity smart contract auditor that combines static analysis with dynamic exploit verification using specialized AI personas.

![RedSpectre Architecture]

## What It Does

RedSpectre is a hybrid AI agent that audits Solidity smart contracts for security vulnerabilities using a multi-layered approach:

- **Static Analysis**: Integrates with Slither to identify potential vulnerabilities
- **AI Reasoning**: Uses 25+ specialized AI personas (experts) that analyze code from different perspectives (access control, reentrancy, arithmetic, DeFi logic, etc.)
- **Dynamic Verification**: Automatically generates and runs Foundry tests to verify if identified vulnerabilities are actually exploitable
- **Intelligent Routing**: Uses a Routing Analyst AI to select the most relevant personas based on code heuristics and patterns

## Architecture

### Core Components

**Agent Code Layer:**
- `orchestrator.py` - Coordinates the entire audit workflow
- `architect_llm.py` - Converts Slither findings into concrete exploit hypotheses
- `dynamic_executor.py` - Generates and executes Foundry tests to verify exploits
- `static_scanner.py` - Runs Slither analysis on target contracts

**Services Layer:**
- `swarm.py` - Manages a collection of 25+ AI expert personas
- `auditor.py` - Main audit service that integrates Swarm reasoning
- `scout.py` - Discovers Solidity files in target repositories

**Persona System:**
- **Thief** - Access control and privilege escalation
- **Logician** - Reentrancy and state update vulnerabilities
- **DeFiAnalyst** - AMM, yield farming, and DeFi-specific risks
- **ArithmeticExpert** - Integer overflow/underflow issues
- **RoutingAnalyst** - Intelligently selects which personas to run based on code patterns

### Two Operation Modes

**Server Mode (AgentArena Integration):**
- Runs as a webhook server for automated platform integration
- Downloads repositories from AgentArena, audits them, and posts findings back
- Supports custom ports and authentication tokens

**Local Mode:**
- Processes GitHub repositories directly from the command line
- Interactive file selection or full repository scanning
- Outputs JSON results with severity classifications

## Installation

```bash
# Clone and setup (using the comprehensive Makefile)
git clone https://github.com/asyaasha7/RedSpectre.git
cd RedSpectre
make install  # Bootstrap venv, install deps, setup localtunnel

# Or manual setup
python -m venv RedSpectre/.venv
source RedSpectre/.venv/bin/activate
pip install -e RedSpectre
```

## Configuration

Create `.env` file in the RedSpectre directory:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini

# Logging
LOG_LEVEL=INFO
LOG_FILE=agent.log

# Server mode (AgentArena)
AGENTARENA_API_KEY=aa-...
WEBHOOK_AUTH_TOKEN=your_webhook_token
DATA_DIR=./data
```

## Usage

### Local Mode (Test Repository)

```bash
# Audit a GitHub repository
audit-agent local --repo https://github.com/andreitoma8/learn-solidity-hacks.git --output audit.json

# Interactive file selection
audit-agent local --repo <repo_url> --only-selected-files
```

### Server Mode (AgentArena)

```bash
# Start webhook server on port 8000
audit-agent server

# Custom port
audit-agent server --port 8008
```

### Makefile Automation

The comprehensive Makefile provides full automation:

```bash
make install         # Complete setup + server launch + tunnel
make env             # Create .env from template
make run-server      # Start audit server
make run-local       # Run local audit on test repo
make server-tunnel   # Server + localtunnel for public webhook
make check-env       # Validate environment variables
make clean           # Remove all setup
```

## How It Works

### Audit Flow

1. **Repository Processing**: Downloads/clones target repository
2. **File Discovery**: Scout identifies Solidity files (excluding tests/node_modules)
3. **Static Analysis**: Slither scans for potential vulnerabilities
4. **AI Analysis**: Routing Analyst selects relevant personas based on code heuristics
5. **Persona Reasoning**: Selected AI experts analyze code from their specialty perspective
6. **Exploit Generation**: Architect LLM converts findings into concrete exploit hypotheses
7. **Dynamic Verification**: Foundry tests are generated and executed to confirm exploitability
8. **Result Classification**: Findings categorized as Critical/High/Medium/Low/Informational

### Persona Examples

```json
// Thief Persona (Access Control)
{
  "found_vulnerability": true,
  "title": "Public Initialize Function",
  "severity": "Critical",
  "kill_chain": "Step 1: Call init() with attacker address. Step 2: Become owner..."
}
```

### Exploit Verification

Generated Foundry test example:
```solidity
function testExploit_EXP001() public {
    // Before state
    address beforeOwner = target.owner();

    // Attack steps (AI-generated)
    target.init(msg.sender);  // Step 1: Become owner
    target.setValue(42);      // Step 2: Modify state

    // Verification
    require(target.storedValue() == 42, 'Exploit failed');
}
```

## Performance

Benchmarks show comprehensive analysis capabilities:
- **Sample Run**: 38 findings (20 Critical, 18 High) in ~1.75 minutes
- **Persona Selection**: Routing reduces analysis time by 60-80% vs running all personas
- **Dynamic Testing**: Foundry integration provides exploit verification with high confidence

## Key Features

- **25+ AI Personas**: Specialized experts for different vulnerability classes
- **Hybrid Analysis**: Combines static analysis (Slither) with AI reasoning
- **Exploit Verification**: Dynamic testing confirms theoretical vulnerabilities
- **Intelligent Routing**: Context-aware persona selection based on code patterns
- **Dual Mode Operation**: Server mode for platforms, local mode for direct use
- **Comprehensive Automation**: Makefile provides complete development workflow
- **Severity Classification**: Standard Critical/High/Medium/Low/Informational levels
- **Benchmarking**: Built-in metrics tracking for performance analysis

## Notes

- Requires OpenAI API key for AI analysis
- Uses Slither for static analysis (must be installed separately)
- Foundry required for dynamic exploit verification
- Server mode integrates with AgentArena platform (currently in development)
- All findings include both theoretical analysis and practical verification attempts

## License

MIT License - Copyright (c) 2025 Nethermind

---

*Built with Python 3.8+, FastAPI, OpenAI GPT models, Slither, and Foundry. Specializes in DeFi protocol security auditing.*
