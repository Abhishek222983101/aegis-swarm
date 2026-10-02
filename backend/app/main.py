"""AEGIS backend — single FastAPI process holding the simulation, decision
layer, ledger, and WebSocket broadcast. See BUILD-PLAN.md for why this is one
process instead of five services.
"""
from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.ledger import DecisionLedger
from app.ml.inference import Allocator
from app.ml.planner import decompose_mission
from app.sim import faults
from app.sim.faults import FaultTargetError
from app.sim.comms import CommMessage, CommScheduler
from app.sim.entities import AgentType
from app.sim.world import World
from app.supervisor import Supervisor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aegis")

TICK_INTERVAL_SECONDS = 0.5
REPLAY_BUFFER_SIZE = 120  # ~60s of history at 0.5s/tick, per BUILD-PLAN.md Phase 6.3


class ConnectionManager:
    def __init__(self):
        self.active: set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.add(ws)

    def disconnect(self, ws: WebSocket):
        self.active.discard(ws)

    async def broadcast(self, message: dict):
        dead = []
        payload = json.dumps(message)
        for ws in self.active:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


class AppState:
    def __init__(self):
        self.world = World()
        self.world.spawn_default_swarm()
        self.ledger = DecisionLedger()
        self.allocator = Allocator()
        self.supervisor = Supervisor(self.world, self.ledger, self.allocator)
        self.comm_scheduler = CommScheduler(bandwidth_per_tick=3)
        self.manager = ConnectionManager()
        self.replay_buffer: list[dict] = []
        self.tick_running = False


state = AppState()


async def tick_loop():
    state.tick_running = True
    while state.tick_running:
        events = state.world.tick(dt=TICK_INTERVAL_SECONDS)

        for event in events:
            if event.agent_id:
                state.comm_scheduler.enqueue(CommMessage(event.agent_id, event.type, event.data))

        comm_results = state.comm_scheduler.tick()
        for agent_id, result in comm_results.items():
            for msg in result.sent:
                if msg.event_type is None:
                    continue
                from app.sim.events import SimEvent
                record = state.supervisor.handle_event(SimEvent(msg.event_type, agent_id, msg.payload))
                await state.manager.broadcast({"type": "decision", "data": record.to_dict()})

        expired = state.supervisor.expire_stale_escalations()
        for esc in expired:
            await state.manager.broadcast({
                "type": "escalation_resolved",
                "data": {"id": esc.id, "operator_decision": esc.operator_decision},
            })

        snapshot = {"type": "state", "data": state.world.state_snapshot()}
        state.replay_buffer.append(snapshot)
        if len(state.replay_buffer) > REPLAY_BUFFER_SIZE:
            state.replay_buffer.pop(0)

        await state.manager.broadcast(snapshot)
        await asyncio.sleep(TICK_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(tick_loop())
    logger.info("AEGIS tick loop started (allocator backend: %s)", state.allocator.backend)
    yield
    state.tick_running = False
    task.cancel()


app = FastAPI(title="AEGIS", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # same-origin in production via Vercel Services rewrite; permissive for local dev
    allow_methods=["*"],
    allow_headers=["*"],
)


class StripServerPrefixMiddleware:
    """Vercel Services' rewrite forwards the full path, '/server' prefix still
    attached, to this service (see BUILD-PLAN.md §2). The Vite dev proxy mirrors
    that exact behavior (no local rewrite) so dev and prod are never divergent —
    this one middleware is the single place that strips the prefix, for both."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket") and scope["path"].startswith("/server"):
            scope = dict(scope)
            scope["path"] = scope["path"][len("/server"):] or "/"
        await self.app(scope, receive, send)


app.add_middleware(StripServerPrefixMiddleware)


@app.exception_handler(FaultTargetError)
async def fault_target_error_handler(request: Request, exc: FaultTargetError):
    # Scenario Injector clicks must never surface a raw 500/traceback to a
    # non-technical operator — always a clean, explainable JSON error.
    return JSONResponse(status_code=404, content={"error": str(exc)})


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "tick": state.world.tick_count,
        "agents": len(state.world.agents),
        "allocator_backend": state.allocator.backend,
    }


@app.get("/state")
async def get_state():
    return state.world.state_snapshot()


@app.get("/ledger")
async def get_ledger(limit: int = 50):
    return state.ledger.recent(limit)


@app.get("/replay")
async def get_replay():
    return state.replay_buffer


# -- Scenario Injection API (Phase 1.5 / Phase 4.4 Scenario Injector target) --
class BatteryDrainReq(BaseModel):
    agent_id: str
    drop_to: float = 15.0


class CommLossReq(BaseModel):
    agent_id: str


class RouteBlockReq(BaseModel):
    zone_id: str
    x: float
    y: float
    radius: float = 40.0


class AgentFailureReq(BaseModel):
    agent_id: str


class WeatherReq(BaseModel):
    level: str


class TargetFoundReq(BaseModel):
    x: float
    y: float
    priority: str = "high"


async def _inject_and_broadcast(event):
    await state.manager.broadcast({"type": "event", "data": event.to_dict()})
    return event


@app.post("/inject/battery-drain")
async def inject_battery_drain(req: BatteryDrainReq):
    event = faults.inject_battery_drain(state.world, req.agent_id, req.drop_to)
    return (await _inject_and_broadcast(event)).to_dict()


@app.post("/inject/comm-loss")
async def inject_comm_loss(req: CommLossReq):
    event = faults.inject_comm_loss(state.world, req.agent_id)
    return (await _inject_and_broadcast(event)).to_dict()


@app.post("/inject/route-block")
async def inject_route_block(req: RouteBlockReq):
    event = faults.inject_route_block(state.world, req.zone_id, req.x, req.y, req.radius)
    return (await _inject_and_broadcast(event)).to_dict()


@app.post("/inject/agent-failure")
async def inject_agent_failure(req: AgentFailureReq):
    event = faults.inject_agent_failure(state.world, req.agent_id)
    return (await _inject_and_broadcast(event)).to_dict()


@app.post("/inject/weather")
async def inject_weather(req: WeatherReq):
    event = faults.inject_weather_change(state.world, req.level)
    return (await _inject_and_broadcast(event)).to_dict()


@app.post("/inject/target-found")
async def inject_target_found(req: TargetFoundReq):
    event = faults.inject_target_found(state.world, req.x, req.y, req.priority)
    record = state.supervisor.handle_event(event)
    await state.manager.broadcast({"type": "decision", "data": record.to_dict()})
    return record.to_dict()


# -- Mission intake (Phase 2.7 / Phase 5) --
class MissionReq(BaseModel):
    objective: str


@app.post("/mission")
async def post_mission(req: MissionReq):
    plan = decompose_mission(req.objective)
    for task in plan.tasks:
        if task.required_type:
            state.supervisor.task_target_type[task.id] = task.required_type
    await state.manager.broadcast({"type": "mission_plan", "data": plan.to_dict()})
    return plan.to_dict()


# -- Escalation resolution (Phase 3.3) --
class EscalationResponseReq(BaseModel):
    decision: str  # "approve" | "override"


@app.post("/escalation/{escalation_id}/respond")
async def respond_escalation(escalation_id: str, req: EscalationResponseReq):
    esc = state.supervisor.resolve_escalation(escalation_id, req.decision)
    if esc is None:
        return {"error": "no such pending escalation (already resolved or unknown id)"}
    await state.manager.broadcast({
        "type": "escalation_resolved",
        "data": {"id": esc.id, "operator_decision": esc.operator_decision},
    })
    return {"id": esc.id, "resolved": True, "operator_decision": esc.operator_decision}


@app.get("/escalations")
async def get_escalations():
    return [
        {"id": e.id, "reasoning": e.reasoning, "resolved": e.resolved, "operator_decision": e.operator_decision}
        for e in state.supervisor.pending_escalations.values()
    ]


# -- WebSocket ----------------------------------------------------------------
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await state.manager.connect(ws)
    try:
        await ws.send_text(json.dumps({"type": "state", "data": state.world.state_snapshot()}))
        while True:
            await ws.receive_text()  # keepalive / ignored client pings
    except WebSocketDisconnect:
        state.manager.disconnect(ws)
