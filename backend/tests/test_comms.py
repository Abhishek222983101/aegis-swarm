from app.sim.comms import CommMessage, CommScheduler
from app.sim.events import EventType


def test_high_priority_message_sent_before_routine_telemetry():
    sched = CommScheduler(bandwidth_per_tick=1)
    sched.enqueue(CommMessage("a1", None, {"telemetry": "position"}))  # routine
    sched.enqueue(CommMessage("a1", EventType.TARGET_FOUND, {}))  # critical

    results = sched.tick()
    sent_types = [m.event_type for m in results["a1"].sent]
    assert sent_types == [EventType.TARGET_FOUND]


def test_messages_beyond_bandwidth_are_deferred_not_lost_immediately():
    sched = CommScheduler(bandwidth_per_tick=1, max_queue_depth=5)
    sched.enqueue(CommMessage("a1", EventType.TARGET_FOUND, {}))
    sched.enqueue(CommMessage("a1", EventType.AGENT_FAILURE, {}))

    results = sched.tick()
    assert len(results["a1"].sent) == 1
    assert len(results["a1"].deferred) == 1
    assert results["a1"].deferred[0].event_type == EventType.AGENT_FAILURE


def test_deferred_messages_carry_forward_and_eventually_send():
    sched = CommScheduler(bandwidth_per_tick=1)
    sched.enqueue(CommMessage("a1", EventType.TARGET_FOUND, {}))
    sched.enqueue(CommMessage("a1", EventType.AGENT_FAILURE, {}))
    sched.tick()  # TARGET_FOUND sent, AGENT_FAILURE deferred

    results = sched.tick()  # deferred AGENT_FAILURE should now send
    assert results["a1"].sent[0].event_type == EventType.AGENT_FAILURE


def test_queue_overflow_drops_lowest_priority_oldest_first():
    sched = CommScheduler(bandwidth_per_tick=0, max_queue_depth=2)
    sched.enqueue(CommMessage("a1", EventType.TARGET_FOUND, {}))
    sched.enqueue(CommMessage("a1", EventType.AGENT_FAILURE, {}))
    sched.enqueue(CommMessage("a1", None, {}))  # routine, lowest priority

    results = sched.tick()
    assert len(results["a1"].deferred) == 2
    assert len(results["a1"].dropped) == 1
    assert results["a1"].dropped[0].event_type is None  # routine telemetry dropped first


def test_routine_telemetry_never_starves_critical_messages_across_ticks():
    sched = CommScheduler(bandwidth_per_tick=1)
    for _ in range(5):
        sched.enqueue(CommMessage("a1", None, {}))  # flood with routine telemetry
    sched.enqueue(CommMessage("a1", EventType.AGENT_FAILURE, {}))

    results = sched.tick()
    # Critical message must win the single bandwidth slot despite being enqueued last.
    assert results["a1"].sent[0].event_type == EventType.AGENT_FAILURE


def test_agents_with_no_pending_messages_are_absent_from_results():
    sched = CommScheduler()
    sched.enqueue(CommMessage("a1", EventType.TARGET_FOUND, {}))
    results = sched.tick()
    assert "a2" not in results
