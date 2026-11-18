"""Unit tests for the store of agent runs waiting for approval."""

import pytest

from app.services.pending_runs import PendingRunStore, RunNotFoundError
from app.services.tool_agent import AgentResult


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def paused() -> AgentResult:
    return AgentResult(status="needs_approval")


def test_put_then_take_returns_the_same_run() -> None:
    store = PendingRunStore()
    run = paused()

    run_id = store.put(run)

    assert store.take(run_id) is run


def test_ids_are_random_and_long() -> None:
    store = PendingRunStore()

    ids = {store.put(paused()) for _ in range(50)}

    assert len(ids) == 50
    assert all(len(i) >= 20 for i in ids)  # unguessable


def test_a_run_can_be_taken_only_once() -> None:
    store = PendingRunStore()
    run_id = store.put(paused())
    store.take(run_id)

    with pytest.raises(RunNotFoundError):
        store.take(run_id)


def test_unknown_id_is_not_found() -> None:
    with pytest.raises(RunNotFoundError):
        PendingRunStore().take("nope")


def test_runs_expire() -> None:
    clock = FakeClock()
    store = PendingRunStore(ttl_seconds=60, clock=clock)
    run_id = store.put(paused())

    clock.now += 61

    assert len(store) == 0
    with pytest.raises(RunNotFoundError):
        store.take(run_id)
