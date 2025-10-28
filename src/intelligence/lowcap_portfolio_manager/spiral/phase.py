from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


def hysteresis_label(prev: str, score: float) -> str:
    # Simple hysteresis: widen thresholds by ±0.2 depending on direction (prev)
    # For brevity, implement only a stabilizer around Recover/Good boundary
    if prev == "Recover" and score >= 0.20:
        return "Good"
    if prev == "Good" and score < 0.20:
        return "Recover"
    return label_from_score(score)


@dataclass
class PhaseScores:
    macro: float
    meso: float
    micro: float


def compute_phase_scores(lens: dict) -> PhaseScores:
    """Weighting per §3.2 (defaults)."""
    macro = 0.55 * lens.get("S_btcusd", 0.0) + 0.35 * lens.get("S_rotation", 0.0) + 0.05 * lens.get("S_port_btc", 0.0) + 0.05 * lens.get("S_port_alt", 0.0)
    meso = 0.50 * lens.get("S_port_btc", 0.0) + 0.30 * lens.get("S_port_alt", 0.0) + 0.15 * lens.get("S_rotation", 0.0) + 0.05 * lens.get("S_btcusd", 0.0)
    micro = 0.70 * lens.get("S_port_btc", 0.0) + 0.30 * lens.get("S_port_alt", 0.0)
    return PhaseScores(macro=macro, meso=meso, micro=micro)


def label_from_score(score: float) -> str:
    if score >= 1.20:
        return "Euphoria"
    if score >= 0.40:
        return "Good"
    if score >= -0.20:
        return "Recover"
    if score >= -0.90:
        return "Dip"
    if score >= -1.30:
        return "Double-Dip"
    return "Oh-Shit"


def band_distance(score: float) -> float:
    # Distance to nearest band threshold (approx for confidence)
    bands = [1.20, 0.40, -0.20, -0.90, -1.30]
    return min(abs(score - b) for b in bands)


def apply_skip_rules(prev: str, next_label: str) -> str:
    # Enforce plan rule: Recover cannot jump to Double‑Dip directly
    if prev == "Recover" and next_label == "Double-Dip":
        return "Dip"
    return next_label


