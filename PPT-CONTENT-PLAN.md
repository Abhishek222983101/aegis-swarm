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
- Insert the Gemini-generated diagram from `SYSTEM-ARCHITECTURE.md` §4 here.
- One-line caption under it: *"5-layer pipeline: Operator Cockpit → Go Orchestrator (Supervisor Loop) → ML Decision Layer (fast ONNX allocator + LLM mission planner) → Rust Simulation Core → Heterogeneous Agent Fleet."*

**Technologies, Frameworks and Models (badge row — small labeled boxes, not a paragraph):**
`Rust (sim core)` · `PyTorch → ONNX Runtime (trained policy)` · `Go (orchestrator, WebSocket hub)` · `React Three Fiber (3D cockpit)` · `Redis (state fan-out)` · `PostgreSQL (decision audit log)` · `LLM Mission Planner (NL → task DAG)`

**Implementation and System Components (3 short lines, each tied to a metric if you have one by pitch time):**
- Simulation core ticks at 30Hz, deterministic, zero-GC-pause agent state engine
- Trained assignment policy benchmarked against Greedy and Hungarian-algorithm baselines — [X]% faster mission completion once you have the number from Build Phase 6.2
- Frontend renders live swarm state at 60fps via a worker + SharedArrayBuffer hot path that bypasses React's render cycle entirely for position updates

**One-sentence "why polyglot" callout box** (use the line from `SYSTEM-ARCHITECTURE.md` §2): *"Each layer runs in the language built for its job, so the system stays real-time under load instead of degrading like a single-language stack would."*

---

## Slide 4 — Innovation and Uniqueness (template slide4.xml)
Sub-sections: *Innovative Approach and Core Differentiators / Unique Features and Functionalities / Comparison with Existing Approaches*

**Layout:** comparison table as the dominant visual (judges love a clean comparison table — it does the differentiation argument for you).

**Core Differentiators (3 bullets max):**
- A trained policy that conditions on *predicted future state* (battery trajectory, comm degradation), not just current snapshot
- A two-speed decision architecture — millisecond reassignment for routine events, LLM reasoning only for structural mission changes — so it's real-time where it must be and intelligent where it should be
- Every autonomous decision is logged with a human-readable reason and traceable to a Postgres row — not a black box

**Comparison table** (pull directly from `SYSTEM-ARCHITECTURE.md` §7 — use the full 4-row table, format as a clean grid, bold the AEGIS column):
Rule-based dispatch | Single-LLM "agentic" demos | Academic multi-agent RL papers | **AEGIS**

**Visual:** the comparison table itself IS the visual for this slide — don't add a separate chart, keep it clean and let the table breathe (plenty of cell padding).

---

## Slide 5 — Feasibility and Viability (template slide5.xml)
Sub-sections: *Technical and Operational Feasibility / Scalability, Deployment and Resource Requirements / Challenges, Risks and Sustainability*

**Layout:** 3-4 large stat callouts across the top (big number + small label), short text underneath each column.

**Stat callouts (fill with real numbers once captured in Build Phase 6, per the metrics table in `SYSTEM-ARCHITECTURE.md` §6):**
- `<10ms` — Allocator inference latency
- `<1s` — event-to-replan visible latency on stage
- `[X]` agents — sustained at 60fps in the 3D cockpit
- `[X]%` — mission completion improvement, trained policy vs. rule-based baseline

**Technical and Operational Feasibility (short):**
> Every component chosen has been proven at production scale elsewhere (Rust sim engines in production RL systems, Go+Redis+WebSocket for real-time multi-agent dashboards, ONNX for latency-critical trained-model serving) — this isn't a novel unproven stack, it's a proven pattern applied to a new mission-orchestration problem.

**Scalability, Deployment and Resource Requirements:**
- Horizontally scalable: Orchestrator is stateless per-mission (state lives in Redis/Postgres), so multiple missions can run concurrently
- Simulation core swappable for a real MAVLink/ROS2 bridge without changing the Orchestrator or frontend contract — same gRPC interface — path to real hardware is architected in, not bolted on later
- Deployable as containers (Docker Compose for demo, same images go to Kubernetes for production)

**Challenges, Risks and Sustainability (be honest — judges respect this):**
- LLM-in-the-loop latency for structural replans — mitigated by keeping LLM out of the fast/routine decision path entirely
- Simulation-to-reality gap if moving to physical hardware — mitigated by the capability-abstraction boundary (sensor/actuator stubs are swappable)
- Demo network reliability — mitigated by the Redis replay-buffer "cached mode" fallback (§4.6 in architecture doc)

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
- Simulation environment: self-built on Rust (no external dataset dependency — environment/fault scenarios are procedurally generated for the demo)

**Demo / Competitor Analysis / Links:**
- GitHub repo: *[your repo link]*
- Live demo: *[local/hosted link]*
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
