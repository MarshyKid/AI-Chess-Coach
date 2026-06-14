"""Typed metadata shared by all detected events."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EventMetadata:
    """Canonical move and position metadata for a detected event."""

    before_fen: str
    after_fen: str
    move_uci: str
    move_san: str
    ply: int
