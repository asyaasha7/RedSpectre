
import json
from typing import Tuple, Dict, Any


REQUIRED_FIELDS = {
    "is_exploitable": bool,
    "exploit_name": str,
    "step_1_code": str,
    "step_2_code": str,
    "invariant_check": str,
    "vulnerability_id": str,
}


def clean_llm_json(raw: str) -> Dict[str, Any]:
    """Backward-compatible parser that returns a minimal dict."""
    parsed, valid, _ = parse_llm_json(raw)
    if not valid:
        return {"is_exploitable": False}
    return parsed


def parse_llm_json(raw: str) -> Tuple[Dict[str, Any], bool, str]:
    """
    Parse and validate LLM JSON against the expected schema.
    Returns (parsed_dict, is_valid, error_message).
    """
    try:
        data = json.loads(raw)
    except Exception as exc:
        return {}, False, f"json_decode_error: {exc}"

    if not isinstance(data, dict):
        return {}, False, "json_not_object"

    missing = [k for k in REQUIRED_FIELDS if k not in data]
    if missing:
        return {}, False, f"missing_fields: {','.join(missing)}"

    # Soft type checks; allow truthy/falsy coercion for bool.
    for key, expected_type in REQUIRED_FIELDS.items():
        val = data.get(key)
        if expected_type is bool and not isinstance(val, bool):
            return {}, False, f"field_type:{key}=expected_bool"
        if expected_type is str and not isinstance(val, str):
            return {}, False, f"field_type:{key}=expected_str"

    return data, True, ""
