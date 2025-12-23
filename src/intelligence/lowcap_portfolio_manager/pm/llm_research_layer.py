"""
LLM Research Layer – Jim Simons Mode

Core principle:
    The math is the brainstem.
    The LLM is a research assistant that:
        - Reads what the math already knows
        - Names latent factors
        - Proposes re-groupings / hypotheses
        - NEVER overrides statistics
        - NEVER decides trades

This file defines a narrow, testable interface for LLM-powered research
on top of the braiding + learning system.

Levels:

    L1 – Edge Landscape Commentary
         "Tell me what changed in the last X days."

    L2 – Semantic Factor Extraction
         "Name latent factors (narratives / styles) that might explain clusters."

    L3 – Family Core Optimization
         "Suggest alternative family cores that should increase out-of-sample robustness."

    L4 – Semantic Pattern Compression
         "Compress many concrete braids into a few conceptual patterns/factors."

    L5 – Hypothesis Auto-Generation
         "Propose strictly testable hypotheses, never conclusions."

All LLM outputs are stored as hypotheses in `llm_learning` and must be
validated by the math layer (edge stats, baselines, significance tests).
"""

from __future__ import annotations

import logging
import json
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional, Literal
from datetime import datetime, timezone

from llm_integration.openrouter_client import OpenRouterClient
from llm_integration.prompt_manager import PromptManager

logger = logging.getLogger(__name__)

ModuleName = Literal["pm", "dm"]

# --------------------------------------------------------------------------
# Configuration + Data Contracts
# --------------------------------------------------------------------------

DEFAULT_ENABLEMENT = {
    "level_1_commentary": True,          # day 1
    "level_2_semantic_factors": True,    # day 1
    "level_3_family_optimization": False,
    "level_4_semantic_compression": False,
    "level_5_hypothesis_generation": False,
}


@dataclass
class BraidStats:
    """Minimal stats the LLM is allowed to see for a braid/pattern."""
    pattern_key: str
    family_id: str
    module: ModuleName
    n: int
    avg_rr: float
    variance: float
    win_rate: float
    rr_baseline: float
    edge_raw: float
    time_efficiency: Optional[float] = None
    field_coherence: Optional[float] = None
    recurrence_score: Optional[float] = None
    emergence_score: Optional[float] = None
    # v5 fields
    action_category: Optional[str] = None
    scope_dims: Optional[List[str]] = None
    scope_values: Optional[Dict[str, Any]] = None


@dataclass
class LessonStats:
    """Minimal stats for a lesson (active rule) the LLM can see."""
    lesson_id: str
    module: ModuleName
    family_id: str
    n: int
    avg_rr: float
    edge_raw: float
    recurrence_score: Optional[float] = None
    # v5 fields
    pattern_key: Optional[str] = None
    action_category: Optional[str] = None
    scope_dims: Optional[List[str]] = None
    scope_values: Optional[Dict[str, Any]] = None
    lesson_strength: Optional[float] = None
    decay_halflife_hours: Optional[int] = None
    latent_factor_id: Optional[str] = None


@dataclass
class EdgeLandscapeSnapshot:
    """
    Snapshot for L1 commentary:
    'Tell me how the edge landscape has shifted recently.'
    """
    module: ModuleName
    time_window_days: int
    top_braids: List[BraidStats]
    top_lessons: List[LessonStats]
    timestamp: str


@dataclass
class SemanticFactorTag:
    """
    Output for L2 semantic factor extraction.
    Stored as a hypothesis; math does correlation later.
    """
    name: str
    confidence: float
    reasoning: str
    applies_to_positions: List[str]
    source_fields: List[str]


@dataclass
class FamilyOptimizationProposal:
    """
    Output for L3: "maybe the family core should look like THIS instead."
    """
    current_family_core: str
    proposed_family_core: str
    reasoning: str
    affected_pattern_keys: List[str]


@dataclass
class SemanticPatternProposal:
    """
    Output for L4: conceptual patterns that compress multiple braids.
    """
    pattern_name: str
    components: List[str]  # pattern_keys
    conceptual_summary: str
    proposed_trigger: Dict[str, Any]
    family_id: str


@dataclass
class HypothesisProposal:
    """
    Output for L5: strictly testable hypotheses.
    """
    type: Literal["interaction_pattern", "bucket_boundary", "semantic_dimension", "other"]
    proposal: str
    reasoning: str
    test_query: str  # SQL-ish or pattern-query-ish; math layer interprets


# --------------------------------------------------------------------------
# LLM Research Layer – Jim Simons Style
# --------------------------------------------------------------------------


class LLMResearchLayer:
    """
    Jim-Simons-first LLM layer.

    - It ONLY consumes already-computed statistics.
    - It ONLY produces hypotheses, factors, commentary.
    - All proposals are written to `llm_learning` as 'hypothesis' / 'report'.
    - The math / backtest layer ALWAYS judges them.

    This class should stay thin:
        - Build small, focused prompts.
        - Parse strictly defined JSON schemas.
        - No trading logic lives here.
    """

    def __init__(
        self,
        sb_client,
        llm_client: Optional[OpenRouterClient] = None,
        enablement: Optional[Dict[str, bool]] = None,
    ):
        self.sb = sb_client
        self.llm = llm_client or OpenRouterClient()
        self.prompt_manager = PromptManager()
        self.enablement = {**DEFAULT_ENABLEMENT, **(enablement or {})}

        logger.info(f"LLMResearchLayer initialized with enablement={self.enablement}")

    # ------------------------------------------------------------------
    # Public orchestration
    # ------------------------------------------------------------------

    async def process(
        self,
        module: ModuleName = "pm",
        position_closed_strand: Optional[Dict[str, Any]] = None,
        token_data: Optional[Dict[str, Any]] = None,
        curator_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Main entrypoint for the LLM research layer.

        Called e.g. when:
          - a position closes, or
          - a periodic cron tick runs.

        It should be CHEAP: if a level is disabled, we do nothing.
        """
        results: Dict[str, Any] = {
            "level_1": None,
            "level_2": None,
            "level_3": None,
            "level_4": None,
            "level_5": None,
        }

        # L1 – commentary on edge landscape
        if self.enablement.get("level_1_commentary", False):
            try:
                results["level_1"] = await self._run_level_1_commentary(module)
            except Exception as e:
                logger.error(f"L1 commentary failed: {e}", exc_info=True)

        # L2 – semantic factors from token / curator data
        if self.enablement.get("level_2_semantic_factors", False) and token_data:
            try:
                position_id = position_closed_strand.get("position_id") if position_closed_strand else None
                results["level_2"] = await self._run_level_2_semantic_factors(
                    module=module,
                    position_id=position_id,
                    token_data=token_data,
                    curator_message=curator_message,
                )
            except Exception as e:
                logger.error(f"L2 semantic factors failed: {e}", exc_info=True)

        # L5 – hypotheses (we often want these earlier than 3/4)
        if self.enablement.get("level_5_hypothesis_generation", False):
            try:
                results["level_5"] = await self._run_level_5_hypotheses(module)
            except Exception as e:
                logger.error(f"L5 hypothesis generation failed: {e}", exc_info=True)

        # L3 – family optimization (heavier, run less often)
        if self.enablement.get("level_3_family_optimization", False):
            try:
                results["level_3"] = await self._run_level_3_family_optimization(module)
            except Exception as e:
                logger.error(f"L3 family optimization failed: {e}", exc_info=True)

        # L4 – semantic compression (heavier, run rarely)
        if self.enablement.get("level_4_semantic_compression", False):
            try:
                results["level_4"] = await self._run_level_4_semantic_compression(module)
            except Exception as e:
                logger.error(f"L4 semantic compression failed: {e}", exc_info=True)

        return results

    # ------------------------------------------------------------------
    # Level 1 – Edge Landscape Commentary
    # ------------------------------------------------------------------

    async def _run_level_1_commentary(self, module: ModuleName, time_window_days: int = 30) -> Dict[str, Any]:
        """
        L1: Given braid + lesson stats, describe how the edge landscape shifted.

        Input:   EdgeLandscapeSnapshot (built from DB).
        Output:  Structured natural-language report stored in `llm_learning`.
        """
        snapshot = await self._build_edge_landscape_snapshot(module, time_window_days)
        if not snapshot.top_braids and not snapshot.top_lessons:
            logger.debug("L1: no data for commentary")
            return {}

        prompt = self._build_l1_prompt(snapshot)
        params = self.prompt_manager.get_parameters("l1_edge_landscape_commentary")
        raw = self.llm.generate_completion(
            prompt=prompt,
            temperature=params.get("temperature", 0.4),
            max_tokens=params.get("max_tokens", 1600),
        )
        content = raw.get("content", "").strip()

        report_record = {
            "kind": "report",
            "level": 1,
            "module": module,
            "status": "active",
            "content": {
                "type": "edge_landscape_commentary",
                "snapshot": {
                    "time_window_days": time_window_days,
                    "top_braids": [asdict(b) for b in snapshot.top_braids],
                    "top_lessons": [asdict(l) for l in snapshot.top_lessons],
                },
                "summary": content,
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        self.sb.table("llm_learning").insert(report_record).execute()
        return report_record

    async def _build_edge_landscape_snapshot(
        self,
        module: ModuleName,
        time_window_days: int,
    ) -> EdgeLandscapeSnapshot:
        """
        Pull top braids + lessons with their stats from DB and wrap in typed object.

        This is where we constrain the LLM's view:
          - Only a handful of numeric fields.
          - No raw trades.
          - No direct price series.

        v5: Reads from learning_lessons (v5 only).
        """
        from datetime import timedelta
        
        # Calculate cutoff time for time window filtering
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=time_window_days)
        
        top_braids: List[BraidStats] = []
        
        stats_res = (
            self.sb.table("learning_lessons")
            .select("pattern_key,action_category,scope_subset,scope_values,n,stats,updated_at")
            .eq("module", module)
            .eq("status", "active")
            .gte("updated_at", cutoff_time.isoformat())
            .limit(100)  # Fetch more, then sort by edge_raw in Python
            .execute()
        )
        stats_rows = stats_res.data or []
        
        if stats_rows:
            # Sort by edge_raw (from stats JSONB) descending
            stats_rows.sort(
                key=lambda r: float((r.get("stats") or {}).get("edge_raw", 0.0)),
                reverse=True
            )
            
            # Group by pattern_key to get best performing scope subset per pattern
            pattern_map: Dict[str, Dict[str, Any]] = {}
            for row in stats_rows:
                pattern_key = row.get("pattern_key", "")
                if not pattern_key:
                    continue
                
                # Use pattern with highest edge_raw (already sorted)
                if pattern_key not in pattern_map:
                    stats = row.get("stats") or {}
                    # Use scope_subset if available, fallback to scope_values (compat column)
                    scope_values = row.get("scope_subset") or row.get("scope_values") or {}
                    
                    # Extract scope dims from scope JSONB keys (instead of bitmask)
                    scope_dims = list(scope_values.keys()) if isinstance(scope_values, dict) else []
                    
                    # Derive family_id from pattern_key (format: "module.family.state.motif")
                    parts = pattern_key.split(".")
                    family_id = f"{parts[0]}.{parts[1]}" if len(parts) >= 2 else "unknown"
                    
                    pattern_map[pattern_key] = {
                        "pattern_key": pattern_key,
                        "family_id": family_id,
                        "module": module,
                        "action_category": row.get("action_category"),
                        "scope_dims": scope_dims,
                        "scope_values": scope_values,
                        "n": int(row.get("n", 0)),
                        "stats": stats,
                    }
            
            # Convert to BraidStats
            for pattern_data in list(pattern_map.values())[:30]:
                stats = pattern_data["stats"]
                try:
                    top_braids.append(
                        BraidStats(
                            pattern_key=pattern_data["pattern_key"],
                            family_id=pattern_data["family_id"],
                            module=module,
                            n=pattern_data["n"],
                            avg_rr=float(stats.get("avg_rr", 0.0)),
                            variance=float(stats.get("variance", 0.0)),
                            win_rate=float(stats.get("win_rate", 0.0)),
                            rr_baseline=0.0,  # Not in pattern_scope_stats, would need separate lookup
                            edge_raw=float(stats.get("edge_raw", 0.0)),
                            time_efficiency=stats.get("time_efficiency"),
                            field_coherence=stats.get("field_coherence"),
                            recurrence_score=stats.get("recurrence_score"),
                            emergence_score=stats.get("emergence_score"),
                            action_category=pattern_data["action_category"],
                            scope_dims=pattern_data["scope_dims"],
                            scope_values=pattern_data["scope_values"],
                        )
                    )
                except Exception as e:
                    logger.warning(f"Skipping learning_lessons row in snapshot: {e}")

        # Query lessons with v5 fields
        lessons_res = (
            self.sb.table("learning_lessons")
            .select("id,module,stats,pattern_key,action_category,scope_subset,scope_values,decay_halflife_hours,latent_factor_id")
            .eq("module", module)
            .eq("status", "active")
            .limit(20)
            .execute()
        )
        lessons = lessons_res.data or []

        top_lessons: List[LessonStats] = []
        for row in lessons:
            stats = row.get("stats") or {}
            try:
                # Derive family_id from pattern_key
                pattern_key = row.get("pattern_key", "")
                parts = pattern_key.split(".") if pattern_key else []
                family_id = f"{parts[0]}.{parts[1]}" if len(parts) >= 2 else "unknown"
                
                # Derive scope_dims from scope_subset keys
                scope_subset = row.get("scope_subset") or row.get("scope_values") or {}
                scope_dims = list(scope_subset.keys()) if isinstance(scope_subset, dict) else []
                scope_values = scope_subset if isinstance(scope_subset, dict) else (row.get("scope_values") or {})
                
                top_lessons.append(
                    LessonStats(
                        lesson_id=str(row.get("id")),
                        module=row.get("module", module),
                        family_id=family_id,
                        n=int(stats.get("n", 0)),
                        avg_rr=float(stats.get("avg_rr", 0.0)),
                        edge_raw=float(stats.get("edge_raw", 0.0)),
                        recurrence_score=stats.get("recurrence_score"),
                        pattern_key=pattern_key,
                        action_category=row.get("action_category"),
                        scope_dims=scope_dims,
                        scope_values=scope_values,
                        lesson_strength=stats.get("lesson_strength"),  # May be in stats JSONB
                        decay_halflife_hours=row.get("decay_halflife_hours"),
                        latent_factor_id=row.get("latent_factor_id"),
                    )
                )
            except Exception as e:
                logger.warning(f"Skipping lesson row in snapshot: {e}")

        return EdgeLandscapeSnapshot(
            module=module,
            time_window_days=time_window_days,
            top_braids=top_braids,
            top_lessons=top_lessons,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def _build_l1_prompt(self, snapshot: EdgeLandscapeSnapshot) -> str:
        """
        Build L1 prompt using PromptManager template.
        """
        def format_b(b: BraidStats) -> str:
            action_str = f" | action={b.action_category}" if b.action_category else ""
            scope_str = ""
            if b.scope_dims and b.scope_values:
                scope_parts = [f"{dim}={b.scope_values.get(dim, '?')}" for dim in b.scope_dims[:3]]
                scope_str = f" | scope={{{', '.join(scope_parts)}}}" if scope_parts else ""
            return (
                f"- {b.pattern_key} | family={b.family_id}{action_str}{scope_str} | "
                f"n={b.n}, avg_rr={b.avg_rr:.2f}, baseline={b.rr_baseline:.2f}, "
                f"edge={b.edge_raw:.2f}, var={b.variance:.2f}, win={b.win_rate:.2f}, "
                f"time_eff={b.time_efficiency}, φ={b.field_coherence}, ρ={b.recurrence_score}, "
                f"⚘={b.emergence_score}"
            )

        def format_l(l: LessonStats) -> str:
            action_str = f" | action={l.action_category}" if l.action_category else ""
            pattern_str = f" | pattern={l.pattern_key}" if l.pattern_key else ""
            return (
                f"- lesson={l.lesson_id} | family={l.family_id}{action_str}{pattern_str} | "
                f"n={l.n}, avg_rr={l.avg_rr:.2f}, edge={l.edge_raw:.2f}, ρ={l.recurrence_score}"
            )

        braids_block = "\n".join(format_b(b) for b in snapshot.top_braids) or "None."
        lessons_block = "\n".join(format_l(l) for l in snapshot.top_lessons) or "None."

        return self.prompt_manager.format_prompt(
            "l1_edge_landscape_commentary",
            {
                "module": snapshot.module,
                "time_window_days": snapshot.time_window_days,
                "braids_block": braids_block,
                "lessons_block": lessons_block,
            }
        )

    # ------------------------------------------------------------------
    # Level 2 – Semantic Factor Extraction
    # ------------------------------------------------------------------

    async def _run_level_2_semantic_factors(
        self,
        module: ModuleName,
        position_id: Optional[str],
        token_data: Dict[str, Any],
        curator_message: Optional[str],
    ) -> List[Dict[str, Any]]:
        """
        L2: Extract semantic narrative/style factors from token + curator.

        Output is a list of SemanticFactorTag, each stored as a row in `llm_learning`
        with kind='semantic_factor', status='hypothesis'.
        """
        prompt = self._build_l2_prompt(token_data, curator_message)
        params = self.prompt_manager.get_parameters("l2_semantic_factor_extraction")
        raw = self.llm.generate_completion(
            prompt=prompt,
            temperature=params.get("temperature", 0.4),
            max_tokens=params.get("max_tokens", 900),
        )
        text = raw.get("content", "")

        tags = self._parse_json_array(text, fallback_key="tags")
        results: List[Dict[str, Any]] = []

        for tag in tags:
            try:
                factor = SemanticFactorTag(
                    name=str(tag.get("name", "unknown")).strip(),
                    confidence=float(tag.get("confidence", 0.5)),
                    reasoning=str(tag.get("reasoning", "")),
                    applies_to_positions=[position_id] if position_id else [],
                    source_fields=["token_data"] + (["curator_message"] if curator_message else []),
                )
            except Exception as e:
                logger.warning(f"Skipping malformed semantic factor tag: {e}")
                continue

            record = {
                "kind": "semantic_factor",
                "level": 2,
                "module": module,
                "status": "hypothesis",
                "content": asdict(factor),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            res = self.sb.table("llm_learning").insert(record).execute()
            if res.data:
                record["id"] = res.data[0].get("id")
            results.append(record)

        return results

    def _build_l2_prompt(self, token_data: Dict[str, Any], curator_message: Optional[str]) -> str:
        """
        Build L2 prompt using PromptManager template.
        """
        token_name = token_data.get("token_name") or token_data.get("symbol") or "Unknown"
        chain = token_data.get("chain", "Unknown")
        mcap = token_data.get("market_cap", "Unknown")
        age = token_data.get("age_days", "Unknown")
        extra = json.dumps({k: v for k, v in token_data.items() if k not in ["token_name", "symbol", "chain", "market_cap", "age_days"]}, default=str)  # noqa: E501

        curator_block = f"\nCurator Message:\n{curator_message}\n" if curator_message else ""

        return self.prompt_manager.format_prompt(
            "l2_semantic_factor_extraction",
            {
                "token_name": token_name,
                "chain": chain,
                "market_cap": mcap,
                "age_days": age,
                "extra_metadata": extra,
                "curator_block": curator_block,
            }
        )

    # ------------------------------------------------------------------
    # Level 3 – Family Core Optimization
    # ------------------------------------------------------------------

    async def _run_level_3_family_optimization(self, module: ModuleName) -> List[Dict[str, Any]]:
        """
        L3: Ask the LLM to suggest better family cores (groupings of patterns).
        """
        stats_res = (
            self.sb.table("learning_lessons")
            .select("pattern_key,action_category,scope_subset,scope_values,stats")
            .eq("module", module)
            .eq("status", "active")
            .limit(300)
            .execute()
        )
        stats_rows = stats_res.data or []
        
        if not stats_rows:
            logger.info("L3: no learning_lessons data available")
            return []
        
        # Sort by edge_raw descending
        stats_rows.sort(
            key=lambda r: float((r.get("stats") or {}).get("edge_raw", 0.0)),
            reverse=True
        )
        
        # Convert pattern_scope_stats to braid-like format
        pattern_map: Dict[str, Dict[str, Any]] = {}
        for row in stats_rows:
            pattern_key = row.get("pattern_key", "")
            if not pattern_key:
                continue
            
            # Group by pattern_key, keep best edge_raw
            if pattern_key not in pattern_map:
                parts = pattern_key.split(".")
                family_id = f"{parts[0]}.{parts[1]}" if len(parts) >= 2 else "unknown"
                scope_data = row.get("scope_subset") or row.get("scope_values") or {}
                pattern_map[pattern_key] = {
                    "pattern_key": pattern_key,
                    "family_id": family_id,
                    "module": module,
                    "stats": row.get("stats", {}),
                    "dimensions": scope_data,
                }
        
        braids = list(pattern_map.values())
        
        if len(braids) < 10:
            logger.info("L3: not enough braids for family optimization")
            return []

        prompt = self._build_l3_prompt(braids)
        params = self.prompt_manager.get_parameters("l3_family_optimization")
        raw = self.llm.generate_completion(
            prompt=prompt,
            temperature=params.get("temperature", 0.5),
            max_tokens=params.get("max_tokens", 2000),
        )
        text = raw.get("content", "")

        proposals_json = self._parse_json_array(text, fallback_key="proposals")
        stored: List[Dict[str, Any]] = []

        for p in proposals_json:
            try:
                proposal = FamilyOptimizationProposal(
                    current_family_core=str(p.get("current_family_core", "")),
                    proposed_family_core=str(p.get("proposed_family_core", "")),
                    reasoning=str(p.get("reasoning", "")),
                    affected_pattern_keys=list(p.get("affected_pattern_keys", [])),
                )
            except Exception as e:
                logger.warning(f"Skipping malformed family proposal: {e}")
                continue

            record = {
                "kind": "family_proposal",
                "level": 3,
                "module": module,
                "status": "hypothesis",
                "content": asdict(proposal),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            res = self.sb.table("llm_learning").insert(record).execute()
            if res.data:
                record["id"] = res.data[0].get("id")
            stored.append(record)

        # math layer will later call a validator to test these proposals numerically
        return stored

    def _build_l3_prompt(self, braids: List[Dict[str, Any]]) -> str:
        """
        Build L3 prompt using PromptManager template.
        """
        # very compact summary to avoid prompt bloat
        families: Dict[str, List[Dict[str, Any]]] = {}
        for b in braids:
            fid = b.get("family_id", "unknown")
            families.setdefault(fid, []).append(b)

        lines = []
        for fid, group in list(families.items())[:12]:
            lines.append(f"\nFamily: {fid} (braids={len(group)})")
            for b in group[:3]:
                stats = b.get("stats") or {}
                dims = b.get("dimensions") or {}
                lines.append(
                    f"  - {b.get('pattern_key')} | n={stats.get('n', 0)}, "
                    f"avg_rr={stats.get('avg_rr', 0.0):.2f}, edge={stats.get('edge_raw', 0.0):.2f}, "
                    f"dims={{{k: dims[k] for k in sorted(dims.keys())[:4]}}}"
                )

        families_block = "\n".join(lines)

        return self.prompt_manager.format_prompt(
            "l3_family_optimization",
            {
                "families_block": families_block,
            }
        )

    # ------------------------------------------------------------------
    # Level 4 – Semantic Pattern Compression
    # ------------------------------------------------------------------

    async def _run_level_4_semantic_compression(self, module: ModuleName) -> List[Dict[str, Any]]:
        """
        L4: For each family, propose 1–3 semantic pattern names that compress multiple braids.
        """
        stats_res = (
            self.sb.table("learning_lessons")
            .select("pattern_key")
            .eq("module", module)
            .eq("status", "active")
            .limit(500)
            .execute()
        )
        stats_rows = stats_res.data or []
        
        # Extract family_id from pattern_key (format: "module.family.state.motif")
        family_set = set()
        for row in stats_rows:
            pattern_key = row.get("pattern_key", "")
            if pattern_key:
                parts = pattern_key.split(".")
                if len(parts) >= 2:
                    family_set.add(f"{parts[0]}.{parts[1]}")
        
        family_ids = list(family_set)[:8]

        stored: List[Dict[str, Any]] = []

        for fid in family_ids:
            stats_res = (
                self.sb.table("learning_lessons")
                .select("pattern_key,scope_subset,scope_values,stats")
                .eq("module", module)
                .eq("status", "active")
                .like("pattern_key", f"{fid}%")
                .limit(50)
                .execute()
            )
            stats_rows = stats_res.data or []
            
            if not stats_rows:
                continue
            
            # Sort by edge_raw descending
            stats_rows.sort(
                key=lambda r: float((r.get("stats") or {}).get("edge_raw", 0.0)),
                reverse=True
            )
            
            # Convert to braid-like format
            braids: List[Dict[str, Any]] = []
            for row in stats_rows:
                pattern_key = row.get("pattern_key", "")
                if pattern_key:
                    scope_data = row.get("scope_subset") or row.get("scope_values") or {}
                    braids.append({
                        "pattern_key": pattern_key,
                        "family_id": fid,
                        "module": module,
                        "stats": row.get("stats", {}),
                        "dimensions": scope_data,
                    })
            
            if len(braids) < 5:
                continue

            prompt = self._build_l4_prompt(fid, braids)
            params = self.prompt_manager.get_parameters("l4_semantic_compression")
            raw = self.llm.generate_completion(
                prompt=prompt,
                temperature=params.get("temperature", 0.5),
                max_tokens=params.get("max_tokens", 2000),
            )
            text = raw.get("content", "")

            patterns_json = self._parse_json_array(text, fallback_key="patterns")

            for p in patterns_json:
                try:
                    proposal = SemanticPatternProposal(
                        pattern_name=str(p.get("pattern_name", "")),
                        components=list(p.get("components", [])),
                        conceptual_summary=str(p.get("conceptual_summary", "")),
                        proposed_trigger=p.get("proposed_trigger", {}),
                        family_id=fid,
                    )
                except Exception as e:
                    logger.warning(f"Skipping malformed semantic pattern: {e}")
                    continue

                record = {
                    "kind": "semantic_pattern",
                    "level": 4,
                    "module": module,
                    "status": "hypothesis",
                    "content": asdict(proposal),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                res = self.sb.table("llm_learning").insert(record).execute()
                if res.data:
                    record["id"] = res.data[0].get("id")
                stored.append(record)

        return stored

    def _build_l4_prompt(self, family_id: str, braids: List[Dict[str, Any]]) -> str:
        """
        Build L4 prompt using PromptManager template.
        """
        lines = [f"Family {family_id} – sample braids:"]
        for b in braids[:12]:
            stats = b.get("stats") or {}
            dims = b.get("dimensions") or {}
            lines.append(
                f"- {b.get('pattern_key')} | n={stats.get('n', 0)}, avg_rr={stats.get('avg_rr', 0.0):.2f}, "
                f"edge={stats.get('edge_raw', 0.0):.2f}, dims={dims}"
            )
        braids_block = "\n".join(lines)

        return self.prompt_manager.format_prompt(
            "l4_semantic_compression",
            {
                "family_id": family_id,
                "braids_block": braids_block,
            }
        )

    # ------------------------------------------------------------------
    # Level 5 – Hypothesis Auto-Generation
    # ------------------------------------------------------------------

    async def _run_level_5_hypotheses(self, module: ModuleName) -> List[Dict[str, Any]]:
        """
        L5: Use braids + lessons to generate NEW testable hypotheses.
        """
        stats_res = (
            self.sb.table("learning_lessons")
            .select("pattern_key,action_category,scope_subset,scope_values,stats")
            .eq("module", module)
            .eq("status", "active")
            .limit(200)
            .execute()
        )
        stats_rows = stats_res.data or []
        
        if not stats_rows:
            logger.info("L5: no learning_lessons data available")
            return []
        
        # Sort by edge_raw descending
        stats_rows.sort(
            key=lambda r: float((r.get("stats") or {}).get("edge_raw", 0.0)),
            reverse=True
        )
        
        # Convert to braid-like format
        pattern_map: Dict[str, Dict[str, Any]] = {}
        for row in stats_rows:
            pattern_key = row.get("pattern_key", "")
            if not pattern_key:
                continue
            
            # Group by pattern_key, keep best edge_raw
            if pattern_key not in pattern_map:
                parts = pattern_key.split(".")
                family_id = f"{parts[0]}.{parts[1]}" if len(parts) >= 2 else "unknown"
                scope_data = row.get("scope_subset") or row.get("scope_values") or {}
                pattern_map[pattern_key] = {
                    "pattern_key": pattern_key,
                    "family_id": family_id,
                    "module": module,
                    "stats": row.get("stats", {}),
                    "dimensions": scope_data,
                }
        
        braids = list(pattern_map.values())

        lessons_res = (
            self.sb.table("learning_lessons")
            .select("id,module,stats,pattern_key,action_category,scope_subset,scope_values")
            .eq("module", module)
            .eq("status", "active")
            .limit(50)
            .execute()
        )
        lessons = lessons_res.data or []
        
        # Process lessons to derive missing fields
        processed_lessons = []
        for lesson in lessons:
            pattern_key = lesson.get("pattern_key", "")
            parts = pattern_key.split(".") if pattern_key else []
            family_id = f"{parts[0]}.{parts[1]}" if len(parts) >= 2 else "unknown"
            scope_subset = lesson.get("scope_subset") or lesson.get("scope_values") or {}
            scope_dims = list(scope_subset.keys()) if isinstance(scope_subset, dict) else []
            
            processed_lessons.append({
                **lesson,
                "family_id": family_id,
                "scope_dims": scope_dims,
                "trigger": None,  # Not in v5 schema
                "effect": None,   # Not in v5 schema
            })
        lessons = processed_lessons

        if len(braids) < 5:
            logger.info("L5: not enough braids for hypothesis generation")
            return []

        prompt = self._build_l5_prompt(braids, lessons)
        params = self.prompt_manager.get_parameters("l5_hypothesis_generation")
        raw = self.llm.generate_completion(
            prompt=prompt,
            temperature=params.get("temperature", 0.6),
            max_tokens=params.get("max_tokens", 2000),
        )
        text = raw.get("content", "")

        hyps_json = self._parse_json_array(text, fallback_key="hypotheses")
        stored: List[Dict[str, Any]] = []

        for h in hyps_json:
            try:
                proposal = HypothesisProposal(
                    type=h.get("type", "other"),
                    proposal=str(h.get("proposal", "")),
                    reasoning=str(h.get("reasoning", "")),
                    test_query=str(h.get("test_query", "")),
                )
            except Exception as e:
                logger.warning(f"Skipping malformed hypothesis: {e}")
                continue

            record = {
                "kind": "hypothesis",
                "level": 5,
                "module": module,
                "status": "hypothesis",
                "content": asdict(proposal),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            res = self.sb.table("llm_learning").insert(record).execute()
            if res.data:
                record["id"] = res.data[0].get("id")
            stored.append(record)

        return stored

    def _build_l5_prompt(self, braids: List[Dict[str, Any]], lessons: List[Dict[str, Any]]) -> str:
        """
        Build L5 prompt using PromptManager template.
        """
        def fmt_b(b: Dict[str, Any]) -> str:
            s = b.get("stats") or {}
            d = b.get("dimensions") or {}
            return (
                f"- {b.get('pattern_key')} | family={b.get('family_id')} "
                f"| n={s.get('n', 0)}, avg_rr={s.get('avg_rr', 0.0):.2f}, edge={s.get('edge_raw', 0.0):.2f}, dims={d}"
            )

        def fmt_l(l: Dict[str, Any]) -> str:
            s = l.get("stats") or {}
            return (
                f"- lesson={l.get('id')} | family={l.get('family_id')} "
                f"| n={s.get('n', 0)}, edge={s.get('edge_raw', 0.0):.2f}, trigger={l.get('trigger')}, effect={l.get('effect')}"
            )

        braids_block = "\n".join(fmt_b(b) for b in braids[:25]) or "None."
        lessons_block = "\n".join(fmt_l(l) for l in lessons[:15]) or "None."

        return self.prompt_manager.format_prompt(
            "l5_hypothesis_generation",
            {
                "braids_block": braids_block,
                "lessons_block": lessons_block,
            }
        )

    # ------------------------------------------------------------------
    # Helper: Parse JSON safely from LLM
    # ------------------------------------------------------------------

    def _parse_json_array(self, text: str, fallback_key: str) -> List[Dict[str, Any]]:
        """
        Extract a JSON array from an LLM response.

        Handles:
        - ```json ... ```
        - ``` ... ```
        - plain JSON
        - or a top-level dict with a given key pointing to a list.
        """
        if not text:
            return []

        try_strs = []

        # code fence variants
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            try_strs.append(text[start:end].strip())
        if "```" in text and not try_strs:
            start = text.find("```") + 3
            end = text.find("```", start)
            try_strs.append(text[start:end].strip())

        # whole text as fallback
        try_strs.append(text.strip())

        for candidate in try_strs:
            try:
                data = json.loads(candidate)
                if isinstance(data, list):
                    return data
                if isinstance(data, dict) and fallback_key in data and isinstance(data[fallback_key], list):
                    return data[fallback_key]
            except Exception:
                continue

        logger.warning("Failed to parse LLM JSON array; returning empty list")
        return []
