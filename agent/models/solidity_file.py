"""
Data models for Solidity files.
"""
from pydantic import BaseModel
from typing import Optional

class SolidityFile(BaseModel):
    """Represents a Solidity source file."""
    path: str
    content: str
    repo_url: Optional[str] = None 