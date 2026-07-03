"""NeuroPlan research UX layer (offline, non-clinical).

A friendly dashboard + command layer over 3D Slicer for a research-only
workflow. This package never makes medical decisions; it orchestrates safe
technical stages, each behind a quality gate, with mandatory human confirmation
on sensitive actions.

    Research use only. Not for clinical or intraoperative decision-making.
"""
from __future__ import annotations

from .banner import RESEARCH_BANNER

__all__ = ["RESEARCH_BANNER"]
