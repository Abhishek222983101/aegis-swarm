import { Scene } from './components/Scene'
import { SceneErrorBoundary } from './components/SceneErrorBoundary'
import { HUD } from './components/HUD'
import { DecisionFeed } from './components/DecisionFeed'
import { ScenarioInjector } from './components/ScenarioInjector'
import { EscalationConsole } from './components/EscalationConsole'
import { MissionIntake } from './components/MissionIntake'
import { ReplayToggle } from './components/ReplayToggle'
import { ResetButton } from './components/ResetButton'
import { HelpGuide } from './components/HelpGuide'
import { useAegisStore } from './store'
import { useAegisSocket } from './lib/useAegisSocket'

export default function App() {
  useAegisSocket()
  const replayMode = useAegisStore((s) => s.replayMode)

  return (
    <div className="flex h-screen w-screen flex-col bg-ink p-3 gap-3">
      <header className="flex items-center justify-between border-b-[3px] border-paper pb-2">
        <h1 className="font-display text-2xl tracking-tight">
          AEGIS <span className="text-amber">/</span> MISSION ORCHESTRATION
          {replayMode && <span className="ml-3 text-sm text-signal-red">● REPLAY MODE</span>}
        </h1>
        <div className="flex items-center gap-3">
          <HelpGuide />
          <ReplayToggle />
          <ResetButton />
          <p className="mono-tag text-neutral-500">EL-05 · AUTONOMOUS SWARM PROTOTYPE</p>
        </div>
      </header>

      <div className="grid flex-1 grid-cols-[280px_1fr_320px] gap-3 overflow-hidden">
        <div className="flex flex-col gap-3 overflow-hidden">
          <div className="h-[55%]">
            <HUD />
          </div>
          <div className="h-[45%]">
            <MissionIntake />
          </div>
        </div>

        <div className="panel overflow-hidden">
          <SceneErrorBoundary>
            <Scene />
          </SceneErrorBoundary>
        </div>

        <div className="flex flex-col gap-3 overflow-hidden">
          <div className="h-[45%]">
            <ScenarioInjector />
          </div>
          <div className="h-[55%]">
            <DecisionFeed />
          </div>
        </div>
      </div>

      <EscalationConsole />
    </div>
  )
}
