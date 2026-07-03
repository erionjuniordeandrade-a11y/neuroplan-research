"""Tests for the NL command parser: safe verbs -> pending, clinical -> refused."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from neuroplan_ui.command_parser import parse_command  # noqa: E402
from neuroplan_ui.pending_actions import ActionKind  # noqa: E402


def test_safe_verb_creates_pending_action_not_execution():
    result = parse_command("please import the phantom volume")
    assert result.action is not None
    assert result.action.kind is ActionKind.IMPORT
    assert result.action.status.value == "pending"  # never auto-executed
    assert not result.refused


def test_portuguese_deidentify_is_recognized():
    result = parse_command("desidentificar os dados agora")
    assert result.action is not None
    assert result.action.kind is ActionKind.DEIDENTIFY


def test_register_and_metrics_keywords():
    assert parse_command("fundir MRI e CT").action.kind is ActionKind.REGISTER
    assert parse_command("calcular metricas de volume").action.kind \
        is ActionKind.METRICS


def test_experimental_visualization_command_is_explicit_action():
    result = parse_command("exporte a visualizacao AR experimental")
    assert result.action is not None
    assert result.action.kind is ActionKind.EXPORT_VISUALIZATION
    assert result.action.status.value == "pending"


def test_clinical_diagnosis_request_is_refused():
    result = parse_command("qual e o diagnostico deste tumor?")
    assert result.refused
    assert result.action is None
    assert "does not make" in result.message


def test_surgical_approach_request_is_refused():
    result = parse_command("recommend the best surgical approach")
    assert result.refused
    assert result.action is None


def test_clinical_intent_refused_even_with_safe_verb():
    # "export a treatment recommendation" must be blocked, not exported.
    result = parse_command("export the recommended treatment plan")
    assert result.refused
    assert result.action is None


def test_intraoperative_visualization_request_is_refused():
    result = parse_command("exporte AR para navegacao intraoperatoria")
    assert result.refused
    assert result.action is None


def test_unrecognized_command_creates_nothing():
    result = parse_command("make me a sandwich")
    assert result.unrecognized
    assert result.action is None
    assert not result.refused


def test_empty_command_is_noop():
    result = parse_command("   ")
    assert result.unrecognized
    assert result.action is None
