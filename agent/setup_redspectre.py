import os

# ========== DIRECTORY STRUCTURE ==========
dirs = [
    "agent_code",
    "agent_code/templates",
    "foundry_test",
    "foundry_test/src",
    "foundry_test/test"
]

for d in dirs:
    os.makedirs(d, exist_ok=True)

# ========== FILE CONTENTS ==========

files = {
"agent_code/orchestrator.py": r'''
import os
import json
from agent_code.static_scanner import run_slither_scan
from agent_code.architect_llm import generate_attack_hypothesis
from agent_code.dynamic_executor import generate_and_run_test
from agent_code.parsers import clean_llm_json


def run_redspectre(target_contract_path: str):
    print("[*] Starting RedSpectre Analysis")

    print("[*] Running static analysis...")
    slither_results = run_slither_scan(target_contract_path)
    print(f"[+] Slither returned {len(slither_results['findings'])} findings.")

    verified_exploits = []
    suspected_exploits = []

    for finding in slither_results["findings"][:3]:
        print(f"\n[*] Evaluating finding: {finding['id']} ({finding['impact']})")

        hypothesis_raw = generate_attack_hypothesis(
            contract_path=target_contract_path,
            slither_finding=finding
        )
        hypothesis = clean_llm_json(hypothesis_raw)

        if not hypothesis.get("is_exploitable"):
            print("[!] LLM decided this is not exploitable.\n")
            suspected_exploits.append(finding)
            continue

        print(f"[+] Hypothesis: {hypothesis['exploit_name']}")

        result = generate_and_run_test(
            target_contract_path,
            hypothesis
        )

        if result["success"]:
            print(f"[+] VERIFIED exploit: {hypothesis['exploit_name']}\n")
            verified_exploits.append({
                "name": hypothesis["exploit_name"],
                "severity": "Critical",
                "trace": result["trace_summary"],
                "steps": [hypothesis["step_1_code"], hypothesis["step_2_code"]],
                "test_name": result["test_name"]
            })
        else:
            print("[-] Exploit failed, storing as suspected.")
            suspected_exploits.append(finding)

    final_report = {
        "verified": verified_exploits,
        "suspected": suspected_exploits
    }

    print("\n========== FINAL REPORT ==========")
    print(json.dumps(final_report, indent=2))

    return final_report
''',

"agent_code/static_scanner.py": r'''
import json
import subprocess

def run_slither_scan(contract_path: str):
    cmd = ["slither", contract_path, "--json", "slither_report.json"]
    subprocess.run(cmd, check=False)

    try:
        with open("slither_report.json") as f:
            data = json.load(f)
    except:
        data = {"findings": []}

    findings = []
    for item in data.get("results", {}).get("detectors", []):
        findings.append({
            "id": item.get("check"),
            "impact": item.get("impact"),
            "elements": item.get("elements", [])
        })

    return {"findings": findings}
''',

"agent_code/architect_llm.py": r'''
import json
import openai
from agent_code.prompts import SYSTEM_PROMPT

def generate_attack_hypothesis(contract_path, slither_finding):
    source_code = open(contract_path).read()

    prompt = f"""
You are RedSpectre, an elite smart contract exploit hunter.

Contract:
{source_code}

Slither Finding:
{json.dumps(slither_finding, indent=2)}

Follow your exploit playbooks and OUTPUT JSON ONLY.

JSON Schema:
{{
  "is_exploitable": bool,
  "exploit_name": str,
  "step_1_code": str,
  "step_2_code": str,
  "invariant_check": str,
  "vulnerability_id": "EXP001"
}}
"""

    response = openai.ChatCompletion.create(
        model="gpt-5",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
    )

    return response["choices"][0]["message"]["content"]
''',

"agent_code/dynamic_executor.py": r'''
import subprocess
import os
from jinja2 import Environment, FileSystemLoader

def generate_and_run_test(contract_path, hypothesis):
    env = Environment(loader=FileSystemLoader("agent_code/templates"))
    template = env.get_template("ExploitTemplate.t.sol.jinja2")

    rendered = template.render(
        target_contract_name=os.path.splitext(os.path.basename(contract_path))[0],
        vulnerability_id=hypothesis["vulnerability_id"],
        step_1_code=hypothesis["step_1_code"],
        step_2_code=hypothesis["step_2_code"],
        invariant_check=hypothesis["invariant_check"]
    )

    test_path = f"foundry_test/test/Exploit_{hypothesis['vulnerability_id']}.t.sol"
    with open(test_path, "w") as f:
        f.write(rendered)

    result = subprocess.run(
        ["forge", "test", "--match-test", f"testExploit_{hypothesis['vulnerability_id']}"],
        capture_output=True,
        text=True
    )

    success = ("test passed" in result.stdout.lower()) or ("ok" in result.stdout.lower())

    return {
        "success": success,
        "trace_summary": result.stdout[-500:],
        "test_name": f"testExploit_{hypothesis['vulnerability_id']}"
    }
''',

"agent_code/parsers.py": r'''
import json

def clean_llm_json(raw):
    try:
        return json.loads(raw)
    except:
        return {"is_exploitable": False}
''',

"agent_code/prompts.py": r'''
SYSTEM_PROMPT = """
You are RedSpectre, an elite hybrid attacker.
Your mission: Turn static Slither hints into dynamic Foundry exploits.
Respond ONLY with valid JSON.
"""
''',

"agent_code/templates/ExploitTemplate.t.sol.jinja2": r'''
// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import "forge-std/Test.sol";
import "../src/{{ target_contract_name }}.sol";

contract AutoExploitTest_{{ vulnerability_id }} is Test {
    {{ target_contract_name }} public target;

    function setUp() public {
        target = new {{ target_contract_name }}();
        vm.deal(address(this), 100 ether);
    }

    function testExploit_{{ vulnerability_id }}() public {
        address beforeOwner = target.owner();
        uint256 beforeBalance = address(target).balance;

        console.log("[-] Before: owner=%s bal=%s", beforeOwner, beforeBalance);

        {{ step_1_code }}
        {{ step_2_code }}

        address afterOwner = target.owner();
        uint256 afterBalance = address(target).balance;

        console.log("[+] After: owner=%s bal=%s", afterOwner, afterBalance);

        {{ invariant_check }}
    }
}
''',

"run_agent.sh": r'''#!/bin/bash
set -e
echo "[*] Running RedSpectre..."
python3 - <<EOF
from agent_code.orchestrator import run_redspectre
run_redspectre("foundry_test/src/Target.sol")
EOF
''',

"Dockerfile": r'''
FROM python:3.10-slim-bullseye

RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

ENV FOUNDRY_DIR="/root/.foundry"
ENV PATH="$FOUNDRY_DIR/bin:$PATH"
RUN curl -L https://foundry.paradigm.xyz | bash && foundryup

RUN pip install slither-analyzer solc-select
RUN solc-select install 0.8.20 && solc-select use 0.8.20

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENTRYPOINT ["./run_agent.sh"]
''',

"requirements.txt": r'''
openai
jinja2
slither-analyzer
''',

"foundry_test/foundry.toml": r'''
[profile.default]
src = "src"
test = "test"
libs = ["lib"]
'''
}

# ========== WRITE FILES ==========
for path, content in files.items():
    with open(path, "w") as f:
        f.write(content)

print("RedSpectre scaffold created successfully!")
