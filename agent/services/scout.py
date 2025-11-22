import os
import logging

logger = logging.getLogger(__name__)

class Scout:
    """
    Identifies target files to analyze.
    Currently acts as a file walker. Ready to be upgraded with Slither integration.
    """
    def scan(self, repo_path: str) -> list:
        logger.info("👀 Scout is walking the file tree...")
        leads = []
        
        for root, _, files in os.walk(repo_path):
            for file in files:
                # Filter: Only Solidity files, ignore tests/node_modules to save tokens
                if file.endswith(".sol") and "test" not in root.lower() and "node_modules" not in root.lower():
                    full_path = os.path.join(root, file)
                    leads.append({
                        "file_path": full_path,
                        "rel_path": os.path.relpath(full_path, repo_path),
                        "description": "Source Code Analysis Target"
                    })
        
        logger.info(f"Scout found {len(leads)} targets.")
        return leads