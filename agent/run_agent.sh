#!/bin/bash
set -e
echo "[*] Running RedSpectre..."
python3 - <<EOF
from agent_code.orchestrator import run_redspectre
run_redspectre("foundry_test/src/Target.sol")
EOF
