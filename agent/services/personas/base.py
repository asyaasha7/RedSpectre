from abc import ABC, abstractmethod
from openai import OpenAI
import os
import json
import re
from typing import Dict, Any, List

class BasePersona(ABC):
    def __init__(self, name: str, api_key: str | None, model: str = "gpt-4o"):
        self.name = name
        self.model = model
        # Prefer provided api_key, fallback to env for backwards compatibility
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))

    @abstractmethod
    def get_system_prompt(self) -> str:
        pass

    def _normalize_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        allowed_severities = {"Critical", "High", "Medium", "Low", "Informational"}
        severity_normalization = {
            "critical": "Critical",
            "high": "High",
            "medium": "Medium",
            "low": "Low",
            "info": "Informational",
            "informational": "Informational",
            "high/critical": "Critical",
            "critical/high": "Critical",
            "high/medium": "High",
            "medium/high": "High",
            "medium/low": "Medium",
            "low/medium": "Medium",
        }

        # Default structure
        normalized = {
            "found_vulnerability": bool(data.get("found_vulnerability", False)),
            "optimization_opportunity": bool(data.get("optimization_opportunity", False)),
            "title": data.get("title", "Unknown Finding"),
            "description": data.get("description", data.get("kill_chain", "")),
            "attack_logic": data.get("attack_logic", data.get("kill_chain", "")),
            "verification_proof": data.get("verification_proof"),
            "gas_savings_estimate": data.get("gas_savings_estimate"),
            "kill_chain": data.get("kill_chain"),
            "affected_functions": data.get("affected_functions") or [],
            "affected_lines": data.get("affected_lines") or [],
        }

        severity_raw = str(data.get("severity", "High"))
        sev_key = severity_raw.strip().lower()
        severity = severity_normalization.get(sev_key, None)
        if severity is None and severity_raw in allowed_severities:
            severity = severity_raw
        if severity not in allowed_severities:
            severity = "High"
        normalized["severity"] = severity

        try:
            line_number = int(data.get("line_number", 0))
            if line_number < 0:
                line_number = 0
        except Exception:
            line_number = 0
        # Prefer an explicit affected_lines entry if provided
        if not line_number:
            try:
                if normalized["affected_lines"]:
                    line_number = int(normalized["affected_lines"][0])
            except Exception:
                line_number = 0
        normalized["line_number"] = line_number

        def _clamp_int(val, default=50):
            try:
                parsed = int(val)
                return max(0, min(100, parsed))
            except Exception:
                return default

        normalized["confidence_score"] = _clamp_int(data.get("confidence_score", 60))
        normalized["false_positive_risk"] = _clamp_int(data.get("false_positive_risk", 30))

        return normalized

    def _extract_code_context(self, source_code: str) -> Dict[str, Any]:
        lines = source_code.splitlines()
        line_count = len(lines)
        func_pattern = re.compile(
            r"function\s+([A-Za-z0-9_]+)\s*\(([^)]*)\)\s*(public|external|internal|private)?\s*(payable)?\s*(view|pure)?",
            re.IGNORECASE,
        )
        functions: List[Dict[str, Any]] = []
        for match in func_pattern.finditer(source_code):
            name, _, visibility, payable, mutability = match.groups()
            functions.append(
                {
                    "name": name,
                    "visibility": visibility or "",
                    "payable": bool(payable),
                    "mutability": mutability or "",
                }
            )
        external_funcs = [f["name"] for f in functions if f["visibility"].lower() in {"external", "public"}]
        payable_funcs = [f["name"] for f in functions if f["payable"]]
        pragma_match = re.search(r"pragma\s+solidity\s+([^;]+);", source_code, re.IGNORECASE)
        pragma = pragma_match.group(1).strip() if pragma_match else "unspecified"
        # Rough version detect: take first numeric token
        version_number = None
        version_match = re.search(r"(\d+\.\d+(?:\.\d+)?)", pragma or "")
        if version_match:
            try:
                parts = version_match.group(1).split(".")
                major, minor = int(parts[0]), int(parts[1])
                version_number = (major, minor)
            except Exception:
                version_number = None
        is_sol_0_8_plus = False
        if version_number:
            maj, minr = version_number
            is_sol_0_8_plus = (maj > 0) or (maj == 0 and minr >= 8)
        uses_safe_math = "using safemath" in source_code.lower()
        has_reentrancy_guard = "nonreentrant" in source_code.lower() or "reentrancyguard" in source_code
        unchecked_blocks = len(re.findall(r"\bunchecked\s*{", source_code))

        return {
            "line_count": line_count,
            "function_count": len(functions),
            "external_functions": external_funcs,
            "payable_functions": payable_funcs,
            "functions_preview": functions[:10],
            "pragma": pragma,
            "is_sol_0_8_plus": is_sol_0_8_plus,
            "uses_safe_math": uses_safe_math,
            "has_reentrancy_guard": has_reentrancy_guard,
            "unchecked_blocks": unchecked_blocks,
        }

    def hunt(
        self,
        source_code: str,
        filename: str,
        docs: str | None = None,
        additional_links: list | None = None,
        additional_docs: str | None = None,
        qa_responses: list | None = None,
    ) -> dict:
        system_prompt = self.get_system_prompt()
        context = self._extract_code_context(source_code)
        user_prompt = (
            f"FILE: {filename}\n\nCODE:\n{source_code}\n\n"
            "CONTEXT (use only if relevant and cite when used):\n"
            f"Docs:\n{docs or 'None'}\n\n"
            f"Additional Docs:\n{additional_docs or 'None'}\n\n"
            f"Additional Links:\n{(additional_links or [])}\n\n"
            f"Q&A:\n{qa_responses or 'None'}\n\n"
            "CODE STATS:\n"
            f"- Lines: {context['line_count']}\n"
            f"- Functions: {context['function_count']}\n"
            f"- External/Public: {context['external_functions']}\n"
            f"- Payable: {context['payable_functions']}\n"
            f"- Functions preview: {context['functions_preview']}\n"
            f"- Pragma: {context['pragma']}\n"
            f"- Solidity >=0.8: {context['is_sol_0_8_plus']}\n"
            f"- Uses SafeMath: {context['uses_safe_math']}\n"
            f"- Has ReentrancyGuard/nonReentrant: {context['has_reentrancy_guard']}\n"
            f"- unchecked blocks: {context['unchecked_blocks']}\n\n"
            "Analyze this code strictly according to your persona.\n"
            "Methodology:\n"
            " 1) Identify external/public/payable and state-changing surfaces.\n"
            " 2) Map persona-specific risks to those surfaces using concrete code cues.\n"
            " 3) Avoid false positives: CEI with reentrancy guards is safe; arithmetic in Solidity >=0.8 has built-in checks unless unchecked; validated interfaces with require statements are acceptable.\n"
            " 4) Cite exact lines and functions; do not report without a specific location.\n"
            " 5) Provide a concise proof-of-concept or reasoning chain.\n"
            "Respond with a single JSON object matching:\n"
            "{\n"
            '  "found_vulnerability": boolean,\n'
            '  "optimization_opportunity": boolean (optional),\n'
            '  "title": "Clear title",\n'
            '  "severity": "Critical|High|Medium|Low|Informational",\n'
            '  "line_number": integer (best-guess line of issue),\n'
            '  "affected_functions": ["funcName", ...],\n'
            '  "affected_lines": [int, ...],\n'
            '  "confidence_score": 0-100,\n'
            '  "false_positive_risk": 0-100,\n'
            '  "description": "Details and remediation",\n'
            '  "attack_logic": "How it is exploited",\n'
            '  "verification_proof": "Minimal PoC or reasoning",\n'
            '  "proof_of_concept": "Optional concrete exploit steps or code"\n'
            "}\n"
            'If no issue, return {"found_vulnerability": false}.'
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"}
            )
            raw = json.loads(response.choices[0].message.content)
            return self._normalize_response(raw)
        except Exception as e:
            print(f"[{self.name}] Error: {e}")
            return {"found_vulnerability": False}
