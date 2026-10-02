import pytest
from fastapi.testclient import TestClient

import app.main as main_module


@pytest.fixture
def client():
    main_module.state = main_module.AppState()  # fresh world/ledger per test, avoid cross-test bleed
    with TestClient(main_module.app) as c:
        yield c


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["agents"] == 4


def test_state_endpoint_returns_agents(client):
    r = client.get("/state")
    assert r.status_code == 200
    assert len(r.json()["agents"]) == 4


def test_inject_battery_drain_via_api(client):
    r = client.post("/inject/battery-drain", json={"agent_id": "scout-1", "drop_to": 10.0})
    assert r.status_code == 200
    assert r.json()["type"] == "battery_critical"

    state_r = client.get("/state")
    scout = next(a for a in state_r.json()["agents"] if a["id"] == "scout-1")
    assert scout["battery"] <= 10.0


def test_inject_unknown_agent_returns_clean_404_not_a_crash(client):
    r = client.post("/inject/battery-drain", json={"agent_id": "ghost-agent"})
    assert r.status_code == 404
    assert "ghost-agent" in r.json()["error"]


def test_inject_agent_failure_via_api(client):
    r = client.post("/inject/agent-failure", json={"agent_id": "rover-1"})
    assert r.status_code == 200
    state_r = client.get("/state")
    rover = next(a for a in state_r.json()["agents"] if a["id"] == "rover-1")
    assert rover["status"] == "lost"


def test_inject_weather_via_api(client):
    r = client.post("/inject/weather", json={"level": "severe"})
    assert r.status_code == 200
    assert client.get("/state").json()["weather"] == "severe"


def test_inject_target_found_produces_a_decision(client):
    r = client.post("/inject/target-found", json={"x": 200, "y": 200})
    assert r.status_code == 200
    assert r.json()["decision"] in ("reassign", "escalate")


def test_mission_endpoint_returns_task_plan(client):
    r = client.post("/mission", json={"objective": "Scout Sector 7 and establish a comm relay"})
    assert r.status_code == 200
    plan = r.json()
    assert len(plan["tasks"]) >= 1
    assert plan["source"] == "template"  # no ANTHROPIC_API_KEY in test env


def test_ledger_endpoint_reflects_injected_events(client):
    client.post("/inject/agent-failure", json={"agent_id": "rover-1"})
    # agent-failure injection itself doesn't go through the supervisor directly in
    # this route (it's a raw fault injection); trigger one that does:
    client.post("/inject/target-found", json={"x": 100, "y": 100})
    r = client.get("/ledger")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_websocket_sends_initial_state_on_connect(client):
    with client.websocket_connect("/ws") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "state"
        assert len(msg["data"]["agents"]) == 4


def test_escalations_endpoint_lists_pending(client):
    r = client.get("/escalations")
    assert r.status_code == 200
    assert r.json() == []


def test_server_prefix_is_stripped_for_http(client):
    # Mirrors how Vercel Services forwards requests in production (full path,
    # /server prefix still attached) — the backend must handle both forms.
    r = client.get("/server/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_bare_path_still_works_without_prefix(client):
    r = client.get("/health")
    assert r.status_code == 200
