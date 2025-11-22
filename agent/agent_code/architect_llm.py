
import json
import os
from openai import OpenAI
from .prompts import SYSTEM_PROMPT

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
