import { useState } from 'react'
import { api } from '../lib/api'
import { useAegisStore } from '../store'

/** The recovery button. If every agent is dead or the swarm is wedged, this
 * gets back to a clean, working demo in one click — no terminal, no server
 * restart. Every judge-facing control needs an undo/recover path; this is it. */
export function ResetButton() {
  const [busy, setBusy] = useState(false)
  const setReplayMode = useAegisStore((s) => s.setReplayMode)
  const replayMode = useAegisStore((s) => s.replayMode)

  async function handleReset() {
    setBusy(true)
    try {
      if (replayMode) setReplayMode(false) // don't reset while replaying a stale buffer
      await api.reset()
    } catch {
      // the WebSocket 'reset' broadcast + next state push will still land even
      // if this specific fetch response was lost — nothing more to do here.
    } finally {
      setBusy(false)
    }
  }

  return (
    <button
      className="btn-brutal text-xs"
      style={{ borderColor: '#ff3b30', color: '#ff3b30' }}
      disabled={busy}
      onClick={handleReset}
      title="Restore a fresh, fully-healthy swarm — use this if agents are dead or the demo is stuck"
    >
      {busy ? 'RESETTING…' : '↺ RESET SIMULATION'}
    </button>
  )
}
