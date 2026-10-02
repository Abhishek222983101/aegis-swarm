import { Scene } from './components/Scene'
import { SceneErrorBoundary } from './components/SceneErrorBoundary'
import { HUD } from './components/HUD'
import { DecisionFeed } from './components/DecisionFeed'
import { ScenarioInjector } from './components/ScenarioInjector'
import { EscalationConsole } from './components/EscalationConsole'
import { MissionIntake } from './components/MissionIntake'
import { useAegisSocket } from './lib/useAegisSocket'

export default function App() {
  useAegisSocket()

  return (
    <div className="flex h-screen w-screen flex-col bg-ink p-3 gap-3">
      <header className="flex items-center justify-between border-b-[3px] border-paper pb-2">
        <h1 className="font-display text-2xl tracking-tight">
          AEGIS <span className="text-amber">/</span> MISSION ORCHESTRATION
        </h1>
        <p className="mono-tag text-neutral-500">EL-05 · AUTONOMOUS SWARM PROTOTYPE</p>
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
