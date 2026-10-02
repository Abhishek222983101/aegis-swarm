import { useAegisStore } from '../store'
import { COLORS } from '../lib/colors'

const DECISION_LABEL: Record<string, string> = {
  reassign: 'REASSIGN',
  reposition: 'REPOSITION',
  escalate: 'ESCALATE',
  terminate: 'TERMINATE',
  acknowledge: 'ACK',
}

const DECISION_COLOR: Record<string, string> = {
  reassign: COLORS.signalGreen,
  reposition: COLORS.signalBlue,
  escalate: COLORS.amber,
  terminate: COLORS.signalRed,
  acknowledge: COLORS.line,
}

export function DecisionFeed() {
  const decisions = useAegisStore((s) => s.decisions)

  return (
    <div className="panel flex h-full flex-col">
      <div className="border-b-[3px] border-paper px-3 py-2">
        <h2 className="font-display text-sm tracking-tight">DECISION FEED</h2>
      </div>
      <div className="flex-1 space-y-2 overflow-y-auto p-3">
        {decisions.length === 0 && (
          <p className="mono-tag text-neutral-500">Waiting for swarm activity&hellip;</p>
        )}
        {decisions.map((d, i) => (
          <div key={`${d.timestamp}-${i}`} className="border-l-4 pl-2 py-1" style={{ borderColor: DECISION_COLOR[d.decision] }}>
            <div className="flex items-center justify-between">
              <span
                className="mono-tag font-bold"
                style={{ color: DECISION_COLOR[d.decision] }}
              >
                {DECISION_LABEL[d.decision] ?? d.decision.toUpperCase()}
              </span>
              {d.confidence_score != null && (
                <span className="mono-tag text-neutral-400">conf {d.confidence_score.toFixed(2)}</span>
              )}
            </div>
            <p className="text-sm leading-snug text-neutral-200">{d.reasoning_text}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
