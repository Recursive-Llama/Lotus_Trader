import copy

import pytest

from src.intelligence.lowcap_portfolio_manager.pm.overrides import (
    apply_pattern_strength_overrides,
    apply_pattern_execution_overrides,
)


class FakeQuery:
    """Minimal Supabase query builder stub."""

    def __init__(self, rows):
        self._rows = rows

    # All builder methods return self so call chaining works.
    def select(self, *_, **__):
        return self

    def eq(self, *_, **__):
        return self

    def in_(self, *_, **__):
        return self

    def filter(self, *_, **__):
        return self

    def limit(self, *_, **__):
        return self

    def execute(self):
        return type("Resp", (), {"data": self._rows})


class FakeSupabase:
    def __init__(self, table_rows):
        self._table_rows = table_rows

    def table(self, name):
        return FakeQuery(self._table_rows.get(name, []))


def _make_sb(rows):
    return FakeSupabase({"pm_overrides": rows})


def test_strength_override_scales_position_size():
    rows = [
        {
            "pattern_key": "pm.uptrend.S1.entry",
            "action_category": "entry",
            "scope_subset": {"chain": "solana"},
            "multiplier": 2.0,
            "confidence_score": 1.0,
        }
    ]
    sb = _make_sb(rows)

    base = {"A_value": 0.5, "E_value": 0.4, "position_size_frac": 0.33}
    adjusted = apply_pattern_strength_overrides(
        pattern_key="pm.uptrend.S1.entry",
        action_category="entry",
        scope={"chain": "solana"},
        base_levers=base,
        sb_client=sb,
    )

    assert adjusted["position_size_frac"] == pytest.approx(0.66)


def test_strength_override_no_match_returns_base():
    sb = _make_sb([])
    base = {"A_value": 0.4, "E_value": 0.2, "position_size_frac": 0.25}
    adjusted = apply_pattern_strength_overrides(
        pattern_key="pm.uptrend.S1.entry",
        action_category="entry",
        scope={"chain": "solana"},
        base_levers=base,
        sb_client=sb,
    )
    assert adjusted == base


def test_execution_override_tightens_ts_min():
    rows = [
        {
            "pattern_key": "pm.uptrend.S1.entry",
            "action_category": "tuning_ts_min",
            "scope_subset": {"curator": "tuning_harness"},
            "multiplier": 1.2,
            "confidence_score": 1.0,
        }
    ]
    sb = _make_sb(rows)
    controls = {"ts_min": 60.0, "halo_mult": 1.0}

    adjusted = apply_pattern_execution_overrides(
        pattern_key="pm.uptrend.S1.entry",
        action_category="tuning",
        scope={"curator": "tuning_harness"},
        plan_controls=copy.deepcopy(controls),
        sb_client=sb,
    )

    assert adjusted["ts_min"] == pytest.approx(72.0)
    assert adjusted["halo_mult"] == 1.0  # untouched


def test_execution_override_loosen_s3_dx():
    rows = [
        {
            "pattern_key": "pm.uptrend.S3.add",
            "action_category": "tuning_dx_min",
            "scope_subset": {"curator": "tuning_harness"},
            "multiplier": 0.8,
            "confidence_score": 1.0,
        }
    ]
    sb = _make_sb(rows)
    controls = {"ts_min": 60.0, "dx_min": 60.0}

    adjusted = apply_pattern_execution_overrides(
        pattern_key="pm.uptrend.S3.add",
        action_category="tuning",
        scope={"curator": "tuning_harness"},
        plan_controls=copy.deepcopy(controls),
        sb_client=sb,
    )

    assert adjusted["dx_min"] == pytest.approx(48.0)
    assert adjusted["ts_min"] == controls["ts_min"]  # unaffected without ts override


