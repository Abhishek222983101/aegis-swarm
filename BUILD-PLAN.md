# AEGIS — Deployable Prototype Build Plan
### Lean architecture + phase-by-phase plan to ship a real, live-linked, 3D, ML-backed prototype before the PPT round

This supersedes §5 of `SYSTEM-ARCHITECTURE.md` for actual execution. It keeps every PRD-mandated capability and every module from the original design — Mission Planner, trained Allocator, Risk/Escalation model, Supervisor loop, Simulation core, Decision log, 3D Cockpit — but collapses the number of *services* so an AI coding agent can build it fast, with minimal boilerplate/context-switching, and so it deploys as **one live public URL** you put directly in the PPT.

---

## 1. Why the stack changes (not the architecture)

The original doc's 4-language, 5-service design (§2) is the **correct answer to "how would this scale in production"** — keep that story for the slides and for Q&A, it's genuinely defensible and backed by real precedent. But building 5 services across 4 languages with gRPC contracts between them burns enormous agent time on plumbing (proto definitions, inter-service auth, 4 separate deploy targets) before a single pixel moves on screen — exactly the token/time cost you want to avoid before a deadline.

**The fix: same logical modules, fewer physical services.**

| Logical module (unchanged from SYSTEM-ARCHITECTURE.md §3) | Production version | **Prototype version (what we build)** |
|---|---|---|
| Simulation core | Rust, separate gRPC service | **Python, `asyncio` background task inside the same FastAPI process** — a dict of agent objects, ticked every ~150ms |
| Allocator (trained policy) | PyTorch → ONNX, called from Go | **PyTorch → ONNX, called in-process from FastAPI** via `onnxruntime` — same trained model, same ONNX export step, just no network hop |
| Risk/Escalation classifier | Separate model service | Small sklearn/PyTorch classifier, loaded in-process, same FastAPI app |
| Mission Planner (LLM) | Separate FastAPI service | Same process, a `/mission` route that calls an LLM API (Anthropic) with a strict JSON-schema response |
| Orchestrator / Supervisor loop | Go service | **Python, `asyncio` task** inside the same FastAPI process, consuming an in-memory event queue instead of a gRPC stream |
| WebSocket hub | Go + Redis pub/sub | **FastAPI's native WebSocket support**, broadcasting to an in-memory set of connected clients (Redis only added back if you need multi-instance scaling — not needed for a demo) |
| Decision log / persistence | PostgreSQL | **SQLite** (zero-config, file-based, still real SQL, still a real audit trail) |
| Frontend 3D Cockpit | React + R3F, worker + SharedArrayBuffer hot path | **Same** — React + R3F + Zustand. Skip the Worker/SharedArrayBuffer optimization for the prototype (only needed past ~50+ simultaneous agents; our demo runs 3-15) — note it in the doc as the "next optimization" so the Feasibility slide claim stays honest |

**Net result: one backend process (Python/FastAPI) + one frontend (Vite/React) = 2 things to build and deploy, not 5.** Same PRD coverage, same "real trained ML, not a wrapper" story, same live 3D interactive demo — just built in one language on the backend so the coding agent isn't context-switching between Rust/Go/Python/Protobuf all day.

**If there's time left after the core demo works**, Phase 6 below has an optional "harden toward production" step that peels the Allocator out into its own process — proving the architecture *can* decompose into the original polyglot design without a rewrite, which is itself a good thing to say live if a judge asks "so is this actually one monolith pretending to be microservices?" Answer: no — it's one deployable unit today, with clean internal module boundaries (separate Python modules, not just functions in one file) so it decomposes into the full design in §2-3 without restructuring, only extraction.

---

## 2. Deployment target (get the live link early, not at the end)

**Backend + Frontend together on Vercel, using Vercel Services** (one project, two sub-services routed by path — frontend owns `/`, FastAPI backend owns `/server/*`, same origin so no CORS pain, WebSocket works natively on Vercel's Python runtime). This is a documented, maintained pattern (Vercel's own FastAPI+WebSocket templates use exactly this setup) and gets you **one public URL for both the 3D UI and the live backend** with a single `vercel --prod`.

```
vercel.json
{
  "services": {
    "web": { "root": "frontend/", "framework": "vite" },
    "api": { "root": "backend/", "entrypoint": "app.main:app", "framework": "fastapi" }
  },
  "rewrites": [
    { "source": "/server/(.*)", "destination": { "service": "api" } },
    { "source": "/(.*)", "destination": { "service": "web" } }
  ]
}
```

- Frontend connects to `wss://<your-project>.vercel.app/server/ws` — same-origin, no CORS config needed.
- SQLite file persists per-deploy on Vercel's ephemeral filesystem — fine for a demo (resets on redeploy, which you won't do mid-demo). If you want persistence across redeploys, swap in a free-tier Postgres (Neon/Supabase) later — same SQLAlchemy models, one connection-string env var change, not a rewrite.
- Env vars needed: `ANTHROPIC_API_KEY` (Mission Planner LLM calls) — set in Vercel project settings, never committed.

**Deploy the skeleton on Day 1, before any real logic exists** (see Phase 0 below) — an empty "hello swarm" 3D scene live at a public URL on hour one means every subsequent phase is just `git push` → already deployed, never a last-minute deploy scramble, and you always have a live link to put in the PPT even if later phases run out of time.

---

## 3. Phase-by-Phase Build Plan

### Phase 0 — Skeleton + Live Link (do this first, budget: get it done fast)
**0.1** — `backend/`: minimal FastAPI app, one `/health` route, one `/ws` route that echoes a hardcoded JSON payload of 3 fake agents on a timer.
**0.2** — `frontend/`: Vite + React + TS + R3F scaffold, one `<Canvas>` with 3 colored boxes whose position updates from the `/ws` payload via a simple `useEffect` WebSocket client → Zustand store → `useFrame` read (no worker/SAB yet, keep it simple).
**0.3** — `vercel.json` as above, `vercel --prod`. **Confirm the live URL works end-to-end — 3 boxes moving, served publicly — before writing one more line of "real" logic.** This URL goes in the PPT today and stays valid as you keep shipping to it.
**0.4** — Agree the 3 demo scenarios now (Phase 6 below) so every subsequent phase builds toward the same end state.

### Phase 1 — Real Simulation Core (in-process)
**1.1** — `backend/app/sim/` module: `Agent` dataclass (id, type, **position as `(x, y, z)` — not `(x, y)`**, battery, status, current_task, comm_range), `World` class holding all agents + environment (obstacles, no-fly zones, weather enum). **This 3-axis position is the single most important modeling decision for the demo's visual appeal** — see the 3D Audit at the end of this phase list.
**1.2** — Three agent types per PRD's "heterogeneous" requirement: `ScoutDrone`, `HeavyRover`, `CommRelay` — differ in speed, battery drain rate, payload, comm range (exactly as specified in SYSTEM-ARCHITECTURE.md §3.1).
**1.3** — `asyncio` background task ticks the `World` every ~150ms (not 30Hz — this is Python in-process, ~7Hz tick is plenty smooth for a 3-15 agent demo and far cheaper on tokens/complexity than chasing a Rust-grade tick rate we don't need for a prototype this size).
**1.4** — Comm graph: simple distance-based (upgrade to raycast-vs-obstacles only if time allows) — who-can-hear-whom recomputed each tick.
**1.5** — Fault injection functions: `inject_battery_drain(agent_id)`, `inject_comm_loss(agent_id)`, `inject_route_block(zone)`, `inject_agent_failure(agent_id)`, `inject_weather_change(level)` — each is a plain Python function callable from a REST route, no gRPC needed since it's all one process.
**1.6** — Event queue: an `asyncio.Queue` that the tick loop pushes typed events onto (`BatteryCritical`, `CommLost`, `RouteBlocked`, `AgentFailure`, `WeatherChanged`, `TargetFound`) whenever a threshold crosses.
**1.7 — Comm-priority scheduler (PRD-explicit, don't skip).** The PRD separately asks the system to "reason about limited communication... determine which observations or data are important enough to transmit" — this is distinct from Phase 1.4's connectivity graph (which only answers *can* two agents talk). Model a small bandwidth budget per comm link (e.g. N messages/tick an agent can push through a degraded or relay-only connection) and a priority function over pending messages (`TargetFound` > `AgentFailure` > routine telemetry). When bandwidth is constrained, lower-priority messages queue or drop, and this is visible in the Decision Feed ("ScoutDrone-2: comm-constrained, deferred routine telemetry to prioritize TargetFound alert"). This is cheap to build (one priority queue + one config value) and directly answers a named PRD requirement that's otherwise easy to miss.
**Exit criteria:** hit the fault-injection REST routes with `curl`, watch the right events land in server logs, confirm a comm-constrained scenario visibly drops/defers low-priority messages, before touching ML or frontend.

### Phase 2 — Decision Layer (the real ML — start this early, it's the long pole)
**2.1** — Build a lightweight `gymnasium` environment wrapping the Phase 1 `World` (headless, no FastAPI, run standalone for fast training iteration).
**2.2** — **Baselines first** (cheap, fast, and they're your "proof we trained something real" comparison evidence): Greedy nearest-agent, Hungarian-algorithm optimal static assignment (`scipy.optimize.linear_sum_assignment`).
**2.3** — Train a small PPO policy (`stable-baselines3`, CPU-only is fine — matches the realistic constraint most teams will actually have) on the assignment task: reward = mission completion % − time penalty − agents-lost penalty. Keep the network small (2-3 hidden layers) — this trains in minutes on CPU, not hours, and a small-but-genuinely-trained policy beats a "we didn't actually train anything" fallback every time.
**2.4** — Log training curves (`reward vs. episode`) to a CSV/PNG — this screenshot goes straight on the Technical Approach slide.
**2.5** — Export the trained policy to ONNX (`torch.onnx.export`), load it in the FastAPI backend with `onnxruntime` — confirm inference is single-digit milliseconds, log this number.
**2.6** — Train the Risk/Escalation classifier: label rollouts from 2.3 where the chosen action led to a bad outcome as "should have escalated," train a small logistic-regression or 1-hidden-layer classifier on (comm quality, battery margin, obstacle density, policy confidence) → `should_escalate`. This is a second, separate, genuinely trained model — don't hardcode it as an if-statement, that's the exact "fake ML" trap to avoid.
**2.6b — Mission-level feasibility score (PRD-explicit, separate from 2.6).** The PRD distinguishes a single risky *decision* from the whole *mission* becoming unachievable — e.g. losing 2 of 3 agents mid-mission is a mission-feasibility event even if any single remaining reassignment looks individually "low risk." Add a lightweight aggregate score computed each tick from swarm-wide state (fraction of agents lost/degraded, fraction of mission tasks still coverable given remaining capability, comm-graph connectivity) — simple weighted formula is fine here, it doesn't need its own neural net, but it must be a distinct, visible number (`mission_feasibility: 0.0-1.0`) shown in the HUD, separate from any single agent's risk score, and it's what triggers a *mission-level* escalation ("recommend aborting Sector 7 sub-mission") rather than a per-task one.
**2.7** — Mission Planner route: `POST /mission` takes NL text, calls an LLM with a strict JSON-schema/tool-call response (task list + dependencies + priorities), with a template-based fallback decomposer if the API call fails or is rate-limited — **never let a live demo depend on an LLM call succeeding with no fallback.**

### Phase 3 — Supervisor Loop (wires Phase 1 + Phase 2 together)
**3.1** — `asyncio` task consuming the Phase 1.6 event queue: for each event, decide — routine event (battery/comm/route/failure) → call the Phase 2.5 ONNX Allocator; structural event (new high-priority target found) → call the Phase 2.7 Mission Planner. **The decision space must include four actions, not two**: reassign task, reposition (e.g. move a CommRelay to restore connectivity), escalate to human, and **terminate/abort** (drop a sub-mission or recall an agent entirely) — the PRD explicitly lists "terminate part of the mission" as a system action alongside reassign/reprioritize/reroute/reposition, and it's the one most teams forget because reassignment is the "interesting" case. Wire the Phase 2.6b mission-feasibility score to trigger `terminate` when it drops below a threshold — this also gives you a 4th, distinct demo moment (Phase 6.1-D below) that most competing teams won't have.
**3.2** — Every decision writes a row to SQLite (`decision_log` table: timestamp, trigger_event, decision, reasoning_text, confidence_score, escalated) **and** immediately pushes it onto the WebSocket broadcast — build logging and live-streaming together, not logging-then-bolt-on-streaming-later.
**3.3** — When the Risk classifier (2.6) returns `should_escalate=True`, pause that agent's reassignment, push an `escalation_pending` event to the frontend, wait for an operator response via a `POST /escalation/{id}/respond` route — with a sane timeout (e.g. 15s) that auto-resolves so a demo never hard-freezes if nobody clicks in time.

### Phase 4 — Cockpit (this is what judges actually watch)
**4.1** — Replace Phase 0's hardcoded payload with the real WebSocket stream of `World` state (positions, battery, status, comm links) at the Phase 1.3 tick rate.
**4.2** — Swap boxes for free low-poly glTF models (drone/rover/tower), color-coded by status (green/yellow/red), loaded via `useLoader` (cached, per R3F best practice — never reload per-frame).
**4.3** — Comm-link lines between agents in range (simple `Line` components, dim/break visually on comm loss).
**4.4** — **Scenario Injector panel** — buttons/click targets wired directly to the Phase 1.5 fault-injection REST routes. This is the judge's toy; make it obvious and satisfying to click.
**4.5** — **Decision Feed panel** — scrolling list rendered from the WebSocket decision-log stream, human-readable sentence template per decision type (e.g. *"ScoutDrone-3 battery critical (18%) → reassigned to HeavyRover-1 → confidence 0.91"*).
**4.6** — **Escalation Console** — modal that appears on `escalation_pending`, Approve/Override buttons calling the Phase 3.3 route.
**4.7** — HUD: mission status bar, per-agent cards (battery/status/task) — plain React components reading from Zustand, re-rendering a few times/sec is fine at this scale.
**4.8 (only if time remains)** — Move the WebSocket connection into a Web Worker and switch position updates to a `SharedArrayBuffer` read in `useFrame`, per the original Tier-A pattern — do this only if you push past ~30 agents and start seeing frame drops; don't pre-optimize before you've measured a real problem.

**4.9 — 3D Audit (do this explicitly, don't assume R3F = 3D).** Building the frontend in React Three Fiber does not automatically make the demo *read* as 3D — if every agent sits at the same Z and the camera looks straight down, it's a 2D scene rendered through a 3D library, and a judge will clock that in five seconds. Concrete checklist, all required:
  - **Altitude is real and varies.** ScoutDrones fly at a meaningfully different Z than HeavyRovers (ground-level) and CommRelays (fixed mid-altitude or elevated terrain points) — this falls directly out of Phase 1.1's `(x,y,z)` position, but confirm it's actually *used*, not just carried as a dead field.
  - **Camera is NOT top-down.** Use an orbit/perspective camera at an angle (`@react-three/drei`'s `OrbitControls` with an initial elevation, not a locked overhead view) so altitude differences are visually obvious — a drone hovering above a rover only reads as "above" if the camera angle lets you see the gap.
  - **A ground plane or terrain mesh is present** as a visual reference frame — without one, floating agents have no depth cue and altitude differences look arbitrary rather than meaningful.
  - **Vertical motion is visible during replanning** — when a CommRelay repositions (Phase 1.7/comm scenario) or a drone changes altitude to avoid an obstacle, that should visibly move it up/down, not just across — this is a cheap, free "wow" moment that pure top-down dashboards (what most competing teams will default to) structurally cannot show.
  - **Shadows or a simple ground-contact indicator** (even a basic drop-shadow circle under each airborne agent) make altitude readable at a glance without requiring the judge to study the camera angle carefully.
  This is a ~30-minute pass once Phase 4.2's models are in, but it's the difference between "we used a 3D library" and "this is visibly, usefully 3D" — which is the entire basis of the visual-appeal argument for picking this PS over the disaster-relief one.

### Phase 5 — Mission Intake UX
**5.1** — A simple text input + "Launch Mission" button that `POST`s to `/mission`, shows the returned task DAG as a small readable list/graph before the swarm starts executing it — this is what makes "natural language → coordinated plan" visible and understandable to a judge instead of implicit.

### Phase 6 — Demo Scenarios, Benchmarking, Hardening (do not skip this phase)
**6.1** — Script and rehearse exactly 3 scenarios (same three as the original plan, now running on the lean stack):
  - *A — Battery-critical reassignment*: trigger low battery on a ScoutDrone, watch the trained Allocator reassign in real time, Decision Feed explains why.
  - *B — Comm loss + relay repositioning*: break comm between two agents, watch the system route around it, comm-link lines visibly reconnect.
  - *C — Structural replan via Planner*: inject "high-priority target found," watch it go to the LLM Planner (not the fast Allocator), restructures the task DAG, triggers an Escalation if risk is high.
  - *D — Route block + mission-level abort*: block a route AND fail an agent in quick succession so the Phase 2.6b feasibility score drops — watch the Supervisor choose `terminate` for the now-infeasible sub-mission instead of endlessly trying to reassign, with the Decision Feed explaining *why it gave up on that sub-goal* rather than just reshuffling forever. This closes the PRD's 5th fault type (route-blocked was previously only a backend function, not a rehearsed scenario) and is the single best demo moment for "mission-level reasoning, not just task reassignment" — the exact framing the PRD asks you to prove.
**6.2** — **Baseline comparison run**: same scenario, Greedy vs. Hungarian vs. Trained policy, capture completion-rate/time numbers — your hard evidence slide, and proof the training (Phase 2) was real.
**6.3** — **Demo-safety replay buffer**: keep a rolling in-memory list of the last ~60 seconds of broadcast messages; add a `/replay` mode the frontend can switch to if live WiFi drops on stage — same "cached mode" pattern used in production multi-agent demo systems, so a network hiccup never kills the presentation.
**6.4** — Stress test: push to 10-15 agents, confirm the frontend stays smooth, screenshot the frame counter for the Feasibility slide.
**6.5** — Final timed rehearsal, someone else operating the Scenario Injector cold, no hints — catch anything non-obvious before a judge does.

### Phase 6.5 (optional, only if ahead of schedule) — Prove the decomposition story
Extract the Allocator into its own small FastAPI process, call it over HTTP instead of in-process, deploy it as a second Vercel service. Costs almost nothing since the module boundary was already clean (Phase 1-2 kept the sim/ML code in separate Python modules, not tangled into route handlers) — and it's a genuinely strong live answer to "prove this isn't just a monolith" if a judge pushes on it.

---

## 4. What to capture for the PPT (same table as SYSTEM-ARCHITECTURE.md §6, now with the lean stack's real numbers)

| Metric | Captured in | Slide |
|---|---|---|
| **Live demo URL** | Phase 0.3 — put this directly under the abstract on the Title slide and again on Feasibility | Title / Feasibility |
| Allocator inference latency (ms, ONNX, in-process) | Phase 2.5 | Feasibility |
| Event→replan visible latency on stage | Phase 6.1 | Technical Approach / Feasibility |
| Mission completion % — Greedy vs Hungarian vs Trained | Phase 6.2 | Innovation / Feasibility |
| Max agents sustained smoothly in the 3D cockpit | Phase 6.4 | Feasibility |
| Training reward curve | Phase 2.4 | Technical Approach |

---

## 5. One-line answer if a judge asks "why not Rust/Go like the architecture doc says?"

> "The full design decomposes cleanly into Rust/Go microservices for production scale — we documented that path — but for the prototype we built the same modules as clean, separately-bounded components in one deployable service, specifically so we could ship a live, working link instead of a slide. That's the only trade we made, nothing architectural changed, only the deployment unit."

This is true, and it's a better answer than hand-waving — judges reward "we made a deliberate, explainable engineering trade-off" far more than "we built the maximally impressive-sounding stack and it doesn't quite run."
