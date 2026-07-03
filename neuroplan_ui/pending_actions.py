"""Pending-action model and queue.

Requirement 5 of the research spec: natural-language commands must create
*pending* actions that a human reviews and confirms — nothing runs
automatically. This module is the data layer for that guarantee.

Design notes:
- :class:`PendingAction` is frozen. State transitions return a *new* action;
  an action is never mutated in place, so history is always reconstructable.
- :class:`ActionQueue` is likewise immutable-by-copy: ``add`` / ``confirm`` /
  ``reject`` / ``mark_executed`` each return a new queue. The Streamlit layer
  reassigns ``session_state`` with the returned queue.
- Confirmation is explicit and cannot be skipped: :meth:`ActionQueue.confirm`
  is the *only* path from PENDING to CONFIRMED, and only CONFIRMED actions are
  eligible for execution (:meth:`ActionQueue.confirmed`).
"""
from __future__ import annotations

import dataclasses
import itertools
from enum import Enum
from typing import Any, Mapping


class ActionStatus(str, Enum):
    PENDING = "pending"        # parsed, awaiting human confirmation
    CONFIRMED = "confirmed"    # human confirmed; eligible to execute
    REJECTED = "rejected"      # human declined
    EXECUTED = "executed"      # ran after confirmation
    FAILED = "failed"          # ran after confirmation but errored


class ActionKind(str, Enum):
    """The closed set of safe, non-clinical actions the parser may propose."""

    IMPORT = "import"
    DEIDENTIFY = "deidentify"
    REGISTER = "register"
    SEGMENT = "segment"
    METRICS = "metrics"
    EXPORT = "export"
    EXPORT_VISUALIZATION = "export_visualization"


_ID_COUNTER = itertools.count(1)


@dataclasses.dataclass(frozen=True)
class PendingAction:
    id: int
    kind: ActionKind
    raw_text: str
    params: Mapping[str, Any]
    status: ActionStatus = ActionStatus.PENDING
    decided_by: str = ""          # operator who confirmed/rejected
    decision_reason: str = ""     # human-entered note, if any
    result_note: str = ""         # populated after execution

    @staticmethod
    def create(kind: ActionKind, raw_text: str,
               params: Mapping[str, Any] | None = None) -> "PendingAction":
        return PendingAction(
            id=next(_ID_COUNTER),
            kind=kind,
            raw_text=raw_text,
            params=dict(params or {}),
        )


class ActionQueue:
    """An append-only, immutable-by-copy queue of pending actions."""

    def __init__(self, actions: tuple[PendingAction, ...] = ()):
        self._actions = tuple(actions)

    def __iter__(self):
        return iter(self._actions)

    def __len__(self) -> int:
        return len(self._actions)

    @property
    def actions(self) -> tuple[PendingAction, ...]:
        return self._actions

    def get(self, action_id: int) -> PendingAction:
        for a in self._actions:
            if a.id == action_id:
                return a
        raise KeyError(f"no pending action with id {action_id}")

    def add(self, action: PendingAction) -> "ActionQueue":
        return ActionQueue(self._actions + (action,))

    def _replace(self, action_id: int, **changes: Any) -> "ActionQueue":
        updated = tuple(
            dataclasses.replace(a, **changes) if a.id == action_id else a
            for a in self._actions
        )
        return ActionQueue(updated)

    def confirm(self, action_id: int, operator: str,
                reason: str = "") -> "ActionQueue":
        """Move a PENDING action to CONFIRMED. Requires a non-empty operator.

        Confirmation is the human-in-the-loop checkpoint; an anonymous confirm
        is refused so the audit trail always names who authorized the action.
        """
        action = self.get(action_id)
        if action.status is not ActionStatus.PENDING:
            raise ValueError(
                f"action {action_id} is {action.status.value}, not pending; "
                f"cannot confirm"
            )
        if not operator.strip():
            raise ValueError("confirmation requires a named operator")
        return self._replace(
            action_id, status=ActionStatus.CONFIRMED,
            decided_by=operator.strip(), decision_reason=reason.strip(),
        )

    def reject(self, action_id: int, operator: str,
               reason: str = "") -> "ActionQueue":
        action = self.get(action_id)
        if action.status is not ActionStatus.PENDING:
            raise ValueError(
                f"action {action_id} is {action.status.value}, not pending; "
                f"cannot reject"
            )
        return self._replace(
            action_id, status=ActionStatus.REJECTED,
            decided_by=operator.strip(), decision_reason=reason.strip(),
        )

    def mark_executed(self, action_id: int, note: str = "") -> "ActionQueue":
        action = self.get(action_id)
        if action.status is not ActionStatus.CONFIRMED:
            raise ValueError(
                f"action {action_id} is {action.status.value}; only a CONFIRMED "
                f"action may be executed"
            )
        return self._replace(
            action_id, status=ActionStatus.EXECUTED, result_note=note.strip())

    def mark_failed(self, action_id: int, note: str = "") -> "ActionQueue":
        action = self.get(action_id)
        if action.status is not ActionStatus.CONFIRMED:
            raise ValueError(
                f"action {action_id} is {action.status.value}; only a CONFIRMED "
                f"action may be executed")
        return self._replace(
            action_id, status=ActionStatus.FAILED, result_note=note.strip())

    def pending(self) -> tuple[PendingAction, ...]:
        return tuple(a for a in self._actions
                     if a.status is ActionStatus.PENDING)

    def confirmed(self) -> tuple[PendingAction, ...]:
        return tuple(a for a in self._actions
                     if a.status is ActionStatus.CONFIRMED)
