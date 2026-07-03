"""Natural-language command parser.

Requirement 5: text commands create *pending* actions for review — they never
execute. This parser maps free text (pt-BR or English) onto the closed set of
safe :class:`ActionKind` values, and — just as important — *refuses* anything
that reads like a request for a clinical decision (diagnosis, treatment,
surgical approach, intraoperative navigation). A refusal is not a pending
action: it produces no executable intent at all.

The parser is deliberately dumb and keyword-based. It has no medical knowledge
and makes no medical judgment; it only routes safe technical verbs and blocks
unsafe ones. When in doubt it returns "unrecognized", never a guessed action.
"""
from __future__ import annotations

import dataclasses
import re
import unicodedata

from .pending_actions import ActionKind, PendingAction


@dataclasses.dataclass(frozen=True)
class ParseResult:
    """Outcome of parsing one command line.

    Exactly one of ``action`` / ``refused`` / ``unrecognized`` is meaningful:
    - ``action`` set  -> a PENDING action was created (still needs confirming).
    - ``refused`` True -> the text requested a clinical decision; blocked.
    - otherwise       -> unrecognized; nothing was created.
    """

    raw_text: str
    action: PendingAction | None = None
    refused: bool = False
    message: str = ""

    @property
    def unrecognized(self) -> bool:
        return self.action is None and not self.refused


# Clinical-decision intents this research tool must never act on. Checked FIRST
# so a command like "recommend the best surgical approach and export it" is
# refused, not partially honored.
_CLINICAL_BLOCKLIST: tuple[tuple[str, str], ...] = (
    (r"diagnos", "diagnosis"),                 # diagnosis / diagnóstico
    (r"\btratamento\b|\btreatment\b|\btherap", "treatment"),
    (r"\bprognos", "prognosis"),
    (r"aborda(g|j)em|\bapproach\b|acesso cirurgic|craniotom",
     "surgical approach"),
    (r"navega|intraoperat|intra-operat|\bintraop\b", "intraoperative use"),
    (r"recomend|\brecommend\b|melhor conduta|should i|devo operar",
     "clinical recommendation"),
    (r"resec|\bgrade\b|\bgrau\b\s+(who|oms)|malign|beni(g|gn)",
     "clinical characterization"),
)

# Safe technical verbs -> action kind. Order matters only for readability; each
# pattern is matched independently and the first hit wins.
_SAFE_INTENTS: tuple[tuple[str, ActionKind], ...] = (
    (r"import|carreg|abrir|load", ActionKind.IMPORT),
    (r"de-?ident|deid|anonimiz|desidentific", ActionKind.DEIDENTIFY),
    (r"regist|fund(i|e)|fus(a|ã|e)|align|coregist", ActionKind.REGISTER),
    (r"segment", ActionKind.SEGMENT),
    (r"metric|métric|medi(r|ç)|mensur|calcul.*med|measur|volume|diamet",
     ActionKind.METRICS),
    (r"\bunreal\b|\bar\b|realidade aumentada|visualiza.*(3d|experimental)|"
     r"export.*(unreal|ar|visualiza)", ActionKind.EXPORT_VISUALIZATION),
    (r"export|exportar|salvar artefato|gerar relat|report", ActionKind.EXPORT),
)


def _normalize(text: str) -> str:
    """Lowercase and strip accents so pt-BR and English match the same rules."""
    lowered = text.strip().lower()
    decomposed = unicodedata.normalize("NFKD", lowered)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def parse_command(text: str) -> ParseResult:
    """Parse one command line into a :class:`ParseResult`.

    Never executes anything. Clinical-decision requests are refused before any
    safe intent is considered.
    """
    raw = text.strip()
    if not raw:
        return ParseResult(raw_text=raw, message="empty command")

    normalized = _normalize(raw)

    for pattern, topic in _CLINICAL_BLOCKLIST:
        if re.search(pattern, normalized):
            return ParseResult(
                raw_text=raw,
                refused=True,
                message=(
                    f"Refused: this is a research tool and does not make "
                    f"clinical decisions ({topic}). No action was created."
                ),
            )

    for pattern, kind in _SAFE_INTENTS:
        if re.search(pattern, normalized):
            action = PendingAction.create(kind=kind, raw_text=raw)
            return ParseResult(
                raw_text=raw,
                action=action,
                message=(
                    f"Created PENDING '{kind.value}' action — confirm it in the "
                    f"review panel before it runs."
                ),
            )

    return ParseResult(
        raw_text=raw,
        message=(
            "Unrecognized command. Known verbs: import, de-identify, register, "
            "segment, metrics, export."
        ),
    )
