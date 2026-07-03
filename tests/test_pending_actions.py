"""Tests for the pending-action queue: confirmation is mandatory and named."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from neuroplan_ui.pending_actions import (  # noqa: E402
    ActionKind, ActionQueue, ActionStatus, PendingAction,
)


def _queue_with_one() -> tuple[ActionQueue, int]:
    action = PendingAction.create(ActionKind.IMPORT, "import volume")
    return ActionQueue().add(action), action.id


def test_new_action_starts_pending():
    queue, aid = _queue_with_one()
    assert queue.get(aid).status is ActionStatus.PENDING
    assert len(queue.pending()) == 1
    assert len(queue.confirmed()) == 0


def test_confirm_requires_named_operator():
    queue, aid = _queue_with_one()
    with pytest.raises(ValueError, match="named operator"):
        queue.confirm(aid, operator="   ")


def test_confirm_moves_to_confirmed_and_records_operator():
    queue, aid = _queue_with_one()
    queue = queue.confirm(aid, operator="Dr. Erion", reason="reviewed")
    action = queue.get(aid)
    assert action.status is ActionStatus.CONFIRMED
    assert action.decided_by == "Dr. Erion"
    assert action.decision_reason == "reviewed"


def test_only_confirmed_actions_are_executable():
    queue, aid = _queue_with_one()
    with pytest.raises(ValueError, match="only a CONFIRMED"):
        queue.mark_executed(aid)  # cannot execute a still-pending action


def test_cannot_confirm_twice():
    queue, aid = _queue_with_one()
    queue = queue.confirm(aid, operator="op")
    with pytest.raises(ValueError, match="not pending"):
        queue.confirm(aid, operator="op")


def test_queue_operations_are_immutable():
    queue, aid = _queue_with_one()
    confirmed = queue.confirm(aid, operator="op")
    # Original queue is unchanged; a new queue was returned.
    assert queue.get(aid).status is ActionStatus.PENDING
    assert confirmed.get(aid).status is ActionStatus.CONFIRMED


def test_execute_after_confirm_records_note():
    queue, aid = _queue_with_one()
    queue = queue.confirm(aid, operator="op").mark_executed(aid, "ran ok")
    assert queue.get(aid).status is ActionStatus.EXECUTED
    assert queue.get(aid).result_note == "ran ok"
