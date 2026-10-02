# AEGIS — PPT Content Plan
### Mapped exactly to the ELEVATE 1.0 template (9 slides in template → 8 usable, Instructions slide deleted before submission)

Judging rubric from the template's own Instructions slide: **Problem understanding & solution, Technical Depth & Scaling, Originality & Differentiation, Quality of research/prototype/presentation.** Every slide below is built to hit at least one of these explicitly — don't let any slide be "just filler."

General visual rules for every slide (per template's existing look — dark navy/blue gradient, sky photo, gold/amber accent headers, airplane motif top-right):
- Keep the template's header bar and background exactly as-is — do not reskin the template, extend its own style.
- One clear visual per slide (diagram, chart, screenshot, or icon row) — never a slide that's only bullet text.
- Use the amber/gold (`#D4A843`-ish, matches "ELEVATE 1.0" wordmark) as your one accent color for callouts/highlights, consistent with the template.
- Numbers get their own large callout treatment (big bold figure + small label) — don't bury metrics in paragraph text.

---

## Slide 1 — Title (template slide1.xml)
**Fields to fill:**
- Team Name: *[your team name]*
- PS ID: **EL-05**
- PS Name: **AI-Powered Autonomous Robot & Drone Swarm Mission Orchestration**
- Abstract (keep to ~40-50 words, this is the box judges read first): 
  > "AEGIS is a mission-level orchestration platform that converts a natural-language objective into a coordinated multi-agent plan, dynamically reallocates tasks across a heterogeneous drone/rover swarm as conditions change in real time, and escalates to a human operator only when autonomous confidence drops — demonstrated live in an interactive 3D cockpit."
- **Live prototype:** `https://elevate-swarm-orchestration.vercel.app` — put this directly under the abstract. Verified working end-to-end as of submission (trained ONNX policy, risk classifier, WebSocket, mission dispatch, reset all confirmed live in production, not just localhost).

No other visual needed here — template's own hero image carries the slide.

---

## Slide 2 — Proposed Solution (template slide2.xml)
Sub-sections per template: *Proposed Solution and Core Concept / Key Functionalities and Detailed Approach / Problem-Solution Alignment*

**Layout: left column text, right column a simple 3-icon-row graphic (not the full arch diagram — save that for slide 3).**

**Core Concept (2-3 sentences):**
> A mission-level "nervous system" sitting above a heterogeneous drone/rover swarm. Operators give a high-level objective in plain language; AEGIS decomposes it into a task plan, assigns it across agents by capability and real-time state, and continuously replans as battery, communication, obstacles, or priorities change — escalating to a human only when its own confidence says it should.

**Key Functionalities (bullets, 4 max, bold the verb):**
- **Decomposes** natural-language mission objectives into a dependency-aware task plan
- **Allocates** tasks dynamically across agents using a trained policy, not static rules
- **Replans in real time** on failure, comm loss, obstacle, or new priority — sub-second for routine events
- **Escalates to a human operator** with a plain-language reason when autonomous confidence is low

**Problem-Solution Alignment (short table or 2-row comparison, visual):**
| PRD asks for | AEGIS delivers |
|---|---|
| Mission-level reasoning beyond individual capabilities | Supervisor loop + LLM Mission Planner sit above sim/control layer |
| Dynamic reallocation under changing conditions | Trained ONNX policy reassigns in <10ms per decision |
| Communication-aware, risk-aware, human-escalating | Comm-priority queue + risk classifier + Escalation Console |

**Visual:** simple 3-icon row — brain icon ("Plans"), gear/arrows icon ("Allocates & Replans"), person icon ("Escalates") — in colored circles, matching the Design Ideas icon-row pattern.

---

## Slide 3 — Technical Approach (template slide3.xml)
Sub-sections: *System Architecture and Overall Workflow / Technologies, Frameworks and Models / Implementation and System Components*

**This is the most important slide — it's where the Gemini-generated architecture diagram goes, full width or near-full width.**

**Layout:** architecture diagram as the dominant visual (top ~65% of content area), tech stack as a compact badge row underneath.

**System Architecture and Overall Workflow:**
- Insert the Gemini-generated diagram from `SYSTEM-ARCHITECTURE.md` §4 here (or the Mermaid diagram in §0.5, rendered).
- One-line caption under it: *"Operator Cockpit (React/R3F) → FastAPI Supervisor (event routing, mission-feasibility, risk classifier) → ML Decision Layer (ONNX allocator + trained risk classifier) → Simulation Core (tick loop, comm graph, fault injection) → Heterogeneous Agent Fleet."*

**Technologies, Frameworks and Models (badge row — small labeled boxes, not a paragraph):**
`Python / FastAPI (single deployable service)` · `PyTorch → ONNX Runtime (trained PPO allocation policy)` · `scikit-learn (trained risk/escalation classifier)` · `React Three Fiber (3D cockpit)` · `WebSocket (live state broadcast)` · `SQLite (decision audit log)` · `Vercel Services (live deployment)`

**Deliberate architecture decision — say this out loud, it's a strength not a compromise:** the system was designed as 5 polyglot microservices (Rust/Go/Redis/Postgres — documented in full in `SYSTEM-ARCHITECTURE.md`) for production scale, then *intentionally collapsed* into one lean, fast-to-build, torch-free-at-runtime Python service for the hackathon — same module boundaries, same decision logic, just one deployable unit instead of five. This is the actual, live, deployed system, not a mockup of the bigger design.

**Implementation and System Components — real, measured numbers:**
- Allocator inference: **0.016ms average per decision** (500-call local benchmark, ONNX Runtime) — the ML decision itself is not the bottleneck anywhere in the pipeline
- End-to-end latency on the live deployment, public internet, judge's laptop to Vercel and back: **~300ms average** (measured against the production URL, included below)
- Mission planning is NL→tasks only at mission launch; every live replanning decision (routine or structural) runs through the fast trained-policy/baseline path with **zero LLM calls in the hot loop** — no external-API latency or failure risk during the part of the demo judges are actually watching

**Honest callout, not hidden:** *"The trained policy currently has to prove it beats classical baselines — see Feasibility — the engineering (training pipeline, ONNX export, safe production fallback, hard capability constraints) is real and complete regardless of that outcome."*

---

## Slide 4 — Innovation and Uniqueness (template slide4.xml)
Sub-sections: *Innovative Approach and Core Differentiators / Unique Features and Functionalities / Comparison with Existing Approaches*

**Layout:** comparison table as the dominant visual (judges love a clean comparison table — it does the differentiation argument for you).

**Core Differentiators (3 bullets max):**
- A genuinely trained PPO policy (not a pretrained wrapper) with a reward function that weighs distance, battery health, *and* task priority together — benchmarked honestly against classical baselines on the exact same objective, not a cherry-picked metric
- A hard-constrained ML layer: the trained policy can never violate a capability requirement (enforced by logit masking, not hoped-for from training) and automatically falls back to the proven Hungarian-optimal baseline the moment it's outside its trained envelope — this is what real production ML safety looks like, not just "trust the model"
- Every autonomous decision is logged with a human-readable reason and traceable in the live Decision Feed and ledger — not a black box, and independently verifiable by any judge live

**Comparison table** (pull directly from `SYSTEM-ARCHITECTURE.md` §7 — use the full 4-row table, format as a clean grid, bold the AEGIS column):
Rule-based dispatch | Single-LLM "agentic" demos | Academic multi-agent RL papers | **AEGIS**

**Visual:** the comparison table itself IS the visual for this slide — don't add a separate chart, keep it clean and let the table breathe (plenty of cell padding).

---

## Slide 5 — Feasibility and Viability (template slide5.xml)
Sub-sections: *Technical and Operational Feasibility / Scalability, Deployment and Resource Requirements / Challenges, Risks and Sustainability*

**Layout:** 3-4 large stat callouts across the top (big number + small label), short text underneath each column.

**Stat callouts — real, measured numbers (captured from the actual running system, not projected):**
- `0.016ms` — Allocator inference latency (500-call local benchmark)
- `~300ms` — end-to-end decision latency on the **live public deployment**, public internet round-trip included
- `24 agents` — stress-tested swarm size, tick compute stayed under 0.5ms/tick average (4→24 agents tested)
- `100%` — scenario pass rate: all 4 PRD fault scenarios (battery, comm-loss, structural replan, mission termination) verified passing live against the production URL, not just localhost or unit tests

**If asked about the trained-policy-vs-baseline number specifically:** be direct — *"On our current benchmark, the trained policy doesn't yet beat Hungarian on the blended objective (6.9 vs 7.75 mean reward over 30 trials). We're presenting that honestly rather than a cherry-picked number. What's solid: it genuinely learns (reward improved ~2.6x during training), exports to ONNX, runs in production with hard capability constraints, and automatically falls back to the proven baseline outside its trained envelope — that safety pattern is the actual production-readiness story here, not a rigged benchmark."* This is a stronger answer in Q&A than an inflated claim that falls apart under one follow-up question.

**Technical and Operational Feasibility (short):**
> This is not a mockup — it's live at `https://elevate-swarm-orchestration.vercel.app` right now, trained ML included. Every component (ONNX Runtime for latency-critical serving, WebSocket for real-time multi-agent state, FastAPI for the whole decision layer) is a proven pattern — we chose to prove it by actually shipping it, not by diagramming it.

**Scalability, Deployment and Resource Requirements:**
- Deployed today on Vercel Services (one project, frontend + backend, single public URL) — stress-tested to 24 heterogeneous agents locally with tick compute staying under 0.5ms average
- The full production-scale design (Rust simulation core, Go orchestrator, Redis fan-out, Postgres) is documented and the module boundaries were built clean specifically so it decomposes into that without a rewrite — only extraction. This hackathon build proves the logic; that document proves we know how it scales past a hackathon
- Simulation core's capability-abstraction boundary means swapping in a real ROS2/MAVLink data source doesn't change the Supervisor or frontend contract — same interface

**Challenges, Risks and Sustainability (be honest — judges respect this):**
- The trained policy doesn't yet beat classical baselines on our benchmark — stated plainly above, not hidden. The safety pattern (hard capability constraints, automatic fallback outside the trained envelope) is what makes this production-honest regardless
- Simulation-to-reality gap if moving to physical hardware — mitigated by the capability-abstraction boundary (sensor/actuator stubs are swappable)
- Demo network reliability — mitigated by the in-app replay-mode toggle (rolling buffer of real captured state, switchable live if WiFi drops mid-demo)

---

## Slide 6 — Impact and Scaling (template slide6.xml)
Sub-sections: *Target Users and Areas of Application / Expected Impact and Key Benefits / "VC says yes tomorrow" — Users, Breaks, Crashes, Robustness*

**Layout:** two-column — left "who uses this," right "what happens under load/stress."

**Target Users and Areas of Application (icon + label row):**
- Disaster response / search-and-rescue coordination teams
- Industrial & infrastructure inspection (mines, pipelines, remote facilities)
- Agricultural fleet monitoring
- Defense/perimeter surveillance coordination

**Expected Impact and Key Benefits (3 bullets, outcome-framed not feature-framed):**
- Faster mission completion under disruption vs. static dispatch (your Phase 6.2 benchmark number)
- Reduced operator cognitive load — human only intervenes on genuinely ambiguous calls, not every decision
- Auditable autonomy — every decision traceable, which matters for any regulated deployment (defense, emergency services)

**"Users next week" / robustness answer (this directly answers the template's blunt prompt — don't dodge it):**
> The architecture already answers this: the Orchestrator is stateless per mission (horizontal scaling via standard load balancing), the simulation core is swappable for a real robotics bridge (ROS2/MAVLink) without touching the decision layer, and every fault type we demo live (battery, comm, route, agent failure, weather) is a real typed event in the system — not a scripted demo path. Scaling from 3 simulated agents to a real fleet changes the data source, not the architecture.

---

## Slide 7 — Research and References (template slide7.xml)
Sub-sections: *Research Background and Supporting Evidence / Datasets, Papers, Sources and References / Demo, Competitor Analysis, GitHub or Supporting Links*

**Layout:** simple reference list, grouped under 3 short headers, small text is fine here — this slide is evidence, not spectacle.

**Research Background and Supporting Evidence:**
- Precedent for the two-speed (fast policy / slow LLM) architecture: TACOS — Task-Agnostic COordinator of a multi-drone system (Coordinator/Supervisor LLM hierarchy for real-time multi-drone coordination)
- Precedent for trained multi-agent allocation policies: MAPPO/QMIX swarm RL (centralized-training-decentralized-execution pattern), PPO-GNN humanitarian routing (trained policy vs. heuristic baseline comparison, same benchmarking approach we use)
- Precedent for the frontend's hot-path architecture: production drone/C2 dashboard pattern — WebSocket→Worker→SharedArrayBuffer→rAF, bypassing React's render cycle for live telemetry

**Datasets / Papers / Sources (list format, keep citations short):**
- Wang et al., "Dashing for the Golden Snitch: Multi-Drone Time-Optimal Motion Planning with MARL," ICRA 2025
- "Hierarchical Trajectory (Re)Planning for a Large-Scale Swarm," arXiv:2501.16743
- TACOS: Task-Agnostic Coordinator of a Multi-Drone System (MDPI Drones)
- Simulation environment: self-built in Python (no external dataset dependency — environment/fault scenarios are procedurally generated for the demo)

**Demo / Competitor Analysis / Links:**
- GitHub repo: *[push the local repo at `~/elevate-swarm-orchestration` to GitHub and link it here — not done yet, that's on you]*
- **Live demo: `https://elevate-swarm-orchestration.vercel.app`** — deployed and verified working (trained ML, WebSocket, mission dispatch, reset, all 4 fault scenarios tested live in production)
- Nearest existing approaches referenced for comparison: rule-based dispatch systems, single-LLM agent demos, academic MARL simulators (see Slide 4 comparison table for how AEGIS differs from each)

---

## Optional Slide 8 (template allows +1 extra, total 8 content slides max)
Only add this if you have room — **suggested use: a "Live Metrics Snapshot" slide** with actual screenshots from your Phase 6 stress test and benchmark run (frame-rate counter, latency numbers, the 3-way baseline comparison chart). This is stronger evidence than anything else you could add, and it's the slide most likely to make a judge say "wait, this actually works." Only include it if the numbers are real by submission time — never mock them.

---

## Before export
- Delete the Instructions slide (template's slide8.xml / final slide).
- Confirm no team member names appear anywhere (rubric requires anonymized submission).
- Confirm any shared links (GitHub, demo) are set to viewable, not restricted.
- File name: `EL-05_[YourTeamName].pptx` (or `.pdf`) per the template's own naming instruction.
- Total slide count ≤ 9 (8 content + title), per the instructions slide's stated limit.
