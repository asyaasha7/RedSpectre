
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
