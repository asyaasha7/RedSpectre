"""
Lightweight built-in reference docs passed to personas to reduce false positives and
provide shared best practices without requiring external input.
Keep concise to avoid prompt bloat.
"""

DEFAULT_DOCS = """
Persona Reference Notes:
- Reentrancy: CEI (checks-effects-interactions) with nonReentrant is usually safe. Pull payments safer than push.
- Arithmetic: Solidity >=0.8 reverts on overflow/underflow unless inside unchecked. SafeMath adds guards for <0.8.
- Access Control: onlyOwner/roles/timelocks/multisigs mitigate centralization; do not flag when properly used.
- Proxies/Upgrades: transparent/beacon proxies should restrict admin/implementation changes; storage layouts must align.
- Tokens: ERC20 transfer/transferFrom may return false; some tokens are fee-on-transfer or rebasing—handle received amount.
- External Calls: low-level call must check success and bubble errors; avoid delegatecall to untrusted addresses.
- Oracles: check freshness (updatedAt) and stale/zero values; consider price deviation bounds.
- Timestamp/Block: avoid using block.timestamp/block.number for critical randomness; allow small drift tolerances.
- Validation: guard zero address, bounds (min/max), array length alignment, and zero amounts where unsafe.
- Gas: avoid SLOAD/SSTORE in tight loops, pack variables, cache storage reads, and avoid redundant checks in pure/view paths.
"""
