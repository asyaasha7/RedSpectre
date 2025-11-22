
import json

def clean_llm_json(raw):
    try:
        return json.loads(raw)
    except:
        return {"is_exploitable": False}
