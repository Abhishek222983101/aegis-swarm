// Same-origin in production (Vercel Services rewrites /server/* to the FastAPI
// backend); the Vite dev server proxies /server to localhost:8731 (see
// vite.config.ts) so this base path works unmodified in both environments.
const BASE = '/server'

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }))
    throw new Error(err.error ?? `request failed: ${res.status}`)
  }
  return res.json()
}

export const api = {
  injectBatteryDrain: (agent_id: string, drop_to = 15) =>
    postJSON('/inject/battery-drain', { agent_id, drop_to }),
  injectCommLoss: (agent_id: string) => postJSON('/inject/comm-loss', { agent_id }),
  injectRouteBlock: (zone_id: string, x: number, y: number, radius = 40) =>
    postJSON('/inject/route-block', { zone_id, x, y, radius }),
  injectAgentFailure: (agent_id: string) => postJSON('/inject/agent-failure', { agent_id }),
  injectWeather: (level: 'clear' | 'degraded' | 'severe') => postJSON('/inject/weather', { level }),
  injectTargetFound: (x: number, y: number, priority = 'high') =>
    postJSON('/inject/target-found', { x, y, priority }),
  postMission: (objective: string) => postJSON('/mission', { objective }),
  respondEscalation: (id: string, decision: 'approve' | 'override') =>
    postJSON(`/escalation/${id}/respond`, { decision }),
}
