from .base import BasePersona
from agent.services.prompts.audit_prompt import AUDIT_PROMPT


class AuditGeneralist(BasePersona):
    def __init__(self, api_key: str, model: str):
        super().__init__(name="AuditGeneralist", api_key=api_key, model=model)

    def get_system_prompt(self) -> str:
        # Reuse the consolidated audit prompt so this persona can provide a holistic pass.
        return AUDIT_PROMPT
