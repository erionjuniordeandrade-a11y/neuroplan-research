"""The mandatory research-use banner and its enforcement.

Every artifact the dashboard emits, and every screen it renders, must carry this
notice. The text is fixed; :func:`stamp` and :func:`assert_present` make it
structurally hard to emit output without it.
"""
from __future__ import annotations

from typing import Any, Mapping

RESEARCH_BANNER = (
    "Research use only. Not for clinical or intraoperative decision-making."
)

# The JSON/dict key under which the banner is stamped into exported artifacts.
BANNER_KEY = "notice"


class BannerMissing(RuntimeError):
    """Raised when an artifact that must carry the banner does not."""


def stamp(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy of ``payload`` with the research banner stamped in.

    Never mutates the input. If the caller already set ``BANNER_KEY`` to a
    different string, it is overwritten with the canonical banner — the notice
    is not negotiable and cannot be softened by an upstream caller.
    """
    out = dict(payload)
    out[BANNER_KEY] = RESEARCH_BANNER
    return out


def assert_present(payload: Mapping[str, Any]) -> None:
    """Fail loud if ``payload`` does not carry the exact research banner."""
    if payload.get(BANNER_KEY) != RESEARCH_BANNER:
        raise BannerMissing(
            f"artifact is missing the mandatory research banner under "
            f"'{BANNER_KEY}'; refusing to treat it as a valid research export"
        )
