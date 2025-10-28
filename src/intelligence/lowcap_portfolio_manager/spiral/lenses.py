from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List
import statistics


@dataclass
class LensScores:
    S_btcusd: float
    S_rotation: float
    S_port_btc: float
    S_port_alt: float


def _z(values: List[float], value: float) -> float:
    if len(values) < 5:
        return 0.0
    mean = statistics.fmean(values)
    sd = statistics.pstdev(values) or 1.0
    return (value - mean) / sd


def compute_lens_scores(streams: Dict[str, float]) -> LensScores:
    """Minimal scoring per §3.1: weighted mix of components prepared upstream.
    Expect keys: slope, curvature, delta, level for each lens stream.
    """
    def score(prefix: str) -> float:
        # 0.5×Slope + 0.3×Curvature + 0.2×Δ + 0.1×Level (clamped in caller if needed)
        return (
            0.5 * streams.get(f"{prefix}_slope", 0.0)
            + 0.3 * streams.get(f"{prefix}_curv", 0.0)
            + 0.2 * streams.get(f"{prefix}_delta", 0.0)
            + 0.1 * streams.get(f"{prefix}_level", 0.0)
        )

    return LensScores(
        S_btcusd=score("btc"),
        S_rotation=score("rotation"),
        S_port_btc=score("port_btc"),
        S_port_alt=score("port_alt"),
    )


