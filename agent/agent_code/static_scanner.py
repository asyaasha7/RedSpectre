
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
