import { useEffect, useState } from 'react'
import { useAegisStore } from '../store'
import { api } from '../lib/api'

interface MissionTemplate {
  label: string
  objective: string
}

export function MissionIntake() {
  const missionPlan = useAegisStore((s) => s.missionPlan)
  const [objective, setObjective] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [templates, setTemplates] = useState<MissionTemplate[]>([])

  useEffect(() => {
    api.getMissionTemplates().then(setTemplates).catch(() => setTemplates([]))
  }, [])

  async function launch(text: string) {
    if (!text.trim()) return
    setBusy(true)
    setError(null)
    try {
      await api.postMission(text.trim())
    } catch (e) {
      setError(e instanceof Error ? e.message : 'mission intake failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="panel flex h-full flex-col">
      <div className="border-b-[3px] border-paper px-3 py-2">
        <h2 className="font-display text-sm tracking-tight">MISSION OBJECTIVE</h2>
      </div>
      <div className="p-3">
        {/* Ready-to-use prompts — click one to launch immediately, or edit it
            first in the box below. No one should have to write a mission
            objective from a blank page to try the system. */}
        {templates.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-1.5">
            {templates.map((t) => (
              <button
                key={t.label}
                className="border-2 border-line px-2 py-1 text-[11px] font-bold text-neutral-300 hover:border-amber hover:text-amber"
                disabled={busy}
                onClick={() => {
                  setObjective(t.objective)
                  launch(t.objective)
                }}
                title={t.objective}
              >
                {t.label}
              </button>
            ))}
          </div>
        )}
        <textarea
          className="mono-tag w-full resize-none border-2 border-line bg-black p-2 text-paper focus:border-amber focus:outline-none"
          rows={2}
          placeholder="e.g. Scout Sector 7 and establish a comm relay"
          value={objective}
          onChange={(e) => setObjective(e.target.value)}
        />
        <button className="btn-brutal-amber mt-2 w-full text-xs" disabled={busy} onClick={() => launch(objective)}>
          {busy ? 'DECOMPOSING…' : 'LAUNCH MISSION'}
        </button>
        {error && <p className="mono-tag mt-2 text-signal-red">{error}</p>}
      </div>
      {missionPlan && (
        <div className="flex-1 space-y-1.5 overflow-y-auto border-t border-line p-3">
          <p className="mono-tag text-neutral-400">
            source: {missionPlan.source} · {missionPlan.tasks.length} task(s)
          </p>
          {missionPlan.tasks.map((t) => (
            <div key={t.id} className="border-l-4 border-amber pl-2 py-0.5">
              <p className="text-sm">{t.description}</p>
              <p className="mono-tag text-neutral-500">
                {t.required_type ?? 'any type'} · priority {t.priority}
                {t.depends_on.length > 0 ? ` · after ${t.depends_on.join(', ')}` : ''}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
