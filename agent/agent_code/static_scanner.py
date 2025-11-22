
import json
import os
import subprocess


def run_slither_scan(contract_path: str):
    """Run Slither and return normalized findings; include error info if scan fails."""
    abs_contract_path = os.path.abspath(contract_path)
    if not os.path.exists(abs_contract_path):
        return {"findings": [], "error": f"contract_not_found:{contract_path}"}

    # Run Slither from the Foundry project root so Crytic finds foundry.toml
    foundry_root = os.path.abspath(os.path.join(abs_contract_path, os.pardir, os.pardir))
    report_path = os.path.join(foundry_root, "slither_report.json")

    # Remove stale report to avoid reading old data
    if os.path.exists(report_path):
        try:
            os.remove(report_path)
        except OSError:
            pass

    # Use absolute path for the target so Slither can resolve it reliably
    cmd = ["slither", abs_contract_path, "--json", report_path]
    result = subprocess.run(cmd, cwd=foundry_root, capture_output=True, text=True)

    findings = []
    data = {}
    if os.path.exists(report_path):
        try:
            with open(report_path) as f:
                data = json.load(f)
        except Exception:
            data = {}

    for item in data.get("results", {}).get("detectors", []):
        findings.append({
            "id": item.get("check"),
            "impact": item.get("impact"),
            "elements": item.get("elements", [])
        })

    error = None
    if result.returncode != 0:
        error = result.stderr.strip() or "slither_returned_nonzero"
        # If Slither failed entirely, clear findings to avoid stale data
        if not data:
            findings = []

    return {"findings": findings, "error": error}
