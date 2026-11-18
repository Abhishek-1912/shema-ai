"""A paused run must come back from the database exactly as it was saved."""

import json

import pytest

from app.services.agent_snapshot import SnapshotError, from_snapshot, to_snapshot
from tests.agent_fakes import done, waiting


def test_round_trip_through_json_keeps_everything() -> None:
    original = waiting()

    # json.dumps/loads = what happens when it goes into a jsonb column and back
    restored = from_snapshot(json.loads(json.dumps(to_snapshot(original))))

    assert restored == original  # dataclass equality: every field, incl. the AI messages


def test_thought_signature_survives() -> None:
    restored = from_snapshot(json.loads(json.dumps(to_snapshot(waiting()))))

    call = restored.state.messages[2]["tool_calls"][0]
    assert call["extra_content"]["google"]["thought_signature"] == "sig=="


def test_only_paused_runs_can_be_saved() -> None:
    with pytest.raises(ValueError):
        to_snapshot(done())


def test_unknown_version_is_refused() -> None:
    data = to_snapshot(waiting())
    data["version"] = 99

    with pytest.raises(SnapshotError):
        from_snapshot(data)


def test_plan_survives_the_round_trip() -> None:
    original = waiting()
    original.state.plan = ["Search the documents", "Delete the old copy"]
    original.plan = list(original.state.plan)

    restored = from_snapshot(json.loads(json.dumps(to_snapshot(original))))

    assert restored.plan == original.plan and restored.state.plan == original.state.plan


def test_snapshot_without_plan_still_loads() -> None:
    data = to_snapshot(waiting())
    del data["state"]["plan"]  # saved before planning existed

    restored = from_snapshot(data)

    assert restored.state.plan is None and restored.plan == []
