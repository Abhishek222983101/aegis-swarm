import { useState } from 'react'
import { useAegisStore } from '../store'
import { api } from '../lib/api'

export function EscalationConsole() {
  const escalations = useAegisStore((s) => s.escalations)
  const resolveEscalation = useAegisStore((s) => s.resolveEscalation)
  const [busyId, setBusyId] = useState<string | null>(null)

  const pending = Object.values(escalations).filter((e) => !e.resolved)
  if (pending.length === 0) return null

  async function respond(id: string, decision: 'approve' | 'override') {
    setBusyId(id)
    try {
      await api.respondEscalation(id, decision)
      resolveEscalation(id, decision)
    } catch {
      // backend will still auto-resolve on timeout; UI just stops showing "busy"
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="fixed inset-x-0 top-0 z-50 flex justify-center p-4">
      <div className="panel-amber w-full max-w-xl">
        <div className="border-b-[3px] border-ink px-4 py-2">
          <h2 className="font-display text-base">HUMAN ESCALATION REQUIRED</h2>
        </div>
        <div className="space-y-3 p-4">
          {pending.map((esc) => (
            <div key={esc.id} className="border-2 border-ink bg-paper px-3 py-2">
              <p className="mono-tag mb-2">{esc.id}</p>
              <p className="mb-3 text-sm font-medium">{esc.reasoning}</p>
              <div className="flex gap-2">
                <button
                  className="btn-brutal flex-1 text-xs"
                  style={{ background: '#00e676', color: '#000', borderColor: '#000' }}
                  disabled={busyId === esc.id}
                  onClick={() => respond(esc.id, 'approve')}
                >
                  APPROVE
                </button>
                <button
                  className="btn-brutal flex-1 text-xs"
                  style={{ background: '#ff3b30', color: '#000', borderColor: '#000' }}
                  disabled={busyId === esc.id}
                  onClick={() => respond(esc.id, 'override')}
                >
                  OVERRIDE
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
