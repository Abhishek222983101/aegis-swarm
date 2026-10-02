import { useAegisStore } from '../store'
import { STATUS_COLOR } from '../lib/colors'

export function HUD() {
  const worldState = useAegisStore((s) => s.worldState)
  const connectionStatus = useAegisStore((s) => s.connectionStatus)
  const selectAgent = useAegisStore((s) => s.selectAgent)
  const selectedAgentId = useAegisStore((s) => s.selectedAgentId)

  return (
    <div className="panel flex h-full flex-col">
      <div className="flex items-center justify-between border-b-[3px] border-paper px-3 py-2">
        <h2 className="font-display text-sm tracking-tight">SWARM STATUS</h2>
        <span
          className="mono-tag"
          style={{ color: connectionStatus === 'open' ? '#00e676' : '#ff3b30' }}
        >
          {connectionStatus === 'open' ? '● LIVE' : '○ RECONNECTING'}
        </span>
      </div>
      <div className="flex items-center justify-between px-3 py-2 border-b border-line">
        <span className="mono-tag text-neutral-400">tick</span>
        <span className="mono-tag">{worldState?.tick ?? 0}</span>
      </div>
      <div className="flex items-center justify-between px-3 py-2 border-b border-line">
        <span className="mono-tag text-neutral-400">weather</span>
        <span className="mono-tag uppercase">{worldState?.weather ?? '—'}</span>
      </div>
      <div className="flex-1 space-y-2 overflow-y-auto p-3">
        {(worldState?.agents ?? []).map((agent) => (
          <button
            key={agent.id}
            onClick={() => selectAgent(agent.id)}
            className="block w-full border-2 px-2 py-1.5 text-left transition-colors"
            style={{
              borderColor: selectedAgentId === agent.id ? '#ffb800' : '#2c2c2c',
              background: selectedAgentId === agent.id ? '#1a1a1a' : 'transparent',
            }}
          >
            <div className="flex items-center justify-between">
              <span className="mono-tag font-bold">{agent.id}</span>
              <span className="mono-tag" style={{ color: STATUS_COLOR[agent.status] }}>
                {agent.status.toUpperCase()}
              </span>
            </div>
            <div className="mt-1 h-1.5 w-full bg-neutral-800">
              <div
                className="h-full"
                style={{
                  width: `${Math.max(0, agent.battery)}%`,
                  background: agent.battery < 20 ? '#ff3b30' : agent.battery < 50 ? '#ffb800' : '#00e676',
                }}
              />
            </div>
            <p className="mono-tag mt-1 truncate text-neutral-400">
              {agent.current_task ?? 'idle'} {agent.comm_lost ? '· comm-isolated' : ''}
            </p>
          </button>
        ))}
      </div>
    </div>
  )
}
