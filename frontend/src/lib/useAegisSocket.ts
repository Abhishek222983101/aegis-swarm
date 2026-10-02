import { useEffect, useRef } from 'react'
import { useAegisStore } from '../store'
import type { ServerMessage } from '../types'

const RECONNECT_DELAY_MS = 1500

export function useAegisSocket() {
  const setWorldState = useAegisStore((s) => s.setWorldState)
  const setConnectionStatus = useAegisStore((s) => s.setConnectionStatus)
  const pushDecision = useAegisStore((s) => s.pushDecision)
  const resolveEscalation = useAegisStore((s) => s.resolveEscalation)
  const setMissionPlan = useAegisStore((s) => s.setMissionPlan)

  const wsRef = useRef<WebSocket | null>(null)
  const stoppedRef = useRef(false)

  useEffect(() => {
    stoppedRef.current = false

    function connect() {
      if (stoppedRef.current) return
      const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
      const ws = new WebSocket(`${protocol}://${window.location.host}/server/ws`)
      wsRef.current = ws

      ws.onopen = () => setConnectionStatus('open')
      ws.onclose = () => {
        setConnectionStatus('closed')
        if (!stoppedRef.current) setTimeout(connect, RECONNECT_DELAY_MS)
      }
      ws.onerror = () => ws.close()

      ws.onmessage = (ev) => {
        let msg: ServerMessage
        try {
          msg = JSON.parse(ev.data)
        } catch {
          return
        }
        switch (msg.type) {
          case 'state':
            // Replay mode owns worldState while active — ignore live pushes so
            // a WiFi hiccup mid-replay can't interleave stale/fresh frames.
            if (!useAegisStore.getState().replayMode) setWorldState(msg.data)
            break
          case 'decision':
            pushDecision(msg.data)
            break
          case 'escalation_resolved':
            resolveEscalation(msg.data.id, msg.data.operator_decision)
            break
          case 'mission_plan':
            setMissionPlan(msg.data)
            break
          default:
            break
        }
      }
    }

    connect()
    return () => {
      stoppedRef.current = true
      wsRef.current?.close()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
}
