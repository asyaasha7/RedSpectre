import logging
import re
import concurrent.futures
import hashlib
import threading
import copy
from typing import List, Dict, Any, Set, Type, Optional
from .personas.access_control_expert import AccessControlExpert
from .personas.arithmetic_expert import ArithmeticExpert
from .personas.centralization_expert import CentralizationExpert
from .personas.defi_analyst import DeFiAnalyst
from .personas.dos_expert import DoSExpert
from .personas.economic_expert import EconomicExpert
from .personas.error_handling_expert import ErrorHandlingExpert
from .personas.flashloan_expert import FlashLoanExpert
from .personas.frontrunning_expert import FrontrunningExpert
from .personas.gas_optimization_expert import GasOptimizationExpert
from .personas.inheritance_expert import InheritanceExpert
from .personas.logic_expert import LogicExpert
from .personas.lowlevel_calls_expert import LowLevelCallsExpert
from .personas.oracle_expert import OracleExpert
from .personas.reentrancy_expert import ReentrancyExpert
from .personas.signature_expert import SignatureExpert
from .personas.storage_proxy_expert import StorageProxyExpert
from .personas.thief import Thief
from .personas.timestamp_expert import TimestampExpert
from .personas.token_expert import TokenExpert
from .personas.routing_analyst import RoutingAnalyst
from .personas.critic import Critic

logger = logging.getLogger(__name__)

class Swarm:
    def __init__(
        self,
        api_key: str = None,
        model: str = "gpt-4o",
        cache_enabled: bool = False,
        persona_models: Optional[Dict[str, str]] = None,
        routing_enabled: bool = False,
    ):
        # The Council of Agents
        # Add new personas here as you build them
        self.persona_models = persona_models or {}

        def _select_model(cls):
            return self.persona_models.get(cls.__name__, model)

        self.agents = [
            Thief(api_key=api_key, model=_select_model(Thief)),
            AccessControlExpert(api_key=api_key, model=_select_model(AccessControlExpert)),
            ArithmeticExpert(api_key=api_key, model=_select_model(ArithmeticExpert)),
            CentralizationExpert(api_key=api_key, model=_select_model(CentralizationExpert)),
            DeFiAnalyst(api_key=api_key, model=_select_model(DeFiAnalyst)),
            DoSExpert(api_key=api_key, model=_select_model(DoSExpert)),
            EconomicExpert(api_key=api_key, model=_select_model(EconomicExpert)),
            ErrorHandlingExpert(api_key=api_key, model=_select_model(ErrorHandlingExpert)),
            FlashLoanExpert(api_key=api_key, model=_select_model(FlashLoanExpert)),
            FrontrunningExpert(api_key=api_key, model=_select_model(FrontrunningExpert)),
            GasOptimizationExpert(api_key=api_key, model=_select_model(GasOptimizationExpert)),
            InheritanceExpert(api_key=api_key, model=_select_model(InheritanceExpert)),
            LogicExpert(api_key=api_key, model=_select_model(LogicExpert)),
            LowLevelCallsExpert(api_key=api_key, model=_select_model(LowLevelCallsExpert)),
            OracleExpert(api_key=api_key, model=_select_model(OracleExpert)),
            ReentrancyExpert(api_key=api_key, model=_select_model(ReentrancyExpert)),
            SignatureExpert(api_key=api_key, model=_select_model(SignatureExpert)),
            StorageProxyExpert(api_key=api_key, model=_select_model(StorageProxyExpert)),
            TimestampExpert(api_key=api_key, model=_select_model(TimestampExpert)),
            TokenExpert(api_key=api_key, model=_select_model(TokenExpert)),
            Critic(api_key=api_key, model=_select_model(Critic)),
        ]
        self._agent_by_type = {type(agent): agent for agent in self.agents}
        self._persona_name_to_type: Dict[str, Type] = {
            "Thief": Thief,
            "AccessControlExpert": AccessControlExpert,
            "ArithmeticExpert": ArithmeticExpert,
            "CentralizationExpert": CentralizationExpert,
            "DeFiAnalyst": DeFiAnalyst,
            "DoSExpert": DoSExpert,
            "EconomicExpert": EconomicExpert,
            "ErrorHandlingExpert": ErrorHandlingExpert,
            "FlashLoanExpert": FlashLoanExpert,
            "FrontrunningExpert": FrontrunningExpert,
            "GasOptimizationExpert": GasOptimizationExpert,
            "InheritanceExpert": InheritanceExpert,
            "LogicExpert": LogicExpert,
            "LowLevelCallsExpert": LowLevelCallsExpert,
            "OracleExpert": OracleExpert,
            "ReentrancyExpert": ReentrancyExpert,
            "SignatureExpert": SignatureExpert,
            "StorageProxyExpert": StorageProxyExpert,
            "TimestampExpert": TimestampExpert,
            "TokenExpert": TokenExpert,
            "Critic": Critic,
        }
        self.routing_analyst = RoutingAnalyst(api_key=api_key, model=model)
        # In-memory cache keyed by content hash to skip re-analysis of unchanged files.
        self._analysis_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._cache_lock = threading.Lock()
        # Toggle for enabling/disabling caching while iterating on logic.
        self.cache_enabled = cache_enabled
        # Allow disabling router for benchmarking.
        self.routing_enabled = routing_enabled

    def _select_agents(self, source_code: str, filename: str) -> List[Any]:
        """
        Routing is delegated to the RoutingAnalyst persona. We only collect lightweight
        context (pragma/imports/contracts/heuristics) to feed the router. If the router
        returns nothing or errors, we fall back to a minimal always-on set.
        """
        if not self.routing_enabled:
            logger.info("Routing disabled; using all personas for %s", filename)
            return self.agents

        code_lower = source_code.lower()

        def has_any(substrings: List[str]) -> bool:
            return any(s in code_lower for s in substrings)

        always_on: Set[Type] = {
            Thief,
            AccessControlExpert,
            ReentrancyExpert,
            LogicExpert,
            DeFiAnalyst,
            GasOptimizationExpert,
            Critic,
        }

        heuristic_hits: Set[str] = set()

        high_signal_heuristics = {
            "oracle": ["oracle", "pricefeed", "aggregatorv3", "chainlink", "feed", "price"],
            "flashloan": ["flashloan", "flash loan", "flashborrower", "flashborrowerbase", "flash mint", "flashmint"],
            "proxy": ["delegatecall", ".delegatecall", "proxy", "upgradeable", "beacon", "transparentupgradable", "implementation"],
            "amm/defi": ["swap", "pool", "liquidity", "amm", "lp", "dex", "vault", "stake", "yield"],
            "signature": ["ecrecover", "permit(", "signature", "nonces", "v,r,s", "signed"],
            "low-level": ["call{value", ".call(", "staticcall", "low level call", "assembly {", "inline assembly"],
            "timestamp": ["timestamp", "block.timestamp", "block.number", "vrf"],
            "token": ["token", "erc20", "erc777", "erc721", "erc1155", "allowance", "approve"],
            "governance/access": ["owner", "onlyowner", "accesscontrol", "role", "governance", "multisig", "timelock"],
        }

        for label, terms in high_signal_heuristics.items():
            if has_any(terms) or (label == "signature" and "sig" in filename.lower()):
                heuristic_hits.add(label)

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
        logger.info(
            "Selected agents for %s: %s (heuristics=%s)",
            filename,
            [agent.name for agent in selected],
            sorted(heuristic_hits),
        )
        logger.debug(
            "Routing %s through %d personas (fallback size=%d).",
            filename,
            len(selected),
            len(always_on),
        )
        return selected

    def _code_snippet(self, source_code: str, line_number: int, context: int = 12) -> str:
        """
        Returns a small, line-numbered snippet around the reported line for triage.
        """
        if not line_number or line_number < 1:
            return ""
        lines = source_code.splitlines()
        idx = line_number - 1
        if idx >= len(lines):
            return ""
        start = max(0, idx - context)
        end = min(len(lines), idx + context + 1)
        snippet_lines = [f"{i + 1}: {lines[i][:400]}" for i in range(start, end)]
        return "\n".join(snippet_lines)

    def _content_hash(self, source_code: str) -> str:
        return hashlib.sha256(source_code.encode("utf-8")).hexdigest()

    def analyze_file(
        self,
        source_code: str,
        filename: str,
        docs: str | None = None,
        additional_links: List[str] | None = None,
        additional_docs: str | None = None,
        qa_responses: List | None = None,
        persona_outputs: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Broadcasts the file to all agents in the Swarm.
        """
        cache_key = self._content_hash(source_code)
        if self.cache_enabled:
            with self._cache_lock:
                cached = self._analysis_cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache hit for %s (key=%s)", filename, cache_key[:8])
                return copy.deepcopy(cached)

        findings = []
        selected_agents = self._select_agents(source_code, filename)

        def _run_agent(agent):
            try:
                return agent, agent.hunt(
                    source_code,
                    filename,
                    docs=docs,
                    additional_links=additional_links,
                    additional_docs=additional_docs,
                    qa_responses=qa_responses,
                )
            except Exception:
                logger.exception("Agent %s failed during hunt on %s", agent.name, filename)
                return agent, {}

        max_workers = len(selected_agents) or 1
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            for agent, analysis in executor.map(_run_agent, selected_agents):
                if persona_outputs is not None:
                    persona_outputs.append({"persona": agent.name, "raw": analysis})
                if analysis.get("found_vulnerability"):
                    snippet = self._code_snippet(source_code, analysis.get('line_number'))
                    description = analysis.get('kill_chain', 'No details')
                    if snippet:
                        description = f"{description}\n\nCode snippet:\n{snippet}"
                    findings.append({
                        "title": analysis.get('title', 'Unknown Vuln'),
                        "description": description,
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
                    snippet = self._code_snippet(source_code, analysis.get('line_number'))
                    if snippet:
                        description = f"{description}\n\nCode snippet:\n{snippet}"
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

        if self.cache_enabled:
            with self._cache_lock:
                self._analysis_cache[cache_key] = copy.deepcopy(findings)

        return findings
