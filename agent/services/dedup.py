from typing import List, Dict, Tuple, Set, TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent.services.auditor import VulnerabilityFinding
else:
    VulnerabilityFinding = object  # runtime placeholder to avoid circular import


SeverityRank = Dict[str, int]


def _aggregate(
    findings: List[VulnerabilityFinding],
) -> Tuple[Dict[Tuple[str, str], Dict[str, Any]], SeverityRank]:
    severity_rank: SeverityRank = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1, "Informational": 0}
    unique: Dict[Tuple[str, str], Dict[str, Any]] = {}

    for finding in findings:
        for path in finding.file_paths:
            key = (finding.title.strip().lower(), path)
            entry = unique.get(key, None)
            if not entry:
                unique[key] = {
                    "best": finding,
                    "support": 1,
                    "severities": {finding.severity},
                    "file_paths": set(finding.file_paths),
                }
                continue

            entry["support"] += 1
            entry["severities"].add(finding.severity)
            entry["file_paths"].update(finding.file_paths)

            # Prefer the higher-severity finding as the canonical representative
            if severity_rank.get(finding.severity, 0) > severity_rank.get(entry["best"].severity, 0):
                entry["best"] = finding
    return unique, severity_rank


def deduplicate_findings(findings: List[VulnerabilityFinding]) -> List[VulnerabilityFinding]:
    """
    Keep one finding per (title, file_path) pair, preferring the highest severity.
    If duplicates carry different file path lists, merge them.
    """
    unique, _ = _aggregate(findings)
    deduped: List[VulnerabilityFinding] = []

    for entry in unique.values():
        best = entry["best"]
        best.file_paths = sorted(entry["file_paths"])
        deduped.append(best)

    return deduped


def select_top_findings(findings: List[VulnerabilityFinding], limit: int = 20) -> List[VulnerabilityFinding]:
    """
    De-duplicate and rank findings by:
    1) Persona consensus (how many agents independently reported the same issue)
    2) Severity (Critical > High > Medium > Low > Informational)
    3) Breadth of impact (issues spanning more files rank higher)
    Adds a brief consensus note to the description when multiple agents agree.
    """
    unique, severity_rank = _aggregate(findings)
    scored: List[Tuple[Tuple[int, int, int], VulnerabilityFinding]] = []

    for entry in unique.values():
        best = entry["best"]
        support = entry["support"]
        severities = sorted(entry["severities"], key=lambda s: severity_rank.get(s, 0), reverse=True)

        best.file_paths = sorted(entry["file_paths"])
        if support > 1:
            consensus_note = (
                f"\n\nConsensus: {support} personas independently reported this issue "
                f"(severities seen: {', '.join(severities)})."
            )
            if "Consensus:" not in best.description:
                best.description = f"{best.description}{consensus_note}"

        confidence = getattr(best, "confidence_score", None)
        if confidence is None and isinstance(best, dict):
            confidence = best.get("confidence_score")
        if confidence is None:
            confidence = 50
        try:
            confidence = int(confidence)
        except Exception:
            confidence = 50

        false_positive_risk = getattr(best, "false_positive_risk", None)
        if false_positive_risk is None and isinstance(best, dict):
            false_positive_risk = best.get("false_positive_risk")
        if false_positive_risk is None:
            false_positive_risk = 50
        try:
            false_positive_risk = int(false_positive_risk)
        except Exception:
            false_positive_risk = 50

        # Rank by consensus, severity, confidence, negative of false-positive risk, then breadth.
        score = (
            support,
            severity_rank.get(best.severity, 0),
            confidence,
            -false_positive_risk,
            len(best.file_paths),
        )
        scored.append((score, best))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [finding for _, finding in scored[:limit]]
