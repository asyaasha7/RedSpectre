
import os
import json
from .static_scanner import run_slither_scan
from .architect_llm import generate_attack_hypothesis
from .dynamic_executor import generate_and_run_test
from .parsers import parse_llm_json


def run_redspectre(target_contract_path: str):
    print("[*] Starting RedSpectre Analysis")

    print("[*] Running static analysis...")
    slither_results = run_slither_scan(target_contract_path)
    print(f"[+] Slither returned {len(slither_results['findings'])} findings.")
    if slither_results.get("error"):
        print(f"[!] Slither reported an error: {slither_results['error']}")

    verified_exploits = []
    suspected_exploits = []

    if not slither_results["findings"]:
        print("[!] No findings returned by Slither; skipping exploitation phase.")

    for finding in slither_results["findings"]:
        print(f"\n[*] Evaluating finding: {finding['id']} ({finding['impact']})")

        max_attempts = 2
        hypothesis = {"is_exploitable": False}
        parse_error = None
        for attempt in range(1, max_attempts + 1):
            retry_reason = None if attempt == 1 else parse_error
            hypothesis_raw = generate_attack_hypothesis(
                contract_path=target_contract_path,
                slither_finding=finding,
                retry_reason=retry_reason
            )
            parsed, valid, parse_error = parse_llm_json(hypothesis_raw)
            if valid:
                hypothesis = parsed
                break
            print(f"[!] LLM output invalid (attempt {attempt}/{max_attempts}): {parse_error}")

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
