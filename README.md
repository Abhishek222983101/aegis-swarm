<div align="center">

# 🛡️ AEGIS
### Autonomous Swarm Mission Orchestration Platform

**A heterogeneous drone/rover/relay swarm that plans, replans, and defends its own mission — live, in 3D, with a human operator in the loop.**

[![Live Demo](https://img.shields.io/badge/🔴_LIVE_DEMO-elevate--swarm--orchestration.vercel.app-2ea44f?style=for-the-badge)](https://elevate-swarm-orchestration.vercel.app)

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://python.org)
[![PyTorch](https://img.shields.io/badge/PyTorch_%E2%86%92_ONNX-trained_policy-EE4C2C?logo=pytorch&logoColor=white)](https://pytorch.org)
[![React Three Fiber](https://img.shields.io/badge/React_Three_Fiber-3D_cockpit-61DAFB?logo=react&logoColor=white)](https://docs.pmnd.rs/react-three-fiber)
[![Tests](https://img.shields.io/badge/tests-101%2F101_passing-brightgreen)](backend/tests/)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache_2.0-informational)](#-license)

</div>

---

## 📋 At a glance

| | |
|---|---|
| **Problem Statement** | EL-05 — *"AI-Powered Autonomous Robot & Drone Swarm Mission Orchestration"* |
| **Hackathon** | ELEVATE 1.0, Dwarkadas J. Sanghvi College of Engineering (with NSDC) |
| **Live demo** | **https://elevate-swarm-orchestration.vercel.app** ← open this first |
| **Repo** | https://github.com/Abhishek222983101/aegis-swarm |
| **Tests** | 101/101 passing (`backend/tests/`) |

---

## 💡 The idea, in 20 seconds

Give AEGIS a mission in plain English — *"Scout Sector 7 and establish a comm relay"* — and it decomposes that into tasks, assigns them across a heterogeneous swarm (drones, a rover, a comm relay), and then **keeps the mission alive as things go wrong**: an agent's battery dies, it loses communication, a route gets blocked, a higher-priority target shows up mid-mission. A trained ML allocation policy and a trained risk classifier decide what to do about each event in real time — reassign, reposition, escalate to a human, or terminate a sub-mission that's no longer achievable — and every single decision is logged with a human-readable reason you can watch live in the 3D cockpit.

## 🎯 The problem we were asked to solve

> Design an intelligent mission-planning and orchestration platform capable of coordinating a heterogeneous swarm of autonomous robots and drones to accomplish complex missions in dynamic, infrastructure-constrained environments. The system should accept a high-level mission objective and transform it into an executable multi-agent plan — determining task decomposition, agent assignment, sequencing, and how routes, energy, payload, communication, and risk are managed collectively. Beyond initial planning, it must continuously monitor the swarm and environment, dynamically re-plan on new information or unexpected events (battery depletion, communication loss, blocked routes, agent failure, high-priority discoveries), reason about limited communication bandwidth, and escalate to a human operator when autonomous confidence is insufficient. **The objective is to demonstrate mission-level autonomy and swarm coordination — not an isolated capability like object detection or obstacle avoidance.** — *paraphrased from the official EL-05 brief*

---

## ✅ Every PS requirement — where to check it, live

| # | PS asked for | We built | Proof — check it yourself |
|---|---|---|---|
| 1 | High-level NL objective → executable multi-agent plan | **Mission Planner**: template-based NL decomposer (LLM-upgradeable) turns an objective into a task DAG, then dispatches it through the same Allocator used for live replanning | Type a mission in the UI, hit LAUNCH MISSION — watch agents move within ~1s. [`backend/app/ml/planner.py`](backend/app/ml/planner.py) |
| 2 | Dynamic task/resource allocation by capability, battery, risk, priority | **Allocation Engine**: trained PPO policy (PyTorch → ONNX), with a **hard capability constraint** (logit-masked, not just hoped-for) so it can never assign the wrong agent type | [`backend/app/ml/inference.py`](backend/app/ml/inference.py), [`backend/app/ml/env.py`](backend/app/ml/env.py) |
| 3 | Continuous re-planning on failures, obstacles, new info, changing priorities | **Supervisor Loop**: 4-action decision space — reassign / reposition / escalate / **terminate** — routes every typed event live | Click any Scenario Injector button, watch Decision Feed react in <1s. [`backend/app/supervisor.py`](backend/app/supervisor.py) |
| 4 | Specific triggers: battery, comm loss, blocked route, agent failure, weather, high-priority target | All 5 fault types implemented as real simulation events, not scripted animations | [`backend/app/sim/faults.py`](backend/app/sim/faults.py) — verified live: [`backend/scripts/demo_scenarios.py`](backend/scripts/demo_scenarios.py) |
| 5 | Reason about limited communication — what's worth transmitting | **Comm-priority scheduler**: per-agent bandwidth budget, priority queue (`TARGET_FOUND` > `AGENT_FAILURE` > routine telemetry), overflow drops lowest-priority first | [`backend/app/sim/comms.py`](backend/app/sim/comms.py) |
| 6 | Identify when the *mission* (not just one task) is no longer achievable | **Mission-feasibility score**: explainable weighted aggregate (agent health + task-type coverage + comm connectivity) — triggers `terminate`, not endless reassignment attempts | [`backend/app/ml/feasibility.py`](backend/app/ml/feasibility.py) |
| 7 | Escalate to a human when autonomous confidence is low | **Trained risk/escalation classifier** (scikit-learn, 91.2% held-out accuracy) + live Escalation Console with Approve/Override and an auto-resolving timeout so a demo never hard-freezes | [`backend/app/ml/risk_model.py`](backend/app/ml/risk_model.py) |
| 8 | Explanations for every major autonomous decision | **Decision Feed + append-only SQLite ledger** — every decision carries a human-readable reasoning string, queryable live at `/server/ledger` | Try it: `curl https://elevate-swarm-orchestration.vercel.app/server/ledger` |
| 9 | ≥3 heterogeneous agents, distinct capabilities/constraints | `ScoutDrone` (fast, short-range, low battery capacity), `HeavyRover` (slow, high payload), `CommRelay` (stationary-ish, long range) — genuinely different speed/battery/comm-range profiles | [`backend/app/sim/entities.py`](backend/app/sim/entities.py) |
| 10 | Demonstrate mission-level autonomy, not isolated capabilities | No object-detection/SLAM/obstacle-avoidance scope creep — every decision is at the task-assignment/replanning level, exactly as scoped | See Decision Feed reasoning text in the live demo |

**Full line-by-line traceability table (PRD text → module → file):** [`SYSTEM-ARCHITECTURE.md` §1](SYSTEM-ARCHITECTURE.md#1-prd--system-mapping-traceability)

---

## 🚀 Try it live — 2 minutes, no install

### **[👉 Open elevate-swarm-orchestration.vercel.app](https://elevate-swarm-orchestration.vercel.app)**

The app has an in-UI **"? HOW TO TEST THIS"** button (top-right) with 6 numbered step cards — but here's the short version:

1. **Look at the 3D view** — 2 drones floating above a rover, a relay mast, all on a dark grid. Drag to orbit, scroll to zoom. Use the camera toolbar (top-left of the 3D panel) if you lose track: **RESET VIEW**, **TOP-DOWN**, or **FOLLOW SELECTED AGENT**.
2. **Click a mission template** (bottom-left panel) — e.g. "Scout + Relay" — or type your own, then **LAUNCH MISSION**. Agents start moving within ~1 second.
3. **Click an agent** in SWARM STATUS (top-left) to select it, then try any **SCENARIO INJECTOR** button (top-right): DRAIN BATTERY, CUT COMMS, FAIL AGENT, BLOCK ROUTE, SEVERE WEATHER, TARGET FOUND. Watch **DECISION FEED** (bottom-right) explain the system's reaction, live.
4. **Keep failing agents** — eventually a **HUMAN ESCALATION REQUIRED** banner appears (approve/override it), and if the mission becomes genuinely unachievable, a **TERMINATE** decision fires — the mission-feasibility logic, not a scripted ending.
5. **Broke it on purpose?** Click **↺ RESET SIMULATION** (top-right of the header) — fresh, fully-healthy swarm in under a second, no page reload needed.
6. **WiFi flaky?** The **⟲ REPLAY (DEMO SAFETY)** toggle replays the last ~60 seconds of real captured state from the backend's rolling buffer — a genuine demo-safety fallback, not a canned animation.

**Cross-verify it's real, not a mockup** — hit the API directly:
```bash
curl https://elevate-swarm-orchestration.vercel.app/server/health
curl https://elevate-swarm-orchestration.vercel.app/server/state
curl https://elevate-swarm-orchestration.vercel.app/server/ledger
curl -X POST https://elevate-swarm-orchestration.vercel.app/server/inject/target-found \
  -H "Content-Type: application/json" -d '{"x":200,"y":200}'
```

---

## 📊 Results — the numbers, not just the claim

Every number below comes from a committed script against the committed model files — nothing is hand-typed. Reproduce them yourself: `python -m app.ml.train` (see [Run it yourself](#-run-it-yourself)).

#### Training — the policy genuinely learns

| | Episode 0–500 (untrained) | Episode 37,000–37,504 (converged) |
|---|:---:|:---:|
| Mean episode reward | **−6.32** | **+6.82** |

300,000 timesteps, 37,504 episodes, PPO (`stable-baselines3`), ~2 minutes on CPU. Full curve: [`backend/models/training_curve.csv`](backend/models/training_curve.csv).

#### Allocator vs. classical baselines — the honest comparison

| | Greedy | Hungarian (optimal) | **Trained PPO policy** |
|---|:---:|:---:|:---:|
| Mean objective reward (30 trials, same blended objective all three solve) | 7.75 | 7.75 | **6.90** |
| Capability mismatches | 0 | 0 | **0** (hard-constrained) |
| Inference latency | — | — | **0.016ms/decision** |

**We're reporting this straight: the trained policy does not yet beat the classical baselines on our benchmark.** It genuinely learns (see the reward curve above) and runs correctly in production with a hard capability constraint and automatic fallback outside its trained envelope — but outperforming a well-tuned Hungarian-optimal baseline on a small, well-specified allocation problem is a real bar, and we're not claiming to have cleared it. Full methodology, including two real bugs we found and fixed in our own benchmark script before trusting these numbers: [`backend/models/baseline_comparison.json`](backend/models/baseline_comparison.json) and the commit history of [`backend/app/ml/train.py`](backend/app/ml/train.py).

#### System performance (measured, not estimated)

| Metric | Value |
|---|---|
| Allocator inference | 0.016ms average (500-call local benchmark) |
| End-to-end decision latency, live production, public internet | ~300ms average |
| Stress test | 4 → 24 heterogeneous agents, tick compute stayed under 0.5ms average |
| Risk/escalation classifier | 91.2% held-out accuracy |
| All 4 PRD fault scenarios | Verified passing live against the production URL (not just localhost, not just unit tests) |

---

## 🏗️ How it works

```
Operator (3D Cockpit, React Three Fiber)
        │  mission objective / fault injection clicks
        ▼
FastAPI Supervisor  ──────────────────────────────────────┐
        │  routes every typed event                       │
        ▼                                                  │
   ┌─────────────┬──────────────────┬────────────────┐     │
   │  Allocator  │  Risk Classifier │  Feasibility    │     │
   │ (PPO→ONNX,  │  (scikit-learn,  │  Scorer         │     │
   │  hard-       │   trained)       │  (explainable   │     │
   │  constrained)│                  │   aggregate)    │     │
   └─────────────┴──────────────────┴────────────────┘     │
        │  reassign / reposition / escalate / terminate    │
        ▼                                                  │
Simulation Core (tick loop, comm graph, fault injection) ◄──┘
        │  live state @ ~2Hz
        ▼
WebSocket → 3D Cockpit + Decision Feed + SQLite ledger (audit trail)
```

**Deliberate architecture decision, stated plainly:** the system was originally designed as 5 polyglot microservices (Rust simulation core, Go orchestrator, Redis fan-out, PostgreSQL — full design in [`SYSTEM-ARCHITECTURE.md`](SYSTEM-ARCHITECTURE.md)) for production scale, then *intentionally collapsed* into one lean, fast-to-build, torch-free-at-runtime Python service for this hackathon — same module boundaries, same decision logic, just one deployable unit instead of five, so we could ship something **live and working** instead of a slide. The module boundaries were kept clean specifically so it decomposes into the original design without a rewrite — only extraction. Full reasoning: [`BUILD-PLAN.md` §1](BUILD-PLAN.md#1-why-the-stack-changes-not-the-architecture).

**Nothing here is a mock or a stub:** the allocation policy is a real PyTorch PPO network trained from scratch and exported to ONNX; the risk classifier is a real trained scikit-learn model (not an if-statement, even though a simpler rule could have faked the behavior); the simulation core runs real tick-by-tick physics (battery drain, distance-based comm graph, position interpolation); the decision ledger is a real append-only SQLite audit trail you can query over the API right now.

## 🛠️ Tech stack

`Python 3.11` `FastAPI` `PyTorch → ONNX Runtime` `scikit-learn` `SQLite` `React 19` `TypeScript` `React Three Fiber (Three.js)` `Zustand` `Tailwind CSS v4` · deployed on `Vercel Services` (single project, frontend + backend, one public URL)

---

## 💻 Run it yourself

```bash
git clone https://github.com/Abhishek222983101/aegis-swarm.git
cd aegis-swarm

# Backend
cd backend
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt          # lean runtime deps (torch-free, ~491MB)
.venv/bin/uvicorn app.main:app --port 8731          # http://localhost:8731

# Frontend (separate terminal)
cd frontend
npm install
npm run dev -- --port 5180                          # http://localhost:5180
```

The committed [`backend/models/allocator_policy.onnx`](backend/models/allocator_policy.onnx) and [`backend/models/risk_classifier.joblib`](backend/models/risk_classifier.joblib) mean the trained models work immediately — no training step required to run the app.

**Reproduce every ML number in this README from scratch:**
```bash
cd backend
.venv/bin/pip install -r requirements-ml.txt        # adds torch, stable-baselines3, gymnasium (training-only)
.venv/bin/python -m app.ml.train                    # ~2.5 min on CPU: trains policy, exports ONNX, runs the benchmark
.venv/bin/python -m app.ml.risk_model                # trains the risk classifier
```

**Run the full test suite (101 tests):**
```bash
cd backend
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -v
```

**Run the live demo-scenario rehearsal script** (exercises all 4 PRD fault scenarios against a real running server, local or production):
```bash
cd backend
.venv/bin/python scripts/demo_scenarios.py                                       # against localhost:8731
.venv/bin/python scripts/demo_scenarios.py https://elevate-swarm-orchestration.vercel.app/server  # against production
```

**Run the stress test** (4 → 24 agents, measures tick compute scaling):
```bash
cd backend
PYTHONPATH=. .venv/bin/python scripts/stress_test.py
```

---

## 📁 Project structure

```
backend/
  app/
    sim/            simulation core — agents, world tick loop, comm graph, fault injection
    ml/              trained models — PPO allocator, risk classifier, mission planner, baselines
    supervisor.py    the decision brain — routes events to reassign/reposition/escalate/terminate
    ledger.py        append-only SQLite decision audit trail
    main.py          FastAPI app — WebSocket, REST, scenario injection, mission intake, reset
  tests/             101 tests — every module has real, non-trivial unit + integration tests
  scripts/           live demo-scenario rehearsal + stress test (run against a real server)
  models/            committed trained model weights (ONNX + joblib) — ready to run, no training needed
frontend/
  src/
    components/      3D cockpit, HUD, Scenario Injector, Decision Feed, Escalation Console, Mission Intake
    components/agents/  procedural drone/rover/relay 3D models (no external assets, zero licensing risk)
    lib/             WebSocket client, REST API client, shared 3D coordinate mapping
    store.ts         Zustand state store
SYSTEM-ARCHITECTURE.md   full target architecture, PRD traceability table, architecture diagram
BUILD-PLAN.md            the actual phase-by-phase build plan this was built from
PPT-CONTENT-PLAN.md      slide-by-slide pitch deck content, mapped to the hackathon's own template
vercel.json              Vercel Services config (frontend + backend, one deployment)
```

## 📚 Deep-dive documentation

| Doc | What's in it |
|---|---|
| [**SYSTEM-ARCHITECTURE.md**](SYSTEM-ARCHITECTURE.md) | Full target architecture, PRD → module traceability table, Mermaid architecture diagram, module-by-module design rationale |
| [**BUILD-PLAN.md**](BUILD-PLAN.md) | The literal phase-by-phase, sub-phase-by-sub-phase plan this system was built from — and why the deployed stack differs from the documented target architecture |
| [**PPT-CONTENT-PLAN.md**](PPT-CONTENT-PLAN.md) | Slide-by-slide pitch content mapped to the hackathon's own template, with every number sourced from this repo's own benchmark files |

---

## 🏆 Honest engineering log — what we found and fixed

In the spirit of not hiding anything: this system went through real debugging, not a clean first pass. A sample of what we caught and fixed along the way (full history in `git log`):

- A reward-function design flaw meant the trained policy had almost no incentive to differ from a simple nearest-agent heuristic — distance dominated the reward ~9x more than battery health. Fixed by steepening the battery penalty and widening battery variance in training scenarios.
- The ONNX model has a *fixed* input size matching its training-time agent count. The first version crashed whenever the live candidate pool shrank below that — which happens constantly, since that's exactly what a fault-injection scenario does. Fixed with a safe per-task fallback to the Hungarian baseline.
- The trained policy occasionally picked the wrong agent *type* for a capability-restricted task (a rover for a scout-only job). Fixed with a hard logit mask, not a hope that training would eventually prevent it — verified with a 50-trial regression test showing zero violations.
- Our own benchmark script had a bug that manufactured fake "capability mismatches" by defaulting to agent-0 whenever the Allocator correctly declined an unassignable task. Found before trusting the number, not after.
- Launching a mission used to do *nothing* — the task list displayed, but no agent ever moved. Found during live rehearsal, not a unit test, and fixed so mission launch uses the exact same dispatch path as live fault reassignment.
- Deploying to Vercel initially 500'd on every fault-injection request — the SQLite ledger tried writing next to the app code, which is read-only on a serverless filesystem. Fixed by defaulting to `/tmp`.

---

## 👥 Team

Built for **ELEVATE 1.0**, Dwarkadas J. Sanghvi College of Engineering.

## 📄 License

Apache 2.0 (see [`LICENSE`](LICENSE)).
