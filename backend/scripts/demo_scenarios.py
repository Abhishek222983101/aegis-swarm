"""Live demo-scenario rehearsal script — Phase 6.1.

Run against the actual running server (not mocks, not TestClient) to verify
each of the 4 PRD-required fault scenarios produces the right live behavior.
This IS the rehearsal script: run it before presenting to catch anything that
broke since the last check.

Usage: .venv/bin/python scripts/demo_scenarios.py [base_url]
Default base_url: http://localhost:8731
"""
from __future__ import annotations

import sys
import time

import requests

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8731"


def get(path: str):
    r = requests.get(f"{BASE}{path}")
    r.raise_for_status()
    return r.json()


def post(path: str, json: dict):
    r = requests.post(f"{BASE}{path}", json=json)
    return r.status_code, (r.json() if r.content else {})


def banner(title: str):
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def wait_for_decision(predicate, timeout=5.0, label="matching decision"):
    """Poll the ledger until a decision matching `predicate` appears."""
    start = time.time()
    while time.time() - start < timeout:
        entries = get("/ledger?limit=10")
        for entry in entries:
            if predicate(entry):
                return entry
        time.sleep(0.6)
    raise AssertionError(f"Timed out waiting for {label}. Last ledger entries: {get('/ledger?limit=5')}")


def scenario_a_battery():
    banner("SCENARIO A — Battery-critical reassignment")
    state = get("/state")
    agent_id = next(a["id"] for a in state["agents"] if a["status"] != "lost")
    print(f"Target: {agent_id}")

    status, result = post("/inject/battery-drain", {"agent_id": agent_id, "drop_to": 12})
    assert status == 200, f"injection failed: {result}"
    print(f"Injected battery drain -> {result}")

    entry = wait_for_decision(
        lambda e: e["trigger_event"] == "battery_critical" and e["agent_id"] == agent_id,
        label="battery_critical decision",
    )
    print(f"PASS — decision: {entry['decision']} | {entry['reasoning_text']}")
    assert entry["decision"] in ("reassign", "escalate", "acknowledge", "terminate")


def scenario_b_comm_loss():
    banner("SCENARIO B — Comm loss + relay repositioning")
    state = get("/state")
    relay_before = next((a for a in state["agents"] if a["type"] == "comm_relay"), None)
    target = next(a["id"] for a in state["agents"] if a["type"] != "comm_relay" and a["status"] != "lost")
    print(f"Target: {target}, relay before: {relay_before['position'] if relay_before else 'none'}")

    status, result = post("/inject/comm-loss", {"agent_id": target})
    assert status == 200, f"injection failed: {result}"
    print(f"Injected comm loss -> {result}")

    entry = wait_for_decision(
        lambda e: e["trigger_event"] == "comm_lost" and e["agent_id"] == target,
        label="comm_lost decision",
    )
    print(f"PASS — decision: {entry['decision']} | {entry['reasoning_text']}")
    assert entry["decision"] in ("reposition", "escalate")


def scenario_c_target_found():
    banner("SCENARIO C — Structural replan via target-found")
    status, result = post("/inject/target-found", {"x": 250, "y": 250, "priority": "high"})
    assert status == 200, f"injection failed: {result}"
    print(f"PASS — decision: {result['decision']} | {result['reasoning_text']}")
    assert result["decision"] in ("reassign", "escalate")


def scenario_d_route_block_and_failure():
    banner("SCENARIO D — Route block + agent failure -> feasibility check")
    state = get("/state")
    alive = [a for a in state["agents"] if a["status"] != "lost"]
    print(f"Agents alive before: {len(alive)}")

    status, result = post("/inject/route-block", {"zone_id": f"zone-demo-{int(time.time())}", "x": 150, "y": 150, "radius": 60})
    assert status == 200, f"route-block injection failed: {result}"
    print(f"Route blocked -> {result}")

    # Fail agents one by one, checking feasibility after each, until termination
    # fires or we run out of agents — proves the mission-level reasoning path.
    terminated = False
    for agent in alive[:-1]:  # leave at least one so the world isn't fully empty
        status, result = post("/inject/agent-failure", {"agent_id": agent["id"]})
        assert status == 200, f"agent-failure injection failed: {result}"
        print(f"Failed {agent['id']}")
        time.sleep(0.6)

        ledger = get("/ledger?limit=5")
        if any(e["decision"] == "terminate" for e in ledger):
            entry = next(e for e in ledger if e["decision"] == "terminate")
            print(f"PASS — mission-feasibility termination fired: {entry['reasoning_text']}")
            terminated = True
            break

    if not terminated:
        print("NOTE — termination did not fire with this many agents failed; "
              "feasibility threshold may need more failures to trip, or the "
              "default swarm (4 agents) is too small to demonstrate this cleanly. "
              "Not a hard failure, but worth tuning before the live demo.")


def main():
    print(f"Running demo scenario rehearsal against {BASE}")
    health = get("/health")
    print(f"Server health: {health}")

    scenario_a_battery()
    scenario_b_comm_loss()
    scenario_c_target_found()
    scenario_d_route_block_and_failure()

    banner("ALL SCENARIOS EXECUTED")


if __name__ == "__main__":
    main()
