from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple


DEFAULT_MASK_DEFS: List[Tuple[str, ...]] = [
    ("mcap_bucket",),
    ("mcap_bucket", "timeframe"),
    ("mcap_bucket", "timeframe", "macro_phase"),
]

DEFAULT_DIM_WEIGHTS: Dict[str, float] = {
    "curator": 1.0,
    "chain": 1.0,
    "mcap_bucket": 1.0,
    "vol_bucket": 1.0,
    "age_bucket": 1.0,
    "intent": 1.0,
    "mcap_vol_ratio_bucket": 1.0,
    "market_family": 1.0,
    "timeframe": 1.0,
    "A_mode": 1.0,
    "E_mode": 1.0,
    "macro_phase": 1.0,
    "meso_phase": 1.0,
    "micro_phase": 1.0,
    "bucket_leader": 1.0,
    "bucket_rank_position": 1.0,
}


@dataclass(frozen=True)
class ExposureMask:
    dims: Tuple[str, ...]
    weight: float


@dataclass
class ExposureConfig:
    masks: List[ExposureMask]
    dim_weights: Dict[str, float]
    alpha: float
    scope_weight: float
    pattern_weight: float
    max_concentration: float

    @classmethod
    def from_pm_config(cls, pm_config: Dict[str, Any]) -> ExposureConfig:
        cfg = (pm_config or {}).get("exposure_skew", {})
        mask_defs = cfg.get("mask_defs") or DEFAULT_MASK_DEFS
        dim_weights = dict(DEFAULT_DIM_WEIGHTS)
        dim_weights.update(cfg.get("scope_dim_weights", {}))
        alpha = float(cfg.get("alpha", 0.5))
        scope_weight = float(cfg.get("scope_weight", 1.0))
        pattern_weight = float(cfg.get("pattern_weight", 0.5))
        max_concentration = float(cfg.get("max_concentration_pct", 100.0))

        total_weight = sum(dim_weights.values()) or len(dim_weights) or 1.0
        masks: List[ExposureMask] = []
        for mask_def in mask_defs:
            dims = tuple(mask_def)
            numerator = sum(dim_weights.get(dim, 1.0) for dim in dims)
            ratio = max(numerator / total_weight, 1e-6)
            weight = math.pow(ratio, alpha)
            masks.append(ExposureMask(dims=dims, weight=weight))
        return cls(
            masks=masks,
            dim_weights=dim_weights,
            alpha=alpha,
            scope_weight=scope_weight,
            pattern_weight=pattern_weight,
            max_concentration=max_concentration,
        )


class ExposureLookup:
    def __init__(
        self,
        config: ExposureConfig,
        scope_exposure: Dict[Tuple[Tuple[str, str], ...], float],
        pk_scope_exposure: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], float],
        total_exposure: float,
    ) -> None:
        self.config = config
        self.scope_exposure = scope_exposure
        self.pk_scope_exposure = pk_scope_exposure
        self.total_exposure = total_exposure

    @classmethod
    def build(
        cls,
        positions: Iterable[Dict[str, Any]],
        config: ExposureConfig,
        regime_defaults: Optional[Dict[str, Optional[str]]] = None,
    ) -> ExposureLookup:
        scope_exposure: Dict[Tuple[Tuple[str, str], ...], float] = {}
        pk_scope_exposure: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], float] = {}
        total_exposure = 0.0

        regime_defaults = regime_defaults or {}

        for pos in positions:
            exposure_pct = float(pos.get("total_allocation_pct") or 0.0)
            if exposure_pct <= 0:
                continue

            scope = cls._scope_from_position(pos, regime_defaults)
            mask_keys = cls._mask_keys_for_scope(scope, config)
            if not mask_keys:
                continue

            total_exposure += exposure_pct
            pattern_key = cls._pattern_key_for_position(pos)

            for mask, mask_key in mask_keys:
                weighted = mask.weight * exposure_pct
                scope_exposure[mask_key] = scope_exposure.get(mask_key, 0.0) + weighted
                if pattern_key:
                    pk_key = (pattern_key, mask_key)
                    pk_scope_exposure[pk_key] = pk_scope_exposure.get(pk_key, 0.0) + weighted

        return cls(config, scope_exposure, pk_scope_exposure, total_exposure)

    def lookup(self, pattern_key: Optional[str], scope: Dict[str, Any]) -> float:
        mask_keys = self._mask_keys_for_scope(scope, self.config)
        if not mask_keys or self.total_exposure <= 0:
            return 1.33

        conc_scope = sum(self.scope_exposure.get(mask_key, 0.0) for _, mask_key in mask_keys)
        conc_pattern = 0.0
        if pattern_key:
            for _, mask_key in mask_keys:
                conc_pattern += self.pk_scope_exposure.get((pattern_key, mask_key), 0.0)

        conc_total = (self.config.scope_weight * conc_scope) + (self.config.pattern_weight * conc_pattern)
        denom = max(self.total_exposure, 1e-6)
        if self.config.max_concentration > 0:
            denom = min(denom, self.config.max_concentration)
        conc_norm = max(0.0, min(1.0, conc_total / denom))
        skew = 1.33 - conc_norm
        return max(0.33, min(1.33, skew))

    @staticmethod
    def _scope_from_position(
        position: Dict[str, Any],
        regime_defaults: Dict[str, Optional[str]],
    ) -> Dict[str, Any]:
        scope: Dict[str, Any] = {}
        entry = position.get("entry_context") or {}

        def set_value(key: str, value: Optional[Any]) -> None:
            if value is None:
                return
            if isinstance(value, str) and value.strip() == "":
                return
            scope[key] = value

        set_value("curator", entry.get("curator") or entry.get("curator_id"))
        set_value("chain", entry.get("chain") or position.get("token_chain"))
        set_value("mcap_bucket", entry.get("mcap_bucket"))
        set_value("vol_bucket", entry.get("vol_bucket"))
        set_value("age_bucket", entry.get("age_bucket"))
        set_value("intent", entry.get("intent"))
        set_value("mcap_vol_ratio_bucket", entry.get("mcap_vol_ratio_bucket"))
        set_value("timeframe", position.get("timeframe"))
        set_value("market_family", entry.get("market_family"))
        set_value("A_mode", entry.get("A_mode"))
        set_value("E_mode", entry.get("E_mode"))

        set_value("macro_phase", regime_defaults.get("macro_phase"))
        set_value("meso_phase", regime_defaults.get("meso_phase"))
        set_value("micro_phase", regime_defaults.get("micro_phase"))
        set_value("bucket_leader", entry.get("bucket_leader"))
        set_value("bucket_rank_position", entry.get("bucket_rank_position"))

        return scope

    @staticmethod
    def _pattern_key_for_position(position: Dict[str, Any]) -> Optional[str]:
        features = position.get("features") or {}
        if isinstance(features, dict):
            pk = features.get("pattern_key") or features.get("current_pattern_key")
            if pk:
                return str(pk)
        entry = position.get("entry_context") or {}
        pk = entry.get("pattern_key")
        return str(pk) if pk else None

    @staticmethod
    def _mask_keys_for_scope(
        scope: Dict[str, Any],
        config: ExposureConfig,
    ) -> List[Tuple[ExposureMask, Tuple[Tuple[str, str], ...]]]:
        matches: List[Tuple[ExposureMask, Tuple[Tuple[str, str], ...]]] = []
        for mask in config.masks:
            mask_key = ExposureLookup._build_mask_key(scope, mask.dims)
            if mask_key:
                matches.append((mask, mask_key))
        return matches

    @staticmethod
    def _build_mask_key(scope: Dict[str, Any], dims: Tuple[str, ...]) -> Optional[Tuple[Tuple[str, str], ...]]:
        key: List[Tuple[str, str]] = []
        for dim in dims:
            value = scope.get(dim)
            if value is None:
                return None
            if isinstance(value, str) and value.strip() == "":
                return None
            key.append((dim, str(value)))
        return tuple(key) if key else None

