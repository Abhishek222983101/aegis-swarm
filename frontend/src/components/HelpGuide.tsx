import { useState } from 'react'

interface Step {
  n: number
  title: string
  body: string
}

const STEPS: Step[] = [
  {
    n: 1,
    title: 'Look at the 3D view',
    body: 'Drag to orbit, scroll to zoom. You should see 2 drones floating above a rover, plus a relay mast — all on a dark grid.',
  },
  {
    n: 2,
    title: 'Launch a mission',
    body: 'Click one of the quick-prompt buttons in MISSION OBJECTIVE (bottom-left), or type your own, then LAUNCH MISSION. Agents should start moving within ~1s.',
  },
  {
    n: 3,
    title: 'Select an agent',
    body: 'Click any agent card in SWARM STATUS (top-left). It highlights with an amber ring in the 3D view, and becomes the target for the buttons on the right.',
  },
  {
    n: 4,
    title: 'Break something',
    body: 'Click any button in SCENARIO INJECTOR (top-right): drain its battery, cut its comms, or fail it outright. Watch DECISION FEED (bottom-right) explain what the system did about it.',
  },
  {
    n: 5,
    title: 'Push it until it escalates or terminates',
    body: 'Keep failing agents. Eventually a HUMAN ESCALATION banner appears, or — if the whole mission becomes unachievable — a TERMINATE decision fires. Both are real reasoning, not scripted.',
  },
  {
    n: 6,
    title: 'Stuck or dead? Reset.',
    body: 'Click ↺ RESET SIMULATION (top-right of the header) any time. Fresh, fully-healthy swarm in one click — no restart needed.',
  },
]

export function HelpGuide() {
  const [open, setOpen] = useState(false)

  if (!open) {
    return (
      <button
        className="btn-brutal-amber text-xs"
        onClick={() => setOpen(true)}
        title="Step-by-step guide to testing this prototype"
      >
        ? HOW TO TEST THIS
      </button>
    )
  }

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/80 p-4">
      <div className="panel-amber max-h-[85vh] w-full max-w-3xl overflow-y-auto">
        <div className="flex items-center justify-between border-b-[3px] border-ink px-4 py-3">
          <h2 className="font-display text-lg">HOW TO TEST AEGIS</h2>
          <button
            className="border-2 border-ink bg-black px-3 py-1 text-xs font-bold text-paper"
            onClick={() => setOpen(false)}
          >
            CLOSE ✕
          </button>
        </div>
        <div className="grid grid-cols-1 gap-3 p-4 sm:grid-cols-2">
          {STEPS.map((step) => (
            <div key={step.n} className="border-2 border-ink bg-paper p-3">
              <div className="mb-1 flex items-center gap-2">
                <span className="flex h-6 w-6 items-center justify-center border-2 border-ink bg-ink font-display text-xs text-amber">
                  {step.n}
                </span>
                <h3 className="font-display text-sm text-ink">{step.title}</h3>
              </div>
              <p className="text-sm leading-snug text-ink">{step.body}</p>
            </div>
          ))}
        </div>
        <div className="border-t-2 border-ink p-4 text-xs text-ink">
          Tip: use the camera toolbar in the top-left of the 3D view — RESET VIEW, TOP-DOWN, and
          FOLLOW SELECTED (after clicking an agent) — if you lose track of the swarm while orbiting.
        </div>
      </div>
    </div>
  )
}
