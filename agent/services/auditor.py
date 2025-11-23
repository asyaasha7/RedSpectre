"""
Core service for auditing Solidity contracts using RedSpectre Swarm.
MODIFIED to integrate Swarm logic while maintaining template compatibility.
"""
import json
import logging
from typing import List
from pydantic import BaseModel, Field
from openai import OpenAI

# --- REDSPECTRE IMPORTS ---
from agent.services.swarm import Swarm
from agent.services.scout import Scout
from agent.services.dedup import select_top_findings
# --------------------------

logger = logging.getLogger(__name__)

# Keep these models identical to the template so dependent files don't break
class VulnerabilityFinding(BaseModel):
    """Model representing a single vulnerability finding."""
    title: str = Field(..., description="Title of the vulnerability")
    description: str = Field(..., description="Detailed description of the vulnerability")
    severity: str = Field(..., description="Severity level: Critical, High, Medium, Low, or Informational")
    file_paths: List[str] = Field(..., description="List of file paths containing the vulnerability")

class Audit(BaseModel):
    """Model representing the complete audit response."""
    findings: List[VulnerabilityFinding] = Field(default_factory=list, description="List of vulnerability findings")

class SolidityAuditor:
    """Service for auditing Solidity contracts using RedSpectre Swarm."""
    
    def __init__(self, api_key: str, model: str):
        """
        Initialize the auditor with OpenAI credentials.
        """
        self.model = model
        self.client = OpenAI(api_key=api_key)
        
        # Initialize RedSpectre Components
        self.scout = Scout()
        self.swarm = Swarm(api_key=api_key, model=model)

    def audit_files(self, contracts: List[object], docs: str = "", additional_links: List[str] = None, additional_docs: str = None, qa_responses: List = None) -> Audit:
        """
        RedSpectre Implementation:
        1. Takes the list of SolidityFile objects (from local.py/server.py)
        2. Feeds them to the Swarm (Thief/Logician)
        3. Returns the standard Audit object compatible with AgentArena
        """
        try:
            logger.info("🚀 RedSpectre Swarm Activated")
            logger.info(f"Received contracts payload type={type(contracts)}")
            verified_findings = []

            # In the template, 'contracts' is passed as a List[SolidityFile] object in local.py
            # But sometimes as a string in other contexts. We handle the list case here.
            files_to_audit = contracts if isinstance(contracts, list) else []
            if not files_to_audit:
                logger.warning("No contracts supplied to audit_files; skipping swarm analysis.")
            
            # 1. The Swarm Analysis Loop
            for file_obj in files_to_audit:
                # file_obj has .path and .content attributes (from models/solidity_file.py)
                logger.info(f"Swarm analyzing: {file_obj.path}")
                
                # Call the Swarm
                # We pass the content and filename to the swarm logic
                swarm_results = self.swarm.analyze_file(file_obj.content, file_obj.path)
                logger.debug(f"Raw swarm results for {file_obj.path}: {swarm_results}")
                
                for res in swarm_results:
                    # Map RedSpectre result to AgentArena Finding Model
                    # We construct a detailed description including the reasoning logic
                    detailed_desc = (
                        f"{res['description']}\n\n"
                        f"**Detected by:** {res['detected_by']} Persona\n"
                        f"**Attack Logic:** {res['attack_logic']}"
                    )

                    verified_findings.append(VulnerabilityFinding(
                        title=res['title'],
                        description=detailed_desc,
                        severity=res['severity'],
                        file_paths=[file_obj.path]
                    ))

            limited = select_top_findings(verified_findings, limit=20)
            if len(verified_findings) > 20:
                logger.info(f"Limiting findings to top {len(limited)} by consensus/severity (from {len(verified_findings)})")

            logger.info(f"✅ Audit completed with {len(limited)} returned findings (initial: {len(verified_findings)})")
            # Explicit print to stdout for quick debugging when running the server
            # print(f"[Audit Debug] Verified findings (pre-dedup): {verified_findings}")
            # print(f"[Audit Debug] Deduped findings: {deduped}")
            # print(f"[Audit Debug] Limited (top 20): {limited}")
            return Audit(findings=limited)

        except Exception as e:
            logger.error(f"Error during RedSpectre audit: {str(e)}", exc_info=True)
            return Audit(findings=[])
