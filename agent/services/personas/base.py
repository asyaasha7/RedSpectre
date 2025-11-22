from abc import ABC, abstractmethod
from openai import OpenAI
import os
import json

class BasePersona(ABC):
    def __init__(self, name: str, api_key: str | None, model: str = "gpt-4o"):
        self.name = name
        self.model = model
        # Prefer provided api_key, fallback to env for backwards compatibility
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))

    @abstractmethod
    def get_system_prompt(self) -> str:
        pass

    def hunt(self, source_code: str, filename: str) -> dict:
        system_prompt = self.get_system_prompt()
        user_prompt = f"FILE: {filename}\n\nCODE:\n{source_code}\n\nAnalyze this code strictly according to your persona."

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"[{self.name}] Error: {e}")
            return {"found_vulnerability": False}
