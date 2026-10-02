import { useRef, useState } from 'react'
import { useAegisStore } from '../store'
import type { WorldState } from '../types'

const FRAME_INTERVAL_MS = 500 // matches backend TICK_INTERVAL_SECONDS

/** Demo-safety net (BUILD-PLAN.md Phase 6.3) — if WiFi dies mid-presentation,
 * switch to replaying the last ~60s of real captured state from the backend's
 * rolling buffer instead of staring at a frozen/disconnected screen. This is
 * real captured data, not a canned animation — the timing and values are
 * whatever actually happened moments ago. */
export function ReplayToggle() {
  const replayMode = useAegisStore((s) => s.replayMode)
  const setReplayMode = useAegisStore((s) => s.setReplayMode)
  const setWorldState = useAegisStore((s) => s.setWorldState)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const intervalRef = useRef<number | null>(null)

  async function startReplay() {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/server/replay')
      if (!res.ok) throw new Error(`replay buffer fetch failed: ${res.status}`)
      const buffer: { type: string; data: WorldState }[] = await res.json()
      const frames = buffer.filter((m) => m.type === 'state').map((m) => m.data)
      if (frames.length === 0) throw new Error('replay buffer is empty — nothing captured yet')

      setReplayMode(true)
      let i = 0
      intervalRef.current = window.setInterval(() => {
        setWorldState(frames[i % frames.length])
        i++
      }, FRAME_INTERVAL_MS)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'failed to start replay')
    } finally {
      setLoading(false)
    }
  }

  function stopReplay() {
    if (intervalRef.current) window.clearInterval(intervalRef.current)
    intervalRef.current = null
    setReplayMode(false)
  }

  return (
    <div className="flex items-center gap-2">
      {!replayMode ? (
        <button
          className="btn-brutal text-xs"
          disabled={loading}
          onClick={startReplay}
          title="Demo-safety: replay the last ~60s of captured state if the live connection drops"
        >
          {loading ? 'LOADING…' : '⟲ REPLAY (DEMO SAFETY)'}
        </button>
      ) : (
        <button className="btn-brutal-amber text-xs" onClick={stopReplay}>
          ■ EXIT REPLAY — RESUME LIVE
        </button>
      )}
      {error && <span className="mono-tag text-signal-red">{error}</span>}
    </div>
  )
}
