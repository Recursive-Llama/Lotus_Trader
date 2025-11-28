"""
Diagnostics tooling utilities for PM learning flow.

This package exposes helpers that replay strands, run the lesson builder,
and dry-run the override materializer so both CLI tools and harnesses share
the same implementations.
"""

from .tooling import (  # noqa: F401
    replay_position_closed_strand,
    lesson_builder_dry_run,
    materializer_dry_run,
)

