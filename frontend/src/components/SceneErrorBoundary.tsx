import { Component, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  failed: boolean
}

/** WebGL can fail to initialize for reasons entirely outside this app's
 * control — disabled GPU, sandboxed/remote-desktop environments, old drivers,
 * browser flags. Without this boundary, a Canvas failure takes down the whole
 * React tree (confirmed: it crashes to a blank black page with zero
 * indication of what went wrong — exactly the "breaking point" to avoid on a
 * judge's laptop). The rest of the app — HUD, Decision Feed, Scenario
 * Injector, Mission Intake — must keep working even if the 3D view can't. */
export class SceneErrorBoundary extends Component<Props, State> {
  state: State = { failed: false }

  static getDerivedStateFromError(): State {
    return { failed: true }
  }

  componentDidCatch(error: unknown) {
    console.error('3D scene failed to render:', error)
  }

  render() {
    if (this.state.failed) {
      return (
        <div className="panel flex h-full flex-col items-center justify-center gap-3 p-8 text-center">
          <h2 className="font-display text-lg text-amber">3D VIEW UNAVAILABLE</h2>
          <p className="max-w-sm text-sm text-neutral-300">
            This browser or environment couldn't start WebGL — the mission is still running and fully
            controllable from the panels on either side. Try a different browser, or enable hardware
            acceleration, to restore the live 3D cockpit.
          </p>
        </div>
      )
    }
    return this.props.children
  }
}
