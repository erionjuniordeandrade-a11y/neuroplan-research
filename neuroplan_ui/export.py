"""Research-artifact export.

Emits an offline JSON artifact describing the run. Every artifact is stamped
with the mandatory research banner (:mod:`neuroplan_ui.banner`) and re-validated
before it is returned — it is structurally hard to produce an export without the
notice. The schema deliberately has NO field for diagnosis, grade, treatment, or
surgical approach, so the export cannot carry a clinical recommendation.

3D model export is offline, experimental visualization only (spec R6): the
artifact records a *path* produced by the (stubbed) Slicer model exporter and
flags it as non-clinical. Nothing here is AR or intraoperative.
"""
from __future__ import annotations

import json
from typing import Any, Mapping

from . import banner


# Fields that must never appear in a research artifact. Presence is a hard error
# — it means someone tried to smuggle a clinical decision into the output.
_FORBIDDEN_FIELDS = frozenset({
    "diagnosis", "diagnostico", "grade", "grau", "treatment", "tratamento",
    "approach", "abordagem", "recommendation", "recomendacao", "who_grade",
})


class ForbiddenField(RuntimeError):
    """Raised when an export payload contains a clinical-decision field."""


def build_artifact(*, case_label: str, metrics: Mapping[str, Any],
                   registration_reason: str, audit: list[dict[str, Any]],
                   model_path: str | None = None) -> dict[str, Any]:
    """Assemble a banner-stamped research artifact dict. Never includes PHI."""
    for key in metrics:
        if key.lower() in _FORBIDDEN_FIELDS:
            raise ForbiddenField(
                f"metric field '{key}' is a clinical-decision field and is not "
                f"permitted in a research export")

    payload: dict[str, Any] = {
        "schema": "neuroplan-research-artifact/v1",
        "case_label": case_label,
        "metrics": dict(metrics),
        "registration_gate": registration_reason,
        "audit_log": list(audit),
    }
    if model_path is not None:
        payload["model_export"] = {
            "path": model_path,
            "purpose": "offline experimental visualization only",
            "not_for": "clinical AR or intraoperative navigation",
        }

    stamped = banner.stamp(payload)
    banner.assert_present(stamped)     # fail loud if the notice is missing
    return stamped


def to_json(artifact: Mapping[str, Any]) -> str:
    """Serialize an artifact, re-checking the banner on the way out."""
    banner.assert_present(artifact)
    return json.dumps(artifact, indent=2, ensure_ascii=False, sort_keys=True)


def write_json(artifact: Mapping[str, Any], out_path: str) -> str:
    """Write the artifact to ``out_path`` (offline). Returns the path."""
    banner.assert_present(artifact)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(to_json(artifact))
    return out_path
