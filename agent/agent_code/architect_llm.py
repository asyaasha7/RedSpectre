
import json
import os
from typing import Optional
from openai import OpenAI
from .prompts import SYSTEM_PROMPT

def generate_attack_hypothesis(contract_path, slither_finding, retry_reason: Optional[str] = None):
    source_code = open(contract_path).read()

    prompt = f"""
Contract source:
{source_code}

Slither finding (already parsed):
{json.dumps(slither_finding, indent=2)}

Instructions:
- Produce ONLY JSON, no markdown, no prose.
- Use the exact schema below. Fill every field. Use lowercase true/false for booleans.
- Use only functions/state that exist in the contract.
- Keep step_1_code and step_2_code short snippets of Solidity test code to execute the exploit.
- invariant_check should assert success (e.g., vm.assertEq/require style) or otherwise fail the test.
- vulnerability_id must remain "EXP001".

JSON Schema (fill these fields exactly):
{{
  "is_exploitable": true,
  "exploit_name": "string",
  "step_1_code": "string",
  "step_2_code": "string",
  "invariant_check": "string",
  "vulnerability_id": "EXP001"
}}
"""
    if retry_reason:
        prompt += f"\nPrevious attempt failed because: {retry_reason}\nReturn valid JSON now."

    client = OpenAI()
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content
