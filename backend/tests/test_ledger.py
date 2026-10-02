import tempfile
from pathlib import Path

import pytest

from app.ledger import DecisionLedger, DecisionRecord


@pytest.fixture
def ledger():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        led = DecisionLedger(db_path)
        yield led
        led.close()


def test_record_and_retrieve(ledger):
    ledger.record(DecisionRecord(
        trigger_event="battery_critical",
        decision="reassign",
        reasoning_text="ScoutDrone-3 battery critical, reassigned to HeavyRover-1",
        agent_id="scout-3",
        confidence_score=0.91,
    ))
    rows = ledger.recent(10)
    assert len(rows) == 1
    assert rows[0]["decision"] == "reassign"
    assert rows[0]["confidence_score"] == 0.91


def test_recent_returns_newest_first(ledger):
    for i in range(3):
        ledger.record(DecisionRecord(trigger_event="e", decision=f"d{i}", reasoning_text="r"))
    rows = ledger.recent(10)
    assert [r["decision"] for r in rows] == ["d2", "d1", "d0"]


def test_recent_respects_limit(ledger):
    for i in range(5):
        ledger.record(DecisionRecord(trigger_event="e", decision=f"d{i}", reasoning_text="r"))
    assert len(ledger.recent(2)) == 2


def test_count_tracks_total_records(ledger):
    assert ledger.count() == 0
    ledger.record(DecisionRecord(trigger_event="e", decision="d", reasoning_text="r"))
    assert ledger.count() == 1


def test_escalated_flag_round_trips(ledger):
    ledger.record(DecisionRecord(trigger_event="e", decision="escalate", reasoning_text="r", escalated=True))
    rows = ledger.recent(1)
    assert rows[0]["escalated"] == 1


def test_records_persist_across_connections(tmp_path):
    db_path = tmp_path / "persist.db"
    led1 = DecisionLedger(db_path)
    led1.record(DecisionRecord(trigger_event="e", decision="d", reasoning_text="r"))
    led1.close()

    led2 = DecisionLedger(db_path)
    assert led2.count() == 1
    led2.close()
