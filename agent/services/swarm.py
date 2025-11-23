import logging
import re
from typing import List, Dict, Any, Set, Type
from .personas.access_control_expert import AccessControlExpert
from .personas.arithmetic_expert import ArithmeticExpert
from .personas.centralization_expert import CentralizationExpert
from .personas.compiler_expert import CompilerExpert
from .personas.defi_analyst import DeFiAnalyst
from .personas.dos_expert import DoSExpert
from .personas.economic_expert import EconomicExpert
from .personas.error_handling_expert import ErrorHandlingExpert
from .personas.flashloan_expert import FlashLoanExpert
from .personas.frontrunning_expert import FrontrunningExpert
from .personas.gas_optimization_expert import GasOptimizationExpert
from .personas.inheritance_expert import InheritanceExpert
from .personas.interface_expert import InterfaceExpert
from .personas.logician import Logician
from .personas.logic_expert import LogicExpert
from .personas.lowlevel_calls_expert import LowLevelCallsExpert
from .personas.oracle_expert import OracleExpert
from .personas.reentrancy_expert import ReentrancyExpert
from .personas.signature_expert import SignatureExpert
from .personas.storage_proxy_expert import StorageProxyExpert
from .personas.thief import Thief
from .personas.timestamp_expert import TimestampExpert
from .personas.token_expert import TokenExpert
from .personas.validation_expert import ValidationExpert
from .personas.routing_analyst import RoutingAnalyst

logger = logging.getLogger(__name__)

class Swarm:
    def __init__(self, api_key: str = None, model: str = None):
        # The Council of Agents
        # Add new personas here as you build them
        self.agents = [
            Thief(api_key=api_key, model=model),
            AccessControlExpert(api_key=api_key, model=model),
            ArithmeticExpert(api_key=api_key, model=model),
            CentralizationExpert(api_key=api_key, model=model),
            CompilerExpert(api_key=api_key, model=model),
            DeFiAnalyst(api_key=api_key, model=model),
            DoSExpert(api_key=api_key, model=model),
            EconomicExpert(api_key=api_key, model=model),
            ErrorHandlingExpert(api_key=api_key, model=model),
            FlashLoanExpert(api_key=api_key, model=model),
            FrontrunningExpert(api_key=api_key, model=model),
            GasOptimizationExpert(api_key=api_key, model=model),
            InheritanceExpert(api_key=api_key, model=model),
            InterfaceExpert(api_key=api_key, model=model),
            Logician(api_key=api_key, model=model),
            LogicExpert(api_key=api_key, model=model),
            LowLevelCallsExpert(api_key=api_key, model=model),
            OracleExpert(api_key=api_key, model=model),
            ReentrancyExpert(api_key=api_key, model=model),
            SignatureExpert(api_key=api_key, model=model),
            StorageProxyExpert(api_key=api_key, model=model),
            TimestampExpert(api_key=api_key, model=model),
            TokenExpert(api_key=api_key, model=model),
            ValidationExpert(api_key=api_key, model=model),
        ]
        self._agent_by_type = {type(agent): agent for agent in self.agents}
        self._persona_name_to_type: Dict[str, Type] = {
            "Thief": Thief,
            "AccessControlExpert": AccessControlExpert,
            "ArithmeticExpert": ArithmeticExpert,
            "CentralizationExpert": CentralizationExpert,
            "CompilerExpert": CompilerExpert,
            "DeFiAnalyst": DeFiAnalyst,
            "DoSExpert": DoSExpert,
            "EconomicExpert": EconomicExpert,
            "ErrorHandlingExpert": ErrorHandlingExpert,
            "FlashLoanExpert": FlashLoanExpert,
            "FrontrunningExpert": FrontrunningExpert,
            "GasOptimizationExpert": GasOptimizationExpert,
            "InheritanceExpert": InheritanceExpert,
            "InterfaceExpert": InterfaceExpert,
            "Logician": Logician,
            "LogicExpert": LogicExpert,
            "LowLevelCallsExpert": LowLevelCallsExpert,
            "OracleExpert": OracleExpert,
            "ReentrancyExpert": ReentrancyExpert,
            "SignatureExpert": SignatureExpert,
            "StorageProxyExpert": StorageProxyExpert,
            "TimestampExpert": TimestampExpert,
            "TokenExpert": TokenExpert,
            "ValidationExpert": ValidationExpert,
        }
        self.routing_analyst = RoutingAnalyst(api_key=api_key, model=model)

    def _select_agents(self, source_code: str, filename: str) -> List[Any]:
        """
        Routing is delegated to the RoutingAnalyst persona. We only collect lightweight
        context (pragma/imports/contracts/heuristics) to feed the router. If the router
        returns nothing or errors, we fall back to a minimal always-on set.
        """
        code_lower = source_code.lower()

        def has_any(substrings: List[str]) -> bool:
            return any(s in code_lower for s in substrings)

        always_on: Set[Type] = {
            Thief,
            AccessControlExpert,
            ReentrancyExpert,
            LogicExpert,
            Logician,
            DeFiAnalyst,
            GasOptimizationExpert,
        }

        heuristic_hits: Set[str] = set()

        if has_any(["oracle", "pricefeed", "aggregatorv3", "chainlink", "feed", "price"]):
            heuristic_hits.add("oracle")
        if has_any(["flashloan", "flash loan", "flashborrower", "flashborrowerbase", "flash mint", "flashmint"]):
            heuristic_hits.add("flashloan")
        if has_any(["delegatecall", ".delegatecall", "proxy", "upgradeable", "beacon", "transparentupgradable", "implementation"]):
            heuristic_hits.add("proxy")
        if has_any(["swap", "pool", "liquidity", "amm", "lp", "dex", "vault", "stake", "yield"]):
            heuristic_hits.add("amm/defi")
        if has_any(["ecrecover", "permit(", "signature", "nonces", "v,r,s", "signed"]) or "sig" in filename.lower():
            heuristic_hits.add("signature")
        if has_any(["call{value", ".call(", "staticcall", "low level call", "assembly {", "inline assembly"]):
            heuristic_hits.add("low-level")
        if has_any(["timestamp", "block.timestamp", "block.number", "vrf"]):
            heuristic_hits.add("timestamp")
        if has_any(["math", "unchecked", "safemath", "mul(", "div("]):
            heuristic_hits.add("arithmetic")
        if has_any(["token", "erc20", "erc777", "erc721", "erc1155", "allowance", "approve"]):
            heuristic_hits.add("token")
        if has_any(["interface", "interface ", "abi.encode", "abi.decode"]):
            heuristic_hits.add("interface")
        if has_any(["owner", "onlyowner", "accesscontrol", "role", "governance", "multisig", "timelock"]):
            heuristic_hits.add("governance/access")
        if has_any(["error", "require(", "assert(", "revert"]):
            heuristic_hits.add("errors")
        if has_any(["dos", "loop", "while(", "for("]) or "dos" in filename.lower():
            heuristic_hits.add("dos/loop")

        pragma_matches = re.findall(r"pragma\s+solidity\s+([^;]+);", source_code, flags=re.IGNORECASE)
        import_matches = re.findall(r"import\s+[^;]+;", source_code)
        contract_matches = re.findall(r"\b(contract|interface|library)\s+([A-Za-z0-9_]+)", source_code)

        head = source_code[:4000]
        tail = source_code[-2000:] if len(source_code) > 6000 else ""

        router_payload = (
            f"FILENAME: {filename}\\n"
            f"HEURISTICS: {sorted(heuristic_hits)}\\n"
            f"PRAGMA: {pragma_matches}\\n"
            f"IMPORTS: {import_matches[:15]}\\n"
            f"CONTRACTS: {[name for _, name in contract_matches[:15]]}\\n"
            f"ALWAYS_ON: {[cls.__name__ for cls in always_on]}\\n"
            "CODE_HEAD:\\n"
            f"{head}\\n"
            "CODE_TAIL:\\n"
            f"{tail}"
        )

        routed: Set[Type] = set()
        try:
            router_decision = self.routing_analyst.hunt(router_payload, filename)
            persona_names = router_decision.get("personas", [])
            recommended_types = {
                self._persona_name_to_type[name]
                for name in persona_names
                if name in self._persona_name_to_type
            }
            routed |= recommended_types
            if not routed:
                routed |= always_on
                logger.debug("Router returned empty; using always_on fallback.")
            logger.debug(
                "Router selected personas: %s (heuristics=%s, pragma=%s, imports=%d, contracts=%d)",
                persona_names,
                sorted(heuristic_hits),
                pragma_matches,
                len(import_matches),
                len(contract_matches),
            )
        except Exception as e:
            logger.warning("RoutingAnalyst failed; falling back to always_on: %s", e)
            routed |= always_on

        selected = [agent for agent in self.agents if type(agent) in routed]
        logger.debug(
            "Routing %s through %d personas (fallback size=%d).",
            filename,
            len(selected),
            len(always_on),
        )
        return selected

    def analyze_file(self, source_code: str, filename: str) -> List[Dict[str, Any]]:
        """
        Broadcasts the file to all agents in the Swarm.
        """
        findings = []

        for agent in self._select_agents(source_code, filename):
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
                    "attack_logic": analysis.get('kill_chain', 'See description'),
                    "verification_proof": analysis.get('verification_proof')
                })
            elif analysis.get("optimization_opportunity"):
                gas_savings = analysis.get("gas_savings_estimate", "N/A")
                description = analysis.get(
                    "description",
                    "Gas optimization opportunity identified."
                )
                findings.append({
                    "title": analysis.get("title", "Gas Optimization Opportunity"),
                    "description": f"{description}\n\nEstimated gas savings: {gas_savings}",
                    "severity": analysis.get("severity", "Informational"),
                    "file_path": filename,
                    "line_number": analysis.get("line_number", 0),
                    "confidence": "Optimization recommendation",
                    "detected_by": agent.name,
                    "attack_logic": analysis.get("attack_logic", "Gas optimization reasoning"),
                    "verification_proof": analysis.get("verification_proof")
                })
                
        return findings
