import { useState } from 'react'
import { useAegisStore } from '../store'
import { api } from '../lib/api'

/** The judge's toy — every PRD fault type is a direct, obvious click target.
 * Errors from the backend surface inline, never as a silent failure or a
 * crashed UI — this panel is what a non-technical operator touches live. */
export function ScenarioInjector() {
  const worldState = useAegisStore((s) => s.worldState)
  const selectedAgentId = useAegisStore((s) => s.selectedAgentId)
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const agents = worldState?.agents ?? []
  const activeAgent = selectedAgentId ?? agents.find((a) => a.status !== 'lost')?.id

  async function run(label: string, fn: () => Promise<unknown>) {
    setError(null)
    setBusy(label)
    try {
      await fn()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'injection failed')
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="panel flex h-full flex-col">
      <div className="border-b-[3px] border-paper px-3 py-2">
        <h2 className="font-display text-sm tracking-tight">SCENARIO INJECTOR</h2>
        <p className="mono-tag text-neutral-400">
          target: {activeAgent ?? 'none selected — click an agent'}
        </p>
      </div>
      <div className="grid grid-cols-2 gap-2 p-3">
        <button
          className="btn-brutal-amber text-xs"
          disabled={!activeAgent || busy !== null}
          onClick={() => activeAgent && run('battery', () => api.injectBatteryDrain(activeAgent))}
        >
          {busy === 'battery' ? 'DRAINING…' : 'DRAIN BATTERY'}
        </button>
        <button
          className="btn-brutal text-xs"
          disabled={!activeAgent || busy !== null}
          onClick={() => activeAgent && run('comm', () => api.injectCommLoss(activeAgent))}
        >
          {busy === 'comm' ? 'CUTTING…' : 'CUT COMMS'}
        </button>
        <button
          className="btn-brutal text-xs"
          disabled={!activeAgent || busy !== null}
          onClick={() => activeAgent && run('fail', () => api.injectAgentFailure(activeAgent))}
        >
          {busy === 'fail' ? 'FAILING…' : 'FAIL AGENT'}
        </button>
        <button
          className="btn-brutal text-xs"
          disabled={busy !== null}
          onClick={() => run('route', () => api.injectRouteBlock(`zone-${Date.now()}`, 150, 150, 50))}
        >
          {busy === 'route' ? 'BLOCKING…' : 'BLOCK ROUTE'}
        </button>
        <button
          className="btn-brutal text-xs"
          disabled={busy !== null}
          onClick={() => run('weather', () => api.injectWeather('severe'))}
        >
          {busy === 'weather' ? 'SHIFTING…' : 'SEVERE WEATHER'}
        </button>
        <button
          className="btn-brutal text-xs"
          disabled={busy !== null}
          onClick={() => run('target', () => api.injectTargetFound(Math.random() * 400, Math.random() * 400))}
        >
          {busy === 'target' ? 'REPORTING…' : 'TARGET FOUND'}
        </button>
      </div>
      {error && (
        <div className="mx-3 mb-3 border-2 border-signal-red bg-black px-2 py-1">
          <p className="mono-tag" style={{ color: '#ff3b30' }}>
            {error}
          </p>
        </div>
      )}
    </div>
  )
}
