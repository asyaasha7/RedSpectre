"""
Core service for auditing Solidity contracts using RedSpectre Swarm.
MODIFIED to integrate Swarm logic while maintaining template compatibility.
"""
import json
import logging
from datetime import datetime
from typing import List
from pydantic import BaseModel, Field
from openai import OpenAI

# --- REDSPECTRE IMPORTS ---
from agent.services.swarm import Swarm
from agent.services.scout import Scout
from agent.services.dedup import select_top_findings
from agent.services.prompts.audit_prompt import AUDIT_PROMPT
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
    
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        """
        Initialize the auditor with OpenAI credentials.
        """
        self.model = model
        self.client = OpenAI(api_key=api_key)
        
        # Initialize RedSpectre Components
        self.scout = Scout()
        self.swarm = Swarm(api_key=api_key, model=model)

    def _fallback_audit_prompt(self, contracts: List[object], docs: str, additional_links: List[str], additional_docs: str, qa_responses: List) -> List[dict]:
        """
        Runs a single-shot audit using the consolidated AUDIT_PROMPT to recover findings
        when personas return nothing.
        """
        try:
            contract_blobs = []
            for f in contracts:
                try:
                    contract_blobs.append(f"// {f.path}\n{f.content}")
                except Exception:
                    continue
            rendered_prompt = AUDIT_PROMPT.format(
                contracts="\n\n".join(contract_blobs) or "/* No contracts provided */",
                docs=docs or "None",
                additional_docs=additional_docs or "None",
                additional_links="\n".join(additional_links or []),
                qa_responses=qa_responses or "None",
            )
            severity_normalization = {
                "Critical": "Critical",
                "High": "High",
                "Medium": "Medium",
                "Low": "Low",
                "Info": "Informational",
                "Informational": "Informational",
            }
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert Solidity smart contract auditor. Follow the user's format and respond with strict JSON only.",
                    },
                    {"role": "user", "content": rendered_prompt},
                ],
                response_format={"type": "json_object"},
            )
            data = json.loads(response.choices[0].message.content)
            findings = data.get("findings", [])
            normalized = []
            for f in findings:
                sev = severity_normalization.get(f.get("severity", "High"), "High")
                normalized.append(
                    {
                        "title": f.get("title", "Untitled"),
                        "description": f.get("description", ""),
                        "severity": sev,
                        "file_paths": f.get("file_paths", []),
                        "line_number": f.get("line_number", 0),
                        "attack_logic": f.get("attack_logic"),
                        "verification_proof": f.get("verification_proof"),
                        "detected_by": "AuditPrompt",
                    }
                )
            return normalized
        except Exception as e:
            logger.warning("Fallback AUDIT_PROMPT failed: %s", e, exc_info=True)
            return []

    def audit_files(self, contracts: List[object], docs: str = "", additional_links: List[str] = None, additional_docs: str = None, qa_responses: List = None, benchmark_mode: bool = False) -> Audit:
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
            raw_persona_outputs = [] if benchmark_mode else None

            for file_obj in files_to_audit:
                # file_obj has .path and .content attributes (from models/solidity_file.py)
                logger.info(f"Swarm analyzing: {file_obj.path}")
                
                # Call the Swarm
                # We pass the content, filename, and any supplemental context to the swarm logic
                swarm_results = self.swarm.analyze_file(
                    file_obj.content,
                    file_obj.path,
                    docs=docs,
                    additional_links=additional_links,
                    additional_docs=additional_docs,
                    qa_responses=qa_responses,
                    persona_outputs=raw_persona_outputs,
                )
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

            if not verified_findings and files_to_audit:
                logger.info("No swarm findings; invoking fallback AUDIT_PROMPT.")
                fallback = self._fallback_audit_prompt(files_to_audit, docs, additional_links or [], additional_docs, qa_responses or [])
                for res in fallback:
                    verified_findings.append(VulnerabilityFinding(
                        title=res['title'],
                        description=res['description'],
                        severity=res['severity'],
                        file_paths=res.get('file_paths') or [files_to_audit[0].path]
                    ))

            limited = select_top_findings(verified_findings, limit=20)
            if len(verified_findings) > 20:
                logger.info(f"Limiting findings to top {len(limited)} by consensus/severity (from {len(verified_findings)})")

            logger.info(f"✅ Audit completed with {len(limited)} returned findings (initial: {len(verified_findings)})")
            if benchmark_mode:
                logger.info("Benchmark mode: raw persona outputs=%d, combined deduped=%d", len(raw_persona_outputs or []), len(limited))
                try:
                    logger.debug("Benchmark raw persona outputs: %s", json.dumps(raw_persona_outputs, indent=2, default=str))
                    logger.debug("Benchmark deduped outputs: %s", json.dumps([f.model_dump() for f in limited], indent=2, default=str))
                    benchmark_payload = {
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "raw_persona_outputs": raw_persona_outputs or [],
                        "deduped_findings": [f.model_dump() for f in limited],
                    }
                    with open("benchmarks/last_benchmark.json", "w") as f:
                        json.dump(benchmark_payload, f, indent=2)
                    logger.info("Benchmark artifacts written to benchmarks/last_benchmark.json")
                except Exception:
                    logger.debug("Benchmark serialization failed for persona outputs or findings.")
            return Audit(findings=limited)

        except Exception as e:
            logger.error(f"Error during RedSpectre audit: {str(e)}", exc_info=True)
            return Audit(findings=[])
