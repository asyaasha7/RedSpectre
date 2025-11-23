# SwarmSecurity - Solidity Security Audit Agent 

## Quick Start

### Installation and Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd SwarmSecurity
   ```

2. **Run the Makefile setup:**
   ```bash
   make all
   ```

   This command will:
   - Create a `.env` file (prompting for required API keys)
   - Set up a Python virtual environment
   - Install all Python dependencies
   - Install npm dependencies (localtunnel)
   - Start the audit-agent server
   - Start a localtunnel for webhook access

   **Note:** The `make all` command will prompt you for:
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `OPENAI_MODEL`: Model to use (default: `gpt-4.1-nano-2025-04-14`)
   - `LOG_LEVEL`: Logging level (default: `INFO`)
   - `LOG_FILE`: Log file path (default: `agent.log`)
   - `AGENTARENA_API_KEY`: (Optional) For server mode
   - `WEBHOOK_AUTH_TOKEN`: (Optional) For server mode
   - `DATA_DIR`: Data directory (default: `./data`)

3. **Alternative: Manual Setup**
   ```bash
   make setup          # Create .env and venv
   source venv/bin/activate
   make install        # Install Python packages
   make install-deps   # Install npm dependencies
   make server         # Start server (or make tunnel for webhook)
   ```

---

## Project Summary

Swarm.Security is an advanced AI-powered security audit agent designed to automatically detect vulnerabilities in Solidity smart contracts. The system employs a **swarm intelligence architecture** where multiple specialized AI personas work collaboratively to analyze code from different security perspectives.

Unlike traditional static analysis tools, Swarm.Security uses Large Language Models (LLMs) to understand contract logic, identify complex attack vectors, and provide detailed explanations of potential vulnerabilities. The agent can operate in two modes:

- **Server Mode**: Receives audit tasks via webhook from the Nethermind Agent Arena platform
- **Local Mode**: Directly audits GitHub repositories for testing and development

The system is built with modularity and extensibility in mind, allowing new security expert personas to be easily added to the swarm.

---

## Built for Nethermind Agent Arena

Swarm.Security was specifically developed to compete in the **Nethermind Agent Arena**, a platform that evaluates AI agents' ability to find security vulnerabilities in smart contracts. The agent is designed to:

1. **Receive Tasks via Webhook**: The platform sends notifications when new audit challenges are available, including:
   - Task ID and repository URL
   - Selected files to audit
   - Additional documentation and context
   - QA responses from the challenge creator

2. **Process Contracts Intelligently**: The agent analyzes the provided Solidity files using its swarm of expert personas, identifying vulnerabilities across multiple security domains.

3. **Submit Findings**: Results are automatically formatted and submitted back to the platform via API, with findings classified by severity (Critical, High, Medium, Low, Informational).

4. **Comply with Platform Standards**: The agent adheres to the Agent Arena's API specifications, including proper authentication, finding format, and response structure.

The architecture is optimized for the competitive environment, balancing thoroughness with efficiency to maximize vulnerability detection within time constraints.

---

## Benchmarks

To validate the effectiveness of Swarm.Security, we conducted comprehensive benchmarking against real-world exploits. Our testing methodology involved comparing the agent's vulnerability detection capabilities against:

1. **Production Code**: The same codebase that ran on the Agent Arena server during competition
2. **Real-World Exploits**: Verified historical exploits from public security repositories

### DeFiHackLabs Verification

We verified the agent's detection capabilities against recent exploits documented in [DeFiHackLabs](https://github.com/SunWeb3Sec/DeFiHackLabs), a comprehensive repository of DeFi hack reproductions using Foundry. This repository contains real-world exploit scenarios that have been successfully executed and verified.

#### Verified Exploits from DeFiHackLabs:

- **20251007 TokenHolder - Access Control**
  - Vulnerability Type: Access Control
  - Successfully detected by the agent's `AccessControlExpert` and `Thief` personas

- **20250827 0xf340 - Access Control**
  - Vulnerability Type: Access Control
  - Detected through comprehensive access control analysis

- **20251004 MIMSpell3 - Bypassed Insolvency Check**
  - Vulnerability Type: Logic Flaw (Insolvency Check Bypass)
  - Identified by `LogicExpert`, `DeFiAnalyst`, and `EconomicExpert` personas

### Additional Verification Sources

The agent has also been tested against exploits from [learn-solidity-hacks](https://github.com/andreitoma8/learn-solidity-hacks.git), which provides educational examples of common Solidity vulnerabilities. These tests help ensure the agent can detect a wide range of vulnerability patterns across different contract architectures and attack vectors.

### Benchmarking Methodology

1. **Repository Cloning**: Each exploit repository is cloned locally
2. **Contract Extraction**: Target contracts are identified and extracted
3. **Agent Analysis**: Swarm.Security analyzes the contracts using its swarm of expert personas
4. **Result Validation**: Findings are compared against known vulnerabilities to verify detection accuracy
5. **False Positive Analysis**: The agent's findings are reviewed to minimize false positives while maintaining high detection rates

This benchmarking approach ensures that Swarm.Security maintains high accuracy in detecting real-world vulnerabilities while operating within the constraints of the Agent Arena platform.

---

## How Swarm.Security Works - High Level

Swarm.Security follows a **multi-stage analysis pipeline**:

### 1. **Entry Point**
   - **Server Mode**: FastAPI webhook endpoint receives notifications from Agent Arena
   - **Local Mode**: Directly processes GitHub repositories via CLI

### 2. **Contract Loading**
   - Downloads/clones the repository
   - Extracts selected Solidity files
   - Loads additional context (documentation, links, QA responses)

### 3. **Intelligent Routing**
   - The **RoutingAnalyst** persona analyzes each file's metadata (imports, pragma, contract names, heuristics)
   - Selects the most relevant expert personas for that specific contract
   - Falls back to a core set of always-on personas if routing fails

### 4. **Parallel Analysis (The Swarm)**
   - Selected personas analyze the contract simultaneously using ThreadPoolExecutor
   - Each persona uses an LLM with a specialized system prompt
   - Returns structured JSON findings with vulnerability details

### 5. **Result Aggregation**
   - Findings from all personas are collected
   - Deduplication and ranking by severity/consensus
   - Top findings (limited to 20) are selected
   - Results formatted for Agent Arena API

### 6. **Submission**
   - Findings are sent back to the platform via POST request
   - Includes detailed descriptions, attack logic, and code snippets

---

## How Swarm.Security Works - Deep Dive

### Architecture Components

#### **BasePersona Class**
All expert personas inherit from `BasePersona`, which provides:
- OpenAI client initialization
- Standardized `hunt()` method that:
  - Formats system and user prompts
  - Calls the LLM with JSON response format
  - Handles errors gracefully
- Each persona implements `get_system_prompt()` with domain-specific expertise

#### **Swarm Service**
The `Swarm` class orchestrates the multi-persona analysis:

1. **Agent Selection (`_select_agents`)**:
   - Extracts lightweight context (pragma, imports, contract names, heuristics)
   - Calls `RoutingAnalyst` with this context
   - Router returns recommended persona list
   - Falls back to always-on set: `Thief`, `AccessControlExpert`, `ReentrancyExpert`, `LogicExpert`, `Logician`, `DeFiAnalyst`, `GasOptimizationExpert`

2. **Heuristic Detection**:
   - Scans code for keywords indicating specific vulnerability types
   - Examples: "oracle", "flashloan", "proxy", "signature", "token", etc.
   - These heuristics inform the router's decision

3. **Parallel Execution**:
   - Uses `ThreadPoolExecutor` to run selected personas concurrently
   - Each persona's `hunt()` method is called with full source code
   - Results are collected and processed

4. **Finding Formatting**:
   - Extracts vulnerability details from persona responses
   - Adds code snippets with line numbers
   - Maps to Agent Arena finding format

#### **Auditor Service**
The `SolidityAuditor` class:
- Initializes `Swarm` and `Scout` (for static analysis)
- Processes list of `SolidityFile` objects
- Calls `swarm.analyze_file()` for each contract
- Aggregates findings and applies deduplication
- Returns `Audit` object with `VulnerabilityFinding` list

#### **Deduplication Service**
The `select_top_findings` function:
- Removes duplicate findings based on similarity
- Ranks by severity (Critical > High > Medium > Low > Informational)
- Limits to top 20 findings to meet platform constraints
- Prioritizes findings with higher consensus (detected by multiple personas)

#### **Server Implementation**
The FastAPI server (`server.py`):
- `/webhook` endpoint receives Agent Arena notifications
- Validates webhook authorization token
- Processes notifications in background tasks
- Downloads repository ZIP, extracts files
- Fetches task details (selected files, docs, links)
- Calls auditor service
- Submits results back to platform

#### **Local Mode**
The local processor (`local.py`):
- Clones GitHub repositories
- Finds all `.sol` files (or allows interactive selection)
- Creates `SolidityFile` objects
- Calls auditor service
- Saves results to JSON file
- Records benchmark metrics

### Data Flow

```
Agent Arena → Webhook → Server
                          ↓
                    Download Repo
                          ↓
                    Load Contracts
                          ↓
                    SolidityAuditor
                          ↓
                    Swarm.analyze_file()
                          ↓
              RoutingAnalyst (selects personas)
                          ↓
        ┌─────────────────┴─────────────────┐
        ↓                                     ↓
  Persona 1 (Thief)              Persona N (OracleExpert)
        ↓                                     ↓
    LLM Analysis                          LLM Analysis
        ↓                                     ↓
  JSON Findings                          JSON Findings
        └─────────────────┬─────────────────┘
                          ↓
                    Aggregate Findings
                          ↓
                    Deduplication
                          ↓
                    Top 20 Selection
                          ↓
                    Format for API
                          ↓
                    POST to Agent Arena
```

---

## Agent Personas

Swarm.Security employs **25 specialized AI personas**, each an expert in a specific security domain. Below is a breakdown of each persona:

### Core Security Personas

#### **Thief**
- **Focus**: Access control and asset draining vulnerabilities
- **Targets**: Public `init`/`initialize` functions, unprotected withdrawal functions
- **Key Patterns**: Privilege escalation, missing `onlyOwner` modifiers
- **Always Active**: Yes

#### **AccessControlExpert**
- **Focus**: Authorization and privilege management
- **Expertise**: Missing access modifiers, `tx.origin` authentication, public initializers, RBAC issues
- **Real-World**: Ronin Bridge ($625M), Poly Network ($611M), Parity Wallet ($150M)
- **Key Patterns**: Unprotected admin functions, default visibility issues, constructor vs initializer confusion

#### **ReentrancyExpert**
- **Focus**: All forms of reentrancy attacks
- **Expertise**: Single-function, cross-function, cross-contract, cross-chain, and read-only reentrancy
- **Real-World**: The DAO ($60M), Cream Finance ($130M), Curve Finance ($69M - read-only)
- **Key Patterns**: Check-Effects-Interactions violations, missing reentrancy guards, state reads during callbacks

#### **LogicExpert**
- **Focus**: General logical flaws and state management issues
- **Targets**: Business logic errors, incorrect state transitions, flawed conditional logic
- **Always Active**: Yes

#### **Logician**
- **Focus**: Methodical analysis of reentrancy and state update patterns
- **Targets**: Check-Effects-Interaction violations, state updates after external calls
- **Always Active**: Yes

### DeFi & Economic Personas

#### **DeFiAnalyst**
- **Focus**: Economic exploits and cross-contract interactions in DeFi protocols
- **Priority Targets**: Oracle manipulation, flash loan attacks, liquidation edge cases, misconfigured parameters, token quirks
- **Always Active**: Yes

#### **FlashLoanExpert**
- **Focus**: Flash loan attack vectors and price manipulation
- **Expertise**: Price manipulation, oracle manipulation via flash loans, governance attacks, liquidity pool manipulation, TWAP manipulation
- **Real-World**: PancakeBunny ($45M), bZx ($954K)
- **Key Patterns**: Spot price calculations, single DEX oracle reliance, governance voting with flash loans

#### **OracleExpert**
- **Focus**: Price oracle manipulation and oracle-related vulnerabilities
- **Expertise**: Spot price vs TWAP, low-liquidity pool exploitation, oracle staleness, weak fallback oracles, single oracle dependency
- **Real-World**: Mango Markets ($116M), Polter Finance ($12M)
- **Key Patterns**: Single DEX price reliance, missing staleness checks, no fallback mechanism

#### **EconomicExpert**
- **Focus**: Economic model vulnerabilities and incentive misalignments
- **Expertise**: Tokenomics flaws, reward calculation errors, incentive manipulation, economic attacks

### Token & Standard Personas

#### **TokenExpert**
- **Focus**: ERC token standard vulnerabilities
- **Expertise**: ERC4626 inflation attacks, ERC20 approval race conditions, fee-on-transfer incompatibility, callback reentrancy (ERC721/1155), missing return value checks
- **Key Patterns**: First depositor manipulation, non-standard token handling, NFT callback reentrancy

#### **SignatureExpert**
- **Focus**: Signature replay attacks and cryptographic vulnerabilities
- **Expertise**: Same-chain/cross-chain replay, signature malleability, `ecrecover` misuse, missing nonces, missing chain ID validation (EIP-155)
- **Real-World**: Wormhole Bridge ($325M)
- **Key Patterns**: Signatures without nonce, missing chainId, zero-address returns from `ecrecover`

### Arithmetic & Validation Personas

#### **ArithmeticExpert**
- **Focus**: Integer overflow/underflow and precision vulnerabilities
- **Expertise**: Overflow/underflow (pre-Solidity 0.8), precision loss in division, rounding errors, unsafe type casting, negative value handling
- **Real-World**: BeautyChain (BEC) BatchOverflow
- **Key Patterns**: Arithmetic without SafeMath, division before multiplication, unchecked loops

#### **ValidationExpert**
- **Focus**: Input validation and boundary checking
- **Expertise**: Missing input validation, boundary condition errors, unchecked user inputs, validation bypasses

### System & Infrastructure Personas

#### **StorageProxyExpert**
- **Focus**: Storage collision, proxy vulnerabilities, and uninitialized contracts
- **Expertise**: Storage collision in UUPS/Transparent proxies, uninitialized proxy/implementation contracts, storage layout mismatches, uninitialized storage pointers, upgrade vulnerabilities
- **Real-World**: Parity Wallet ($150M+)
- **Key Patterns**: Storage slot collisions, missing `_disableInitializers()`, public `initialize()` functions

#### **CompilerExpert**
- **Focus**: Compiler-specific issues and version compatibility
- **Expertise**: Solidity version issues, compiler bugs, ABI encoding problems, optimization pitfalls

#### **InheritanceExpert**
- **Focus**: Inheritance and contract composition vulnerabilities
- **Expertise**: Diamond inheritance issues, function selector collisions, multiple inheritance problems, override errors

#### **InterfaceExpert**
- **Focus**: Interface implementation and external contract interaction issues
- **Expertise**: Interface compliance, missing function implementations, incorrect interface usage

### Low-Level & Advanced Personas

#### **LowLevelCallsExpert**
- **Focus**: Low-level call vulnerabilities (`call`, `delegatecall`, `staticcall`, assembly)
- **Expertise**: Unchecked return values, delegatecall storage collisions, assembly vulnerabilities, gas griefing

#### **TimestampExpert**
- **Focus**: Timestamp and block number manipulation
- **Expertise**: `block.timestamp` manipulation, `block.number` dependencies, VRF vulnerabilities, time-based logic flaws

#### **ErrorHandlingExpert**
- **Focus**: Error handling and exception management
- **Expertise**: Missing error handling, unchecked return values, exception propagation issues, error recovery flaws

### Attack Vector Personas

#### **DoSExpert**
- **Focus**: Denial of Service vulnerabilities
- **Expertise**: Gas griefing, unbounded loops, external call DoS, state exhaustion attacks

#### **FrontrunningExpert**
- **Focus**: Frontrunning and MEV vulnerabilities
- **Expertise**: Transaction ordering dependencies, predictable randomness, sandwich attacks, MEV exploitation

### Centralization & Governance Personas

#### **CentralizationExpert**
- **Focus**: Centralization risks and single points of failure
- **Expertise**: Single owner risks, centralized oracles, admin key management, governance centralization

### Optimization Persona

#### **GasOptimizationExpert**
- **Focus**: Gas inefficiencies and optimization opportunities
- **Expertise**: Storage optimization (packing variables), loop optimization, function visibility, redundant operations, expensive operations in loops
- **Note**: Returns `optimization_opportunity: true` instead of vulnerabilities
- **Always Active**: Yes

### Routing Persona

#### **RoutingAnalyst**
- **Focus**: Intelligent persona selection for each contract
- **Function**: Analyzes contract metadata (filename, heuristics, pragma, imports, contracts, code excerpts) and recommends which personas should analyze the file
- **Output**: List of recommended persona names with justification
- **Fallback**: If router fails or returns empty, uses always-on persona set

---

## Configuration

Create a `.env` file with the following variables:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4.1-nano-2025-04-14

# Logging
LOG_LEVEL=INFO
LOG_FILE=agent.log

# Server Mode (Optional)
AGENTARENA_API_KEY=aa-...
WEBHOOK_AUTH_TOKEN=your_webhook_auth_token
DATA_DIR=./data
```

---

## Usage

### Server Mode

Run the agent as a webhook server:

```bash
audit-agent server
```

Or with custom port:

```bash
audit-agent server --port 8008
```

### Local Mode

Audit a GitHub repository directly:

```bash
audit-agent local --repo https://github.com/example/repo.git --output audit.json
```

For interactive file selection:

```bash
audit-agent local --repo https://github.com/example/repo.git --only-selected-files
```

---

## License

CC NC
