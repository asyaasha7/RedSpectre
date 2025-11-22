
import os
import re
import subprocess
from jinja2 import Environment, FileSystemLoader

BASE_DIR = os.path.dirname(__file__)
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
FOUNDRY_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", "foundry_test"))


def _sanitize_vulnerability_id(raw_id: str) -> str:
    """Keep only alphanumerics/underscore, default to EXP001 if empty."""
    safe = re.sub(r"[^A-Za-z0-9_]+", "", raw_id or "")
    return safe or "EXP001"


def _normalize_hypothesis(hypothesis: dict) -> dict:
    """Validate and fill defaults for the hypothesis schema."""
    is_exploitable = bool(hypothesis.get("is_exploitable"))
    return {
        "is_exploitable": is_exploitable,
        "exploit_name": hypothesis.get("exploit_name", "Unnamed Exploit"),
        "vulnerability_id": _sanitize_vulnerability_id(hypothesis.get("vulnerability_id", "EXP001")),
        "step_1_code": hypothesis.get("step_1_code", ""),
        "step_2_code": hypothesis.get("step_2_code", ""),
        "invariant_check": hypothesis.get("invariant_check", "fail()")
    }

def generate_and_run_test(contract_path, hypothesis):
    normalized = _normalize_hypothesis(hypothesis or {})
    if not normalized["is_exploitable"]:
        return {"success": False, "trace_summary": "Hypothesis marked non-exploitable.", "test_name": None}

    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template("ExploitTemplate.t.sol.jinja2")

    rendered = template.render(
        target_contract_name=os.path.splitext(os.path.basename(contract_path))[0],
        vulnerability_id=normalized["vulnerability_id"],
        step_1_code=normalized["step_1_code"],
        step_2_code=normalized["step_2_code"],
        invariant_check=normalized["invariant_check"]
    )

    test_path = os.path.join(FOUNDRY_ROOT, "test", f"Exploit_{normalized['vulnerability_id']}.t.sol")
    with open(test_path, "w") as f:
        f.write(rendered)

    result = subprocess.run(
        ["forge", "test", "--match-test", f"testExploit_{normalized['vulnerability_id']}"],
        capture_output=True,
        text=True,
        cwd=FOUNDRY_ROOT
    )

    stdout_lower = result.stdout.lower()
    success = result.returncode == 0 and ("1 test passed" in stdout_lower or "test passed" in stdout_lower)
    trace = (result.stdout + "\n" + result.stderr)[-500:]

    return {
        "success": success,
        "trace_summary": trace,
        "test_name": f"testExploit_{normalized['vulnerability_id']}"
    }
