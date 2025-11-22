from .personas.thief import Thief
from .personas.logician import Logician
from typing import List, Dict, Any

class Swarm:
    def __init__(self, api_key: str = None, model: str = None):
        # The Council of Agents
        # Add new personas here as you build them
        self.agents = [
            Thief(api_key=api_key, model=model), 
            Logician(api_key=api_key, model=model)
        ]

    def analyze_file(self, source_code: str, filename: str) -> List[Dict[str, Any]]:
        """
        Broadcasts the file to all agents in the Swarm.
        """
        findings = []
        
        for agent in self.agents:
            # The agent reasons about the file
            analysis = agent.hunt(source_code, filename)
            
            if analysis.get("found_vulnerability"):
                findings.append({
                    "title": analysis.get('title', 'Unknown Vuln'),
                    "description": analysis.get('kill_chain', 'No details'),
                    "severity": analysis.get('severity', 'High'),
                    "file_path": filename,
                    "line_number": analysis.get('line_number', 0),
                    "confidence": "Verified by Swarm Reasoning",
                    "detected_by": agent.name,
                    "attack_logic": analysis.get('kill_chain'),
                    "verification_proof": analysis.get('verification_proof')
                })
                
        return findings
